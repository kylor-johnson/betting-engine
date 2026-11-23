# Early-number model: pricing the opener (failed)

Written 2026-11-23. Code: `src/engine/models/openers.py`. Rerun with `uv run engine model-test openers`.

## The question

Can a number we build from information available when the opener is posted predict where the line goes by
kickoff, well enough that betting the opener in our direction wins?

**Our number.** Team ratings backed out of every earlier closing line: this season, plus last season counted
less. A second version builds them from earlier final scores instead. The cutoff is the Sunday before the
week's first game, at 8 pm Eastern for NFL and 6 am for college. A harsher version assumes the opener went up a
week earlier and uses only information from before that.

**Openers.**
- College: Bovada, from CollegeFootballData, 2021 on; about 800 held-out games a season, 2023–2026.
- NFL: ESPN BET, from ESPN's public odds feed, 2024–2025 (477 held-out games).

**Test.** Walk-forward. The share of the gap the market closes is fitted on earlier seasons only. On held-out
seasons, when our number and the opener differ by at least the threshold, we "bet" the opener our way.

## Result: no edge

| | Line moved our way | Record at the opener vs the final score |
|---|---|---|
| College spreads, ratings from closes, gap 2+ | 913 vs 942 against | 1095-1075 (50.5%), -80 units |
| College spreads, ratings from final scores, gap 2+ | 942 vs 877 | 1068-1047 (50.5%), -76 units |
| College totals, ratings from closes, gap 2+ | 925 vs 736 (+0.28 points) | 970-918 (51.4%), -36 units |
| NFL spreads, ratings from closes, gap 1.5+ | 127 vs 87 (+0.33 points) | 140-144 (49.3%), -17 units |
| NFL spreads, ratings from final scores, gap 1.5+ | 138 vs 116 | 177-167 (51.5%), -6 units |
| NFL totals, ratings from closes, gap 2+ | 76 vs 54 (+0.21 points) | 91-86 (51.4%), -3 units |

The fitted share of the gap the market takes back is 0 to 0.1 in every season. Totals drift our way by a
quarter point, but that is not enough to beat the final score at -110. The week-earlier version is no
better.

## The trap we caught

ESPN's DraftKings "open" in 2026 is the line DraftKings posted in May, not the Sunday-night opener. Checked on
2026-11-23 against the logger:
- Eagles at Cowboys shows an "open" of Cowboys -1.5; the real line is 8.5.
- Giants at Colts shows an "open" of Colts -2.5; the real line is Giants -6.5.

With those included, NFL spreads looked like 54% and +23 units. That edge was fake: our number "knew"
three months of football the May line did not. DraftKings openers are now excluded. ESPN BET's
2024–2025 openers moved about 1.1 points on average, which fits a real weekly opener, but their exact
posting time is unknown. That is why we ran the week-earlier version.

## What this means

The opener is already about as good as anything we can build from public closing lines or scores. The
early-number idea still holds for news: a quarterback ruled out, or wind on the forecast, before the book
moves. That is a news edge, not a ratings edge. It is what the watcher and the wind model already chase.

The forward check that remains: the logger now records Wagerhouse's real Sunday-night openers. Once a
season of those exists, rerun this test against Wagerhouse's openers instead of ESPN BET's. A soft book's
opener may be softer than a market-making book's.
