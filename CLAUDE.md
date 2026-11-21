# Betting Engine: Build Spec (revised after Phase 0, approved 2026-11-21)

Owner: Kylor (Denver, Mountain time). This file is copied to `CLAUDE.md`. The research behind it is in `docs/research/00-red-team.md`; decisions are in `docs/decisions/`. `HANDOFF.md` has the working rules and folder layout. Build one phase at a time. Do not start a phase until the one before it passes its exit test and Kylor says go.

## What this is, and what it is not

- It compares the price at Kylor's book (Wagerhouse) with the market price and says when his is better, when a line is moving, and whether his past bets were good prices.
- It does not copy how he has been betting. Big favorites, 13-point teasers, moneyline parlays, same-game stacks and live bets are graded as leaks in the research and the engine never recommends them.
- Scope: pregame NFL, college football and NBA. No live betting, baseball, hockey or soccer.
- It does not place bets. Kylor places every bet by hand (see `docs/decisions/0002`).

## Ground rules

- Python 3.11+, `uv` for the environment (`UV_PROJECT_ENVIRONMENT=.venv.nosync`), DuckDB as the local database (`data.nosync/engine.duckdb`).
- No paid data. Sources: Wagerhouse's own lines and history read from Kylor's account, ESPN's public scoreboard and odds pages (DraftKings open, close and current lines), and The Odds API free tier (500 credits a month) for occasional Pinnacle checks.
- The market reference is DraftKings as published by ESPN. It follows the market; it is not a sharp book. Every report says so, and "fair price" is labelled approximate.
- Every number the system outputs is logged with a timestamp and the odds at that moment. Times are stored in UTC and shown in Mountain time. Wagerhouse timestamps arrive in Eastern time.
- Unit = $25. Flat one unit per bet, two at most. No Kelly sizing until there are 500 bets with measured price quality. Unit, cap and bankroll live in `config.yaml`.
- No pick without a "don't bet past" number.
- Secrets live in `.env`, never committed, never printed or logged. That includes the Wagerhouse login.
- Wagerhouse account access is read-only: sign in, read lines, read history. A handful of reads a day in the hours lines open, never a constant poll.
- If a source is down or returns junk, fail loudly and alert. Never skip silently.
- Every report prints the luck range next to results so a hot streak cannot pass for an edge.
- Closing line value is measured on sides, totals and moneylines only, never props, and is treated as a compass, not proof.

## Phase 1A: Audit the bets already made

1. Import the graded history pulled from the account into the database: one row per wager, one per leg, with time placed, game time, risk, to-win, result, line, price, bought points and teaser points.
2. Split wagers by how they were placed: before the game, live in-game, same-game builder.
3. For every pregame side, total and moneyline leg on NFL, college football and NBA, find the game on ESPN and record DraftKings' opening and closing line and price.
4. Report, by bet type and by price band: results, how often the bet beat the closing line, by how many points, approximate value against the vig-free close, and what bought points and teasers cost.

Exit test: every wager is either priced or listed as unpriced with the reason; totals reconcile to the account's weekly figures.

## Phase 1B: Line logger, alerts, bet log

1. **Line logger.** On a schedule, read Wagerhouse's posted lines for NFL, college football and NBA, and ESPN's DraftKings lines for the same games. Store every snapshot. Derive first-seen (open) and last-before-kickoff (close) per game, market and source.
2. **Your-book measurement.** For every game: when Wagerhouse first posted it, how far it sits from DraftKings, and how long it takes to follow a DraftKings move.
3. **Alerts by Telegram:**
   - Opener digest when Wagerhouse posts a new slate.
   - Off-market: Wagerhouse differs from DraftKings by a point or more, or sits on the good side of 3 or 7 (NFL and college; also 6, 10, 14).
   - Moving now: the market moved a point or more, or through a key number, and Wagerhouse has not followed.
   - Watchlist: Kylor enters "Kansas State +10 or better"; alert when Wagerhouse is there, and when the market is leaving.
4. **Bet log.** New bets come from the account history automatically; `engine bet add "Kansas State +10 -110 25"` exists for notes and for bets that need a reason attached.
5. **Calculators** on every logged bet: is this teaser a 2-team 6.5-point NFL teaser with both legs crossing 3 and 7; was a bought half point worth its price; does a stake exceed the cap.
6. **Weekly report**: results, closing line value by sport and bet type, favorites of −300 and shorter separately, leaks (anything the research grades negative), luck ranges.
7. **Operations.** launchd job on the Mac, gap detection, a heartbeat alert when a scheduled read is missed.
8. **Tests** for the vig removal, key-number logic, bet parser, closing line value and teaser math.

Exit test: three weeks of scheduled reads with every gap explained, closing line value on every eligible bet, and a short written answer to "does Wagerhouse lag the market, by how much, and in which direction does it shade."

## Phase 2: Decide where the edge is

Read the Phase 1 measurements. If Wagerhouse lags, tune the alerts to that lag. If it does not, say so plainly; the remaining price edge would need a second book.

## Phase 3: NBA, narrow version

Injury-report change alerts for players who move a line, aimed at catching Wagerhouse not reposting. A props check that compares Wagerhouse's number with other books. No sub-minute requirement.

## Phase 4: Football ratings (offseason 2027)

NFL first, then college football with preseason priors. The model is blended with the market from day one, tested only on seasons it never saw, and passes only if it adds predictive value on top of the market line. Its job is to rank which openers to look at first. Use `nflreadpy` (not `nfl_data_py`, archived 2025) and CollegeFootballData.

## Phase 5: Own props model

Only if Phase 3 shows props at Wagerhouse are worth it.

## Rules the engine enforces as checks

- Bet the number, not the team. No value at the current price, no bet.
- Ask why a line moved, not only whether it moved.
- No reverse-line-movement or bets-versus-money signals; the evidence is against them.
- "Favorites early, dogs late" is a question the log answers, not a rule.
- Don't double-count: a factor already in a rating is not added again by hand.
- Teasers: only 2-team 6.5-point at −120, NFL sides, both legs crossing 3 and 7. Everything else is flagged.
- Buying points: only on or off 3 in the NFL at 10 to 15 cents; on or off 7 at 10 cents is neutral; never in the NBA.

## Out of scope

Auto-placing bets, live betting, baseball, hockey, soccer, paid data feeds.
