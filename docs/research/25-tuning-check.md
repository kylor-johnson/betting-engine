# 25. Tuning check: every sport and bet type against decisions 0036 and 0037 (Nov 24, 2026, evening)

Handoff: `docs/handoffs/2026-11-24-tuning-check.md`. Every row below was checked in the code that issues, cancels and grades it, not in
the documents. Verdicts: **OK**, **fixed** (this commit, with a test in `tests/test_tuning_check.py`), or **Kylor decides**.

## Settings in force (`playbook.settings(cfg, sport)`, printed from the live config)

| | NFL | College | NBA |
|---|---|---|---|
| Weight on our number: side / total / team total | 0.25 / 0.35 / 0.4 | 0.25 / 0.35 / 0.4 | 0.25 / 0.35 / 0.4 |
| Props weight | 0.15 | (no props) | 0.25 |
| Minimum edge: full game / props | 3% / 4% | 3% / — | 3% / 4% |
| CHECK distance: side / total / team total | 3 / 4 / 4 | 6 / 7 / 6 | 4 / 6 / 5 |
| Largest news entry that counts | 3 points | 5.5 points | 4 points |
| Full game | staked | staked | shown only, news picks off |
| Void after (props / no final score) | 40 h / 72 h | — / 72 h | 30 h / 72 h |

All match decision 0036. Moneylines are not issued in any sport (the playbook builds sides, totals and team totals only).

## The grid

"Market ref" is what our number is pulled toward and what CANCELLED compares with. "Timing" is whether a read runs near enough to the
start to issue, CANCEL and take a closing price.

| Row | Settings | Market ref | Stake path | Caps | Grading | Timing | Card and message text | Verdict |
|---|---|---|---|---|---|---|---|---|
| NFL spread, total | OK | `pin_fair`; CANCELLED like with like (`FAIR_SINCE`) | staked | weekly cap with `COUNTS_FOR_CAP` | closing-line value on Pinnacle's closing line; void at 72 h; reaches tracker and public page | last full read 13 to 58 min before kick; fast reads give a close within 10 min | OK | OK; Kylor decides (question 5) |
| NFL team total | OK | Pinnacle's team total with its lean, else Wagerhouse's line | staked | as above | no-vig close, now this game's only | close from full reads only | OK | **fixed** (rematch lookup) |
| College spread, total, team total | OK | `pin_fair` | staked | weekly cap OK | as NFL | **no fast reads on Saturday evening or Friday night**; the close can be up to 58 min old | OK | Kylor decides (question 5) |
| NBA spread, total, team total | OK | `pin_fair` | always C: never stored as a pick, never a `bet` message; news picks off | n/a | candidates graded for the weight re-fit | every 30 min in the 3 h before tip (0037) | the card gave the old reason for shown-only | **fixed** (reason now from config) |
| NFL props | 0.15 | Pinnacle's no-vig chance | staked | weekly cap OK; per-game cap counts every prop | pays at `limit_price`; closing value at Pinnacle's price; void at 40 h | close from full reads only | CHECK note typed "15+" | **fixed** (CANCELLED weight at issue; CHECK text from config); Kylor decides (question 2) |
| NBA props | 0.25 | Pinnacle's no-vig chance | staked | daily cap OK; per-game as NFL | as NFL; void at 30 h; now graded the same night | every 30 min before tip | as NFL | **fixed** (CANCELLED weight; same-night grading); Kylor decides (question 1) |
| NFL teasers | -110, 6 points, total 49 or lower | n/a | staked; **a fast read could also send a ticket** | one unit a game counts teaser legs | win/loss only (no closing value, no void rule) | legs frozen at first sight; no CANCELLED | OK | **fixed** (fast reads freeze legs only) |
| L1, all sports | 1 point (0.5 through 3 or 7) | Wagerhouse against Pinnacle's raw line (the research 24 definition) | $0, never sent | none | closing-line value on the raw close | needs both books from the last 75 min | OK | OK |
| F1 | 1.5 points | public ratings against Wagerhouse | $0 | none | as L1 | Sun 5pm to Tue 6am | OK | OK |
| D1b | 4% | Pinnacle's first-half and team-total lines with their lean | $0 | none | no-vig close, now this game's only | — | OK | **fixed** (used the disagreement frozen at first sight) |
| College openers | 3 / 4 points | our number against Wagerhouse's first number (by design) | $0 | none | move to the close and result | — | OK | OK |
| NBA news props | 4%, 90 min | the full calibrated model against Pinnacle (a test of the signal, not the 0.25 blend) | $0 | none | result and closing value, now this game's only | — | OK | **fixed** (rematch lookup) |
| NFL news props | — | — | not built: news props are logged for the NBA only (decision 0025) | — | — | — | — | OK (not a lane) |

