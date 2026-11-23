from datetime import datetime, timedelta

import pytest

from engine.reports import wagerhouse_edge as we

T0 = datetime(2026, 11, 22, 12, 0)


def series(rows):
    return [(T0 + timedelta(hours=i), w, p) for i, (w, p) in enumerate(rows)]


def test_a_persistent_half_point_offset_is_not_slowness():
    # Wagerhouse always sits 0.5 off; Pinnacle moves -2.5 -> -3.5 and Wagerhouse follows one read later
    s = series([(-3.0, -2.5), (-3.0, -3.5), (-4.0, -3.5), (-4.0, -3.5)])
    out = we.lags(s)
    assert len(out) == 1 and out[0]["kind"] == "followed" and out[0]["hours"] == pytest.approx(1.0)


def test_never_following_is_reported_as_not_yet():
    out = we.lags(series([(-3, -3), (-3, -4), (-3, -4), (-3, -4)]))
    assert out[0]["kind"] == "not yet"


def test_wagerhouse_moving_first_is_already_there():
    out = we.lags(series([(-3, -3), (-4, -3), (-4, -4)]))
    assert out[0]["kind"] == "already there"


def test_side_value_pays_for_juice_and_rewards_a_better_number():
    sl = we.NORMAL_PEAK / 12
    # same number, Wagerhouse -110/-110 against Pinnacle -105/-105: both sides lose to the extra juice
    v = we.side_value("spread", 0, 0.0, (-110, -110), (-105, -105), sl)
    assert v == pytest.approx(0.5 * 0.909 - 0.5, abs=1e-3) and v < 0
    # half a point better for the home side is worth about slope * 0.5 more
    better = we.side_value("spread", 0, 0.5, (-110, -110), (-105, -105), sl)
    assert better - v == pytest.approx(sl * 0.5 * 1.909, abs=1e-3)


def test_sides_and_clv_signs():
    # home +3 at Wagerhouse against Pinnacle +2.5: home side gets half a point better; away side half a point worse
    s = dict((n, a) for n, a, _ in we.sides("spread", 3.0, 2.5))
    assert s == {"home": 0.5, "away": -0.5}
    t = dict((n, a) for n, a, _ in we.sides("total", 45.0, 44.5))
    assert t == {"over": -0.5, "under": 0.5}
    assert we.clv_points("spread", "home", 3.0, 2.0) == 1.0 and we.clv_points("total", "over", 44.5, 45.5) == 1.0


def test_close_must_be_near_kickoff():
    kick = T0 + timedelta(hours=3)
    assert we.close_line([(T0 + timedelta(hours=2, minutes=10), 3.0)], kick) == 3.0
    assert we.close_line([(T0, 3.0)], kick) is None
