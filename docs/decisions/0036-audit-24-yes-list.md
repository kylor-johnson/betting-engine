# 0036: The full audit's yes-list (2026-11-24)

Kylor, Nov 24, on the 14 questions in `docs/research/24-full-audit.md`: "yes to 1-13, do them". Question 14 (the Titans +15 pick) was his
call and is left to him.

Replaces:
- the props blend weight of 0.5 in decisions 0021 and 0022;
- NBA full-game "stake" in 0035 and NBA news picks "on" in 0030;
- the stop's start date in 0033 item 2 (the rule stays, the date moves) and the review line's count in 0027 (now from the same date);
- the "before" line in 0029 and 0033 item 4;
- "caps count paper picks" in 0025 and 0033 item 7, for one kind of paper pick;
- prop profit at Pinnacle's price in 0021 and 0025;
- read hours 7am-5pm on weekdays (0002, 0004) and the NBA watcher's three times (commit b115f72; no note);
- the not-done items of 0025: the market reference, the NBA team-points curve, and re-training the NFL script without actual weather.

Every document that quoted the old rule is updated in the same commit.

1. **Props weight:** our props model counts 0.15 (NFL) and 0.25 (NBA) against Pinnacle, not 0.5. These are the best weights on the forward
   test (research 24 re-run of `scripts/research18/props_fwd.py`: 199 NFL, 563 NBA props). Config `playbook.sports.<SPORT>.weights.prop`.
2. **NBA spreads and totals: shown only, no money.** News picks are off too. The NBA script cannot see who is injured. Back to staked takes
   a decision note Kylor asks for.
3. **News adjustments:**
   - They count toward the CHECK distance (our script plus the news, against the market).
   - An entry larger than NFL 3, college 5.5 or NBA 4 points counts for nothing, and the card says why (`playbook.MAX_NEWS_POINTS`).
4. **What Pinnacle has priced** is measured from its earliest read in the 12 hours before `news_at`, so a late time cannot double-count
   (`slate.unpriced_part`).
5. **Our number:**
   - The market reference is Pinnacle's line moved by its price lean, for sides, totals and team totals (`playbook.pin_fair`). CANCELLED
     compares like with like: picks issued before 23:00 UTC Nov 24 keep the raw line (`FAIR_SINCE`).
   - The NFL script is fitted without actual weather. A forecast-wind term (−0.273 points of total per mph above 6) was fitted on 2024-2025
     day-before forecasts and passed its rule on 2026, written before it ran (squared error 148.73 against 151.85 on 81 games;
     `scripts/research24/nfl_forecast_weather.py`). Rain is gone: there is no rain forecast history.
   - The NBA team-total curve is 11.5 (measured 11.46).
6. **Stops and the review line count from Nov 23** (`playbook.live_since: 2026-11-23`), so the 11 picks sent that day count. On this
   change: NFL +1.64 units, NBA −0.54, college 0.
7. **Units first** on every Telegram stake line ("Stake: ½ unit ($12.50)"), the recap, `TRACKER.md` and `tracker.html`'s model numbers. The
   daily check's "$0 sent as a bet" guard reads both wordings. Kylor's own wagers stay in dollars, as the account reports them.
8. **Reads until 9pm Mountain every day:** resends, CANCELLED and a closing read for evening NBA and college games. The NBA watcher also runs
   at 6:30pm. Kylor reloads the nba-watch launchd job.
9. **A pick Pinnacle has moved against** is demoted before one pick per game is chosen, so the next-best pick on that game can be issued.
10. **Picks made paper by the one-unit-a-game rule** no longer take a weekly or daily cap slot (`playbook.COUNTS_FOR_CAP`, column
    `paper_reason`).
11. **Props pay at the limit price** (the worst Wagerhouse price the message said to take, column `limit_price`). The five props graded
    before today were re-graded the same way.
    - Closing-line value stays against Pinnacle's price, the honest measure.
    - **Voids:** a prop whose player has no stat line, once the game is final, is V (no money either way) 30 hours (NBA) or 40 hours (NFL)
      after the start. Any pick with no final score 72 hours after the start is V. Voids show on the tracker as "void".
12. **NFL props variant** (zero-usage games skipped, carry share into catches): pre-registered in `docs/research/24b-props-variant.md`
    (commit d732378) before it ran. **It failed** (best blend weight 0.00 against Pinnacle), so it stays off. The run also found the NFL
    props model's best weight is 0.00 when each prop's true first read is used (0.20 at the last read; NBA 0.15 to 0.20). Item 1's weights
    stay as approved, and that range is recorded in 24b.
13. **Three paper lanes,** $0 and never sent (`picks/paper_lanes.py`, `docs/lanes/PAPER-LANES.md`, a block at the bottom of each sport's
    card). Kill rule: at 150 graded (per sport for L1), off unless average closing-line value is above zero with its 95% range above zero.
    - **L1:** Wagerhouse 1+ point better than Pinnacle's current number (0.5 through 3 or 7 in the NFL), all three sports.
    - **F1:** Sunday 5pm to Tuesday 6am, public ratings 1.5+ points from Wagerhouse's NFL spread.
    - **D1b:** our script's disagreement with Pinnacle's full-game line, carried into Pinnacle's first-half spread and total and game team
      totals, at 4%+.

Tests: `tests/test_decision_0036.py`, `tests/test_paper_lanes.py`.
