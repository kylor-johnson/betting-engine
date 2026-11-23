# Handoff: deep review of the whole engine, and how to make it elite

Written Monday Nov 23, 2026, afternoon Mountain. Paste the prompt at the bottom into a fresh Claude Code session opened in this folder.

## Why this exists

Kylor wants to make real money with this. After a long build session, the honest state is: the machinery is solid and honest, but **no model has shown an edge over the market**, the bet alerts are rare, and Kylor is (rightly) asking whether the engine is useful or just a careful price checker. He wants a fresh, independent, deep review: what the best bettors and public research actually do, what the historical data we hold can prove or disprove, what is missing, and whether NFL, college football and NBA should be separate models because work keeps going into one sport while the others lag.

**Be an outside reviewer, not a defender of this code.** If the best answer is "change the premise", say so and show the evidence.

## Read first, in this order

1. `CHARTER.md` (purpose, five lanes, drift guard, locked decisions). It wins over everything else.
2. `docs/lanes/STATUS.md` and `docs/lanes/READINESS.md` (generated: what each lane can and cannot do today, and when money may go on a pick). Run `uv run engine status` and `uv run engine ready` to regenerate.
3. `docs/research/10-plan.md`, then `11-audit.md` (the engine checked against a 59-item red-team checklist), `11a-calibration.md`, `12-wagerhouse-vs-pinnacle.md` and `12a-reading-2026-11-23.md`, `13-nba-absences.md`.
4. The failed-model write-ups, so you do not repeat them: `04-evaluation.md` (sides from market ratings and public systems), `03-sharp-style-handicapping.md` (play-by-play ratings), `02-totals-model.md`, `05-model-first-picks.md` (first-half habits; wind totals passed), `09-early-number-openers.md`, `06-props-model.md`, `08-nba-props-model.md`, `07-injury-news-sources.md`, `00-red-team.md`, `01-bet-audit.md` (Kylor's own past bets, graded as leaks), `01-picks-engine.md`.
5. `docs/decisions/` (0001 to 0013) and the three older handoffs in `docs/handoffs/`.
6. `config.yaml` (every switch and threshold), `ops/agent_prompt.md` (what the research agent is told), `CLAUDE.md`.
7. Code, as needed: `src/engine/picks/` (slate, card, pricing, grade, leans, agent), `src/engine/models/` (wind, props, calibration, nba_absences), `src/engine/stale.py`, `burst.py`, `readiness.py`, `version.py`, `lanes.py`.
8. Run `git status`, `git log --oneline | head -40`, `uv run pytest -q` (199 tests pass at handoff). Everything through f8c1d2a is pushed to `github.com/kylor-johnson/betting-engine`.

Kylor also wrote a separate red-team document with another agent (sources in tiers, and the checklist now summarised in `11-audit.md`). Sections 1 to 9 were not saved in the repo. Do not ask him to paste it back; work without it and say in your summary that you did.

## What is true today (each line traces to a file)

**Fair line.** For sides and totals it is Pinnacle's no-vig line plus the unpriced part of sourced news (`config.yaml` `picks.use_model_leg: false`; `src/engine/picks/slate.py` `unpriced_part`). An own ratings blend was tested and lost (`04-evaluation.md`).

**Models tested against the closing line, and what happened**

| Model | Result | File |
|---|---|---|
| Sides from market ratings and public systems | Failed (2,663 games) | `04-evaluation.md` |
| Sides from play-by-play ratings | Failed (918 games) | `03-sharp-style-handicapping.md` |
| Totals from pace and efficiency | Failed (918 games) | `02-totals-model.md` |
| First-half scoring habits | Failed (2,111 games) | `05-model-first-picks.md` |
| Early-week openers from ratings | Failed (about 3,600 games) | `09-early-number-openers.md` |
| Wind on NFL totals | Passed on held-out seasons, weaker since 2024 (Unders 214-147 on 2019 to 2026, 48-46 since 2024), tested on realized wind not the forecast | `05-model-first-picks.md` |
| NBA absences vs the closing spread | No effect at the close (slope +0.10 points per 10 minutes missing, t = 2.0; stars -0.02) | `13-nba-absences.md` |
| Landing tables (points to probability) | Calibrated, NFL 2019 to 2025 and NBA | `11a-calibration.md` |
| Wagerhouse small markets (halves, quarters, team totals) | Not soft: juice 6.3 to 7.0% against Pinnacle's 3.4 to 4.3%, gaps 0.2 to 0.35 points | `12-wagerhouse-vs-pinnacle.md` |

**Props.** NFL and NBA player-prop models exist and are scored against Pinnacle's props only (150 NFL and 209 NBA graded of 300; no Wagerhouse prop lines, by Kylor's choice, `docs/decisions/0011`). On graded props the model is no better than Pinnacle (NFL log loss 0.2579 against 0.2524; NBA about level, with a heavy lean toward Unders). Every 5%+ disagreement is frozen as a paper suggestion and graded.

