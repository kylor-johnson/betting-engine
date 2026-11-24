# NBA playbook picks

How these are made: PLAYBOOK.md. Our team points come from the NBA game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.25). Full-game picks: shown only, not staked (its walk-forward test lost; Kylor can switch it on). Props: staked. Units: $25; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.

**Record:** 1-2-0, -0.57 units at the grade's size (-0.57 staked), closing-line value -3.0% win chance; 3 open.

## Issued (frozen at the number shown; $0 = paper)

| Pick | Game | Grade | Stake | Don't bet past | Start (MT) | Why |
|---|---|---|---|---|---|---|
| John Collins over 1.5 Threes Made (+182) | Detroit Pistons at Orlando Magic | B | $12.5 | over 1.5 at +163 or better (a lower line is fine) | Tue 5:00 PM | typical outcome 1 against a line of 1.5; chance over: ours 40%, Pinnacle 33%; DET at 108.6 points in our script against 107.5 in the market. Win chance 40.0% against 35.5% at Pinnacle's price. |
| Orlando Magic team total over 105 (-115) | Detroit Pistons at Orlando Magic | B | $12.5 | Orlando Magic team total over 105.5 | Tue 5:00 PM | our handicap Detroit Pistons 110.2, Orlando Magic 108.6 (market Detroit Pistons 107.5, Orlando Magic 105.0). Blended at the playbook weight, our team total number is 106.7 against Wagerhouse's 105; win chance 57.2% against 53.5% needed. |
| Ausar Thompson over 4.5 Assists (-107) | Detroit Pistons at Orlando Magic | B | paper | over 4.5 at -116 or better (a lower line is fine) | Tue 5:00 PM | typical outcome 5 against a line of 4.5; chance over: ours 56%, Pinnacle 48%; DET at 108.6 points in our script against 107.5 in the market. Win chance 55.7% against 51.7% at Pinnacle's price. |

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-nba-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`; a clear also needs `because`, a positive reason the market is wrong, and `market_assumes`, what the current number already prices); a cleared one is issued and staked like any other B pick on the next read (decision 0027).

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Over 212.5 (-110) | Detroit Pistons at Orlando Magic | +1.7% | 214.3 / 211.9 / 218.8 | under the minimum edge | `401909314|total|over` |
| Over 234.5 (-110) | Dallas Mavericks at Denver Nuggets | +0.1% | 235.7 / 234.5 / 238.0 | under the minimum edge | `401909316|total|over` |
| Over 219 (-110) | Boston Celtics at Washington Wizards | -0.5% | 219.8 / 218.8 / 221.7 | under the minimum edge | `401909315|total|over` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| John Collins over 1.5 Threes Made (Pinnacle +182) | Detroit Pistons at Orlando Magic | +1.1% | typical outcome 1 against a line of 1.5; chance over: ours 37%, Pinnacle 33% | under the minimum edge | `prop|3908845|fg3m|over|1.5|401909314` |
| Anthony Black over 1.5 Threes Made (Pinnacle -105) | Detroit Pistons at Orlando Magic | +0.9% | typical outcome 2 against a line of 1.5; chance over: ours 52%, Pinnacle 48% | under the minimum edge | `prop|4712849|fg3m|over|1.5|401909314` |
| Ausar Thompson over 4.5 Assists (Pinnacle -106) | Detroit Pistons at Orlando Magic | +0.4% | typical outcome 5 against a line of 4.5; chance over: ours 52%, Pinnacle 48% | under the minimum edge | `prop|4684742|ast|over|4.5|401909314` |
| Tristan Da Silva over 2.5 Threes Made (Pinnacle +122) | Detroit Pistons at Orlando Magic | +0.4% | typical outcome 2 against a line of 2.5; chance over: ours 45%, Pinnacle 42% | under the minimum edge | `prop|4702382|fg3m|over|2.5|401909314` |
| Jamal Murray over 2.5 Threes Made (Pinnacle -111) | Dallas Mavericks at Denver Nuggets | +0.2% | typical outcome 3 against a line of 2.5; chance over: ours 53%, Pinnacle 49%; blowout risk (spread 8.5) | under the minimum edge | `prop|3936299|fg3m|over|2.5|401909316` |
| Kyshawn George over 2.5 Threes Made (Pinnacle +122) | Boston Celtics at Washington Wizards | +0.1% | typical outcome 2 against a line of 2.5; chance over: ours 45%, Pinnacle 42%; blowout risk (spread 11.5) (-4% on the projection) | under the minimum edge | `prop|5174563|fg3m|over|2.5|401909315` |
| Zaccharie Risacher over 3.5 Rebounds (Pinnacle -137) | Dallas Mavericks at Denver Nuggets | -0.1% | typical outcome 5 against a line of 3.5; chance over: ours 58%, Pinnacle 54% | under the minimum edge | `prop|5211175|reb|over|3.5|401909316` |
| Daniss Jenkins over 2.5 Threes Made (Pinnacle +162) | Detroit Pistons at Orlando Magic | -0.2% | typical outcome 2 against a line of 2.5; chance over: ours 38%, Pinnacle 36% | under the minimum edge | `prop|5107199|fg3m|over|2.5|401909314` |
| Jamal Murray over 22.5 Points (Pinnacle -124) | Dallas Mavericks at Denver Nuggets | -0.2% | typical outcome 24.8 against a line of 22.5; chance over: ours 55%, Pinnacle 52%; blowout risk (spread 8.5) | under the minimum edge | `prop|3936299|pts|over|22.5|401909316` |
| Desmond Bane over 3.5 Threes Made (Pinnacle +114) | Detroit Pistons at Orlando Magic | -0.3% | typical outcome 3 against a line of 3.5; chance over: ours 46%, Pinnacle 44% | under the minimum edge | `prop|4066320|fg3m|over|3.5|401909314` |

## News on this card (adjustments.yaml)

| Game | Entry | Counted? |
|---|---|---|
| Detroit Pistons at Orlando Magic | Detroit Pistons -2: Jalen Duren (hamstring) ruled out for Tuesday at Orlando (ESPN feed Nov 23 22:08 UTC). Starting center, new absence. Duncan Robinson (quad, out since Nov 17) is | NO: not applied: no Pinnacle line stored from before the news, so it cannot be shown unpriced |
