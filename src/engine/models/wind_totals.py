"""Wind totals model and its walk-forward test against the NFL closing total.

The model: expected total = closing total + b x max(0, wind - knot), with wind the reanalysis wind at the
stadium over the first three hours of the game (Open-Meteo). `b` and `knot` are fitted only on seasons
before the one being tested. A bet is an Under when the model says the total is at least `threshold`
points below the line.

The test answers one question: does the model, fitted on earlier seasons, predict totals better than the
closing line on seasons it never saw, and does betting its Unders at -110 clear the 52.4% break-even?
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime

import duckdb

from engine import config
from engine.models import weather

GAMES_CSV = config.DATA / "raw" / "nflverse_games.csv"
KNOTS = (6.0, 8.0, 10.0, 12.0)
THRESHOLDS = (1.0, 1.5, 2.0)
BREAK_EVEN = 110 / 210


@dataclass
class Game:
    game_id: str
    season: int
    stadium: str
    kickoff: datetime          # Eastern
    close: float
    actual: float
    wind: float | None = None
    temp: float | None = None
    precip: float | None = None
    fwind: float | None = None  # day-before forecast wind, where available


def outdoor_games(first: int = 2010) -> list[Game]:
    rows = duckdb.connect().sql(f"""
        SELECT game_id, season, stadium_id, gameday, gametime, total_line, total
        FROM read_csv_auto('{GAMES_CSV}')
        WHERE season >= {first} AND total_line IS NOT NULL AND total IS NOT NULL AND gametime IS NOT NULL
          AND coalesce(roof, 'outdoors') NOT IN ('dome', 'closed')
    """).fetchall()
    out = []
    for gid, season, st, day, gt, line, tot in rows:
        if st not in weather.STADIUMS:
            continue
        ko = datetime.combine(day, gt).replace(tzinfo=weather.EASTERN)
        out.append(Game(gid, season, st, ko, float(line), float(tot)))
    return out


def attach_weather(games: list[Game], forecast: bool = False) -> None:
    """Reanalysis for every game; the day-before forecast too when `forecast` (2024 on)."""
    groups: dict[tuple[str, int], list[Game]] = {}
    for g in games:
        groups.setdefault((g.stadium, g.season), []).append(g)
    for (st, season), gs in sorted(groups.items()):
        start = min(g.kickoff.date() for g in gs)
        end = max(g.kickoff.date() for g in gs)
        hours = weather.archive(st, start, end)
        for g in gs:
            w = weather.game_window(hours, g.kickoff)
            if w:
                g.wind, g.temp, g.precip = w["wind_mph"], w["temp_f"], w["precip_mm"]
        if forecast and start >= date(2024, 2, 1):
            fh = weather.previous_day(st, start, end)
            for g in gs:
                w = weather.game_window(fh, g.kickoff)
                if w:
                    g.fwind = w["wind_mph"]


def fit(games: list[Game]) -> tuple[float, float]:
    """Least-squares slope of (actual - close) on max(0, wind - knot), best knot by squared error."""
    best = None
    for k in KNOTS:
        xs = [max(0.0, g.wind - k) for g in games]
        ys = [g.actual - g.close for g in games]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)   # intercept fitted, then dropped: the market's average bias is not the model's to claim
        sxx = sum((x - mx) ** 2 for x in xs)
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
        sse = sum((y - my - b * (x - mx)) ** 2 for x, y in zip(xs, ys))
        if best is None or sse < best[0]:
            best = (sse, b, k)
    return best[1], best[2]


def adjustment(wind: float, b: float, knot: float) -> float:
    return b * max(0.0, wind - knot)


def _record(rows: list[tuple[float, float, float]], threshold: float) -> dict:
    """rows = (adjustment, close, actual). Under bets where adjustment <= -threshold."""
    w = l = p = 0
    for adj, close, actual in rows:
        if adj > -threshold:
            continue
        if actual < close:
            w += 1
        elif actual > close:
            l += 1
        else:
            p += 1
    n = w + l
    rate = w / n if n else None
    # one-sided chance of doing this well or better with no edge at a 50% coin
    z = (w - 0.5 * n) / math.sqrt(0.25 * n) if n else None
    units = w * (100 / 110) - l
    return {"threshold": threshold, "won": w, "lost": l, "push": p, "win_rate": rate,
            "units_at_110": round(units, 1), "z_vs_coin": None if z is None else round(z, 2)}


def walk_forward(games: list[Game], first_test: int = 2019, use_forecast: bool = False) -> dict:
    """Each test season uses a model fitted on every earlier season only."""
    have = [g for g in games if g.wind is not None]
    seasons = sorted({g.season for g in have if g.season >= first_test})
    test_rows, per_season, mse_close, mse_model = [], [], 0.0, 0.0
    for s in seasons:
        b, k = fit([g for g in have if g.season < s])
        tested = [g for g in have if g.season == s and (not use_forecast or g.fwind is not None)]
        for g in tested:
            wind = g.fwind if use_forecast else g.wind
            adj = adjustment(wind, b, k)
            test_rows.append((adj, g.close, g.actual))
            mse_close += (g.actual - g.close) ** 2
            mse_model += (g.actual - g.close - adj) ** 2
        per_season.append({"season": s, "slope": round(b, 3), "knot": k, "games": len(tested),
                           **{f"under_{t:g}": _record([(adjustment(g.fwind if use_forecast else g.wind, b, k), g.close, g.actual) for g in tested], t)
                              for t in THRESHOLDS}})
    n = len(test_rows)
    return {"games": n, "mse_close": round(mse_close / n, 2) if n else None, "mse_model": round(mse_model / n, 2) if n else None,
            "records": [_record(test_rows, t) for t in THRESHOLDS], "per_season": per_season}


def run(forecast_check: bool = True) -> dict:
    games = outdoor_games()
    attach_weather(games, forecast=forecast_check)
    have = [g for g in games if g.wind is not None]
    out = {"games_with_weather": len(have), "games_total": len(games), "fit_all_before_2019": fit([g for g in have if g.season < 2019]),
           "held_out": walk_forward(games, 2019)}
    if forecast_check:
        fc = [g for g in have if g.fwind is not None]
        if fc:
            diffs = [g.fwind - g.wind for g in fc]
            mw, mf = sum(g.wind for g in fc) / len(fc), sum(g.fwind for g in fc) / len(fc)
            cov = sum((g.wind - mw) * (g.fwind - mf) for g in fc)
            corr = cov / math.sqrt(sum((g.wind - mw) ** 2 for g in fc) * sum((g.fwind - mf) ** 2 for g in fc))
            out["forecast_vs_reanalysis"] = {"games": len(fc), "mean_gap_mph": round(sum(diffs) / len(diffs), 2),
                                             "mean_abs_gap_mph": round(sum(abs(d) for d in diffs) / len(diffs), 2), "correlation": round(corr, 3)}
            out["held_out_with_forecast"] = walk_forward(games, 2024, use_forecast=True)
            out["held_out_same_games_reanalysis"] = walk_forward([g for g in games if g.fwind is not None or g.season < 2024], 2024)
    return out
