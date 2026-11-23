"""The slate sheet: every number for every game, built by code.

The agent reads this sheet. It can add entries to adjustments.yaml (which
changes the model number and re-runs the sheet) but it never types a line,
a price, an edge or a stake.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from engine import config
from engine.odds import espn
from engine.odds.espn import SourceError
from engine.odds.math import no_vig
from engine.odds.wagerhouse import Wagerhouse
from engine.picks import history, sources

SPORTS = ("NFL", "College", "NBA")
DAYS_AHEAD = {"NFL": 8, "College": 8, "NBA": 2}
PUBLIC_NAMES = {
    "n.y. giants": "new york giants", "n.y. jets": "new york jets", "ny giants": "new york giants",
    "ny jets": "new york jets", "l.a. rams": "los angeles rams", "l.a. chargers": "los angeles chargers",
    "la rams": "los angeles rams", "la chargers": "los angeles chargers",
    "louisiana-monroe": "ul monroe", "louisiana-lafayette": "louisiana", "miami-florida": "miami",
    "miami-ohio": "miami (oh)", "southern miss": "southern miss", "texas-san antonio": "utsa",
    "texas-el paso": "utep", "middle tennessee st.": "middle tennessee", "central florida": "ucf",
    "florida intl": "florida international", "n.c. state": "nc state", "north carolina st.": "nc state",
    "mississippi": "ole miss", "southern cal": "usc", "brigham young": "byu", "massachusetts": "umass",
    "connecticut": "uconn", "hawaii": "hawai'i", "san jose st.": "san josé state", "sam houston st.": "sam houston",
    "appalachian st.": "app state", "pittsburgh": "pittsburgh",
}
ADJ_FILE = config.ROOT / "adjustments.yaml"


def load_adjustments() -> list[dict]:
    if not ADJ_FILE.exists():
        return []
    data = yaml.safe_load(ADJ_FILE.read_text()) or {}
    out = []
    for a in data.get("adjustments", []) or []:
        for k in ("game", "market", "points", "reason", "source", "added"):
            if k not in a:
                raise SourceError(f"adjustments.yaml entry is missing '{k}': {a}")
        if a["market"] not in ("spread", "total"):
            raise SourceError(f"adjustments.yaml market must be spread or total: {a}")
        if a["market"] == "spread" and "team" not in a:
            raise SourceError(f"adjustments.yaml spread entry needs 'team': {a}")
        if not str(a["source"]).startswith("http"):
            raise SourceError(f"adjustments.yaml entry needs a source link: {a}")
        out.append(a)
    return out


def _names(team: dict) -> set[str]:
    return espn.team_names(team)


def _find(events, name_a: str, name_b: str, start: datetime | None = None):
    a = espn.norm(PUBLIC_NAMES.get(name_a.lower().strip(), name_a))
    b = espn.norm(PUBLIC_NAMES.get(name_b.lower().strip(), name_b))
    hits = [e for e in events if a in (_names(e.home) | _names(e.away)) and b in (_names(e.home) | _names(e.away))]
    if start is not None:
        hits = [e for e in hits if abs((e.start - start).total_seconds()) < 12 * 3600]
    return hits[0] if len(hits) == 1 else None


def back_to_backs(sport: str, events: list[espn.Event], now: datetime) -> dict[str, set[str]]:
    """NBA: for each game, the team ids that also played the previous day."""
    if sport != "NBA":
        return {}
    played: dict = {}
    days = {e.start.astimezone(espn_tz()).date() for e in events}
    for d in days:
        prev = d - timedelta(days=1)
        if prev not in played:
            played[prev] = {str(t["id"]) for ev in espn.scoreboard("NBA", prev, None) for t in (ev.home, ev.away)}
    out = {}
    for e in events:
        prev = e.start.astimezone(espn_tz()).date() - timedelta(days=1)
        out[e.event_id] = {tid for tid in (str(e.home["id"]), str(e.away["id"])) if tid in played.get(prev, set())}
    return out


def espn_tz():
    from zoneinfo import ZoneInfo
    return ZoneInfo("America/New_York")


def build(sport: str = "NFL", now: datetime | None = None, days_ahead: int | None = None) -> dict:
    if sport not in SPORTS:
        raise ValueError(sport)
    cfg, env = config.load_config(), config.load_env()
    pc = cfg["picks"]
    use_model = bool(pc.get("use_model_leg", False))
    now = now or datetime.now(timezone.utc)
    days_ahead = days_ahead or DAYS_AHEAD[sport]
    hfa = pc["home_field"][sport]
    problems: list[str] = []

    events = [e for e in espn.upcoming(sport, now.date() - timedelta(days=1), now.date() + timedelta(days=days_ahead)) if e.start > now]
    if not events:
        return {"sport": sport, "built_utc": now.isoformat(), "settings": {}, "problems": [f"No upcoming {sport} games in the next {days_ahead} days."],
                "games": [], "adjustments_used": []}

    hist = history.load(sport, now, cfg, env)
    land_spread, land_total = hist.land_spread, hist.land_total

    wh = Wagerhouse(env.get("WAGERHOUSE_USER", ""), env.get("WAGERHOUSE_PASSWORD", ""))
    book = {}
    for l in wh.lines(sport):
        e = _find(events, l.home, l.away, l.start)
        if e:
            book[e.event_id] = l
    sharp = {}
    for s in sources.pinnacle(sport):
        e = _find(events, s.home, s.away, s.start)
        if e:
            sharp[e.event_id] = s
    public = {}
    if sport in sources.TRACKER:
        for t in sources.tracker(sport, config.DATA / "raw" / "tracker"):
            e = _find(events, t["home"], t["road"])
            if e:
                public[e.event_id] = t
    adjustments = load_adjustments()
    b2b = back_to_backs(sport, [e for e in events if e.event_id in book], now)

    # only games the book has posted are priced; the rest are counted, not listed
    listed = [e for e in sorted(events, key=lambda e: e.start) if e.event_id in book]
    not_posted = len(events) - len(listed)
    no_public = sum(1 for e in listed if e.event_id not in public) if sport in sources.TRACKER else 0
    no_sharp = [e for e in listed if e.event_id not in sharp]
    if no_public and use_model:
        problems.append(f"{no_public} game(s) had no public-systems number; their model used market ratings alone.")
    for e in no_sharp[:8]:
        problems.append(f"No Pinnacle price for {e.away['displayName']} at {e.home['displayName']}: no fair line, no pick possible.")

    eff = None
    if sport == "NFL":
        try:
            from engine.picks import totals
            eff = totals.current(now)
        except (SourceError, ValueError) as ex:
            problems.append(f"Pace-and-efficiency numbers unavailable: {ex}")
    to_nflverse = {v: k for k, v in history.NFLVERSE_TO_ESPN.items()}
    mu = pw = None
    if sport == "NFL":
        try:
            from engine.picks import matchup
            mu, pw = matchup.current(now)
        except (SourceError, ValueError) as ex:
            problems.append(f"Matchup numbers unavailable: {ex}")

    wind_cfg = (cfg.get("models") or {}).get("wind_totals") or {}
    first_seen = dk_first_seen(sport)
    pin_hist = pinnacle_history(sport)
    games = []
    for e in listed:
        home, away = e.home["displayName"], e.away["displayName"]
        g = {"event_id": e.event_id, "game": f"{away} at {home}", "home": home, "away": away,
             "start_utc": e.start.isoformat(), "markets": [], "notes": [], "adjustments": []}
        b, s, t = book[e.event_id], sharp.get(e.event_id), public.get(e.event_id)
        dk = espn.event_odds(e, None)
        dkc = dk.current if dk else None
        hk, ak = hist.key(e.home), hist.key(e.away)
        rated = hk in hist.spread_rating and ak in hist.spread_rating
        if not rated:
            g["notes"].append("No market rating for one of these teams (too few lined games).")
        my_adj = [a for a in adjustments if espn.norm(a["game"]) == espn.norm(g["game"])]
        g["adjustments"] = list(my_adj)
        for tid in b2b.get(e.event_id, set()):
            team = home if tid == str(e.home["id"]) else away
            g["notes"].append(f"{team} is on the second night of a back-to-back. Pinnacle's line already prices it, so no adjustment is made.")
        pin_rows = pin_hist.get(e.event_id, [])
        now_sp = s.home_spread if s else None
        now_tot = s.total if s else None
        applied: list[dict] = []          # adjustment entries with the part that still counts
        for a in my_adj:
            sign = 1 if a["market"] != "spread" or espn.norm(a["team"]) in _names(e.home) else -1
            left, status = unpriced_part(a, pin_rows, now_sp, now_tot, sign)
            applied.append({**a, "applied_points": left, "status": status})
        g["adjustments"] = applied

        # ---- spread (all numbers are the HOME spread; negative = home favored)
        game_hfa = 0.0 if e.neutral else hfa
        if e.neutral:
            g["notes"].append("Neutral site: no home-field points.")
        rating_line = -(hist.spread_rating[hk] - hist.spread_rating[ak] + game_hfa) if rated else None
        public_line = -t["avg_home_margin"] if t else None
        adj_pts = 0.0
        for a in applied:
            if a["market"] == "spread":      # points are a change to that team's strength
                adj_pts += a["applied_points"] * (1 if espn.norm(a["team"]) in _names(e.home) else -1)
        parts = [x for x in (rating_line, public_line) if x is not None]
        model = (sum(parts) / len(parts) - adj_pts) if parts else None
        m = {"market": "spread", "rating_line": None if rating_line is None else round(rating_line, 2),
             "public_systems_line": None if public_line is None else round(public_line, 2),
             "public_systems_count": t["systems"] if t else 0, "adjustment_points": adj_pts,
             "model_line": None if model is None else round(model, 2), "fair_line": None}
        fair = None
        if s and s.home_spread is not None and s.home_spread_price and s.away_spread_price and model is not None:
            p_home = no_vig(s.home_spread_price, s.away_spread_price)[0]
            sharp_fair = land_spread.fair_from_price(s.home_spread, p_home)
            if use_model:
                fair = pc["market_weight"] * sharp_fair + (1 - pc["market_weight"]) * model
            else:   # the model leg is a lagged copy of the market (docs/research/04-evaluation.md): Pinnacle plus sourced adjustments only
                fair = sharp_fair - adj_pts
            m.update(pinnacle_line=s.home_spread, pinnacle_home_price=s.home_spread_price,
                     pinnacle_away_price=s.away_spread_price, pinnacle_fair=round(sharp_fair, 2), fair_line=round(fair, 2))
        if dkc and dkc.home_spread is not None:
            m["draftkings_line"], m["draftkings_open"] = dkc.home_spread, first_seen.get((e.event_id, "spread"))
        if b.home_spread is not None:
            m["book_line"] = b.home_spread
        if b.home_spread is not None and fair is not None:
            sides = []
            for side, price in (("home", b.home_spread_price), ("away", b.away_spread_price)):
                if price is None:
                    continue
                val = land_spread.value(fair, b.home_spread, side, price)
                is_bet, lim = land_spread.limit(fair, b.home_spread, side, price, pc["min_value"])
                win, push, _ = land_spread.probs(fair, b.home_spread, side)
                team = home if side == "home" else away
                show = lambda hs, sd=side: hs if sd == "home" else -hs
                sign = 1 if side == "home" else -1
                model_edge = (b.home_spread - model) * sign
                sides.append({"side": side, "pick": f"{team} {show(b.home_spread):+g}", "price": price, "value": round(val, 4),
                              "edge_points": round((b.home_spread - fair) * sign, 2), "win": round(win, 3), "push": round(push, 3),
                              "numbers_say_bet": bool(is_bet and (model_edge > 0 or not use_model)),
                              "dont_bet_past": None if lim is None else f"{team} {show(lim):+g}", "limit_line": lim,
                              "model_agrees": model_edge > 0})
            m["sides"] = sides
        g["markets"].append(m)

        # ---- total
        rating_total = (hist.avg_total + hist.total_tendency[hk] + hist.total_tendency[ak]) if rated and hist.avg_total is not None else None
        adj_t = sum(a["applied_points"] for a in applied if a["market"] == "total")
        wind = wind_adjustment(sport, e, now, wind_cfg, problems)
        model_t = None if rating_total is None else rating_total + adj_t
        mt = {"market": "total", "rating_line": None if rating_total is None else round(rating_total, 2),
              "adjustment_points": adj_t, "model_line": None if model_t is None else round(model_t, 2), "fair_line": None}
        fair_t = None
        if s and s.total is not None and s.over_price and s.under_price and model_t is not None:
            p_over = no_vig(s.over_price, s.under_price)[0]
            sharp_t = land_total.fair_from_price(s.total, p_over)
            if use_model:
                fair_t = pc["market_weight"] * sharp_t + (1 - pc["market_weight"]) * model_t
            else:
                fair_t = sharp_t + adj_t
            fair_t_no_model = fair_t
            if wind and wind["used"]:
                fair_t += wind["points"]
            mt.update(pinnacle_line=s.total, pinnacle_fair=round(sharp_t, 2), fair_line=round(fair_t, 2))
        if wind:
            mt["wind_model"] = wind
        if dkc and dkc.total is not None:
            mt["draftkings_line"], mt["draftkings_open"] = dkc.total, first_seen.get((e.event_id, "total"))
        if b.total is not None:
            mt["book_line"] = b.total
        if b.total is not None and fair_t is not None:
            sides = []
            for side, price in (("over", b.over_price), ("under", b.under_price)):
                if price is None:
                    continue
                val = land_total.value(fair_t, b.total, side, price)
                is_bet, lim = land_total.limit(fair_t, b.total, side, price, pc["min_value"])
                bet_without_model, _ = land_total.limit(fair_t_no_model, b.total, side, price, pc["min_value"])
                win, push, _ = land_total.probs(fair_t, b.total, side)
                sign = 1 if side == "over" else -1
                model_edge = (model_t - b.total) * sign
                sides.append({"side": side, "pick": f"{side.title()} {b.total:g}", "price": price, "value": round(val, 4),
                              "edge_points": round((fair_t - b.total) * sign, 2), "win": round(win, 3), "push": round(push, 3),
                              # no real totals model yet: a total needs a specific sourced adjustment (wind, QB, a star out)
                              "numbers_say_bet": bool(is_bet and (not use_model or (model_edge > 0 and adj_t != 0))),
                              "dont_bet_past": None if lim is None else f"{side.title()} {lim:g}", "limit_line": lim,
                              "model_agrees": model_edge > 0})
                if wind and wind["used"] and is_bet and not bet_without_model:
                    sides[-1].update(model="wind", max_status=wind_cfg.get("max_status", "Conditional"),
                                     model_says=f"Wind model: {wind['wind_mph']:g} mph forecast at kickoff, total {wind['points']:+.1f} points.")
            mt["sides"] = sides
        if eff is not None:
            hn, an = to_nflverse.get(e.home["abbreviation"], e.home["abbreviation"]), to_nflverse.get(e.away["abbreviation"], e.away["abbreviation"])
            et = eff.total(hn, an)
            # shown for context only: in testing this number added nothing on top of the market's total
            mt["efficiency_total_for_context_only"] = None if et is None else round(et, 1)
            g["luck"] = {"home": eff.luck.get(hn), "away": eff.luck.get(an)}
        if mu is not None:
            from engine.picks import matchup
            hn, an = to_nflverse.get(e.home["abbreviation"], e.home["abbreviation"]), to_nflverse.get(e.away["abbreviation"], e.away["abbreviation"])
            pm = matchup.power_margin(pw, hn, an, game_hfa)
            # the engine's own play-by-play number; in testing it added nothing on top of the closing spread
            m["own_power_line_for_context_only"] = None if pm is None else round(-pm, 1)
            g["matchup"] = {"home": matchup.brief(mu.get(hn)), "away": matchup.brief(mu.get(an)),
                            "how_to_read": "rank 1 is best for that unit; 'recent' is the last 4 games, 'earlier' the games before; toughness rank 1 means the hardest opponents faced"}
        g["markets"].append(mt)
        games.append(g)

    # keep the research list workable: only the strongest flags stay flagged
    flagged = sorted((s for g in games for m in g["markets"] for s in m.get("sides", []) if s["numbers_say_bet"]),
                     key=lambda s: -s["value"])
    cap = pc.get("max_flagged", 12)
    for s in flagged[cap:]:
        s["numbers_say_bet"] = False
        s["trimmed"] = True
    if len(flagged) > cap:
        problems.append(f"{len(flagged)} sides cleared the numbers; only the top {cap} by value were sent for research.")

    return {"sport": sport, "built_utc": now.isoformat(),
            "settings": {"home_field": hfa, "market_weight": pc["market_weight"], "use_model_leg": use_model,
                         "public_systems_available": bool(public), "min_value": pc["min_value"],
                         "games_behind_ratings": hist.games_used, "games_not_posted_at_book": not_posted, "history_note": hist.note},
            "problems": problems, "games": games, "adjustments_used": adjustments}


def _news_time(a: dict) -> datetime | None:
    """When the news broke, from the entry's 'news_at' ('YYYY-MM-DD HH:MM MT'). 'added' is NOT used: an entry written
    today about news from last week would look fresh and be counted on top of a line that priced it days ago."""
    from zoneinfo import ZoneInfo
    raw = str(a.get("news_at") or "").replace(" MT", "").strip()
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("America/Denver")).astimezone(timezone.utc)
    except ValueError:
        return None


def pinnacle_history(sport: str) -> dict:
    """Every Pinnacle read our logger stored, per ESPN event id: [(ts_utc, home_spread, total)], oldest first."""
    import duckdb
    from engine.odds import snapshots
    try:
        con = snapshots.connect(config.DB, read_only=True)
    except duckdb.Error:
        return {}
    try:
        rows = con.execute("select event_id, ts_utc, home_spread, total from line_snapshots "
                           "where source='pinnacle' and sport=? order by ts_utc", [sport]).fetchall()
    except duckdb.Error:
        return {}
    finally:
        con.close()
    out: dict = {}
    for eid, ts, sp, tot in rows:
        out.setdefault(eid, []).append((ts.replace(tzinfo=timezone.utc), sp, tot))
    return out


def unpriced_part(a: dict, history_rows: list, now_spread, now_total, home_sign: int) -> tuple[float, str]:
    """How much of an entered adjustment is NOT yet in Pinnacle's number, as (points to apply, one-line status).

    Pinnacle's line already carries news the market has seen. Adding the agent's points on top counted the
    same injury twice (that produced the 'edge, then Pass' flags). So: compare Pinnacle's line now with its
    last line at or before the news. The share of the expected move that has already happened is 'priced'.
    No stored Pinnacle line from before the news means we cannot show the news is unpriced, so nothing is applied.
    """
    pts = float(a["points"])
    when = _news_time(a)
    if when is None:
        return 0.0, "not applied: no news_at time on the entry, so it cannot be shown unpriced"
    base = [r for r in history_rows if r[0] <= when]
    if not base:
        return 0.0, "not applied: no Pinnacle line stored from before the news, so it cannot be shown unpriced"
    if a["market"] == "spread":
        b0, now = base[-1][1], now_spread
        expected = -pts * home_sign      # change in the HOME spread if the market fully priced it
    else:
        b0, now = base[-1][2], now_total
        expected = pts
    if b0 is None or now is None or expected == 0:
        return 0.0, "not applied: no comparable Pinnacle number"
    done = max(0.0, min(1.0, (now - b0) / expected))
    left = pts * (1 - done)
    if done >= 0.999:
        return 0.0, f"priced: Pinnacle moved {now - b0:+g} since the news"
    if done == 0:
        return left, "unpriced: Pinnacle has not moved since the news"
    return left, f"partly priced: Pinnacle moved {now - b0:+g} of the {expected:+g} expected, {left:+g} points still applied"


def dk_first_seen(sport: str) -> dict:
    """First DraftKings number OUR logger saw for each game, keyed (event_id, market).

    ESPN's own 'open' for NFL is a lookahead line from the spring, so it is not used.
    The logger only started on 2026-11-21, so for a game already posted that day this is
    'first seen by us', not the true opener; the card says so.
    """
    import duckdb
    from engine.odds import snapshots
    try:
        con = snapshots.connect(config.DB, read_only=True)
    except duckdb.Error:
        return {}
    try:
        rows = con.execute(
            "select event_id, arg_min(home_spread, ts_utc), arg_min(total, ts_utc) from line_snapshots "
            "where source='draftkings' and sport=? group by event_id", [sport]).fetchall()
    except duckdb.Error:
        return {}
    finally:
        con.close()
    out = {}
    for eid, sp, tot in rows:
        out[(eid, "spread")], out[(eid, "total")] = sp, tot
    return out


def wind_adjustment(sport: str, e, now: datetime, wc: dict, problems: list[str]) -> dict | None:
    """The wind totals model (docs/decisions/0005): forecast wind at an open-air NFL stadium, turned into points."""
    if sport != "NFL" or not wc.get("enabled") or e.neutral:
        return None
    from engine.models import weather, wind_totals
    st = weather.HOME_STADIUM.get(e.home.get("abbreviation"))
    if st is None:
        return None
    try:
        fc = weather.forecast_at(st, e.start)
    except SourceError as ex:
        problems.append(f"Wind forecast unavailable for {e.away['displayName']} at {e.home['displayName']}: {ex}")
        return None
    lead = (e.start - now).total_seconds() / 3600
    wind = max(0.0, fc["wind_mph"] - float(wc.get("forecast_bias_mph", 0)))
    pts = float(wc.get("scale", 1.0)) * wind_totals.adjustment(wind, float(wc["slope"]), float(wc["knot"]))
    used = lead <= float(wc.get("max_lead_hours", 60)) and pts <= -float(wc.get("min_points", 1.0))
    return {"wind_mph": fc["wind_mph"], "temp_f": fc["temp_f"], "precip_mm": fc["precip_mm"], "points": round(pts, 2),
            "used": used, "hours_to_kickoff": round(lead, 1), "source": "Open-Meteo forecast"}


def build_nfl(now: datetime | None = None, days_ahead: int = 8) -> dict:
    return build("NFL", now, days_ahead)


def save(sheet: dict) -> Path:
    d = config.DATA / "slates"
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromisoformat(sheet["built_utc"]).strftime("%Y-%m-%d_%H%M")
    p = d / f"{sheet['sport']}_{stamp}.json"
    p.write_text(json.dumps(sheet, indent=1))
    (d / f"{sheet['sport']}_latest.json").write_text(json.dumps(sheet, indent=1))
    return p
