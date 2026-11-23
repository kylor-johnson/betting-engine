# NFL playbook picks

How these are made: PLAYBOOK.md. Our team points come from the NFL game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.5). Full-game picks: staked. Props: on. Units: $50; A = 1 unit, B = half a unit.

**Record:** no graded picks yet; 3 open.

## Issued (staked, frozen at the number shown)

| Pick | Game | Grade | Stake | Don't bet past | Start (MT) | Why |
|---|---|---|---|---|---|---|
| Washington Commanders team total under 24 (-105) | Cincinnati Bengals at Washington Commanders | B | $25 | Washington Commanders team total under 23.5 | Mon 6:15 PM | our handicap Cincinnati Bengals 27.9, Washington Commanders 21.9 (market Cincinnati Bengals 30.2, Washington Commanders 23.8). Blended at the playbook weight, our team total number is 22.9 against Wagerhouse's 24; win chance 55.4% against 51.2% needed. |
| Ja'Marr Chase under 0.5 Touchdowns (+123) | Cincinnati Bengals at Washington Commanders | B | $25 | under 0.5 at +111 or better (a higher line is fine) | Mon 6:15 PM | typical outcome 0 against a line of 0.5; chance over: ours 51%, Pinnacle 57%; CIN at 29.3 points in our script against 30.2 in the market. Win chance 49.3% against 44.8% at Pinnacle's price. |
| DeVonta Smith under 64.5 Receiving Yards (-114) | Philadelphia Eagles at Dallas Cowboys | B | $25 | under 64.5 at -124 or better (a higher line is fine) | Thu 2:30 PM | typical outcome 52.9422 against a line of 64.5; chance over: ours 43%, Pinnacle 50%; PHI at 20.9 points in our script against 19.5 in the market. Win chance 57.4% against 53.3% at Pinnacle's price. |

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-nfl-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`); a cleared one is issued on the next read.

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Los Angeles Rams -2 (-110) | Green Bay Packers at Los Angeles Rams | +10.1% | -3.8 / -2.5 / -7.6 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401873079|side|home` |
| Miami Dolphins +3.5 (-110) | New York Jets at Miami Dolphins | +8.2% | 2.0 / 3.5 / -2.4 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401873089|side|home` |
| Over 35.5 (-110) | New England Patriots at Los Angeles Chargers | +6.4% | 38.4 / 35.5 / 43.6 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401873093|total|over` |
| Indianapolis Colts +7 (-120) | New York Giants at Indianapolis Colts | +4.4% | 5.4 / 6.5 / 2.0 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401873088|side|home` |
| Under 55.5 (-110) | Chicago Bears at Detroit Lions | +3.3% | 53.7 / 55.5 / 50.5 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401873081|total|under` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| Van Jefferson over 7.5 Receiving Yards (Pinnacle +109) | Cincinnati Bengals at Washington Commanders | +15.5% | typical outcome 24.2 against a line of 7.5; chance over: ours 63%, Pinnacle 46% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|00-0036415|receiving_yards|over|7.5|401873078` |
| Kyle Monangai over 8.5 Rush Attempts (Pinnacle -114) | Chicago Bears at Detroit Lions | +12.7% | typical outcome 14 against a line of 8.5; chance over: ours 66%, Pinnacle 50% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|00-0040236|carries|over|8.5|401873081` |
| Josh Allen under 36.5 Rushing Yards (Pinnacle -115) | Kansas City Chiefs at Buffalo Bills | +10.7% | typical outcome 16.9 against a line of 36.5; chance over: ours 36%, Pinnacle 50%; role down (8% share last two games vs 20%) (-16% on the projection) | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|00-0034857|rushing_yards|under|36.5|401873082` |
| J.K. Dobbins over 6.5 Rushing Yards (Pinnacle -114) | Denver Broncos at Pittsburgh Steelers | +9.2% | typical outcome 20.3 against a line of 6.5; chance over: ours 62%, Pinnacle 50%; role down (9% share last two games vs 40%) (-16% on the projection) | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|00-0036158|rushing_yards|over|6.5|401873083` |
| Van Jefferson over 0.5 Receptions (Pinnacle -177) | Cincinnati Bengals at Washington Commanders | +8.8% | typical outcome 2 against a line of 0.5; chance over: ours 73%, Pinnacle 61% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|00-0036415|receptions|over|0.5|401873078` |
| Jonah Coleman under 69.5 Rushing Yards (Pinnacle -114) | Denver Broncos at Pittsburgh Steelers | +8.1% | typical outcome 49.3 against a line of 69.5; chance over: ours 39%, Pinnacle 50%; role up (67% share last two games vs 45%) (+10% on the projection) | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|00-0041496|rushing_yards|under|69.5|401873083` |
| Joe Burrow under 2.5 Touchdown Passes (Pinnacle +106) | Cincinnati Bengals at Washington Commanders | +8.0% | typical outcome 2 against a line of 2.5; chance over: ours 43%, Pinnacle 54% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|00-0036442|passing_tds|under|2.5|401873078` |
| Joe Burrow under 27.5 Pass Completions (Pinnacle -112) | Cincinnati Bengals at Washington Commanders | +7.9% | typical outcome 24 against a line of 27.5; chance over: ours 39%, Pinnacle 50% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|00-0036442|completions|under|27.5|401873078` |
| Kyle Monangai over 34.5 Rushing Yards (Pinnacle -114) | Chicago Bears at Detroit Lions | +7.5% | typical outcome 55.8 against a line of 34.5; chance over: ours 61%, Pinnacle 50% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|00-0040236|rushing_yards|over|34.5|401873081` |
| Chase Brown under 0.5 Touchdowns (Pinnacle +111) | Cincinnati Bengals at Washington Commanders | +7.0% | typical outcome 0 against a line of 0.5; chance over: ours 46%, Pinnacle 55% | CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched | `prop|00-0038597|tds|under|0.5|401873078` |
