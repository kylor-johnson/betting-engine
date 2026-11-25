"""Decision 0036 (research 24's yes-list, items 1-11): one test per change."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import duckdb
import pytest


def _cfg():
    from engine import config
    return config.load_config()


def _con():
    from engine.picks import playbook as pb, teasers
    from engine.models import props
    con = duckdb.connect()
    con.execute(pb.SCHEMA)
    con.execute(pb.ALERTS_SCHEMA)
    con.execute(teasers.SCHEMA)
    con.execute(props.SCHEMA)
    return con


# 1, 2, 6, 8: the switches
def test_config_switches():
    from engine.picks import playbook as pb
    cfg = _cfg()
    assert pb.settings(cfg, "NFL")["weights"]["prop"] == 0.15 and pb.settings(cfg, "NBA")["weights"]["prop"] == 0.25
    nba = pb.settings(cfg, "NBA")
    assert nba["full_game"] == "show" and not nba.get("news_picks")          # no money on NBA full-game, news picks included
    assert pb.settings(cfg, "College")["full_game"] == "stake"
    assert all(pb.settings(cfg, s)["live_since"] == "2026-11-23" for s in ("NFL", "NBA", "College"))
    assert cfg["read_hours"]["other"][-1] == 21 and cfg["read_hours"]["sunday"][-1] == 21
    assert "18:30" in cfg["nba_watch"]["run_times"]


def test_nba_watch_plist_matches_config():
    import plistlib
    from engine import config
    pl = plistlib.loads((config.ROOT / "ops" / "launchd" / "com.kylor.betting-engine.nba-watch.plist").read_bytes())
    times = sorted(f"{d['Hour']:02d}:{d['Minute']:02d}" for d in pl["StartCalendarInterval"])
    assert times == sorted(_cfg()["nba_watch"]["run_times"])


def test_review_line_counts_from_live_since():
    from engine.picks import playbook as pb
    con = _con()
    cfg = {"playbook": {"live_since": "2030-01-10"}, "go_live": {"pause_n": 2, "pause_clv": -0.015}, "timezone_display": "America/Denver"}
    for i, day in enumerate((5, 6)):          # two bad picks before live_since: no review
        con.execute("INSERT INTO playbook_picks (pick_key, first_seen_utc, sport, market, units, dollars) VALUES (?, ?, 'NFL', 'side', 0.5, 25)",
                    [f"k{i}", datetime(2030, 1, day)])
        con.execute("INSERT INTO playbook_grades (pick_key, result, clv_chance) VALUES (?, 'L', -0.05)", [f"k{i}"])
    assert not [k for k, _ in pb.lane_events(con, cfg) if k.startswith("review|NFL")]
    for i, day in enumerate((11, 12)):
        con.execute("INSERT INTO playbook_picks (pick_key, first_seen_utc, sport, market, units, dollars) VALUES (?, ?, 'NFL', 'side', 0.5, 25)",
                    [f"n{i}", datetime(2030, 1, day)])
        con.execute("INSERT INTO playbook_grades (pick_key, result, clv_chance) VALUES (?, 'L', -0.05)", [f"n{i}"])
    assert [k for k, _ in pb.lane_events(con, cfg) if k.startswith("review|NFL")]


# 3. News counts toward CHECK; oversized entries are refused
def _game(**kw):
    g = {"event_id": "e", "home": "H", "away": "A", "kick": datetime(2030, 1, 1, tzinfo=timezone.utc),
         "own_home": 22.0, "own_away": 20.0, "own_margin": 2.0, "own_total": 42.0, "mkt_home": 22.0, "mkt_away": 20.0,
         "mkt_margin": 2.0, "mkt_total": 42.0, "wh_spread": -2.0, "wh_home_price": -110, "wh_away_price": -110,
         "wh_total": 42.0, "wh_over": -110, "wh_under": -110}
    g.update(kw)
    return g


def test_news_counts_toward_check():
    from engine.picks import playbook as pb
    from engine.picks.pricing import Landing, bell_rows
    st = pb.settings({}, "NFL")
    lands = (Landing(bell_rows("spread", 13.0, -20, 20), "spread", 0.25, 100), Landing(bell_rows("total", 13.0, 30, 60), "total", 0.25, 100))
    side = [c for c in pb.candidates([_game(adj_margin=3.5)], st, lands) if c["market"] == "side"]
    assert side and all(c["check"] for c in side)          # our script equals the market, but the news alone is 3.5 points: CHECK
    side = [c for c in pb.candidates([_game(adj_margin=2.0)], st, lands) if c["market"] == "side"]
    assert side and not any(c["check"] for c in side)


def test_oversized_news_is_not_applied(monkeypatch):
    from engine.picks import playbook as pb, slate
    entry = {"game": "A at H", "market": "spread", "team": "H", "points": -5.0, "reason": "QB out", "source": "https://x",
             "added": "2030-01-01", "news_at": "2030-01-01 09:00 MT"}
    monkeypatch.setattr(slate, "load_adjustments", lambda: [entry])
    monkeypatch.setattr(pb, "_pin_history", lambda con, sport: {})
    games = [_game()]
    pb.apply_news(None, games, "NFL", datetime(2030, 1, 1, 20, tzinfo=timezone.utc))
    assert "adj_margin" not in games[0] and "larger than the 3-point limit" in games[0]["news"][0]
    games = [_game()]
    pb.apply_news(None, games, "College", datetime(2030, 1, 1, 20, tzinfo=timezone.utc))
    assert "larger than" not in games[0]["news"][0]                 # college allows 5.5


# 4. A late news_at cannot hide a move that already happened
def test_late_news_time_still_sees_the_earlier_move():
    from engine.picks.slate import unpriced_part
    t0 = datetime(2030, 1, 1, 15, 30, tzinfo=timezone.utc)          # 8:30 MT, when the news really broke
    rows = [(t0 - timedelta(hours=1), -3.0, 44), (t0 + timedelta(hours=1), -0.5, 44), (t0 + timedelta(hours=4), -0.5, 44)]
    late = {"market": "spread", "team": "Home", "points": -2.5, "news_at": "2030-01-01 11:30 MT"}      # typed three hours late
    pts, why = unpriced_part(late, rows, -0.5, 44, 1)
    assert pts == 0.0 and why.startswith("priced")


# 5. Pinnacle's price, the forecast wind term, the NBA curve
def test_market_reference_uses_the_price():
    from engine.picks import playbook as pb
    from engine.picks.pricing import Landing, bell_rows
    land = Landing(bell_rows("spread", 13.0, -20, 20), "spread", 0.25, 100)
    assert pb._fair_line(-3.0, -125, 105, land) < -3.2          # home at -125 is more than a 3-point favourite
    assert pb._fair_line(-3.0, -110, -110, land) == pytest.approx(-3.0)
    assert pb._fair_line(-3.0, None, -110, land) == -3.0


def test_nfl_script_has_no_actual_weather_and_a_forecast_wind_term():
    from engine.models import script
    assert "wind6" not in script.FEATURES and "rain" not in script.FEATURES
    assert script.forecast_wind_points(None) == 0.0 and script.forecast_wind_points(6.0) == 0.0
    assert script.forecast_wind_points(16.0) == pytest.approx(-2.73)


def test_nba_team_total_curve():
    from engine.picks import playbook as pb
    assert pb.settings({}, "NBA")["team_total_sd"] == 11.5


# 7. Units first; the $0 guard still sees a $0 bet in the new wording
def test_units_text_and_zero_guard():
    from engine import checks, config
    assert config.units_text(0.5, 12.5) == "½ unit ($12.50)" and config.units_text(1, 50) == "1 unit ($50)"
    assert config.units_text(0, 0) == "0 units ($0)"
    con = _con()
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    con.execute("INSERT INTO alerts_sent VALUES ('playbook|z', ?, 'bet', 'NFL\nStake: 0 units ($0) (paper: test)', true)", [now.replace(tzinfo=None)])
    assert [k for k, _ in checks.delivery_problems(con) if "z" in k]


# 9. A pick the market moved past does not hide the next-best pick on the game
def test_moved_pick_does_not_hide_the_next_one():
    from engine.picks import playbook as pb
    st = pb.settings({}, "NFL")
    a = {"event_id": "e", "market": "side", "side": "home", "edge": 0.06, "check": False, "line": -3}
    b = {"event_id": "e", "market": "total", "side": "under", "edge": 0.04, "check": False, "line": 44}
    got = pb.grade_all([dict(a), dict(b)], st, mover=lambda c: "moved" if c["market"] == "side" else None)
    assert got[0]["market"] == "total" and got[0]["grade"] == "B"


# 10. Game-cap paper does not use a cap slot
def test_game_cap_paper_does_not_count_for_the_weekly_cap():
    from engine.picks import playbook as pb
    con = _con()
    for i, (dollars, reason) in enumerate(((25, None), (0, "paper: $50 is already on this game; the cap is one unit"), (0, "paper: past the cap"))):
        con.execute("INSERT INTO playbook_picks (pick_key, sport, market, nfl_week, dollars, paper_reason) VALUES (?, 'NFL', 'side', 'w', ?, ?)",
                    [f"k{i}", dollars, reason])
    assert con.execute(f"SELECT count(*) FROM playbook_picks WHERE nfl_week='w' AND {pb.COUNTS_FOR_CAP}").fetchone()[0] == 2


# 11. Props pay at the limit price; voids
def _prop_pick(con, kick, limit_price=111.0):
    con.execute("INSERT INTO playbook_picks (pick_key, first_seen_utc, sport, event_id, game, market, side, pick, line, price, grade, units, "
                "dollars, kickoff_utc, nominal_units, limit_price) VALUES ('prop|p|tds|under|0.5|e1', ?, 'NFL', 'e1', 'A at H', 'prop', 'under', "
                "'p under 0.5', 0.5, 123, 'B', 0.5, 25, ?, 0.5, ?)", [kick - timedelta(hours=3), kick, limit_price])


def test_prop_profit_at_the_limit_price():
    from engine.picks import playbook as pb
    con = _con()
    kick = datetime(2020, 1, 1, 18)
    _prop_pick(con, kick)
    con.execute("INSERT INTO prop_evals (ts_utc, start_utc, sport, player_id, stat, home, away, line, outcome) VALUES "
                "(?, '2020-01-01T18:00:00Z', 'NFL', 'p', 'tds', 'H', 'A', 0.5, 0)", [kick])
    pb.grade(con, {}, scorer=lambda s, e: (20, 17))
    prof = con.execute("SELECT profit_units FROM playbook_grades").fetchone()[0]
    assert prof == pytest.approx(0.5 * 1.11)             # +111, not Pinnacle's +123


def test_prop_whose_player_did_not_play_is_void():
    from engine.picks import playbook as pb
    con = _con()
    _prop_pick(con, datetime(2020, 1, 1, 18))
    pb.grade(con, {}, scorer=lambda s, e: (20, 17))      # final, long ago, no stat line for the player
    assert con.execute("SELECT result, profit_units FROM playbook_grades").fetchone() == ("V", 0.0)


def test_prop_not_void_too_early():
    from engine.picks import playbook as pb
    con = _con()
    _prop_pick(con, datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=10))
    pb.grade(con, {}, scorer=lambda s, e: (20, 17))
    assert con.execute("SELECT count(*) FROM playbook_grades").fetchone()[0] == 0


def test_postponed_game_is_void():
    from engine.picks import playbook as pb
    con = _con()
    kick = datetime(2020, 1, 1, 18)
    con.execute("INSERT INTO playbook_picks (pick_key, first_seen_utc, sport, event_id, game, market, side, pick, line, price, grade, units, "
                "dollars, kickoff_utc) VALUES ('k', ?, 'NFL', 'e', 'A at H', 'total', 'under', 'Under 44', 44, -110, 'B', 0.5, 25, ?)",
                [kick - timedelta(hours=3), kick])
    pb.grade(con, {}, scorer=lambda s, e: None)
    assert con.execute("SELECT result FROM playbook_grades").fetchone()[0] == "V"


def test_backfill_regrades_old_prop_wins_at_the_limit():
    from engine.picks import playbook as pb
    con = _con()
    con.execute("INSERT INTO playbook_picks (pick_key, market, units, nominal_units, dont_bet_past) VALUES "
                "('k', 'prop', 0.5, 0.5, 'under 0.5 at +111 or better (a higher line is fine)')")
    con.execute("INSERT INTO playbook_grades (pick_key, result, profit_units, nominal_profit) VALUES ('k', 'W', 0.615, 0.615)")
    pb._backfill(con)
    assert con.execute("SELECT profit_units FROM playbook_grades").fetchone()[0] == pytest.approx(0.555)


def _prop_cancel(m_then, m_now):
    import duckdb
    from engine.picks import playbook as pb
    con = duckdb.connect()
    con.execute("CREATE TABLE prop_evals (ts_utc TIMESTAMP, sport VARCHAR, player_id VARCHAR, stat VARCHAR, home VARCHAR, away VARCHAR, "
                "start_utc VARCHAR, line DOUBLE, market_p_over DOUBLE)")
    kick = datetime(2026, 11, 25, 0, 0)
    con.execute("INSERT INTO prop_evals VALUES (?, 'NBA', 'p1', 'threes', 'Magic', 'Pistons', '2026-11-25T00:00:00Z', 1.5, ?)",
                [kick - timedelta(hours=2), m_now])
    row = {"sport": "NBA", "market": "prop", "pick_key": "prop|p1|threes|over|1.5|e1", "game": "Pistons at Magic", "kickoff_utc": kick,
           "first_seen_utc": kick - timedelta(hours=10), "market_line": m_then, "own_line": 0.40, "price": 182}
    return pb.cancel_reason(con, {"playbook": {"sports": {"NBA": {"weights": {"prop": 0.25}}}}}, row)


def test_prop_cancel_says_when_pinnacle_has_not_moved():
    # The Collins message on Nov 24 said "moved from 33% to 33%": the edge fell because the props weight changed, not Pinnacle.
    msg = _prop_cancel(0.33, 0.33)
    assert msg and "has not moved" in msg and "moved from" not in msg
    moved = _prop_cancel(0.36, 0.33)
    assert moved and "moved from 36% to 33%" in moved
