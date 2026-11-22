# Evaluation of the picks engine, research, and a tuning plan

Written 2026-11-22 (Mountain). Nothing in the code was changed. Scratch scripts for every test below are in the session scratchpad and will be moved into `tests/` or `scripts/` only if you approve the plan.

## Verdict

**Read this first: the engine is well built and honest, but today it cannot find bets. The flagged sides it produces are mostly an artifact of its own design, and the real edge candidates (period lines, team totals, props, wind) are the parts it does not yet cover.**

The plumbing is sound: tests pass, sources fail loudly, the agent cannot type a number into a card, and the agent's passes were sensible. The weak part is the "model" half of the fair line. It is the market's own old closing lines (plus public rating systems that are themselves near the market), so whenever the market moves for real news, the engine sees an "edge" on the pre-news side. All five NFL sides flagged this morning were exactly that, and the agent correctly passed all five. A test of that model against closing lines over 2,663 games found it adds nothing, and the 55/45 blend is worse than using the market alone. Wagerhouse's full-game lines sit within about 0.3 points of Pinnacle in the little data we have, so there is almost no price edge to find there either. Meanwhile Wagerhouse posts first-half, first-quarter and team-total lines that the engine does not read, and Pinnacle posts free reference lines for the same markets and for player props. That is where to look next, and the first step is to log them for a few weeks so the question "is Wagerhouse loose there" can be answered with data. Wind is the one input with a measurable edge in history.

## What is sound

- **Tests and failure behavior.** 86 tests pass. Sources raise `SourceError` instead of dropping a factor (`src/engine/odds/espn.py`, `picks/sources.py`). The Wagerhouse client refuses any operation outside a read-only list (`odds/wagerhouse.py`, `READ_ONLY`).
- **Walk-forward tests were the right kind.** `totals-test` and `spread-test` use only earlier weeks and compare against the close with a break-even of 52.4%. I reran both and got the documented numbers (totals: market 10.14 vs model 10.65; sides: 9.43 vs 10.03; best blend 100% market).
- **The landing tables are a good idea.** `picks/pricing.py` prices half points from how real games landed near that line, so 3 and 7 count for what they are worth. Reasonable for football.
- **The card renderer refuses a Bet the numbers do not support** (`picks/card.py`).
- **The agent's judgment on Nov 22 was good.** It saw that Detroit, New Orleans and others were flagged only because the ratings were behind the news, and said so (`docs/cards/2026-11-22-nfl.md`).
- **The bet audit reconciles** to the account to the cent, and the "8 bets placed after kickoff" are explained below (not a data defect).
- **Quarterback point values are about right.** See the test below.

## What is weak

1. **The model side is a lagged copy of the market** (`picks/ratings.py`, `picks/history.py`, `picks/slate.py` lines ~182-199). Fair = 55% Pinnacle + 45% model, where model = average of (ratings backed out of closing lines) and (about 50 public systems). Any real move in the line this week shows up as "edge" on the old side at 45% of the move size. Hand-entered adjustments only fix it if they exactly equal the move. Evidence: test A below, and today's card (Saints +11 flagged because "market ratings" said -4.9 against a line of -11.5).
2. **"Code owns every number" is only partly true.** `adjustments.yaml` points are typed by the agent and move the fair line. The spec says an edge that exists only because of the agent's own adjustment is not a Bet, but nothing in code checks this (I searched `slate.py` and `card.py`; there is no with-and-without computation). The Baltimore pass on Nov 22 shows the agent noticing this by hand.
3. **The agent has more reach than the prompt says.** `picks/agent.py` allows `Write` and `Edit` with `acceptEdits`, so it can edit any file in the project, not just the decisions and adjustments files. The prompt forbids it; the permissions do not.
4. **No grading data for the thing that matters.** `engine_picks` holds one row (an NBA Conditional) and logs only non-Pass picks, overwriting the row on each update. Flagged-but-passed sides are never recorded, so you cannot tell whether the agent's judgment adds anything over the raw numbers. `engine_pick_events` has one row.
5. **The line log is one day old.** `polls` has 8 rows (Nov 21 22:35 to Nov 22 17:02 UTC), `line_snapshots` 487 rows, Pinnacle in only 73 of them. The Phase 1B question "does Wagerhouse lag the market" cannot be answered yet; the three-week exit test has not run.
6. **The NBA model is market ratings alone.** Same flaw as item 1 with no second opinion. The one engine pick so far (OKC +3.5, Conditional) comes from it.
7. **Wind values in the agent prompt are too big.** See test D.
8. **DraftKings "open" is often a lookahead number** (card shows Baltimore +4.5 open to -3 now). Already known; it should not appear in a decision.

