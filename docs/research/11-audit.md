# 11. Audit of the engine against the red-team checklist (Nov 23, 2026)

Source: the checklist (section 10) from Kylor's red-team write-up with a separate agent. Only section 10 and the source list reached this session, so this audits the engine against the checklist, not the write-up's claims. I could not open its sources; several are dated October 2026 or are vendor pages (the write-up's own Tier C), so none of its numbers were used.

Rule for the marks, from the checklist: **pass** has evidence in a file; **fail** contradicts the item; **untested** means no test exists ("we plan to" counts here); **n/a** means the engine does not claim that market or has switched that model off (fair line for sides and totals is Pinnacle's, `config.yaml` `picks.use_model_leg: false`, because every own-model version lost to the close, `04-evaluation.md`). Where an item concerns a model that is off, it applies the day that model is rebuilt, not before.

## Verdict (the shape section 10.9 asks for)

- **Forecasting.** Sides and totals have no forecast of their own, by decision. The two live models are wind totals (walk-forward on earlier seasons) and the two props models (held-out seasons, then a forward test against Pinnacle).
- **Versus the market.** Own sides model: tested, lost. Wind: beat the closing total on seasons it never saw, weaker since 2024. Props: forward test only, 150 NFL and 209 NBA graded of 300 needed; the model is currently no better than Pinnacle's price on NFL and about level on NBA.
- **Pricing errors.** Key numbers: handled by real landing tables and now checked (`11a-calibration.md`: predicted and realized within 0.6 points in every bin, NFL 2019 to 2025 and NBA 2026 to 2027). Impossible sigma: not found. Double-counted vig: not found. **Correlated stakes: was a gap, now fixed** (one position per game, `card.py`).
- **Overfit risk.** Wind is the only tuned input; its forecast-bias constant was fitted on 2024 to 2026, the same seasons used to say it weakened. Injury values entered by the agent are untested until graded Leans exist.
- **Unverified hurdles in use.** None found copied into the engine as requirements. `home_field` constants in `config.yaml` (NFL 1.7, College 2.5, NBA 2.2) are flat by sport, not by era, but they only feed the switched-off model leg.
- **Highest-priority missing test, per market.** Sides and totals: unpriced-news Leans graded against Pinnacle's close at the issue time (now being collected). Wind totals: wind tested on the forecast available at bet time, not on realized wind. Props: Wagerhouse prop lines logged (item 9 in the plan, blocked), then the same test.

## 10.1 Shared

| # | Mark | Evidence |
|---|---|---|
| 1 Features known at bet time | pass for sides and totals; untested for wind | Sides use Pinnacle at the read time. The wind model was fitted and tested on realized (reanalysis) wind; live use takes a day-before forecast plus a bias constant (`config.yaml` `forecast_bias_mph`). The test never used a forecast. |
| 2 Walk-forward, tuning inside training | pass | Wind (`wind_totals.py` fits only on earlier seasons), props (`props.py` backtest), calibration check (`calibration.py`). |
| 3 Baselines against the no-vig market | pass for props; untested for wind | Props are scored against Pinnacle's vig-free chance (150 NFL graded: model 0.2579 against Pinnacle 0.2524). Wind was compared with the closing total, not on log loss. |
| 4 Reliability diagram on an unused season | **pass for the landing tables (new)**; props pass; wind untested | `docs/research/11a-calibration.md`. Props backtest checks "when it says 60%" (`props.py` docstring). |
| 5 Blend test | pass | Test A in `04-evaluation.md` blended the model with the market; the model got no weight, so it is off. Props gate requires the blend to lower error. |
| 6 ROI on a pre-fixed rule, with sample size | pass | Gates are fixed in config (300 props, 100 picks). |
| 7 Search disclosed | untested | Thresholds and knots tried for wind are listed in `wind_totals.py` (`KNOTS`, `THRESHOLDS`) but the count tried before the one used is not stated in a write-up. |
| 8 Vig removal fits the market | pass | Multiplicative for near-even spreads and totals (`odds/math.py`); no lopsided moneylines are priced. |
| 9 Kelly on residual edge, correlated bets as one | pass (flat stakes); **correlation fixed** | Flat 1 unit, 0.5 for a Conditional, cap until 100 graded (`config.yaml`). No Kelly is used. One position per game now enforced in `card.py`, with a test. |
| 10 Decision time declared | pass | Every pick is logged at issue and graded against Pinnacle's last line before kickoff (`grade.py`); a Lean is fixed at issue (`leans.py`). |
| 11 Betting into a worse price than the best | pass | The book is the only book; the reference is Pinnacle, and the "don't bet past" number is code-stamped. |
| 12 Historical inefficiencies re-estimated on recent seasons | partial | Wind re-estimated on 2010 to 2025 with the weakness since 2024 stated and a half-unit cap. Public-side fades and splits are banned (CHARTER). |

## 10.2 NFL spreads

Items 13 to 16 and 18 to 19: **n/a** (no own spread model; fair is Pinnacle). Item 17: **pass** (`pricing.py` builds the margin distribution from real landing spots, so 3 and 7 carry their weight; the calibration check priced 7,970 bets at 2.5/3/3.5 and 6.5/7/7.5 with squared error 0.2393 and bins within 0.4 points).
Item 19 (quarterback): **untested**. The agent enters point values by judgment (`adjustments.yaml`). The engine counts only the part Pinnacle has not moved for and requires `news_at` (`slate.py` `unpriced_part`), which prevents double-counting but does not validate the size. Graded Leans and Bets are the test. Item 20: **n/a** to backtests (none run with injury reports); live use uses the report at read time.

## 10.3 NFL totals

Items 21 to 23: **n/a** (the pace-and-efficiency totals model failed and is off, `02-totals-model.md`). Item 24: **fail as stated, partial in practice**: the wind model beat the closing total on held-out seasons, which is the market comparison, but on realized wind rather than a forecast (see item 1). Item 25: pass for the engine (the only totals rule is wind, a recent re-test, half-unit Conditional).

## 10.4 NFL props

| # | Mark | Evidence |
|---|---|---|
| 26 Role layer | partial | Recent weighted game history scaled by team implied points (`props.py` docstring); no snaps, routes or targets layer. |
| 27 Distribution matches the stat | pass | Empirical distribution from the 500 closest earlier player-games, not a normal (`props.py` docstring). |
| 28 Reconciles with the game model | partial | Scaled by implied team points from spread and total; target shares are not forced to sum. |
| 29 Teammate out moves opportunity | untested for NFL | The NBA model has it (`nba_props.py`); the NFL docstring lists none. |
| 30 Against historical prop prices | **untested** | No history of prop prices exists; forward test only since Nov 21. Betting performance on props is labelled untested everywhere. |
| 31 Alternate lines | untested | Only Pinnacle's main lines are scored. |
| 32 Same-game props as one position | n/a | Props cannot produce a pick yet. |

## 10.5 to 10.6 College

Items 33 to 43: **n/a** for a model (none is on). The college lane prices Pinnacle against Wagerhouse and counts unpriced news. A college model would need items 33 (a real preseason prior) and 34 first; the opener test using outside ratings (plan Test 4) is the first step and is **untested**.

## 10.7 NBA spreads and totals

Items 44 to 49: **n/a** (no own NBA model). Item 47: the flat back-to-back adjustment was removed on Nov 23 because Pinnacle already prices rest; consistent with the checklist's caution. Item 50 (market test, blend weight): **untested** because there is no NBA model to blend. The curve that prices half points (`pricing.py` `bell_rows`) was checked: bins within 0.6 points on 24,880 priced NBA bets. A bell curve with sd 12 held up locally even though the overall residual spread is about 13.9 (results bunch near the line); replacing it with real results was marginally better on squared error (0.24469 against 0.24502) and is not worth the switch on two seasons.

## 10.8 NBA props

| # | Mark | Evidence |
|---|---|---|
| 51 Minutes times rate, wider for bench | partial | Minutes times per-minute rate (`nba_props.py` docstring); uncertainty comes from the 500 closest earlier player-games, not an explicit bench width. |
| 52 Sit probability separate | partial | Teammates out are handled from the official report; the player's own sit probability is not separate. |
| 53 Usage and minutes both move, feasibly | partial | Vacated shot volume boosts rates and minutes move (`nba_props.py`); no team-level feasibility constraint. |
| 54 Dispersion per stat | pass | Empirical distribution per stat, not one Poisson or normal. |
| 55 Combined props share a minutes draw | untested | PRA is its own stat with its own empirical distribution; shared-draw correlation is not modelled. |
| 56 Splits survived a held-out test | pass | Opponent, home/away and personal rest splits are not in the model. |
| 57 Coherent with game pace | partial | Scaled by team expected points from the closing line (fitted power). |
| 58 Historical prop closes, pre-registered rule | **untested** | Same as item 30. Gate: 300 graded, edge 5% (`config.yaml` `models.props`). |
| 59 Limits and correlation | n/a | No prop can be bet yet. |

## What changed because of this audit (Nov 23)

1. **Freeze stamp.** Every pick, flagged Pass event and Lean now records the commit and a fingerprint of the settings that decide picks (`src/engine/version.py`, `rule_versions` table). A change to rules or settings starts a new version, shown on the board and in `engine status`. Picks made on uncommitted code are stamped "+edited".
2. **Landing-table calibration** (`engine calib-test`, `11a-calibration.md`). Passed for NFL sides, NFL totals, NBA sides, NBA totals.
3. **One position per game** (`card.py`): a side and a total in the same game are not independent, so only the stronger stays live; the other becomes a Pass with the reason on the card.
4. **Open items, unchanged:** wind on the forecast (needs forecast history we do not store), Wagerhouse prop lines, NFL teammate-out minutes for props, a team-level feasibility check for NBA props. None blocks grading week; none affects a Bet.

## What this audit cannot tell you

The checklist tests whether a model's numbers are honest. The engine's sides and totals have no model of their own, so for most of the engine the only honest test is graded picks against the close, which has one graded pick so far (0-1, a Conditional with no closing line stored). A week of grading shows whether the process runs cleanly and whether the average closing-line value is not negative; it cannot prove an edge.
