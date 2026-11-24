# Playbook: how this engine picks bets

**Approved 2026-11-23 (decision 0018); built the same night (decisions 0019 to 0022); kept in line with the charter by decision 0027.** This file sits next to `CHARTER.md` and outranks every handoff, prompt and research note on *how a pick is chosen*. The charter owns the purpose, what reaches Telegram, the money rules (units, cap, stops) and the locked rules. This file never quotes a dollar amount.

## 1. What changed and why

Until now the engine treated Pinnacle's line as the truth and looked for places where Wagerhouse disagreed with it. That is a price checker. It produces almost no picks, and when it does, they are about the book, not the game.

**From here on, the engine handicaps the game and picks the bets its own handicap says are good.** Other books are one input. They are a sanity check and a price filter, never the reason for a pick and never the thing that decides it.

## 2. The method in one paragraph

First, predict how each game will play out (the **game script**): who leads, by how much, how many plays, how often each team passes. Then adjust that script for injuries, weather, rest and travel. Then price every market that script touches (team totals, game total, side, player props, halves), using the engine's own numbers. Bet the ones where our number beats Wagerhouse's by enough, starting with the markets where the method has the most room: props and team totals first, sides last.

## 3. Step by step (what code does for every game)

### Step 1: the script

| Piece | How it is built | Data we have |
|---|---|---|
| Implied team points | From the spread and total (Bills −16.5, total 45 → 30.75 to 14.25) | Wagerhouse lines, every read |
| Expected lead path | Implied margin, plus how often teams with this margin lead at halftime | nflverse play-by-play 2015+ |
| Plays per team | Neutral-situation pace (seconds per play when the score is within 7), adjusted for the expected lead: leaders slow down, trailers speed up | Play-by-play |
| Pass rate | Pass rate over expected (PROE) in neutral situations, then shifted by the expected lead (trailing teams throw more) | Play-by-play has `pass_oe` and `xpass` |
| Throw out outliers | Games against the league's top and bottom 3 defenses get half weight in a team's averages | Tested, no held-out gain, off (research 17) |

### Step 2: adjust the script

| Adjustment | Rule | Status |
|---|---|---|
| Quarterback out | Backup's own numbers if he has 100+ dropbacks; otherwise a league-average replacement-level drop | Measured: QB news moves lines about 2.5 to 2.7 points (research 14, 2b) |
| Sourced news, every sport | The research agent's `adjustments.yaml` entries move our number by the part Pinnacle has not moved for since the news broke; added after the blend, at full size. In a shown-only lane (college), a pick is staked only when that news is what clears the bar (a news pick) | Live (decision 0029). College starter out = about 3.5 points (research 21) |
| Injury clusters | Two or more starters out in one unit (OL, DL, secondary) shift that matchup: rushing efficiency up against a gutted defensive line, targets up against backup corners | Tested, no held-out gain, off (research 17) |
| Who absorbs the volume | A player out → his targets, carries or minutes go to teammates by their recent share. A player returning → the others lose share | Built in both props models; the history says the target bump is smaller than people expect (research 06) |
| Wind | 8 mph or more starts to matter; scaled per mph | Tested: 10 to 19 mph Unders hit 56 to 60% (research 04, 05); effect weaker since 2024. The script's totals lead used actual kickoff wind, not the forecast; re-test on forecasts (research 18) |
| Rain | Fewer passing yards | Live input to the NFL script since it was built; not tested on its own |
| Rest and travel | Short week, off a bye, long trip, altitude | NBA tested and already priced (research 14, 2d); NFL not tested |
| Referees | Crew penalty and total history | Tested, no held-out gain, off (research 17) |
| Look-ahead and trap spots | Rivalry or big game next week | Folklore until tested; tracked, zero weight |

### Step 3: our number for every market

From the adjusted script, the engine prices:

1. **Player props**: usage (target share, carries, snap share, air yards; minutes for the NBA) × the script's team points and expected margin, read off the median (books price the median, not the average). Coverage type is not buildable (free data has 2023 only); blitz and box splits were tested and are off (research 17).
2. **Team totals**: each offense's scoring per drive against this defense, times the script's drives.
3. **Game total**: the two team totals added up, plus weather.
4. **Side**: the difference between the team totals, priced with how real games land (3 and 7 matter).
5. **First half and quarters**: not built. Period lines and team totals are logged only.

### Step 4: decide

For each market, **edge = our chance of winning − the chance Wagerhouse's price needs** (52.4% at −110).

| Market | Minimum edge to be a pick | Why this order |
|---|---|---|
| Player props | 4% | Where the script method lives; smaller limits, softer lines |
| Team totals | 3% | One offense against one defense is the cleanest read |
| Game totals | 3% | Script plus weather |
| First half and quarters | 4% | Thinner data |
| Sides | 3% | The hardest market; also the one most tests have failed in |