## What is wrong

- **The 55% Pinnacle / 45% model blend and the 2% minimum edge are not supported.** Test A: no weight below 100% market improves prediction, and the held-out seasons (2023-2026) agree. A threshold sweep found no setting where engine-style flags beat the 52.4% break-even on held-out seasons.
- **"Flagged side" is therefore not an edge signal.** Treating it as one wastes the agent's runs and, if the agent ever gets less careful, loses money.

Not wrong, but unexplained in the handoff: the eight "bets placed after kickoff". I checked them in `data.nosync/engine.duckdb`. Five show the book's own game time later than the time you placed them (so the book took them as pregame); three are 1 to 3 minutes after the scheduled start. The audit compares against ESPN's scheduled start, not the book's cutoff (`bets/audit.py:72`). Not a leak worth chasing; one has a wrong game time stored (SMU/Florida State, off by 75 minutes), which is a small parsing issue.

## Tests I ran

All use free data already in `data.nosync/`. All are walk-forward (each game sees only earlier information). Scripts are in the scratchpad.

### A. The model side against the closing spread (never tested before)

Engine's own ratings (`ratings.solve`, decay 0.9, same-season only, weeks 3+), 2,663 NFL games, 2015-2026, nflverse closing spreads.

| Weight on the market | Mean squared error |
|---|---|
| 0% (model only) | 173.0 |
| 50% | 164.3 |
| 55% (current) | 163.7 |
| 75% | 162.1 |
| 100% | 161.4 |

- Best weight on the market: 100% overall; 0.85 on 2015-2022 and 1.00 on 2023-2026.
- With the previous season added at 35% weight: same answer (1.00 overall).
- Engine-style flags, assuming Wagerhouse equals the close (true to within about 0.3 points in our small sample): betting where 0.45 x gap was at least 1.0, 1.5, 2.0 points won 51.7%, 51.7%, 51.1% (break-even 52.4%). With the prior-season variant 51.0%, 52.8%, 52.9%. Held-out 2023-2026, model-vs-close gap of 2 or more: 189-218 (46%); 3 or more: 121-141. None beats break-even out of sample.

Plain English: a rating built from last week's market adds noise on top of this week's market. The fix is not a better blend weight; it is not using it as a source of edge.

### B. How far the market moves for a quarterback change (injury point values)

Residual of the closing line against the same slow ratings, from the team whose quarterback situation changed, 2015-2026:

| Situation | Games | Market vs ratings |
|---|---|---|
| Same starter as last week | 3,934 | +0.42 (baseline bias) |
| Backup in, starter played last game | 341 | -2.86, so about -3.3 beyond baseline |
| Backup again (second game or later without starter) | 469 | -1.01, about -1.4 beyond baseline |
| Starter returns | 135 | +0.08 |

The agent's entries (-4.5 third QB, -2 two games without Hurts, -3 Jackson, -1.5 Cousins for Murray, -2.5 Willis, -5 Maye) are in a plausible range. The averages blend all quality levels, so these cannot grade a single entry; they show no sign of systematic over-subtraction. For non-quarterback injuries (star players, line clusters) I have no test; nflverse injuries could support one (see plan).

### C. Wagerhouse against Pinnacle, full game (stored data)

78 matched rows over 6 snapshots (about one day). NFL: mean spread gap 0.31 points, 46% exactly equal, max 1.0; totals 0.18. College: gap 0.15. That is 12 NFL and 13 college games, heavily repeated, so it is anecdote, not a measurement.

### D. Wind and totals (historical)

