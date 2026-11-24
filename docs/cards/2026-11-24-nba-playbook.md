# NBA playbook picks

How these are made: PLAYBOOK.md. Our team points come from the NBA game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.5). Full-game picks: staked. Props: staked. Units: $25; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.

**Record:** 1-2-0, -0.54 units at the grade's size (-0.54 staked), closing-line value -3.0% win chance; 3 open.

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
| Over 212.5 (-110) | Detroit Pistons at Orlando Magic | +2.6% | 214.7 / 212.5 / 218.8 | under the minimum edge | `401909314|total|over` |
| Over 234 (-110) | Dallas Mavericks at Denver Nuggets | +0.1% | 235.1 / 233.5 / 238.0 | under the minimum edge | `401909316|total|over` |
| Washington Wizards +11 (-110) | Boston Celtics at Washington Wizards | -0.6% | 10.4 / 10.5 / 10.2 | under the minimum edge | `401909315|side|home` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| Anthony Black over 1.5 Threes Made (Pinnacle -105) | Detroit Pistons at Orlando Magic | +5.1% | typical outcome 2 against a line of 1.5; chance over: ours 56%, Pinnacle 48% | CHECK held: Checked the ESPN feed for Orlando: Banchero (since Oct 24), Isaac (Nov 21) and Penda are out, all long-standing and priced; nothing found on Anthony Black's role or minutes, so the gap is most likely model noise. | `prop|4712849|fg3m|over|1.5|401909314` |
| Jamal Murray over 33.5 Pts & Rebs & Asts (Pinnacle -123) | Dallas Mavericks at Denver Nuggets | +4.2% | typical outcome 36.9 against a line of 33.5; chance over: ours 59%, Pinnacle 52% | CHECK held: Checked the ESPN feed for Denver and Dallas: no Denver player listed; Dallas has P.J. Washington questionable with illness (Nov 23 16:21 MT) and Lawal and Lively out. Nothing found on Murray's minutes, so finding nothing is a hold. | `prop|3936299|pra|over|33.5|401909316` |
| Jamal Murray over 22.5 Points (Pinnacle -124) | Dallas Mavericks at Denver Nuggets | +3.8% | typical outcome 25 against a line of 22.5; chance over: ours 59%, Pinnacle 52% | under the minimum edge | `prop|3936299|pts|over|22.5|401909316` |
| Jamal Murray over 2.5 Threes Made (Pinnacle -111) | Dallas Mavericks at Denver Nuggets | +3.6% | typical outcome 3 against a line of 2.5; chance over: ours 56%, Pinnacle 49% | under the minimum edge | `prop|3936299|fg3m|over|2.5|401909316` |
| Tristan Da Silva over 2.5 Threes Made (Pinnacle +122) | Detroit Pistons at Orlando Magic | +3.6% | typical outcome 2 against a line of 2.5; chance over: ours 49%, Pinnacle 42% | under the minimum edge | `prop|4702382|fg3m|over|2.5|401909314` |
| Tristan Da Silva over 10.5 Points (Pinnacle -112) | Detroit Pistons at Orlando Magic | +2.9% | typical outcome 12 against a line of 10.5; chance over: ours 56%, Pinnacle 49% | under the minimum edge | `prop|4702382|pts|over|10.5|401909314` |
| Zaccharie Risacher over 3.5 Rebounds (Pinnacle -139) | Dallas Mavericks at Denver Nuggets | +2.9% | typical outcome 5 against a line of 3.5; chance over: ours 61%, Pinnacle 54% | under the minimum edge | `prop|5211175|reb|over|3.5|401909316` |
| Derrick White under 3.5 Rebounds (Pinnacle -139) | Boston Celtics at Washington Wizards | +2.8% | typical outcome 3 against a line of 3.5; chance over: ours 39%, Pinnacle 46%; blowout risk (spread 10.5) (-3% on the projection) | under the minimum edge | `prop|3078576|reb|under|3.5|401909315` |
| Franz Wagner over 6.5 Assists (Pinnacle -116) | Detroit Pistons at Orlando Magic | +2.7% | typical outcome 7 against a line of 6.5; chance over: ours 56%, Pinnacle 50% | under the minimum edge | `prop|4566434|ast|over|6.5|401909314` |
| Ausar Thompson over 23.5 Pts & Rebs & Asts (Pinnacle -123) | Detroit Pistons at Orlando Magic | +2.7% | typical outcome 26 against a line of 23.5; chance over: ours 58%, Pinnacle 52% | under the minimum edge | `prop|4684742|pra|over|23.5|401909314` |

## News on this card (adjustments.yaml)

| Game | Entry | Counted? |
|---|---|---|
| Detroit Pistons at Orlando Magic | Detroit Pistons -2: Jalen Duren (hamstring) ruled out for Tuesday at Orlando (ESPN feed Nov 23 22:08 UTC). Starting center, new absence. Duncan Robinson (quad, out since Nov 17) is | NO: not applied: no Pinnacle line stored from before the news, so it cannot be shown unpriced |
