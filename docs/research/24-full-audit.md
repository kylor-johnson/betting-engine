# 24. Full audit of the engine, Sharp red-team, and outside research for all three sports (Nov 24, 2026)

**What you need to do:** answer the 14 yes/no questions at the bottom (one line each), and reload two launchd jobs (poll and weekly; the
command is in the last section). Nothing about money changed today; every money change below waits for your yes.

Written Tue Nov 24, 2026, evening, by a fresh session that built none of the engine. Five helpers read the code part by part, one graded
Sharp's saved picks, three searched the outside research by sport. I checked their numbers before using them; where my re-run differs
from a helper's, my number is the one here and the difference is said. Sources: `24a-sources.md`. Scripts: `scripts/research24/`. The
tests in Job 3 were committed before they ran (commit fccd765). Database opened read-only throughout. 295 tests pass (273 before, 22 new).

## The verdict on one page

**Is the engine doing what you asked?** Mostly, yes. There is one pick path. Every staked pick since Nov 24 01:00 UTC has a delivered
Telegram message (8 of 8; the 11 picks before that have no saved record, as decision 0033 says). No $0 pick has been sent as a bet. The
money rules in the code match the charter exactly: units, A = 1 and B = ½, the caps, one unit a game, the 10-unit stops, the review line.
Every model's walk-forward number in its research note reproduces when re-run (Job 1, part 2).

**What was wrong**, fixed today (each with a test):
- A test read (`poll --no-send`) could send a real-money teaser ticket.
- Three Saturday college games were never read (team-name mismatch).
- The NBA injury watcher reported false news every time the official report rolled over to the next day's games. It started a research
  run on "Embiid Out to Available" this morning.
- Rotoworld news could be lost silently. One bad score could stop grading, the daily check and the 9am recap together. A failed system line
  (a tripped stop, for example) was never sent again.
- "Don't bet past" used a different test from CANCELLED.
- No report showed the luck range.

**Is each staked lane earning its money?** Only one lane has evidence behind it:

| Lane | Unit | Evidence it should have money | Evidence against | Live so far (staked, graded) |
|---|---|---|---|---|
| NFL Wong teasers | 1 NFL unit a ticket | Legs crossing 3 and 7 won 76.3% (607 of 796, 2015-2026) against 72.4% needed (research 18); the rule is from 2001, so the data did not choose it | Favourite legs 42-24 since 2023 (watched) | 1 ticket, 0 legs graded |
| NFL sides, totals, team totals | $50 | Your choice (0019). The one lead (totals at 4+ points apart) is the actual-weather input: without it, 122-135 and worse than the market (re-run today) | Weight against the market 0/0/0 for 2024-2026 (research 15, re-run today: same) | 1 graded: 1-0, +0.48u |
| College sides, totals | $25 | Your choice (0035). Totals at 4+ apart 621-555 (52.8%) over 2023-2026 | Failed in all three markets (research 23, re-run today: exact); 2026 totals 106-122 | 0 graded |
| NBA sides, totals | $25 | Your choice (0035) only | Weight 0 every market and season (research 16, re-run today: same); the script cannot see who is injured; no public NBA rating beats the close either (24a) | 0 graded |
| NFL props | $50 | Your choice (0026) | Model alone is worse than Pinnacle; blending it in at the live 0.5 is also worse than Pinnacle alone. The best weight is 0.15 (re-run today, 199 props) | 2 graded: 2-0, +1.16u |
| NBA props | $25 | Your choice (0026); best weight 0.25 | The model still leans Under (average 44.5% Over against 49.1% actual, 574 props) | 3 graded: 1-2, −0.54u |

Nine graded picks tell you nothing yet: the luck range on them is ±1.9 units (NBA props) and ±1.5 (NFL props). Closing-line value is the
only early read, and it needs 25 picks per lane for the review line and 100 to 300 for the charter's yardsticks.

**The biggest risks to money, in order:**
1. **Props are staked at a weight the data does not support** (0.5 against 0.15 NFL and 0.25 NBA). Question 1.
2. **NBA full-game picks are staked with no evidence and a blind spot.** The script cannot see injuries, so its gap from the market is partly
   just "someone is out". Question 2.
