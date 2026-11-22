# NFL player props model

Written 2026-11-22. Code: `src/engine/models/props.py`. Commands: `uv run engine props-test` (held-out test), `uv run engine props` (price the latest Pinnacle props, grade finished ones, write `docs/cards/<date>-nfl-props.md`). The hourly read does the same pricing and grading automatically.

## Bottom line

The model is built and its probabilities are honest on seasons it never saw. It is slightly more accurate than a plain recent average on every stat. That does **not** show it beats Pinnacle, and nothing free can show that historically: no free history of prop lines exists (`04-evaluation.md`, Q3). So the market test runs forward. Every read logs the model's chance next to Pinnacle's vig-free chance, and every prop is graded from nflverse stats after the game. Props become picks only after 300 are graded and the model has shown it adds something to Pinnacle (`config.yaml`, `models.props`; decision 0006). Expect two to three NFL weeks to reach 300.

## How it works

1. **Projection.** For each player and stat: a weighted average of his recent games (up to 16; newer count more; last season's games at 0.6 weight; nothing older), needing at least three earlier games. It's scaled by his team's expected points this game (from Pinnacle's spread and total) against his team's expected points in the games behind the average, raised to a fitted power. Recency and the game-context power are fitted per stat on earlier seasons only.
2. **Distribution.** Books price the median, and these stats are lopsided, with a floor of 0 and a long tail of big games (Unabated, https://unabated.com/post/the-biggest-mistake-youre-making-when-betting-nfl-player-props). So the model doesn't assume a bell curve. It looks up the 500 earlier player-games with the closest projection and reads what actually happened, scaling yardage to this projection. The chance of going over any line comes from those outcomes.
3. **Who counts.** Only players with a real role: 3+ targets a game for receiving props, 6+ carries for rushing, 20+ attempts for passing, kickers for field goals.

Data: nflverse weekly player stats 2018-2026 (https://github.com/nflverse/nflverse-data/releases/tag/stats_player) and nflverse closing lines.

## Held-out test (each season 2023-2026 fitted only on earlier seasons)

"Typical miss" is the average distance from the model's median to what happened. "Probability score" is the Brier score at three lines per player-game (the model's median and one step either side); lower is better. "Worst calibration gap" is the largest difference between what the model said and what happened in any 10%-wide band with 200+ cases.

| Stat | Player-games | Typical miss: model | Plain average | Probability score: model | Plain average | Worst calibration gap |
|---|---|---|---|---|---|---|
| receptions | 8527 | 1.65 | 1.66 | 0.2367 | 0.2392 | 0.028 |
| receiving yards | 8527 | 23.13 | 23.24 | 0.2448 | 0.2464 | 0.026 |
| rushing yards | 3176 | 24.76 | 25.30 | 0.2445 | 0.2502 | 0.020 |
| rush attempts | 3170 | 4.18 | 4.34 | 0.2482 | 0.2598 | 0.012 |
| passing yards | 1920 | 65.67 | 66.29 | 0.2326 | 0.2354 | 0.047 |
| pass attempts | 1912 | 7.67 | 7.70 | 0.2482 | 0.2498 | 0.038 |
| completions | 1917 | 5.35 | 5.37 | 0.2475 | 0.2484 | 0.027 |
| touchdown passes | 1922 | 0.88 | 0.89 | 0.2174 | 0.2188 | 0.046 |
| interceptions | 1922 | 0.67 | 0.67 | 0.1665 | 0.1666 | 0.028 |
| touchdowns (rush + rec) | 6741 | 0.42 | 0.42 | 0.1461 | 0.1465 | 0.038 |
| field goals | 1908 | 1.00 | 1.01 | 0.2106 | 0.2117 | 0.035 |

Read: honest probabilities (gaps of 1 to 5 points), small accuracy gains over a plain average. The biggest gains are on rushing and attempts, where game script (expected points) matters most.

## First comparison with Pinnacle (2026-11-22 afternoon, 552 prop-reads, 74 players, late and Monday games)

The largest disagreements were lopsided: model 77% vs Pinnacle 40% on Justin Jefferson under 6.5 receptions, and a rookie running back's rushing line 71.5 against a model median of 34. Those look like news and role changes the model can't see (injuries, a teammate out, a new starter). Pinnacle prices news; this model only knows past box scores. Grading will show whether the moderate disagreements carry anything.

## Known gaps, in order of likely value

1. **News.** Injuries, inactives and role changes, which a sharp book prices and this model can't. The research agent can supply them, but code can't check that yet.
2. **Opponent.** No adjustment for how the defense defends that position.
3. **Wagerhouse props.** Still unread (the request hasn't been found), so even a passing prop has to be checked by hand against Wagerhouse's posted line.
4. NBA props: not built.