**Where the market comes in, and only here:**
- **Price filter.** Never bet a number worse than ours. If another book has a better number than Wagerhouse, the card says so (you can't bet it, but it tells you Wagerhouse is worse).
- **Sanity check, not a veto.** If our number is far from the market (3+ points on a side, 4+ on a total, 15+ points of chance on a prop), the pick is marked **CHECK**. A gap that big usually means news we don't have. The research agent must find what the market knows before it can go out. "Nothing found" is a hold. A clear needs a positive sourced reason the market is wrong and what the current number already assumes (decision 0025); a cleared pick is staked and sent like any other B pick in a staked lane (decision 0027); in the shown-only lanes (NBA and college full-game) it is staked only if it is also a news pick (decision 0029). These distances are the NFL's; NBA uses 4 / 6 / 5 and college 6 / 7 / 6 points (side / total / team total).
- **Blend.** Our number is pulled part of the way toward the market before the edge is computed. That is the one lesson every serious modeller agrees on (Benter: a model that ignores the market loses to it). Starting weight on **our** number: props 0.5, team totals 0.4, totals 0.35, sides 0.25. A weight changes only after 40 graded candidates, by a session, with a decision note (decision 0022); `engine playbook-record` shows the fitted weight against the current one.

### Step 5: always produce picks

**Every slate gets a pick list.** For each lane, it shows the top picks by edge with a grade. Caps: full-game, 5 a week for NFL and college and 2 a day for the NBA; props, 10 a week and 2 a game for the NFL, 4 a day and 2 a game for the NBA; one unit a game across everything. A pick past a cap is paper.

- **A**: clears the minimum edge, no CHECK flag, and the principle behind it has passed a test.
- **B**: clears the minimum edge; the principle is untested or the pick is CHECK-cleared.
- **C**: the best the model has that day, under the minimum edge. Shown so you always see what the model thinks; never staked.

"No pick" is never the whole answer: the card and the board show the best C picks and why they fell short. Telegram carries only staked picks; the 9am recap says what was not sent and why.

## 4. Staking and grading

- Every pick is frozen at the Wagerhouse number when issued, with a "don't bet past" number, and graded on the result and against the closing number.
- **Stakes:** A = 1 unit, B = half a unit, C = nothing; units and the stops are in the charter's Money section. Staked lanes (decision 0026): NFL full-game, NFL props, NBA props and NFL Wong teasers. NBA and college full-game picks are shown only (research 16). Research 18's restart numbers are the yardstick for keeping a lane staked.
- **Every pick shows where its edge came from:** the part it would have if our number were the market's (that is only Wagerhouse's price against Pinnacle) and the rest, which is our handicap (decision 0027). The charter's rule stands: a price gap alone is never a reason.
- **Every principle keeps its own record.** After 4 weeks and 40 picks, a principle whose picks lose against the closing number is cut to zero weight by a session, with a decision note; the lane-change line then reaches Telegram (charter drift guard). A principle that wins gets more weight. Nothing does this automatically: `engine playbook-record` reports the fitted weight, and the only automatic Telegram line is the review line in the charter.
- Results alone take thousands of bets to prove anything, so the closing number is the scorecard week to week, and results are shown next to it.

## 5. Per sport

### NFL
The full method above. Strongest areas: props from usage and script, team totals, wind totals. Inputs we have free: play-by-play (pace, PROE, EPA, success rate), snap counts, target share and air yards, coverage type (nflverse participation file), blitz and box counts (FTN charting), injury reports, Open-Meteo weather. Not free: route participation, first-read rate, yards per route run. We use snap share times pass plays as the stand-in.

### College football
Script from the spread and total; pace and efficiency from CollegeFootballData (free tier: lines, scores, basic stats, PPA). Quarterback news is the biggest single adjustment: a starter out is worth about 3.5 points to the market (Power 4 about 3, Group of 5 about 4), and only about 0.9 of it usually moves after the opener (research 21). Because the college script lost its test, college full-game picks are staked only as news picks: unpriced, sourced news is what clears the bar (decision 0029). Bowl season adds opt-outs and portal exits. No scheme data (stacked box, pressure) without paying, so college picks lean on totals and quarterback situations. Early season: last year's ratings mislead since the transfer portal (research 14, 2c); weight current-season numbers from week 3. Wind does not help college totals (research 20).

### NBA
The script is pace and minutes: the expected margin sets blowout risk (starters sit), pace sets possessions, and injuries move minutes and shots to teammates. The props model already does most of this. Sides and totals come from team pace and efficiency adjusted for who plays. Rest and travel are already in the market; they move the script (minutes), but they are not a reason on their own.

## 6. Red team: what we take from published methods, and what we don't

We copy methods, never picks. Warren Sharp's write-ups are one example; Walters, Benter and the academic work are others (research 14 and 14a).

