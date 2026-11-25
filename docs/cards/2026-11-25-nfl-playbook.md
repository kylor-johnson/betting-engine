# NFL playbook picks

How these are made: PLAYBOOK.md. Our team points come from the NFL game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.15). Full-game picks: staked. Props: staked. Units: $50; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.

**Record:** 3-0-0, +1.51 units at the grade's size (+1.51 staked), closing-line value -1.0% win chance; 7 open.

## Issued (frozen at the number shown; $0 = paper)

| Pick | Game | Grade | Stake | Don't bet past | Start (MT) | Why |
|---|---|---|---|---|---|---|
| Under 55.5 (-110) | Chicago Bears at Detroit Lions | B | $25 | Under 55 | Thu 11:00 AM | our handicap Chicago Bears 23.6, Detroit Lions 27.5 (market Chicago Bears 28.2, Detroit Lions 26.9). Blended at the playbook weight, our total number is 53.7 against Wagerhouse's 55.5; win chance 55.6% against 52.4% needed. |
| DeVonta Smith under 64.5 Receiving Yards (-114) | Philadelphia Eagles at Dallas Cowboys | B | $25 | under 64.5 at -124 or better (a higher line is fine) | Thu 2:30 PM | typical outcome 52.9422 against a line of 64.5; chance over: ours 43%, Pinnacle 50%; PHI at 20.9 points in our script against 19.5 in the market. Win chance 57.4% against 53.3% at Pinnacle's price. |
| Josh Allen over 244.5 Passing Yards (+148) | Kansas City Chiefs at Buffalo Bills | B | $25 | over 244.5 at +136 or better (a lower line is fine) | Thu 6:20 PM | typical outcome 246.4 against a line of 244.5; chance over: ours 44%, Pinnacle 38%; BUF at 25.3 points in our script against 25.5 in the market. Win chance 44.3% against 40.3% at Pinnacle's price. |
| Under 48 (-110) | Kansas City Chiefs at Buffalo Bills | B | $25 | Under 47.5 | Thu 6:20 PM | our handicap Kansas City Chiefs 19.6, Buffalo Bills 24.1 (market Kansas City Chiefs 22.5, Buffalo Bills 25.0). Blended at the playbook weight, our total number is 46.2 against Wagerhouse's 48; win chance 55.6% against 52.4% needed. |
| Pittsburgh Steelers +3 (-120) | Denver Broncos at Pittsburgh Steelers | B | paper | Pittsburgh Steelers +3 | Fri 1:00 PM | our handicap Denver Broncos 20.0, Pittsburgh Steelers 20.5 (market Denver Broncos 20.2, Pittsburgh Steelers 17.8). Blended at the playbook weight, our side number is 1.8 against Wagerhouse's 3; win chance 57.8% against 54.5% needed. |
| Under 42.5 (-110) | Atlanta Falcons at Minnesota Vikings | B | $25 | Under 41.5 | Sun 11:00 AM | our handicap Atlanta Falcons 17.2, Minnesota Vikings 21.3 (market Atlanta Falcons 17.2, Minnesota Vikings 24.2). Blended at the playbook weight, our total number is 40.4 against Wagerhouse's 42.5; win chance 56.5% against 52.4% needed. |
| Tennessee Titans +15 (-110) | Tennessee Titans at Jacksonville Jaguars | B | $25 | Tennessee Titans +14.5 | Sun 11:00 AM | our handicap Tennessee Titans 20.1, Jacksonville Jaguars 31.0 (market Tennessee Titans 16.5, Jacksonville Jaguars 31.0). Blended at the playbook weight, our side number is -13.6 against Wagerhouse's -15; win chance 56.4% against 52.4% needed. |

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-nfl-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`; a clear also needs `because`, a positive reason the market is wrong, and `market_assumes`, what the current number already prices); a cleared one is issued and staked like any other B pick on the next read (decision 0027).

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Miami Dolphins +3.5 (-110) | New York Jets at Miami Dolphins | +8.5% | 1.9 / 3.5 / -2.6 | CHECK held: Malik Willis is on injured reserve with a groin/core injury (Hafley Monday, via Joe Schad, ESPN feed Nov 23 10:19 MT) and Kyle McCord starts; the model assumes the usual starter. | `401873089|side|home` |
| Pittsburgh Steelers +3.5 (-110) | Denver Broncos at Pittsburgh Steelers | +7.0% | 2.5 / 3.5 / -0.5 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401873083|side|home` |
| Arizona Cardinals +7.5 (-110) | Washington Commanders at Arizona Cardinals | +6.6% | 5.8 / 6.8 / 2.7 | CHECK held: Same game as the total row: Arizona's quarterback is unsettled. Josh Johnson started Sunday's 34-7 loss, Gardner Minshew II is on injured reserve after UCL surgery (ESPN, Nov 17), and Carson Beck is Questionable with no note (ESPN feed Nov 24 05:39 MT). The model assumes the usual starter; Washington at 7.5 on the road already prices a backup, and Pinnacle has no line to clear against. | `401873092|side|home` |
| Los Angeles Rams -2.5 (-110) | Green Bay Packers at Los Angeles Rams | +6.4% | -3.4 / -2.4 / -6.2 | CHECK held: Rams are without Puka Nacua (MCL surgery, out 4 to 5 months, ESPN feed Nov 21 18:25 MT), Davante Adams (IR) and Steve Avila; Green Bay lists Micah Parsons out, and Josh Jacobs is now Questionable after a limited Monday practice (Matt Schneidman, The Athletic, ESPN feed Nov 23 14:35 MT). The market knows this and the play-by-play model does not. | `401873079|side|home` |
| Over 35.5 (-110) | New England Patriots at Los Angeles Chargers | +5.2% | 37.9 / 35.2 / 43.1 | CHECK held: Drake Maye is out and Tommy DeVito starts (Vrabel via Mike Reiss, ESPN feed Nov 23 18:15 MT), and Justin Herbert is in the concussion protocol (The Athletic, Nov 22 17:32 MT); Pinnacle has no line on the game. | `401873093|total|over` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| Justin Jefferson under 6.5 Receptions (Pinnacle -106) | Atlanta Falcons at Minnesota Vikings | +1.3% | typical outcome 5 against a line of 6.5; chance over: ours 47%, Pinnacle 52% | under the minimum edge | `prop|00-0036322|receptions|under|6.5|401873084` |
| Kyle Monangai over 8.5 Rush Attempts (Pinnacle -116) | Chicago Bears at Detroit Lions | +1.2% | typical outcome 14 against a line of 8.5; chance over: ours 55%, Pinnacle 50% | under the minimum edge | `prop|00-0040236|carries|over|8.5|401873081` |
| Josh Allen under 36.5 Rushing Yards (Pinnacle -112) | Kansas City Chiefs at Buffalo Bills | +0.9% | typical outcome 17.2 against a line of 36.5; chance over: ours 46%, Pinnacle 51%; role down (8% share last two games vs 20%) (-16% on the projection) | under the minimum edge | `prop|00-0034857|rushing_yards|under|36.5|401873082` |
| Justin Jefferson under 85.5 Receiving Yards (Pinnacle -114) | Atlanta Falcons at Minnesota Vikings | +0.8% | typical outcome 52.3 against a line of 85.5; chance over: ours 46%, Pinnacle 50% | under the minimum edge | `prop|00-0036322|receiving_yards|under|85.5|401873084` |
| Saquon Barkley under 15.5 Rush Attempts (Pinnacle +104) | Philadelphia Eagles at Dallas Cowboys | +0.7% | typical outcome 13 against a line of 15.5; chance over: ours 50%, Pinnacle 54%; role up (59% share last two games vs 50%) (+4% on the projection) | under the minimum edge | `prop|00-0034844|carries|under|15.5|401873080` |
| Jauan Jennings under 30.5 Receiving Yards (Pinnacle -114) | Atlanta Falcons at Minnesota Vikings | +0.3% | typical outcome 14.5 against a line of 30.5; chance over: ours 46%, Pinnacle 50% | under the minimum edge | `prop|00-0036259|receiving_yards|under|30.5|401873084` |
| Kaleb Johnson under 10.5 Rush Attempts (Pinnacle -136) | Green Bay Packers at Los Angeles Rams | +0.2% | typical outcome 6 against a line of 10.5; chance over: ours 42%, Pinnacle 45%; role up (51% share last two games vs 28%) (+15% on the projection) | under the minimum edge | `prop|00-0040142|carries|under|10.5|401873079` |
| Caleb Williams under 1.5 Touchdown Passes (Pinnacle +162) | Chicago Bears at Detroit Lions | +0.2% | typical outcome 1 against a line of 1.5; chance over: ours 62%, Pinnacle 64% | under the minimum edge | `prop|00-0039918|passing_tds|under|1.5|401873081` |
| Kyle Monangai over 34.5 Rushing Yards (Pinnacle -114) | Chicago Bears at Detroit Lions | -0.1% | typical outcome 55.6 against a line of 34.5; chance over: ours 53%, Pinnacle 50% | under the minimum edge | `prop|00-0040236|rushing_yards|over|34.5|401873081` |
| Xavier Worthy over 2.5 Receptions (Pinnacle +130) | Kansas City Chiefs at Buffalo Bills | -0.4% | typical outcome 3 against a line of 2.5; chance over: ours 43%, Pinnacle 41% | under the minimum edge | `prop|00-0039894|receptions|over|2.5|401873082` |

