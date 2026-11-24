# Handoff: deep evaluation of the betting model (written Monday Nov 23, 2026, evening Mountain)

Paste the prompt at the bottom into a fresh Claude Code session opened in this folder (set `UV_PROJECT_ENVIRONMENT=.venv.nosync` first; a
plain `uv run` from a shell without it fails, see "Traps" below).

## Why this exists

In one day the engine went from a price checker to a handicapping model that stakes **real money from the first pick** (NFL $50 unit, NBA $25,
college $25). Kylor approved each step, and on two occasions chose to stake markets whose walk-forward tests gave the model no weight. He
now wants an independent, deep evaluation: is the model built right, is anything leaking or double-counted, which parts deserve money, and
what the best public research says the model should be doing that it is not. **Be an outside reviewer, not a defender of this code.** The
author of most of it is the session that wrote this handoff.

## Read first, in this order

1. `CHARTER.md`, then `PLAYBOOK.md` (approved; how picks are chosen; section 9 says what is built).
2. Decisions `docs/decisions/0014` to `0023` (teasers, stale-plus-news, run-on-change, readiness in win chance, the playbook and real money,
   betting at starting weights, units, props, all sports, script additions).
3. Research, newest first: `17` (script additions, matchup layer), `16` (NBA and college scripts, props lead effect, NBA Under lean),
   `15` (NFL script), `14` and `14a` (deep review and sourced brief), then `04`, `02`, `03`, `05`, `09`, `06`, `08`, `13`, `11`, `11a`, `12`.
