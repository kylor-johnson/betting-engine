# Charter: what this engine is for, and how we keep it on track

Owner: Kylor. Written 2026-11-23. Every session reads this before `CLAUDE.md` and before touching anything. If something in the code, the spec or a handoff disagrees with this page, this page wins until I change it.

## What I want

An agent that does the handicapping research on a schedule and tells me when there is a bet to place, early enough in the week that I'm the one holding the good number.

It is not a bet tracker and it is not a price checker. Those are plumbing.

This repository is the betting engine only. Nothing else lives here: my DFS model has its own folder and its own repository, and the two never share code, data or settings.

## The lanes

The engine is separate lanes. Each has its own model, its own status, its own record and its own messages.

1. NFL spreads and totals
2. College football spreads and totals
3. NBA spreads and totals
4. NFL player props
5. NBA player props
6. NFL Wong teasers, paper first (added 2026-11-23, decision 0014)

Each sport also has its own research-agent guide (`ops/agent_prompt_<sport>.md`) and its own money-readiness thresholds (decisions 0016 and 0017), so no sport hides behind another's progress.

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
2. **It goes where I will see it.** The table is on the board page and is sent to Telegram every Monday morning and any time it changes.
3. **Switching something off is an event.** If a session turns off a model, an input or a lane, it writes a decision note, the status table changes, and I get a message that day saying what was turned off and why.
4. **Cards say what they actually do.** Any sentence on a card or message that describes how a number was built must be generated from the same config the number came from.
5. **Every session ends by checking the table** against what it changed, and says in its summary what each lane can and cannot do now.

`engine status` now exists (built 2026-11-23). The table is generated into `docs/lanes/STATUS.md`, onto `board.html`, and to Telegram on Monday mornings and whenever it changes. Do not edit it by hand; change `config.yaml` (`lanes:` and the switches it points to).

Generated table as of Monday Nov 23, 2026 (see `docs/lanes/STATUS.md` for the current one):

| Lane | What produces a flag today | Own model that passed a test | Can issue a pick? | Record |
|---|---|---|---|---|
| NFL spreads and totals | Injury news the agent enters, counted only for the part Pinnacle has not moved for; wind on outdoor totals | Wind totals only | Sides: only on unpriced news. Totals: a half-unit Conditional from wind | 0-0 |
| College spreads and totals | Injury news the agent enters, same rule | None | Only on unpriced news | 0-0 |
| NBA spreads and totals | Injury news (checked 10am, 3pm, 5pm Mountain), same rule | None | Only on unpriced news | 0-1 (one Conditional, graded on result) |
| NFL props | Nothing yet | Being scored, not passed | No | Not started (150 of 300 graded) |
| NBA props | Nothing yet | Being scored, not passed | No | Not started (209 of 300 graded) |

Models tested and switched off because they did not beat the closing line: sides from market ratings and public systems, sides from play-by-play ratings, totals from pace and efficiency, first-half scoring habits, early-week openers from ratings.

## How picks are chosen

**`PLAYBOOK.md` (approved 2026-11-23).** The engine handicaps each game (game script first, then injuries, weather, rest), builds its own number for every market, and picks where its number beats Wagerhouse's. Other books are a price filter and a sanity check, never the reason for a pick. Pinnacle is no longer the fair line. Every slate gets a pick list graded A, B or C.

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

## Open decision I still owe

**Leans: decided 2026-11-23, paper only.** Built in `src/engine/picks/leans.py`. The agent's best handicapped opinions, never staked, at most 3 per lane per week, each with a code-stamped Wagerhouse number and "don't bet past" number and one of three reasons (timestamped news Pinnacle has not moved for, a forecast of where the line goes, a wind or weather case). Graded on closing-line value, result, and whether I bet it. Not to be bet until 50 are graded and the average closing-line value is above zero. They show on the board and cards, never in Telegram.

**Real money from the start (2026-11-23, replaces the Stage 0 rule).** Playbook picks are staked from the first one: A picks 1 unit, B picks half a unit, C picks nothing, full size from the start. Units by sport: NFL $50, NBA $25 (decision 0020). Bankroll protection kept from decision 0012: if playbook picks are down 10 units, picks go back to paper until I say otherwise. Decision 0018.

**Telegram is for bets only (2026-11-23).** Playbook A and B picks ping; C picks stay on the board (decision 0018). Before the playbook picks go live, Telegram pings only for a Bet, a Conditional or a cancellation (`telegram.send_kinds` in `config.yaml`), plus alerts that the engine itself is broken. NO BETS summaries, openers, news, price gaps, the Monday lane table and grades stay on the cards and `board.html`. This replaces the drift guard's rule 2 for Telegram; the table is on the board and in `docs/lanes/STATUS.md`.

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
board.html                 the page I look at
docs/
  lanes/                   one folder per lane (to be created)
    nfl-sides-totals/      what it evaluates, model status, tests run, record
    college-sides-totals/
    nba-sides-totals/
    nfl-props/
    nba-props/
  research/                numbered research and test write-ups
  decisions/               one short note per decision, numbered
  handoffs/                handoffs between sessions, dated
  cards/                   daily cards per lane; decisions/ holds the agent's status and reasons
src/engine/                code
tests/
ops/                       scheduled jobs and the research agent's instructions
data.nosync/               database and raw data (not synced, not in git)
```
