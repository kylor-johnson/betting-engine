# 0040: Every pick the model makes is a real bet on Telegram (2026-11-24)

Kylor, Nov 24 night: "i want to make sure what goes to telegram is all bets this model is proposing. i am not tuning it for a little while
until we see the results of how the model is working." Asked whether every pick (all sports, all bet types, props included) should come
to Telegram as a real bet with a stake and a "don't bet past" number: "Yes, all as real bets".

Replaces:
- decision 0038 (NFL and NBA props to paper): props are staked again;
- decision 0036 item 2 (NBA spreads, totals and team totals shown only, news picks off): NBA full-game is staked again, as in 0035.

(The caps kept here were removed the next morning by decision 0041.) Unchanged: every money rule in the charter (unit sizes, A = 1 unit, B = half, the per-lane caps, one unit a game, the stops and the review
line), the props weights and everything else in 0036 and 0037, 0039. A pick past a cap, or on a game that already carries a unit, is still
issued at $0 and named in the 9am recap; a stop still pauses a sport. The three paper lanes, college openers and NBA news props are tests of
other signals, not the model's picks, and stay off Telegram.

**No tuning:** from now until Kylor says otherwise, sessions do not change weights, thresholds, lanes or read times. They fix plain bugs
only (code that disagrees with a decision) and report results.

What he was told before choosing (research 25): NBA props' paper suggestions are 71-72, −11.9 units; the NFL props model's best weight on
true first reads is 0.00; the NBA script cannot see who is injured and lost its walk-forward test.

Test: `tests/test_tuning_check.py::test_every_model_pick_is_staked_decision_0040`.
