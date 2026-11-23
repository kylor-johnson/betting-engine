"""Closing-line value as win chance (review 14, approved 2026-11-23).

Points are not worth the same everywhere: half a point on 3 in the NFL is worth far more than half a point in the NBA. So closing-line value
is also stored as win chance: the chance the bet wins at the number it was issued at, if Pinnacle's last line before kickoff is the fair line,
minus one half (pushes count half). +0.03 means the number you got was worth three percentage points of win chance against the close.
It uses the same landing tables as pricing and stale alerts (NFL and College from real results, NBA a bell curve). The price is left out on
purpose: this is a measure of the number, comparable across sports; whether it clears Wagerhouse's juice is a separate question.
"""
from __future__ import annotations


def chance(cfg: dict, sport: str, market: str, side: str, issued: float, close: float) -> float | None:
    """Win chance gained (+) or lost (-) against Pinnacle's close. None if the sport or market cannot be priced."""
    from engine import stale
    try:
        ls, lt = stale.landings(sport, cfg)
        land = ls if market == "spread" else lt if market == "total" else None
        if land is None:
            return None
        win, push, _ = land.probs(close, issued, side)
        return round(win + push / 2 - 0.5, 4)
    except (ValueError, KeyError):
        return None
