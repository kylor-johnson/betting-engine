# NFL totals model: built, tested, not good enough to bet

Written 2026-11-22 (Mountain).

## Verdict

I built a totals model the way Warren Sharp and other pace-and-efficiency handicappers describe theirs, then tested whether it adds anything on top of the market's closing total. It does not. In every version tried, the best blend of market and model put 100% on the market. The engine therefore still does not pick totals from a model. The model's number is shown on the slate sheet for context, and the work produced something else that is useful: per-team luck numbers the research agent now reads.

## What the model does

For each team: drives per game, points per drive, and play-by-play success rate, on offense and defense, from free nflverse play-by-play.

- Expected points for a team = expected drives × its points per drive × how soft the opposing defense is.
- Points per drive is half the real figure and half what the team's success rate says it should be. That takes out part of the turnover and red-zone luck.
- Small samples are pulled toward league average.
- The total is both teams' expected points plus the league's average points that do not come from offensive drives.

## The test

Walk-forward, the honest way: for each game, the model saw only that season's earlier weeks. Weeks 5 and later, 2022 through 2026, 918 games. The comparison is the closing total from nflverse.

| | Market close | Model |
|---|---|---|
| Average miss (points) | 10.14 | 10.65 |

- **Best blend:** 100% market, 0% model. Adding any weight on the model made predictions worse.
- **Betting the model's side when it disagreed with the close:** 275-300 at a 1.5-point gap, 192-213 at 2.5, 136-137 at 3.5. All at or below a coin flip; break-even is 52.4%.
- **Bias:** the model ran about a point higher than the close on average.

Then three variations with 2025 and 2026 held out (heavier pull toward average at two levels, and using only week 8 onward), with the bias removed using the earlier seasons:

| Version | Best market weight on 2022-24 | Held-out bets at a 2.5+ gap |
|---|---|---|
| Base | 100% | 63-52 |
| Heavier pull to average | 100% | 59-53 |
| Much heavier pull | 100% | 66-61 |
| Week 8 onward only | 100% | 44-36 |

The held-out records are slightly above 50%, but on about 115 bets the luck range is roughly ±9 points of win rate, and the larger sample above is below 50%. That is noise, not an edge.

## What this means

- The market's total already contains pace, drives, success rate and points per drive. A public-data model built from them repeats what is priced, with more error.
- This does not show Sharp's own totals model has no edge. His is undisclosed, his 63% record is self-reported, and he may use inputs this one lacks (personnel groupings, pass rate over expected by situation, weather, play-caller tendencies). It shows that the public version of the idea is not enough.
- The rule stands: a total becomes a pick only with a specific sourced reason the market may not have absorbed, such as wind or a late quarterback change.

## What was kept

- `efficiency_total_for_context_only` on each NFL game in the slate sheet, labelled as context.
- A `luck` block per team per game: share of fumbles recovered, turnover margin, red-zone touchdown rate against the league, and real points per drive against what success rate implies. The research agent uses these to support or reject "the market overreacted to results".
- `uv run engine totals-test` reruns the test any time, so a better model can be held to the same bar.

## What would have to be true to try again

A new input that the closing total demonstrably lacks, tested the same way, with seasons held out, and a blend weight below 100% on the market before any totals pick is allowed.