### What the grid fixed (beyond the known gaps below)

- **D1b carried a stale disagreement.** It read our number and the market's from `playbook_candidates`, which are frozen the first time a
  candidate is seen, possibly days earlier. If Pinnacle had since moved toward us, the gap was counted twice. Each candidate now also keeps
  the latest read's numbers (`last_own_value`, `last_market_value`, `last_seen_utc`; the first ones stay for the weight re-fit), and D1b
  uses only candidates priced in the last read.
- **Fast reads could send a real-money teaser ticket.** `burst.py` called `teasers.scan`, which builds and sends tickets. That broke the
  fast read's own rule (it sends no Telegram message). Fast reads now freeze legs only; the ticket forms and is sent on the next full read.
  The one ticket in the database came from a full read.
- **Team-total and prop lookups could read an earlier meeting of the same two teams.** Fixed in Pinnacle's current team total for
  CANCELLED, never-into-a-move, both closing grades, the paper lanes' close and the news props' result and close. Not yet hit (the data
  starts Nov 22), but NBA pairings repeat within weeks.
- **Text:** the NBA card's shown-only reason is now decision 0036's (from `playbook.sports.NBA.shown_reason`); the prop CHECK note reads its
  distance from config; the college card no longer prints a props weight; `TRACKER.md`'s "Every pick sent" table is units first and says
  "void" (`tracker.html` and the public page already were).

### Noted, not changed (the rules already say this)

- Closing-line value for sides and totals is on Pinnacle's closing line without its price lean, as `CLAUDE.md` says; team totals and props
  use the no-vig price. Our number now uses the lean (`pin_fair`), so the two measure slightly different things.
- A team total with no Pinnacle team total falls back to Wagerhouse's line, as the playbook says ("else Wagerhouse's line"). No sent pick
  used it.
- The props-per-game cap counts paper props too. It changes no stake (a game that is full stays full), only the paper reason.
- Teasers have no closing-line value, CANCELLED or void rule, and tickets may pair legs from different NFL weeks while the paper record
  pairs within a week. No decision covers these.
- The paper lanes, college openers and news props have no void rule, so a postponed game stays open on their reports.


## The known gaps from the handoff

### 1. Stale text about the NBA watcher — fixed

- `picks/nba_news.py` said "three times a day (10:00, 15:00 and 17:00)". It now names all four times and the half-hourly reads of 0037.
- The parity cell in `STATUS.md` was typed in `config.yaml` (`parity.news_source.NBA`). It is now built from config by
  `lanes.read_schedule`: the watcher times (`nba_watch.run_times`), the pre-tip half-hourly reads (`read_pregame_hours`) and the fast-read
  window (`burst`). Today it reads: "watcher at 10am, 3pm, 5pm and 6:30pm; full reads every 30 minutes in the 3 hours before any tip;
  10-minute fast reads from 2 hours before the day's first start only (cap 25 a day)". The next change to any of those times changes the
  cell with it.

### 2. NBA fast reads follow only the first tip — Kylor decides

Fast reads are a 10-minute window from 2 hours before the day's first tip to 15 minutes after it. Covering every tip instead would need:

| Night (Mountain) | Tips | Fast reads, first tip only | Fast reads, every tip |
|---|---|---|---|
| Sat Nov 21 | 5:30, 6:00, 8:00 | 14 | 29 |
| Sun Nov 22 | 1:30, 4:00, 5:00, 6:00, 6:30 | 14 | 44 |
| Mon Nov 23 | 5:00, 5:30, 6:00, 6:30, 8:00 | 14 | 32 |
| Tue Nov 24 | 5:00, 6:00, 8:00 | 14 | 32 |

Every night is over the cap of 25 a day, so this is not a plain fix. What the late games already get since decision 0037: a full read
every 30 minutes in the 3 hours before every tip, and each full read runs the stale-number scan and starts a research run on a new one
(`poll.py`). The gap is 10-minute against 30-minute resolution for late games, not no coverage.

### 3. The props weight change cancelled a pick sent under the old weight — fixed (same principle as `FAIR_SINCE`)

