"""First-half model and its walk-forward test.

Benchmark ("the market's first-half number"): the first-half spread and total implied by the full-game
closing line, using a straight-line fit on earlier seasons only (about 0.62 x spread and 0.47 x total plus
a constant). Free historical first-half closing lines do not exist, and the books' posted first-half lines
sit within half a point of this implied number almost every time we have compared (docs/research/04).

Model: the benchmark plus each team's own first-half habit: over its last `N` games (crossing seasons),
how much more or less it scored and allowed in the first half than the full-game line implied. The weight
on that habit is fitted on earlier seasons only. A habit that is just noise gets a weight near zero.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque

import duckdb

from engine.picks.totals import RAW

N = 16
THRESHOLDS = (0.5, 1.0, 1.5)


def games(first: int = 2015, last: int = 2026) -> list[dict]:
    files = [str(RAW / f"pbp_{y}.parquet") for y in range(first, last + 1) if (RAW / f"pbp_{y}.parquet").exists()]
    rows = duckdb.connect().sql(f"""
        SELECT game_id, season, week, home_team, away_team, any_value(spread_line) AS spread, any_value(total_line) AS total,
               max(total_home_score) FILTER (WHERE qtr <= 2) AS h1_home, max(total_away_score) FILTER (WHERE qtr <= 2) AS h1_away,
               max(total_home_score) AS f_home, max(total_away_score) AS f_away, min(game_date) AS day
        FROM read_parquet({files!r}, union_by_name=true)
        WHERE season_type IN ('REG', 'POST')
        GROUP BY ALL HAVING spread IS NOT NULL AND total IS NOT NULL AND h1_home IS NOT NULL
        ORDER BY day, game_id
    """).fetchall()
    cols = ("game_id", "season", "week", "home", "away", "spread", "total", "h1_home", "h1_away", "f_home", "f_away", "day")
    # nflverse spread_line is the home team's expected margin (positive = home favored)
    return [dict(zip(cols, r)) for r in rows]


def _line(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return my - b * mx, b


def build_features(gs: list[dict]) -> None:
    """Attach each team's prior first-half habit to every game (only games before it count)."""
    seasons = sorted({g["season"] for g in gs})
    implied = {}
    for s in seasons:   # implied-line coefficients from earlier seasons; the first season uses itself (it is never tested)
        train = [g for g in gs if g["season"] < s] or [g for g in gs if g["season"] == s]
        implied[s] = (_line([g["spread"] for g in train], [g["h1_home"] - g["h1_away"] for g in train]),
                      _line([g["total"] for g in train], [g["h1_home"] + g["h1_away"] for g in train]))
    hist_for = defaultdict(lambda: deque(maxlen=N))   # team -> first-half points scored above implied
    hist_against = defaultdict(lambda: deque(maxlen=N))
    for g in gs:
        (am, bm), (at, bt) = implied[g["season"]]
        g["imp_margin"] = am + bm * g["spread"]
        g["imp_total"] = at + bt * g["total"]
        imp_home_pts = (g["imp_total"] + g["imp_margin"]) / 2
        imp_away_pts = (g["imp_total"] - g["imp_margin"]) / 2
        mean = lambda d: sum(d) / len(d) if len(d) >= 4 else 0.0
        hf, ha = mean(hist_for[g["home"]]), mean(hist_against[g["home"]])
        af, aa = mean(hist_for[g["away"]]), mean(hist_against[g["away"]])
        g["x_margin"] = (hf + aa) - (af + ha)     # home expected to outscore its implied share by its habit and the away defense's
        g["x_total"] = hf + ha + af + aa
        hist_for[g["home"]].append(g["h1_home"] - imp_home_pts)
        hist_against[g["home"]].append(g["h1_away"] - imp_away_pts)
        hist_for[g["away"]].append(g["h1_away"] - imp_away_pts)
        hist_against[g["away"]].append(g["h1_home"] - imp_home_pts)


def _slope(gs, x, y):
    sxx = sum(g[x] ** 2 for g in gs)
    return sum(g[x] * g[y] for g in gs) / sxx if sxx else 0.0


def _half(v: float) -> float:
    return round(v * 2) / 2


def walk_forward(gs: list[dict], first_test: int = 2019) -> dict:
    for g in gs:
        g["r_margin"] = (g["h1_home"] - g["h1_away"]) - g["imp_margin"]
        g["r_total"] = (g["h1_home"] + g["h1_away"]) - g["imp_total"]
    out = {}
    for market, x, r, imp, act in (("first-half spread", "x_margin", "r_margin", "imp_margin", lambda g: g["h1_home"] - g["h1_away"]),
                                   ("first-half total", "x_total", "r_total", "imp_total", lambda g: g["h1_home"] + g["h1_away"])):
        mse_b = mse_m = 0.0
        n = 0
        rec = {t: [0, 0, 0] for t in THRESHOLDS}
        slopes = {}
        for s in sorted({g["season"] for g in gs if g["season"] >= first_test}):
            k = _slope([g for g in gs if g["season"] < s], x, r)
            slopes[s] = round(k, 3)
            for g in (g for g in gs if g["season"] == s):
                pred = g[imp] + k * g[x]
                a = act(g)
                mse_b += (a - g[imp]) ** 2
                mse_m += (a - pred) ** 2
                n += 1
                line = _half(g[imp])            # stand-in for the posted first-half line
                edge = pred - line
                for t in THRESHOLDS:
                    if abs(edge) < t:
                        continue
                    if a == line:
                        rec[t][2] += 1
                    elif (a > line) == (edge > 0):
                        rec[t][0] += 1
                    else:
                        rec[t][1] += 1
        records = []
        for t, (w, l, p) in rec.items():
            m = w + l
            records.append({"threshold": t, "won": w, "lost": l, "push": p, "win_rate": round(w / m, 3) if m else None,
                            "units_at_110": round(w * 100 / 110 - l, 1), "z_vs_coin": round((w - m / 2) / math.sqrt(m / 4), 2) if m else None})
        out[market] = {"games": n, "mse_market_implied": round(mse_b / n, 3), "mse_model": round(mse_m / n, 3),
                       "weight_on_habit_by_season": slopes, "records": records}
    return out


def run() -> dict:
    gs = games()
    build_features(gs)
    return walk_forward(gs, 2019)
