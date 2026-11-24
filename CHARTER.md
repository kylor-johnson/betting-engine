# Charter: what this engine is for, and how we keep it on track

Owner: Kylor. Written 2026-11-23; revised the same night after the charter review (`docs/research/19-charter-review.md`, decision 0027).
Every session reads this before anything else. If the code, the playbook, the spec or a handoff disagrees with this page, this page wins
until I change it. `PLAYBOOK.md` owns how a pick is chosen; `CLAUDE.md` owns how code is built. Neither repeats a money amount or a locked
rule; they point here.

## What I want

An agent that does the handicapping research on a schedule and tells me when there is a bet to place, early enough in the week that I'm the
one holding the good number.

**Telegram is the source of truth (decisions 0026, 0027).** It is where I get every bet this model finds, with its stake and its "don't bet
past" number, and I place them from there. Telegram carries only three things:
- **staked picks**: playbook A and B picks and teaser tickets, each with stake, limit, and how much of the edge is price and how much is
  handicap (a CANCELLED message if a sent pick should no longer be bet);
- **the 9am recap**: yesterday's results, what was not sent and why, and the money rules (this week's total, units left
  before each stop);
- **system lines**: the engine is broken, or a lane changed (a model or lane switched, a stop tripped, a lane fell below its review line).

Anything that is not on Telegram is not a bet, and nothing on Telegram is a $0 pick. Config: `telegram.send_kinds: [bet, system, recap]`.

It is not a price checker. The tracker (`tracker.html`, `docs/lanes/TRACKER.md`) grades every Telegram pick against what I actually bet,
and shows the picks that were not sent (paper lanes, per-lane caps, holds) on their own line. The price checks, logs and reports are plumbing.

This repository is the betting engine only. My DFS model has its own folder and its own repository, and the two never share code, data or
settings.

## The lanes

1. NFL spreads and totals
2. College football spreads and totals
3. NBA spreads and totals
4. NFL player props
5. NBA player props
6. NFL Wong teasers

Each lane is in one of three states, set in `config.yaml` and shown in `docs/lanes/STATUS.md`: **staked** (sent to Telegram), **paper**
(issued and graded at $0, not sent), or **shown** (on the card only). Today: staked = NFL spreads and totals, NFL props, NBA props, NFL
teasers; shown = college and NBA spreads and totals.

Each sport has its own research-agent guide (`ops/agent_prompt_<sport>.md`) and its own record by market (`docs/lanes/PLAYBOOK-RECORD.md`),
so no sport hides behind another's progress. A lane is never allowed to hide inside another lane's "no bets" message.

## How picks are chosen

`PLAYBOOK.md`, and only there. In one sentence: the engine builds its own number for each market from a game-script handicap, pulls it part
of the way toward Pinnacle, and picks where that beats Wagerhouse's price; the research agent clears the picks whose number is far from the
market. **There is one pick path.** The research agent does not send picks of its own; its news decisions are a $0 record on the card.

## Money

- **Units:** NFL $50, NBA $25, college $25 (decision 0020).
- **Stakes:** A = 1 unit, B = half a unit, C = nothing. A teaser ticket = 1 NFL unit. At most 1 unit on any one game across picks and teaser
  legs.
- **No bankroll figure and no weekly dollar cap for now** (my call, Nov 23): everything is in units. The code keeps a weekly cap switch
  (`playbook.weekly_cap_dollars`, 0 = off) for when I want one.
- **Stops:** each sport pauses to paper when its staked picks are down 10 units since `live_since`; NFL counts teaser tickets. A stop is a
  pause for review, not a verdict: at this volume 10 units can go in two bad weeks by luck alone. I restart it.
- **Review line:** a staked lane whose average closing-line value is below -1.5% win chance on 25 graded picks gets one Telegram line and a
  session review. It stays staked until I decide.
- **Yardstick for keeping a lane staked** (research 18): full-game, closing-line value of +2.4 points of win chance on 100 picks; props, the
  blend beats Pinnacle on 300 and closing-line value is above zero; teasers, 72.4% on 300 legs. Missing them is a review, not an automatic
  switch-off, because I chose to stake these lanes (decision 0026).

Changing anything in this section needs a decision note I asked for.

## What "working" looks like

These checks pass, at the end of every session and every morning:

1. Every staked pick (playbook and teaser, more than $0) has a Telegram message marked delivered and a row in the tracker.
2. No Telegram message of kind `bet` has a $0 stake.
3. Every staked pick has a "don't bet past" number and is graded within 24 hours of the game ending; props and team totals also have a
   closing grade.
4. Every lane's last candidate (A, B or C) is less than 2 days old for the NBA and less than 8 days old for the NFL and college in season,
   or `STATUS.md` says why.
5. `STATUS.md` was generated in the last 24 hours from the current config.
6. The tracker shows this week's staked total and how many units are left before each stop.
7. The hourly read ran in the last 2 hours during read hours, and the research runs ran at their fixed times.
8. No session lock is older than 4 hours.

