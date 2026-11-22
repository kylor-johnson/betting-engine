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

## Injury and role news (added 2026-11-22, `src/engine/models/props_news.py`)

Three effects, each sized on earlier seasons only and each a multiplier on the projection:
- **Teammate out.** A regular (appeared in one of the team's last two games) with 10%+ of the targets, carries or touches who is out. In history, "out" means listed Out or Doubtful on that week's nflverse injury report, or missing from the game (the inactive list shows this before kickoff). Live, it means listed Out, Doubtful, Injured Reserve or Suspended on ESPN's report. The vacated share goes to the players still playing, in proportion to their shares, at a fitted rate.
- **Role change.** His share over his last two games against his longer average, clipped to half to double, raised to a fitted power.
- **Questionable.** A fitted trim for players listed Questionable who play. A player listed Out or Doubtful himself is not priced.

**What the history said.** With 40%+ of the team's targets vacated, receivers got about 6% more targets than their average said. With that much of the carries vacated, running backs got about 20% more carries. The fitted rates are small (10% of the vacated share, plus a 0.25 power on recent role) and matter for running backs only. For receivers the fit chose zero: the extra targets are real but too small and noisy to help the projection.

**Held-out result (2023-2026), probability score, lower is better.** The last two numbers are only the player-games where news changed the projection by more than 5%. "Used" means news is on for that stat live; it is on only where it helped.

| Stat | Player-games | Plain average | Base model | With news | Player-games news touched | Base on those | With news on those | Used |
|---|---|---|---|---|---|---|---|---|
| receptions | 8527 | 0.2392 | 0.2367 | 0.2367 | 486 | 0.2413 | 0.2401 | on |
| receiving yards | 8527 | 0.2464 | 0.2448 | 0.2450 | 486 | 0.2463 | 0.2486 | off |
| rushing yards | 3176 | 0.2502 | 0.2445 | 0.2424 | 1317 | 0.2460 | 0.2411 | on |
| rush attempts | 3170 | 0.2598 | 0.2482 | 0.2411 | 1416 | 0.2476 | 0.2339 | on |
| passing yards | 1920 | 0.2354 | 0.2326 | 0.2327 | 19 | 0.2372 | 0.2395 | off |
| pass attempts | 1912 | 0.2498 | 0.2482 | 0.2481 | 16 | 0.2498 | 0.2491 | on |
| completions | 1917 | 0.2484 | 0.2475 | 0.2475 | 35 | 0.2551 | 0.2559 | off |
| touchdown passes | 1922 | 0.2188 | 0.2174 | 0.2173 | 35 | 0.2034 | 0.1998 | on |
| interceptions | 1922 | 0.1666 | 0.1665 | 0.1665 | 0 | n/a | n/a | off |
| touchdowns | 6741 | 0.1465 | 0.1461 | 0.1461 | 383 | 0.1373 | 0.1367 | on |
| field goals | 1908 | 0.2117 | 0.2106 | 0.2105 | 19 | 0.1813 | 0.1773 | on |

Read: a clear gain on rush attempts and rushing yards, the props where a role change or a teammate out shifts the workload most. Elsewhere, news is close to neutral. For passing and field goals it is only the Questionable trim, on very few games.

**What it did to today's sheet.** It caught real role changes (a rookie back's share up from 39% to 55% over two games; veteran backs' shares down) and moved those projections 6-15%. It did not close the biggest gaps. The model still says 77% for Justin Jefferson under 6.5 catches against Pinnacle's 40%, with Jordan Addison out. History says a receiver's target bump from a teammate out is small, while the market expects a big one. The forward test will settle who is right.

## Known gaps, in order of likely value

1. **News it still can't see.** Late inactives, a coach's stated plan, new signings, a backup quarterback starting (receivers' numbers do not adjust for who throws to them).
2. **Opponent.** No adjustment for how the defense defends that position.
3. **Wagerhouse props.** Still unread (the request hasn't been found), so even a passing prop has to be checked by hand against Wagerhouse's posted line.
4. NBA props: not built.
