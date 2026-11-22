from datetime import datetime, timedelta

import duckdb
import pytest

from engine.odds import snapshots as snap
from engine.picks import agent, grade


def test_result_spread():
    assert grade.result("spread", "away", -2.5, 20, 23) == "W"     # away +2.5 and wins outright
    assert grade.result("spread", "home", -3.0, 23, 20) == "P"     # home -3 wins by exactly 3
    assert grade.result("spread", "home", 2.5, 20, 23) == "L"


def test_result_total():
    assert grade.result("total", "over", 44.5, 24, 21) == "W"
    assert grade.result("total", "under", 44.5, 24, 21) == "L"
    assert grade.result("total", "over", 45.0, 24, 21) == "P"


def test_unknown_market_fails_loudly():
    with pytest.raises(ValueError):
        grade.result("moneyline", "home", 0, 1, 0)


def test_clv_points_from_the_sides_own_view():
    assert grade.clv_points("spread", "home", -2.5, -3.5) == pytest.approx(1.0)    # laid a point less than the close
    assert grade.clv_points("spread", "away", -2.5, -3.5) == pytest.approx(-1.0)   # took a point fewer
    assert grade.clv_points("total", "over", 44.5, 46.0) == pytest.approx(1.5)
    assert grade.clv_points("total", "under", 44.5, 46.0) == pytest.approx(-1.5)


def test_profit():
    assert grade.profit(1, -110, "W") == pytest.approx(0.909, abs=1e-3)
    assert grade.profit(0.5, -110, "L") == -0.5
    assert grade.profit(1, -110, "P") == 0.0


def _db():
    con = duckdb.connect(":memory:")
    con.execute(snap.SCHEMA)
    con.execute(agent.SCHEMA)
    start = datetime.utcnow() - timedelta(hours=5)
    con.execute("INSERT INTO line_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [start - timedelta(hours=1), snap.SHARP, "NFL", "E1", "A", "H", start, -3.5, -110, -110, None, None, 44.0, -110, -110])
    con.execute("INSERT INTO engine_pick_events VALUES (?,?,?,?,?,?,?,?,?,?)",
                [start - timedelta(hours=20), "E1|spread|home", "A at H", "H -2.5", "Bet", -2.5, -110, -3.0, 0.03, -3.5])
    con.execute("INSERT INTO engine_pick_events VALUES (?,?,?,?,?,?,?,?,?,?)",
                [start - timedelta(hours=20), "E1|total|over", "A at H", "Over 43", "Pass", 43.0, -110, 43.5, 0.01, None])
    return con


CFG = {"picks": {"max_units": 1, "conditional_units": 0.5}}


def test_run_grades_bet_and_pass_and_does_not_repeat():
    con = _db()
    out = grade.run(CFG, con, scorer=lambda sport, eid: (27, 20))
    assert sum(l.startswith("GRADED") for l in out) == 2
    bet = con.execute("SELECT result, clv_points, profit_units FROM engine_pick_grades WHERE status='Bet'").fetchone()
    assert bet[0] == "W" and bet[1] == pytest.approx(1.0) and bet[2] == pytest.approx(0.909, abs=1e-3)
    ps = con.execute("SELECT result, profit_units FROM engine_pick_grades WHERE status='Pass'").fetchone()
    assert ps == ("W", 0.0)       # over 43 with 47 points; a Pass never carries units
    assert grade.run(CFG, con, scorer=lambda *a: (_ for _ in ()).throw(AssertionError("regraded"))) == []


def test_run_waits_when_game_not_final():
    con = _db()
    out = grade.run(CFG, con, scorer=lambda sport, eid: None)
    assert all(l.startswith("waiting") for l in out) and con.execute("SELECT count(*) FROM engine_pick_grades").fetchone()[0] == 0


def test_run_says_why_when_no_pinnacle_close():
    con = _db()
    con.execute("DELETE FROM line_snapshots WHERE source=?", [snap.SHARP])
    con.execute("INSERT INTO line_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [datetime.utcnow() - timedelta(hours=9), snap.WH, "NFL", "E1", "A", "H", datetime.utcnow() - timedelta(hours=5),
                 -3.0, -110, -110, None, None, 44.0, -110, -110])
    out = grade.run(CFG, con, scorer=lambda *a: (27, 20))
    assert any("no Pinnacle line stored" in l for l in out)