John Collins over 1.5 threes (+182) was sent at 7:02am MT under weight 0.5, edge +4.6%. At 4:32pm MT the CANCELLED test ran with
today's weight, 0.25: Pinnacle had not moved (33% over), the edge was +1.1%, and the pick was cancelled.

Why this is a plain bug: the charter sends CANCELLED "if Pinnacle moves so a sent pick should no longer be bet". A rule change is not
Pinnacle moving. `FAIR_SINCE` already keeps the market-reference change from cancelling older sides and totals; the props weight had no
equivalent. Now every pick stores the blend weight in force when it was issued (`playbook_picks.blend_weight`), and CANCELLED uses it, for
props and full-game picks alike. Props issued before the column existed get their weight back exactly from the frozen numbers (our chance =
Pinnacle's + weight × (model − Pinnacle)); all nine come back at 0.500.

The Collins CANCELLED message is already sent and is not taken back. Kylor placed that bet anyway; it stays on the record at the number sent.

### 4. Props grading lag — fixed

Not a lookup miss: `models/nba_data.download` fetched box scores only through yesterday, so a prop could not grade until the 7am read
the next morning (the Nov 23 props graded at 7:03am Nov 24). Team totals grade from ESPN's live scoreboard, which is why the Pistons-Magic
team total graded at 7:33pm and Collins' prop did not. The download now includes today; a scoreboard is still cached only once its day is
past and every game is final (`espn.scoreboard`), so tonight's games are never frozen as unplayed. Collins' prop (and the paper
assists prop on the same game) grade on the next read.

### 5. Research 24's unfixed plain bugs — all fixed

- **Missed-read alarm after 20 hours.** It now counts scheduled read hours (`read_hours`) since the last good read
  (`poll.missed_read_hours`) and fires at 2 (`missed_read_alert_hours: 2`, the charter's "2 hours during read hours"). The overnight gap
  has no read hours, so it needs no allowance.
- **`down_units` swallowed errors.** A missing table still means nothing is graded (0). Any other read error now raises: the playbook run
  and teaser tickets fail loudly in the log, the daily check says "could not read", and the tracker's money lines say COULD NOT READ
  instead of "+0.0".
- **The hourly read held the database lock during its network reads.** It now closes the database for the line read (Wagerhouse, ESPN,
  Pinnacle) and reopens it after. The props-model and grading steps that follow still hold it while they fetch; they are shorter.
- **No CollegeFootballData cache fallback.** When the site fails, the last good copy is used and the slate sheet's note carries a
  PROBLEM line saying so and how old it is. With no copy it still fails loudly.
- **The dry-run copy of the database was never deleted.** `engine playbook --dry-run` now removes it. 28 old copies (495 MB) were removed.

## Kylor decides

1. **NBA props: stay staked until the review line decides, or go to paper now?** Paper suggestions (5%+ disagreements): 71-72,
   −11.9 units. Live staked: 1-2, closing-line value −3.0% on 3 (the Collins prop grades on the next read). Research 24b: best weight 0.15
   to 0.20; live is 0.25. The review line needs 25 graded at −1.5%.
2. **NFL props: same question.** With each prop's true first read, the best weight is 0.00 (24b); live is 0.15. Live staked: 2-0,
   closing-line value −2.1% on 2.
3. **College props: no lane. Still fine?** The parity table says "planned", triggered by Pinnacle posting college props we can read.
4. **NBA fast reads before every tip, not only the first?** It needs 29 to 44 fast reads a night against a cap of 25 (table above). The
   half-hourly full reads already cover late tips.
5. **Half-hourly full reads before NFL and college starts too, like the NBA (`read_pregame_hours`)?** Today the last full read before a
   6:15pm Thursday, Sunday or Monday night kick can be 58 minutes out, and college has no Saturday-evening fast reads. Cost: about 3 more
   Wagerhouse reads per NFL night game and up to about 10 on a college Saturday.

## Kylor's answers (Nov 24, night)

1. NBA props: **paper** (decision 0038).
2. NFL props: **paper** (decision 0038).
3. College props without a lane: fine.
4. NBA fast reads before every tip: no.
5. Half-hourly pre-start reads for NFL and college: no. "NFL and CFB need less of a read but at least 2 times early week and then 3-4 for
   each game that is within 24 hours." The hourly read already reads every sport every hour from 7am to 9pm Mountain, every day
   (`read_hours`), so both minimums are met today with no change: Monday and Tuesday get about 15 reads each, and any game gets 15 or more in
   its last 24 hours unless the Mac is asleep, which the missed-read alarm now catches after 2 read hours.
