import math

import pytest

from engine.odds.math import (american_to_decimal, breakeven_leg_rate, crosses_3_and_7,
                              ev_per_dollar, hold, implied_prob, luck_range, no_vig,
                              parlay_decimal, prob_to_american, touches_key, win_prob_shift)


def test_american_to_decimal():
    assert american_to_decimal(-110) == pytest.approx(1.9091, abs=1e-4)
    assert american_to_decimal(150) == 2.5
    assert american_to_decimal(-500) == pytest.approx(1.2)
    with pytest.raises(ValueError):
        american_to_decimal(0)


def test_breakeven_rates():
    assert implied_prob(-110) == pytest.approx(0.5238, abs=1e-4)
    assert implied_prob(-500) == pytest.approx(0.8333, abs=1e-4)
    assert implied_prob(100) == 0.5


def test_no_vig_sums_to_one_and_is_fair_at_even_prices():
    a, b = no_vig(-110, -110)
    assert a == pytest.approx(0.5) and b == pytest.approx(0.5)
    a, b = no_vig(-400, 320)
    assert a + b == pytest.approx(1.0)
    assert a == pytest.approx(0.8 / (0.8 + 1 / 4.2), abs=1e-6)


def test_hold():
    assert hold(-110, -110) == pytest.approx(0.0455, abs=1e-4)
    assert hold(-400, 320) == pytest.approx(0.0367, abs=1e-3)


def test_prob_to_american_round_trip():
    assert prob_to_american(0.8) == -400
    assert prob_to_american(0.25) == 300


def test_ev():
    assert ev_per_dollar(0.5238095, -110) == pytest.approx(0, abs=1e-6)
    assert ev_per_dollar(0.80, -500) == pytest.approx(-0.04)


def test_parlay_of_three_minus_400s_loses_about_ten_percent():
    fair = no_vig(-400, 320)[0]
    assert fair ** 3 * parlay_decimal([-400] * 3) - 1 == pytest.approx(-0.106, abs=0.005)


def test_teaser_breakeven_per_leg():
    assert breakeven_leg_rate(-120, 2) == pytest.approx(0.7385, abs=1e-4)
    assert breakeven_leg_rate(-140, 4) == pytest.approx(0.8739, abs=1e-4)
    assert breakeven_leg_rate(-130, 3) == pytest.approx(0.8268, abs=1e-4)
    assert breakeven_leg_rate(140, 3) == pytest.approx(0.7469, abs=1e-4)


@pytest.mark.parametrize("line,pts,expected", [
    (1.5, 6.5, True), (2.5, 6.5, True), (1, 6.5, True), (3, 6.5, False),
    (-8.5, 6.5, True), (-7.5, 6.5, True), (-9, 6.5, True), (-9.5, 6.5, False),
    (-7, 6.5, False), (-8.5, 6, True), (-9, 6, False), (4, 13, False), (-5, 13, False),
    (2.5, 6, True), (0.5, 6.5, False),
])
def test_crosses_3_and_7(line, pts, expected):
    assert crosses_3_and_7(line, pts) is expected


def test_touches_key():
    assert touches_key(-3, -2.5) == [3]
    assert touches_key(2.5, 3) == [3]
    assert touches_key(7, 7.5) == [7]
    assert touches_key(4, 4.5) == []
    assert touches_key(17, 18.5) == []


def test_win_prob_shift():
    assert win_prob_shift(0, 13.3) == 0
    assert win_prob_shift(1, 13.3) == pytest.approx(0.030, abs=0.002)
    assert win_prob_shift(-1, 13.3) == pytest.approx(-0.030, abs=0.002)


def test_luck_range():
    # 100 bets risking 110 to win 100: sd of one bet = 105, two sd of the sum = 2100
    assert luck_range([(110, 100)] * 100) == pytest.approx(2 * math.sqrt(100) * 104.88, rel=0.01)
    assert luck_range([]) == 0
