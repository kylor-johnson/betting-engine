# NBA playbook picks

How these are made: PLAYBOOK.md. Our team points come from the NBA game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.25). Full-game picks: staked. Props: staked. Units: $25; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.

**Record:** 3-3-0, +0.17 units at the grade's size (-0.26 staked), closing-line value -3.0% win chance; 0 open.

## Issued (frozen at the number shown; $0 = paper)

None open.

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-nba-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`; a clear also needs `because`, a positive reason the market is wrong, and `market_assumes`, what the current number already prices); a cleared one is issued and staked like any other B pick on the next read (decision 0027).

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Over 222.5 (-110) | Chicago Bulls at Charlotte Hornets | +4.1% | 225.5 / 222.4 / 231.1 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401909318|total|over` |
| Milwaukee Bucks +1 (-110) | Brooklyn Nets at Milwaukee Bucks | +3.6% | -0.7 / 0.4 / -3.9 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401909322|side|home` |
| New York Knicks -3.5 (-110) | Cleveland Cavaliers at New York Knicks | +2.5% | -5.0 / -3.5 / -9.8 | under the minimum edge | `401909319|side|home` |
| Under 226 (-110) | San Antonio Spurs at Portland Trail Blazers | +2.1% | 223.9 / 225.8 / 220.5 | under the minimum edge | `401909325|total|under` |
| Over 230 (-110) | Los Angeles Clippers at Memphis Grizzlies | +1.4% | 231.8 / 229.4 / 236.1 | under the minimum edge | `401909321|total|over` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| Grayson Allen over 12.5 Points (Pinnacle -114) | Chicago Bulls at Charlotte Hornets | +0.6% | typical outcome 14.1 against a line of 12.5; chance over: ours 54%, Pinnacle 50%; out: Ryan Kalkbrenner; listed Questionable (official report); not adjusted (+2% on the projection) | under the minimum edge | `prop|3135045|pts|over|12.5|401909318` |
| Kenrich Williams over 8.5 Points (Pinnacle -114) | Minnesota Timberwolves at Oklahoma City Thunder | +0.3% | typical outcome 10 against a line of 8.5; chance over: ours 54%, Pinnacle 50%; out: Jaylin Williams, Aday Mara (+5% on the projection) | under the minimum edge | `prop|3133626|pts|over|8.5|401909320` |
| Grayson Allen over 2.5 Threes Made (Pinnacle -118) | Chicago Bulls at Charlotte Hornets | +0.0% | typical outcome 3 against a line of 2.5; chance over: ours 54%, Pinnacle 51%; listed Questionable (official report); not adjusted | under the minimum edge | `prop|3135045|fg3m|over|2.5|401909318` |
| Miles Bridges over 5.5 Rebounds (Pinnacle -136) | Phoenix Suns at Houston Rockets | -0.1% | typical outcome 7 against a line of 5.5; chance over: ours 58%, Pinnacle 54%; blowout risk (spread 9) (-1% on the projection) | under the minimum edge | `prop|4066383|reb|over|5.5|401909323` |
| Naz Reid over 8.5 Rebounds (Pinnacle +110) | Chicago Bulls at Charlotte Hornets | -0.1% | typical outcome 9 against a line of 8.5; chance over: ours 47%, Pinnacle 45% | under the minimum edge | `prop|4396971|reb|over|8.5|401909318` |
| Rudy Gobert under 8.5 Points (Pinnacle -102) | Minnesota Timberwolves at Oklahoma City Thunder | -0.2% | typical outcome 7 against a line of 8.5; chance over: ours 50%, Pinnacle 53% | under the minimum edge | `prop|3032976|pts|under|8.5|401909320` |
| Dillon Brooks over 1.5 Threes Made (Pinnacle -125) | Phoenix Suns at Houston Rockets | -0.5% | typical outcome 2 against a line of 1.5; chance over: ours 55%, Pinnacle 52%; blowout risk (spread 9) (-1% on the projection) | under the minimum edge | `prop|3155526|fg3m|over|1.5|401909323` |
| Ayo Dosunmu over 1.5 Threes Made (Pinnacle -152) | Minnesota Timberwolves at Oklahoma City Thunder | -0.6% | typical outcome 2 against a line of 1.5; chance over: ours 60%, Pinnacle 56% | under the minimum edge | `prop|4397002|fg3m|over|1.5|401909320` |
| Josh Giddey over 8.5 Assists (Pinnacle -148) | Chicago Bulls at Charlotte Hornets | -0.8% | typical outcome 9 against a line of 8.5; chance over: ours 59%, Pinnacle 56%; out: Norman Powell (+6% on the projection) | under the minimum edge | `prop|4871145|ast|over|8.5|401909318` |
| Brandon Miller under 22.5 Points (Pinnacle -136) | Chicago Bulls at Charlotte Hornets | -0.8% | typical outcome 19.1 against a line of 22.5; chance over: ours 43%, Pinnacle 46%; out: Ryan Kalkbrenner (+2% on the projection) | under the minimum edge | `prop|4433287|pts|under|22.5|401909318` |

## News on this card (adjustments.yaml)

No sourced news entries match games on this card. News is how a shown-only lane gets a staked pick, so an empty section in a busy news week is worth a look.