## The drift guard

This is the rule that stops me finding out a week later that the engine is only looking at wind.

1. **One generated status table.** `engine status` builds it from the live config and the database, never by hand. For each lane: which
   inputs are on; which models are on and whether each passed, failed or is still being tested; what can produce a pick today; the lane's
   staked record; the date of its last pick.
2. **It goes where I will see it.** The table is on `board.html` and in `docs/lanes/STATUS.md`. When a lane changes (a model switched on or
   off, a lane moved between staked, paper and shown, a stop tripped, a review line crossed), Telegram gets one line saying what changed.
3. **Switching something off is an event.** A session that turns off a model, an input or a lane writes a decision note, the table changes,
   and the session says in its summary what was turned off and why.
4. **Cards say what they actually do.** Any sentence on a card or message that describes how a number was built is generated from the same
   config the number came from.
5. **Every session ends by checking the table** against what it changed, and says in its summary what each lane can and cannot do now.

What has been tested and its result is in `PLAYBOOK.md` (section 9) and `STATUS.md`. Do not edit the table by hand; change `config.yaml`
(`lanes:` and the switches it points to).

## Locked decisions

Do not reopen these without asking me.

- I stay on Wagerhouse only. It charges more than sharp books, so a pick has to beat its higher margin. If it has a weakness, it is being
  slow to follow news; that is measured, not assumed.
- No paid data.
- The engine never places bets. I place every bet by hand.
- Pregame only. NFL, college football and NBA.
- Money rules are in the Money section; a session never changes them without a decision note I asked for.
- Code owns every number. The agent owns research and judgment, and cannot type a line, a price or a stake.
- Every pick has a "don't bet past" number.
- Betting splits and reverse line movement are never a reason for a pick.
- A price gap alone is never a reason for a pick. Because the playbook blends toward Pinnacle, a pick can clear the bar mostly on
  Wagerhouse being off Pinnacle, so every pick shows how much of its edge was the price and how much was the handicap, and the tracker
  totals it per lane.
- Tests never look ahead, and anything tuned is checked on seasons it never saw.

History of how we got here: `docs/decisions/`.

## How sessions work together

- **One session owns the code at a time, enforced.** Before editing `src/`, `ops/`, `config.yaml`, `adjustments.yaml`, `CHARTER.md` or
  `PLAYBOOK.md`, run `uv run engine lock take "what you are changing"`. If it is refused, stop and ask me. Release it
  (`uv run engine lock release`) after you commit. A lock older than 4 hours is stale. Scheduled jobs do not auto-commit while a lock is
  held. The research agent may still write its decisions, checks and adjustments files.
- **Decisions:** the newest decision note wins. It says what it replaces (`Replaces: 00NN` or `Replaces: none`), and the same commit updates
  every document that quoted the old rule (this page, the playbook, the agent prompts, config comments).
- **Commit before you hand off.** No session leaves uncommitted work for the next one to guess at.
- **Start by running `git status` and `git log`.** If there is uncommitted work you did not write, stop and ask me. Generated outputs of a
  scheduled run (cards, `TRACKER.md`, `STATUS.md`) are not work: say they are there and leave them for the engine's auto-commit.
- **Logins live in `.env`** in this folder (Wagerhouse, Sharp Football Analysis, Telegram, CollegeFootballData). Every session reads them
  from there. `.env` is never committed and never pushed.
- **Explain in plain English.** I'm technical but not a quant.
- **When I'm reading on my phone, the first line tells me what to do.**

## Where things live

```
CHARTER.md                 this page: purpose, Telegram, lanes, money, drift guard, locked decisions, sessions
PLAYBOOK.md                how picks are chosen and graded; what is tested and built (section 9)
CLAUDE.md                  how code is built: environment, sources, logging, secrets, tests
README.md                  every command
HANDOFF.md                 the original Phase 0 brief (historical)
config.yaml                every switch and threshold; the status table is generated from it
adjustments.yaml           this week's sourced point adjustments
board.html                 the picks page (generated, not in git)
tracker.html               every Telegram pick against what I bet (generated, not in git)
docs/
  lanes/                   generated: STATUS.md (lane table), PLAYBOOK-RECORD.md (record and weight re-fit by sport and market),
                           TRACKER.md (picks against my bets, money rules, where the edge came from), NEWS-PROPS.md
  research/                numbered research and test write-ups
  decisions/               one short note per decision, numbered
  handoffs/                handoffs between sessions, dated
  cards/                   daily cards per lane; decisions/ holds the agent's status, reasons and CHECK verdicts
src/engine/                code
tests/
ops/                       scheduled jobs and the research agent's instructions
data.nosync/               database and raw data (not synced, not in git); SESSION.lock (who holds the code);
                           tracker/open_bets.yaml (open bets entered by hand)
```
