# 12. Where is Wagerhouse soft against Pinnacle, and how fast does it follow?

Generated 2026-11-23 14:56. Data: our own hourly reads from Nov 22 to Nov 23 20:56 UTC, 2038 paired reads across 120 games. **This is a small sample; read the counts, not the averages.** Re-run with `engine wh-edge` as it grows.

How to read it: **gap** is how far Wagerhouse's number is from Pinnacle's (points). **Juice** is the book's built-in margin on a two-way market (Pinnacle is usually 2 to 4%). **Best side worth** is the better side's expected profit per $1 at Wagerhouse's price if Pinnacle's no-vig price is the truth (the points-to-probability step is an approximation: normal curve, spread scaled to the part of the game; NFL key numbers are not modelled). **Reads worth 2%+** is how often that clears the engine's own bar. **Closing-line value** is Wagerhouse's number against Pinnacle's last line before kickoff, in points, for the best side at each read at least 30 minutes before the game (games that have started only). Reads of one game are correlated, so the number of distinct games is shown.

## 1. Price

| Sport | Market | Reads | Games | Mean gap (pts) | Wagerhouse juice | Pinnacle juice | Best side worth, average | Reads worth 2%+ | Games with one |
|---|---|---|---|---|---|---|---|---|---|
| College | side | 561 | 79 | 0.26 | 4.8% | 3.8% | -3.1% | 0% | 0 |
| College | total | 37 | 16 | 0.22 | 4.8% | 4.1% | -3.4% | 0% | 0 |
| NBA | 1st half side | 102 | 16 | 0.21 | 4.7% | 2.9% | -3.2% | 2% | 2 |
| NBA | 1st half total | 102 | 16 | 0.24 | 4.7% | 3.4% | -2.5% | 0% | 0 |
| NBA | 1st quarter side | 102 | 16 | 0.17 | 6.9% | 3.8% | -3.5% | 1% | 1 |
| NBA | 1st quarter total | 102 | 16 | 0.23 | 6.9% | 4.3% | -4.0% | 1% | 1 |
| NBA | side | 68 | 10 | 0.27 | 4.8% | 2.7% | -3.1% | 1% | 1 |
| NBA | team total | 216 | 16 | 0.34 | 7.0% | 3.8% | -4.8% | 0% | 0 |
| NBA | total | 68 | 10 | 0.22 | 4.8% | 3.1% | -3.1% | 0% | 0 |
| NFL | 1st half side | 36 | 5 | 0.25 | 4.7% | 3.0% | -1.6% | 8% | 1 |
| NFL | 1st half total | 36 | 5 | 0.28 | 4.7% | 3.4% | -2.4% | 8% | 2 |
| NFL | 1st quarter side | 36 | 5 | 0.04 | 6.3% | 3.4% | -3.7% | 3% | 1 |
| NFL | 1st quarter total | 36 | 5 | 0.04 | 6.8% | 3.9% | -3.0% | 8% | 1 |
| NFL | side | 243 | 25 | 0.28 | 4.7% | 2.8% | -2.1% | 10% | 3 |
| NFL | team total | 50 | 5 | 0.34 | 6.6% | 3.9% | -3.3% | 2% | 1 |
| NFL | total | 243 | 25 | 0.19 | 4.8% | 3.2% | -3.3% | 0% | 0 |

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
| College | side | 20 | 1 | 14 | 0 | 0 | 0 | 5 | n/a |
| College | total | 1 | 0 | 1 | 0 | 0 | 0 | 0 | n/a |
| NBA | 1st half side | 1 | 0 | 0 | 0 | 0 | 0 | 1 | n/a |
| NBA | 1st half total | 6 | 0 | 1 | 0 | 0 | 0 | 5 | n/a |
| NBA | 1st quarter total | 2 | 0 | 1 | 0 | 0 | 0 | 1 | n/a |
| NBA | side | 2 | 1 | 0 | 0 | 0 | 0 | 1 | n/a |
| NBA | team total | 15 | 3 | 5 | 0 | 0 | 0 | 7 | n/a |
| NBA | total | 9 | 1 | 1 | 1 | 0 | 0 | 6 | 1.0 |
| NFL | side | 5 | 0 | 1 | 0 | 2 | 0 | 2 | 2.6 |
| NFL | total | 10 | 0 | 4 | 0 | 0 | 2 | 4 | 5.8 |

## 4. Speed in minutes (full-game lines; fast reads every ten minutes)

A Pinnacle move counts at 0.5 point in football and 1 in the NBA. **Timed** moves are those seen within 15 minutes of the read before (inside a fast-read window); only they can say whether Wagerhouse was behind for minutes or for an hour. Rule approved 2026-11-23: over 60+ timed moves, keep the speed idea if 30% or more left Wagerhouse on the old number 20+ minutes; kill it if 80% or more were matched within 10 minutes.

| Sport | Market | Moves | Timed | Matched within 10 min | 10-30 min | 30-60 min | Over 60 min | Never before kickoff | Still behind now | Median minutes behind (caught) | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| College | side | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | no data |
| College | total | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | no data |
| NBA | side | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | no data |
| NBA | total | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | no data |
| NFL | side | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | no data |
| NFL | total | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | no data |

**All sports together:** No Pinnacle moves seen inside the fast-read windows yet.
