# Handoff: make the engine suggest bets from its own model

**Read this, then `CLAUDE.md`, then `docs/research/04-evaluation.md`. Do not ask Kylor to re-explain the goal. It is below.**

## The goal, in Kylor's words (2026-11-22)

"The goal of this and to be sharp is to have you provide me with a suggested bet based on the underlying model."

He is not asking for random picks, and he is not asking for a price checker. He wants an engine whose own handicapping model says "bet this, at this number, don't bet past this number," on its own judgment, the way a sharp shop's write-up does. He was angry that after a long session the engine had no suggested bet, only logging and grading.

## Where the last session went wrong (own it, do not repeat)

The last session ran the evaluate-and-tune handoff (`docs/handoffs/2026-11-22-evaluate-and-tune.md`). It found the model leg adds nothing over the market, then:

1. Turned the model leg OFF for flags (`picks.use_model_leg: false` in `config.yaml`, commit eca6ae3). Fair line is now Pinnacle plus the agent's sourced adjustments. That makes the engine a price-gap finder. Kylor said earlier the same day he does NOT want that (memory: betting-engine-project, 2026-11-22). He approved the plan, but he approved it expecting a model-driven pick at the end.
2. Spent the rest on plumbing (logging, grading, board section), none of which produces a suggested bet.
3. Told him "no pick" three times without offering the thing he asked for: a model.

The evaluation is not wrong. The old model really was a lagged copy of the market (test A, 2,663 games: market-only had the lowest error). The answer is a better model, not no model.

## Locked, do not reopen

Wagerhouse only. No paid data. Engine never places bets. Pregame NFL, CFB, NBA only. Unit $25, 1 unit per Bet, 0.5 per Conditional until 100 graded. Code owns every number, the agent owns research and judgment. Splits and reverse line movement are never a reason. Every pick has a "don't bet past" number. A model drives picks only after a walk-forward test on held-out seasons shows it adds value over the market. Fail loudly. No look-ahead. Never print or store the login (it is in `.env`).

That last locked rule is the real constraint: the model must earn its way in by beating the closing line out of sample. The job of the next session is to build models that can pass that test, not to argue the test away.

## What exists (all committed, 96 tests pass; last commit 98c5c08)

- Slate sheet, card, decisions files, board page, Telegram alerts, hourly Wagerhouse reads, scheduled research agent. See `CLAUDE.md`.
- `picks/matchup.py`: play-by-play matchup block per NFL game (EPA, success, splits, last four games). It failed as a sides and totals model against the close (`docs/research/02-totals-model.md`, `03-sharp-style-handicapping.md`).
- `odds/derivatives.py`: every read now logs Wagerhouse first-half, first-quarter and team-total lines, and Pinnacle period lines, team totals and about 500 player props, into table `derivative_snapshots` in `data.nosync/engine.duckdb`.
- `picks/grade.py`, `engine grade`: grades engine picks on result, points against Pinnacle's close, and units, flagged Passes included. Shown on the board, in the weekly Telegram report, and as a message when a Bet or Conditional is graded.
- Agent can only edit its decisions files and `adjustments.yaml`. Wind guidance corrected to about −1 to −1.5 on totals at 10–19 mph.

## Facts the next session needs (each from this session's work)

- Test A (`04-evaluation.md`): model side vs closing spread, 2,663 games 2015–2026, MSE 173.0 at 0% market, 161.4 at 100% market. The old model adds nothing on full-game sides.
- Test B: the market moves about 3.3 points for a fresh starting-QB loss; the agent's QB values are reasonable.
- Test D: wind is the one input with a historical edge, and the prompt's values were too large.
- Test E: 1H margin = 0.48 + 0.62 × full spread; 1Q margin about 0.25 × spread; 1H total about 51% of full.
- Wagerhouse full-game lines sit about 0.3 points from Pinnacle; 46% exactly equal. 70 period, team-total lines compared on 2026-11-22 afternoon: nearly all within half a point. The three biggest gaps (Raiders at Broncos first half, Denver team total, Jets at Chargers first half) are Pinnacle's derivative numbers being inconsistent with its own full-game line, not Wagerhouse being soft. Do not treat a Wagerhouse-vs-Pinnacle gap on a derivative as an edge without checking it against the full-game implied number.
- Player props: Pinnacle's props are readable free (`odds/derivatives.py`, special matchups). Wagerhouse shows them on the site under Football, "NFL Player Props" (Sunday Night Player Specials, Anytime TD, 1st TD, Props Plus; rows are player vs stat with the over/under in the Total column), but `Lines/Get_LeagueLines2` with guessed league names (`NFL Player Props`, `NFL Props Plus`, etc., wagerType Straight/Props/Prop, many propDescription values) returned zero lines, and the site's script is behind the login. The real request has NOT been found. Kylor was asked to capture the Network tab (the request with "Lines" in its name, Payload and Response); he has not yet. Ask for it once, in plain steps, or find it yourself by probing; do not block on it.
- No free historical prop-line source was found (`04-evaluation.md`, Q3). A prop model can be built from nflverse play-by-play and tested against actual results and against Pinnacle's logged props from now on.
- Data in the logger is about one day old; every week adds data.

## Do this next, in order

1. **Reread the goal above and say back, in one line, what you will deliver:** a model that produces a suggested side or total with a number, a "don't bet past" number, and a held-out test showing it beats the closing line.
2. **Decide the model leg question in the open.** `use_model_leg` is currently false. Either restore a model into fair line only where a walk-forward test supports it, or leave it off for full-game sides and put models where they can win. Write the decision in `docs/decisions/`.
3. **Build candidate models and test each walk-forward on held-out seasons** (train earlier seasons, test later ones, no look-ahead), against the closing line, not against results alone:
   - NFL first-half and first-quarter models from play-by-play (scoring by half, pace, early-down rates). Test A found the full-game side model adds nothing; period lines are a different, less efficient market and Pinnacle's period numbers are the benchmark.
   - NFL player props (receiving yards, receptions, rushing, passing, anytime TD) from nflverse usage and play-by-play, benchmarked against Pinnacle's logged props.
   - Totals with weather and pace using free Open-Meteo history. Test the forecast-versus-actual gap first (`04-evaluation.md` tuning item 5).
   - Injury value beyond quarterbacks, measured from nflverse (tuning item 7).
   A model that fails the held-out test gets weight 0 and a short note in `docs/research/`, as the matchup and totals models did.
4. **Wire any model that passes into the slate sheet** so it drives a Bet or Conditional, with its own "don't bet past" number. Keep `engine card` refusing a Bet the numbers do not support. Extend `engine card` to period lines, team totals and props; today it only handles full-game spread and total.
5. **Props at Wagerhouse:** find the request (see above), add a read-only call to `READ_ONLY` in `odds/wagerhouse.py`, log it, compare with Pinnacle.
6. Small commits, tests with each, plain-English summary to Kylor with the instruction first.

## Working rules

- Write for a phone: first line says what to do or what happened, plain words, no ref numbers.
- Claims about the engine cite a file; claims about the world cite a link.
- Wagerhouse is read-only and paced. Do not poll constantly.
- Kylor is not a quant. When you hand back, say what you built, what it found, what you could not verify.
- Do not tell him there is "no pick" and stop. If the numbers support none, say what model you are building to find one and when it will be testable.