## News on this card (adjustments.yaml)

| Game | Entry | Counted? |
|---|---|---|
| Baltimore Ravens at Houston Texans | Baltimore Ravens -3: Lamar Jackson on injured reserve after right thumb surgery (ESPN feed Nov 18: chance of a Week 16 return); Jacoby Brissett starts. Hurt on the first snap of the | NO: not applied: no news_at time on the entry, so it cannot be shown unpriced |
| New England Patriots at Los Angeles Chargers | New England Patriots -5.0: Drake Maye out with a fractured right fibula (reported Nov 20); Tommy DeVito named the starter for Nov 29. None of this is in the ratings. [https://www.espn.com | NO: not applied: larger than the 3-point limit for NFL, decision 0036; split it or size it down with a reason |

## Paper lanes ($0, not sent; decision 0036; record in docs/lanes/PAPER-LANES.md)

| Lane | Bet | Price | Why |
|---|---|---|---|
| Wagerhouse trailing Pinnacle | Chicago Bears -1.5 (Chicago Bears at Detroit Lions) | -110 | Wagerhouse +1.5, Pinnacle +2.5 (home spread) |
| Wagerhouse trailing Pinnacle | Kansas City Chiefs +3 (Kansas City Chiefs at Buffalo Bills) | -120 | Wagerhouse -3, Pinnacle -2.5 (home spread) |
| Wagerhouse trailing Pinnacle | Pittsburgh Steelers +3 (Denver Broncos at Pittsburgh Steelers) | -120 | Wagerhouse +3, Pinnacle +2.5 (home spread) |
| Wagerhouse trailing Pinnacle | Under 37 (Denver Broncos at Pittsburgh Steelers) | -110 | Wagerhouse 37, Pinnacle 36 |
| Wagerhouse trailing Pinnacle | Baltimore Ravens +7 (Baltimore Ravens at Houston Texans) | -120 | Wagerhouse -7, Pinnacle -6.5 (home spread) |
| Wagerhouse trailing Pinnacle | Over 40 (New York Jets at Miami Dolphins) | -110 | Wagerhouse 40, Pinnacle 41 |
| Wagerhouse trailing Pinnacle | Los Angeles Chargers pick (New England Patriots at Los Angeles Chargers) | -110 | Wagerhouse -0, Pinnacle -1 (home spread) |
| NFL derivatives (halves, team totals) | 1st Half Over 17.5 (New England Patriots at Los Angeles Chargers) | +102 | 1st Half total: ours 18.4 against Pinnacle 17.5 (+102), +4.6% |
| Wagerhouse trailing Pinnacle | Washington Commanders -7 (Washington Commanders at Arizona Cardinals) | -110 | Wagerhouse +7, Pinnacle +7.5 (home spread) |
| Wagerhouse trailing Pinnacle | Over 40.5 (Las Vegas Raiders at Cleveland Browns) | -110 | Wagerhouse 40.5, Pinnacle 41.5 |
