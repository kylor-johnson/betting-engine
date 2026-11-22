# Handicapping layer: what Warren Sharp's write-ups do, what the engine now does, and what the tests say

Written 2026-11-22 (Mountain). Based on the free site, and on the members' write-ups from Kylor's free week (read while signed in to his account; a copy of the dashboard text is in `data.nosync/raw/sharp/`, outside git, for personal reference only).

## What his write-ups actually do

Read across this week's releases, the method is consistent:

- **Unit against unit.** Each offense against the opposing defense, by EPA per play, EPA per dropback, success rate, early-down and third-down results, red zone, and per-drive results (points, touchdowns, punts, three-and-outs, yards).
- **Schedule adjustment by span.** "Weeks 1 to 7 against the #4 easiest schedule of offenses" against "the last two games against real offenses". A unit's ranking is re-read in light of who it has faced.
- **What changed and why.** Quarterback changes, trades and injuries to specific units, pace, and pass rate over expected before and after a date.
- **Period splits.** First-quarter margins, first-half touchdowns, first-drive results, home and road.
- **Results in context.** "23 points against the #8 defense" instead of the raw score.

## Where he actually bets

This is the part worth copying, and it is not full-game sides. This week's releases:

| Released | Bet | Market type |
|---|---|---|
| Mon Nov 16, 10:13am | Titans/Cowboys Over 53.5 | Full-game total |
| Wed Nov 18 | Bears first quarter −2.5 | First quarter |
| Wed Nov 18 | Chiefs first-half touchdowns over 1.5 | First-half team prop |
| Thu Nov 19 | Buccaneers +7, buying the half point | Full-game side |
| Sun Nov 22 | Broncos team total over 25.5 | Team total |
| Thu to Sat | Five waves of player props | Props |

One full-game side in a week. Most of the action is derivatives (quarters, halves, team totals) and player props, and the full-game total went out Monday morning. The Titans total is 55 to 55.5 now; the number he bet was gone within the week.

## What the engine now has

- **A matchup block on every NFL game**, built from free play-by-play: each offense and defense on the metrics above, with league ranks, for the season, the last four games and the games before those; the toughness of the units each has faced; first-quarter and first-half scoring; first-drive results; game-by-game results with quarter and half scores. `uv run engine matchup TEN DAL` prints it side by side.
- **Luck numbers per team** (fumble recovery share, turnover margin, red-zone rate against the league, points per drive against what success rate implies).
- **The research agent is told to write the handicap from these numbers** for every side it considers, and that a price gap with no handicap behind it is not a bet.
- **Price-only Telegram messages are off.** "Your book is half a point better than DraftKings" stays an input to the slate sheet; it no longer reaches Kylor as a message.

## What the tests say (the uncomfortable part)

Two models built from this same play-by-play were tested walk-forward over 918 games, 2022 to 2026, each seeing only earlier weeks:

| Model | Average miss | Market's average miss | Best blend | Betting its side at a 2.5+ point gap |
|---|---|---|---|---|
| Totals from pace, drives and success rate | 10.65 | 10.14 | 100% market | 192-213 |
| Sides from opponent-adjusted EPA per play | 10.03 | 9.43 | 100% market | 198-210 |

Neither adds anything to the closing line on full-game sides or totals. That matches the first research document and it matches where Sharp himself puts his money. Public efficiency numbers are in the full-game closing line already.

So the handicapping layer is not a machine for beating full-game closing lines. What it is good for:

- Explaining why a line is where it is, so the agent can tell a real mispricing from a number the market moved for a reason.
- **Early in the week**, when the line has not yet absorbed a change the numbers already show (a quarterback change, a play-calling shift, a defense exposed by its first real opponents).
- **Derivative and prop markets**, which get less attention from the market and are where a unit-against-unit or first-quarter read turns into a bet.

## What this points to next

1. **Derivative markets at Wagerhouse**: first quarter, first half and team totals. Read those lines, price them from the period splits and matchup numbers, and test the pricing against history before it can issue a pick.
2. **Player props**: usage and matchup projections against the book's prop lines, tested the same way.
3. **Early-week runs with the matchup layer**: Sunday night and Monday, when Sharp's own full-game plays go out.
4. **Grading**, so every one of these is measured against the closing line and results.

## Honest limits

- His records are self-reported and his computer totals model is undisclosed. Reproducing his style of analysis does not reproduce his results.
- His releases move the market, which is part of why his numbers disappear. The engine has no such effect and should not chase a number he has already moved.
- Routes and first-read data, which his prop work leans on, are a paid product and are not in the engine.
