"""Changes from review 14 (approved 2026-11-23): teasers, win-chance CLV, minute lags, NBA first-tip window, per-sport readiness."""
from datetime import datetime, timedelta, timezone

import duckdb

from engine import clv, readiness, stale
from engine.burst import in_window
from engine.odds import snapshots as snap
from engine.picks import teasers
from engine.reports import wagerhouse_edge as we

UTC = timezone.utc
CFG = {"margin_sd": {"NBA": {"spread": 12.0, "total": 18.0}}, "timezone_display": "America/Denver"}


def S(**kw):
    base = dict(ts=None, source=snap.WH, sport="NFL", event_id="e1", away="DAL", home="PHI", start=datetime(2030, 1, 1, tzinfo=UTC),
                home_spread=-8.0, home_spread_price=-110, away_spread_price=-110, home_ml=None, away_ml=None, total=44.5, over_price=-110, under_price=-110)
    base.update(kw)
    return snap.Snap(**base)


def test_breakeven_matches_the_review():
    assert round(teasers.breakeven(-110), 4) == 0.7237
    assert round(teasers.breakeven(-120), 4) == 0.7385


def test_wong_legs_only_in_range_and_low_totals():
    st = teasers.settings({})
    now = datetime(2029, 12, 31, tzinfo=UTC)
    legs = teasers.legs_from([S()], now, st)                       # home -8 is a Wong favorite; away +8 is not
    assert [(l["team"], l["line"], l["teased"]) for l in legs] == [("PHI", -8.0, -2.0)]
    assert [l["team"] for l in teasers.legs_from([S(home_spread=2.0)], now, st)] == ["PHI"]     # home underdog +2; away -2 is not a Wong leg
    assert teasers.legs_from([S(total=51.5)], now, st) == []
    assert teasers.legs_from([S(home_spread=-6.5)], now, st) == []
    assert teasers.legs_from([S(source=snap.SHARP)], now, st) == []
    assert teasers.legs_from([S()], datetime(2030, 1, 2, tzinfo=UTC), st) == []    # already started


def test_tickets_pair_within_a_week_and_across_games():
    rows = [("a", "g1", "w1", "W"), ("b", "g1", "w1", "W"), ("c", "g2", "w1", "L"), ("d", "g3", "w2", "W"), ("e", "g4", "w2", "P"), ("f", "g5", "w2", None)]
    assert teasers.tickets(rows) == [("w1", "L"), ("w2", "void")]


def test_teaser_scan_freezes_once_and_grades(monkeypatch):
    con = duckdb.connect()
    cfg = {"teasers": {}, "picks": {}, "timezone_display": "America/Denver"}
    import engine.version as v
    monkeypatch.setattr(v, "stamp", lambda cfg, con: "test")
    now = datetime(2029, 12, 31, tzinfo=UTC)
    assert len(teasers.scan(cfg, con, [S()], now)) == 1
    assert teasers.scan(cfg, con, [S(home_spread=-7.5)], now) == []      # same game and side: frozen at first sight
    con.execute("CREATE TABLE IF NOT EXISTS line_snapshots (event_id VARCHAR, source VARCHAR, ts_utc TIMESTAMP, home_spread DOUBLE)")
    con.execute("UPDATE teaser_legs SET kickoff_utc = '2020-01-01'")
    out = teasers.grade(con, scorer=lambda sport, eid: (20, 21))          # PHI loses by 1: -8 teased to -2 loses? margin -1 + (-2) = -3 -> L
    assert out == ["TEASER LEG GRADED e1|home: L"]
    rec = teasers.record(con, cfg)
    assert (rec["w"], rec["l"], rec["status"]) == (0, 1, "testing")


def test_clv_chance_is_zero_at_the_close_and_signed():
    assert clv.chance(CFG, "NBA", "spread", "home", -5.0, -5.0) == 0.0
    better = clv.chance(CFG, "NBA", "spread", "home", -4.0, -5.0)       # home -4 when the close was -5
    assert better > 0.02 and clv.chance(CFG, "NBA", "spread", "away", -4.0, -5.0) < 0
    assert clv.chance(CFG, "NBA", "moneyline", "home", 1, 1) is None


