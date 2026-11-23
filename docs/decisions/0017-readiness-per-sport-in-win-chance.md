# 0017: Readiness per sport, closing-line value as win chance; no new full-game models (2026-11-23)

Kylor approved: "3. yes" (review 14, section 5, items 7 and 12).

**Readiness.** `engine ready` now judges NFL, College and NBA separately (`go_live.per_sport`): NFL and College need 10 graded Bets and Conditionals with 5 closing lines; NBA needs 25 with 15, because NBA picks arrive in days. Closing-line value is measured as win chance against Pinnacle's close (`src/engine/clv.py`; stored as `clv_chance` on graded picks and stale alerts): the floor is 0.0 and the pause line is -1.5% (about half a point in the NFL) once 25 picks in a sport have a close. Points are still stored and shown. The stages, the half unit and the 2-unit weekly cap are unchanged. Changing `go_live` restarts nothing (it is not a pick-deciding setting).

**No new full-game models.** Eight models built from public data have failed against the closing line (sides from ratings, play-by-play, pace totals, first-half habits, openers, the NFL injury report with practice status, college rating systems, NBA rest and travel). No session builds another full-game sides or totals model unless it brings a new kind of input the close demonstrably lacks, written up first. Amends decision 0005.
