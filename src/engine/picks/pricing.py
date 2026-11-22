"""Turn "my number is better than the fair number" into a win probability,
using how real games actually landed instead of a bell curve.

For a fair line f, take past games whose closing line was close to f and count
how often the result landed on each exact margin. Moving from f to a better
number m wins every game that landed in between (and half of those that landed
exactly on an end point). That is why half a point through 3 is worth far more
than half a point through 5.
"""
from __future__ import annotations

from collections import Counter

from engine.odds.math import american_to_decimal


class Landing:
    """Empirical landing frequencies. `rows` are (closing_line, outcome) pairs.

    Spreads: closing_line = home spread (negative = home favored), outcome = home margin,
             and the home side covers when outcome > -line.
    Totals:  closing_line = total, outcome = points scored, over wins when outcome > line.
    """

    def __init__(self, rows: list[tuple[float, float]], kind: str, window: float, min_n: int = 400):
        if kind not in ("spread", "total"):
            raise ValueError(kind)
        self.rows, self.kind, self.window, self.min_n = rows, kind, window, min_n
        self._cache: dict = {}

    def _pmf(self, fair: float) -> tuple[dict[float, float], int]:
        key = round(fair * 2) / 2
        if key in self._cache:
            return self._cache[key]
        w = self.window
        sel = [o for l, o in self.rows if abs(l - key) <= w]
        while len(sel) < self.min_n and w < 12:
            w += 1
            sel = [o for l, o in self.rows if abs(l - key) <= w]
        if len(sel) < 100:
            raise ValueError(f"too few past games near a line of {fair}")
        # Use the real landing spots of games with similar lines, so 3, 7 and 10 keep their weight.
        # Only the share landing BETWEEN the fair line and the bet line is ever used.
        vals = sel
        c = Counter(round(v * 2) / 2 for v in vals)
        n = sum(c.values())
        pmf = {k: v / n for k, v in c.items()}
        self._cache[key] = (pmf, n)
        return pmf, n

    def _w(self, pmf: dict, line: float) -> float:
        """Share of landings that win at `line`, pushes counted half."""
        thr = -line if self.kind == "spread" else line
        return sum(p for k, p in pmf.items() if k > thr) + 0.5 * pmf.get(thr, 0.0)

    def probs(self, fair: float, line: float, side: str) -> tuple[float, float, float]:
        """(win, push, lose) for a bet at `line` when the fair line is `fair`.

        side: 'home' / 'away' for spreads (line is always the HOME spread), 'over' / 'under' for totals.
        """
        pmf, _ = self._pmf(fair)
        fair_r = round(fair * 2) / 2
        w = 0.5 + self._w(pmf, line) - self._w(pmf, fair_r)
        # the fair line is rarely an exact half point: credit the leftover fraction at the local rate
        frac = (fair_r - fair) * self.slope(fair)
        w += frac if self.kind == "spread" else -frac
        thr = -line if self.kind == "spread" else line
        push = pmf.get(thr, 0.0)
        win_first = min(max(w - push / 2, 0.0), 1.0)       # home covers, or over wins
        lose_first = min(max(1 - win_first - push, 0.0), 1.0)
        if side in ("home", "over"):
            return win_first, push, lose_first
        return lose_first, push, win_first

    def slope(self, fair: float) -> float:
        """Win probability per point near the fair line (averaged over two points)."""
        pmf, _ = self._pmf(fair)
        f = round(fair * 2) / 2
        return max(abs(self._w(pmf, f + 1) - self._w(pmf, f - 1)) / 2, 0.015)

    def value(self, fair: float, line: float, side: str, price: float) -> float:
        """Expected profit per $1 risked."""
        win, _, lose = self.probs(fair, line, side)
        return win * (american_to_decimal(price) - 1) - lose

    def fair_from_price(self, line: float, p_first: float) -> float:
        """A book's line plus its price lean, as one number. p_first = vig-free chance home covers / over wins."""
        shift = (p_first - 0.5) / self.slope(line)
        return line - shift if self.kind == "spread" else line + shift

    def limit(self, fair: float, line: float, side: str, price: float, min_value: float, max_steps: int = 16):
        """The worst line that is still a bet (walking away from `line`), and
        if `line` is not a bet, the nearest better line that would be."""
        better = {"home": 0.5, "away": -0.5, "over": -0.5, "under": 0.5}[side]
        if self.value(fair, line, side, price) >= min_value:
            last = line
            for i in range(1, max_steps):
                cand = line - better * i
                if self.value(fair, cand, side, price) < min_value:
                    break
                last = cand
            return True, last
        for i in range(1, max_steps):
            cand = line + better * i
            if self.value(fair, cand, side, price) >= min_value:
                return False, cand
        return False, None


def bell_rows(kind: str, sd: float, lo: float, hi: float, n: int = 199) -> list[tuple[float, float]]:
    """Synthetic landing rows for a sport with no key numbers (basketball): results scatter
    around the closing line like a bell curve with spread `sd`."""
    from statistics import NormalDist
    q = [NormalDist(0, sd).inv_cdf((i + 0.5) / n) for i in range(n)]
    rows, line = [], lo
    while line <= hi:
        for z in q:
            rows.append((line, float(round((-line if kind == "spread" else line) + z))))
        line += 0.5
    return rows
