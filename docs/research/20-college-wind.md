# 20. Does wind give college totals an edge? (Nov 23, 2026)

**Answer: no. College wind stays off.** Judged on the forecast you would have had the day before the game, a wind-under rule was 57-53 at a
1-point edge (-1.2 units at -110), 25-22 at 1.5 points and 10-9 at 2 points, over 2,556 games from 2024 to 2026. That is a coin flip. The
closing total already prices college wind. Parity cell "weather" for college: failed.

## How it was tested (no look-ahead)

- **Games:** 4,270 FBS games with a closing total and an outdoor venue (CollegeFootballData games, venues and lines), 2022 to 2026. Domes
  removed.
- **Wind:** Open-Meteo at the stadium's coordinates at kickoff. For fitting, the archive (what happened, reanalysis). For judging 2024 on,
  the **previous-day forecast** (Open-Meteo previous-runs, which starts in Feb 2024), because that is what a bet placed the day before would
  have seen (research 18's rule).
- **Model:** points off the closing total = slope x (wind above a knot). Fit on 2022-2023 only: slope -0.34 points per mph above 10 mph.
  Re-fit walk-forward each season (2025: -0.20, 2026: -0.20) and judged only on seasons it never saw.
- **Bet rule tested:** take the under when the model's total is at least 1, 1.5 or 2 points under the close.

## Results, judged on the day-before forecast

| Edge needed | Won | Lost | Push | Win rate | Units at -110 |
|---|---|---|---|---|---|
| 1 point | 57 | 53 | 2 | 51.8% | -1.2 |
| 1.5 points | 25 | 22 | 1 | 53.2% | +0.7 |
| 2 points | 10 | 9 | 1 | 52.6% | +0.1 |

You need 52.4% at -110 to break even. The luck range on 110 bets is about plus or minus 9.5 points of win rate, so none of this is
distinguishable from zero. By season at 1 point: 2024 28-35 (-9.5 units), 2025 19-7 (+10.3), 2026 10-11 (-1.9). One good season, one bad.

The model's total was also no closer to the final score than the closing total (mean squared error 241.2 against 240.93 for the close).
Judged on what actually happened (reanalysis wind, which you could not have known), it was worse: 35-35 at 1 point, 4-9 at 2 points.

## Wind bands (forecast wind, all 2024-2026 games, no model)

| Wind (mph) | Games | Unders | Overs | Under rate | Final minus close (points) |
|---|---|---|---|---|---|
| 0-8 | 1,697 | 855 | 834 | 50.6% | +0.4 |
| 8-12 | 621 | 296 | 320 | 48.1% | +1.4 |
| 12-16 | 192 | 98 | 93 | 51.3% | +1.0 |
| 16-20 | 41 | 22 | 18 | 55.0% | +0.2 |
| 20+ | 5 | 4 | 1 | 80% | -9.9 |

Only the 20+ band leans under, and it is 5 games in three seasons: not a lane. Windy college games do not go under the close more than calm
ones.

## Why the NFL is different

NFL wind passed (research 05, 17) and is weaker since 2024. College totals move more on the news a big wind forecast brings, and the market
has had years to learn it. This test does not touch the NFL model.

## What changed

- `config.yaml`: college lane model `college_wind_totals` = failed; parity cell weather/College = failed; "wind test running" removed from what the
  lane is not evaluating.
- No live code: the wiring written in case it passed was removed before commit. `src/engine/models/college_wind.py` stays as the test
  script (`uv run python -m engine.models.college_wind`, cached in `data.nosync/weather/`; results in
  `data.nosync/models/college_wind_test.json`).
- Re-test only with a new idea (wind direction against the stadium, or the 20+ band once it has 50 games), not by re-running this one.
