"""Decision 0030: engine check and the sport parity table."""
from __future__ import annotations

import copy
from datetime import datetime, timezone

from test_review18 import _pb_con

NOW = datetime(2026, 11, 25, 20, 0, tzinfo=timezone.utc)


def _cfg():
    from engine import config
    return config.load_config()


def _con():
    con = _pb_con()
    con.execute("CREATE TABLE alerts_sent (key VARCHAR PRIMARY KEY, ts_utc TIMESTAMP, kind VARCHAR, text VARCHAR, delivered BOOLEAN)")
    con.execute("CREATE TABLE agent_runs (ts_utc TIMESTAMP, reason VARCHAR, ok BOOLEAN, note VARCHAR)")
    return con


def test_parity_is_complete_in_config_and_a_gap_fails():
    from engine import lanes
    cfg = _cfg()
    assert lanes.parity_problems(cfg) == []
    bad = copy.deepcopy(cfg)
    del bad["parity"]["weather"]["College"]
    assert lanes.parity_problems(bad) == ["parity: College has no entry for weather"]
    bad2 = copy.deepcopy(cfg)
    bad2["parity"]["props_model"]["NBA"]["status"] = "maybe"
    assert "status 'maybe'" in lanes.parity_problems(bad2)[0]


def test_parity_money_cells_come_from_switches():
    from engine import lanes
    rows = dict(lanes.parity_rows(_cfg()))
    assert rows["Full-game picks (money)"]["NFL"] == "staked"
    assert rows["Full-game picks (money)"]["College"].startswith("shown")
    assert rows["News into our number (decision 0029)"]["College"].startswith("on")


def test_undelivered_staked_pick_and_zero_dollar_bet_fail():
    from engine import checks
    con = _con()
    con.execute("INSERT INTO playbook_picks (pick_key, first_seen_utc, sport, pick, dollars, units, dont_bet_past, kickoff_utc) "
                "VALUES ('k1', ?, 'NFL', 'Titans +15', 25, 0.5, 'Titans +14.5', ?)", [NOW.replace(tzinfo=None), NOW.replace(tzinfo=None)])
    con.execute("INSERT INTO alerts_sent VALUES ('playbook|k1', ?, 'bet', 'x', false)", [NOW.replace(tzinfo=None)])
    con.execute("INSERT INTO alerts_sent VALUES ('playbook|k2', ?, 'bet', 'NFL\\nStake: $0 (paper: test)', true)", [NOW.replace(tzinfo=None)])
    res = {n: (ok, d) for n, ok, d in checks.run(con, _cfg(), NOW)}
    assert res["Every staked pick reached Telegram"][0] is False and "Titans" in res["Every staked pick reached Telegram"][1]
    assert res["No $0 pick sent as a bet"][0] is False


def test_failures_make_one_telegram_line_and_passes_make_none():
    from engine import checks
    assert checks.telegram_text([("a", True, "fine")]) is None
    t = checks.telegram_text([("a", True, "fine"), ("b", False, "broken")])
    assert t.startswith("CHECK FAILED (not a bet)") and "- b: broken" in t and "- a" not in t
