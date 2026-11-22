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
    if no_public:
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
        auto = []
        for tid in b2b.get(e.event_id, set()):
            team = home if tid == str(e.home["id"]) else away
            auto.append({"game": g["game"], "team": team, "market": "spread", "points": pc["nba_back_to_back"],
                         "reason": "Second night of a back-to-back (from the schedule).", "source": "schedule", "added": "automatic"})
        g["adjustments"] += auto

        # ---- spread (all numbers are the HOME spread; negative = home favored)
        game_hfa = 0.0 if e.neutral else hfa
        if e.neutral:
            g["notes"].append("Neutral site: no home-field points.")
        rating_line = -(hist.spread_rating[hk] - hist.spread_rating[ak] + game_hfa) if rated else None
        public_line = -t["avg_home_margin"] if t else None
        adj_pts = 0.0
        for a in my_adj + auto:
            if a["market"] == "spread":      # points are a change to that team's strength
                adj_pts += float(a["points"]) * (1 if espn.norm(a["team"]) in _names(e.home) else -1)
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
            fair = pc["market_weight"] * sharp_fair + (1 - pc["market_weight"]) * model
            m.update(pinnacle_line=s.home_spread, pinnacle_home_price=s.home_spread_price,
                     pinnacle_away_price=s.away_spread_price, pinnacle_fair=round(sharp_fair, 2), fair_line=round(fair, 2))
        if dkc and dkc.home_spread is not None:
            m["draftkings_line"], m["draftkings_open"] = dkc.home_spread, dk.open.home_spread
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
                              "numbers_say_bet": bool(is_bet and model_edge > 0),
                              "dont_bet_past": None if lim is None else f"{team} {show(lim):+g}", "limit_line": lim,
                              "model_agrees": model_edge > 0})
            m["sides"] = sides
        g["markets"].append(m)

        # ---- total
        rating_total = (hist.avg_total + hist.total_tendency[hk] + hist.total_tendency[ak]) if rated and hist.avg_total is not None else None
        adj_t = sum(float(a["points"]) for a in my_adj if a["market"] == "total")
        model_t = None if rating_total is None else rating_total + adj_t
        mt = {"market": "total", "rating_line": None if rating_total is None else round(rating_total, 2),
              "adjustment_points": adj_t, "model_line": None if model_t is None else round(model_t, 2), "fair_line": None}
        fair_t = None
        if s and s.total is not None and s.over_price and s.under_price and model_t is not None:
            p_over = no_vig(s.over_price, s.under_price)[0]
            sharp_t = land_total.fair_from_price(s.total, p_over)
            fair_t = pc["market_weight"] * sharp_t + (1 - pc["market_weight"]) * model_t
            mt.update(pinnacle_line=s.total, pinnacle_fair=round(sharp_t, 2), fair_line=round(fair_t, 2))
        if dkc and dkc.total is not None:
            mt["draftkings_line"], mt["draftkings_open"] = dkc.total, dk.open.total
        if b.total is not None:
            mt["book_line"] = b.total
        if b.total is not None and fair_t is not None:
            sides = []
            for side, price in (("over", b.over_price), ("under", b.under_price)):
                if price is None:
                    continue
                val = land_total.value(fair_t, b.total, side, price)
                is_bet, lim = land_total.limit(fair_t, b.total, side, price, pc["min_value"])
                win, push, _ = land_total.probs(fair_t, b.total, side)
                sign = 1 if side == "over" else -1
                model_edge = (model_t - b.total) * sign
                sides.append({"side": side, "pick": f"{side.title()} {b.total:g}", "price": price, "value": round(val, 4),
                              "edge_points": round((fair_t - b.total) * sign, 2), "win": round(win, 3), "push": round(push, 3),
                              # no real totals model yet: a total needs a specific sourced adjustment (wind, QB, a star out)
                              "numbers_say_bet": bool(is_bet and model_edge > 0 and adj_t != 0),
                              "dont_bet_past": None if lim is None else f"{side.title()} {lim:g}", "limit_line": lim,
                              "model_agrees": model_edge > 0})
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
            "settings": {"home_field": hfa, "market_weight": pc["market_weight"], "min_value": pc["min_value"],
                         "games_behind_ratings": hist.games_used, "games_not_posted_at_book": not_posted, "history_note": hist.note},
            "problems": problems, "games": games, "adjustments_used": adjustments}


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
