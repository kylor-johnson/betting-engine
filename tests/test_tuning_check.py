"""The Nov 24 tuning check (docs/research/25-tuning-check.md): one test per fix."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import duckdb
import pytest


def _cfg():
    from engine import config
    return config.load_config()


def _con():
    from engine.models import props
    from engine.picks import playbook as pb, teasers
    con = duckdb.connect()
    con.execute(pb.SCHEMA)
    con.execute(pb.ALERTS_SCHEMA)
    con.execute(teasers.SCHEMA)
    con.execute(props.SCHEMA)
    return con


# Gap 1: the NBA read schedule in the parity table comes from config, so it cannot go stale.
def test_parity_nba_news_cell_is_built_from_config():
    from engine import lanes
    cfg = _cfg()
    cell = dict(lanes.parity_rows(cfg))["News source"]["NBA"]
    assert "10am, 3pm, 5pm and 6:30pm" in cell
    assert "every 30 minutes in the 3 hours before any tip" in cell
    cfg["nba_watch"]["run_times"] = ["09:00", "19:15"]
    assert "watcher at 9am and 7:15pm" in dict(lanes.parity_rows(cfg))["News source"]["NBA"]


def test_watcher_docstring_names_all_four_times():
    from engine.picks import nba_news
    assert "18:30" in nba_news.__doc__ and "three times a day" not in nba_news.__doc__


# Gap 3: a rule change (the props weight) can never cancel a pick sent under the old weight, the FAIR_SINCE principle.
def _prop_row(con, weight):
    kick = datetime(2026, 11, 25, 0, 0)
    con.execute("INSERT INTO prop_evals (ts_utc, sport, player_id, stat, home, away, start_utc, line, market_p_over) "
                "VALUES (?, 'NBA', 'p1', 'fg3m', 'Magic', 'Pistons', '2026-11-25T00:00:00Z', 1.5, 0.33)", [kick - timedelta(hours=2)])
    # Collins, Nov 24: sent at weight 0.5 with Pinnacle 33% over and our model 47% (+4.6% edge); +182 needs 35.5%
    return {"sport": "NBA", "market": "prop", "pick_key": "prop|p1|fg3m|over|1.5|e1", "game": "Pistons at Magic", "kickoff_utc": kick,
            "first_seen_utc": kick - timedelta(hours=10), "market_line": 0.33, "own_line": 0.47, "price": 182, "blend_weight": weight}


def test_prop_cancel_uses_the_weight_it_was_sent_under():
    from engine.picks import playbook as pb
    cfg = {"playbook": {"sports": {"NBA": {"weights": {"prop": 0.25}}}}}
    con = _con()
    assert pb.cancel_reason(con, cfg, _prop_row(con, 0.5)) is None           # Pinnacle has not moved: no CANCELLED
    con = _con()
    assert pb.cancel_reason(con, cfg, _prop_row(con, None))                  # no stored weight: today's weight (the old behaviour)


def test_backfill_recovers_the_blend_weight_of_older_props():
    from engine.picks import playbook as pb
    con = _con()
    mkt, own, w, price = 0.33, 0.41, 0.5, 182
    edge = (mkt + w * (own - mkt)) - pb.chance_needed(price)
    con.execute("INSERT INTO playbook_picks (pick_key, market, side, price, edge, market_line, own_line) VALUES ('k', 'prop', 'over', ?, ?, ?, ?)",
                [price, edge, mkt, own])
    con.execute("INSERT INTO playbook_picks (pick_key, market, side, price, edge, market_line, own_line) VALUES ('u', 'prop', 'under', ?, ?, ?, ?)",
                [-120, (1 - (mkt + w * (own - mkt))) - pb.chance_needed(-120), mkt, own])
    pb._backfill(con)
    got = dict(con.execute("SELECT pick_key, blend_weight FROM playbook_picks").fetchall())
    assert got["k"] == pytest.approx(0.5) and got["u"] == pytest.approx(0.5)


# Gap 5: the missed-read alarm counts scheduled read hours, not a flat 20 hours.
def test_missed_read_hours_ignore_the_night_and_catch_a_dead_afternoon():
    from engine import poll
    cfg = {"timezone_display": "America/Denver", "read_hours": {"sunday": list(range(7, 22)), "other": list(range(7, 22))}}
    mt = timezone(timedelta(hours=-7))
    night = poll.missed_read_hours(cfg, datetime(2026, 11, 24, 21, 2, tzinfo=mt), datetime(2026, 11, 25, 7, 2, tzinfo=mt))
    assert night == 0
    assert poll.missed_read_hours(cfg, datetime(2026, 11, 24, 10, 2, tzinfo=mt), datetime(2026, 11, 24, 11, 2, tzinfo=mt)) == 0
    assert poll.missed_read_hours(cfg, datetime(2026, 11, 24, 10, 2, tzinfo=mt), datetime(2026, 11, 24, 13, 2, tzinfo=mt)) == 2
    assert _cfg()["missed_read_alert_hours"] == 2


# Gap 5: an unreadable stop is never reported as +0.0 units.
def test_down_units_raises_on_a_read_error_but_not_on_an_empty_database():
    from engine.picks import playbook as pb
    assert pb.down_units(duckdb.connect(), "NFL", {}) == 0.0                 # no tables yet: nothing graded
    con = _con()
    con.execute("DROP TABLE playbook_picks")
    con.execute("CREATE TABLE playbook_picks (pick_key VARCHAR)")            # wrong shape: a real read error
    with pytest.raises(duckdb.Error):
        pb.down_units(con, "NFL", {})


# Gap 5: CollegeFootballData down -> the cached copy, with a PROBLEM note, never a dead college slate.
def test_cfbd_falls_back_to_its_cache(tmp_path, monkeypatch):
    import json
    import urllib.request
    from engine.picks import sources
    (tmp_path / "cfbd_lines_2026.json").write_text(json.dumps([{"id": 1}]))
    (tmp_path / "cfbd_adv_2026.json").write_text(json.dumps([{"id": 2}]))
    import os
    old = datetime.now().timestamp() - 24 * 3600
    for f in tmp_path.iterdir():
        os.utime(f, (old, old))

    def down(*a, **k):
        raise urllib.error.URLError("down")
    monkeypatch.setattr(urllib.request, "urlopen", down)
    sources.CFBD_FALLBACKS.clear()
    assert sources.cfbd_lines(2026, "key", tmp_path, current=True) == [{"id": 1}]
    assert sources.cfbd_advanced(2026, "key", tmp_path, current=True) == [{"id": 2}]
    assert len(sources.CFBD_FALLBACKS) == 2 and "cached copy" in sources.CFBD_FALLBACKS[0]
    with pytest.raises(sources.SourceError):
        sources.cfbd_lines(2025, "key", tmp_path, current=True)              # no copy: still fails loudly


# Grid B1: D1b carries this read's disagreement, not the one frozen at first sight.
def test_candidates_keep_first_numbers_and_record_the_latest():
    from engine.picks import playbook as pb
    con = _con()
    kick = datetime(2026, 11, 30, 18, tzinfo=timezone.utc)
    c = {"market": "total", "side": "over", "event_id": "e", "game": "A at H", "line": 44.0, "price": -110, "grade": "C", "edge": 0.01,
         "own_line": 47.0, "market_line": 44.0, "kick": kick}
    t0 = datetime(2026, 11, 25, 15, tzinfo=timezone.utc)
    pb.log_candidates(con, "NFL", [c], t0)
    pb.log_candidates(con, "NFL", [{**c, "own_line": 46.0, "market_line": 45.5}], t0 + timedelta(hours=5))
    row = con.execute("SELECT own_value, market_value, last_own_value, last_market_value, last_seen_utc FROM playbook_candidates").fetchone()
    assert row[:4] == (47.0, 44.0, 46.0, 45.5) and row[4] == datetime(2026, 11, 25, 20)


# Grid B2: a fast read freezes teaser legs but never sends a ticket (a bet).
def test_fast_read_teaser_scan_sends_no_ticket(monkeypatch):
    from engine.picks import teasers
    monkeypatch.setattr(teasers, "tickets_to_send", lambda *a, **k: pytest.fail("a fast read built a ticket"))
    monkeypatch.setattr(teasers, "legs_from", lambda *a, **k: [])
    teasers.scan({"teasers": {"enabled": True}}, _con(), [], datetime(2026, 11, 25, tzinfo=timezone.utc), tickets=False)
    import inspect
    from engine import burst
    assert "tickets=False" in inspect.getsource(burst.run)


# Grid B3: the closing team total is this game's, never an earlier meeting of the same two teams.
def test_team_total_close_ignores_an_earlier_meeting():
    from engine.picks import playbook as pb
    con = duckdb.connect()
    con.execute("CREATE TABLE derivative_snapshots (ts_utc TIMESTAMP, source VARCHAR, sport VARCHAR, away VARCHAR, home VARCHAR, start_utc VARCHAR, "
                "market VARCHAR, period VARCHAR, description VARCHAR, line DOUBLE, price_a DOUBLE, price_b DOUBLE)")
    kick = datetime(2026, 12, 20, 0, 10)
    con.execute("INSERT INTO derivative_snapshots VALUES (?, 'Pinnacle', 'NBA', 'A', 'H', '2026-11-25T00:10:00Z', 'team_total', 'Game', 'home', "
                "110.5, -110, -110)", [datetime(2026, 11, 24, 23)])
    assert pb.team_total_close(con, {}, "NBA", "H", "A", "home", "over", 112.5, -110, kick) == (None, None, None)
    con.execute("INSERT INTO derivative_snapshots VALUES (?, 'Pinnacle', 'NBA', 'A', 'H', '2026-12-20T00:10:00Z', 'team_total', 'Game', 'home', "
                "113.5, -110, -110)", [kick - timedelta(hours=1)])
    assert pb.team_total_close(con, {}, "NBA", "H", "A", "home", "over", 112.5, -110, kick)[0] == 113.5


# Grid B4: the shown-only reason on the card comes from config.
def test_shown_only_reason_comes_from_config():
    from engine.picks import playbook as pb
    st = {**pb.settings(_cfg(), "NBA"), "shown_reason": "the NBA script cannot see who is injured"}
    assert "cannot see who is injured" in pb.shown_reason(st)


# Decision 0040 (replacing 0038 and 0036 item 2): every pick the model makes is staked and sent.
def test_every_model_pick_is_staked_decision_0040():
    from engine.picks import playbook as pb
    cfg = _cfg()
    for sport in ("NFL", "NBA", "College"):
        st = pb.settings(cfg, sport)
        assert st["full_game"] == "stake"
        c = {"grade": "B", "event_id": "e", "market": "side"}
        assert pb._paper_or_staked(_con(), st, c, 0.5, 12.5, "B pick", 25.0, full_game=True)[1] == 12.5
        if sport != "College":
            assert st["props"] and st["props_stake"] is True
            assert pb._paper_or_staked(_con(), st, {**c, "market": "prop"}, 0.5, 12.5, "B pick", 25.0, full_game=False)[1] == 12.5


# Decision 0039: one full read 8-25 minutes before each NFL and college kickoff.
def test_closing_read_before_each_nfl_and_college_kickoff():
    from engine import poll
    cfg = {"closing_read": {"enabled": True, "sports": ["NFL", "College"], "minutes_before": [25, 8]}}
    con = duckdb.connect()
    con.execute("CREATE TABLE line_snapshots (sport VARCHAR, start_utc TIMESTAMP)")
    kick = datetime(2026, 11, 27, 1, 15, tzinfo=timezone.utc)                     # Thu 6:15pm MT
    con.execute("INSERT INTO line_snapshots VALUES ('NFL', ?), ('NBA', ?)", [kick.replace(tzinfo=None), datetime(2026, 11, 27, 1, 5)])
    hourly = kick - timedelta(minutes=43)                                         # the 5:32pm read
    assert poll.closing_due(con, cfg, kick - timedelta(minutes=30), hourly) is None       # too early
    assert poll.closing_due(con, cfg, kick - timedelta(minutes=20), hourly) == kick       # 5:55pm: due
    assert poll.closing_due(con, cfg, kick - timedelta(minutes=10), kick - timedelta(minutes=19)) is None   # already done
    assert poll.closing_due(con, cfg, kick - timedelta(minutes=5), hourly) is None        # too late to bet on it
    cfg["closing_read"]["sports"] = ["College"]
    assert poll.closing_due(con, cfg, kick - timedelta(minutes=20), hourly) is None       # NBA and unlisted sports never
    from engine import lanes
    assert "closing read 8-25 minutes before each kickoff" in dict(lanes.parity_rows(_cfg()))["News source"]["NFL"]


def test_books_short_warriors_name_maps_to_gs():
    """Pinnacle, Wagerhouse and DraftKings write "Golden St Warriors"; without the alias the NBA model and props skipped every Warriors game."""
    from engine.models.nba_props import NAME_TO_ABBR
    assert NAME_TO_ABBR["Golden St Warriors"] == NAME_TO_ABBR["Golden State Warriors"] == "GS"
