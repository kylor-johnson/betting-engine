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
    con.execute("INSERT INTO engine_pick_events (ts_utc, pick_key, game, pick, status, book_line, price, fair, value, pinnacle_line) VALUES (?,?,?,?,?,?,?,?,?,?)",
                [start - timedelta(hours=20), "E1|spread|home", "A at H", "H -2.5", "Bet", -2.5, -110, -3.0, 0.03, -3.5])
    con.execute("INSERT INTO engine_pick_events (ts_utc, pick_key, game, pick, status, book_line, price, fair, value, pinnacle_line) VALUES (?,?,?,?,?,?,?,?,?,?)",
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
    assert any("closing-line value n/a" in l and l.startswith("GRADED") for l in out)
    bet = con.execute("SELECT result, clv_points, pinnacle_close FROM engine_pick_grades WHERE status='Bet'").fetchone()
    assert bet == ("W", None, None)        # the result is graded; only the closing-line value is blank
    assert "closing-line value n/a" in " ".join(grade.summary(con, CFG))


def test_board_section_shows_graded_picks(tmp_path, monkeypatch):
    from datetime import datetime
    from engine import config
    from engine.picks import board
    db = tmp_path / "t.duckdb"
    monkeypatch.setattr(config, "DB", db)
    con = snap.connect(db)
    con.execute(grade.GRADES)
    con.execute("INSERT INTO engine_pick_grades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ["E1|spread|home", "A at H", "H -2.5", "Bet", "NFL", "spread", datetime(2026, 11, 22), -2.5, -110, 1.0, -3.5, 1.0,
                 27, 20, "W", 0.909, datetime(2026, 11, 23)])
    con.close()
    html = board._grades_html(None)
    assert "H -2.5" in html and "+1.0" in html and "W" in html and "+0.91" in html


def _hold_in_other_process(db, seconds):
    import subprocess, sys, time
    code = f"import duckdb,time; c=duckdb.connect(r'{db}'); print('held', flush=True); time.sleep({seconds})"
    p = subprocess.Popen([sys.executable, "-I", "-c", code], stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == "held"
    return p


def test_connect_waits_for_a_busy_file_then_succeeds(tmp_path):
    import time
    db = tmp_path / "busy.duckdb"
    p = _hold_in_other_process(db, 2)
    t = time.monotonic()
    con = snap.connect(db, wait=15)
    assert time.monotonic() - t >= 1.0
    con.close()
    p.wait()


def test_connect_gives_up_after_the_wait(tmp_path):
    import duckdb
    db = tmp_path / "busy2.duckdb"
    p = _hold_in_other_process(db, 5)
    with pytest.raises(duckdb.IOException):
        snap.connect(db, wait=2)
    p.kill()


def test_board_shows_a_graded_pick_with_no_closing_line(tmp_path, monkeypatch):
    from datetime import datetime
    from engine import config
    from engine.picks import board
    db = tmp_path / "t2.duckdb"
    monkeypatch.setattr(config, "DB", db)
    con = snap.connect(db)
    con.execute(grade.GRADES)
    con.execute("INSERT INTO engine_pick_grades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ["E9|spread|away", "A at H", "A +2.5", "Conditional", "NBA", "spread", datetime(2026, 11, 22), 2.5, -110, 0.5, None, None,
                 100, 104, "L", -0.5, datetime(2026, 11, 23)])
    con.close()
    html = board._grades_html(None)
    assert "A +2.5" in html and "n/a" in html