**Where an edge could still be.** News timing at Wagerhouse: after Pinnacle moves, Wagerhouse took 1 to 6 hours to follow on some NFL moves (15 moves seen, hourly resolution). Fast reads every 10 minutes in news windows (NFL: practice-report afternoons, Sunday inactives; NBA: around the 10am, 3pm, 5pm injury checks) now log this; `uv run engine wh-edge` regenerates the table. STALE NUMBER price alerts (`docs/decisions/0013`) send a Telegram alert when Wagerhouse is better than Pinnacle's fair price by 2% and grade it.

**Output.** Telegram pings only for a Bet, a Conditional, a cancellation, a STALE NUMBER price alert, or a broken engine (`telegram.send_kinds`). Paper Leans (agent opinions, 3 per sport per week), paper prop suggestions and everything else stay on cards and `board.html`. Record: one graded pick (a Conditional, 0-1, no closing line stored). Betting stages are in `docs/decisions/0012` (Stage 0 now).

## Locked decisions (do not reopen without a written case Kylor can answer yes or no to)

Wagerhouse only; no paid data; the engine never places bets; pregame NFL, college football and NBA only; unit $25; code owns every number and the agent cannot type a line, price or stake; every pick has a "don't bet past" number; betting splits and reverse line movement are never a reason; a price gap alone is never a reason for a **pick** (a labelled price alert is allowed); tests never look ahead and tuned things are checked on seasons they never saw.

## What data we actually hold, and what we do not

**Have (local, `data.nosync/raw/`):** nflverse games 1999 to 2026 with closing spread, total and result; nflverse play-by-play (from 2015); nflverse weekly injury reports (practice and game status, 2018 to 2026); nflverse player stats; CollegeFootballData lines and scores (2021 to 2026); ESPN NBA box scores with closing lines (seasons labelled 2024 to 2027, about 4,200 games); Open-Meteo weather; Kylor's graded Wagerhouse bets (Sep to Nov 2026, `wagers`, `legs`); The Prediction Tracker's current weekly file; our own logs since Nov 21 (`line_snapshots`: Wagerhouse, Pinnacle, DraftKings; `derivative_snapshots`: halves, quarters, team totals, Pinnacle props; `prop_evals`, `prop_paper_picks`, `wind_forecasts`, `stale_alerts`, `leans`, `burst_reads`, injury and news tables).
**Do not have, and no free source is known:** historical opening lines; historical prop lines; any Wagerhouse line history before Nov 21; news timestamps; Pinnacle history before Nov 21. Wagerhouse's Bet Builder (the real prop prices) is a third-party iframe signed in with the account login; it was deliberately not automated.

## What I want from you

Deliver one document, `docs/research/14-deep-review.md`, that starts with a half-page answer to **"where could real money come from here, and how sure are you?"** in plain English, then:

