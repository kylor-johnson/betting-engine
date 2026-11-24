"""Decision 0036, item 5: the NFL script fitted without actual weather, plus a wind term fitted on day-before FORECASTS only.

Rule, written before running: the script is walk-forward without wind and rain. A wind term (points of total per mph above 6, forecast
issued the day before) is fitted on 2024-2025 outdoor games against the no-weather script's own total, and judged on 2026, a season it
never saw. It is switched on only if (a) the fitted slope is negative and (b) 2026 squared error of our own total improves with it.
Rain is dropped: no rain forecast history is cached, and research 18 showed the actual-weather inputs were the look-ahead.

uv run python scripts/research24/nfl_forecast_weather.py
"""
from __future__ import annotations

from engine.models import script, wind_totals

KNOT = 6.0


def main() -> None:
    rows = script.build_features()
    nw = tuple(f for f in script.BASE_FEATURES if f not in ("wind6", "rain"))
    res = script.walk_forward(rows, features=nw)
    s = script.summary(res)
    print("no-weather script, totals: market", round(s["total"]["mse_market"], 2), "own", round(s["total"]["mse_own"], 2),
          "blend", round(s["total"]["mse_blend"], 2), "| weights by season", [(w["season"], w["w_total"]) for w in s["weights"]])
    games = {g["game_id"]: g for g in res["game"]}
    gs = wind_totals.outdoor_games(2024)
    wind_totals.attach_weather(gs, forecast=True)
    pts = []
    for g in gs:
        a = games.get(g.game_id)
        if a is None or g.fwind is None:
            continue
        pts.append((a["season"], max(0.0, g.fwind - KNOT), a["actual_total"] - a["own_total"], a))
    fit = [(x, y) for se, x, y, _ in pts if se in (2024, 2025)]
    test = [(x, y) for se, x, y, _ in pts if se == 2026]
    mx, my = sum(x for x, _ in fit) / len(fit), sum(y for _, y in fit) / len(fit)
    sxx = sum((x - mx) ** 2 for x, _ in fit)
    b = sum((x - mx) * (y - my) for x, y in fit) / sxx if sxx else 0.0
    base = sum(y * y for _, y in test) / len(test)
    withw = sum((y - b * x) ** 2 for x, y in test) / len(test)
    print(f"forecast wind games: fit 2024-2025 n={len(fit)}, test 2026 n={len(test)}; slope {b:+.3f} points per mph above {KNOT:g}")
    print(f"2026 squared error of our own total on outdoor games: without wind {base:.2f}, with forecast wind {withw:.2f}")
    on = b < 0 and withw < base
    print("VERDICT:", "switch the forecast wind term ON" if on else "leave it OFF", f"(slope {b:+.3f})")


if __name__ == "__main__":
    main()
