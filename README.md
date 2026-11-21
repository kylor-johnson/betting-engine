# Betting engine

Personal tool. Compares Wagerhouse prices with the market, logs lines, and grades bets against the closing line. It does not place bets. Plan: `BUILD_SPEC.md`. Research: `docs/research/`. Decisions: `docs/decisions/`.

## Setup (once)

```sh
brew install uv
cd "~/Library/Mobile Documents/com~apple~CloudDocs/Bettng Model"
export UV_PROJECT_ENVIRONMENT=.venv.nosync   # keeps the virtualenv out of iCloud; add to ~/.zshrc
uv sync
cp .env.example .env                          # then fill in; never commit .env
```

## Commands

| Command | What it does |
|---|---|
| `uv run engine audit` | Prices every graded bet in the newest history pull (`data.nosync/raw/`) against DraftKings' closing line from ESPN, saves to the database, writes `docs/research/01-bet-audit.md` |
| `uv run engine audit --history PATH` | Same, for a specific pull file |
| `uv run pytest` | Runs the tests |

## Where things are

- `data.nosync/engine.duckdb`: the database (not synced, not in git)
- `data.nosync/raw/`: raw pulls from Wagerhouse and cached ESPN responses
- `config.yaml`: unit, cap, bankroll, key numbers
- Times are stored in UTC and shown in Mountain. Wagerhouse reports Eastern.
