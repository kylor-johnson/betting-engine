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
from engine.picks import ratings, sources
from engine.picks.pricing import Landing

NFLVERSE_ABBR = {"LA": "LAR", "WAS": "WSH"}
TRACKER_NAMES = {"n.y. giants": "new york giants", "n.y. jets": "new york jets", "ny giants": "new york giants",
                 "ny jets": "new york jets", "l.a. rams": "los angeles rams", "l.a. chargers": "los angeles chargers",
                 "la rams": "los angeles rams", "la chargers": "los angeles chargers"}
ADJ_FILE = config.ROOT / "adjustments.yaml"


def load_adjustments(now: datetime) -> list[dict]:
    if not ADJ_FILE.exists():
        return []
    data = yaml.safe_load(ADJ_FILE.read_text()) or {}
    out = []
    for a in data.get("adjustments", []) or []:
        for k in ("game", "team", "market", "points", "reason", "source", "added"):
            if k not in a:
                raise SourceError(f"adjustments.yaml entry is missing '{k}': {a}")
        if a["market"] not in ("spread", "total"):
            raise SourceError(f"adjustments.yaml market must be spread or total: {a}")
        if not str(a["source"]).startswith("http"):
            raise SourceError(f"adjustments.yaml entry needs a source link: {a}")
        out.append(a)
    return out


def _team_key(ev_team: dict) -> set[str]:
    return espn.team_names(ev_team)


def _find(events, name_a: str, name_b: str | None = None):
    a = espn.norm(TRACKER_NAMES.get(name_a.lower(), name_a))
    b = espn.norm(TRACKER_NAMES.get(name_b.lower(), name_b)) if name_b else None
    hits = []
    for e in events:
        names = _team_key(e.home) | _team_key(e.away)
        if a in names and (b is None or b in names):
            hits.append(e)
    return hits[0] if len(hits) == 1 else None