def test_lag_minutes_and_verdict():
    t0 = datetime(2026, 11, 24, 17, 0)
    ser = [(t0, -3.0, -3.0), (t0 + timedelta(minutes=10), -3.0, -4.0), (t0 + timedelta(minutes=20), -3.0, -4.0), (t0 + timedelta(minutes=40), -4.0, -4.0)]
    rows = we.lag_minutes(ser, t0 + timedelta(hours=3), t0 + timedelta(hours=1))
    assert rows == [{"status": "caught", "stale_min": 30.0, "gap_min": 10.0}]
    assert we.lag_verdict(rows)[0] == "too early"
    assert we.lag_verdict(rows * 60)[0] == "keep"
    quick = [{"status": "caught", "stale_min": 0.0, "gap_min": 10.0}] * 60
    assert we.lag_verdict(quick)[0] == "kill"
    assert we.lag_verdict([{"status": "caught", "stale_min": 0.0, "gap_min": 60.0}])[0] == "no data"     # hourly reads cannot time it


def test_nba_window_follows_the_first_tip():
    cfg = {"timezone_display": "America/Denver", "burst": {"enabled": True, "sports": {"NBA": {"before_first_start": [120, 15]}}}}
    tip = datetime(2026, 11, 25, 0, 0, tzinfo=UTC)           # 5:00 pm MT
    assert in_window(cfg, tip - timedelta(minutes=90), "NBA", tip) is not None
    assert in_window(cfg, tip - timedelta(minutes=150), "NBA", tip) is None
    assert in_window(cfg, tip + timedelta(minutes=10), "NBA", tip) is not None
    assert in_window(cfg, tip - timedelta(minutes=90), "NBA", None) is None


def test_readiness_per_sport_thresholds():
    cfg = {"go_live": {"per_sport": {"NBA": {"graded_min": 25}}}}
    assert readiness.settings(cfg, "NBA")["graded_min"] == 25
    assert readiness.settings(cfg, "NFL")["graded_min"] == 10
    text = readiness.report({"unit": 25, **cfg}, duckdb.connect())
    assert "## NFL" in text and "## NBA" in text and "win chance" in text


def test_college_is_a_stale_sport_with_a_landing_table():
    assert "College" in stale.DEFAULTS["sports"]
    ls, lt = stale.landings("College", {})
    assert 0.3 < ls.probs(-7.0, -7.0, "home")[0] < 0.6


def test_stage_zero_messages_never_ask_for_money():
    from zoneinfo import ZoneInfo
    from engine.picks import agent
    r = {"event_id": "e", "market": "spread", "side": "home", "status": "Conditional", "pick": "UCLA +7", "price": -110, "game": "USC at UCLA",
         "kick": datetime(2030, 1, 1, tzinfo=UTC), "dollars": 12.5, "dont_bet_past": "UCLA +7",
         "decision": {"condition": "QB confirmed", "summary": "why"}}
    wait = agent.changes({}, [r], ZoneInfo("America/Denver"), "College", "", 0)[0]
    assert "Bet $" not in wait and "Paper only" in wait
    bet = agent.changes({}, [{**r, "status": "Bet", "dollars": 25}], ZoneInfo("America/Denver"), "College", "", 0)[0]
    assert bet.split("\n")[0].endswith("PAPER BET (Stage 0: tracked, no money yet)") and "Stake: $0" in bet
    live = agent.changes({}, [{**r, "status": "Bet", "dollars": 25}], ZoneInfo("America/Denver"), "College", "", 1)[0]
    assert "BET NOW" in live and "Stake: $25" in live


def test_script_blend_weight_and_ridge():
    from engine.models import script
    assert script.fit_weight([1, 2, 3], [0, 0, 0], [1, 2, 3]) == 1.0
    assert script.fit_weight([1, 2, 3], [0, 0, 0], [0, 0, 0]) == 0.0
    X = [[float(i), float(i % 3)] for i in range(50)]
    y = [2.0 * r[0] + 1.0 for r in X]
    m = script.ridge(X, y, 0.0)
    assert abs(script.predict(m, [10.0, 1.0]) - 21.0) < 1e-6


def _game(**kw):
    g = {"event_id": "g1", "home": "Home", "away": "Away", "kick": datetime(2030, 1, 1, tzinfo=UTC),
         "own_home": 27.0, "own_away": 20.0, "own_margin": 7.0, "own_total": 47.0, "mkt_home": 24.0, "mkt_away": 21.0,
         "mkt_margin": 3.0, "mkt_total": 45.0, "wh_spread": -3.0, "wh_home_price": -110, "wh_away_price": -110,
         "wh_total": 45.0, "wh_over": -110, "wh_under": -110}
    g.update(kw)
    return g


