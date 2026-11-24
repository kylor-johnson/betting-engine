# Charter: what this engine is for, and how we keep it on track

Owner: Kylor. Written 2026-11-23. Every session reads this before `CLAUDE.md` and before touching anything. If something in the code, the spec or a handoff disagrees with this page, this page wins until I change it.

## What I want

An agent that does the handicapping research on a schedule and tells me when there is a bet to place, early enough in the week that I'm the one holding the good number.

**Telegram is the source of truth (decision 0026).** It is where I get every bet this model finds, with its stake and its "don't bet past" number, and I place them from there. Anything that is not on Telegram is not a bet.

It is not a price checker. The tracker (`tracker.html`, decision 0024) grades every Telegram pick against what I actually bet; the price checks, logs and reports are plumbing.

This repository is the betting engine only. Nothing else lives here: my DFS model has its own folder and its own repository, and the two never share code, data or settings.

## The lanes

The engine is separate lanes. Each has its own model, its own status, its own record and its own messages.

1. NFL spreads and totals
2. College football spreads and totals
3. NBA spreads and totals
4. NFL player props
5. NBA player props
6. NFL Wong teasers (added 2026-11-23, decision 0014; real money since decision 0019)

Each sport has its own research-agent guide (`ops/agent_prompt_<sport>.md`) and its own record by market (`docs/lanes/PLAYBOOK-RECORD.md`), so no sport hides behind another's progress.

A lane is never allowed to hide inside another lane's "no bets" message.

## What "working" looks like

- Every lane says, in plain words, what it is evaluating right now and what it is not.
- Every lane produces output on its schedule: picks, or a clear statement that it has no model that can produce one yet.
- Every pick is logged at the price when issued and graded against the result and the closing line.
- I can open one page and see every lane, what each one looks at, and each one's record.

## The drift guard

This is the rule that stops me finding out a week later that the engine is only looking at wind.

1. **One generated status table.** A command (`engine status`) builds a table from the live config and code, never typed by hand. For each lane it shows:
   - which inputs are switched on;
   - which models are switched on, and whether each passed a test, failed, or is still being tested;
   - what can produce a pick in that lane today;
   - the lane's record and the date of its last pick.
2. **It goes where I will see it.** The table is on the board page and in `docs/lanes/STATUS.md`. (It used to go to Telegram on Mondays; since Telegram became bets-only it does not. See "Telegram" below.)
3. **Switching something off is an event.** If a session turns off a model, an input or a lane, it writes a decision note, the status table changes, and the session tells me in its summary what was turned off and why.
4. **Cards say what they actually do.** Any sentence on a card or message that describes how a number was built must be generated from the same config the number came from.
5. **Every session ends by checking the table** against what it changed, and says in its summary what each lane can and cannot do now.

`engine status` now exists (built 2026-11-23). The table is generated into `docs/lanes/STATUS.md`, onto `board.html`, and to Telegram on Monday mornings and whenever it changes. Do not edit it by hand; change `config.yaml` (`lanes:` and the switches it points to).

The current table is `docs/lanes/STATUS.md` (generated). A hand-typed copy used to sit here and went stale within a day (research 18), so it was removed.

Tested against the closing line and left off (each has a write-up in `docs/research/`): sides from market ratings and public systems (04), sides from play-by-play ratings (03), totals from pace and efficiency (02), first-half scoring habits (05), early-week openers from ratings (09), the NFL injury report with practice status, college public rating systems, NBA rest and travel (14), NBA and college game scripts for staked picks (16), outlier half weight, injury clusters, referees, and blitz/stacked-box prop matchups (17). Passed and in use: wind on NFL totals (05), schedule-adjusted form in the NFL script (17), the props lead effect for three stats (16), the landing tables (11a).

## How picks are chosen

**`PLAYBOOK.md` (approved 2026-11-23).** The engine handicaps each game (game script first, then injuries, weather, rest), builds its own number for every market, and picks where its number beats Wagerhouse's. Other books are a price filter and a sanity check, never the reason for a pick. Every slate gets a pick list graded A, B or C. In code, "the market" our number is blended toward is Pinnacle's line when posted, else Wagerhouse's (`playbook.market_implied`).

## Locked decisions

Do not reopen these without asking me.

