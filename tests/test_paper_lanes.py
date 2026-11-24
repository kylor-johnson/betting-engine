"""Decision 0036, item 13: the three paper lanes (src/engine/picks/paper_lanes.py)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import duckdb
import pytest

from engine.picks import paper_lanes as pl

ST = pl.settings({"models": {"paper_lanes": {"enabled": True}}})
NOW = datetime(2030, 1, 7, 1, 0, tzinfo=timezone.utc)      # Sunday Jan 6, 6pm Mountain


def _snap(eid="e1", hs=-3.0, tot=44.0, hsp=-110, asp=-110, op=-110, up=-110, ts=None):
    return (eid, ts or NOW.replace(tzinfo=None), "Away", "Home", datetime(2030, 1, 7, 18), hs, hsp, asp, tot, op, up)


def test_l1_needs_a_full_point_or_half_through_a_key_number():
    assert pl.l1_picks(_snap(hs=-2.5), _snap(hs=-3.5), "NBA", ST)[0]["side"] == "home"           # home gets a point more at Wagerhouse
    assert not pl.l1_picks(_snap(hs=-4.5), _snap(hs=-5.0), "NBA", ST)                            # half a point, no key: nothing
    nfl = pl.l1_picks(_snap(hs=-2.5), _snap(hs=-3.0), "NFL", ST)                                 # half a point through 3
    assert nfl and nfl[0]["side"] == "home" and nfl[0]["key"].startswith("L1|NFL|e1|spread")
    tot = [p for p in pl.l1_picks(_snap(tot=45.5), _snap(tot=44.0), "College", ST) if p["market"] == "total"]
    assert tot and tot[0]["side"] == "under" and tot[0]["line"] == 45.5


def test_f1_side_and_window():
    assert pl.f1_pick(5.0, -3.0, 1.5) == "home"       # ratings home by 5, Wagerhouse home by 3: the home side
    assert pl.f1_pick(1.0, -3.0, 1.5) == "away"
    assert pl.f1_pick(3.5, -3.0, 1.5) is None
    cfg = {"timezone_display": "America/Denver"}
    assert pl.f1_window(cfg, NOW)                                       # Sunday 6pm MT
    assert pl.f1_window(cfg, NOW + timedelta(days=1))                   # Monday
    assert not pl.f1_window(cfg, NOW + timedelta(days=1, hours=19))     # Tuesday 1pm


def test_d1b_moves_pinnacles_line_by_our_disagreement_only():
    w = {"side": 0.25, "total": 0.35, "team_total": 0.4}
    derivs = [("total", "1st Half", "", 22.5, -110, -110), ("spread", "1st Half", "", -1.5, -110, -110),
              ("team_total", "Game", "home", 24.5, -110, -110)]
    same = pl.d1b_picks("Away at Home", "e1", None, {"total": (45.0, 45.0), "side": (3.0, 3.0), "tt_home": (24.0, 24.0)}, derivs, w, 0.04)
    assert same == []                                                   # we agree with the market: no picks, whatever the rule of thumb says
    far = pl.d1b_picks("Away at Home", "e1", None, {"total": (55.0, 45.0)}, derivs, w, 0.04)
    assert far and far[0]["side"] == "over" and far[0]["ours"] == pytest.approx(22.5 + 0.47 * 0.35 * 10)


def test_chance_and_fair_mean():
    assert pl.chance(44.0, 44.5, 10.0, "over", "total") == pytest.approx(1 - pl.NormalDist(44, 10).cdf(44.5))
    assert pl.chance(0.0, 0.0, 10.0, "home", "spread") == pytest.approx(0.5)
    assert pl.fair_mean(44.5, -110, -110, 9.0, "total") == pytest.approx(44.5)
    assert pl.fair_mean(-3.0, -130, 110, 9.0, "spread") > 3.0           # home at -130 on -3: a margin above 3


def _con():
    con = duckdb.connect()
    con.execute(pl.SCHEMA)
    con.execute("CREATE TABLE line_snapshots (ts_utc TIMESTAMP, source VARCHAR, sport VARCHAR, event_id VARCHAR, away VARCHAR, home VARCHAR, "
                "start_utc TIMESTAMP, home_spread DOUBLE, home_spread_price DOUBLE, away_spread_price DOUBLE, home_ml DOUBLE, away_ml DOUBLE, "
                "total DOUBLE, over_price DOUBLE, under_price DOUBLE)")
    con.execute("CREATE TABLE derivative_snapshots (ts_utc TIMESTAMP, source VARCHAR, sport VARCHAR, away VARCHAR, home VARCHAR, start_utc VARCHAR, "
                "market VARCHAR, period VARCHAR, description VARCHAR, line DOUBLE, price_a DOUBLE, price_b DOUBLE)")
    return con


def test_grade_first_half_total_with_closing_value():
    con = _con()
    kick = datetime(2020, 1, 5, 18)
    pl._freeze(con, {"key": "D1b|NFL|e|total|1st Half||over", "lane": "D1b", "sport": "NFL", "event_id": "e", "game": "A at H",
                     "market": "total", "period": "1st Half", "side": "over", "line": 21.5, "price": -110, "kick": kick}, NOW)
    from engine.odds import snapshots as snap
    con.execute("INSERT INTO derivative_snapshots VALUES (?, 'Pinnacle', 'NFL', 'A', 'H', '', 'total', '1st Half', '', 22.5, -110, -110)",
                [kick - timedelta(hours=1)])
    pl.grade(con, {}, NOW, scorer=lambda s, e: (14, 10, 27, 20))
    res, clv = con.execute("SELECT result, clv FROM paper_lane_grades").fetchone()
    assert res == "W" and clv > 0                                       # 24 first-half points over 21.5; the close went to 22.5


def test_grade_l1_spread_uses_landing_tables():
    from engine import config
    con = _con()
    kick = datetime(2020, 1, 5, 18)
    pl._freeze(con, {"key": "L1|NBA|e|spread|home", "lane": "L1", "sport": "NBA", "event_id": "e", "game": "A at H", "market": "spread",
                     "period": "Game", "side": "home", "line": -2.5, "price": -110, "kick": kick}, NOW)
    from engine.odds import snapshots as snap
    con.execute("INSERT INTO line_snapshots (ts_utc, source, sport, event_id, home_spread, home_spread_price, away_spread_price) VALUES "
                "(?, ?, 'NBA', 'e', -4.0, -110, -110)", [kick - timedelta(hours=1), snap.SHARP])
    pl.grade(con, config.load_config(), NOW, scorer=lambda s, e: (50, 50, 110, 100))
    res, clv = con.execute("SELECT result, clv FROM paper_lane_grades").fetchone()
    assert res == "W" and clv > 0                                       # got -2.5, the close was -4


def test_report_and_run_never_send(monkeypatch):
    from engine.alerts import telegram
    monkeypatch.setattr(telegram, "send", lambda *a, **k: pytest.fail("a paper lane sent something"))
    monkeypatch.setattr(pl, "REPORT", __import__("pathlib").Path("/dev/null"))
    con = _con()
    con.execute("CREATE TABLE playbook_candidates (cand_key VARCHAR, first_seen_utc TIMESTAMP, sport VARCHAR, event_id VARCHAR, market VARCHAR, "
                "side VARCHAR, line DOUBLE, price DOUBLE, grade VARCHAR, edge DOUBLE, own_value DOUBLE, market_value DOUBLE, kickoff_utc TIMESTAMP, "
                "game VARCHAR, outcome DOUBLE, graded_utc TIMESTAMP)")
    cfg = {"models": {"paper_lanes": {"enabled": True, "f1": False}}, "timezone_display": "America/Denver",
           "playbook": {}}
    out = pl.run(con, cfg, NOW)
    assert not [o for o in out if "failed" in o]
    assert "Paper lanes" in pl.report(con, cfg, NOW)
