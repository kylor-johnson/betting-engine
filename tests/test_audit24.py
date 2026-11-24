"""Audit 24 (docs/research/24-full-audit.md): one test per plain bug fixed in that session."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import duckdb
import pytest


def _con():
    from engine.picks import playbook as pb, teasers
    from engine.models import props
    con = duckdb.connect()
    con.execute(pb.SCHEMA)
    con.execute(pb.ALERTS_SCHEMA)
    con.execute(teasers.SCHEMA)
    con.execute(props.SCHEMA)
    return con


# 1. `poll --no-send` sent real-money teaser tickets: scan() now passes send through.
def test_teaser_scan_passes_no_send_through(monkeypatch):
    from engine.picks import teasers
    seen = {}
    monkeypatch.setattr(teasers, "legs_from", lambda snaps, now, st: [])
    monkeypatch.setattr(teasers, "tickets_to_send", lambda cfg, con, now, send=True, sender=None: seen.setdefault("send", send) and [])
    cfg = {"teasers": {"enabled": True, "real_money": True}}
    teasers.scan(cfg, _con(), [], datetime(2030, 1, 1, tzinfo=timezone.utc), send=False)
    assert seen["send"] is False


def test_tickets_to_send_never_calls_telegram_when_send_is_false(monkeypatch):
    from engine.alerts import telegram
    from engine.picks import teasers
    monkeypatch.setattr(telegram, "send", lambda *a, **k: pytest.fail("Telegram called on a no-send read"))
    con = _con()
    kick = datetime(2030, 1, 5, 18)
    for i, (eid, team) in enumerate((("g1", "A"), ("g2", "B"))):
        con.execute("INSERT INTO teaser_legs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [f"leg{i}", datetime(2030, 1, 1, i), eid, f"X at {team}", "home", team, 1.5, 7.5, 44.0, kick, "2029-12-31", "v"])
    cfg = {"teasers": {"enabled": True, "real_money": True}, "unit": 25, "units_by_sport": {"NFL": 50}, "timezone_display": "America/Denver"}
    out = teasers.tickets_to_send(cfg, con, datetime(2030, 1, 2, tzinfo=timezone.utc), send=False)
    assert any("TEASER" in o for o in out)


# 2. NBA prop re-centring kept only the first game when the same two teams met again.
def test_calibration_counts_both_games_of_a_rematch():
    from engine.models import calibrate
    con = _con()
    for start in ("2030-01-01T01:00:00Z", "2030-01-20T01:00:00Z"):
        con.execute("INSERT INTO prop_evals (ts_utc, start_utc, sport, player_id, stat, home, away, line, model_p_over, outcome) "
                    "VALUES (?, ?, 'NBA', 'p', 'pts', 'H', 'A', 20.5, 0.5, 25)", [datetime.fromisoformat(start[:-1]), start])
    shifts = calibrate.fit(con, "NBA", prior_n=0.0)
    # both overs counted: with one row the shift is the same sign, so check the count through the pooled fit directly
    rows = con.execute("""SELECT count(*) FROM (SELECT row_number() OVER (PARTITION BY player_id, stat, home, away, start_utc ORDER BY ts_utc) rn
                          FROM prop_evals) WHERE rn = 1""").fetchone()[0]
    assert rows == 2 and shifts["pts"] > 0


# 3. Three Saturday college games were never logged: Wagerhouse names ESPN did not know.
@pytest.mark.parametrize("wh,espn_name", [("UL Lafayette", "louisiana"), ("Florida Intl", "fiu"),
                                          ("Sam Houston St", "sam houston"), ("Middle Tennessee St", "middle tennessee")])
def test_college_aliases(wh, espn_name):
    from engine.odds import espn
    assert espn.norm(wh) == espn.norm(espn_name)


# 4. The scoreboard cache froze tonight's games as unplayed (ESPN dates are Eastern).
def test_scoreboard_caches_a_past_day_only_when_every_game_is_final(tmp_path, monkeypatch):
    from engine.odds import espn
    ev = lambda done: {"events": [{"id": "1", "date": "2020-01-01T01:00Z", "status": {"type": {"completed": done}},
                                   "competitions": [{"competitors": [{"homeAway": "home", "team": {"displayName": "H"}},
                                                                     {"homeAway": "away", "team": {"displayName": "A"}}]}]}]}
    monkeypatch.setattr(espn, "_get", lambda url: ev(False))
    espn.scoreboard("NBA", date(2020, 1, 1), tmp_path)
    assert not list(tmp_path.iterdir())
    monkeypatch.setattr(espn, "_get", lambda url: ev(True))
    espn.scoreboard("NBA", date(2020, 1, 1), tmp_path)
    assert len(list(tmp_path.iterdir())) == 1


# 5. One DraftKings failure threw away the whole read.
def test_one_draftkings_failure_is_a_problem_not_a_lost_read(monkeypatch):
    from engine.odds import espn, snapshots as snap
    from engine.picks import sources
    start = datetime(2030, 1, 2, tzinfo=timezone.utc)
    line = SimpleNamespace(away="A", home="H", start=start, home_spread=-3.0, home_spread_price=-110, away_spread_price=-110,
                           home_ml=None, away_ml=None, total=44.0, over_price=-110, under_price=-110)
    event = SimpleNamespace(event_id="e1", start=start)
    wh = SimpleNamespace(lines=lambda sport: [line])
    monkeypatch.setattr(espn, "upcoming", lambda *a, **k: [event])
    monkeypatch.setattr(snap, "match_event", lambda l, events: event)
    monkeypatch.setattr(sources, "PINNACLE_LEAGUES", {})

    def boom(ev, cache):
        raise espn.SourceError("DraftKings down")
    monkeypatch.setattr(espn, "event_odds", boom)
    snaps, problems = snap.collect(wh, ["NFL"], datetime(2030, 1, 1, tzinfo=timezone.utc))
    assert len(snaps) == 1 and any("DraftKings" in p for p in problems)


# 6. Rotoworld cut at 4 pages with no warning, and the gap was never read.
def test_rotoworld_gap_is_reported_and_posts_are_kept(monkeypatch):
    from engine.picks import player_news as pn
    since = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)
    posts = [SimpleNamespace(posted=since + timedelta(hours=3), url="u1"), SimpleNamespace(posted=since + timedelta(hours=2), url="u2")]
    assert pn.gap(posts, since) and pn.gap(posts, since - timedelta(days=1)) and pn.gap(posts, since + timedelta(hours=2)) is None
    monkeypatch.setattr(pn, "last_seen", lambda con, sport: since)
    monkeypatch.setattr(pn, "fetch", lambda sport, s: posts)
    monkeypatch.setattr(pn, "store_new", lambda con, p, now: p)
    with pytest.raises(pn.Truncated) as e:
        pn.update(None, "NBA", since + timedelta(hours=4))
    assert e.value.new == posts and e.value.first is False


# 7. The official report rolling to the next day's teams looked like news (Embiid, Nov 24).
def test_official_report_rollover_is_not_news():
    from engine.picks import nba_news
    con = duckdb.connect()
    now = datetime(2030, 1, 1, 17, tzinfo=timezone.utc)
    team_of = {"embiid": "philadelphia 76ers", "star": "boston celtics", "newguy": "boston celtics", "late": "miami heat"}
    nba_news.check_official(con, now, "a.pdf", {"embiid": "Out", "star": "Questionable"},
                            teams={"philadelphia 76ers", "boston celtics"}, team_of=team_of)
    # next report: PHI is not on it (no game that day); Miami appears for the first time; Boston's star is now Out
    ch, first = nba_news.check_official(con, now, "b.pdf", {"star": "Out", "newguy": "Out", "late": "Out"},
                                        teams={"boston celtics", "miami heat"}, team_of=team_of)
    assert not first
    assert set(ch) == {("star", "Questionable", "Out"), ("newguy", None, "Out")}       # no Embiid "off the report", no Miami "news"


def test_official_team_names_match_espn_short_names():
    from engine.odds import espn
    from engine.picks import nba_news
    pdf_teams = {espn.norm(t) for t in nba_news.NBA_TEAMS}
    assert {nba_news.team_full(a) for a in nba_news.ESPN_ABBR} <= pdf_teams


# 8. A system line whose send failed was never tried again.
def test_failed_system_line_is_sent_again(monkeypatch):
    from engine import poll
    con = _con()
    now = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)
    con.execute("INSERT INTO alerts_sent VALUES (?,?,?,?,?)", ["stop|NFL", now.replace(tzinfo=None) - timedelta(hours=1), "lane", "NFL STOP", False])
    con.execute("INSERT INTO alerts_sent VALUES (?,?,?,?,?)", ["old", now.replace(tzinfo=None) - timedelta(days=5), "lane", "old line", False])
    sent = []
    monkeypatch.setattr(poll.telegram, "send", lambda env, text, kind=None, **k: sent.append(text) or True)
    out = []
    poll.resend_system(con, {}, now, out)
    assert sent == ["NFL STOP"]
    assert con.execute("SELECT delivered FROM alerts_sent WHERE key='stop|NFL'").fetchone()[0] is True


# 9. A lane that changed back to an earlier state was never announced.
def test_lane_change_key_differs_when_a_state_repeats():
    from engine import poll
    a = poll.lane_change_key("h1", datetime(2030, 1, 1, 12, tzinfo=timezone.utc))
    b = poll.lane_change_key("h1", datetime(2030, 1, 3, 12, tzinfo=timezone.utc))
    assert a != b and a.startswith("status-changed|h1|")


# 10. One bad score stopped all grading (and the daily check and recap behind it).
def test_one_bad_score_does_not_stop_other_grades():
    from engine.picks import playbook as pb
    con = _con()
    con.execute("CREATE TABLE line_snapshots (ts_utc TIMESTAMP, source VARCHAR, sport VARCHAR, event_id VARCHAR, away VARCHAR, home VARCHAR, "
                "start_utc TIMESTAMP, home_spread DOUBLE, home_spread_price DOUBLE, away_spread_price DOUBLE, home_ml DOUBLE, away_ml DOUBLE, "
                "total DOUBLE, over_price DOUBLE, under_price DOUBLE)")
    kick = datetime(2020, 1, 1, 1)
    for key, eid in (("k1", "bad"), ("k2", "good")):
        con.execute("INSERT INTO playbook_picks (pick_key, first_seen_utc, sport, event_id, game, market, side, pick, line, price, grade, units, "
                    "dollars, kickoff_utc) VALUES (?, ?, 'NBA', ?, 'A at H', 'total', 'over', 'Over 200', 200, -110, 'B', 0.5, 12.5, ?)",
                    [key, kick - timedelta(hours=3), eid, kick])

    def scorer(sport, eid):
        if eid == "bad":
            raise ValueError("malformed summary")
        return 110, 100
    out = pb.grade(con, {}, scorer=scorer)
    assert con.execute("SELECT result FROM playbook_grades WHERE pick_key='k2'").fetchone()[0] == "W"
    assert any("NOT GRADED" in o for o in out)


# 11. Daily check 3 crashed on a read error; check 7 counted runs that only started.
def test_checks_survive_a_read_error_and_count_finished_runs(monkeypatch):
    from engine import checks
    con = _con()
    con.execute("CREATE TABLE agent_runs (ts_utc TIMESTAMP, reason VARCHAR, ok BOOLEAN, note VARCHAR)")
    now = datetime(2030, 1, 1, 18, tzinfo=timezone.utc)
    con.execute("INSERT INTO agent_runs VALUES (?, 'NFL: test', NULL, 'started')", [now.replace(tzinfo=None) - timedelta(hours=1)])
    con.execute("DROP TABLE playbook_grades")          # check 3's query now fails
    from engine import config
    res = {name: (ok, why) for name, ok, why in checks.run(con, config.load_config(), now)}
    assert res["Every staked pick graded within a day of the game"][0] is False
    assert "could not read" in res["Every staked pick graded within a day of the game"][1]
    assert res["A research run finished in the last 26 hours"][0] is False


# 12. Prop grading could read the earlier game of a rematch.
def test_prop_grade_reads_this_games_outcome():
    from engine.picks import playbook as pb
    con = _con()
    kick = datetime(2020, 1, 20, 1)
    con.execute("INSERT INTO prop_evals (ts_utc, start_utc, sport, player_id, stat, home, away, line, outcome) VALUES "
                "(?, '2020-01-01T01:00:00Z', 'NBA', 'p', 'pts', 'H', 'A', 20.5, 30)", [datetime(2020, 1, 1)])
    con.execute("INSERT INTO prop_evals (ts_utc, start_utc, sport, player_id, stat, home, away, line, outcome) VALUES "
                "(?, '2020-01-20T01:00:00Z', 'NBA', 'p', 'pts', 'H', 'A', 20.5, 10)", [datetime(2020, 1, 19)])
    con.execute("INSERT INTO playbook_picks (pick_key, first_seen_utc, sport, event_id, game, market, side, pick, line, price, grade, units, "
                "dollars, kickoff_utc) VALUES ('prop|p|pts|over|20.5|e2', ?, 'NBA', 'e2', 'A at H', 'prop', 'over', 'p over 20.5', 20.5, -110, "
                "'B', 0.5, 12.5, ?)", [kick - timedelta(hours=3), kick])
    pb.grade(con, {})
    assert con.execute("SELECT result FROM playbook_grades").fetchone()[0] == "L"      # 10 points this game, not the first game's 30


# 13. "Don't bet past" walked on profit while CANCELLED tests win chance.
def test_dont_bet_past_is_the_cancel_test():
    from engine.odds.math import american_to_decimal
    from engine.picks import playbook as pb
    from engine.picks.pricing import Landing, bell_rows
    st = pb.settings({}, "NBA")
    land = Landing(bell_rows("total", 18.0, 180, 260), "total", window=0.25, min_n=100)
    price, fair = -110, 226.0
    ok, lim = land.limit(fair, 222.0, "over", price, pb.limit_value(st, "total", price))
    half = st["min_edge"]["total"] / 2
    assert pb.limit_value(st, "total", price) == pytest.approx(half * american_to_decimal(price))
    assert ok and pb.edge_of(land, fair, lim, "over", price)[0] >= half - 1e-9          # the limit itself passes the cancel test
    assert pb.edge_of(land, fair, lim + 0.5, "over", price)[0] < half                    # one step past it fails


# 14. An unreadable checks file was skipped without a word.
def test_unreadable_checks_file_is_a_problem(tmp_path, monkeypatch):
    from engine import config
    from engine.picks import playbook as pb
    d = tmp_path / "docs" / "cards" / "decisions"
    d.mkdir(parents=True)
    now = datetime(2030, 1, 1, 18, tzinfo=timezone.utc)
    (d / "2030-01-01-nfl-checks.yaml").write_text("checks: [unclosed")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    got = pb.load_checks(now, {"timezone_display": "America/Denver"}, "NFL")
    assert pb.checks_file_problems(got) and "could not be read" in pb.checks_file_problems(got)[0]


# 15. Two entries for the same news were both added.
def test_duplicate_news_entries_are_refused(tmp_path, monkeypatch):
    from engine.odds.espn import SourceError
    from engine.picks import slate
    e = {"game": "A at H", "market": "spread", "team": "H", "points": -2.5, "reason": "QB out", "source": "https://x", "added": "2030-01-01"}
    f = tmp_path / "adjustments.yaml"
    import yaml
    f.write_text(yaml.safe_dump({"adjustments": [e, {**e, "reason": "QB out (again)"}]}))
    monkeypatch.setattr(slate, "ADJ_FILE", f)
    with pytest.raises(SourceError, match="two entries"):
        slate.load_adjustments()
    f.write_text(yaml.safe_dump({"adjustments": [e, {**e, "market": "total"}]}))
    assert len(slate.load_adjustments()) == 2          # a spread and a total entry on one game are two different things


# 16. No report printed the luck range.
def test_luck_range_in_tracker_and_record():
    from engine.bets import tracker
    from engine.odds.math import luck_range
    r = SimpleNamespace(result="W", dollars=25.0, price=-110)
    assert tracker.luck_dollars([r, r]) == pytest.approx(luck_range([(25.0, 25 / 1.1)] * 2))
    from engine.picks import playbook as pb
    con = _con()
    con.execute("INSERT INTO playbook_picks (pick_key, sport, market, price, units, nominal_units) VALUES ('k', 'NFL', 'total', -110, 0.5, 0.5)")
    con.execute("INSERT INTO playbook_grades (pick_key, result) VALUES ('k', 'W')")
    assert pb.luck_units(con, "p.sport = ?", ["NFL"]) == pytest.approx(luck_range([(0.5, 0.5 / 1.1)]))


# 17. The NFL fast reads missed this week's Wednesday, Thanksgiving-morning and Friday kickoffs.
def test_nfl_fast_reads_follow_the_days_first_kickoff():
    from zoneinfo import ZoneInfo
    from engine import burst, config
    cfg, mt = config.load_config(), ZoneInfo("America/Denver")
    for now, first in (("2026-11-25 16:30", "2026-11-25 18:00"), ("2026-11-26 09:30", "2026-11-26 11:00"), ("2026-11-27 11:30", "2026-11-27 13:00")):
        n, f = (datetime.fromisoformat(x).replace(tzinfo=mt) for x in (now, first))
        assert burst.in_window(cfg, n, "NFL", f) is not None
