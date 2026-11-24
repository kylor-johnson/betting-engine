"""Decision 0034: bowl-season extra runs, college openers on paper, college context blocks."""
from datetime import datetime, timezone

from engine import poll
from engine.models import college_context
from engine.picks import college_openers as co

CFG = {"timezone_display": "America/Denver",
       "agent": {"extra_runs": [{"sport": "College", "from": "2026-12-14", "to": "2027-01-12", "times": ["12:15", "16:15"]}]}}


def test_extra_slot_fires_inside_window_and_half_hour():
    now = datetime(2026, 12, 20, 19, 30, tzinfo=timezone.utc)          # 12:30 MT
    (sport, slot), = poll.extra_slots(CFG, now)
    assert sport == "College" and slot == datetime(2026, 12, 20, 19, 15, tzinfo=timezone.utc)


def test_extra_slot_quiet_outside_window_or_time():
    assert poll.extra_slots(CFG, datetime(2026, 12, 1, 19, 30, tzinfo=timezone.utc)) == []    # before Dec 14
    assert poll.extra_slots(CFG, datetime(2026, 12, 20, 20, 0, tzinfo=timezone.utc)) == []    # 1:00 MT, 45 min after the slot
    assert poll.extra_slots({"agent": {}, "timezone_display": "America/Denver"}, datetime(2026, 12, 20, 19, 30, tzinfo=timezone.utc)) == []


ST = co.settings({"models": {"college_openers": {"enabled": True}}})


def test_picks_for_side_and_total():
    first = ("9", "Away U", "Home U", datetime(2026, 12, 1), -3.0, 50.0, datetime(2026, 11, 29))
    picks = co.picks_for(first, own_margin=7.0, own_total=45.0, st=ST)      # we say home by 7 vs -3 (gap 4); total 45 vs 50 (gap 5)
    assert {(p["market"], p["side"]) for p in picks} == {("side", "home"), ("total", "under")}
    assert co.picks_for(first, own_margin=4.0, own_total=52.0, st=ST) == []  # gaps 1 and 2: nothing


def test_grade_side_move_and_result():
    # bet home at -3; close -5 (moved 2 toward home); home won by 4: covers -3
    assert co.grade_one("side", "home", -3.0, -5.0, 24, 20) == (2.0, "W")
    # bet away at home -3 (away +3); close -2 moved 1 toward away; home won by 3: push
    assert co.grade_one("side", "away", -3.0, -2.0, 23, 20) == (1.0, "P")


def test_grade_total_move_and_result():
    assert co.grade_one("total", "under", 50.0, 48.5, 20, 21) == (1.5, "W")
    assert co.grade_one("total", "over", 50.0, None, 30, 21) == (None, "W")


def _game(gid, week, home, away, hs, as_):
    return {"id": gid, "season": 2026, "week": week, "startDate": f"2026-09-{week:02d}", "homeTeamId": home, "awayTeamId": away,
            "homeTeam": f"T{home}", "awayTeam": f"T{away}", "homeClassification": "fbs", "awayClassification": "fbs",
            "homeScore": hs, "awayScore": as_}


def test_context_blocks_rank_and_luck():
    games, adv = [], {}
    for wk in (1, 2, 3):
        games.append(_game(wk, wk, 1, 2, 35, 10))
        adv[(str(wk), "T1")] = {"oppa": 0.4, "dppa": -0.1, "osr": 0.5, "dsr": 0.35, "opl": 70.0, "dpl": 60.0}
        adv[(str(wk), "T2")] = {"oppa": -0.1, "dppa": 0.4, "osr": 0.35, "dsr": 0.5, "opl": 60.0, "dpl": 70.0}
    out = college_context.season_blocks(games, adv, 2026)
    assert out["1"]["matchup"]["offense"]["ppa_per_play"]["rank"] == 1
    assert out["2"]["matchup"]["defense"]["ppa_per_play_allowed"]["rank"] == 2
    assert out["1"]["luck"]["points_per_game"] == 35.0
