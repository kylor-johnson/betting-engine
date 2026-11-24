"""Re-center a props model's chance of going over on what actually happened (research 18, item 5; decision 0025).

Why: on the first 209 graded NBA props the model said 42.6% of them would go over on average; 49.3% did (Pinnacle said 48.0%). Blending
that model with Pinnacle passed half of that Under lean straight into the picks. This fits one shift per stat on the log-odds scale so the
model's average chance matches the outcomes, shrunk toward the all-stat shift (and that toward zero) by `prior_n` props, so a stat with a
handful of graded props barely moves.

Data: prop_evals, one row per prop (the first price seen for each player, stat and game), graded, not a push. Fitted fresh on every read.
"""
from __future__ import annotations

import math


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _sig(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def solve_shift(ps: list[float], ys: list[int]) -> float:
    """The shift s with mean(sigmoid(logit(p) + s)) = mean(y) (Newton; this is the maximum-likelihood intercept)."""
    if not ps:
        return 0.0
    s = 0.0
    for _ in range(50):
        q = [_sig(_logit(p) + s) for p in ps]
        g = sum(y - v for y, v in zip(ys, q))
        h = sum(v * (1 - v) for v in q)
        if h <= 0:
            break
        step = g / h
        s += max(-1.0, min(1.0, step))
        if abs(step) < 1e-8:
            break
    return s


def fit_rows(rows: list[tuple[str, float, int]], prior_n: float = 100.0) -> dict[str, float]:
    """rows: (stat, model chance over, 1 if it went over). Returns {"_all": pooled shift, stat: shift}. Pure."""
    if not rows:
        return {"_all": 0.0}
    n = len(rows)
    pooled = solve_shift([p for _, p, _ in rows], [y for _, _, y in rows]) * n / (n + prior_n)
    out = {"_all": pooled}
    for stat in {s for s, _, _ in rows}:
        sub = [(p, y) for s, p, y in rows if s == stat]
        raw = max(-1.0, min(1.0, solve_shift([p for p, _ in sub], [y for _, y in sub])))      # all-overs on 4 props would run away
        out[stat] = (len(sub) * raw + prior_n * pooled) / (len(sub) + prior_n)
    return out


def fit(con, sport: str, prior_n: float = 100.0) -> dict[str, float]:
    """Shifts for one sport from every graded prop in prop_evals (first price seen per player, stat and game)."""
    try:
        rows = con.execute("""
            WITH g AS (SELECT stat, model_p_over, outcome, line,
                              row_number() OVER (PARTITION BY player_id, stat, home, away ORDER BY ts_utc) AS rn
                       FROM prop_evals WHERE coalesce(sport, 'NFL') = ? AND outcome IS NOT NULL AND outcome <> line
                         AND model_p_over IS NOT NULL)
            SELECT stat, model_p_over, CASE WHEN outcome > line THEN 1 ELSE 0 END FROM g WHERE rn = 1""", [sport]).fetchall()
    except Exception:
        return {"_all": 0.0}
    return fit_rows([(s, float(p), int(y)) for s, p, y in rows], prior_n)


def apply(p: float, shifts: dict[str, float] | None, stat: str) -> float:
    if not shifts:
        return p
    return _sig(_logit(p) + shifts.get(stat, shifts.get("_all", 0.0)))
