# Betting Engine: Build Spec for Claude Code

Owner: Kylor. Drop this in the repo root as `CLAUDE.md` (or reference it from there). Build in phases. Do not start a phase until the one before it passes its exit test.

## Ground rules

- Python 3.11+, `uv` for env, `polars` for data, `duckdb` as the local database (one file: `data/engine.duckdb`).
- Every number the system outputs gets logged with a timestamp and the odds at that moment. If we can't measure it against the close, it didn't happen.
- No model output becomes a bet without a "don't bet past" number.
- Unit = $25. Bankroll and Kelly fraction live in `config.yaml`, not in code.
- Secrets (API keys) in `.env`, never committed.

## Phase 1: Odds logger + CLV tracker (build this first, it pays for itself)

Why first: most of the value lost this season came from betting after the line moved. This phase fixes that before any model exists, and it creates the closing-line history every later phase needs.

1. **Odds ingest.** The Odds API (paid tier, ~$30/mo). Pull NFL, NCAAF, NBA spreads, totals and moneylines from Pinnacle (or the sharpest book available), Circa if available, plus 2-3 retail books. Poll every 15 min on game days, hourly otherwise. Table: `odds_snapshots(ts, sport, game_id, book, market, side, line, price)`.
2. **Openers and closers.** Derive `open_line` (first snapshot) and `close_line` (last snapshot before kickoff) per game/market/book.
3. **No-vig fair price.** Remove juice from the sharp book to get a fair probability for every snapshot.
4. **Alerts** (Telegram bot or Slack webhook):
   - A retail book is off the sharp fair line by more than a threshold (start at 1.5 pts for spreads, 2 for totals).
   - A line crosses a key number: NFL 3, 7, 10, 14; CFB the same plus 17, 21; NBA none.
   - Openers posted for the week (Sunday evening CFB, Sunday night NFL lookahead).
5. **Bet log.** A CLI command `bet add "KSU +10 -110 $20"` writes to `bets(ts, game_id, market, side, line, price, stake, book, source)`. After close, compute CLV in points and in no-vig probability.
6. **Weekly report.** Units won, CLV by sport/market/bet type, and the same split for -300 and shorter favorites vs. everything else.

Exit test: one full week of snapshots with no gaps, alerts firing, CLV computed for every logged bet.

## Phase 2: Football ratings model (NFL + CFB spreads/totals)

Data:
- NFL: `nfl_data_py`. Play-by-play with EPA, success rate, CPOE, air yards, 2016-present.
- CFB: CollegeFootballData API (free key). PBP, EPA/PPA, havoc, drives, lines.
- Weather: Open-Meteo forecast for stadium coordinates (wind and precip only matter outdoors).

Features (process over results):
- Opponent-adjusted offense and defense: early-down EPA/play, success rate, pass vs. rush split.
- Havoc / pressure rate vs. pass-block quality (Collin Wilson's Havoc lens).
- Turnover luck: fumble recovery rate and INT rate vs. expected. Fade teams running hot on these.
- Pace (plays per game, seconds per play), red-zone TD rate (regress hard toward the mean).
- Situational: rest, travel, lookahead/letdown spots, rivalry, motivation flags. Keep these as small manual adjustments, not model features, until there's enough data to fit them.
- QB adjustment table, Walters-style: starting QB worth up to ~7 pts in the rating, top non-QB starters 1-3 pts. Maintained by hand from injury reports.

Model:
1. Baseline: Elo-style power ratings with home field and QB adjustments. Output a fair spread and total.
2. Then: ridge regression of game margin and total on the adjusted efficiency features, walk-forward by week.
3. Translate to probabilities with an empirical margin distribution (not normal: key numbers matter in football). Build a lookup of historical cover rates by line.

Exit test: walk-forward over 3+ seasons. Beat the closing spread on mean absolute error, or at least match it while generating positive CLV in paper bets taken at the opener.

## Phase 3: NBA model

Data: `nba_api` (PBP, lineups, tracking), Cleaning the Glass-style filtering (drop garbage time yourself from PBP), the official injury report.

Features:
- Garbage-time-filtered offensive/defensive rating, pace, 3PA rate (regress 3P% hard, don't regress 3PA rate much).
- Record vs. point differential gap (the regression-to-mean signal).
- Rest: back-to-backs, 3-in-4, travel, altitude (Denver, Utah).
- Lineup-level on/off for the actual starting five, recomputed the moment injury news lands.

Speed matters more here than in football. The edge is reacting to confirmed lineup news before the market adjusts.

Exit test: same as Phase 2, plus alert latency under 60 seconds from injury-report change to recalculated line.

## Phase 4: Player props (highest edge, build last)

- Derive props from the game sim, bottom-up: team volume (plays, pass attempts, possessions) given game script, then player share (snaps, routes, targets, usage, minutes), then efficiency.
- Distributions: Poisson / negative binomial for counts (TDs, 3PM, receptions, rebounds); gamma or log-normal for yardage and points. Compare our median to the book's line, since books set yardage props near the median, which sits below the mean.
- Correlations: game script drives pass/rush mix; same-game outcomes are not independent.

## Phase 5: Sizing

- Edge = model probability minus no-vig market probability.
- Stake = quarter Kelly, capped at 3% of bankroll and 3 units, floored at 0.5 unit.
- No bet if the edge disappears at the current price. Every output shows the price where edge goes to zero (the "don't bet past" number).

## Rule layer (handicapper principles to encode as checks, not features)

- Bet the number, not the team. No edge at the current price, no bet.
- Favorites early, dogs late (Walters).
- Buy low / sell high on teams the market overreacts to (Wilson).
- Ask why a line moved, not just whether it moved. Agreement with the move: bet early. Disagreement: wait.
- Don't double-count. If a factor is already in the rating (e.g., pace), don't add it again as a manual adjustment.
- Check that data matches real conditions (stadium wind vs. airport wind, roof open/closed).
- Track CLV, but also track results on bets that went against the market.

## Explicitly out of scope for v1

- Auto-placing bets (manual only).
- Soccer.
- Live/in-game betting.
