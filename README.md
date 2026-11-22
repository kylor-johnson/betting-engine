# Betting engine

Personal tool. Reads Wagerhouse's lines and bet history (read-only), compares them with the market (DraftKings via ESPN), sends alerts to Telegram, and grades bets against the closing line. It does not place bets. Plan: `BUILD_SPEC.md`. Research: `docs/research/`. Decisions: `docs/decisions/`.

## Setup (once)

```sh
brew install uv
cd "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Bettng Model"
export UV_PROJECT_ENVIRONMENT=.venv.nosync   # keeps the virtualenv out of iCloud; add this line to ~/.zshrc
uv sync
cp .env.example .env                          # then fill in; never commit .env
uv run engine telegram-setup                  # after sending your bot any message in Telegram
```

## Commands

| Command | What it does |
|---|---|
| `uv run engine matchup TEN DAL` | Play-by-play matchup numbers for two NFL teams (away, then home), with league ranks, last-four-games splits and schedule strength |
| `uv run engine spread-test` | Tests the engine's own play-by-play power number against closing spreads |
| `uv run engine totals-test` | Reruns the test of the NFL totals model against the market's closing totals (see `docs/research/02-totals-model.md`) |
| `uv run engine board` | Opens the picks page (`board.html`) in your browser: what to bet now, what is waiting, what came close and every game's numbers. Rebuilt after every research run |
| `uv run engine agent` | The research run: builds the numbers, has Claude research and decide, writes the card to `docs/cards/`, sends pick alerts |
| `uv run engine agent --no-send` | Same, but prints the alerts |
| `uv run engine agent --skip-research` | Re-prices the existing decisions at current numbers without new research |
| `uv run engine slate` | Just the numbers: fair line and edge for every NFL game in the next 8 days |
| `uv run engine card` | Renders today's card from the latest slate sheet and `docs/cards/decisions/<date>-nfl.yaml` |
| `uv run engine injuries` | Current NFL quarterback statuses (`--all` for every position, `--team Vikings`) |
| `uv run engine poll --force` | Read Wagerhouse and market lines now, store them, send any alerts |
| `uv run engine poll --force --no-send` | Same, but print alerts instead of sending |
| `uv run engine poll` | What the scheduled job runs: reads only in the hours listed in `config.yaml` |
| `uv run engine watch add "Kansas State +10 -115"` | Alert when Wagerhouse has +10 or better at −115 or better |
| `uv run engine watch add "Bills/Jets o44"` / `"Bills ML -150"` | Totals and moneylines |
| `uv run engine watch list` / `watch remove 3` | See or drop watchlist entries |
| `uv run engine sync` | Pull the last two weeks of graded bets from the account into the history |
| `uv run engine audit` | Price every graded bet against the closing line; writes `docs/research/01-bet-audit.md` |
| `uv run engine report` | Weekly report for the last completed week, summary sent to Telegram |
| `uv run engine report --week 2026-11-10 --no-send` | A specific week, printed |
| `uv run engine book` | How Wagerhouse's lines compare with the market so far |
| `uv run engine bet add "Kansas State +10 -110 25" --note "why"` | Log a bet by hand with a reason (graded bets arrive from the account automatically) |
| `uv run pytest` | Run the tests |

## How a pick gets made

1. Code builds the slate sheet: your book, Pinnacle and DraftKings prices; a fair line from market ratings, public rating systems and Pinnacle; the edge; the "don't bet past" number.
2. Claude researches the sides the numbers flag (injuries, weather, why the line moved) and writes status and reasons to a decisions file. It may add sourced entries to `adjustments.yaml`. It cannot write a line, price or stake.
3. Code re-prices at fresh numbers, renders the card, and sends a Telegram alert only for what changed: a new Bet or Conditional, a status change, or a pick whose value is gone.

Research runs happen on a schedule (Sunday 8:15am, 6:45pm and 8:45pm; Monday and Tuesday 8:15am; Wednesday to Friday 3:15pm; Saturday 8:15am, all Mountain) and whenever the hourly read sees a quarterback's status change or new NFL games at your book, at most once every 90 minutes.

## Running on a schedule (launchd)

Four jobs: line and news reads every 30 minutes (the command itself only reads in scheduled hours), research runs on the schedule above, the weekly report Tuesday 9:00, and the NBA injury watcher every 10 minutes (9am to 9pm Mountain, set in `config.yaml` under `nba_watch`).

```sh
cp ops/launchd/*.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kylor.betting-engine.poll.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kylor.betting-engine.weekly.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kylor.betting-engine.agent.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kylor.betting-engine.nba-watch.plist
launchctl kickstart gui/$(id -u)/com.kylor.betting-engine.poll    # run once now
tail -5 ~/Library/Logs/betting-engine/poll.log ~/Library/Logs/betting-engine/poll.err.log   # check it worked
```

To stop: `launchctl bootout gui/$(id -u)/com.kylor.betting-engine.poll` (and `.weekly`, `.agent`, `.nba-watch`).

**NBA injury watcher** (`engine nba-watch`): reads ESPN's public NBA injury report. When a player who averages 22+ minutes on a team playing in the next 30 hours moves between playing and not playing (to or from Out or Doubtful, or off the report), it reads Wagerhouse and Pinnacle once (at most 12 extra reads a day), messages the news with both lines, and starts an NBA research run (at most one every 20 minutes). A pick still comes only from the card, when the numbers support it. Test it without messaging: `uv run engine nba-watch --dry-run --force`.

Job logs live in `~/Library/Logs/betting-engine/` (outside iCloud, because macOS will not let a background job open a log file inside iCloud Drive). If `poll.err.log` says "Operation not permitted", macOS is blocking background access to iCloud Drive: System Settings → Privacy & Security → Full Disk Access → add `/opt/homebrew/bin/uv`.

Keep the Mac awake: plugged in, lid open, and `sudo pmset -c sleep 0` (never sleep on power). If reads stop for a long stretch, the next read sends a "no line reads for N hours" message.

## Where things are

- `data.nosync/engine.duckdb`: the database (not synced, not in git). Tables: `line_snapshots`, `polls`, `alerts_sent`, `watchlist`, `manual_bets`, `wagers`, `legs`.
- `data.nosync/raw/`: bet history from Wagerhouse and cached ESPN responses
- `data.nosync/reports/`: weekly reports
- `~/Library/Logs/betting-engine/`: scheduled job output
- `config.yaml`: unit, cap, alert thresholds, read hours, key numbers, picks and agent settings
- `adjustments.yaml`: this week's point adjustments, each with reason and source
- `docs/cards/`: one card per day; `docs/cards/decisions/` holds the agent's status and reasons
- `ops/agent_prompt.md`: the research agent's instructions
- Times are stored in UTC and shown in Mountain. Wagerhouse reports Eastern.
