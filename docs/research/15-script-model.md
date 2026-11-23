# 15. NFL game-script model, first walk-forward test (Nov 23, 2026)

Code: `src/engine/models/script.py` (PLAYBOOK steps 1 to 3). Each team's points in each game are predicted from play-by-play of earlier games only:
offense and defense EPA per play, success rate, points per drive, drives per game (pace, own and opponent), neutral pass rate over expected,
home, a starting quarterback different from the team's usual starter, wind above 6 mph and rain. Ridge regression fitted on earlier seasons
(from 2016); the weight our number gets against the market is fitted one season back inside the training window and used on the test season.

## Result, held-out seasons 2019 to 2026 (3,447 team-games, 1,722 games)

| Market | Squared error: market | Our number alone | Blend | Bets at the market number when our number disagrees |
|---|---|---|---|---|
| Team points vs implied team total | 83.35 | 88.19 | 83.32 | 1.5+: 862-814 (51.4%); 2.5+: 458-430; 3.5+: 214-198 (51.9%) |
| Game total | 174.72 | 181.19 | 174.60 | 2+: 444-416; 3+: 293-275; 4+: 172-141 (55.0%) |
| Side | 158.82 | 171.68 | 158.80 | 2+: 445-450; 3+: 298-301; 4+: 186-183 |

Fitted weight on our number by test season (team total / game total / side): 2019 0.07/0.00/0.20, 2020 0.13/0.16/0.12, 2021 0.33/0.49/0.22,
2022 0.15/0.24/0.04, 2023 0.09/0.27/0.00, **2024 to 2026: 0/0/0**.

## What it means

- Our number alone is less accurate than the market in all three markets. Blended, it improves squared error by about 0.1%: nothing.
- The weight it earns has fallen to zero for the last three seasons. Under decision 0018 these markets can only produce C picks until graded
  picks earn weight.
- One bucket is above break-even (game totals where we disagree by 4+ points, 172-141), with nine buckets tried; treat it as a lead to track,
  not an edge.
- Not yet in the model (PLAYBOOK step 1): schedule-adjusted form, half weight for outlier opponents, injury clusters, coverage matchups.
  These are worth adding, but the history of eight earlier failures says to expect small gains on full-game markets.
- Props are where the method is aimed and are the next step (the props model gets plays and pass rate from this script).