def test_playbook_blends_at_the_starting_weight_and_checks_big_gaps():
    from engine.picks import playbook as pb
    st = pb.settings({})
    lands = stale.landings("NFL", {})
    cands = pb.candidates([_game()], st, lands)
    side = next(c for c in cands if c["market"] == "side" and c["side"] == "home")
    assert abs(side["our_line"] - -(3.0 + 0.25 * 4.0)) < 1e-9 and side["check"] is True     # own 7 vs market 3: 4 points > 3
    graded = pb.grade_all(cands, st)
    assert len(graded) == 1                                      # one position per game
    key = pb.key_of(next(c for c in cands if c["market"] == "side" and c["side"] == "home"))
    cleared = pb.grade_all(pb.candidates([_game()], st, lands), st, checks={key: {"verdict": "clear", "why": "nothing found"}})
    assert any(c["grade"] == "B" for c in cleared)


def test_playbook_stakes_half_size_then_full_and_stop_loss():
    from engine.picks import playbook as pb
    st = pb.settings({"playbook": {"live_since": "2026-11-24"}})
    assert pb.stake(st, "B", datetime(2026, 11, 25, tzinfo=UTC), 0.0, 25)[:2] == (0.25, 6.25)
    assert pb.stake(st, "A", datetime(2027, 1, 5, tzinfo=UTC), 0.0, 25)[:2] == (1.0, 25.0)
    assert pb.stake(st, "B", datetime(2027, 1, 5, tzinfo=UTC), -10.0, 25)[:2] == (0.0, 0.0)
    assert pb.stake(st, "C", datetime(2027, 1, 5, tzinfo=UTC), 0.0, 25)[:2] == (0.0, 0.0)


def test_teaser_tickets_pair_open_legs_from_different_games(monkeypatch):
    con = duckdb.connect()
    con.execute(teasers.SCHEMA)
    import engine.version as v
    monkeypatch.setattr(v, "stamp", lambda cfg, con: "test")
    now = datetime(2029, 12, 31, tzinfo=UTC)
    cfg = {"teasers": {}, "timezone_display": "America/Denver", "unit": 25, "playbook": {"live_since": "2029-12-30"}}
    teasers.scan({**cfg, "teasers": {"real_money": False}}, con, [S(), S(event_id="e2", home="PIT", away="DEN", home_spread=2.5, total=38.0)], now)
    sent = []
    out = teasers.tickets_to_send(cfg, con, now, sender=lambda env, text, lane, kind: sent.append((lane, kind)))
    assert len(out) == 1 and "TEASER BET (A)" in out[0] and "$12.5" in out[0] and sent == [("nfl_teasers", "bet")]
    assert teasers.tickets_to_send(cfg, con, now) == []          # legs already used


def test_prop_candidates_feed_the_script_and_blend():
    from engine.picks import playbook as pb

    class D:
        def p_over(self, proj, line): return 0.70 if proj > line else 0.30
        def median(self, proj): return round(proj)

    class PM:
        params = {"receptions": (0.85, 1.0)}
        dists = {"receptions": D()}

    g = _game(home="Philadelphia Eagles", away="Dallas Cowboys", own_home=36.0, mkt_home=24.0)
    priced = [{"away": "Dallas Cowboys", "home": "Philadelphia Eagles", "team": "PHI", "stat": "receptions", "projection": 5.0, "line": 5.5,
               "market_p_over": 0.45, "over_price": -110, "under_price": -110, "player": "A Receiver", "player_id": "p1", "label": "Receptions"}]
    st = pb.settings({})
    cands = pb.prop_candidates([g], PM(), priced, st)
    over = next(c for c in cands if c["side"] == "over")
    assert abs(over["our_line"] - 5.0 * (24 + 0.4 * 12) / 24) < 1e-9       # script lifts the projection past the line
    assert abs(over["p"] - (0.45 + 0.5 * 0.25)) < 1e-9 and over["check"] is True
    assert pb.grade_props(cands, st)[0]["grade"] == "C"                    # held: CHECK
    key = pb.prop_key(over)
    assert pb.grade_props(cands, st, {key: {"verdict": "clear", "why": "x"}})[0]["grade"] == "B"
