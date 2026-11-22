"""Log period lines, team totals and player props (plan item 2, docs/research/04-evaluation.md).

Nothing here drives a pick. It records Wagerhouse and Pinnacle numbers for the markets the engine
does not price yet, so they can be measured against each other before any model touches them.
Each row: when, source, sport, game, market, period, description, line, two prices.
"""
from __future__ import annotations

import json
import time
from datetime import datetime

from engine.odds.espn import SourceError
from engine.picks.sources import PINNACLE_LEAGUES, _fetch

SCHEMA = """
CREATE TABLE IF NOT EXISTS derivative_snapshots (
  ts_utc TIMESTAMP, source VARCHAR, sport VARCHAR, away VARCHAR, home VARCHAR, start_utc VARCHAR,
  market VARCHAR, period VARCHAR, description VARCHAR, line DOUBLE, price_a DOUBLE, price_b DOUBLE);
"""
PERIODS = {0: "Game", 1: "1st Half", 3: "1st Quarter"}


def pinnacle_rows(sport: str) -> list[tuple]:
    base = f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{PINNACLE_LEAGUES[sport]}"
    try:
        matchups = json.loads(_fetch(base + "/matchups", "Pinnacle"))
        markets = json.loads(_fetch(base + "/markets/straight", "Pinnacle"))
    except json.JSONDecodeError:
        raise SourceError("Pinnacle returned something that is not JSON") from None
    if not isinstance(matchups, list) or not isinstance(markets, list):
        raise SourceError("Pinnacle returned an unexpected shape")
    games, specials = {}, {}
    for m in matchups:
        if m.get("isLive"):
            continue
        if m.get("type") == "matchup" and not m.get("parent"):
            p = {x.get("alignment"): x.get("name") for x in m.get("participants", [])}
            if "home" in p and "away" in p:
                games[m["id"]] = (p["away"], p["home"], m.get("startTime", ""))
        elif m.get("type") == "special" and m.get("parentId"):
            specials[m["id"]] = m
    rows: list[tuple] = []
    for k in markets:
        if k.get("isAlternate") or k.get("status", "open") != "open":
            continue
        mid, per = k.get("matchupId"), k.get("period")
        pr = k.get("prices", [])
        if mid in games:
            away, home, start = games[mid]
            if k["type"] in ("spread", "total") and per in (1, 3) and len(pr) == 2:
                by = {p.get("designation"): p for p in pr}
                a, b = (by.get("home"), by.get("away")) if k["type"] == "spread" else (by.get("over"), by.get("under"))
                if a and b:
                    rows.append((sport, away, home, start, k["type"], PERIODS[per], "", a["points"], a["price"], b["price"]))
            elif k["type"] == "team_total" and per in (0, 1, 3):
                by = {p.get("designation"): p for p in pr}
                if "over" in by and "under" in by:
                    rows.append((sport, away, home, start, "team_total", PERIODS[per], k.get("side", ""),
                                 by["over"]["points"], by["over"]["price"], by["under"]["price"]))
        elif mid in specials and k["type"] == "total" and len(pr) == 2:
            s = specials[mid]
            parent = games.get(s["parentId"])
            if parent is None:
                continue
            ids = {x["id"]: x["name"] for x in s.get("participants", [])}
            by = {ids.get(p["participantId"]): p for p in pr}
            if "Over" in by and "Under" in by:
                rows.append((sport, parent[0], parent[1], parent[2], "prop", "Game",
                             (s.get("special") or {}).get("description", ""), by["Over"]["points"],
                             by["Over"]["price"], by["Under"]["price"]))
    return rows


def wagerhouse_rows(wh, sport: str, pause: float = 1.5) -> list[tuple]:
    """First half, first quarter, and team totals from Wagerhouse. Spread rows are home-side prices."""
    from engine.odds.wagerhouse import normalize_line
    rows: list[tuple] = []
    seen_tt: set = set()
    for period in ("Game", "1st Half", "1st Quarter"):
        raw = wh.raw_lines(sport, period)
        time.sleep(pause)
        for r in raw:
            label = (r.get("PeriodDescription") or "Game").strip()
            if label != period:
                continue
            b = normalize_line(sport, r)
            start = b.start.isoformat() if b.start else ""
            if period != "Game":
                if b.home_spread is not None:
                    rows.append((sport, b.away, b.home, start, "spread", period, "", b.home_spread,
                                 b.home_spread_price, b.away_spread_price))
                if b.total is not None:
                    rows.append((sport, b.away, b.home, start, "total", period, "", b.total, b.over_price, b.under_price))
            else:
                for side, tag in (("home", "2"), ("away", "1")):
                    pts, o, u = r.get(f"Team{tag}TotalPoints"), r.get(f"Team{tag}TtlPtsAdj1"), r.get(f"Team{tag}TtlPtsAdj2")
                    key = (b.away, b.home, side)
                    if pts is not None and key not in seen_tt:
                        seen_tt.add(key)
                        rows.append((sport, b.away, b.home, start, "team_total", "Game", side, float(pts),
                                     float(o) if o is not None else None, float(u) if u is not None else None))
    return rows


def collect(wh, sports: list[str], now: datetime) -> tuple[list[tuple], list[str]]:
    """All rows for this read, plus a plain message for each source that failed (never silent)."""
    out: list[tuple] = []
    problems: list[str] = []
    ts = now.replace(tzinfo=None)
    for sport in sports:
        for name, fn in (("Wagerhouse", lambda s=sport: wagerhouse_rows(wh, s)), ("Pinnacle", lambda s=sport: pinnacle_rows(s))):
            try:
                out += [(ts, name, *r) for r in fn()]
            except SourceError as e:
                problems.append(f"{name} {sport} period/team-total/prop read: {e}")
    return out, problems


def save(con, rows: list[tuple]) -> None:
    con.execute(SCHEMA)
    if rows:
        con.executemany("INSERT INTO derivative_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
