from datetime import datetime, timedelta, timezone

import pytest

from engine.odds.espn import SourceError
from engine.picks import leans

NOW = datetime(2026, 11, 23, 20, 0, tzinfo=timezone.utc)
CFG = {"timezone_display": "America/Denver", "leans": {"max_per_lane_per_week": 2}}
WORDS = " ".join(["injury"] * 30)


def sheet():
    side = {"side": "home", "pick": "Team A +3", "price": -110.0, "numbers_say_bet": False, "limit_line": 4.0}
    side2 = {"side": "away", "pick": "Team B -3", "price": -110.0, "numbers_say_bet": False, "limit_line": -2.5}
    return {"games": [{"event_id": "E1", "game": "Team B at Team A", "start_utc": (NOW + timedelta(days=1)).isoformat(),
                       "markets": [{"market": "spread", "book_line": 3.0, "pinnacle_line": 3.0, "sides": [side, side2]}]}]}


def lean(**kw):
    d = {"game": "Team B at Team A", "market": "spread", "side": "home", "reason_type": "forecast", "reason": WORDS,
         "source": "https://example.com", "forecast_line": 4.0}
    d.update(kw)
    return d


def test_stamps_numbers_from_the_sheet_and_limit_is_issued_number():
    row, why = leans.check(lean(), CFG, sheet(), {}, NOW)
    assert why == "" and row["book_line"] == 3.0 and row["price"] == -110.0
    assert row["dont_bet_past"] == "Team A +3"       # the numbers do not clear the bar, so never worse than as issued


def test_agent_cannot_type_numbers(tmp_path):
    p = tmp_path / "l.yaml"
    p.write_text("leans:\n- {game: x, market: spread, side: home, reason_type: news, reason: y, source: z, line: 3}\n")
    with pytest.raises(SourceError):
        leans.load(p)


@pytest.mark.parametrize("reason", ["sharp money is on them " + WORDS, "reverse line movement " + WORDS, "short"])
def test_banned_or_thin_reasons_refused(reason):
    row, why = leans.check(lean(reason=reason), CFG, sheet(), {}, NOW)
    assert row is None and why


def test_news_needs_pre_news_pinnacle_and_no_move():
    news = lean(reason_type="news", news_at="2026-11-23 10:00 MT")
    assert leans.check(news, CFG, sheet(), {}, NOW)[0] is None                       # no stored line before the news
    before = datetime(2026, 11, 23, 16, 0, tzinfo=timezone.utc)
    hist = {"E1": [(before, 3.0, None)]}
    assert leans.check(news, CFG, sheet(), hist, NOW)[0] is not None                  # unmoved: accepted
    moved = {"E1": [(before, 4.0, None)]}                                             # Pinnacle went 4 -> 3, toward the home side
    row, why = leans.check(news, CFG, sheet(), moved, NOW)
    assert row is None and "priced" in why
    assert leans.check(lean(reason_type="news"), CFG, sheet(), hist, NOW)[1].startswith("news needs news_at")


def test_weather_is_totals_only():
    assert leans.check(lean(reason_type="weather"), CFG, sheet(), {}, NOW)[0] is None


def test_week_cap_and_fixed_once_issued(tmp_path, monkeypatch):
    import duckdb
    import yaml
    con = duckdb.connect()
    p = tmp_path / "d.yaml"
    monkeypatch.setattr(leans, "decisions_path", lambda day, sport: p)
    p.write_text(yaml.safe_dump({"leans": [lean(), lean(side="away", forecast_line=4.0), lean(side="away", game="Team B at Team A", forecast_line=1.0)]}))
    s = sheet()
    out = leans.ingest(CFG, con, s, "2026-11-23", "NFL", pin_hist={}, now=NOW)
    assert sum(l.startswith("LEAN") for l in out) == 2 and con.execute("select count(*) from leans").fetchone()[0] == 2
    # a third on the same week would be refused by the cap (limit 2 in CFG); re-running never re-stamps the first two
    again = leans.ingest(CFG, con, s, "2026-11-23", "NFL", pin_hist={}, now=NOW)
    assert con.execute("select count(*) from leans").fetchone()[0] == 2 and not [l for l in again if l.startswith("LEAN")]


def test_cap_refuses_extra_lean_in_the_same_week(tmp_path, monkeypatch):
    import duckdb
    import yaml
    con = duckdb.connect()
    p = tmp_path / "d.yaml"
    monkeypatch.setattr(leans, "decisions_path", lambda day, sport: p)
    s = sheet()
    s["games"].append({**s["games"][0], "event_id": "E2", "game": "Team D at Team C"})
    cfg = {"timezone_display": "America/Denver", "leans": {"max_per_lane_per_week": 1}}
    p.write_text(yaml.safe_dump({"leans": [lean(), lean(game="Team D at Team C")]}))
    out = leans.ingest(cfg, con, s, "2026-11-23", "NFL", pin_hist={}, now=NOW)
    assert sum(l.startswith("LEAN") for l in out) == 1 and any(l.startswith("REFUSED") and "limit 1" in l for l in out)


def test_grade_result_clv_forecast_and_record(monkeypatch):
    import duckdb
    from engine.odds import snapshots as snap
    con = snap.connect(":memory:") if False else duckdb.connect()
    con.execute(snap.SCHEMA) if hasattr(snap, "SCHEMA") else None
    con.execute(leans.SCHEMA)
    past = datetime.utcnow() - timedelta(hours=5)
    con.execute("INSERT INTO leans VALUES ('k','2026-11-20 12:00','2026-11-16','NFL','E1','B at A','spread','home','A +3',3.0,-110,3.0,'A +3',3.0,"
                "'forecast','r','s',NULL,NULL,4.0,?,NULL)", [past])
    try:
        con.execute("CREATE TABLE IF NOT EXISTS line_snapshots (ts_utc TIMESTAMP, source VARCHAR, sport VARCHAR, event_id VARCHAR, away VARCHAR, home VARCHAR, "
                    "start_utc TIMESTAMP, home_spread DOUBLE, home_spread_price DOUBLE, away_spread_price DOUBLE, a DOUBLE, b DOUBLE, total DOUBLE, over_price DOUBLE, under_price DOUBLE)")
    except Exception:
        pass
    con.execute("INSERT INTO line_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [past - timedelta(hours=1), snap.SHARP, "NFL", "E1", "B", "A", past, 4.0, -110, -110, None, None, 44.0, -110, -110])
    out = leans.grade({}, con, scorer=lambda sport, eid: (20, 20))
    assert out and out[0].startswith("LEAN GRADED")
    r = con.execute("select result, clv_points, forecast_hit from lean_grades").fetchone()
    assert r == ("W", -1.0, True)         # A +3 on a tie wins; Pinnacle closed +4, so +3 was worse by 1 point; forecast of +4 was reached
    assert leans.record(con)["w"] == 1 and "Paper Leans" in leans.summary_text({}, con)