- I stay on Wagerhouse only. It is a soft book; that is probably where my edge is.
- No paid data.
- The engine never places bets. I place every bet by hand.
- Pregame only. NFL, college football and NBA.
- Units: NFL $50, NBA $25 (changed 2026-11-23, decision 0020); college $25 until I say otherwise.
- Code owns every number. The agent owns research and judgment, and cannot type a line, a price or a stake.
- Every pick has a "don't bet past" number.
- Betting splits and reverse line movement are never a reason for a pick.
- A price gap alone is never a reason for a pick.
- Tests never look ahead, and anything tuned is checked on seasons it never saw.

## Decided since this page was first written

**Leans: decided 2026-11-23, paper only.** Built in `src/engine/picks/leans.py`. The agent's best handicapped opinions, never staked, at most 3 per lane per week, each with a code-stamped Wagerhouse number and "don't bet past" number and one of three reasons (timestamped news Pinnacle has not moved for, a forecast of where the line goes, a wind or weather case). Graded on closing-line value, result, and whether I bet it. Not to be bet until 50 are graded and the average closing-line value is above zero. They show on the board and cards, never in Telegram.

**Real money from the start (2026-11-23, replaces the Stage 0 rule).** Playbook picks are staked from the first one: A picks 1 unit, B picks half a unit, C picks nothing, full size from the start. Units by sport: NFL $50, NBA $25 (decision 0020). Bankroll protection kept from decision 0012: if playbook picks are down 10 units, picks go back to paper until I say otherwise. Decision 0018.

**Changed 2026-11-23 (decision 0025, after research 18):** only NFL Wong teasers were staked; NFL full-game picks and all props were paper.
**Reversed the same evening (decision 0026). Telegram is the source of truth: it is where I get the bets this model finds, and I place them from there.** NFL full-game picks, NFL props and NBA props are staked again and sent to Telegram, with teasers. Decision 0025's guards stay: at most one unit on a game, never into a Pinnacle move against us, every Bet says what the number already prices, a CHECK clears only with a sourced reason. NBA and college full-game picks stay shown-only (their tests lost). Paper picks never go to Telegram; the tracker grades everything Telegram sent against what I bet.

**Telegram (current, `telegram.send_kinds` in `config.yaml`: bet, system, stale, recap).** It sends: staked playbook picks (A and B) and teaser tickets with their stake and limit; the old path's Bet, Conditional and cancellation messages; STALE NUMBER price alerts (labelled not a pick); the tracker's 9am recap; and alerts that the engine is broken. It never sends paper picks, C picks, NO BETS summaries, openers, news, the lane table or grades; those stay on the cards, `board.html` and `tracker.html`.

## How sessions work together

- **One session owns the code at a time.** Other sessions may read and write research, but do not edit `src/`, `config.yaml` or `adjustments.yaml` while another session is mid-change.
- **Commit before you hand off.** No session leaves uncommitted work for the next one to guess at.
- **Start by running `git status` and `git log`.** If there is uncommitted work you did not write, stop and ask me.
- **Logins live in `.env`** in this folder (Wagerhouse, Sharp Football Analysis, Telegram, CollegeFootballData). Every session reads them from there, so nobody retypes them. `.env` is never committed and never pushed.
- **Explain in plain English.** I'm technical but not a quant.
- **When I'm reading on my phone, the first line tells me what to do.**

## Where things live

```
CHARTER.md                 this page: purpose, lanes, drift guard, locked decisions
CLAUDE.md                  the build spec and working rules
README.md                  every command
config.yaml                every switch and threshold; the status table is generated from it
adjustments.yaml           this week's sourced point adjustments
PLAYBOOK.md                how picks are chosen (approved; what is built is in its section 9)
board.html                 the picks page (generated, not in git)
tracker.html               every Telegram pick against what I bet (generated, not in git)
docs/
  lanes/                   generated: STATUS.md (lane table), PLAYBOOK-RECORD.md (record and weight re-fit by sport and market),
                           TRACKER.md (picks against my bets), READINESS.md (the old Stage rules, kept for the old Bet path)
  research/                numbered research and test write-ups
  decisions/               one short note per decision, numbered
  handoffs/                handoffs between sessions, dated
  cards/                   daily cards per lane; decisions/ holds the agent's status and reasons
src/engine/                code
tests/
ops/                       scheduled jobs and the research agent's instructions
data.nosync/               database and raw data (not synced, not in git); data.nosync/tracker/open_bets.yaml holds open bets entered by hand
```
