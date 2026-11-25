# NBA playbook picks

How these are made: PLAYBOOK.md. Our team points come from the NBA game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.25). Full-game picks: shown only, not staked (its walk-forward test lost; Kylor can switch it on). Props: staked. Units: $25; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.

**Record:** 1-2-0, -0.57 units at the grade's size (-0.57 staked), closing-line value -3.0% win chance; 3 open.

## Issued (frozen at the number shown; $0 = paper)

None open.

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-nba-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`; a clear also needs `because`, a positive reason the market is wrong, and `market_assumes`, what the current number already prices); a cleared one is issued and staked like any other B pick on the next read (decision 0027).

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Dallas Mavericks team total over 113 (-115) | Dallas Mavericks at Denver Nuggets | +0.3% | 114.0 / 113.1 / 115.5 | under the minimum edge | `401909316|team_total|away_over` |
| Over 219 (-110) | Boston Celtics at Washington Wizards | -0.5% | 219.8 / 218.8 / 221.7 | under the minimum edge | `401909315|total|over` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| Jamal Murray over 2.5 Threes Made (Pinnacle -111) | Dallas Mavericks at Denver Nuggets | +0.2% | typical outcome 3 against a line of 2.5; chance over: ours 53%, Pinnacle 49%; blowout risk (spread 8.5) | under the minimum edge | `prop|3936299|fg3m|over|2.5|401909316` |
| Kyshawn George over 2.5 Threes Made (Pinnacle +122) | Boston Celtics at Washington Wizards | +0.1% | typical outcome 2 against a line of 2.5; chance over: ours 45%, Pinnacle 42%; blowout risk (spread 11.5) (-4% on the projection) | under the minimum edge | `prop|5174563|fg3m|over|2.5|401909315` |
| Zaccharie Risacher over 3.5 Rebounds (Pinnacle -137) | Dallas Mavericks at Denver Nuggets | -0.2% | typical outcome 5 against a line of 3.5; chance over: ours 58%, Pinnacle 54% | under the minimum edge | `prop|5211175|reb|over|3.5|401909316` |
| AJ Dybantsa over 6.5 Rebounds (Pinnacle +112) | Boston Celtics at Washington Wizards | -0.4% | typical outcome 7 against a line of 6.5; chance over: ours 47%, Pinnacle 44%; blowout risk (spread 11.5) (-4% on the projection) | under the minimum edge | `prop|5142718|reb|over|6.5|401909315` |
| Zaccharie Risacher over 8.5 Points (Pinnacle +114) | Dallas Mavericks at Denver Nuggets | -0.6% | typical outcome 9 against a line of 8.5; chance over: ours 46%, Pinnacle 44% | under the minimum edge | `prop|5211175|pts|over|8.5|401909316` |
| Jamal Murray over 33.5 Pts & Rebs & Asts (Pinnacle -123) | Dallas Mavericks at Denver Nuggets | -0.6% | typical outcome 36 against a line of 33.5; chance over: ours 55%, Pinnacle 52%; blowout risk (spread 8.5) (-1% on the projection) | under the minimum edge | `prop|3936299|pra|over|33.5|401909316` |
| Neemias Queta under 8.5 Rebounds (Pinnacle -102) | Boston Celtics at Washington Wizards | -0.6% | typical outcome 8 against a line of 8.5; chance over: ours 50%, Pinnacle 53% | under the minimum edge | `prop|4397424|reb|under|8.5|401909315` |
| Kyrie Irving under 31.5 Pts & Rebs & Asts (Pinnacle -107) | Dallas Mavericks at Denver Nuggets | -0.7% | typical outcome 29 against a line of 31.5; chance over: ours 49%, Pinnacle 52%; blowout risk (spread 8.5) (-1% on the projection) | under the minimum edge | `prop|6442|pra|under|31.5|401909316` |
| Alex Sarr over 9.5 Points (Pinnacle -107) | Boston Celtics at Washington Wizards | -0.7% | typical outcome 10 against a line of 9.5; chance over: ours 51%, Pinnacle 48% | under the minimum edge | `prop|5160992|pts|over|9.5|401909315` |
| Jamal Murray over 22.5 Points (Pinnacle -132) | Dallas Mavericks at Denver Nuggets | -0.8% | typical outcome 24.8 against a line of 22.5; chance over: ours 56%, Pinnacle 53%; blowout risk (spread 8.5) | under the minimum edge | `prop|3936299|pts|over|22.5|401909316` |

## News on this card (adjustments.yaml)

No sourced news entries match games on this card. News is how a shown-only lane gets a staked pick, so an empty section in a busy news week is worth a look.
