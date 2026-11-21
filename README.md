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

## Running on a schedule (launchd)

Two jobs: line reads every 30 minutes (the command itself only reads in scheduled hours), and the weekly report Tuesday 9:00.

```sh
cp ops/launchd/*.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kylor.betting-engine.poll.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kylor.betting-engine.weekly.plist
launchctl kickstart gui/$(id -u)/com.kylor.betting-engine.poll    # run once now
tail -5 logs.nosync/poll.log logs.nosync/poll.err.log             # check it worked
```

To stop: `launchctl bootout gui/$(id -u)/com.kylor.betting-engine.poll` (and `.weekly`).

If `poll.err.log` says "Operation not permitted", macOS is blocking background access to iCloud Drive: System Settings → Privacy & Security → Full Disk Access → add `/opt/homebrew/bin/uv`.

Keep the Mac awake: plugged in, lid open, and `sudo pmset -c sleep 0` (never sleep on power). If reads stop for a long stretch, the next read sends a "no line reads for N hours" message.

## Where things are

- `data.nosync/engine.duckdb`: the database (not synced, not in git). Tables: `line_snapshots`, `polls`, `alerts_sent`, `watchlist`, `manual_bets`, `wagers`, `legs`.
- `data.nosync/raw/`: bet history from Wagerhouse and cached ESPN responses
- `data.nosync/reports/`: weekly reports
- `logs.nosync/`: scheduled job output
- `config.yaml`: unit, cap, alert thresholds, read hours, key numbers
- Times are stored in UTC and shown in Mountain. Wagerhouse reports Eastern.