4. Generated state: `docs/lanes/TRACKER.md` (every Telegram pick against Kylor's real wagers since Nov 23, decision 0024; use it for the live record), `docs/lanes/STATUS.md`, `docs/lanes/PLAYBOOK-RECORD.md`, today's cards `docs/cards/<date>-{nfl,nba,college}-playbook.md`,
   `docs/cards/<date>-nfl-teasers.md`.
5. Code: `src/engine/picks/playbook.py` (the pick engine), `src/engine/models/script.py`, `nba_script.py`, `college_script.py`,
   `props_script.py`, `props_matchup.py`, `props.py`, `nba_props.py`, `src/engine/picks/teasers.py`, `src/engine/clv.py`, `src/engine/stale.py`,
   `src/engine/poll.py` (the hourly read that runs all of it), `ops/agent_prompt*.md` (the research agent, which clears CHECK picks).
6. `config.yaml`: `playbook:`, `teasers:`, `units_by_sport`, `lanes:`.
7. Run `git status`, `git log --oneline | head -30`, `uv run pytest -q` (219 tests pass at handoff, commit `085dec0`).

## What is live with real money right now

| Lane | What decides a pick | Stake | Test result behind it |
|---|---|---|---|
| NFL sides, totals, team totals | Game-script team points blended with the market at the playbook's STARTING weights (side 0.25, total 0.35, team total 0.4); 3% edge vs Wagerhouse's price | B = $25 | Walk-forward weight 0 for 2024-26 on sides and team totals; totals weight small but positive after schedule adjustment (research 15, 17). Kylor chose to stake anyway (0019) |
| NFL props | Props model (recent usage, distribution of 500 nearest player-games) re-scaled to script team points and expected margin (carries, attempts, receiving yards only), blended 0.5 with Pinnacle's no-vig chance; 4% edge at Pinnacle's price | B = $25 | Props model honest on held-out seasons; vs Pinnacle forward test slightly worse (150 graded); no historical prop lines exist |
| NBA props | NBA props model (minutes x rate) re-scaled to script team points, blended 0.5; 4% edge | B = $12.50 | Forward test about level with Pinnacle (209 graded); heavy Under lean, not losing so far |
| NFL Wong teasers | Favorites -7.5 to -8.5 / underdogs +1.5 to +2.5, total <= 49, 2-team 6-point at -110 | A = $50 | 75.8% legs 2023-26 vs 72.4% break-even; the most evidence-backed lane |
| NBA and college sides/totals | Same machinery | Shown only | Walk-forward lost outright (research 16) |
| Wind unders (old path) | Wind model, Conditional | Paper | Strong history, weaker since 2024 |

Open picks at handoff: NFL team total 1, NFL props 2, NBA props 2, one teaser ticket ($50); 650 candidates logged in `playbook_candidates`.

## What the session that built it is worried about (check each; do not take its word)

1. **Staking against the evidence.** NFL sides and team totals are staked at weights the walk-forward test rejected. Is that negative expected
   value at Wagerhouse's 4.7% juice? Estimate it.
2. **Prop prices are Pinnacle's, not Wagerhouse's.** Edges are computed at Pinnacle's price; Wagerhouse props (Bet Builder) are juicier and
   unreadable. Each pick carries a "worst price" limit. Are the edges overstated, and is the limit right?
3. **Correlation.** One full-game position per game, but a team total, a player prop on the same team and a teaser leg can all ride on one
   game script (tonight: Commanders team total under and Ja'Marr Chase TD under). Nothing caps combined exposure.
4. **CHECK clearing by an LLM agent.** Picks far from the market are held until the research agent writes "clear". If it clears whenever it
   finds no news, the safeguard is weak. There is no record yet of how it behaves.
5. **Look-ahead risks to audit:** the NFL script's `backup_qb` uses the actual game starter from nflverse (known at kickoff, not at the
   opener); injury clusters use the final report; team-total tests use totals implied by the closing spread and total, not real team-total
   lines; the wind model was tested on reanalysis wind; NBA absences in the props model come from box scores in history.
6. **Multiple testing.** The NFL totals lead (53-56% at 3+/4+ disagreements, research 17) is one of seven script variants, on top of many
   earlier tests (research 02 to 17). How much of it survives a correction?
7. **Pricing curves never calibrated:** team-total bell curves (NFL sd 9, NBA 10.5, college 11) and college landing tables used by the new
   college stale alerts. Only the NFL and NBA side/total tables were checked (`11a`).
8. **Weights re-fit** from graded candidates after 40 per market (`engine playbook-record`), but the fit is least squares on the blend; is
   that the right objective for betting decisions (log loss, closing-line value)?
9. **Full units from the first pick,** stop-loss 10 units per sport, no Kelly. Fine for $50 at this volume, or reckless given the evidence?
10. **Drift:** the charter's lane list, the status table, the cards and the Telegram messages should all describe the same rules. Check one
    live message against the code that produced it.

## Data available (all free, local unless noted)

nflverse games 1999-2026 (closing spread/total, results, referees partly), play-by-play 2015-2026, weekly player stats 2018-2026, injury
reports 2018-2026, snap counts 2018-2026 (`data.nosync/raw/nflverse/snaps`), FTN charting 2022-2026 (`.../ftn`, blitzers and box counts),
participation 2023 only (`.../participation`, coverage type); CollegeFootballData 2021-2026 (scores, closing lines by book, ESPN event ids);
Prediction Tracker college archive 2015-2025 (`data.nosync/raw/tracker/archive`); ESPN NBA box scores with closing lines (seasons 2024-2027);
Open-Meteo weather; our own logs since Nov 21 (`line_snapshots`, `derivative_snapshots`, `prop_evals`, `playbook_picks`,
`playbook_candidates`, `playbook_grades`, `teaser_legs`, `teaser_tickets`, `stale_alerts`, `wind_forecasts`, `burst_reads`). Kylor's graded
Wagerhouse bets: `wagers`, `legs`. **Not available:** historical prop lines, historical Wagerhouse or Pinnacle lines before Nov 21, news
timestamps, coverage data after 2023.

## Traps

- Shells need `export UV_PROJECT_ENVIRONMENT=.venv.nosync`. A stray `.venv` inside iCloud was deleted on Nov 23 because iCloud marks it
  hidden and Python then skips its `.pth` file. The launchd jobs set the variable themselves.
- The hourly read and the 10-minute fast reads write to `data.nosync/engine.duckdb`. Open it read-only, or copy it, for analysis.
  `engine playbook --dry-run` works on a copy.
- Scheduled jobs auto-commit cards and generated status files by path; that is expected, not someone else's work.
- `engine wh-edge` rewrites `docs/research/12-...`; the playbook card files are rewritten every hour.

## Rules

- Plain English; Kylor is technical but not a quant. Lead with what he gets. A claim about the engine needs the file; a claim about the world
  needs a link you opened (mark anything you could not open).
- No look-ahead; hold out seasons for anything tuned; report every variant tried.
- **Stop for Kylor's approval before changing code, config or schedules.** Exception: if the engine is telling him to bet something false
  (wrong stake, wrong number, a rule broken), say so at the top with the one-line fix.
- Logins are in `.env`; never print or store them.
- Commit your documents; do not push unless asked.

---

## Prompt to paste into the fresh session

```
Read CHARTER.md and PLAYBOOK.md first, then docs/handoffs/2026-11-23-model-evaluation.md, and do what it says.
Run git status and git log before anything else and tell me if there is uncommitted work you did not write.
Set UV_PROJECT_ENVIRONMENT=.venv.nosync in every shell.

This is a deep, independent evaluation of the betting model that now stakes real money (NFL $50 unit, NBA $25).
Be an outside reviewer, not a defender of the code. Do all of this:

1. Read every file the handoff lists, including the code that makes picks (src/engine/picks/playbook.py and the
   models it calls) and the research agent's instructions.
2. Do deep source research with a research agent: how the best bettors and the public research build NFL, college
   and NBA models, props models, totals models and staking, and what they say about blending with the market,
   closing-line value, correlation and soft books. Open and cite real sources; mark claims as shown with data,
   asserted, or folklore; discard tout and affiliate pages.
3. Re-run and audit every walk-forward test the engine relies on (research 15, 16, 17, the props models, the
   teasers, wind). Look for look-ahead, leakage, double counting and multiple-testing luck. Correct for the number
   of variants tried. Re-run what you can independently, from the raw data, without reusing the engine's code
   where possible.
4. Answer the ten worries in the handoff one by one, with numbers.
5. Grade what is live today: for each lane (NFL sides/totals/team totals, NFL props, NBA props, teasers, NBA and
   college shown-only picks, wind), the expected value per bet at Wagerhouse's real prices, how sure you are, and
   whether it deserves real money, paper, or nothing.
6. Check one live Telegram message and one card against the code and config that produced them.

Write one document, docs/research/18-model-evaluation.md, that starts with a half-page plain-English answer to
"which of these bets should I keep making with real money, and how sure are you?", then a ranked list of what to
change, keep and stop, each with the test that proves it and the number that kills it, and a 4-week plan.
Stop for my approval before changing code, config or schedules.
```
