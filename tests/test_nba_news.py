from datetime import datetime, timezone

import duckdb

from engine.picks import agent, nba_news as n


def report(*rows):
    return {"injuries": [{"displayName": team, "injuries": [
        {"status": status, "shortComment": "c", "athlete": {"displayName": name, "links": [{"href": f"https://www.espn.com/nba/player/_/id/{pid}/x"}]}}
        for pid, team2, name, status in rows if team2 == team]} for team in {r[1] for r in rows}]}


def stats(*rows):
    return {"categories": [{"name": "general", "names": ["gamesPlayed", "avgMinutes", "avgRebounds"]},
                           {"name": "offensive", "names": ["avgPoints", "avgAssists"]}],
            "athletes": [{"athlete": {"id": pid, "displayName": name, "teamShortName": "LAL"},
                          "categories": [{"name": "general", "totals": [str(gp), str(mins), "5"]},
                                         {"name": "offensive", "totals": ["20", "4"]}]} for pid, name, gp, mins in rows]}


def test_parse_report_takes_athlete_id_from_links():
    r = n.parse_report(report(("123", "Los Angeles Lakers", "Star Guy", "Questionable")))
    assert r[0].key == "123" and r[0].team == "Los Angeles Lakers" and r[0].status == "Questionable"


def test_crossing_the_will_he_play_line():
    p = lambda s: n.Listed("1", "T", "N", s, "")
    assert n.Change(p("Out"), "Questionable", None).crosses()
    assert n.Change(p("Questionable"), "Doubtful", None).crosses()
    assert n.Change(p(n.OFF), "Out", None).crosses()           # back from injury
    assert not n.Change(p("Day-To-Day"), "Questionable", None).crosses()
    assert not n.Change(p("Out"), "Doubtful", None).crosses()


def test_matters_needs_minutes_and_games():
    imp = n.parse_impact(stats(("1", "Star", 20, 34.0), ("2", "Bench", 20, 12.0), ("3", "New", 2, 30.0)))
    p = n.Listed("x", "T", "N", "Out", "")
    assert n.Change(p, None, imp["1"]).matters(22)
    assert not n.Change(p, None, imp["2"]).matters(22)
    assert not n.Change(p, None, imp["3"]).matters(22)


def test_check_baseline_then_changes_including_players_who_drop_off():
    con = duckdb.connect()
    now = datetime(2026, 11, 22, 21, tzinfo=timezone.utc)
    first = n.parse_report(report(("1", "Los Angeles Lakers", "Star", "Questionable"), ("2", "Los Angeles Lakers", "Hurt", "Out")))
    ch, is_first = n.check(con, now, first, {})
    assert is_first and ch == []
    second = n.parse_report(report(("1", "Los Angeles Lakers", "Star", "Out")))
    ch, is_first = n.check(con, now, second, {}, persist=False)
    got = {(c.player.name, c.old_status, c.new_status) for c in ch}
    assert got == {("Star", "Questionable", "Out"), ("Hurt", "Out", n.OFF)}
    # persist=False left the stored report alone, so the same changes show again
    assert len(n.check(con, now, second, {})[0]) == 2
    assert n.check(con, now, second, {})[0] == []


def test_sport_cooldown_ignores_other_sports():
    con = duckdb.connect()
    con.execute(agent.SCHEMA)
    con.execute("INSERT INTO agent_runs VALUES ('2026-11-22 20:55', 'NFL: scheduled', true, '')")
    now = datetime(2026, 11, 22, 21, tzinfo=timezone.utc)
    assert not agent.cooled_down(con, now, 20)
    assert agent.cooled_down(con, now, 20, sport="NBA")


def test_watch_only_reads_just_after_the_scheduled_times():
    from datetime import datetime, timedelta, timezone
    from engine.picks.nba_news import in_window
    cfg = {"timezone_display": "America/Denver", "nba_watch": {"enabled": True, "run_times": ["10:00", "15:00", "17:00"]}}
    mt = lambda h, m: datetime(2026, 11, 23, tzinfo=timezone.utc) + timedelta(hours=h + 7, minutes=m)      # MST = UTC-7
    assert in_window(cfg, mt(10, 0)) and in_window(cfg, mt(15, 20)) and in_window(cfg, mt(17, 29))
    assert not in_window(cfg, mt(9, 59)) and not in_window(cfg, mt(10, 31)) and not in_window(cfg, mt(12, 0))
    assert not in_window({**cfg, "nba_watch": {**cfg["nba_watch"], "enabled": False}}, mt(10, 0))
