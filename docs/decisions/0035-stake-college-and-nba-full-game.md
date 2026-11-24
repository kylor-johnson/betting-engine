# 0035: College and NBA full-game picks are staked (2026-11-24)

Kylor, Nov 24, after asking why only the NFL full-game lane was bet: "option 1" (stake college and NBA full-game picks the same way as the
NFL). Replaces: decision 0022's "show" for NBA and college full-game and research 16's decision to keep them shown; the shown-only part of
0029 no longer applies to any lane today (the news-pick code stays for any lane set back to show). Every document that quoted the old rule
is updated in the same commit.

**Why this is a choice, not a result.** None of the three full-game scripts beats the closing line: the NFL's weight against the market fell
to zero for 2024-2026 (research 15), the NBA's lost (research 16) and the college script lost before and after research 23's upgrade. The
NFL lane is staked because Kylor chose to build its record with money (decision 0019). This applies the same choice to college and the NBA.

**What changes.** `playbook.sports.NBA.full_game` and `playbook.sports.College.full_game` = `stake`. Every A or B college and NBA full-game
pick, including CHECK picks the research agent clears, is staked and sent to Telegram under the existing rules: B = half a unit (college and
NBA unit $25), caps of 5 a week (college) and 2 a day (NBA), one unit a game, never into a move, CANCELLED on a big Pinnacle move. News still
moves the number by its unpriced part (0029).

**The risk, in units.** With no proven edge, each half-unit B pick costs about 0.02 units on average to Wagerhouse's margin: about 0.1 unit
a week at the college cap and about 0.3 a week at the NBA cap, with swings of about ±1 to 2 units a week. Each sport's stop (10 units down
since `live_since`) pauses it to paper; at this volume that can happen in a month on luck alone, and it is a pause for review, not a verdict.

**Yardstick.** Research 18's restart numbers, as for the NFL: closing-line value of +2.4 points of win chance on 100 picks; the charter's
review line (-1.5% on 25 graded) sends one Telegram line and a session review.