3,007 outdoor NFL games with measured wind, 2010-2026, nflverse closing totals. Observed wind, not forecast, so it overstates what a forecast can deliver.

| Wind | Games | Actual total minus close | Under rate |
|---|---|---|---|
| 0-9 mph | 1,957 | +0.93 | 48.1% |
| 10-14 | 691 | -0.91 | 56.1% |
| 15-19 | 274 | -1.56 | 55.6% |
| 20+ | 85 | +0.01 | 52.4% |

Later half (2019-2026): 10-14 mph 59.9% under (294 games), 15-19 57.3% (112). The agent prompt uses -2 (10-15), -3 (16-25), -7 (above 25) against the close. The data supports about -1 to -1.5 against the close at 10-19 mph and nothing demonstrated above 20 (85 games, no effect). So the direction is right and the size is too large. Caveat: multiple bands were examined and forecasts are noisier than measured wind. This is the only input I found that the market appears to under-price, and it matches the first research doc.

### E. First half and first quarter against the full-game line (historical)

1,238 games 2022-2026 from play-by-play quarter scores and nflverse closing lines:
- 1H margin = 0.48 + 0.62 x closing spread. 1Q margin = about 0.25 x closing spread.
- 1H total averages 51.2% of the full total (1H total = 1.89 + 0.47 x total); 1Q total 19.7% (1.56 + 0.16 x total).
- By spread size, the 1H share jumps around (47%, 74%, 59%, 67% for spreads of 0-3.5, 3.5-7, 7-10.5, 10.5+), which is noise plus key-number effects.

### F. First reads of Wagerhouse period and team-total lines (new)

I made about 15 read-only calls to `Lines/Get_LeagueLines2` with other `period` values. `"1st Half"` and `"1st Quarter"` work. Team totals come with the main game line (fields `Team1TotalPoints`, `Team2TotalPoints` and their prices) and the engine already receives them but ignores them. The response lists `PropCount: 0` for every game on a Sunday morning, so prop lines are either not posted yet or live under a call I did not find; I stopped probing rather than guess at the account.

Pinnacle's free feed (`guest.api.arcadia.pinnacle.com/0.1/leagues/889/markets/straight`) carries period 0 (game), 1 (1H) and 3 (1Q) spread, total and moneyline, team totals for each period, and player props as `special` markets in units like Receiving Yards, Receptions, Rushing Yards, Touchdowns, Pass Attempts. The engine filters to period 0 only (`picks/sources.py`).

One snapshot, five games (Nov 22, ~11am MT), Wagerhouse against Pinnacle:
- Wagerhouse 1H spreads are 50-71% of the full-game spread (3 to 1.5, 6 to 3.5, 11 to 6.5, 3.5 to 2.5, 6 to 3.5), average about 58%, close to the 62% historical. Four of five match Pinnacle's 1H line exactly. The outlier: Raiders at Broncos, Wagerhouse 1H Denver -6.5 against Pinnacle -4.5 (Raiders +6.5 at +100 against +4.5 at +117). Whether that is Wagerhouse formula-pricing or Pinnacle's thin 1H market is unknown from one point.
- Wagerhouse 1Q totals and 1H totals are within 0 to 0.5 of Pinnacle's in four of five games.
- Team totals: Denver 26 at Wagerhouse against 24.5 at Pinnacle; most others within 0.5.

Conclusion: no proof either way. The fair statement is that period lines at Wagerhouse look close to the market in this sample and may have occasional 1 to 2 point gaps. The only way to know is to log them for weeks.

## Research findings

I split web research across three delegated agents. A tool outage and thin search results limited them, so many names you listed could not be checked on a primary page. Each claim is tagged: **[READ]** opened the page, **[SNIPPET]** search snippet only, **[MEMORY]** not verified.

Tags are as reported by the research agents; I did not reopen their pages. Search quality was poor (mostly affiliate and SEO pages). Where nothing primary was found, it says so.

### Q1. Where a one-person bettor at a soft book has an edge (props, quarters, halves, team totals)

