# 17. NFL script additions and the props matchup layer (Nov 23, 2026)

Kylor: "build the rest." The playbook's remaining inputs were each built and tested walk-forward against the closing line (method as
research 15: fit on earlier seasons, blend weight fitted one season back, scored on 2019-2026). Seven variants were run for the script and two
for the matchup layer; all are reported here. A piece is used only if it helps on seasons it never saw.

## Game script additions (`src/engine/models/script.py`)

| Variant | Total: blend error | Total bets at 2+ / 3+ / 4+ | Side: blend error | Team: blend error | Totals weight 2024 / 2025 / 2026 |
|---|---|---|---|---|---|
| Original | 174.60 | 444-416 / 293-275 / 172-141 | 158.80 | 83.32 | 0 / 0 / 0 |
| **Schedule-adjusted form** | **174.34** | **441-382 / 280-247 (53.1%) / 175-136 (56.3%)** | 158.82 | 83.33 | 0.16 / 0.06 / 0.02 |
| Adjusted + outlier half weight | 174.41 | 448-391 / 284-241 / 165-145 | 158.81 | 83.32 | 0.20 / 0.07 / 0.00 |
| Outlier half weight only | 174.60 | 444-416 / 285-258 / 163-147 | 158.75 | 83.31 | 0 / 0.06 / 0 |
| Adj + outlier + injury clusters by unit | 174.36 | 462-403 / 301-243 / 186-155 | 159.06 | 83.34 | 0.19 / 0.07 / 0 |
| Adj + outlier + referee total history | 174.48 | 449-394 / 281-249 / 165-145 | 158.81 | 83.33 | 0.20 / 0.06 / 0 |
| Adj + outlier + clusters + referee | 174.40 | 459-414 / 307-250 / 185-159 | 159.06 | 83.34 | 0.19 / 0.07 / 0 |

(Market errors for reference: totals 174.72, sides 158.82, team points 83.35.)

- **Kept: schedule-adjusted form** (each game's EPA, success rate and points per drive corrected for the opponent's pre-game form). It is the
  best result in the whole series of tests on totals: the totals weight stays above zero in every season including 2024-2026, and held-out
  total bets clear 52.4% at 3+ and 4+ point disagreements. It does nothing for sides or team totals. One of seven variants, so a lead, not proof.
- **Left out:** outlier half weight (mixed), injury clusters by unit (better total bets, worse side error), referee total history (no gain;
  also, nflverse only fills referees for 65 of 272 games this season, so it could rarely be used live).

## Props matchup layer (`src/engine/models/props_matchup.py`)

Coverage type (man or zone) is free only for 2023 (nflverse participation stops there), so it cannot be tested on later seasons or used live:
**not built.** The free FTN charting (2022 to date) has blitzers and box counts on every play, so the matchup terms are quarterbacks' yards per
attempt against the blitz times the defense's blitz rate, and runners' yards per carry against stacked boxes times the defense's box rate.

| Stat | Power tuned on 2023 | Test player-games (2024-26) | Error without | Error with | Used |
|---|---|---|---|---|---|
| Passing yards | 1.5 | 1,354 | 6,535.5 | 6,546.8 | no |
| Rushing yards | 0.0 | 2,226 | 1,084.8 | 1,084.8 | no |

Neither helps; both stay off (wired, switched by the test result, so a re-fit can turn them on if they ever pass).

## What this leaves

The one place a public-data handicap shows a consistent edge over the closing number is **NFL game totals with schedule-adjusted form**
(and, more weakly, college totals, research 16). Sides and team totals show nothing in any sport. Props rely on the props model plus the
game script; the matchup terms add nothing measurable.
