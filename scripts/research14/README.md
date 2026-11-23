# Research scripts for docs/research/14-deep-review.md

Walk-forward tests from the Nov 23, 2026 review. Run from the project root:

```
export UV_PROJECT_ENVIRONMENT=.venv.nosync
uv run --with pandas --with pyarrow --with numpy --with statsmodels python scripts/research14/<script>.py
```

| Script | Section | What it tests |
|---|---|---|
| `nfl_inj.py` | 2a | NFL injury report (incl. practice status), snap-weighted, against the closing spread and total. Writes `data.nosync/reports/nfl_inj_games.parquet` |
| `nfl_move.py` | 2b | How much of the opener-to-close move is injury news (run `nfl_inj.py` first) |
| `ptr_test.py` | 2c | College: ~60 Prediction Tracker systems against the close and the opener |
| `extra.py` | 2c, 2f | College early-season split by season; college and NBA teaser legs |
| `nba_rest.py` | 2d | NBA rest, travel and schedule density against the close |
| `teaser.py` | 2f | NFL Wong teaser legs by era and total; key-number landing rates |

Data downloaded for these (free, not in git): nflverse snap counts in `data.nosync/raw/nflverse/snaps/`
(https://github.com/nflverse/nflverse-data/releases/tag/snap_counts) and Prediction Tracker season files in
`data.nosync/raw/tracker/archive/` (https://www.thepredictiontracker.com/ncaa2015.csv to ncaa2025.csv).
Not part of the engine; nothing imports them.
