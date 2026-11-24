# NBA playbook picks

How these are made: PLAYBOOK.md. Our team points come from the NBA game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.5). Full-game picks: shown only, not staked (its walk-forward test lost; Kylor can switch it on); except news picks, where sourced news Pinnacle has not priced is what clears the bar (staked, decision 0029). Props: staked. Units: $25; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.

**Record:** 1-2-0, -0.54 units at the grade's size (-0.54 staked), closing-line value -3.0% win chance; 1 open.

## Issued (frozen at the number shown; $0 = paper)

| Pick | Game | Grade | Stake | Don't bet past | Start (MT) | Why |
|---|---|---|---|---|---|---|
| John Collins over 1.5 Threes Made (+182) | Detroit Pistons at Orlando Magic | B | $12.5 | over 1.5 at +163 or better (a lower line is fine) | Tue 5:00 PM | typical outcome 1 against a line of 1.5; chance over: ours 40%, Pinnacle 33%; DET at 108.6 points in our script against 107.5 in the market. Win chance 40.0% against 35.5% at Pinnacle's price. |

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-nba-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`; a clear also needs `because`, a positive reason the market is wrong, and `market_assumes`, what the current number already prices); a cleared one is issued and staked like any other B pick on the next read (decision 0027).

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Over 212 (-110) | Detroit Pistons at Orlando Magic | +4.0% | 214.7 / 212.5 / 218.8 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401909314|total|over` |
| Over 233.5 (-110) | Dallas Mavericks at Denver Nuggets | +1.0% | 235.1 / 233.5 / 238.0 | under the minimum edge | `401909316|total|over` |
| Over 217.5 (-110) | Boston Celtics at Washington Wizards | +0.8% | 219.0 / 217.5 / 221.7 | under the minimum edge | `401909315|total|over` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| Ausar Thompson over 4.5 Assists (Pinnacle +112) | Detroit Pistons at Orlando Magic | +6.4% | typical outcome 5 against a line of 4.5; chance over: ours 54%, Pinnacle 44% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|4684742|ast|over|4.5|401909314` |
| Anthony Black over 1.5 Threes Made (Pinnacle -104) | Detroit Pistons at Orlando Magic | +5.3% | typical outcome 2 against a line of 1.5; chance over: ours 56%, Pinnacle 48% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|4712849|fg3m|over|1.5|401909314` |
| Tristan Da Silva over 10.5 Points (Pinnacle -112) | Detroit Pistons at Orlando Magic | +2.9% | typical outcome 12 against a line of 10.5; chance over: ours 56%, Pinnacle 49% | under the minimum edge | `prop|4702382|pts|over|10.5|401909314` |
| Tristan Da Silva over 2.5 Threes Made (Pinnacle +111) | Detroit Pistons at Orlando Magic | +2.3% | typical outcome 2 against a line of 2.5; chance over: ours 50%, Pinnacle 44% | under the minimum edge | `prop|4702382|fg3m|over|2.5|401909314` |
| Desmond Bane over 3.5 Threes Made (Pinnacle +114) | Detroit Pistons at Orlando Magic | +2.3% | typical outcome 3 against a line of 3.5; chance over: ours 49%, Pinnacle 44% | under the minimum edge | `prop|4066320|fg3m|over|3.5|401909314` |
| Jalen Suggs under 11.5 Points (Pinnacle -132) | Detroit Pistons at Orlando Magic | +2.1% | typical outcome 9 against a line of 11.5; chance over: ours 41%, Pinnacle 47% | under the minimum edge | `prop|4432165|pts|under|11.5|401909314` |
| Paul George over 2.5 Threes Made (Pinnacle -132) | Boston Celtics at Washington Wizards | +1.1% | typical outcome 3 against a line of 2.5; chance over: ours 58%, Pinnacle 53%; blowout risk (spread 10.5) (-3% on the projection) | under the minimum edge | `prop|4251|fg3m|over|2.5|401909315` |
| Paul Reed over 9.5 Points (Pinnacle -122) | Detroit Pistons at Orlando Magic | +1.1% | typical outcome 11 against a line of 9.5; chance over: ours 56%, Pinnacle 51% | under the minimum edge | `prop|4278562|pts|over|9.5|401909314` |
| Daniss Jenkins over 4.5 Assists (Pinnacle -107) | Detroit Pistons at Orlando Magic | +0.9% | typical outcome 4 against a line of 4.5; chance over: ours 53%, Pinnacle 48% | under the minimum edge | `prop|5107199|ast|over|4.5|401909314` |
| Wendell Carter Jr. under 8.5 Rebounds (Pinnacle -133) | Detroit Pistons at Orlando Magic | +0.7% | typical outcome 7 against a line of 8.5; chance over: ours 42%, Pinnacle 47% | under the minimum edge | `prop|4277847|reb|under|8.5|401909314` |

## News on this card (adjustments.yaml)

| Game | Entry | Counted? |
|---|---|---|
| Detroit Pistons at Orlando Magic | Detroit Pistons -2: Jalen Duren (hamstring) ruled out for Tuesday at Orlando (ESPN feed Nov 23 22:08 UTC). Starting center, new absence. Duncan Robinson (quad, out since Nov 17) is | NO: not applied: no Pinnacle line stored from before the news, so it cannot be shown unpriced |
