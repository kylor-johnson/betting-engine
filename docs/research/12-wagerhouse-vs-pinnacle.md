# 12. Where is Wagerhouse soft against Pinnacle, and how fast does it follow?

Generated 2026-11-23 13:28. Data: our own hourly reads from Nov 22 to Nov 23 19:32 UTC, 1580 paired reads across 120 games. **This is a small sample; read the counts, not the averages.** Re-run with `engine wh-edge` as it grows.

How to read it: **gap** is how far Wagerhouse's number is from Pinnacle's (points). **Juice** is the book's built-in margin on a two-way market (Pinnacle is usually 2 to 4%). **Best side worth** is the better side's expected profit per $1 at Wagerhouse's price if Pinnacle's no-vig price is the truth (the points-to-probability step is an approximation: normal curve, spread scaled to the part of the game; NFL key numbers are not modelled). **Reads worth 2%+** is how often that clears the engine's own bar. **Closing-line value** is Wagerhouse's number against Pinnacle's last line before kickoff, in points, for the best side at each read at least 30 minutes before the game (games that have started only). Reads of one game are correlated, so the number of distinct games is shown.

## 1. Price

| Sport | Market | Reads | Games | Mean gap (pts) | Wagerhouse juice | Pinnacle juice | Best side worth, average | Reads worth 2%+ | Games with one |
|---|---|---|---|---|---|---|---|---|---|
| College | side | 433 | 79 | 0.26 | 4.8% | 3.8% | -3.1% | 0% | 0 |
| College | total | 31 | 16 | 0.19 | 4.8% | 4.1% | -3.5% | 0% | 0 |
| NBA | 1st half side | 82 | 16 | 0.21 | 4.7% | 2.9% | -3.2% | 1% | 1 |
| NBA | 1st half total | 82 | 16 | 0.22 | 4.7% | 3.4% | -2.6% | 0% | 0 |
| NBA | 1st quarter side | 82 | 16 | 0.17 | 6.9% | 3.8% | -3.6% | 0% | 0 |
| NBA | 1st quarter total | 82 | 16 | 0.24 | 6.9% | 4.3% | -4.0% | 1% | 1 |
| NBA | side | 28 | 10 | 0.27 | 4.8% | 2.6% | -3.0% | 0% | 0 |
| NBA | team total | 176 | 16 | 0.35 | 7.0% | 3.8% | -4.7% | 0% | 0 |
| NBA | total | 28 | 10 | 0.20 | 4.8% | 3.1% | -3.1% | 0% | 0 |
| NFL | 1st half side | 34 | 5 | 0.26 | 4.7% | 3.0% | -1.5% | 9% | 1 |
| NFL | 1st half total | 34 | 5 | 0.29 | 4.7% | 3.4% | -2.3% | 9% | 2 |
| NFL | 1st quarter side | 34 | 5 | 0.04 | 6.3% | 3.4% | -3.7% | 3% | 1 |
| NFL | 1st quarter total | 34 | 5 | 0.04 | 6.8% | 3.9% | -2.9% | 9% | 1 |
| NFL | side | 187 | 25 | 0.29 | 4.7% | 2.7% | -2.3% | 9% | 3 |
| NFL | team total | 46 | 5 | 0.30 | 6.5% | 3.9% | -3.5% | 2% | 1 |
| NFL | total | 187 | 25 | 0.18 | 4.8% | 3.2% | -3.4% | 0% | 0 |

## 2. Closing-line value of the best side at each read (games already started)

| Sport | Market | Games | Reads | Average, all reads (pts) | Reads worth 2%+ | Average on those (pts) |
|---|---|---|---|---|---|---|
| College | side | 1 | 1 | +0.50 | 0 | n/a |
| College | total | 1 | 1 | +1.00 | 0 | n/a |
| NBA | 1st half side | 6 | 31 | +0.06 | 0 | n/a |
| NBA | 1st half total | 6 | 31 | +0.00 | 0 | n/a |
| NBA | 1st quarter side | 6 | 31 | +0.13 | 0 | n/a |
| NBA | 1st quarter total | 6 | 31 | +0.13 | 1 | +1.00 |
| NBA | team total | 12 | 62 | -0.02 | 0 | n/a |
| NFL | 1st half side | 4 | 16 | +0.56 | 3 | +2.00 |
| NFL | 1st half total | 4 | 16 | +0.00 | 3 | -0.67 |
| NFL | 1st quarter side | 4 | 16 | -0.09 | 1 | -0.50 |
| NFL | 1st quarter total | 4 | 16 | -0.09 | 3 | -0.50 |
| NFL | side | 11 | 79 | +0.08 | 0 | n/a |
| NFL | team total | 8 | 32 | +0.14 | 1 | +1.50 |
| NFL | total | 11 | 79 | +0.08 | 0 | n/a |

A positive average means that betting the better side at Wagerhouse's number, at the times we read, would have beaten Pinnacle's close by that many points before paying the extra juice. Zero or negative means the gap at the time of the read was not predictive of where Pinnacle ended up.

## 3. Speed: after Pinnacle moves, how long until Wagerhouse shows the same number?

Only moves of half a point or more between two reads. Resolution is one hour, so 'within the next read' means about an hour or less.

| Sport | Market | Pinnacle moves seen | Wagerhouse already there | Same read | Followed within 1h | Followed in 1-3h | Followed later | Not by the last read | Median hours (followed) |
|---|---|---|---|---|---|---|---|---|---|
| College | side | 17 | 1 | 12 | 0 | 0 | 0 | 4 | n/a |
| NBA | 1st half side | 7 | 0 | 2 | 0 | 0 | 0 | 5 | n/a |
| NBA | 1st half total | 7 | 1 | 2 | 0 | 0 | 0 | 4 | n/a |
| NBA | 1st quarter side | 4 | 0 | 1 | 0 | 0 | 0 | 3 | n/a |
| NBA | 1st quarter total | 5 | 1 | 3 | 0 | 0 | 0 | 1 | n/a |
| NBA | side | 2 | 0 | 0 | 0 | 0 | 0 | 2 | n/a |
| NBA | team total | 12 | 1 | 5 | 0 | 0 | 0 | 6 | n/a |
| NBA | total | 4 | 0 | 1 | 1 | 0 | 0 | 2 | 1.0 |
| NFL | side | 5 | 0 | 1 | 0 | 2 | 0 | 2 | 2.6 |
| NFL | total | 10 | 0 | 4 | 0 | 0 | 2 | 4 | 5.8 |
