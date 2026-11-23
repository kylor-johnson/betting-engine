# NBA playbook picks

How these are made: PLAYBOOK.md. Our team points come from the NBA game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.5). Full-game picks: shown only, not staked (its walk-forward test lost; Kylor can switch it on). Props: on. Units: $25; A = 1 unit, B = half a unit.

**Record:** no graded picks yet; 2 open.

## Issued (staked, frozen at the number shown)

| Pick | Game | Grade | Stake | Don't bet past | Start (MT) | Why |
|---|---|---|---|---|---|---|
| Coby White under 1.5 Threes Made (+146) | Memphis Grizzlies at Charlotte Hornets | B | $12.5 | under 1.5 at +134 or better (a higher line is fine) | Mon 5:00 PM | typical outcome 1 against a line of 1.5; chance over: ours 55%, Pinnacle 62%; CHA at 108.7 points in our script against 105.8 in the market. Win chance 44.7% against 40.7% at Pinnacle's price. |
| Donovan Mitchell under 36.5 Pts & Rebs & Asts (-108) | Cleveland Cavaliers at Chicago Bulls | B | $12.5 | under 36.5 at -117 or better (a higher line is fine) | Mon 6:00 PM | typical outcome 33.2 against a line of 36.5; chance over: ours 44%, Pinnacle 51%; blowout risk (spread 8.5); CLE at 124.7 points in our script against 125.0 in the market. Win chance 56.0% against 51.9% at Pinnacle's price. |

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-nba-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`); a cleared one is issued on the next read.

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Charlotte Hornets team total over 105.5 (-115) | Memphis Grizzlies at Charlotte Hornets | +8.3% | 108.6 / 105.5 / 113.1 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401910036|team_total|home_over` |
| Over 225 (-110) | Utah Jazz at Los Angeles Lakers | +4.1% | 227.9 / 225.5 / 232.4 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401910044|total|over` |
| Over 223 (-110) | Brooklyn Nets at Minnesota Timberwolves | +1.4% | 224.6 / 223.5 / 226.6 | under the minimum edge | `401910040|total|over` |
| Under 230.5 (-110) | Portland Trail Blazers at Philadelphia 76ers | +1.1% | 228.9 / 230.5 / 226.0 | under the minimum edge | `401910037|total|under` |
| Over 224 (-110) | Los Angeles Clippers at Houston Rockets | +1.0% | 225.6 / 224.5 / 227.8 | under the minimum edge | `401910043|total|over` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| De'Aaron Fox under 15.5 Points (Pinnacle -132) | San Antonio Spurs at Sacramento Kings | +9.4% | typical outcome 10.9 against a line of 15.5; chance over: ours 34%, Pinnacle 47%; out: Dylan Harper; blowout risk (spread 12.5); listed Questionable (official report); not adjusted | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|4066259|pts|under|15.5|401910045` |
| De'Aaron Fox under 25.5 Pts & Rebs & Asts (Pinnacle -121) | San Antonio Spurs at Sacramento Kings | +9.3% | typical outcome 20 against a line of 25.5; chance over: ours 36%, Pinnacle 49%; out: Dylan Harper; blowout risk (spread 12.5); listed Questionable (official report); not adjusted | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|4066259|pra|under|25.5|401910045` |
| Stephon Castle under 32.5 Pts & Rebs & Asts (Pinnacle -127) | San Antonio Spurs at Sacramento Kings | +9.1% | typical outcome 26 against a line of 32.5; chance over: ours 35%, Pinnacle 48%; out: Dylan Harper; blowout risk (spread 12.5) | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|4845367|pra|under|32.5|401910045` |
| Collin Murray-Boyles under 6.5 Rebounds (Pinnacle -135) | Milwaukee Bucks at Toronto Raptors | +7.3% | typical outcome 5 against a line of 6.5; chance over: ours 35%, Pinnacle 46% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|5093267|reb|under|6.5|401910039` |
| De'Aaron Fox under 1.5 Threes Made (Pinnacle -174) | San Antonio Spurs at Sacramento Kings | +7.0% | typical outcome 0 against a line of 1.5; chance over: ours 30%, Pinnacle 40%; blowout risk (spread 12.5); listed Questionable (official report); not adjusted (-5% on the projection) | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|4066259|fg3m|under|1.5|401910045` |
| Mo Bamba under 9.5 Rebounds (Pinnacle -130) | Utah Jazz at Los Angeles Lakers | +6.9% | typical outcome 7 against a line of 9.5; chance over: ours 37%, Pinnacle 47% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|4277919|reb|under|9.5|401910044` |
| Sidy Cissoko over 1.5 Threes Made (Pinnacle +198) | Portland Trail Blazers at Philadelphia 76ers | +6.5% | typical outcome 1 against a line of 1.5; chance over: ours 40%, Pinnacle 31% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|5081727|fg3m|over|1.5|401910037` |
| VJ Edgecombe over 3.5 Assists (Pinnacle +113) | Portland Trail Blazers at Philadelphia 76ers | +6.5% | typical outcome 4 against a line of 3.5; chance over: ours 53%, Pinnacle 44%; out: Joel Embiid (+6% on the projection) | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|5124612|ast|over|3.5|401910037` |
| Devin Vassell under 1.5 Threes Made (Pinnacle +122) | San Antonio Spurs at Sacramento Kings | +6.0% | typical outcome 1 against a line of 1.5; chance over: ours 49%, Pinnacle 58%; blowout risk (spread 12.5) (-4% on the projection) | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|4395630|fg3m|under|1.5|401910045` |
| Brook Lopez over 12.5 Points (Pinnacle +118) | Los Angeles Clippers at Houston Rockets | +5.9% | typical outcome 14.1 against a line of 12.5; chance over: ours 52%, Pinnacle 43% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|3448|pts|over|12.5|401910043` |
