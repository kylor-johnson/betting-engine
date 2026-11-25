# NFL playbook picks

How these are made: PLAYBOOK.md. Our team points come from the NFL game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.15). Full-game picks: staked. Props: staked. Units: $50; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.

**Record:** 3-0-0, +1.51 units at the grade's size (+1.51 staked), closing-line value -1.0% win chance; 6 open.

## Issued (frozen at the number shown; $0 = paper)

| Pick | Game | Grade | Stake | Don't bet past | Start (MT) | Why |
|---|---|---|---|---|---|---|
| Under 55.5 (-110) | Chicago Bears at Detroit Lions | B | $25 | Under 55 | Thu 11:00 AM | our handicap Chicago Bears 23.6, Detroit Lions 27.5 (market Chicago Bears 28.2, Detroit Lions 26.9). Blended at the playbook weight, our total number is 53.7 against Wagerhouse's 55.5; win chance 55.6% against 52.4% needed. |
| DeVonta Smith under 64.5 Receiving Yards (-114) | Philadelphia Eagles at Dallas Cowboys | B | $25 | under 64.5 at -124 or better (a higher line is fine) | Thu 2:30 PM | typical outcome 52.9422 against a line of 64.5; chance over: ours 43%, Pinnacle 50%; PHI at 20.9 points in our script against 19.5 in the market. Win chance 57.4% against 53.3% at Pinnacle's price. |
| Josh Allen over 244.5 Passing Yards (+148) | Kansas City Chiefs at Buffalo Bills | B | $25 | over 244.5 at +136 or better (a lower line is fine) | Thu 6:20 PM | typical outcome 246.4 against a line of 244.5; chance over: ours 44%, Pinnacle 38%; BUF at 25.3 points in our script against 25.5 in the market. Win chance 44.3% against 40.3% at Pinnacle's price. |
| Under 48 (-110) | Kansas City Chiefs at Buffalo Bills | B | $25 | Under 47.5 | Thu 6:20 PM | our handicap Kansas City Chiefs 19.6, Buffalo Bills 24.1 (market Kansas City Chiefs 22.5, Buffalo Bills 25.0). Blended at the playbook weight, our total number is 46.2 against Wagerhouse's 48; win chance 55.6% against 52.4% needed. |
| Under 42.5 (-110) | Atlanta Falcons at Minnesota Vikings | B | $25 | Under 41.5 | Sun 11:00 AM | our handicap Atlanta Falcons 17.2, Minnesota Vikings 21.3 (market Atlanta Falcons 17.2, Minnesota Vikings 24.2). Blended at the playbook weight, our total number is 40.4 against Wagerhouse's 42.5; win chance 56.5% against 52.4% needed. |
| Tennessee Titans +15 (-110) | Tennessee Titans at Jacksonville Jaguars | B | $25 | Tennessee Titans +14.5 | Sun 11:00 AM | our handicap Tennessee Titans 20.1, Jacksonville Jaguars 31.0 (market Tennessee Titans 16.5, Jacksonville Jaguars 31.0). Blended at the playbook weight, our side number is -13.6 against Wagerhouse's -15; win chance 56.4% against 52.4% needed. |

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-nfl-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`; a clear also needs `because`, a positive reason the market is wrong, and `market_assumes`, what the current number already prices); a cleared one is issued and staked like any other B pick on the next read (decision 0027).

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Miami Dolphins +3.5 (-110) | New York Jets at Miami Dolphins | +8.5% | 1.9 / 3.5 / -2.6 | CHECK held: Malik Willis is on injured reserve with a groin/core injury (Hafley Monday, via Joe Schad, ESPN feed Nov 23 10:19 MT) and Kyle McCord starts; the model assumes the usual starter. No change this morning. | `401873089|side|home` |
| Over 35.5 (-110) | New England Patriots at Los Angeles Chargers | +8.2% | 38.9 / 35.2 / 45.8 | CHECK held: Drake Maye is out and Tommy DeVito starts (Vrabel via Mike Reiss, ESPN feed Nov 23 18:15 MT), and Justin Herbert is in the concussion protocol, still listed Questionable (The Athletic, Nov 22 17:32 MT). The model assumes both usual starters; a 35.5 total prices a backup and a doubtful Herbert. | `401873093|total|over` |
| Los Angeles Rams -2.5 (-110) | Green Bay Packers at Los Angeles Rams | +7.7% | -3.6 / -2.7 / -6.2 | CHECK held: Rams are without Puka Nacua (MCL surgery, ESPN feed Nov 21 18:25 MT), Davante Adams (IR) and Steve Avila; Green Bay lists Micah Parsons out and Josh Jacobs Questionable after a limited Monday practice (Matt Schneidman, The Athletic, ESPN feed Nov 23 14:35 MT). The market knows this and the play-by-play model does not. | `401873079|side|home` |
| Over 36.5 (-110) | Denver Broncos at Pittsburgh Steelers | +5.1% | 38.9 / 36.8 / 43.0 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401873083|total|over` |
| Indianapolis Colts +6.5 (-110) | New York Giants at Indianapolis Colts | +4.2% | 4.9 / 6.2 / 1.0 | CHECK held: Colts waived Daniel Jones and named Anthony Richardson the starter (Steichen, ESPN feed Nov 20 11:16 MT), and signed Shane Buechele Tuesday (ESPN feed Nov 24 15:05 MT); tackles Raimann and Travis and corners Gardner and Ward are listed out. The model's usual starter is wrong. | `401873088|side|home` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| Emmett Johnson under 80.5 Rushing Yards (Pinnacle -110) | Kansas City Chiefs at Buffalo Bills | +3.6% | typical outcome 34.8 against a line of 80.5; chance over: ours 44%, Pinnacle 50%; role up (78% share last two games vs 29%) (+19% on the projection) | under the minimum edge | `prop|00-0041013|rushing_yards|under|80.5|401873082` |
| Kyle Monangai over 8.5 Rush Attempts (Pinnacle -111) | Chicago Bears at Detroit Lions | +2.4% | typical outcome 14 against a line of 8.5; chance over: ours 55%, Pinnacle 50% | under the minimum edge | `prop|00-0040236|carries|over|8.5|401873081` |
| Emmett Johnson under 19.5 Rush Attempts (Pinnacle -126) | Kansas City Chiefs at Buffalo Bills | +2.2% | typical outcome 11 against a line of 19.5; chance over: ours 42%, Pinnacle 48%; role up (78% share last two games vs 29%) (+19% on the projection) | under the minimum edge | `prop|00-0041013|carries|under|19.5|401873082` |
| Josh Allen under 36.5 Rushing Yards (Pinnacle -108) | Kansas City Chiefs at Buffalo Bills | +2.0% | typical outcome 16.9 against a line of 36.5; chance over: ours 46%, Pinnacle 50%; role down (8% share last two games vs 20%) (-16% on the projection) | under the minimum edge | `prop|00-0034857|rushing_yards|under|36.5|401873082` |
| Saquon Barkley under 15.5 Rush Attempts (Pinnacle +109) | Philadelphia Eagles at Dallas Cowboys | +1.7% | typical outcome 13 against a line of 15.5; chance over: ours 50%, Pinnacle 54%; role up (59% share last two games vs 50%) (+4% on the projection) | under the minimum edge | `prop|00-0034844|carries|under|15.5|401873080` |
| MarShawn Lloyd over 0.5 Touchdowns (Pinnacle +465) | Green Bay Packers at Los Angeles Rams | +1.4% | typical outcome 0 against a line of 0.5; chance over: ours 19%, Pinnacle 17% | under the minimum edge | `prop|00-0039811|tds|over|0.5|401873079` |
| Xavier Worthy over 2.5 Receptions (Pinnacle +160) | Kansas City Chiefs at Buffalo Bills | +1.3% | typical outcome 3 against a line of 2.5; chance over: ours 40%, Pinnacle 37% | under the minimum edge | `prop|00-0039894|receptions|over|2.5|401873082` |
| Emmett Johnson under 0.5 Touchdowns (Pinnacle +129) | Kansas City Chiefs at Buffalo Bills | +1.1% | typical outcome 0 against a line of 0.5; chance over: ours 55%, Pinnacle 58% | under the minimum edge | `prop|00-0041013|tds|under|0.5|401873082` |
| Caleb Williams under 1.5 Touchdown Passes (Pinnacle +167) | Chicago Bears at Detroit Lions | +0.9% | typical outcome 1 against a line of 1.5; chance over: ours 62%, Pinnacle 64% | under the minimum edge | `prop|00-0039918|passing_tds|under|1.5|401873081` |
| Justin Jefferson under 85.5 Receiving Yards (Pinnacle -114) | Atlanta Falcons at Minnesota Vikings | +0.8% | typical outcome 52.3 against a line of 85.5; chance over: ours 46%, Pinnacle 50% | under the minimum edge | `prop|00-0036322|receiving_yards|under|85.5|401873084` |

