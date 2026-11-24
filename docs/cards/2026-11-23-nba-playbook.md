# NBA playbook picks

How these are made: PLAYBOOK.md. Our team points come from the NBA game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.5). Full-game picks: shown only, not staked (its walk-forward test lost; Kylor can switch it on). Props: on. Units: $25; A = 1 unit, B = half a unit.

**Record:** no graded picks yet; 3 open.

## Issued (staked, frozen at the number shown)

| Pick | Game | Grade | Stake | Don't bet past | Start (MT) | Why |
|---|---|---|---|---|---|---|
| Donovan Mitchell under 36.5 Pts & Rebs & Asts (-108) | Cleveland Cavaliers at Chicago Bulls | B | $12.5 | under 36.5 at -117 or better (a higher line is fine) | Mon 6:00 PM | typical outcome 33.2 against a line of 36.5; chance over: ours 44%, Pinnacle 51%; blowout risk (spread 8.5); CLE at 124.7 points in our script against 125.0 in the market. Win chance 56.0% against 51.9% at Pinnacle's price. |
| Brook Lopez over 12.5 Points (+118) | Los Angeles Clippers at Houston Rockets | B | $12.5 | over 12.5 at +101 or better (a lower line is fine) | Mon 6:30 PM | typical outcome 14.1 against a line of 12.5; chance over: ours 52%, Pinnacle 43%; LAC at 107.0 points in our script against 105.8 in the market. Win chance 51.7% against 45.9% at Pinnacle's price. |

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-nba-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`); a cleared one is issued on the next read.

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Over 225 (-110) | Utah Jazz at Los Angeles Lakers | +4.1% | 227.9 / 225.5 / 232.4 | CHECK held: Austin Reaves ruled out (Nov 22 18:09 MT) and Jaxson Hayes ruled out (Nov 23 14:04 MT), with Utah on the second night of a back-to-back; those explain a lower market total. | `401910044|total|over` |
| Over 226 (-110) | Oklahoma City Thunder at Indiana Pacers | +2.0% | 228.0 / 226.0 / 231.7 | under the minimum edge | `401910038|total|over` |
| Over 223 (-110) | Brooklyn Nets at Minnesota Timberwolves | +1.4% | 224.6 / 223.5 / 226.6 | under the minimum edge | `401910040|total|over` |
| Over 224 (-110) | Los Angeles Clippers at Houston Rockets | +1.0% | 225.6 / 224.5 / 227.8 | under the minimum edge | `401910043|total|over` |
| Milwaukee Bucks team total over 106 (-115) | Milwaukee Bucks at Toronto Raptors | +0.6% | 107.0 / 106.5 / 107.9 | under the minimum edge | `401910039|team_total|away_over` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| De'Aaron Fox under 15.5 Points (Pinnacle -132) | San Antonio Spurs at Sacramento Kings | +9.4% | typical outcome 10.9 against a line of 15.5; chance over: ours 34%, Pinnacle 47%; out: Dylan Harper; blowout risk (spread 12.5); listed Questionable (official report); not adjusted | CHECK held: Fox is questionable with a right shin contusion (Nov 22 18:39 MT, Jared Weiss); status unresolved, and Wembanyama is also questionable, which would change Fox's usage. | `prop|4066259|pts|under|15.5|401910045` |
| De'Aaron Fox under 25.5 Pts & Rebs & Asts (Pinnacle -121) | San Antonio Spurs at Sacramento Kings | +9.3% | typical outcome 20 against a line of 25.5; chance over: ours 36%, Pinnacle 49%; out: Dylan Harper; blowout risk (spread 12.5); listed Questionable (official report); not adjusted | CHECK held: Same as Fox points: questionable with a shin contusion (Nov 22 18:39 MT) and Wembanyama questionable; the gap may be minutes and usage the market is pricing. | `prop|4066259|pra|under|25.5|401910045` |
| Stephon Castle under 32.5 Pts & Rebs & Asts (Pinnacle -127) | San Antonio Spurs at Sacramento Kings | +9.1% | typical outcome 26 against a line of 32.5; chance over: ours 35%, Pinnacle 48%; out: Dylan Harper; blowout risk (spread 12.5) | CHECK held: Fox and Wembanyama are both questionable (Nov 22 18:39 and 21:52 MT) with Harper out; if either sits, Castle's usage rises, which the market is likely pricing. | `prop|4845367|pra|under|32.5|401910045` |
| Collin Murray-Boyles under 6.5 Rebounds (Pinnacle -135) | Milwaukee Bucks at Toronto Raptors | +7.3% | typical outcome 5 against a line of 6.5; chance over: ours 35%, Pinnacle 46% | CHECK held: Toronto center Nate Bittle ruled out (Nov 22 14:13 MT, Blake Murphy) with Barrett and Leonard also out; more rebounds for Murray-Boyles is what the market knows. | `prop|5093267|reb|under|6.5|401910039` |
| Mo Bamba under 9.5 Rebounds (Pinnacle -130) | Utah Jazz at Los Angeles Lakers | +6.9% | typical outcome 7 against a line of 9.5; chance over: ours 37%, Pinnacle 47% | CHECK held: Utah centers Jaxson Hayes (ruled out Nov 23 14:04 MT) and Jusuf Nurkic are out, leaving Bamba as the main big; that explains a higher rebound line. | `prop|4277919|reb|under|9.5|401910044` |
| De'Aaron Fox under 1.5 Threes Made (Pinnacle -175) | San Antonio Spurs at Sacramento Kings | +6.8% | typical outcome 0 against a line of 1.5; chance over: ours 30%, Pinnacle 40%; blowout risk (spread 12.5); listed Questionable (official report); not adjusted (-5% on the projection) | CHECK held: Fox questionable with a shin contusion (Nov 22 18:39 MT); status unresolved. | `prop|4066259|fg3m|under|1.5|401910045` |
| Luka Doncic under 7.5 Assists (Pinnacle +116) | Utah Jazz at Los Angeles Lakers | +6.7% | typical outcome 7 against a line of 7.5; chance over: ours 47%, Pinnacle 57%; blowout risk (spread 14) (-6% on the projection) | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|3945274|ast|under|7.5|401910044` |
| Josh Giddey under 13.5 Points (Pinnacle -108) | Cleveland Cavaliers at Chicago Bulls | +6.2% | typical outcome 11 against a line of 13.5; chance over: ours 42%, Pinnacle 51%; out: Norman Powell; second night of a back-to-back; blowout risk (spread 8.5) | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|4871145|pts|under|13.5|401910041` |
| Devin Vassell under 1.5 Threes Made (Pinnacle +122) | San Antonio Spurs at Sacramento Kings | +6.0% | typical outcome 1 against a line of 1.5; chance over: ours 49%, Pinnacle 58%; blowout risk (spread 12.5) (-4% on the projection) | CHECK held: Fox and Wembanyama are both questionable; if either sits, Vassell's shot volume rises, which the market is likely pricing. | `prop|4395630|fg3m|under|1.5|401910045` |
| Quentin Grimes under 16.5 Points (Pinnacle -119) | Utah Jazz at Los Angeles Lakers | +5.9% | typical outcome 13 against a line of 16.5; chance over: ours 40%, Pinnacle 49%; blowout risk (spread 14) (-6% on the projection) | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|4397014|pts|under|16.5|401910044` |