def build_nfl(now: datetime | None = None, days_ahead: int = 3) -> dict:
    cfg, env = config.load_config(), config.load_env()
    pc = cfg["picks"]
    now = now or datetime.now(timezone.utc)
    hfa = pc["home_field"]["NFL"]
    problems: list[str] = []

    events = [e for e in espn.upcoming("NFL", now.date(), now.date() + timedelta(days=days_ahead)) if e.start > now]
    if not events:
        raise SourceError("ESPN lists no upcoming NFL games in the window")

    # history: ratings and landing tables
    rows = sources.nfl_games(config.DATA / "raw" / "nflverse_games.csv")
    season = max(int(r["season"]) for r in rows if r["spread_line"] not in ("", None))
    today = now.astimezone(config.display_tz(cfg)).strftime("%Y-%m-%d")
    # only games already played: their lines are true closing lines, and this week's news is not in them
    played = [r for r in rows if r["result"] not in ("", None)]
    spread_r, total_t, avg_total, n_rated = ratings.market_ratings(played, season, "9999-12-31", hfa)
    hist = [r for r in rows if int(r["season"]) >= 2015 and r["result"] not in ("", None) and r["spread_line"] not in ("", None)]
    land_spread = Landing([(-float(r["spread_line"]), float(r["result"])) for r in hist], "spread", window=1.0)
    land_total = Landing([(float(r["total_line"]), float(r["total"])) for r in hist if r["total_line"] not in ("", None)], "total", window=3.0)

    wh = Wagerhouse(env.get("WAGERHOUSE_USER", ""), env.get("WAGERHOUSE_PASSWORD", ""))
    book = {}
    for l in wh.lines("NFL"):
        e = _find(events, l.home, l.away)
        if e:
            book[e.event_id] = l
    sharp = {}
    for s in sources.pinnacle("NFL"):
        e = _find(events, s.home, s.away)
        if e and abs((e.start - s.start).total_seconds()) < 12 * 3600:
            sharp[e.event_id] = s
    public = {}
    for t in sources.tracker("NFL", config.DATA / "raw" / "tracker"):
        e = _find(events, t["home"], t["road"])
        if e:
            public[e.event_id] = t
    for e in events:
        if e.event_id not in public:
            problems.append(f"No public-systems number for {e.away['displayName']} at {e.home['displayName']}; the model used market ratings alone.")
        if e.event_id not in sharp:
            problems.append(f"No Pinnacle price for {e.away['displayName']} at {e.home['displayName']}.")
        if e.event_id not in book:
            problems.append(f"Wagerhouse has not posted {e.away['displayName']} at {e.home['displayName']}.")
    adjustments = load_adjustments(now)
    abbr = lambda team: NFLVERSE_ABBR_INV.get(team["abbreviation"], team["abbreviation"])

    games = []
    for e in sorted(events, key=lambda e: e.start):
        home, away = e.home["displayName"], e.away["displayName"]
        g = {"event_id": e.event_id, "game": f"{away} at {home}", "home": home, "away": away,
             "start_utc": e.start.isoformat(), "markets": [], "notes": [],
             "adjustments": []}
        b, s, t = book.get(e.event_id), sharp.get(e.event_id), public.get(e.event_id)
        dk = espn.event_odds(e, None)
        dkc = dk.current if dk else None
        ha, aa = abbr(e.home), abbr(e.away)
        if ha not in spread_r or aa not in spread_r:
            raise SourceError(f"no market rating for {ha} or {aa}")
        my_adj = [a for a in adjustments if espn.norm(a["game"]) == espn.norm(g["game"])]
        g["adjustments"] = my_adj

        # ---- spread (all numbers are the HOME spread; negative = home favored)
        game_hfa = 0.0 if e.neutral else hfa
        if e.neutral:
            g["notes"].append("Neutral site: no home-field points.")
        rating_line = -(spread_r[ha] - spread_r[aa] + game_hfa)
        public_line = -t["avg_home_margin"] if t else None
        adj_pts = 0.0
        for a in my_adj:
            if a["market"] == "spread":      # points are a change to that team's strength
                adj_pts += float(a["points"]) * (1 if espn.norm(a["team"]) in _team_key(e.home) else -1)
        model_parts = [x for x in (rating_line, public_line) if x is not None]
        model = sum(model_parts) / len(model_parts) - adj_pts
        m = {"market": "spread", "rating_line": round(rating_line, 2), "public_systems_line": None if public_line is None else round(public_line, 2),
             "public_systems_count": t["systems"] if t else 0, "public_disagreement": round(t["spread_of_opinion"], 1) if t else None,
             "adjustment_points": adj_pts, "model_line": round(model, 2)}
        if s and s.home_spread is not None and s.home_spread_price and s.away_spread_price:
            p_home = no_vig(s.home_spread_price, s.away_spread_price)[0]
            sharp_fair = land_spread.fair_from_price(s.home_spread, p_home)
            m.update(pinnacle_line=s.home_spread, pinnacle_home_price=s.home_spread_price, pinnacle_away_price=s.away_spread_price,
                     pinnacle_fair=round(sharp_fair, 2))
            fair = pc["market_weight"] * sharp_fair + (1 - pc["market_weight"]) * model
        else:
            sharp_fair, fair = None, None
            g["notes"].append("No Pinnacle spread: no fair line, no pick possible on the side.")
        m["fair_line"] = None if fair is None else round(fair, 2)
        if dkc and dkc.home_spread is not None:
            m["draftkings_line"] = dkc.home_spread
            m["draftkings_open"] = dk.open.home_spread
        if b and b.home_spread is not None and fair is not None:
            m["book_line"] = b.home_spread
            sides = []
            for side, price in (("home", b.home_spread_price), ("away", b.away_spread_price)):
                if price is None:
                    continue
                val = land_spread.value(fair, b.home_spread, side, price)
                is_bet, lim = land_spread.limit(fair, b.home_spread, side, price, pc["min_value"])
                win, push, lose = land_spread.probs(fair, b.home_spread, side)
                team = home if side == "home" else away
                show = lambda hs, sd=side: hs if sd == "home" else -hs
                edge_pts = (b.home_spread - fair) * (1 if side == "home" else -1)
                model_edge = (b.home_spread - model) * (1 if side == "home" else -1)
                sides.append({"side": side, "pick": f"{team} {show(b.home_spread):+g}", "price": price, "value": round(val, 4),
                              "edge_points": round(edge_pts, 2), "win": round(win, 3), "push": round(push, 3),
                              "numbers_say_bet": bool(is_bet and model_edge > 0),
                              "dont_bet_past": None if lim is None else f"{team} {show(lim):+g}", "limit_line": lim,
                              "model_agrees": model_edge > 0})
            m["sides"] = sides
        elif fair is not None:
            g["notes"].append("Wagerhouse has no spread posted.")
        g["markets"].append(m)

        # ---- total
        rating_total = avg_total + total_t[ha] + total_t[aa]
        adj_t = sum(float(a["points"]) for a in my_adj if a["market"] == "total")
        model_t = rating_total + adj_t
        mt = {"market": "total", "rating_line": round(rating_total, 2), "adjustment_points": adj_t, "model_line": round(model_t, 2)}
        if s and s.total is not None and s.over_price and s.under_price:
            p_over = no_vig(s.over_price, s.under_price)[0]
            sharp_t = land_total.fair_from_price(s.total, p_over)
            fair_t = pc["market_weight"] * sharp_t + (1 - pc["market_weight"]) * model_t
            mt.update(pinnacle_line=s.total, pinnacle_fair=round(sharp_t, 2), fair_line=round(fair_t, 2))
        else:
            fair_t = None
            mt["fair_line"] = None
        if dkc and dkc.total is not None:
            mt["draftkings_line"], mt["draftkings_open"] = dkc.total, dk.open.total
        if b and b.total is not None and fair_t is not None:
            mt["book_line"] = b.total
            sides = []
            for side, price in (("over", b.over_price), ("under", b.under_price)):
                if price is None:
                    continue
                val = land_total.value(fair_t, b.total, side, price)
                is_bet, lim = land_total.limit(fair_t, b.total, side, price, pc["min_value"])
                win, push, _ = land_total.probs(fair_t, b.total, side)
                edge_pts = (fair_t - b.total) * (1 if side == "over" else -1)
                model_edge = (model_t - b.total) * (1 if side == "over" else -1)
                sides.append({"side": side, "pick": f"{side.title()} {b.total:g}", "price": price, "value": round(val, 4),
                              "edge_points": round(edge_pts, 2), "win": round(win, 3), "push": round(push, 3),
                              # v1 has no real totals model: a total needs a specific sourced adjustment (wind, QB)
                              "numbers_say_bet": bool(is_bet and model_edge > 0 and adj_t != 0),
                              "dont_bet_past": None if lim is None else f"{side.title()} {lim:g}", "limit_line": lim,
                              "model_agrees": model_edge > 0})
            mt["sides"] = sides
        g["markets"].append(mt)
        games.append(g)

    return {"sport": "NFL", "built_utc": now.isoformat(), "settings": {"home_field": hfa, "market_weight": pc["market_weight"],
            "min_value": pc["min_value"], "games_behind_ratings": n_rated}, "problems": problems, "games": games,
            "adjustments_used": adjustments}


NFLVERSE_ABBR_INV = {v: k for k, v in NFLVERSE_ABBR.items()}


def save(sheet: dict) -> Path:
    d = config.DATA / "slates"
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromisoformat(sheet["built_utc"]).strftime("%Y-%m-%d_%H%M")
    p = d / f"{sheet['sport']}_{stamp}.json"
    p.write_text(json.dumps(sheet, indent=1))
    (d / f"{sheet['sport']}_latest.json").write_text(json.dumps(sheet, indent=1))
    return p
