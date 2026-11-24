# Betting Engine: how code is built

**Read `CHARTER.md` first, then `PLAYBOOK.md`.** The charter owns what this engine is for, what reaches Telegram, the money rules, the
locked decisions and how sessions work. The playbook owns how a pick is chosen and graded. This file owns how code is built. If this file
disagrees with either, they win. It contains no pick rules and no money amounts on purpose (decision 0027): those drifted when three files
repeated them.

Owner: Kylor (Denver, Mountain time). Research is in `docs/research/`, decisions in `docs/decisions/`, every command in `README.md`.
`HANDOFF.md` is the original Phase 0 brief and is historical.

## Before you change anything

- `git status` and `git log`. Generated outputs of a scheduled run (cards, `TRACKER.md`, `STATUS.md`) are not anyone's unfinished work.
- `uv run engine lock take "what you are changing"` before editing `src/`, `ops/`, `config.yaml`, `adjustments.yaml`, `CHARTER.md` or
  `PLAYBOOK.md`. Refused means another session holds it: stop and ask Kylor. `uv run engine lock release` after you commit.
- Build what a decision note approves. A change to a rule gets a new decision note that says what it replaces, and the same commit updates
  every document that quoted the old rule.

## Environment

- Python 3.11+, `uv`, and `UV_PROJECT_ENVIRONMENT=.venv.nosync` in every shell (a `.venv` inside iCloud breaks `uv run`).
- DuckDB at `data.nosync/engine.duckdb`. The hourly read, the 10-minute fast reads, the NBA watcher and research runs all open it; connect
  through `engine.odds.snapshots.connect`, which waits for the lock instead of failing.
- Scheduled jobs are launchd plists in `ops/launchd/`; Kylor loads them himself with `launchctl`. Logs: `~/Library/Logs/betting-engine/`.
- The research agent is a headless `claude -p` run with `ops/agent_prompt.md` plus `ops/agent_prompt_<sport>.md`. It may write only its
  decisions and checks files and `adjustments.yaml`.

## Sources (no paid data)

- **Wagerhouse:** Kylor's own account, read-only. Login is a JSON POST to `/cloud/api/System/authenticateCustomer`; lines and the history
  reports under `/cloud/api/Report/`. The client refuses any operation not on its read-only list. Reads are scheduled (hours in
  `config.yaml`), never a constant poll. The history report does not return open bets. Wagerhouse props (Bet Builder) are not readable.
- **Pinnacle** guest lines and props: the market reference. Vig removed before use.
- **ESPN:** DraftKings lines (kept for history and the bet audit, not the reference), NFL injuries, NBA box scores.
- **News:** the Rotoworld relay tagged by `ops/reporters.yaml`, the official NBA injury report PDF, then ESPN.
- **History and stats:** nflverse (`nflreadpy`), CollegeFootballData (free key in `.env`), The Prediction Tracker, Open-Meteo.
- If a source is down or returns junk, fail loudly and send a `system` alert. Never skip silently.

## Rules for code

- **Code owns every number.** The agent writes status and reasons only; files with number fields are rejected.
- **Log everything with a timestamp and the price at that moment.** Store UTC, show Mountain. Wagerhouse timestamps arrive in Eastern.
- **Freeze picks at issue.** A pick's line, price, stake and limit never change after it is first written.
- **Every message is saved** in `alerts_sent`, sent or not, with whether it was delivered.
- **Telegram kinds:** `bet` (a staked pick), `recap`, `system`; everything else is `info` or `stale` and held back by
  `telegram.send_kinds`. Never send a $0 pick as `bet`.
- **Generated, never typed:** `docs/lanes/STATUS.md`, `PLAYBOOK-RECORD.md`, `TRACKER.md`, `NEWS-PROPS.md`, cards, `board.html`,
  `tracker.html`. Any sentence that describes how a number was built is generated from the config that built it.
- **Tests never look ahead.** Anything tuned is checked walk-forward on seasons it never saw. Weather inputs in tests must be what was
  forecast at bet time, not what happened (research 18).
- **Don't double-count:** a factor already in a rating or in Pinnacle's line is not added again by hand.
- **Secrets** live in `.env`: never committed, printed or logged.
- **Every report prints the luck range** next to results, so a hot streak cannot pass for an edge.
- **Closing-line value:** sides, totals and moneylines on the line; props and team totals as Pinnacle's no-vig closing chance of the bet
  minus the chance its price needed. A compass, not proof.
- **The YAML key `on` loads as `True`;** use `enabled`.
- **Teasers the code may build:** 2-team 6-point at -110 (Wagerhouse's "6/4 MIX"), NFL sides, both legs crossing 3 and 7 (Wong legs).
  Anything else in Kylor's own bets is flagged by the audit. Buying points: only on or off 3 in the NFL at 10 to 15 cents.
- **Auto-commit** (`gitsync.py`) commits only the generated paths it lists, never `src/`, and skips while a session holds the lock.

## Tests and finishing

- `uv run pytest` must pass before a commit. New behaviour gets a test in `tests/`.
- Run `uv run engine status` after any change to config or to what a lane does, and check the table against what you changed.
- End by committing, releasing the lock, and saying in plain English what each lane can and cannot do now.

## History (what the phases built)

Phase 1A: the bet audit (`engine audit`, research 01). Phase 1B: line logger, alerts, bet log, launchd jobs. The price-checker picks engine
(Nov 21-22, research 01-14) was replaced by the playbook (Nov 23, decision 0018). The ratings, pace, first-half, openers, injury-report,
college-systems and NBA rest models all failed against the close and are off; the game scripts, props models and teasers are what run now
(`PLAYBOOK.md` section 9).

## Out of scope

Auto-placing bets, live betting, baseball, hockey, soccer, paid data feeds.
