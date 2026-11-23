# One plan: what you get today, this week, and next

Written Monday Nov 23, 2026, about 10am Mountain, by the consolidation session. No engine code was changed. Reviewed state: commit `1c234cb`, 134 tests passing, `engine board` builds.

**Read this first (phone version).** Nothing today is a bet by the engine's own rules, and I would not make one up. Three things the engine is telling you right now are wrong (box below), each with a one-line fix waiting for your OK. The biggest one: the engine adds the agent's injury points on top of Pinnacle's number even though Pinnacle already priced the injury, which is where the "edge, then Pass" flags come from. Decisions I need from you are at the bottom.

### False or misleading output right now, and the one-line fix for each

1. **Every card says the fair line is "55% Pinnacle, 45% model." It is 100% Pinnacle** (minus the agent's points). `config.yaml:45` has `use_model_leg: false`, but `src/engine/picks/card.py:142` prints the 55/45 sentence anyway. Fix: print the sentence from the same config switch.
2. **The "fair line" and "value" figures are inflated by double counting.** `src/engine/picks/slate.py:203` is `fair = sharp_fair - adj_pts`: Pinnacle's line with the agent's injury points subtracted again. Pinnacle prices a known injury within minutes (your own Test B, `docs/research/04-evaluation.md`: about 3.3 points for a fresh quarterback loss). So any news older than a few hours is counted twice. Today's examples: Ravens at Texans shows fair −9.68 against Pinnacle −6.5 and a logged "value" of +17.7%; Cavaliers at Bulls shows fair +11.27 against Pinnacle +8.5 and +12.3%. Both were Passes only because the agent noticed. The automatic back-to-back entry (`slate.py:176`, −1.2 points) has the same flaw. Fix for now: drop `- adj_pts` from line 203 and line 176's entry unless Pinnacle has not moved since the news time (that rule is in "This week", item 2).
3. **The "DraftKings open → now" column is not an opener.** ESPN's "open" is a May lookahead for NFL (`slate.py:207` and `:252`; proven in `docs/research/09-early-number-openers.md`). It also looks wrong for college: Pittsburgh at California shows −7.5 → +9.5 on today's card. Fix: drop the column, or replace it with "first line our logger saw."

Also false, but in the docs and not in a message to you: `CLAUDE.md`, `README.md` and the charter table say the NBA injury watcher runs every 10 minutes. It is not installed. `~/Library/LaunchAgents` holds only the agent, poll and weekly jobs; `launchctl list` shows no watcher; table `nba_watch_reads` has 0 rows. Fix: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kylor.betting-engine.nba-watch.plist` after copying the plist from `ops/launchd/` (README line 61), or switch it off formally as an event under the drift guard.

---

## 1. Today

### What you will get today with nothing changed

- **3:15pm Mountain: the scheduled research run** for NFL, college and NBA (`config.yaml`, `agent.schedule.other`). It is the first run that will include the five NFL games Wagerhouse posted at 9am (Falcons at Vikings, Jets at Dolphins, Titans at Jaguars, Patriots at Chargers, Seahawks at 49ers). They are not on this morning's 8:17am card (the card's own note says Patriots at Chargers "isn't on the sheet yet").
- **My expectation for that run: no Bets.** I base this on the raw prices below, not on the engine's output. Wagerhouse and Pinnacle are on the same number or a half-point apart on every NFL game this week. The half-point differences come with different juice, so most are re-pricing, not mispricing.
- **Tomorrow 9am: the weekly report.** It will say 0 graded picks (see "This week", item 3, for why).

### The raw price check (Wagerhouse against Pinnacle, latest read, 9:02am MT)

I pulled this from `line_snapshots`; it is the engine's own data, not a new model.

| Game (kickoff) | Wagerhouse | Pinnacle | Note |
|---|---|---|---|
| Bengals at Commanders (tonight) | Commanders −6 | −6.5 | |
| Packers at Rams | Rams −3 | −2.5 | |
| Bears at Lions (Thu) | Lions +2.5 | +2.5 | same |
| Eagles at Cowboys (Thu) | Cowboys −8.5 | −8.5 | same |
| Chiefs at Bills | Bills −3 | −2.5 | Bills −3 pays even money; Pinnacle's −2.5 costs −120. Re-pricing |
| Broncos at Steelers | Steelers +3 | +2.5 | |
| Giants at Colts | Colts +7 (−120) | +6.5 (−103) | expensive at Wagerhouse |
| **Ravens at Texans** | **Texans −7** | **−6.5** | **Ravens +7 at −110 against Pinnacle's +6.5 at +101. Crosses the 7. Wagerhouse was −6.5 at 8:17am; it moved by 9:02.** |
| Falcons at Vikings | Vikings −7 | −7 | same |
| Jets at Dolphins | Dolphins +3.5 | +3.5 | same |
| Titans at Jaguars | Jaguars −15 | −14.5 | |
| **Patriots at Chargers** | **Chargers −1** | **not posted** | **DraftKings −1.5. Herbert is in the concussion protocol (today's NFL agent log); Maye is out (`adjustments.yaml`). The one game where the soft book has a number and the sharp book does not.** |
| Seahawks at 49ers | 49ers −3 | −3 | Total 46.5 against 47.5 at DraftKings |
| Raiders at Browns | Browns −4.5 | −4.5 | same |
| Panthers at Buccaneers | Buccaneers −3 | −2.5 | |

Two lines to watch, neither a bet on price alone (locked rule):

- **Ravens +7.** By my rough arithmetic the half point across 7 is worth about what the extra juice costs, so it is near break-even. The 3:15pm run will price it properly; today's agent will probably Pass because the only "edge" is the Jackson adjustment stacked on Pinnacle (box item 2). I flag it only because it is the one number in the table where Wagerhouse crossed a key number in your favor.
- **Patriots at Chargers.** Nothing to do until Pinnacle posts. When it does, the next hourly read compares automatically.

### What you will not get today, and why

- **Any Bet or Conditional from a model.** The only passed model is wind, and it only works within 60 hours of kickoff (`config.yaml`, `models.wind_totals.max_lead_hours`). Thanksgiving outdoor games: none (Lions and Cowboys play indoors). Sunday's outdoor games come into range Friday evening. The Bills game shows a 15.8 mph forecast and a −1.4 total change today but is out of range.
- **Props.** Neither prop model has passed its gate (see "Next", item 3 for today's scorecard). Wagerhouse prop lines are not logged at all (0 rows in `derivative_snapshots`), so even a passing prop could not be compared automatically.
- **Any graded record.** `engine_pick_grades` has 0 rows (see "This week", item 3).
- **Small-market answers.** This week's NFL games do not have first-half, first-quarter or team-total lines at Wagerhouse yet. The data so far covers 14 reads and 5 NFL games from Sunday (see "Next", item 1).

### The fastest way to get something that looks like what you asked for today

That is the Leans tier, which you have not approved and the charter says not to build. If you say yes to my recommendation in section 4, the smallest version needs no engine code: one research run that writes `docs/leans/2026-11-23.md`, paper only, 3 to 5 leans per lane for the games already posted. I copy each Wagerhouse number from the database and compute the "don't bet past" number from the existing landing tables. The agent supplies only side and written handicap. I'd grade it by hand against Pinnacle's close until the grader is fixed. My estimate: about an hour from your yes. I will not start without it.

---

## 2. This week

In order. Sizes are my estimates in half-days (½d = a few hours). Everything waits for your approval.

1. **Make the output true (½d).** Fix the three box items: print the fair-line sentence from config; replace the DraftKings "open" with first-seen by our logger and label it; show "n/a, ratings file not out yet" in the public-systems column instead of a blank. Add a test that fails if a card sentence disagrees with `config.yaml`. This is also drift-guard rule 4 from the charter.
2. **Stop counting known news twice (1d).** Apply an injury or back-to-back point value only if Pinnacle's line has not moved since the news timestamp; otherwise the adjustment is 0 and the card says "priced". Pinnacle history is already in `line_snapshots` for NFL and college. Remove the flat back-to-back entry. Keep the agent's entries as a record, not as input. Effect: the phantom +12–18% values disappear; a flag appears only when Wagerhouse is stale against Pinnacle on news Pinnacle has moved for, or Pinnacle has not moved yet. This is the one place where the charter's "only on unpriced news" becomes true; today it is not (see Appendix B).
   - Related decision for you: `CLAUDE.md` says a Bet needs "the model on the same side." With `use_model_leg: false` and the model proven useless (Test A), the card still shows the model columns and the agent cites "the model is on the other side" as a reason to Pass (Delaware and Cleveland cards today). I'd drop that gate and those columns for sides.
3. **Grade everything (½d).** Two defects, both confirmed. (a) Pinnacle lines are stored only for NFL and college: `src/engine/odds/snapshots.py:79` reads `if sport in ("NFL", "College")` although `sources.py:16` has NBA's league id 487. So NBA picks, including the only Conditional the engine has ever issued (Thunder at Heat, +3.5 → +2.5), can never be graded; `poll.log` prints "NOT GRADED ... no Pinnacle line stored before kickoff" every hour and nobody sees it. (b) `grade.py:94` refuses to grade the result if there is no close. Fix: store NBA Pinnacle lines; grade the result regardless and show closing-line value as "n/a" when missing; put "NOT GRADED" into the Monday message. Unrelated oddity I did not chase: `engine_picks` has 2 rows while `engine_pick_events` has 7 pick keys.
4. **Fix the database lock (½d).** Three jobs (hourly read, agent, NBA watcher) plus any command you run all open the one DuckDB file for writing (`snapshots.py:32`). The log shows 5 lock tracebacks in `agent.log` and 1 in `poll.err.log`. The hourly reads show no gap since Nov 21, so the damage is smaller than the handoff feared. One scheduled run is missing: Sunday's 3:15pm Mountain research run has no row in `agent_runs` (Sunday's 8:15am, 6:45pm and 8:45pm runs exist). I could not tie a timestamp to that failure, so "probably the lock" is my inference. Fix: retry for 30 seconds before failing, open read-only wherever a command only reads, and alert if a scheduled run has no record.
5. **Install or retire the NBA watcher (¼d).** Your call (see box). If installed, the first real test is tonight's slate.
6. **Split into five lanes (1d).** Add a `lanes:` section to `config.yaml` with each lane's inputs, models, status and record; give each lane its own card header and Telegram topic; props become lanes 4 and 5 with their own line on every message. Today the cards are already per sport; the missing parts are per-lane status, record and messages.
7. **Build `engine status` (1d, after 6).** One table generated from `config.yaml`, the models' test registry and the database, per charter drift guard: inputs on, models on and their test result, what can produce a pick today, record and date of last pick. It goes on `board.html` and to Telegram Monday morning and whenever its contents change. Switching anything off writes a decision note and sends a message the same day. Every session ends by diffing the table against what it changed.
8. **Housekeeping (¼d).** The scheduler rewrites cards and `adjustments.yaml` all day and leaves them uncommitted (today: 5 modified, 6 new). Either commit them automatically on a schedule or move them under `data.nosync/`, so "uncommitted work" always means a person. Close the other Claude sessions on this Mac (four `claude` processes were running when I checked, one of them this session; two had been open since Saturday and Sunday); the charter says one session owns the code.
9. **Wagerhouse props: decided 2026-11-23, skipped (decision 0011); props are compared with Pinnacle only, and the model's disagreements are tracked as paper suggestions.** (Original note:) The real request has never been found (`docs/handoffs/2026-11-22-model-first-picks.md`). I'll ask once, in plain steps, when it matters. Not on the critical path.

---

## 3. Next: tests in order of payoff

**Test 1: Is Wagerhouse loose in the small markets? (cost: low; data already collecting).** This is the premise of the whole engine ("a soft book, that is probably where my edge is") and nobody has measured it. The data so far is too thin to say anything: 14 reads since Nov 22, 5 NFL games and 16 NBA games. What exists: NBA first-half and first-quarter spreads and totals were within half a point of Pinnacle on all 16 comparisons in each market, and team totals within a point on 31 of 32 (one at exactly 1.0); NFL first-half spreads 0.6 average gap on 5 games, 2 of them at or above 1 point (Raiders at Broncos 2.0, Jets at Chargers 1.0). Earlier work says those NFL gaps may be Pinnacle's own thin-market inconsistency, not Wagerhouse being soft (`docs/handoffs/2026-11-22-model-first-picks.md`). **Test design:** for each matched line, compare Wagerhouse to Pinnacle's vig-free number and to the number implied by the full-game line (first-half margin = 0.48 + 0.62 × spread, `04-evaluation.md` Test E), then measure whether the side at Wagerhouse beats Pinnacle's closing number. **Done when:** at least 200 matched lines per market, or the end of the NFL season, whichever comes first; first look Friday when this week's period lines post. **Unlocks:** a real derivative lane, or a clear answer that the price edge needs a second book.

**Test 2: Does Wagerhouse open better than the close? (cost: low).** The "early number" premise. From our own logs, for every game: Wagerhouse's first-seen line against Pinnacle's last line before kickoff. Needs about 3 weeks of reads; the schedule already produces them. **Unlocks:** how much the Sunday-night and Monday-morning timing is really worth, and which sport.

**Test 3: Keep the props forward tests running; do not touch them.** My own count from `prop_evals` (one row per distinct prop, latest read; the engine's scorecard may count differently): NFL 150 graded props, model error 0.2579 against Pinnacle's 0.2524 (model worse), and the model's side won 47 of 91 where it disagreed by 5 points or more (52%, under break-even). NBA 209 graded, model 0.2480 against 0.2466 (model slightly worse), but the model's side won 80 of 138 big disagreements (58%), almost all leaning Under by an average of 5.6 points. Both are one day's games, heavily correlated, and below the 300 gate (`config.yaml`, `models.props.min_graded`). I would not read the NBA 58% as an edge yet; I would not stop it either. **Unlocks:** NBA props Conditional picks if the 300-prop gate passes; requires Wagerhouse prop lines (item 9).

**Test 4: College openers against real outside ratings (cost: 1 to 2 days).** The handoff asked whether past seasons of the weekly ratings file exist. They do for college: `https://www.thepredictiontracker.com/ncaa2019.csv` through `ncaa2025.csv` all return 200 (I fetched them; each is roughly 160 to 285 KB). A sample row has about 50 system columns, a `lineopen` column, `line`, `actual` and `week`. For NFL the same pattern returns 404 for 2019 to 2025, so no NFL archive exists under that name. **Before trusting the file I must check:** what `lineopen` is (I assume the opening line; unverified), and whether the file records when each system published its number (it does not appear to, so late-week numbers could leak look-ahead into an "early" test). **Rule:** a test on leaky data that fails is a definitive fail; one that passes is only a hint and gets re-checked with a stricter cut. **Design:** fit the weights on 2019 to 2022, test on 2023 to 2025, bet the opener where the systems' average differs from it by 2 or more, grade against the final score and against the close. **Pass bar:** over 52.4% on at least 500 held-out games and positive average closing-line value. **My honest prior:** below even odds. Test A already found these systems sit close to the market, and the earlier opener tests with market-derived ratings landed at 50.5%. But this is the one input not built from market lines, so it is the cheapest real shot at a college model. **Unlocks:** the first own-model flag in the college lane.

**Test 5: Injury values beyond quarterbacks (cost: 1 to 2 days).** How far the closing line moves when a non-QB starter is out, measured against nflverse injury reports (Test B did QBs only). **Unlocks:** replaces the agent's judgment points with measured ones, but only after item 2 above makes them matter again.

---

## 4. Recommendation on Leans

**Do it, as paper only for the first four to five weeks, graded on closing-line value first and results second. Do not bet it until 50 are graded and the average closing-line value is above zero.**

The case for:
- Your standard is to be the one holding +10 before it becomes +6.5. That is a prediction about where the line goes, and it can only be tested by writing the predictions down. Nothing in the engine does that today, so the agent's skill at it is simply unknown.
- Closing-line value converges much faster than win rate. At 100 bets a win rate carries about ±5 points of noise (square root of 0.25/100), so 52% against 55% is invisible; points gained against the close show up in far fewer picks. This is arithmetic; I have not yet measured the spread of our own closing-line value.
- It costs nothing at paper stakes ($6.25 at a quarter unit), and it is the only way the "agent as handicapper" half of the product ever gets tested.

The case against:
- Public models have not beaten the close in any test (`04-evaluation.md`; your five failed tests). My default expectation is that Leans come back near zero. The test is worth running because the whole product premise sits on it, not because I expect it to pass.
- Story-fitting. Today's cards show the agent producing a convincing handicap for a side it then passes on (Texans: "the handicap does favor Houston", then Pass). A Lean tier invites those stories to become opinions.
- A lean labelled "unproven" will still be bet by hand. Anchoring is the main risk to your money.
- If a Lean's only reason is a price gap, it breaks two locked rules.

Guardrails I'd write into the spec: a Lean needs one of three stated reasons only (news with a timestamp Pinnacle has not moved for; a forecast of where the line is going and why; a wind or weather case); code stamps the Wagerhouse number and the "don't bet past" number; the agent cannot type either; 3 per lane per week at most; each is graded on closing-line value, result, and whether it was bet at the stated number; every Monday message shows the Leans record next to the Bets record, never merged with it.

---

## 5. What I would stop doing

- **Stop adding agent injury points on top of Pinnacle** (box item 2). Replace with "priced / unpriced."
- **Stop flagging sides where the only gap is juice at the same number.** Two of today's three college and NBA flags (Kentucky +3, Delaware −2.5) are Pinnacle charging more at the same line. Show the price; do not flag it.
- **Stop showing market-ratings, public-systems and "model" columns for sides.** They failed Test A, drive nothing, and feed the agent a "model disagrees" veto it should not have.
- **Stop four research runs on Sunday that repeat "Pass."** Run on a change (news, a new slate, a move of 1 point or more) plus one fixed run before openers. This cuts the noise you read and the Claude usage.
- **Stop building models of the same kind** that have failed five times: ratings from market lines, pace and efficiency, first-half habits, opener pricing from ratings. New models go through the walk-forward test first, as decision 0005 already says.
- **Stop keeping the lane status by hand.** The hand-kept table in the charter is already wrong in two places (Appendix B).
- **Stop running more than one session on the repo at once.**

---

## Appendix A: reconciliation of the two reviews

Where both agree, one line. Where they differ or either is wrong, the file that settles it.

| # | Claim | Verdict | Proof |
|---|---|---|---|
| Both | Spreads are a price check against Pinnacle | **Agree, right.** Sharper than either said: the "fair line" also subtracts the agent's points | `slate.py:203` |
| Both | Totals: only wind, outdoor NFL, half unit | **Agree, right** | `config.yaml` `models.wind_totals` |
| Both | Props can't issue a pick until 300 graded | **Agree, right.** Also can't be checked at Wagerhouse, because its prop lines are not logged | `config.yaml` `models.props`; `derivative_snapshots` Wagerhouse props = 0 |
| Both | Record is 0-0 | **Right, but the cause is a bug, not just newness** | `engine_pick_grades` 0 rows; `snapshots.py:79`; `grade.py:94` |
| Both | College is running | **Right.** 66 games priced this morning, two flagged, both Passed for juice-only reasons | `docs/cards/2026-11-23-college.md` |
| 1 | Card header "55% Pinnacle, 45% model" is false | **Confirmed** | `card.py:142`; `config.yaml:45` |
| 2 | Public-ratings column is blank | **Confirmed** (9 of 10 NFL games, 66 of 66 college). And it no longer matters for sides, since the model leg is off. It matters for the college opener test (Test 4) | cards' "Problems on this build" |
| 3 | DraftKings "open" misleads | **Confirmed, and also for college** | `slate.py:207`, `:252`; `09-early-number-openers.md` |
| 4 | Picks are not graded | **Confirmed, worse than described.** NBA can never be graded because NBA Pinnacle lines are not stored | `snapshots.py:79`; `poll.log` "NOT GRADED" lines |
| 5 | Bengals under reported wrong | **Partly confirmed.** The log shows Conditional at 6:46pm Sunday ("WAIT, DO NOT BET YET") then Pass at 8:46pm ("CANCELLED, DO NOT BET"). I cannot see the message that said it stood | `engine_pick_events`, `agent.log` lines 84–99 |
| 6 | Database lock | **Confirmed but smaller than feared.** 5+1 tracebacks, no gap in hourly reads, one missing Sunday run (inferred) | `agent.log`, `poll.err.log`, `agent_runs` |
| 7 | Several sessions editing at once | **Mostly resolved.** The files the handoff named (`openers.py`, `test_openers.py`, `cli.py`) are now committed (`60525ca`). What is uncommitted today is scheduled-run output written 8:17–8:21am, not a person's code. Other Claude sessions are still open on this Mac | `git status`; `ps` |
| 8 | Injury values by judgment keep getting flagged then passed | **Right, and the root cause is the stacking.** Not the estimates themselves | `slate.py:203`; Texans card |
| New | NBA watcher "runs every 10 minutes" | **Not true.** Not installed | `~/Library/LaunchAgents`; `nba_watch_reads` 0 rows |
| New | "Wagerhouse small markets are being logged" | **Half true.** Period and team-total lines yes (first half, first quarter, team totals); props no | `derivative_snapshots` |

Where the reviews differ, neither was wrong: the first review found the display problems and the second found the plumbing problems. They share one root, which is that the engine's output looks like analysis but is mostly Pinnacle plus the agent's own adjustments.

## Appendix B: charter check, lane by lane (what each will and will not evaluate after this plan)

| Lane | After this plan it evaluates | It still will not |
|---|---|---|
| NFL spreads and totals | Wagerhouse against Pinnacle; news Pinnacle has not moved for (timestamp checked); wind totals within 60 hours, half a unit at most; paper Leans if approved | Any own sides model; opener prediction; non-wind totals; anything from public ratings |
| College spreads and totals | Wagerhouse against Pinnacle; news where machine-readable (big conferences only); paper Leans if approved; may gain a real model if Test 4 passes | Totals; injuries outside big conferences; public ratings until tested |
| NBA spreads and totals | Wagerhouse against Pinnacle (now stored and gradable); the injury watcher once installed; paper Leans if approved | Own model; totals; pace; the flat back-to-back adjustment (removed) |
| NFL props | Prices every Pinnacle prop and grades it; scorecard shown; a pick only after 300 graded props and the gate | Any pick today; any comparison to Wagerhouse until its prop lines are logged |
| NBA props | Same, with Over/Under split shown | Same; the Under lean is a flag to watch, not a signal |

Two statements in `CHARTER.md` are wrong today and should change in the same commit as the fix: the "Sides: only on unpriced news" line (the code subtracts the agent's points regardless of timing; true only after item 2), and the NBA lane's "injury watcher" input (not running). I did not edit the charter; you own it.

## Decisions I need from you

1. **Leans:** yes as paper-only, or no? And, if yes, do you want the paper-only one-off today (section 1)?
2. **Drop the "model agrees" requirement** for a side Bet and the model columns on the card? (I recommend yes; it changes `CLAUDE.md`.)
3. **NBA watcher:** install it, or turn it off formally?
4. **Approve "This week" items 1 to 8** in that order, or tell me which to cut.
5. **Close the other Claude sessions** on this Mac while I work, so one session owns the code.
