# 0042: No CANCELLED messages on Telegram (2026-11-25)

Kylor, Nov 25 evening, after CANCELLED for Bears/Lions under 55.5 and Hornets team total over 112.5, both already placed: "should we add some
kind of thing where it doesnt alert me on bets that have already been suggested / posted if the model changes?" He places every pick as soon
as it arrives, so a later CANCELLED changes nothing he can do and reads as the model breaking.

- `cancel_moved` still checks every sent pick before its game and saves one CANCELLED row per pick in `alerts_sent` (kind `cancel`), but
  sends it with kind `cancel`, which is not in `telegram.send_kinds`; it is held back. Adding `cancel` to `send_kinds` turns the message back on.
- A held-back CANCELLED is checked once, not every read.
- Its numbers now show one decimal ("55.1 to 56.1", not "55.1278 to 56.1207").

How the model makes and stakes picks is unchanged (not tuning; 0040's no-tuning rule stands). A move against a sent pick still shows as
negative closing-line value on the tracker, which is the honest measure of whether the model's edges are real.

Tests: `tests/test_review22.py::test_cancelled_once_when_pinnacle_moves_past_the_limit_and_not_for_a_small_move`,
`tests/test_tuning_check.py::test_cancelled_is_kept_off_telegram`.
