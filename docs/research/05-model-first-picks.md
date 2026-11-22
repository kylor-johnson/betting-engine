# Models that can produce a pick: wind totals (passed), first half (failed)

Written 2026-11-22. Code: `src/engine/models/`. Rerun with `uv run engine model-test wind` or `uv run engine model-test first-half`.

## Bottom line

The engine now has one model of its own that passed a test on seasons it never saw: the **wind totals model**. It can issue an Under as a half-unit Conditional. It is weaker in the last three seasons than before, so it is capped. The first-half model failed and is off. Player props are next; they cannot be tested against the market yet because no free history of prop lines exists, so their test starts from the props the engine logs now.

## Wind totals

**Model.** Expected total = closing total + slope x (wind - 6 mph, if positive). Wind is Open-Meteo's reanalysis wind at the stadium, averaged over the first three hours of the game. Slope and knot are fitted on earlier seasons only. Live, the slate uses the Open-Meteo forecast minus its measured 0.75 mph windy bias, at half the fitted size.

**Data.** 3,267 open-air NFL games 2010-2026 with a closing total (nflverse) and weather (Open-Meteo archive, https://open-meteo.com/en/docs/historical-weather-api). Retractable roofs marked closed and domes are excluded.

**Fit on 2010-2018:** -0.36 points per mph above 6 mph. Refits through each later season stay between -0.32 and -0.36. Latest (2010-2025): -0.319.

**Held out, 2019-2026, each season using only earlier seasons:**

| Unders where the model is this far below the close | Record | Win % | Units at -110 |
|---|---|---|---|
| 1+ point | 320-220 | 59.3% | +70.9 |
| 1.5+ | 224-159 | 58.5% | +44.6 |
| 2+ | 156-104 | 60.0% | +37.8 |

By season at 1+: 2019 54-37, 2020 36-33, 2021 51-32, 2022 57-29, 2023 48-27, 2024 33-34, 2025 28-19, 2026 (to date) 13-9.

**Warnings, all real:**
- Since 2024 the record is 74-62 (54%), and on squared error the full-size adjustment is worse than the close on 2024-2026 (171.1 vs 168.1; half size 169.2). On 2019-2023 three-quarter size was best (165.7 vs 167.1). The market seems to have caught up on how big the wind effect is, but not fully on its direction.
- Forecast, not actual weather: the day-before forecast (Open-Meteo previous runs, https://open-meteo.com/en/docs/previous-runs-api) was off by 2.1 mph on average, correlation 0.79, over 485 games since 2024. Using the forecast, Unders at 1+ went 94-76 (55.3%, +9.5 units). Positive, not proven.
- The close is the benchmark. Betting earlier, before the market reacts to the forecast, may be better or worse; there is no free history of opening totals to test it.

**How it is used.** `config.yaml` `models.wind_totals`: within 60 hours of kickoff and at 1 point or more off the total, the wind points move the fair total. If the Under clears the 2% value bar only because of the wind, the side is marked `model: wind` and can be a Conditional at most (`picks/card.py` refuses a Bet). The card shows a wind table for every open-air game.

**First live output (2026-11-22, 1:52 pm MT):** Bengals at Commanders (Monday): forecast 13.8 mph, -1.1 points; book Under 55 at -110 against a fair 53.3, flagged at +6.6%, don't bet past Under 54.5.

## First half

**Model.** The first-half spread and total implied by the full-game close (fit on earlier seasons), plus each team's habit over its last 16 games of scoring and allowing more or less in the first half than the line implied. The weight on the habit is fitted on earlier seasons.

**Result on 2,111 held-out games (2019-2026):** the fitted weight on the habit stayed between 0.01 and 0.09; squared error 102.77 vs 102.73 (spread) and 74.68 vs 74.66 (total). That is no improvement. Weight 0. This matches PFF's finding that early-game scripted performance is mostly noise (https://www.pff.com/news/nfl-pff-data-study-can-we-predict-hot-starts).

Caveat: the benchmark is the implied first-half number, not real first-half closing lines (none are free). Books' first-half lines sat within half a point of the implied number in the comparisons so far (`04-evaluation.md`, test F).

## Not done yet

- **Player props.** Plan: projections from nflverse usage (targets, carries, snap share, team pass rate), the median from a simulated distribution (books price medians), compared each day with Pinnacle's logged props (`derivative_snapshots`) and graded on results. It may drive picks only after enough logged props are graded against Pinnacle's closing prop number. Wagerhouse's props request has still not been found.
- **Injuries beyond quarterbacks** (tuning item 7 in `04-evaluation.md`).
