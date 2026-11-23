# 0014: NFL Wong teasers, paper first (2026-11-23)

Kylor approved: "1. yes" to review 14's written case (docs/research/14-deep-review.md, sections 2f and 3).

**What.** A sixth lane, NFL Wong teasers (`src/engine/picks/teasers.py`, config `teasers:`, lane `nfl_teasers`). Every read freezes each NFL side at Wagerhouse that is a favorite of -7.5 to -8.5 or an underdog of +1.5 to +2.5, with the total at 49 or lower, at the first number seen. Legs are graded at the teased number (+6) and paired in first-seen order, within a week and across games, into 2-team tickets. The card is `docs/cards/<date>-nfl-teasers.md`; the record is on the status table and board.

**Why.** Wagerhouse pays -110 on a 2-team 6-point teaser (his tickets: to-win / risk 0.909), so a leg needs 72.4%. These legs won 75.8% on 264 legs in 2023-2026 and 75 to 79% in every era since 2010 (nflverse closes; `scripts/research14/teaser.py`). The rule dates from 2001, so those seasons are out of sample for it. It is the opposite of the 13-point teasers graded as a leak.

**Limits.** Paper only: no stake, no Telegram. Judged after 150 graded legs: under the break-even rate it is switched off (with a note, per the drift guard). Also off if Wagerhouse's 2-team 6-point price is no longer -110 (Kylor checks; `teasers.price` in config). After it passes, it follows the same staging as other picks. The "total 49 or lower" filter is kept as approved, but the sourced brief (14a) found it flat since 2015; the underdog legs carry most of the edge.

**Spec.** `CLAUDE.md`'s teaser rule now names the 6-point -110 teaser alongside the 6.5-point -120 one.
