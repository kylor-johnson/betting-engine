# 11a. Do the landing tables tell the truth? (walk-forward reliability check)

Run 2026-11-23. Method and limits are in the docstring of `src/engine/models/calibration.py`: the market close is used as the fair line, bets are priced 0.5 to 3 points either side, the table is built only from earlier seasons. This checks the points-to-probability curve, not whether the fair line is right.

## NFL sides, test seasons 2019 to 2025 (table from 2015 up to the season before)

| Version | Bets priced | Squared error | Average predicted | Average realized | Skipped (too few past games) |
|---|---|---|---|---|---|
| engine's table (window 1.0) | 29904 | 0.24039 | 0.500 | 0.500 | 32 |

Reliability, engine's table (window 1.0):

| Predicted chance | Bets | Predicted | Realized |
|---|---|---|---|
| 30-40% | 3127 | 0.375 | 0.377 |
| 40-50% | 11825 | 0.456 | 0.452 |
| 50-60% | 11824 | 0.544 | 0.548 |
| 60-70% | 3128 | 0.625 | 0.623 |

Bets priced at 2.5/3/3.5 or 6.5/7/7.5: 7970, squared error 0.23932.

## NFL totals, same seasons

| Version | Bets priced | Squared error | Average predicted | Average realized | Skipped (too few past games) |
|---|---|---|---|---|---|
| engine's table (window 3.0) | 31360 | 0.24334 | 0.500 | 0.500 | 0 |

Reliability, engine's table (window 3.0):

| Predicted chance | Bets | Predicted | Realized |
|---|---|---|---|
| 30-40% | 335 | 0.397 | 0.443 |
| 40-50% | 15345 | 0.452 | 0.452 |
| 50-60% | 15345 | 0.548 | 0.548 |
| 60-70% | 335 | 0.603 | 0.557 |

## NBA sides, test seasons [2025, 2026, 2027] (ESPN box scores and closing lines; earlier seasons are the training window)

The overall spread of NBA margins around the close is about 13.9 points, but the engine only prices bets within a few points of fair, where results are more bunched than a bell curve with that spread. That is why the smaller configured value (12) holds up.

| Version | Bets priced | Squared error | Average predicted | Average realized | Skipped (too few past games) |
|---|---|---|---|---|---|
| bell curve, sd 12 (what config.yaml uses) | 46000 | 0.24421 | 0.500 | 0.500 | 0 |
| bell curve, sd fitted on earlier seasons | 46000 | 0.24426 | 0.500 | 0.500 | 0 |
| real results (window 2.0) | 46000 | 0.24400 | 0.500 | 0.500 | 0 |

Reliability, bell curve, sd 12 (what config.yaml uses):

| Predicted chance | Bets | Predicted | Realized |
|---|---|---|---|
| 30-40% | 2875 | 0.399 | 0.410 |
| 40-50% | 20125 | 0.453 | 0.452 |
| 50-60% | 20125 | 0.547 | 0.548 |
| 60-70% | 2875 | 0.601 | 0.590 |

Bets priced at 2.5/3/3.5 or 6.5/7/7.5: 12320, squared error 0.24399.

Reliability, bell curve, sd fitted on earlier seasons:

| Predicted chance | Bets | Predicted | Realized |
|---|---|---|---|
| 40-50% | 23000 | 0.453 | 0.447 |
| 50-60% | 23000 | 0.547 | 0.553 |

Bets priced at 2.5/3/3.5 or 6.5/7/7.5: 12320, squared error 0.24415.

Reliability, real results (window 2.0):

| Predicted chance | Bets | Predicted | Realized |
|---|---|---|---|
| 30-40% | 2552 | 0.383 | 0.384 |
| 40-50% | 20390 | 0.454 | 0.454 |
| 50-60% | 20503 | 0.546 | 0.545 |
| 60-70% | 2555 | 0.617 | 0.616 |

Bets priced at 2.5/3/3.5 or 6.5/7/7.5: 12320, squared error 0.24399.

## NBA totals, same seasons

| Version | Bets priced | Squared error | Average predicted | Average realized | Skipped (too few past games) |
|---|---|---|---|---|---|
| bell curve, sd 18 (config.yaml) | 46000 | 0.24692 | 0.500 | 0.500 | 0 |
| bell curve, sd fitted | 46000 | 0.24692 | 0.500 | 0.500 | 0 |

Reliability, bell curve, sd 18 (config.yaml):

| Predicted chance | Bets | Predicted | Realized |
|---|---|---|---|
| 40-50% | 23000 | 0.464 | 0.464 |
| 50-60% | 23000 | 0.536 | 0.536 |

Reliability, bell curve, sd fitted:

| Predicted chance | Bets | Predicted | Realized |
|---|---|---|---|
| 40-50% | 23000 | 0.463 | 0.464 |
| 50-60% | 23000 | 0.537 | 0.536 |