- [READ] Offshore books historically posted player props only on Sunday, US books a first batch on Tuesday. Offshore prop limits were "only a few hundred dollars"; prop juice about -120 against -110 on spreads. A prop bettor said his plays were once 99.9% unders and are now more evenly split. ESPN, undated (about 2022): https://www.espn.com/chalk/story/_/id/34371732/the-future-nfl-betting-why-player-props-not-point-spreads-expected-king
- [READ] On 12,624 paired over/under props, Pinnacle's closing lines were the best calibrated of four books, by tiny margins and with uncertain significance; closing lines only. https://shaanchanchani.github.io/articles/sportsbook-props
- [READ] Winner limiting at US books is real; no timeframe given. https://www.covers.com/industry/true-state-of-sports-betting-part-iv-whither-the-winners-limiting-regulation-february-2025
- [SNIPPET] Whether a pay-per-head agent limits a winner at $25 stakes is not documented anywhere found. It is a bookie-by-bookie call.
- **No source describes a method for props with no reference price.** The method everyone describes is comparing a soft book to a sharp or consensus price, which you already have free through Pinnacle's guest feed. [MEMORY] The usual rule is to bet when the gap exceeds the extra juice; unverified.
- **No verified formula for how pay-per-head books price halves, quarters or team totals.** One low-quality blog claims a fixed 55-60% of the full-game line (https://www.deucescracked.com/blog/nfl-first-half-halftime-betting-strategy); its own example is 54%. My test E (1H margin about 62% of spread, 1H total about 51% of total) and test F (Wagerhouse averaging 58%) are better evidence than anything the agents found.

### Q2. How elite handicappers build a number, and who publishes method

- **Props (best published source is Unabated).** [READ] Books price props at the median while projections are means. Stats are skewed with a floor of 0, so mean exceeds median, and bettors who treat the mean as the answer bet too many overs. The fix is to simulate (about 10,000 runs) and read the median. https://unabated.com/post/the-biggest-mistake-youre-making-when-betting-nfl-player-props . [READ] Its simulator takes your projection, treats receptions as Poisson, and outputs median and fair prices; it does not name the yardage distribution. https://unabated.com/post/learn-about-the-props-simulator . It is a paid product.
- [READ] A nearest-neighbor method (find similar historical players, sample their outcomes, read the over probability off the distribution) with no backtest against real lines. https://advancedsportsanalytics.substack.com/p/getting-ready-for-nfl-props-and-sports
- [READ] 4for4 lists usage inputs (targets, target share, aDOT, snap share, air yards), game script and betting early; no distribution or line source named. https://www.4for4.com/2022/preseason/9-strategies-beat-nfl-player-prop-market
- [READ] An open-source nflverse model (haunter) with a walk-forward backtest, 2021-2025, 1,344 games: spread error 10.44 against 9.78 for the close, and it says plainly it does not beat the close. A good template for an honest backtest. https://codeberg.org/mck10/haunter-model
- **Sides and totals:** no published step-by-step build found beyond "power ratings, then compare to the close."
- **First half:** [READ] PFF says 1H spreads are almost always more than 50% of the full-game spread (no formula; charts did not load). https://www.pff.com/news/bet-optimizing-spread-bets-with-first-half-lines
- **Not found:** method from Bydlon, Giffen, Millman, Prop Money, Pikkit or Sharp App; any open NFL receiving-yards backtest against real lines; any academic paper on prop pricing.

### Q3. Player-prop modeling with free data

- **The recipe** from the sources: game flow, then usage, then a distribution, then compare the median to the line. [MEMORY] nflverse provides target share, air yards, WOPR, snap counts, team pass rate over expected, opponent by position, rosters and injuries. True route data is not free; the proxy is snap share times pass plays. Exact fields unverified.
- **Distribution family is unsettled.** Unabated names Poisson for receptions. [MEMORY] negative binomial is a natural hypothesis for counts; test by calibration.
- **Under bias.** [READ] A PFF midseason review says blind passing-yard unders were the only profitable passing category (+14.06 units) and running-back receiving-yard unders +108.09 units "in our dataset" with no sample sizes or vig handling; treat it as marketing. [SNIPPET] Other pieces say about 54-55% unders on receiving props in 2017-2019 and that the season-long edge has faded.
- **Historical prop lines: no free source was found.** The Odds API has them from May 2023 on paid plans only (https://the-odds-api.com/historical-odds-data/). OddsPapi says its historical endpoint is free but capped at three books and unproven for 2023-2025 NFL props (https://oddspapi.io/blog/?p=3871). SportsDataIO is sales-gated. Sports Odds History has season-long props only. nflverse schedules carry only game-level lines. Several Kaggle, Hugging Face and Reddit searches found nothing. [READ] r/algobetting posters say to collect your own from now on.
- **Consequence:** a real prop backtest is impossible today. The free Pinnacle feed already returns current props, so logging them daily creates the history. OddsPapi's free endpoint is worth one check.

### Q4. Derivative pricing

- [READ] PFF: full-game total explains R-squared 0.80 of the second-half total, full-game spread 0.55 of the second-half spread (2,671 games since 2010); second-half favorites covered 43.5%. https://www.pff.com/news/betting-nfl-2020-best-approaches-betting-second-half-lines
- [READ] Statz: 3 is "even more dominant" a key number in halves than in full games, then 7; gives no frequencies. https://statz.ai/nfl/betting/first-half-and-quarter-lines
- **Persistence of period splits:** [READ] PFF's 2019 study found first-half scripted-play EPA stable at r = 0.26 (offense) and 0.16 (defense), against 0.57 for overall EPA; first-quarter points were predicted far more by overall EPA than by scripted-play EPA. https://www.pff.com/news/nfl-pff-data-study-can-we-predict-hot-starts . So "slow-starter" splits are mostly noise. This cuts against building a period-split model from the matchup layer's 1Q and 1H columns.
- **Not found anywhere:** 1H or 1Q margin tables or key-number frequencies. I computed the average shares myself (test E); the key-number frequencies are still to be computed from play-by-play.

### Q5. Timing

- US books post a first prop batch Tuesday, offshore Sunday (the ESPN piece above, possibly out of date; I did not check Wagerhouse, and today's `PropCount: 0` suggests props are not posted on game morning).
- [SNIPPET] Other sources say props appear about 48 hours out or game morning, and that late-week prop prices are sharpest. [SNIPPET] 4for4 says the easiest closing-line value on sides is betting as soon as a game posts, often Sunday evening.
- **Not found:** any data on open-to-close movement for props, which market is softest by day, or anything specific to NBA or college.

### Q6. What the two failed tests imply

- Your tests are the right kind, but narrow: same-season weeks only, no quarterback input, no injuries. I added a prior-season carry-over in test A and it did not change the result. Nobody should expect public efficiency inputs to beat a close that already contains them.
- [READ] nfelo's own page reports 55.0% against the closing line and 57.1% against the opening line over 2009-2026, with a mean-error gap to the close of +0.01. The page is self-published, bet selection is not visible, and it includes a quarterback term and a market-regression term. The notable part is the gap between open and close: the best published sign of an edge is early, not at the close. https://www.nfeloapp.com/games/nfl-model-performance
- [SNIPPET] A hobbyist model reports its quarterback-out adjustment was rejected because error rose; another reports no positive-value threshold against the close after vig. Academic literature is mixed and mostly student work; none gave a usable magnitude.
- **Not verified:** Baldwin, Sharpe, DVOA against the market, FPI, Massey, Prediction Tracker records, and whether the NFL close has become more efficient over time.

### Q7. College football and NBA

- [READ] CollegeFootballData: free tier is 1,000 calls a month; lines and PPA are included in every tier; live play-by-play starts at $5 a month. So a no-paid-data rule limits college to lines, scores and basic stats. https://collegefootballdata.com/api-tiers
- [SNIPPET] SP+ preseason uses returning production first; returning-production pieces show correlation with performance, not with the spread. No points values found for neutral site, FCS opponents, rest or weather.
- [READ] nba_api's README says the NBA site blocks many cloud IP ranges and throttles; home connections are not listed as blocked (not tested). https://github.com/swar/nba_api
- [SNIPPET] Back-to-back effects against the spread appear in a 2010 paper with no effect size; practitioners say books already price it. Injury point values from blogs are estimates (about 3 for a star), not measurements. No study of how fast NBA lines move after injury news was found, and none comparing prop softness with sides at soft books.

### What the research does and does not support

- It does **not** support a model that beats full-game closing lines with public data.
- It **does** point at the same places the data does: early numbers, derivative and prop markets, and a sharp reference (Pinnacle) you already read for free.
- It cannot tell us whether Wagerhouse's period, team-total or prop lines are loose. Only your own log can, and it does not exist yet.

## Tuning plan, in priority order

Nothing here is started. Each item has the evidence and a test. Items 1 to 3 are cheap and I recommend doing them together.

1. **Stop using the model side as a source of flags (small code change).** Evidence: tests A and the Nov 22 card. Change: raise `market_weight` to 1.0 for sides and totals in football and the NBA, or equivalently flag only when Wagerhouse differs from Pinnacle after vig removal and the agent's sourced news says why. Keep the model number on the sheet as context. Test: re-run `test_model_side.py` as `engine model-test` for any future model; a model may drive flags only after a held-out blend weight below 1.0.
2. **Log what you need to measure (small).** Add to each hourly read: Wagerhouse 1H, 1Q and team totals (two extra paced calls per sport), and Pinnacle's period lines, team totals and props. Log every flagged side every run, including Passes, with the line at that time. Estimated extra Wagerhouse load: 2 calls per sport per read on top of the existing one; your call whether that is acceptable. Test: after three weeks, report Wagerhouse minus Pinnacle gap by market, by time of week, and how long Wagerhouse takes to follow Pinnacle moves.
3. **Grade engine picks.** Log at issue (line, price, Pinnacle fair, time), and grade on result, Pinnacle close (the stored reads), and against your own bets. Include Passes so we can see whether the agent adds value over the raw numbers. No pick count target changes; the 100-pick gate stays.
4. **Tighten the agent.** Restrict its tools to `Read`, `Write` and `Edit` on two paths if the CLI allows it (or move the adjustments file into a validated entry command). Add a with-and-without check so a Bet that exists only because of an agent adjustment is refused by code. Change the prompt's wind values to about -1 to -1.5 at 10-19 mph, drop -7, and require forecast not observed wind. Test: unit tests for the refusal; a historical Open-Meteo forecast backtest (free historical-forecast API) of forecast wind against totals results since 2022.
5. **Wind as an automatic total input.** If the forecast backtest in item 4 holds, compute it in code from Open-Meteo at kickoff and show it on the sheet rather than relying on the agent. Held-out seasons: tune on 2022-2024, report 2025-2026.
6. **Period and team-total pricing, measured before use.** After item 2 has data, test how Wagerhouse's period lines compare with Pinnacle's and with a pricing from the historical 1H/1Q relationship (test E). Only if Wagerhouse is off Pinnacle at a rate and size that survives the vig, add those markets to the slate. Props follow the same sequence: find where Wagerhouse posts them (I need one more read or a screenshot of the prop screen), log them against Pinnacle's props for a few weeks, then decide.
7. **Injury point values.** Use nflverse injury and snap data to measure market movement for non-quarterback absences, as test B did for quarterbacks. Current values stay until a test supports a change.
8. **Do not extend the matchup layer to college or NBA yet.** Reasons: nothing in the NFL evidence says matchup numbers beat the close, and college and NBA have no tested edge here either. Revisit only if items 2 and 6 show a loose Wagerhouse market in those sports.

## Open questions for you

1. **Extra Wagerhouse reads.** Is it okay to add 1H, 1Q and team-total reads (two extra calls per sport per hourly read)? That is the main data need.
2. **Props.** I could not find where Wagerhouse posts them. A screenshot of the NFL prop screen on a Thursday or Friday, or the browser's network calls on that screen, would let me read them the same read-only way.
3. **Model side.** Are you fine with setting the model weight to zero for flags (item 1) and treating the agent as the only second opinion until a model passes a held-out test?
4. **Agent permissions.** Okay to limit what the research run can edit, which may need a small script rather than a CLI flag?
5. **Sharp login.** I did not need it for this evaluation. If you want method read from more members' write-ups later, paste it then; I have not stored it.
