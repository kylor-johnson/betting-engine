# 0038: NFL and NBA props go to paper (2026-11-24)

Kylor, Nov 24 night, on research 25's questions 1 and 2 ("NBA props staked or paper now?", "NFL props, same question"): "1 paper, 2 paper".

Replaces: "NFL props and NBA props staked" in decision 0026 (kept by 0027). The props weights of decision 0036 item 1 (NFL 0.15, NBA 0.25)
are unchanged.

**Why (the numbers he was shown, research 25):**
- NBA: the paper suggestions (5%+ disagreements) are 71-72, −11.9 units; live staked 1-2, closing-line value −3.0% on 3; research 24b's best
  weight is 0.15 to 0.20, under the live 0.25.
- NFL: on each prop's true first read the best weight is 0.00 (research 24b), so the model may add nothing to Pinnacle; live 2-0,
  closing-line value −2.1% on 2.

**The rule:** `playbook.sports.NFL.props_stake` and `playbook.sports.NBA.props_stake` are false. Prop picks are still priced, issued, frozen
and graded exactly as before, at $0, and never sent to Telegram (decision 0025's paper mode). Props already sent stay on the record at the
number sent, and CANCELLED still covers them before their games.

Back to staked takes a decision note Kylor asks for. The record to watch is the paper props' closing-line value (`PLAYBOOK-RECORD.md`) and
the review yardstick in the charter (the blend beats Pinnacle on 300 and closing-line value above zero).

Also answered the same night: college props stay without a lane (question 3); NBA fast reads stay on the first tip only (question 4); no
half-hourly pre-start reads for NFL and college (question 5).

Test: `tests/test_tuning_check.py::test_props_are_paper_decision_0038`.
