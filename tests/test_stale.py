from datetime import datetime, timedelta, timezone

import duckdb

from engine import stale
from engine.odds import snapshots as snap
from engine.picks.pricing import Landing, bell_rows

NOW = datetime(2026, 11, 23, 20, 0, tzinfo=timezone.utc)
CFG = {"timezone_display": "America/Denver", "picks": {"min_value": 0.02}, "margin_sd": {"NBA": {"spread": 12.0, "total": 18.0}}}
LANDS = (Landing(bell_rows("spread", 12.0, -25, 25), "spread", window=0.25, min_n=100),
         Landing(bell_rows("total", 18.0, 180, 270), "total", window=0.25, min_n=100))


def S(source, hs, total=220.0, hp=-110, ap=-110, eid="E1"):
    return snap.Snap(NOW, source, "NBA", eid, "Away", "Home", NOW + timedelta(hours=5), hs, hp, ap, None, None, total, -110, -110)


def test_a_two_point_gap_on_the_home_side_alerts_and_names_a_limit():
    out = stale.evaluate(S(snap.WH, -3.0), S(snap.SHARP, -5.0), LANDS, 0.02, 3.0)
    assert [c["side"] for c in out] == ["home"] and out[0]["pick"] == "Home -3" and out[0]["value"] > 0.05
    assert out[0]["dont_bet_past"] is not None and out[0]["pinnacle_pick"] == "Home -5"


def test_same_numbers_no_alert_and_a_huge_gap_is_a_mismatch_not_an_opportunity():
    assert stale.evaluate(S(snap.WH, -3.0), S(snap.SHARP, -3.0), LANDS, 0.02, 3.0) == []
    assert stale.evaluate(S(snap.WH, -3.0), S(snap.SHARP, -9.0), LANDS, 0.02, 3.0) == []


def test_totals_over_is_the_stale_side_when_wagerhouse_total_is_lower():
    out = stale.evaluate(S(snap.WH, -3.0, total=218.0), S(snap.SHARP, -3.0, total=220.0), LANDS, 0.02, 3.0)
    assert [c["side"] for c in out] == ["over"] and out[0]["pick"] == "Over 218"


def test_scan_alerts_once_per_number_respects_the_daily_cap_and_sends_as_stale(monkeypatch):
    con = duckdb.connect()
    sent = []
    sender = lambda env, text, lane=None, kind="info": sent.append((kind, text))
    snaps = [S(snap.WH, -3.0), S(snap.SHARP, -5.0)]
    out = stale.scan(CFG, {}, con, snaps, NOW, sender=sender, lands=LANDS)
    assert len(sent) == 1 and sent[0][0] == "stale" and "NOT a pick" in sent[0][1] and "STALE NUMBER" in sent[0][1]
    stale.scan(CFG, {}, con, snaps, NOW, sender=sender, lands=LANDS)
    assert len(sent) == 1                                     # same game, side and number: not again
    stale.scan(CFG, {}, con, [S(snap.WH, -3.5, eid="E1"), S(snap.SHARP, -5.5, eid="E1")], NOW, sender=sender, lands=LANDS)
    assert len(sent) == 2                                     # the number changed: a new alert
    cfg = {**CFG, "stale": {"max_per_day": 2}}
    held = stale.scan(cfg, {}, con, [S(snap.WH, -2.0, eid="E2"), S(snap.SHARP, -4.0, eid="E2")], NOW, sender=sender, lands=LANDS)
    assert len(sent) == 2 and any("held back" in h for h in held)


def test_started_games_and_missing_pinnacle_are_skipped():
    con = duckdb.connect()
    sent = []
    sender = lambda *a, **k: sent.append(1)
    started = snap.Snap(NOW, snap.WH, "NBA", "E9", "A", "H", NOW - timedelta(hours=1), -3.0, -110, -110, None, None, 220.0, -110, -110)
    stale.scan(CFG, {}, con, [started, S(snap.SHARP, -5.0, eid="E9")], NOW, sender=sender, lands=LANDS)
    stale.scan(CFG, {}, con, [S(snap.WH, -3.0, eid="E8")], NOW, sender=sender, lands=LANDS)
    assert sent == []


def test_grade_records_result_and_closing_line_value():
    con = duckdb.connect()
    con.execute(stale.SCHEMA)
    past = datetime.utcnow() - timedelta(hours=5)
    con.execute("INSERT INTO stale_alerts VALUES ('k', ?, 'NBA','E1','A at H','spread','home','H -3',-3,-110,-5,0.08,-2.5,'H -2.5',?,'x')", [past - timedelta(hours=3), past])
    con.execute("CREATE TABLE line_snapshots (ts_utc TIMESTAMP, source VARCHAR, sport VARCHAR, event_id VARCHAR, away VARCHAR, home VARCHAR, start_utc TIMESTAMP, "
                "home_spread DOUBLE, home_spread_price DOUBLE, away_spread_price DOUBLE, home_ml DOUBLE, away_ml DOUBLE, total DOUBLE, over_price DOUBLE, under_price DOUBLE)")
    con.execute("INSERT INTO line_snapshots VALUES (?, 'pinnacle','NBA','E1','A','H',?,-5.5,-110,-110,NULL,NULL,220,-110,-110)", [past - timedelta(minutes=20), past])
    out = stale.grade(con, scorer=lambda sport, eid: (110, 100))      # home wins by 10, covers -3
    assert out and con.execute("select result, clv_points from stale_grades").fetchone() == ("W", 2.5)
    assert "1 graded" in stale.summary_text(con) or "1 sent, 1 graded" in stale.summary_text(con)
