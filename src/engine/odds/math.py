"""Odds arithmetic. Everything here is pure and tested."""
from __future__ import annotations

import math


def american_to_decimal(american: float) -> float:
    """-110 -> 1.909 (total returned per $1 staked, stake included)."""
    if american == 0:
        raise ValueError("American odds cannot be 0")
    if american > 0:
        return 1 + american / 100
    return 1 + 100 / abs(american)


def implied_prob(american: float) -> float:
    """Win rate needed to break even at this price. -110 -> 0.5238."""
    return 1 / american_to_decimal(american)


def prob_to_american(p: float) -> int:
    if not 0 < p < 1:
        raise ValueError("probability must be between 0 and 1")
    if p >= 0.5:
        return -round(100 * p / (1 - p))
    return round(100 * (1 - p) / p)


def no_vig(price_a: float, price_b: float) -> tuple[float, float]:
    """Strip the book's cut from a two-sided market.

    Both sides' break-even rates add up to more than 100%; the excess is the
    vig. Scale both down in proportion so they add to exactly 100%.
    """
    pa, pb = implied_prob(price_a), implied_prob(price_b)
    total = pa + pb
    return pa / total, pb / total


def hold(price_a: float, price_b: float) -> float:
    """The book's cut on a two-sided market, as a share of money bet."""
    total = implied_prob(price_a) + implied_prob(price_b)
    return 1 - 1 / total


def ev_per_dollar(p_win: float, american: float) -> float:
    """Expected profit per $1 risked, given a true win probability."""
    return p_win * (american_to_decimal(american) - 1) - (1 - p_win)


def parlay_decimal(prices: list[float]) -> float:
    out = 1.0
    for p in prices:
        out *= american_to_decimal(p)
    return out


def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def win_prob_shift(points_better: float, sd: float) -> float:
    """Approximate change in win probability from having a better number.

    Final margins scatter around the line roughly like a bell curve with
    spread `sd`. Being `points_better` on the right side of the closing line
    wins the games that land in that gap. This ignores key numbers, so it
    understates a half point on 3 and overstates one on 5.
    """
    return _phi(points_better / sd) - 0.5


def breakeven_leg_rate(payout_american: float, legs: int) -> float:
    """Win rate each leg needs for an all-must-win ticket to break even."""
    return implied_prob(payout_american) ** (1 / legs)


def crosses_3_and_7(original_line: float, teaser_points: float) -> bool:
    """True when teasing a football side moves it through both 3 and 7.

    +1.5 teased 6.5 -> +8 crosses both. -8.5 teased 6.5 -> -2 crosses both.
    Landing exactly on 3 or 7 does not count as crossing it, and neither does
    a teaser that passes through zero (-5 teased 13 -> +8): points spent
    crossing zero are the least valuable ones.
    """
    lo, hi = original_line, original_line + teaser_points
    dog = 0 < lo < 3 and hi > 7
    fav = lo < -7 and -3 < hi < 0
    return dog or fav


def touches_key(original_line: float, bought_line: float, keys=(3, 7)) -> list[int]:
    """Key numbers a bought half point moves onto or off of."""
    a, b = sorted((abs(original_line), abs(bought_line)))
    return [k for k in keys if a <= k <= b]


def luck_range(bets: list[tuple[float, float]]) -> float:
    """Two-standard-deviation swing in dollars for a list of (risk, to_win) bets.

    Treats each bet as a fair coin weighted to its own price. This is how far
    results wander from zero by chance alone for someone with no edge.
    """
    var = 0.0
    for risk, win in bets:
        if risk <= 0 or win <= 0:
            continue
        p = risk / (risk + win)
        var += p * (1 - p) * (risk + win) ** 2
    return 2 * math.sqrt(var)
