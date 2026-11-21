"""Line snapshots: collect from Wagerhouse and ESPN, store, and read back."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb

from engine.odds import espn
from engine.odds.wagerhouse import BookLine, Wagerhouse

SCHEMA = """
CREATE TABLE IF NOT EXISTS line_snapshots (
  ts_utc TIMESTAMP, source VARCHAR, sport VARCHAR, event_id VARCHAR, away VARCHAR, home VARCHAR,
  start_utc TIMESTAMP, home_spread DOUBLE, home_spread_price DOUBLE, away_spread_price DOUBLE,
  home_ml DOUBLE, away_ml DOUBLE, total DOUBLE, over_price DOUBLE, under_price DOUBLE);
CREATE TABLE IF NOT EXISTS polls (ts_utc TIMESTAMP, ok BOOLEAN, wagerhouse_games INTEGER, market_games INTEGER, error VARCHAR);
CREATE TABLE IF NOT EXISTS alerts_sent (key VARCHAR PRIMARY KEY, ts_utc TIMESTAMP, kind VARCHAR, text VARCHAR, delivered BOOLEAN);
CREATE TABLE IF NOT EXISTS watchlist (
  id INTEGER PRIMARY KEY, created_utc TIMESTAMP, team VARCHAR, market VARCHAR, target DOUBLE,
  worst_price DOUBLE, note VARCHAR, active BOOLEAN);
CREATE TABLE IF NOT EXISTS manual_bets (
  created_utc TIMESTAMP, raw VARCHAR, team VARCHAR, market VARCHAR, line DOUBLE, price DOUBLE, stake DOUBLE, note VARCHAR);
"""
WH, MKT = "wagerhouse", "draftkings"
LOOKAHEAD_DAYS = {"NFL": 8, "College": 8, "NBA": 2}


def connect(db: Path) -> duckdb.DuckDBPyConnection:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    con.execute(SCHEMA)
    return con


@dataclass
class Snap:
    ts: datetime
    source: str
    sport: str
    event_id: str
    away: str
    home: str
    start: datetime
    home_spread: float | None
    home_spread_price: float | None
    away_spread_price: float | None
    home_ml: float | None
    away_ml: float | None
    total: float | None
    over_price: float | None
    under_price: float | None

    def row(self):
        n = lambda d: d.replace(tzinfo=None) if d else None
        return (n(self.ts), self.source, self.sport, self.event_id, self.away, self.home, n(self.start),
                self.home_spread, self.home_spread_price, self.away_spread_price, self.home_ml, self.away_ml,
                self.total, self.over_price, self.under_price)


def match_event(line: BookLine, events: list[espn.Event]) -> espn.Event | None:
    near = [e for e in events if line.start and abs((e.start - line.start).total_seconds()) < 12 * 3600]
    ev, how = espn.find_event(near, line.away, line.home)
    return ev if how == "both teams" else None


def collect(wh: Wagerhouse, sports: list[str], now: datetime) -> tuple[list[Snap], list[str]]:
    """One read of Wagerhouse and the market for every sport. Returns snapshots and problems."""
    snaps: list[Snap] = []
    problems: list[str] = []
    for sport in sports:
        lines = [l for l in wh.lines(sport) if l.start and l.start > now]
        if not lines:
            continue
        today = now.date()
        events = espn.upcoming(sport, today - timedelta(days=1), today + timedelta(days=LOOKAHEAD_DAYS[sport]))
        for l in lines:
            ev = match_event(l, events)
            if ev is None:
                problems.append(f"{sport}: could not match {l.away} at {l.home} to an ESPN game")
                continue
            snaps.append(Snap(now, WH, sport, ev.event_id, l.away, l.home, ev.start, l.home_spread,
                              l.home_spread_price, l.away_spread_price, l.home_ml, l.away_ml, l.total,
                              l.over_price, l.under_price))
            odds = espn.event_odds(ev, None)
            c = odds.current if odds else None
            if c is None or (c.home_spread is None and c.total is None and c.home_ml is None):
                continue  # market has not posted this game yet
            snaps.append(Snap(now, MKT, sport, ev.event_id, l.away, l.home, ev.start, c.home_spread,
                              c.home_spread_price, c.away_spread_price, c.home_ml, c.away_ml, c.total,
                              c.over_price, c.under_price))
    return snaps, problems


def save(con, snaps: list[Snap]) -> None:
    if snaps:
        con.executemany("INSERT INTO line_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [s.row() for s in snaps])


COLS = ("ts_utc, source, sport, event_id, away, home, start_utc, home_spread, home_spread_price, "
        "away_spread_price, home_ml, away_ml, total, over_price, under_price")


def _snap(r) -> Snap:
    u = lambda d: d.replace(tzinfo=timezone.utc) if d else None
    return Snap(u(r[0]), r[1], r[2], r[3], r[4], r[5], u(r[6]), *r[7:])


def history(con, event_id: str, source: str, before: datetime | None = None) -> list[Snap]:
    q = f"SELECT {COLS} FROM line_snapshots WHERE event_id=? AND source=?"
    args = [event_id, source]
    if before:
        q += " AND ts_utc < ?"
        args.append(before.replace(tzinfo=None))
    return [_snap(r) for r in con.execute(q + " ORDER BY ts_utc", args).fetchall()]


def last_ok_poll(con) -> datetime | None:
    r = con.execute("SELECT max(ts_utc) FROM polls WHERE ok").fetchone()[0]
    return r.replace(tzinfo=timezone.utc) if r else None
