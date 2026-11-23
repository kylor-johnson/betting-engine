from datetime import datetime, timezone

from engine.models import openers


def test_cutoff_is_sunday_before_week():
    thu = datetime(2026, 11, 27, 1, 15, tzinfo=timezone.utc)          # Thursday night game, Eastern Wed/Thu
    cut = openers.cutoff("NFL", thu).astimezone(openers.EASTERN)
    assert cut.weekday() == 6 and cut.hour == 20 and cut.date().isoformat() == "2026-11-22"
    sat = datetime(2026, 11, 28, 17, 0, tzinfo=timezone.utc)
    cut = openers.cutoff("College", sat).astimezone(openers.EASTERN)
    assert cut.weekday() == 6 and cut.hour == 6 and cut.date().isoformat() == "2026-11-22"


def test_cutoff_never_on_game_day():
    sun = datetime(2026, 11, 22, 18, 0, tzinfo=timezone.utc)
    assert openers.cutoff("NFL", sun) < sun
    assert openers.cutoff("NFL", sun).astimezone(openers.EASTERN).date().isoformat() == "2026-11-15"


def _g(o, c, m, actual):
    return openers.Game("NFL", 2024, 5, datetime(2024, 10, 6, tzinfo=timezone.utc), "A", "B", False,
                        o, c, None, None, actual, 40.0, model_margin=m)


def test_fit_share_and_grading():
    games = [_g(0.0, 1.0, 2.0, 3.0), _g(0.0, -1.0, -2.0, 3.0)]
    assert openers.fit_share(games, "spread") == 0.5
    assert openers.grade_open(games[0], "spread", 1) == 1.0
    assert openers.grade_open(games[1], "spread", -1) == -1.0
    assert openers.grade_open(_g(3.0, 3.0, 4.0, 3.0), "spread", 1) == 0.0