| Claim in the wild | What we do with it |
|---|---|
| Game script drives props and totals | **Core of this playbook** |
| Team totals over game totals | Adopted (Step 4 order) |
| Pace and PROE project plays and passes | Adopted. Note: our full-game pace totals model failed against the close (research 02), so here it feeds team totals and props, where it has not been tested yet |
| "Teams with a 100-yard rusher went 48-6" | Hindsight: the rushing came *because* they led. We use the real mechanism (leaders run more) through the script, not the stat |
| "8 of 10 passing leaders won by one score" | Descriptive, not predictive. The mechanism (close games keep passing volume up) is in the script |
| Wind matters from about 8 mph; 15+ is already priced | Matches our own data (strongest at 10 to 19 mph, nothing proven at 20+) |
| Referee ATS records (e.g. 26-47-2) | Small samples. Zero weight until a walk-forward test passes |
| Look-ahead and trap games | Zero weight until tested |
| Correlated parlays on one script | Not now: Wagerhouse's same-game pricing graded as a leak in your audit. Revisit with data |
| Line moves as a signal | The current line is an input to the script (it is where the market thinks the game goes). A move by itself is never a reason (charter) |
| Line shopping across five books | Not available: Wagerhouse only. Other books show as a price check |

## 7. What this replaces

- **Pinnacle is no longer the fair line.** It becomes the sanity check and price filter in Step 4.
- **"A Bet needs news Pinnacle hasn't moved for"** is replaced by Step 4's edge and grades. That old path still runs, but only as a $0 record on the card; it never sends (decision 0027).
- **The stale-number alerts** stay as a price note on the card and a trigger for a research run. They are not Telegram messages (decision 0027).
- **The research agent's job changes.** It no longer hunts for reasons to pass on a price gap. It checks the script's inputs (injuries, who is playing, weather, news the market has), clears CHECK flags, and writes the handicap in plain words. It still cannot type a number.

## 8. Build order (all built by Nov 23: decisions 0019 to 0022)

1. **NFL script engine** (pace, PROE, implied team points, lead path) and **team totals and game totals** priced from it, back-tested walk-forward on 2019 to 2025 to set the starting weights honestly. About 2 to 3 days.
2. **NFL props wired to the script** (the props model exists; it gets plays and pass rate from the script instead of only the spread and total), plus coverage-type splits. About 2 days.
3. **Pick list with A/B/C grades on the card and Telegram, every slate.** About 1 day. Picks start flowing here.
4. **NBA**: script from pace and minutes; props already exist. About 2 days.
5. **College**: script from CollegeFootballData; totals and QB situations first. About 2 days.
6. Per-principle records and re-fitting every 4 weeks.

## 9. What is built (2026-11-23)

| Piece | Status | Where |
|---|---|---|
| NFL script, sides, totals, team totals | Live, **staked** (decision 0026): walk-forward weight 0 for 2024-26 (research 15); the totals lead was the actual-wind input (research 18) | `models/script.py`, `picks/playbook.py` |
| NFL props | Live, **staked** (decision 0026): props model + script team points + expected margin (3 stats), blended 0.5 with Pinnacle | decision 0021, research 16 |
| NBA props | Live, **staked** (decision 0026): NBA props model (minutes), re-centred on outcomes, + script team points, blended 0.5 | decision 0022 |
| NBA sides, totals, team totals | Shown only (walk-forward lost, research 16) | `models/nba_script.py` |
| College sides, totals, team totals | Shown only (walk-forward lost; totals weight a lead, research 16) | `models/college_script.py` |
| NFL Wong teasers | Live, staked (A), 1 NFL unit a ticket; judged at 300 legs | decision 0014, 0019 |
| CHECK clearing by the research agent | Live for all three sports; a cleared pick is staked in a staked lane (decision 0027), and in NBA and college full-game only as a news pick | `docs/cards/decisions/<date>-<sport>-checks.yaml` |
| Per-principle record and weight re-fit on every candidate | Live | `engine playbook-record`, `docs/lanes/PLAYBOOK-RECORD.md` |
| Schedule-adjusted form (NFL script) | Live: the one addition that helped (NFL totals, research 17) | `script.ADJUST` |
| Rain, wind | Live inputs to the NFL script since the start | `script.py` |
| College wind totals | **Failed** on day-before forecasts, 2024-2026: 57-53 at a 1-point edge; the closing total already prices it (research 20, decision 0032). Off | `models/college_wind.py` (test only) |
| Outlier half weight, injury clusters, referees | Built, tested, off (no held-out gain, research 17) | `script.py` |
| Blitz and stacked-box matchup splits for props | Built, tested, off (no held-out gain, research 17) | `props_matchup.py` |
| Coverage-type (man/zone) splits | Not buildable: free data has 2023 only | |
| Never into a move, one unit a game, CHECK clears with a reason, closing grades for props and team totals | Live (decision 0025, kept by 0026) | `picks/playbook.py` |
| NFL stop with teasers, review line, edge split (price against handicap); weekly dollar cap built but off | Live (decisions 0027, 0028) | `picks/playbook.py`, `bets/tracker.py` |
| NBA news-timed props | Paper test (decision 0025) | `picks/news_props.py`, `docs/lanes/NEWS-PROPS.md` |

Commands: `engine playbook --dry-run [--sport NFL|NBA|College]` shows the current lists without sending or writing; `engine playbook-record`.
