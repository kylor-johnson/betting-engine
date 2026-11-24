# Betting engine

Personal tool. Handicaps NFL, college and NBA games, sends the bets it finds to Telegram with a stake and a "don't bet past" number, and grades them against what you bet. It does not place bets. Start with `CHARTER.md`, then `PLAYBOOK.md` (how picks are chosen) and `CLAUDE.md` (how code is built). Research: `docs/research/`. Decisions: `docs/decisions/`.

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
| `uv run engine agent` | The research run: Claude clears or holds the playbook's CHECK rows and records its news decisions ($0 record), then the card is written to `docs/cards/` |
| `uv run engine agent --no-send` | Same, but prints the alerts |
| `uv run engine agent --skip-research` | Re-prices the existing decisions at current numbers without new research |
| `uv run engine slate` | Just the numbers: fair line and edge for every NFL game in the next 8 days |
| `uv run engine card` | Renders today's card from the latest slate sheet and `docs/cards/decisions/<date>-nfl.yaml` |
| `uv run engine injuries` | Current NFL quarterback statuses (`--all` for every position, `--team Vikings`) |
| `uv run engine poll --force` | Read Wagerhouse and market lines now, store them, send any alerts |
| `uv run engine poll --force --no-send` | Same, but print alerts instead of sending |
| `uv run engine playbook --dry-run` | The playbook pick lists for NFL, NBA and college right now (PLAYBOOK.md), without sending or saving anything; `--sport NBA` for one |
| `uv run engine playbook-record` | Playbook record by sport and market, and the weight re-fit from every priced candidate (`docs/lanes/PLAYBOOK-RECORD.md`) |
| `uv run engine tracker` | Every Telegram pick next to your actual Wagerhouse bets since Nov 23: the model's record, yours on its picks, yours on your own bets, and how closely each pick was followed (`docs/lanes/TRACKER.md`; synced twice a day automatically, 9am recap on Telegram) |
| `uv run engine tracker-publish [--local]` | The live model-picks page: only picks the model sent to Telegram (never your own bets), pushed to Vercel; also pushed automatically when the picks change (`public_tracker` in config.yaml; needs `vercel login` once; live at https://model-picks-fb0112.vercel.app) |
| `uv run engine poll` | What the scheduled job runs: reads only in the hours listed in `config.yaml` |
| `uv run engine watch add "Kansas State +10 -115"` | Alert when Wagerhouse has +10 or better at −115 or better |
| `uv run engine watch add "Bills/Jets o44"` / `"Bills ML -150"` | Totals and moneylines |
| `uv run engine watch list` / `watch remove 3` | See or drop watchlist entries |
| `uv run engine sync` | Pull the last two weeks of graded bets from the account into the history |
| `uv run engine audit` | Price every graded bet against the closing line; writes `docs/research/01-bet-audit.md` |
| `uv run engine report` | Weekly report for the last completed week, written to `data.nosync/reports/`; its summary is kind `info`, so it is not sent |
| `uv run engine report --week 2026-11-10 --no-send` | A specific week, printed |
| `uv run engine book` | How Wagerhouse's lines compare with the market so far |
| `uv run engine bet add "Kansas State +10 -110 25" --note "why"` | Log a bet by hand with a reason (graded bets arrive from the account automatically) |
| `uv run engine check` | The charter's working checks and the sport parity check (`docs/lanes/CHECKS.md`); runs itself every morning |
| `uv run engine news [--sport College]` | Every news entry in `adjustments.yaml` for upcoming games and whether it counts in the playbook number now |
| `uv run engine lock take "why"` / `lock release` / `lock` | One session owns the code: take the lock before changing code, config, the charter or the playbook; release it after committing (decision 0027) |
| `uv run pytest` | Run the tests |

## How a pick gets made

`PLAYBOOK.md` is the whole method. In short: code builds its own number for every market from a game-script handicap, pulls it toward Pinnacle, and picks where that beats Wagerhouse's price (A and B grades). Picks whose number is far from the market are held as CHECK until the research agent finds a sourced reason. Staked picks go to Telegram with stake, limit and how much of the edge was price and how much was handicap. Nothing else goes to Telegram except the 9am recap and system lines (`CHARTER.md`).

Research runs happen at 8:15am every day and 6:45pm Sunday, Mountain (`config.yaml` `agent.schedule`; the agent launchd job matches it since decision 0033, and the hourly read starts a missed one), and on change: a quarterback's status change, new NFL games at your book, an NBA watcher hit, or a new stale number (for that sport), at most once every 90 minutes per trigger (`config.yaml` `agent:`, decision 0016).

## Running on a schedule (launchd)

Five jobs (the fifth, `burst`, runs fast reads every 10 minutes and can start research on a new stale number): line and news reads every 30 minutes (the command itself only reads in scheduled hours), research runs on the schedule above, the weekly report Tuesday 9:00, and the NBA injury watcher three times a day (10am, 3pm and 5pm Mountain, set in `config.yaml` under `nba_watch.run_times`).

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

After changing a plist in `ops/launchd/` (decision 0033 changed the agent's), copy and reload it:

```
cp ops/launchd/com.kylor.betting-engine.agent.plist ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u)/com.kylor.betting-engine.agent; launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kylor.betting-engine.agent.plist
```

**NBA injury watcher** (`engine nba-watch`): reads ESPN's public NBA injury report. When a player who averages 22+ minutes on a team playing in the next 30 hours moves between playing and not playing (to or from Out or Doubtful, or off the report), it reads Wagerhouse and Pinnacle once (at most 12 extra reads a day), records the news with both lines (kind `news`: on the board, not sent to Telegram), and starts an NBA research run (at most one every 20 minutes). A pick still comes only from the card, when the numbers support it. Sources, fastest first: Rotoworld's relay of beat writers and insiders (each tagged from `ops/reporters.yaml`), the official NBA injury report PDF (every 15 minutes on game days), then ESPN. Test it without messaging: `uv run engine nba-watch --dry-run --force`. See which listed reporters actually reach the engine: `uv run engine reporters`. Details: `docs/research/07-injury-news-sources.md`.

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
- `ops/agent_prompt.md`: the research agent's shared instructions; `ops/agent_prompt_nfl.md`, `_college.md`, `_nba.md`: one guide per sport
- `docs/cards/<date>-nfl-teasers.md`: the Wong-teaser legs, tickets (real money since decision 0019) and record (decision 0014)
- Times are stored in UTC and shown in Mountain. Wagerhouse reports Eastern.
