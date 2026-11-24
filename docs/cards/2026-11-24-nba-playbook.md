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
| Orlando Magic team total over 105 (-115) | Detroit Pistons at Orlando Magic | +3.7% | 106.7 / 105.5 / 108.6 | Shown only: NBA full-game picks are not staked (its walk-forward test lost; config playbook.sports.NBA.full_game). | `401909314|team_total|home_over` |
| Over 233.5 (-110) | Dallas Mavericks at Denver Nuggets | +1.0% | 235.1 / 233.5 / 238.0 | under the minimum edge | `401909316|total|over` |
| Over 217.5 (-110) | Boston Celtics at Washington Wizards | +0.8% | 219.0 / 217.5 / 221.7 | under the minimum edge | `401909315|total|over` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| Ausar Thompson over 4.5 Assists (Pinnacle +111) | Detroit Pistons at Orlando Magic | +6.3% | typical outcome 5 against a line of 4.5; chance over: ours 54%, Pinnacle 44% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|4684742|ast|over|4.5|401909314` |
| Anthony Black over 1.5 Threes Made (Pinnacle -104) | Detroit Pistons at Orlando Magic | +5.3% | typical outcome 2 against a line of 1.5; chance over: ours 56%, Pinnacle 48% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|4712849|fg3m|over|1.5|401909314` |
| Jamal Murray over 33.5 Pts & Rebs & Asts (Pinnacle -122) | Dallas Mavericks at Denver Nuggets | +4.3% | typical outcome 36.9 against a line of 33.5; chance over: ours 59%, Pinnacle 51% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|3936299|pra|over|33.5|401909316` |
| Ausar Thompson over 23.5 Pts & Rebs & Asts (Pinnacle -114) | Detroit Pistons at Orlando Magic | +3.8% | typical outcome 26 against a line of 23.5; chance over: ours 57%, Pinnacle 50% | under the minimum edge | `prop|4684742|pra|over|23.5|401909314` |
| Jamal Murray over 2.5 Threes Made (Pinnacle -110) | Dallas Mavericks at Denver Nuggets | +3.8% | typical outcome 3 against a line of 2.5; chance over: ours 56%, Pinnacle 49% | under the minimum edge | `prop|3936299|fg3m|over|2.5|401909316` |
| Zaccharie Risacher over 3.5 Rebounds (Pinnacle -130) | Dallas Mavericks at Denver Nuggets | +3.7% | typical outcome 5 against a line of 3.5; chance over: ours 60%, Pinnacle 53% | under the minimum edge | `prop|5211175|reb|over|3.5|401909316` |
| Jamal Murray over 22.5 Points (Pinnacle -125) | Dallas Mavericks at Denver Nuggets | +3.6% | typical outcome 25 against a line of 22.5; chance over: ours 59%, Pinnacle 52% | under the minimum edge | `prop|3936299|pts|over|22.5|401909316` |
| Daniel Gafford under 7.5 Rebounds (Pinnacle -162) | Dallas Mavericks at Denver Nuggets | +3.4% | typical outcome 6 against a line of 7.5; chance over: ours 35%, Pinnacle 42% | under the minimum edge | `prop|4278049|reb|under|7.5|401909316` |
| Tristan Da Silva over 10.5 Points (Pinnacle -112) | Detroit Pistons at Orlando Magic | +2.9% | typical outcome 12 against a line of 10.5; chance over: ours 56%, Pinnacle 49% | under the minimum edge | `prop|4702382|pts|over|10.5|401909314` |
| Kyshawn George over 14.5 Points (Pinnacle -128) | Boston Celtics at Washington Wizards | +2.9% | typical outcome 17 against a line of 14.5; chance over: ours 59%, Pinnacle 52%; blowout risk (spread 10.5) (-3% on the projection) | under the minimum edge | `prop|5174563|pts|over|14.5|401909315` |

## News on this card (adjustments.yaml)

| Game | Entry | Counted? |
|---|---|---|
| Detroit Pistons at Orlando Magic | Detroit Pistons -2: Jalen Duren (hamstring) ruled out for Tuesday at Orlando (ESPN feed Nov 23 22:08 UTC). Starting center, new absence. Duncan Robinson (quad, out since Nov 17) is | NO: not applied: no Pinnacle line stored from before the news, so it cannot be shown unpriced |
