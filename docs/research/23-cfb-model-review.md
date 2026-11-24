# 23. College football model review (Nov 24, 2026)

(Draft. The pre-registered tests below were written and committed before any test was run. The findings and the yes/no list are added
after the tests.)

## Pre-registered tests (written before looking, Nov 24)

Data, all free CollegeFootballData (CFBD), pulled Nov 24 into `data.nosync/raw/cfbd_review/` (kept apart so the live model's cache is
unchanged): per-game advanced stats with garbage time removed and with it kept (2020-2026), last season's final SP+ ratings, returning
production, team talent composite. Games and closing lines: the same cached `cfbd_lines_2021..2026.json` and the same line choice as
research 16 (`college_script._line`).

Method common to every test, identical to research 16: models fitted on earlier seasons only; the weight our number earns against the
close is fitted one season back inside the training window and used on the test season; test seasons 2023, 2024, 2025, 2026; rows need two
games of current-season form unless the test says otherwise; bets at the closing number at -110 (break-even 52.4%) where our own number
disagrees with the close by a fixed amount: **team points 3.5+, game total 4+, side 3+**. The baseline is research 16's model (points
scored and allowed), rerun in the same code so the comparison is like for like.

**T1. Efficiency and tempo in place of points per game.** Add to research 16's six inputs, for the team and for its opponent (decayed
the same way, last season counting as 2 games): offensive and defensive PPA per play (CFBD's expected points added), success rate for and
against, plays per game run and faced, and one product term: offensive PPA per play times the expected plays (average of own plays run and
the opponent's plays faced). Garbage time removed. Pass in a market only if all three hold: (a) the blend's squared error is below the
market's, pooled over 2023-2026, by at least 0.2%; (b) the fitted weight is above zero in at least 3 of the 4 test seasons; (c) the bets
at the fixed disagreement win at least 52.4% pooled, on at least 300 bets.

**T2. Garbage time.** T1 run twice, garbage time removed and kept. "Remove it" passes if our own number's squared error on team points is
lower with it removed in at least 3 of the 4 test seasons. This is a model-quality test, not a betting claim.

**T3. Preseason priors (roster churn).** T1 plus, for the team and its opponent, four numbers known before the season: last season's
final SP+ offense and defense, this season's returning production (share of last season's PPA that returns) and this season's talent
composite. Each is multiplied by a fade `4 / (4 + current-season games)` so it matters early and fades out. Rows with fewer than two
games are allowed in this test (weeks 1 and 2 use last season's final form). Judged on **CFBD weeks 1 to 4 only**. Pass: the blend's
squared error below the market's on sides or totals in weeks 1-4, bets at the fixed thresholds at least 52.4% on at least 150 bets, and
2026 (the only season not already seen by research 14's week 1-4 slice, which used 2021-2025) not below 50%. Caveat written now: the
talent composite for a season is compiled in the summer and may include late roster moves; that is mild look-ahead and is noted with the
result.

**T4. The early number (openers).** Using the T1 model with garbage time removed (chosen now, whatever T1 shows), compare our number with
the opener from the same book whose close we use (CFBD `spreadOpen`, `overUnderOpen`; 2023-2026). Bet at the opener where we disagree
by 3+ on a side or 4+ on a total, graded against the result at the opening number. Pass: at least 52.4% on at least 200 bets, and the
line moved toward our side from open to close by at least 0.25 points on average. Our inputs use only games already played, so the only
look-ahead is news that broke between the open and kickoff (that would flatter the move, not hurt it) and a few openers posted before the
previous week's game was played.

**T5. Where the close is weakest (market tier).** The T1 bets at the close, split by: both teams Group of 5; at least one power-conference
team; an FCS opponent; CFBD week 1-4, 5-9, 10 and later. 18 slices (6 splits x 3 markets), so about one false pass is expected by luck.
A slice passes only at 54%+ on 200+ bets and 52.4%+ in both halves (2023-24 and 2025-26). A pass here makes a forward test, never a
staked lane on its own.

**Descriptive, no pass/fail:** how often college final margins land exactly on 3, 7 and 10 against the NFL; how far college lines move
from open to close.

Variants: one specification per test, one ridge penalty (50, as research 16), the thresholds above. Anything tried beyond this list is
reported as a variant with its count.
