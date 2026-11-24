# 24b. NFL props variant: zero-usage games and carry share into catches (pre-registered Nov 24, 2026; decision 0036 item 12)

Written and committed before anything was run. Paper only: nothing here changes a live pick unless it passes and a session switches it on
with a note.

**Why** (research 24, Job 1 part 3; the Sharp red-team): our NFL props model put Jonah Coleman's receptions Over 3.5 at 30.8% against
Pinnacle's 45.4%. Two causes: a zero-usage week 1 counted in full in his average, and no link from his new carry share (71% last game)
to his catches (the role-change term is off for receptions). History says reception spikes mostly revert (actual / projection 1.006 on
686 cases), so this may well fail.

**The variant, one specification:**
1. **Zero-usage games:** in every usage average the props model builds, a game where the player had 0 targets, 0 carries and 0 pass
   attempts is skipped (not counted as a zero).
2. **Carry share into catches:** for running backs, when the props news layer's carry role ratio (share in the last two games against the
   long share) is above 1, multiply the receptions, targets and receiving-yards projections by ratio^0.25 (the rushing role power the model
   already uses), with the same cap the rushing role term uses.

**Data:** every graded NFL prop in `prop_evals` (the first price we saw per player, stat and game; about 200 today). The variant's chance
of the Over is computed at the same line, **using only stats from before that game** (the row's `through_week`), so there is no look-ahead.

**The test, both parts must pass:**
1. **Against Pinnacle:** the variant model's log loss on those props is lower than the current model's, and the best blend weight against
   Pinnacle's no-vig price (as in `scripts/research18/props_fwd.py`) is above 0.15, the live weight since decision 0036.
2. **History guard:** on held-out 2023-2026 player-games, squared error for receptions, targets and receiving yards is no more than 0.5%
   worse than the current model.

**If it passes:** a session switches the variant on with a decision note, and the props weight is re-fitted. **If it fails:** it stays
off, and the Coleman miss is recorded as what the history says it is: mostly noise that reverts.

**Small sample, said now:** about 200 props. A pass is a reason to keep watching at the new setting, not proof.

## Result: FAIL (run after commit d732378; `uv run python scripts/research24/props_variant.py`, about a minute)

The variant is fitted exactly as the live model is, from seasons before 2026, with nothing tuned. It uses only games before the day each
prop was read. Recomputing the current model reproduced the stored chance within 0.005 on 193 of 199 props; the misses are injury news
the live read had and the run could not replay.

| Props | n | Pinnacle | Current | Variant | Best weight (current / variant) |
|---|---|---|---|---|---|
| All (the test) | 199 | 0.6881 | 0.7220 | 0.7200 | 0.00 / 0.00 |
| Excluding field goals | 190 | 0.6876 | 0.7259 | 0.7238 | 0.00 / 0.00 |
| Receptions and receiving yards | 86 | 0.6802 | 0.7307 | 0.7319 | 0.00 / 0.00 |

The numbers are log loss: lower is better.

- **Part 1 fails.** The variant's log loss is lower than the current model's (0.7200 against 0.7220), but its best blend weight against
  Pinnacle is 0.00, not above 0.15. On the receiving props it was aimed at, it is slightly worse.
- **Part 2 passes:** 2023-2026, 8,632 player-games. Receptions are +0.34% worse, targets +0.41% and receiving yards +0.20%, each under 0.5%.
- **Verdict: off.** Jonah Coleman's receptions Over 3.5 moves from 30.8% to 45.4% under the variant; Pinnacle is now 53.9%. One player is
  not the sample, and on the sample the variant adds nothing.
- **Kickers** were left out of rule 1, because they never have targets, carries or pass attempts, so the literal rule would delete every
  kicker game. The "excluding field goals" row does not depend on that choice, and it gives the same verdict.

**A finding the test turned up, for Kylor.** With each prop's true first read in time order, the current NFL model's best weight is 0.00,
not the 0.15 decision 0036 set. Research 18's `props_fwd.py` took "first seen" rows in no fixed order. The same check, done both ways:

| Sport | Taken at | n | Pinnacle | Model | Best weight |
|---|---|---|---|---|---|
| NFL | the first read | 199 | 0.6881 | 0.7187 | 0.00 |
| NFL | the last read before the game | 199 | 0.6890 | 0.7073 | 0.20 |
| NBA | the first read | 574 | 0.6863 | 0.6995 | 0.20 |
| NBA | the last read before the game | 574 | 0.6845 | 0.6960 | 0.15 |

The decision 0036 weights (NFL 0.15, NBA 0.25) sit inside or just above these ranges, so they stay as Kylor approved. The honest reading:
- the NFL props model may add nothing to Pinnacle at all;
- the NBA one adds a little.

The review line (−1.5% closing-line value on 25 graded) is the check that will show it in live picks.
