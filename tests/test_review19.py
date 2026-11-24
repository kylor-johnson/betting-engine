"""Research 19 follow-ups (decision 0027): weekly cap, NFL stop counts teasers, price/handicap edge split, lane events, one pick path."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from test_review18 import _pb_con

UTC = timezone.utc
CFG = {"timezone_display": "America/Denver", "playbook": {"weekly_cap_dollars": 100}}
NOW = datetime(2026, 11, 25, 20, 0, tzinfo=UTC)          # Wednesday


def _pick(con, key, dollars, units, when, sport="NFL", market="side", edge=0.04, price_edge=0.03):
    from engine.picks import playbook as pb
    con.execute(f"INSERT INTO playbook_picks (pick_key, first_seen_utc, sport, event_id, market, units, dollars, edge, price_edge) "
                f"VALUES (?,?,?,?,?,?,?,?,?)", [key, when.replace(tzinfo=None), sport, key, market, units, dollars, edge, price_edge])


def test_weekly_cap_counts_picks_and_teasers_from_monday_mountain():
    from engine.picks import playbook as pb
    con = _pb_con()
    _pick(con, "last-week", 50, 1, NOW - timedelta(days=4))           # previous Saturday: not this week
    _pick(con, "mon", 50, 1, datetime(2026, 11, 23, 8, 0, tzinfo=UTC))  # Monday 1am MT
    assert pb.week_staked(con, CFG, NOW) == 50
    assert pb.over_weekly_cap(con, CFG, 50, NOW) is None
    con.execute("INSERT INTO teaser_tickets (ticket_key, sent_utc, units, dollars) VALUES ('t', ?, 1, 25)", [NOW.replace(tzinfo=None)])
    note = pb.over_weekly_cap(con, CFG, 50, NOW)
    assert note and "weekly cap is $100" in note
    st = pb.settings(CFG, "NFL")
    u, d, n, nom = pb._paper_or_staked(con, st, {"grade": "B", "event_id": "new"}, 0.5, 50.0, "B pick", 100, True, now=NOW, cfg=CFG)
    assert (u, d, nom) == (0.0, 0.0, 0.5) and "weekly cap" in n


def test_nfl_stop_counts_teasers_and_nba_does_not():
    from engine.picks import playbook as pb
    con = _pb_con()
    _pick(con, "p1", 25, 0.5, NOW)
    con.execute("INSERT INTO playbook_grades (pick_key, result, profit_units) VALUES ('p1', 'L', -0.5)")
    con.execute("INSERT INTO teaser_legs (leg_key, event_id) VALUES ('a', 'g1'), ('b', 'g2'), ('c', 'g3'), ('d', 'g4')")
    con.execute("INSERT INTO teaser_tickets (ticket_key, sent_utc, leg_a, leg_b, units, dollars, price) VALUES ('t1',?,'a','b',1,50,-110), ('t2',?,'c','d',1,50,-110)",
                [NOW.replace(tzinfo=None)] * 2)
    con.execute("INSERT INTO teaser_grades (leg_key, result) VALUES ('a','W'), ('b','L'), ('c','W'), ('d','W')")
    assert abs(pb.down_units(con, "NFL") - (-0.5 - 1 + 100 / 110)) < 1e-9
    assert pb.down_units(con, "NBA") == 0.0


def test_edge_split_and_price_edge_on_candidates():
    from engine.picks import playbook as pb
    c = {"market": "side", "edge": 0.041, "price_edge": 0.03}
    line = pb.edge_split(c)
    assert "+4.1%" in line and "+3.0% from the price alone" in line and "+1.1% from our handicap" in line
    assert pb.edge_split({"market": "side", "edge": 0.04}) == "Edge +4.0%."


def test_lane_events_stop_and_review_fire_once_with_stable_keys():
    from engine.picks import playbook as pb
    con = _pb_con()
    cfg = {"playbook": {"stop_loss_units": 1.0, "sports": {"NBA": {}}}, "go_live": {"pause_n": 2, "pause_clv": -0.015}}
    for i in range(3):
        _pick(con, f"n{i}", 12.5, 0.5, NOW, sport="NBA", market="prop")
        con.execute("INSERT INTO playbook_grades (pick_key, result, profit_units, clv_chance) VALUES (?, 'L', -0.5, -0.03)", [f"n{i}"])
    ev = dict(pb.lane_events(con, cfg))
    assert any(k.startswith("stop|NBA|") for k in ev)
    assert any(k.startswith("review|NBA|props|") for k in ev)
    assert dict(pb.lane_events(con, cfg)).keys() == ev.keys()


def test_old_path_picks_are_held_back_unless_switched_on(monkeypatch):
    from engine.picks import agent
    import inspect
    src = inspect.getsource(agent.finalize)
    assert 'get("send_picks", False)' in src


def test_lock_refuses_a_second_session(tmp_path, monkeypatch):
    from engine import config, session_lock
    monkeypatch.setattr(config, "DATA", tmp_path)
    assert session_lock.take("a").startswith("Lock taken")
    assert session_lock.take("b").startswith("REFUSED")
    assert session_lock.take("b", force=True).startswith("Lock taken")
    assert session_lock.release() == "Lock released." and session_lock.held() is None


def test_stop_counts_only_from_live_since_so_a_restart_is_a_new_date():
    """Research 22, finding 2 (Kylor 2026-11-24): results before playbook.live_since do not count toward the stop."""
    from engine.picks import playbook as pb
    con = _pb_con()
    _pick(con, "old", 25, 0.5, datetime(2026, 11, 24, 5, 0, tzinfo=UTC))      # Nov 23, 10pm Mountain: before live_since
    _pick(con, "new", 25, 0.5, datetime(2026, 11, 24, 8, 0, tzinfo=UTC))      # Nov 24, 1am Mountain
    con.execute("INSERT INTO playbook_grades (pick_key, result, profit_units) VALUES ('old', 'L', -0.5), ('new', 'L', -0.5)")
    con.execute("INSERT INTO teaser_legs (leg_key, event_id) VALUES ('a', 'g1'), ('b', 'g2')")
    con.execute("INSERT INTO teaser_tickets (ticket_key, sent_utc, leg_a, leg_b, units, dollars, price) VALUES ('t', '2026-11-23 20:00', 'a', 'b', 1, 50, -110)")
    con.execute("INSERT INTO teaser_grades (leg_key, result) VALUES ('a', 'L'), ('b', 'W')")
    cfg = {"timezone_display": "America/Denver", "playbook": {"live_since": "2026-11-24"}}
    assert pb.down_units(con, "NFL", cfg) == -0.5
    assert pb.down_units(con, "NFL", {"timezone_display": "America/Denver", "playbook": {"live_since": "2026-11-25"}}) == 0.0