1. **The best bettors and methods, with sources.** Cover at least: Billy Walters (power ratings, injury point values, key numbers, line timing, information network), Warren Sharp and similar published analysts (one example, never a dependency), Haralabos Voulgaris and NBA approaches, Bill Benter (probability model blended with the market), Pinnacle-based closing-line-value betting and line shopping, steam and speed approaches, market-making and soft-book exploitation, and the academic work on market efficiency in NFL, college and NBA betting. Mark each claim as *shown by the source with data*, *asserted without data*, or *folklore*. A claim about the world needs a link you opened; mark anything you could not open. Discard tout and affiliate marketing.
2. **Which of those methods our data can test now, and run them** (walk-forward, held-out seasons, against the closing line; no look-ahead). Specific candidates, in order of expected value: (a) a replay of every NFL week 2018 to 2026 using the nflverse injury reports for who was out against the closing spread and total (practice participation is an input we do not use); (b) college football with preseason priors, returning production and transfers, and the weekly Prediction Tracker systems, against the close (CollegeFootballData 2021 to 2026); (c) NBA with rest, travel, schedule density and minutes-weighted rosters against the close; (d) totals, including weather on the forecast, not realized wind; (e) anything else you find that the data supports. Say what each can and cannot prove. Be especially clear where a test would need data we do not have.
3. **Is the premise right?** Pinnacle is the reference and we bet a soft book. Say whether "find where Wagerhouse is slow or loose against Pinnacle" is the right edge, whether a model that beats Pinnacle with free data is realistic, and what a more promising framing would be (line shopping and speed, specific game types, specific times in the week, price-lean exploitation, alternate lines, teasers and buying points where the math is known, anything else). Give a probability-weighted view, not reassurance.
4. **Split or not?** Kylor's worry: work keeps going into one sport and the others lag. Today the lanes are separate in `config.yaml` and the status table, props models are separate files, and the shared parts are `slate.build`, `pricing.py` (landing tables), `grade.py`, `leans.py`, `stale.py` and the agent prompt. Recommend with evidence whether NFL, college football and NBA (and props) should become separate models, separate code paths, separate agents, separate schedules and separate tuning versions, and what each sport's real edge hypothesis is. Include how to stop one sport starving the others (a per-sport weekly checklist, per-sport evidence thresholds, per-sport owners of the work).
5. **What to build, stop, and change**, ranked by expected money per hour of work, each with the test that would prove it and the number that would kill it. Include anything in the current engine you think is wrong, over-built or misleading, and edits to the research agent's prompt and the Bet criteria. Include sizing and bankroll (Kelly or fractional Kelly on uncalibrated probabilities, correlation, the half-unit stage) and whether the go/no-go rules in `docs/decisions/0012` are right.
6. **Per lane, after your plan**: what it will evaluate, what it still will not, and what would make it say "make this bet".
7. **A 4-week schedule** against the NFL season that is left (about 6 regular-season weeks and the playoffs), the college bowl season and the NBA season, with what is measured each week.

## Rules

- Plain English. Kylor is technical but not a quant. Lead the document with what he gets.
- A claim about the engine needs the file it came from. A claim about the world needs a link you opened.
- No look-ahead in any test, and hold out seasons for anything tuned. Report how many variants you tried.
- Do not print or store logins; they are in `.env`.
- You are the only session that should edit `src/`, `config.yaml` or `adjustments.yaml`. Run `git status` first; if there is uncommitted work you did not write, stop and tell Kylor. The scheduled jobs auto-commit cards, decisions, adjustments and generated status files by path; that is expected.
- Stop for Kylor's approval before changing code or settings. Exception: if the engine is sending him false information, say so at the top with the one-line fix.
- Commit your documents before handing off. Do not push unless Kylor asks.
- A research agent may be spawned for reading sources; code and numbers stay with you.
- Keep the first chat summary short and lead with what he gets.

---

## Prompt to paste into the fresh session

```
Read CHARTER.md first, then docs/handoffs/2026-11-23-deep-review.md, and do what the handoff says.
Run git status and git log before anything else and tell me if there is uncommitted work you did not write.
This is a deep research review: read every file it lists, open and cite real sources on how the best bettors
and public research build models, run the tests our historical data can support (walk-forward, no look-ahead),
and write one document to docs/research/14-deep-review.md that starts with a half-page, plain-English answer to
"where could real money come from here, and how sure are you?". Tell me whether NFL, college football and NBA
should be separate models, and give me a ranked list of what to build, stop and change, with the test and the kill
number for each. Stop for my approval before changing code or settings.
```