## News on this card (adjustments.yaml)

| Game | Entry | Counted? |
|---|---|---|
| Denver Broncos at Pittsburgh Steelers | Pittsburgh Steelers -2.5: Mason Rudolph will start Friday against Denver in place of Aaron Rodgers (Tom Pelissero, Rotoworld relay via ESPN feed, Nov 24 21:25 MT); Rodgers was not at the | yes: partly priced: Pinnacle moved +1 of the +2.5 expected, -1.5 points still applied |

## Paper lanes ($0, not sent; decision 0036; record in docs/lanes/PAPER-LANES.md)

| Lane | Bet | Price | Why |
|---|---|---|---|
| Wagerhouse trailing Pinnacle | Chicago Bears -1.5 (Chicago Bears at Detroit Lions) | -110 | Wagerhouse +1.5, Pinnacle +2.5 (home spread) |
| Wagerhouse trailing Pinnacle | Kansas City Chiefs +3 (Kansas City Chiefs at Buffalo Bills) | -120 | Wagerhouse -3, Pinnacle -2.5 (home spread) |
| Wagerhouse trailing Pinnacle | Pittsburgh Steelers +3 (Denver Broncos at Pittsburgh Steelers) | -120 | Wagerhouse +3, Pinnacle +2.5 (home spread) |
| Wagerhouse trailing Pinnacle | Under 37 (Denver Broncos at Pittsburgh Steelers) | -110 | Wagerhouse 37, Pinnacle 36 |
| Wagerhouse trailing Pinnacle | Denver Broncos -3 (Denver Broncos at Pittsburgh Steelers) | -120 | Wagerhouse +3, Pinnacle +3.5 (home spread) |
| Wagerhouse trailing Pinnacle | Baltimore Ravens +7 (Baltimore Ravens at Houston Texans) | -120 | Wagerhouse -7, Pinnacle -6.5 (home spread) |
| Wagerhouse trailing Pinnacle | Over 40 (New York Jets at Miami Dolphins) | -110 | Wagerhouse 40, Pinnacle 41 |
| Wagerhouse trailing Pinnacle | Los Angeles Chargers pick (New England Patriots at Los Angeles Chargers) | -110 | Wagerhouse -0, Pinnacle -1 (home spread) |
| NFL derivatives (halves, team totals) | 1st Half Over 17.5 (New England Patriots at Los Angeles Chargers) | +102 | 1st Half total: ours 18.4 against Pinnacle 17.5 (+102), +4.6% |
| Wagerhouse trailing Pinnacle | Washington Commanders -7 (Washington Commanders at Arizona Cardinals) | -110 | Wagerhouse +7, Pinnacle +7.5 (home spread) |
| Wagerhouse trailing Pinnacle | Seattle Seahawks +3 (Seattle Seahawks at San Francisco 49ers) | -120 | Wagerhouse -3, Pinnacle -2.5 (home spread) |
| Wagerhouse trailing Pinnacle | Over 40.5 (Las Vegas Raiders at Cleveland Browns) | -110 | Wagerhouse 40.5, Pinnacle 41.5 |
