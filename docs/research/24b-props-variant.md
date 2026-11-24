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

## Result

(Filled in after the run; see below this line in the next commit.)