3. **The research agent can type a news adjustment of any size, and it skips CHECK.** A 10-point entry made a +32.6% B pick with no CHECK
   flag (helper's test on the pure function; I confirmed the CHECK test ignores the adjustment, `playbook.py:162`). The live Patriots entry
   is −5.0, twice the NFL guide's 2.5 to 2.7; it counts for nothing today only because it has no `news_at`. Question 3.
4. **The stop does not count yesterday's picks.** `live_since` is Nov 24, so the 11 picks sent on Nov 23 (about 3 NFL units still open)
   are outside the stop. Question 6.

## Fixed today (plain bugs; commit d8fa413; tests in `tests/test_audit24.py`)

| # | What was wrong | Where | Fix |
|---|---|---|---|
| 1 | `poll --no-send` still sent real-money teaser tickets to Telegram | `poll.py` → `teasers.scan` (no send flag) | The flag is passed through |
| 2 | UL Lafayette, Florida Intl, Sam Houston St and Middle Tennessee St never matched ESPN: three Saturday games had no lines, no picks. The read logged it as a held-back `problem` | `odds/espn.py` ALIASES | Four aliases; all three games now match (checked live) |
| 3 | The official NBA report lists only teams with games coming up. When it rolled to the next day, every player on a team not playing looked like "off the report", and every player on a newly listed team looked like "Out". It started a research run at 10:00 today on Embiid | `picks/nba_news.py` `check_official` | A player joining or leaving the report counts only when his team is on both reports |
| 4 | Rotoworld read 4 pages (40 posts). When reads were hours apart it silently skipped 4 to 5 hours of NBA posts (Nov 23 and Nov 24), and the gap was never read | `picks/player_news.py` | 15 pages; a gap that remains is a problem line, and the posts read are still used |
| 5 | ESPN's scoreboard was cached for a day as soon as that day was "yesterday" in UTC, which is 5pm Mountain, so tonight's games were frozen as unplayed (15 NBA games missing from ratings) | `odds/espn.py` | A day is cached only when every game in it is final |
| 6 | One DraftKings failure (history only) threw away the whole read for every sport | `odds/snapshots.py` | It is a problem line |
| 7 | Prop lookups (grading, re-centring, never-into-a-move, CANCELLED) matched player, stat and teams only. When the same two NBA teams meet again, they could read the other game. CANCELLED's prop check did not even filter on the teams | `playbook.py`, `calibrate.py` | Tied to this game's start time |
| 8 | "Don't bet past" walked on expected profit; CANCELLED tests win chance. Decision 0033 says they are the same test. At −110 the limit was set at about 0.8% of chance, not 1.5% | `playbook.py` | `limit_value` converts with the price's odds |
| 9 | One bad ESPN score stopped all grading, which also skipped the daily check and the 9am recap | `poll.py`, `playbook.grade` | Each step has its own guard; a bad score skips that game only |
| 10 | A system line that failed to send (stop tripped, review, NOT DELIVERED, lane change) was never tried again. A lane that changed back to an earlier state was never announced | `poll.py` `_deliver` | Failed system lines are resent for 48 hours; the lane key carries the time |
| 11 | Daily check 3 crashed on a database read error and counted paper picks; check 7 counted research runs that only started | `checks.py` | Fixed; check 3 counts staked picks as the charter says; check 7 counts finished runs |
| 12 | An unreadable checks file was skipped without a word (the agent's clears were lost). Two news entries for the same game, market and team were both added | `playbook.load_checks`, `slate.load_adjustments` | A problem line; duplicates refused |
| 13 | No report printed the luck range (CLAUDE.md rule) | tracker, recap, `PLAYBOOK-RECORD.md`, lane records | Added. Today's recap: "Luck range on the model's graded picks: ±$102.03" next to +$68.38 |
| 14 | NFL fast reads used fixed weekday windows: none before Wednesday's 6pm Packers-Rams, Thanksgiving's 11am Bears-Lions, or Friday's 1pm Broncos-Steelers | `config.yaml burst` | Also 2 hours before each day's first NFL kickoff, as the NBA already does; cap 40 → 50 a day |
| 15 | The poll and weekly launchd jobs had no `HOME` (the Vercel publish failed 05:02-16:32 UTC today with "No existing credentials") | `ops/launchd` | Added; you reload them (last section) |
| 16 | False sentences | README (`--no-send`, the 90-minute rule, the missing burst job), CLAUDE.md (what reaches Telegram, auto-commit), PLAYBOOK (wind knot is 6 mph, not 8; CHECK clears in college and NBA), the agent prompt ("no model leg on sides"), config comments (teasers "paper only", props gate, burst "never starts a run", the missed-read hours), the lane table's decision numbers | Corrected |

**Plain bugs found but not fixed today**, for the next session (each is small, none moves money):
- The missed-read alarm fires after 20 hours (`poll.py:174`, the +12 was set for the old schedule); the charter says 2 hours in read hours.
- `down_units` returns 0 when it cannot read the database (`playbook.py`), so an unreadable stop passes as "+0.0".
- The hourly read holds the database's write lock through all its network calls (about 100 to 120 seconds); other jobs wait at most 180.
- CollegeFootballData has no fallback to its cache when the site is down; one outage stops every college slate.
- The `engine playbook --dry-run` temp copy of the database (about 21 MB) is never deleted.

## Job 1. Every part: what it does, why, does the reason hold, what breaks it, verdict

Ranked by money at risk. "Fix" = plain bug (done above unless noted). "Change" = needs your yes (the questions at the bottom). Every
part was read from the code; the "why" is the note that explains it, or "no note", which is itself a finding.

### 1. Choosing a pick (`picks/playbook.py`, 1,466 lines) — money: every staked pick

- **What:** our number per market = market + weight × (our script − market) + unpriced news. Edge = our win chance − the chance
  Wagerhouse's price needs. Minimum edge 3% (4% props). CHECK when our script is 3/4/4 points from the market (NFL), 4/6/5 (NBA), 6/7/6
  (college), or 15 points of chance on a prop. One pick per game, caps, one unit a game, never into a Pinnacle move, CANCELLED on a move.
- **Why:** PLAYBOOK step 4 and decisions 0018-0035. Every threshold, weight, distance and cap in the code matches the documents (helper
  printed `settings()` for all three sports; I checked the CHECK code). Edge signs traced through sides, totals, team totals, news and
  closing grades: no sign error.
- **Does the reason hold:** the weights do not. They are the playbook's starting weights (0.25 / 0.35 / 0.4 / 0.5), kept by your choice
  (0019, 0035) against the walk-forward. Re-run today, they make every number less accurate than the market except NFL totals, and that
  exception is the weather look-ahead: NFL sides +0.9% more error, team points +0.8%; college +0.9% / +1.3%; NBA +1.2% / +1.9%.
- **What breaks it:**
  - The agent's adjustment size has no limit and does not count toward CHECK (risk 3 above). **Change** (question 3).
  - `news_at` is typed by the agent. If it is late, the Pinnacle move since the real news is taken as the "before" line and the full
    adjustment counts again. With the same rows, a −2.5 entry at its real time counted 0; three hours late it counted −2.5. **Change**
    (question 4).
  - A pick that "moved against" is demoted after one pick per game is chosen, so a valid pick on another market of the same game is lost
    (live: Temple at Memphis). **Change** (question 9), since it adds staked picks.
  - Caps count paper picks, including picks made paper by the one-unit-a-game rule. NFL has used 4 of 5 full-game slots for this week
    before Wednesday; all 10 college picks came from one read (5 staked, 5 paper past the cap). Saturday news picks will be paper.
    **Change** (question 10).
  - The market reference reads Pinnacle's line and ignores its price: −3 at −125 is treated as a fair −3. Worth about 0.8 points at a 55%
    price (helper's example; `Landing.fair_from_price` already exists). Decision 0025 listed this as not approved. **Change** (question 5).
  - The NBA team-total curve is too narrow (10.5 against a measured 11.5), so NBA team-total edges read about 9% too big. **Change** (in
    question 5).
- **Verdict:** keep the structure; change the weights, the news guard and the market reference.

### 2. Money (`playbook.stake`, `down_units`, `lane_events`, `teasers.py`)

- **What, from the code:** units $50 NFL, $25 NBA, $25 college. A = 1u, B = ½u; every playbook pick is B (nothing has passed a test,
  0033 item 11); teaser tickets A. Stop at −10u per sport from `live_since`, NFL counting teasers. Review line −1.5% closing-line value on
  25 graded.
- **Why:** charter Money, decisions 0020, 0027, 0028, 0033, 0035. All match.
- **Does the reason hold:** the rules yes. The stop's start date is off by a day (risk 4). The review line counts all staked history
  while the stop counts from `live_since`, so a restart never clears an old review. **Change** (question 6).
- **Lane by lane**, the evidence for and against: in the table at the top. Only the teaser lane has money backed by a test it passed.
- **Verdict:** keep the rules; questions 1, 2 and 6.

### 3. The numbers (models and pricing). Every walk-forward re-run today

| Note | Claim | Note's number | Re-run today | |
|---|---|---|---|---|
| R15 NFL script | Totals error market / ours / blend; 2024-26 weights | 174.72 / 181.19 / 174.60; 0/0/0 | 174.71 / 181.12 / 174.59; 0/0/0 | Confirmed |
| R17 NFL, schedule-adjusted (live) | Totals at 4+ apart | 175-136 | 176-135 | Confirmed |
| R18 NFL without weather | Totals at 4+; error vs market | 122-133; 174.82 vs 174.72 | 122-135; 174.81 vs 174.71; weights 0 | **The lead is look-ahead** |
| R16 NBA script | Team points error market / ours | 131.66 / 145.77 | 131.44 / 145.43; weights 0 | Confirmed |
| R23 college (live, 0034) | Team error; totals 4+; sides 3+ | 120.64 / 120.73 / 133.75; 621-555; 1201-1145 | Identical | Exact |
| R21 college QB | Starter out | 3.7 mean (1,078); P4 3.2, G5 4.2 | 3.71 / 3.18 / 4.18 | Exact |
| R16 props lead | b carries / attempts / rec yds | +0.0029 / −0.0015 / −0.0011 | +0.00288 / −0.0015 / −0.00107 | Confirmed |
| R18 props forward | NFL best weight | 0.1 (150 props) | **0.15** (199 props; my run of `scripts/research18/props_fwd.py`; a helper's earlier run gave 0.05) | Same verdict |
| R18 props forward | NBA best weight | 0.35 (209) | **0.25** (563) | Same verdict |

Part by part:

- **NFL script (`models/script.py`), live, staked.** Ridge on decayed, opponent-adjusted EPA, success rate, points per drive, drives, pass
  rate over expected, home, backup QB, wind, rain (research 15, 17). **Finding:** wind and rain are fitted on the weather that happened
  (reanalysis, `script.py:301-313`) and applied live to forecasts, and wind is also the old wind lane's input. Decision 0025 listed the fix
  as not approved. The decay (0.85) has no note explaining it. **Change** (question 5).
- **College script, NBA script:** live, staked by your choice; both reproduce. The NBA script has no injuries (`nba_script.py:10`).
  **Change** (question 2).
- **NFL props (`models/props.py`, `props_news.py`, `props_script.py`), live, staked.** The receptions projection uses a slow decay (0.92)
  and the role-change term is off for receptions (fitted to zero, research 06). Jonah Coleman: a 0-catch week 1 counted in full, plus no
  link from his new carry share to his catches, put our model at 30.8% against Pinnacle's 45.4% on Over 3.5. Without the week-1 row it is
  41.8%. History says reception spikes mostly revert (actual / projection 1.006 on 686 cases) but carry spikes do not (1.198 on 139). So
  this is a model limit, not a bug. **Change** (question 12: a pre-registered variant).
- **NBA props (`models/nba_props.py`, `calibrate.py`), live, staked.** Under lean persists after re-centring (44.5% average Over against
  49.1% actual). Re-centring had a rematch bug (fixed, item 7).
- **Pricing (`pricing.py`, `odds/math.py`).** Checked by hand: −110/−110 → 50/50; −150 → 60%; −150/+130 no-vig 58.0/42.0; teaser break-even
  72.37%; push at exactly 3 = 9.7% (history at −3 closes: 11.2% on 258, within noise); `crosses_3_and_7` right on every case tried.
  Vig is removed proportionally, which overstates longshots (−400/+300: 23.8% against 21.8% by the power method). It matters for anytime
  touchdown props. **Change** (in question 5).
- **Test-only, off, correctly:** `first_half.py`, `college_wind.py`, `college_review.py`, `nba_absences.py`, `props_matchup.py` (wired, off),
  `calibration.py`, `wind_totals.py` (paper lane).
- **Verdict:** keep the models; change the weights and the weather input.

### 4. Data in

- **Wagerhouse (`odds/wagerhouse.py`):** the client refuses any operation not on a five-item read-only list (login, account, lines, two
  history reports); nothing else in the code calls Wagerhouse. Eastern-to-UTC conversion checked in winter and summer. Empty lines return
  nothing quietly (counted in `polls`). **Keep.**
- **ESPN, DraftKings, scoreboard:** fixed (items 2, 5, 6).
- **Pinnacle (`picks/sources.py`, `odds/derivatives.py`):** errors become problem lines. A malformed derivative row (KeyError) drops every
  sport's derivative rows for that read: a minor bug, not fixed today.
- **CollegeFootballData:** no cache fallback (listed above).
- **Rotoworld, official NBA report:** fixed (items 3, 4). Reporter coverage is thin by research 07's own count. **Keep.**
- **Verdict:** fixed where it was broken.

### 5. What reaches you (Telegram, recap, checks, tracker)

- **What:** `send_kinds: [bet, system, recap]`. $0 picks cannot go out as `bet` on any path today; I checked every send. The one switch
  that would reopen it is `agent.send_picks: true`.
- **Delivery:** 8 of 8 saved staked messages delivered. The 11 picks from before Nov 24 01:00 UTC have no record (admitted in 0033). One
  CANCELLED (DeVonta Smith) delivered.
- **Does the reason hold:** mostly. Gaps:
  - Resends and CANCELLED run only in read hours, which end at 5pm Mountain on weekdays. A staked NBA pick from the 5:32pm read whose send
    fails, or that the market moves past, gets no resend and no CANCELLED before an 8pm tip. **Change** (question 8).
  - **Every message and the tracker are in dollars**, not units ("Stake: $12.5 (B pick)"). Your rule (and the handoff) says units.
    **Change** (question 7).
  - The recap gives paper picks as counts by reason, not by name. Minor.
- **Verdict:** fixed (items 1, 9, 10, 11, 13); change the units wording and the evening hours.

### 6. Grading and the record (`playbook.grade`, `clv.py`, `grade.py`, tracker)

- **Independent recompute:** 22 graded rows, every result, profit and closing-line value matched (helper, from ESPN box scores fetched
  separately); the tracker's +$68.38 recomputes exactly.
- **Which close:** Pinnacle's last read before kickoff. There is no fallback; with no Pinnacle read the result is graded and closing-line
  value is left blank. The "close" is the last hourly read: on average 0.9 hours before an NFL kickoff, 1.5 hours for college, up to 3.5
  hours for an evening college game. No close time is stored.
- **Props, an honest number, but know what it says:** a prop's closing-line value is Pinnacle's no-vig chance at the close minus the chance
  *Pinnacle's own price* needs. So a prop where nothing moves scores about −2.5% (half Pinnacle's margin). Every graded prop is −2% to −3.3%.
  The props lanes will reach the review line at 25 picks unless props beat Pinnacle's margin, which is what "no edge" looks like. Keep this
  measure. But **profit is graded at Pinnacle's price**, while you bet at Wagerhouse at or below the limit. Chase was graded at +123
  against a +111 limit, so the record is about +0.16u too good on three wins. **Change** (question 11).
- **Voids are missing:** a prop where the player does not play, or a postponed game, is never graded. Check 3 will then fail every day.
  Pinnacle's NBA props are "must play" (24a NBA leg). **Change** (question 11), because it decides results.
- **Pushes, teaser pushes, signs:** correct.
- **Verdict:** keep; questions 11.

### 7. Running it (launchd, `poll.py`, `burst.py`, locks, auto-commit)

- **What runs when (Mountain):**
  - poll at :02 and :32, reading about once an hour 7am-5pm (Sundays to 9pm);
  - research 8:15 daily and Sunday 6:45pm, plus news triggers;
  - NBA watcher 10, 15, 17;
  - fast reads every 10 minutes in windows;
  - weekly report Tuesday 9:00.
  All five jobs are loaded and ran in the last 3 days: polls 42 of 42 ok, fast reads 31 of 31.
- **Thanksgiving week:**
  - The hourly read covers Wednesday's 6pm game (last read 5:32).
  - The pick weeks (Tuesday to Monday by kickoff) put Wednesday, Thursday and Friday games in the Nov 24 week. No time-zone bug.
  - The fast-read gap was fixed (item 14).
- **What is missed:** evening NBA and college. The last read is about 5:32pm, so an 8pm tip's "close" is 2.5 hours old, and Outs after
  5pm are not read until the next morning. No decision note explains why the NBA watcher stops at 5pm (moved from every 10 minutes on Nov
  23). **Change** (question 8).
- **Locks:** `session_lock` take is read-then-write (a small race); no lock was held. **Keep.**
- **Auto-commit:** only from research runs, so poll's outputs (`TRACKER.md`) wait for the next research run. **Keep.**

### 8. The documents

- 16 false or stale sentences corrected (item 16).
- **Decisions that contradict without saying so** (I did not edit old decisions; this list is the record):
  - 0035 stakes college full-game but does not name 0034 item 5, written the same day, which said no.
  - 0033 overturns 0031's 3.5 points and its "above 5 needs a reason" without naming 0031.
  - 0017 says no new full-game sides or totals model without a passed test; 0018-0022 and 0034 built three, and none names 0017.
  - 0006's props gate (300 graded, never sent while testing) is overtaken by 0021 and 0026 without a replace line.
  - 0029 and 0030 say "Replaces: none" but turn on staked news picks in lanes 0022 and 0026 had made shown-only.
- **Numbering:** decision files 0007-0009 do not exist (32 notes, not 35).

### 9. Tests

- 273 passed before today; 295 now.
- **Risky paths that had no test:**
  - the no-send read (now tested);
  - `playbook.grade`, the source of the stop's units (now tested);
  - voids (not built);
  - teaser push in the stop count;
  - CANCELLED for props and team totals;
  - week boundaries across a DST change;
  - Telegram's 3,900-character cut.
- **Tests that only restate config:**
  - `test_telegram_gate.py:17`;
  - `test_lanes.py:15`;
  - `test_review14.py:205`, which pins NBA and college `full_game == "show"` in the defaults while config now says `stake`, so it would
    pass even if config regressed.

## Job 2. Sharp's saved picks, graded against Pinnacle (last day of access)

Fifty-nine of his own picks across Nov 16-24 (Week 11 props in five waves, Week 12 releases), plus a handful by other writers on his site.
Times on his pages are Eastern. Full table in the helper's scratch output; here are the findings. His material stays outside git
(research 03).

**Week 11 result:** 21-23, −1.23 units. His straight bets went 21-15 (58%, 95% range 42-73%) against 53.8% needed; his 8 longshots went
0-8. The luck range is ±7.4 units, so nothing here can be told apart from zero.

**At release, most were not good bets against Pinnacle.** Of the 9 Week 12 releases we logged at release, 7 were negative at his quoted price
(−4.3 to −1.3 points of win chance). Only two were positive: the Texans first-half team total Over 13.5 at −110 (+2.0 at release, +3.5 at
the latest read) and Coleman receptions Over 3.5 at +124 (+0.8; Pinnacle had already moved +124 → +106 the day before, so that one is
partly a stale price at FanDuel).

**The handoff's guess was wrong.** It guessed his full-game totals did not move Pinnacle and his derivatives did. In fact, within an hour of
the Nov 24 "computer totals" release, Pinnacle moved his way on all 5 markets. The biggest move was the full-game Ravens-Texans Over: −105
at 18:32 UTC, −115 at 19:32, −118 at 20:32, which I checked in our log. In the same hour, 0 of 14 other full-game totals, 0 of 14 other
first-half totals and 1 of 31 first-half team totals moved by a point of chance or more. His Packers first-quarter pick and his Coleman
props did not move. So it is that release that moves the market, not the kind of market.

**Three rows in the handoff's table are wrong:**
- Bills team total Under: it was −102/−105 and moved to −117 an hour *before* his release; "−108" is never in our log.
- Bills-Chiefs Under 48.5: his ticket at 48.5 against Pinnacle's 47.5 is about +1.8, not −0.9. The 50 → 48.5 move came 1.5 hours before his
  release.
- Ravens-Texans Over 46.5: "no move" is wrong; it was the largest move.

**His methods, taken apart:**

| Method | What the evidence says | Our engine |
|---|---|---|
| Short trend records ("12-1 with extra rest since 2022", "13-0 in the series", coach against coach) | Our own play-by-play gives that Packers split as 15-2, so his definition differs: a forking path. Of 888 team × condition × start-year splits with 13+ games, 3 are at 85%+. Teams at 80%+ in a rest split went 69.2% next time against 66.1% for 45-80% teams (3 points, standard error about 6). More than 600 published betting systems, none survives a correction for testing many ideas (Vandenbruaene et al. 2022, 24a). His referee page gives the same crew two different records | Never tried; should not be ("tests never look ahead") |
| Schedule-adjusted efficiency | Built (`script.ADJUST`, decay 0.85; no note explains 0.85) | Kept (research 17), but its totals lead was the weather look-ahead |
| "Computer totals" with half, full and team totals; lifetime page: "739-431 (63%)", 2006-2025 | A claim: no times, prices or closing-line value. He stakes one opinion across correlated markets (1.3 units on Ravens-Texans across three tickets; our rule is one unit a game) | Full-game totals failed (research 02, 03); first-half model failed (research 05: habit weight 0.01-0.09, error 102.77 vs 102.73). Why it failed: first-half habits are noise (PFF: scripted-play EPA stability r = 0.26), and there were no real first-half closes to test against, only an implied number. Job 4 now has the real lines |
| Role-change props (Coleman after 24 carries, Metcalf after an ejection) | On his 7 logged Week 11 props our model leaned the other way every time; he won 6 of 7 | Built (`props_news`) but lags on role changes (Job 1 part 3) |
| Weather | His 59% under at 12-14 mph matches our research 04 (56.1%, 691 games) | Have it; NFL wind faded since 2024; college wind failed (research 20) |
| Referees | Career over/under splits | Tested, no gain (research 17); nflverse fills referees for only 65 of 272 games this season |

**What to tune, ranked, each with the test that decides it** (copying him is allowed only if a test on data he did not pick says so; none
does):
1. **Grade derivatives and props at the close.** Built today for props and team totals. The decision comes from 100+ graded picks per type,
   with the luck range shown.
2. **Props role-change lag.** The pre-registered variant in question 12. It passes only if the held-out blend weight against Pinnacle
   rises above the current best (0.15).
3. **Read Pinnacle more often around news and releases.** The hourly reads cannot time a move within the hour, and there is a gap from
   00:33 to 14:02 UTC overnight. This is test L1's data.
4. **Our script's halves and team totals against Pinnacle's real derivative lines.** Test D1 and Job 4.
5. **Do not copy releases or trends.** If you ever want to know, the test is whether 1-point moves on an unchanged line, on markets he did
   not pick, continue or reverse by the close.

Which of these you placed is yours to say: Wagerhouse's open bets cannot be read (the history leaves them out; `wagers` ends Nov 21).

## Job 3. Outside research and the pre-registered tests

The sourced brief, every claim tagged, is `24a-sources.md`. The short version, across three sports and about 240 searches and fetches:
- **No public rating system beats the closing line in any of the three sports** with a record someone else checked. The Prediction Tracker
  grades every system: the NFL's best are 42-50% in 2023-2025; no NBA system is above 50.6% against the close over five seasons; college
  systems that beat the opener in 2010-2019 (54-55%) fell to 50-51% after 2020.
- **Published edges decay within 1 to 3 seasons.** Each public model did best in its first year. nfelo's closing-line value fell from 13% to
  3%. Unders on totals of 47.5+ worked 1979-2009 and then failed. Primetime unders worked 2019-2023 and then failed.
- **No handicapper's record was verified by a third party** in any sport. Contest winners are what chance produces with thousands of
  entries.
- **What lasts for a small bettor is execution:** a soft book's price against a sharp one, how fast the soft book follows, derivative lines
  set by rule of thumb, and news before the opener absorbs it (largest in college bowls: openers move 2.3-2.5 points; knowing the move
  perfectly is worth 58-64% there, about 54% in the regular season).

**The tests** (written in commit fccd765 before any ran; scripts `scripts/research24/pt_open.py`, `college_c1_c2.py`):

| Test | Rule | Result | Bar | Verdict |
|---|---|---|---|---|
| **F1** NFL: public ratings (systems average) against the opener, 2023-2025 | Bet the ratings' side at the opener when 1.5+ apart | 272-242 (52.9%, z 1.32); seasons 54.8%, 50.0%, 54.4%. The line moved toward the ratings 307-135 (69.5%, z 8.2). At the close: 254-251 (50.3%) | 150+, 52.4%+, no season under 50%, moves toward >55% with z ≥ 3 | **Passes as written.** The record alone is weak (z 1.3). The strong finding is the move: when the ratings and the opener disagree, the line goes to the ratings 7 times in 10. Caveat: the site does not say when it captures its opener or the ratings |
| **N1** NBA: BPI against the opener, seasons nobody here had opened (2018-19 to 2020-21) | Same, BPI | 900-878 (50.6%, z 0.52); seasons 49.8%, 50.5%, 51.3%. Moved toward 53.3% | 150+, 52.4%+, z ≥ 2, no season under 50% | **Fails.** The helper's 53.8% (2021-2026) did not replicate. The NBA opener idea is closed |
| **C1** College: small-conference teams after a 14+ point miss (Bennett 2021), 2021-2026 | Back the team that beat the spread big, fade the one that missed | 465-493 (48.5%); 2021-23 51.1%, 2024-26 45.7%. Power-conference control 49.3% | 150+, 52.4%+, 50%+ in both halves | **Fails.** Closed |
| **C2** College: fade last season's SP+ top 25 in weeks 1-4, 2021-2026 | At the close | 183-187 (49.5%) | 150+, 52.4%+, 2026 not under 50% | **Fails.** The 2027 test in research 23 stays as written |
| **L1** All three sports: does Wagerhouse trail Pinnacle long enough to bet? (forward) | Paper pick when Wagerhouse is 1+ point better than Pinnacle's current number | Starts when you say yes; not built | 150+ per sport, closing-line value above zero | Question 13 |
| **D1** NFL: our script's halves and team totals against Pinnacle's derivative lines (forward) | Frozen rule from research 04 | This week's slate below; forward grading not built | 150, closing-line value above zero | Question 13 (as D1b) |

What F1 means for you: a paper lane, not money. Each Sunday night and Monday, where the public ratings and Wagerhouse's early NFL number
disagree by 1.5+ points, freeze a $0 pick at Wagerhouse's number and grade it on closing-line value against Pinnacle. That tests the one
thing the history shows (the line moves toward the ratings) at the book you bet. Question 13.

## Job 4. Picks Wagerhouse can't take (or can), on paper

Wagerhouse does post first-half and first-quarter spreads and totals and game team totals for the NFL; we already log them, and Pinnacle's,
every hour (`derivative_snapshots`). It does not post half team totals as straight bets, and its props are in Bet Builder, which we cannot
read.

**The proposal (not built; your yes first):** a paper lane, "NFL derivatives".
- Our script's first-half total, first-half margin and game team totals, priced against Pinnacle's derivative lines.
- A pick at 4% of win chance (the playbook's bar for halves), frozen at Pinnacle's price, never sent as `bet`.
- Shown on the NFL card and on the tracker's paper line.
- Graded on Pinnacle's last read before kickoff and on the result.
- Kill rule: at 150 graded, off if average closing-line value is not above zero.

**What it would have shown this week** (`scripts/research24/d1_slate.py`, latest reads Nov 24): 54 options priced on 16 games, **7 paper
picks**:
- New England at LA Chargers 1H Over 17.5 (+102), +11.5%
- Washington at Arizona 1H Over 20.5 (−109), +7.4%
- Rams 1H −1.5 (+104), +6.3%
- Dolphins 1H +3 (−113), +6.2%
- Las Vegas at Cleveland 1H Over 20.5 (+102), +5.2%
- Carolina at Tampa Bay 1H Over 21.5 (−106), +5.1%
- Denver at Pittsburgh 1H Over 19.5 (+101), +4.1%

**Read that list with suspicion.** Five of seven are first-half Overs. The frozen rule (first half = 1.89 + 0.47 × full total) runs 0.41
points above Pinnacle's own first-half totals on this week's 16 games, and 2026 first halves have scored 0.51 below it. So most of those
"edges" are the rule's lean toward the Over, not a handicap. The Texans first-half team total Sharp released is not on the list, because the
frozen rule has no first-half team totals.

**So the lane should start from a corrected rule, D1b, fixed here before any forward data:** our first-half number = Pinnacle's first-half
number + 0.47 × (our full total − Pinnacle's full total), and the same with 0.62 for the margin. Our team totals stay the script's blended
team points. That prices only where our script disagrees with Pinnacle's full-game line, which is a test of the script, and research 15 and
18 say to expect a null. That is the honest reason to run it on paper: to learn cheaply whether derivatives are mispriced where full games
are not.

## Your questions (yes or no; my advice in brackets)

1. Props: weight our model 0.15 (NFL) and 0.25 (NBA) against Pinnacle instead of 0.5, as the data says. **[yes]**
2. NBA spreads and totals: back to shown-only (no money) until the NBA script can see injuries. **[yes]**
3. News adjustments: count them in the CHECK distance, and refuse one bigger than NFL 3, college 5.5, NBA 4 points. **[yes]**
4. News: measure "what Pinnacle has priced" from its earliest read in the 12 hours before `news_at`, so a late time can't double-count. **[yes]**
5. Our number: use Pinnacle's price as well as its line; fit the NFL script on forecast weather, not actual weather; widen the NBA
   team-total curve to 11.5. **[yes]**
6. Stops: count from Nov 23 (`live_since: 2026-11-23`) so yesterday's 11 picks count; the review line counts from the same date. **[yes]**
7. Telegram, recap and tracker in units first ("½ unit ($12.50)"), not dollars. **[yes]**
8. Read until 9pm Mountain every day (resends, CANCELLED and closing lines for evening NBA and college games), and run the NBA watcher at
   6:30pm too. **[yes]**
9. When the best pick on a game has "moved against", let the next-best pick on that game be issued. **[yes]**
10. Picks made paper by the one-unit-a-game rule stop counting against the weekly cap. **[yes]**
11. Grade prop profit at the "don't bet past" price (what you actually get), and void props whose player doesn't play and games that are
    postponed. **[yes]**
12. Test (paper only) a props variant: drop zero-usage games, and carry a carry-share jump into catches. Judged against Pinnacle, written
    down before it runs. **[yes]**
13. Build three paper lanes: Wagerhouse trailing Pinnacle (L1), early-week NFL numbers against public ratings (F1), NFL derivatives on the
    corrected rule (D1b). $0, never sent. **[yes]**
14. The Titans +15 pick (Sunday, staked ½ unit) was cleared on "nothing else found". It was issued 23 minutes before that clear stopped being
    allowed, and today it would be held. Bet it or not is your call; the engine keeps it on the record. **[your call]**

## Reload, and what each lane can do now

Reload the two jobs whose files changed (the same as README "To stop", then start):
`launchctl bootout gui/$(id -u)/com.kylor.betting-engine.poll; launchctl bootout gui/$(id -u)/com.kylor.betting-engine.weekly; cp ops/launchd/com.kylor.betting-engine.{poll,weekly}.plist ~/Library/LaunchAgents/; launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kylor.betting-engine.poll.plist; launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kylor.betting-engine.weekly.plist`

Lanes, after today (no money rule changed):
- **NFL spreads and totals:** staked, B picks at ½ unit. Fast reads now cover Wednesday's 6pm game, Thanksgiving morning and Friday.
- **College spreads and totals:** staked. Saturday's three missing games now read.
- **NBA spreads and totals:** staked. No false official-report news.
- **NFL props:** staked at weight 0.5, pending question 1.
- **NBA props:** staked at weight 0.5, pending question 1. Re-centring is safe across rematches.
- **NFL Wong teasers:** staked, 1 unit. A test read can no longer send a ticket.
- **Every lane:** "don't bet past" now matches CANCELLED; system lines retry; the recap shows the luck range.
