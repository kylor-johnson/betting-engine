# 0041: No caps on the number of bets (2026-11-25)

Kylor, Nov 25 morning, on learning that two college picks went out at $0 because college had reached 5 for the week: "there should be no
cap on the number of bets". Decision 0040 ("every pick the model makes is a real bet") had wrongly kept the count caps and the one-unit-a-game
cap, so picks the model proposed still came out at $0 and stayed off Telegram.

Turned off (0 = off in `config.yaml`; the switches stay):
- full-game picks a period: NFL 5 a week, college 5 a week, NBA 2 a day (`max_per_period`);
- props a period: NFL 10 a week, NBA 4 a day (`props_per_period`), and 2 props a game (`props_per_game`);
- one unit a game across picks and teaser legs (`game_cap_units`).

Still in force: unit sizes (A = 1 unit, B = half); one full-game position per game, frozen at first qualification; never into a Pinnacle move
against us; the 10-unit stop per sport (a pause, not a cap on count); no weekly dollar cap (already off).

Picks this week that came out at $0 only because of a cap, on games not yet started, were removed so the next hourly read re-prices them at
the current number and sends them as bets if they still clear. Picks already started stay as they were graded.

This is Kylor's call, not tuning; the no-tuning rule of 0040 stands for weights, thresholds and read times.

Test: `tests/test_tuning_check.py::test_no_caps_on_bets_decision_0041`.
