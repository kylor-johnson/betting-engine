"""Save wagers, legs and closing-line comparisons to the local database."""
from __future__ import annotations

from pathlib import Path

import duckdb

from engine.bets.audit import Priced
from engine.bets.history import Wager, category

SCHEMA = """
CREATE OR REPLACE TABLE wagers (
  wager_key VARCHAR PRIMARY KEY, ticket BIGINT, type_code VARCHAR, channel VARCHAR, category VARCHAR,
  accepted_utc TIMESTAMP, risk DOUBLE, to_win DOUBLE, net DOUBLE, status VARCHAR, free_play BOOLEAN,
  teaser_name VARCHAR, description VARCHAR, source VARCHAR);
CREATE OR REPLACE TABLE legs (
  wager_key VARCHAR, item INTEGER, kind VARCHAR, sport VARCHAR, team1 VARCHAR, team2 VARCHAR, chosen VARCHAR,
  line DOUBLE, orig_line DOUBLE, buy_points DOUBLE, teaser_points DOUBLE, over_under VARCHAR, price INTEGER,
  game_time_utc TIMESTAMP, outcome VARCHAR, period VARCHAR,
  priced BOOLEAN, unpriced_reason VARCHAR, ref_book VARCHAR, close_line DOUBLE, open_line DOUBLE, close_price DOUBLE,
  pts_vs_close DOUBLE, pts_vs_open DOUBLE, fair_prob DOUBLE, ev_per_dollar DOUBLE);
"""


def _naive(dt):
    return dt.replace(tzinfo=None) if dt else None


def save_audit(db: Path, wagers: list[Wager], priced: list[Priced]) -> None:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    try:
        con.execute(SCHEMA)
        con.executemany(
            "INSERT INTO wagers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(w.key, w.ticket, w.type_code, w.channel, category(w), _naive(w.accepted), w.risk, w.to_win, w.net,
              w.status, w.free_play, w.teaser_name, w.description, "wagerhouse") for w in wagers])
        con.executemany(
            "INSERT INTO legs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(p.wager.key, l.item, l.kind, l.sport, l.team1, l.team2, l.chosen, l.line, l.orig_line, l.buy_points,
              l.teaser_points, l.over_under, l.price, _naive(l.game_time), l.outcome, l.period, p.ok, p.reason,
              "DraftKings via ESPN" if p.ok else None, p.close_line, p.open_line, p.close_price, p.pts_vs_close,
              p.pts_vs_open, p.fair_prob, p.ev) for p in priced for l in [p.leg]])
    finally:
        con.close()
