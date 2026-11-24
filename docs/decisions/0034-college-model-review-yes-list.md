# 0034: The college model review's yes-list (2026-11-24)

Kylor, Nov 24, on research 23's eight items: "do it" (my advice: yes to 1, 2, 3, 4, 6 and 7; no to 5 and 8). Replaces: the college parts of
decision 0022 (the college script's inputs) and research 21's 3.5-point QB size where 0033 had not yet replaced it. Every document that
quoted the old rule is updated in the same commit.

1. **College QB value text.** The shared agent prompt and the parity note now say what the college guide already said (0033, item 5): a
   starter ruled out before the game is about 4 points, about 5 when he was the team's weak passer. The college script's comment no longer
   says the free CollegeFootballData tier has no play-level data (it has; research 23).
2. **Bowl-season college research runs** at 12:15 and 4:15 MT from Dec 14 to Jan 12 (`agent.extra_runs`), started by the hourly read when no
   college run has happened since the slot. Not in the launchd plist and not part of the missed-run check. Back to none if college news
   picks' closing-line value is below zero after 15 picks (a session decides; nothing switches it automatically).
3. **College openers on paper** (`picks/college_openers.py`, config `models.college_openers`, `docs/lanes/COLLEGE-OPENERS.md`). Every
   college game Wagerhouse posts gets our script's own number against Wagerhouse's first number; 3+ points on the side or 4+ on the total
   freezes a $0 paper pick at that number, graded on the move to the close and the result. Never sent. Kill: at 150 graded, an average
   move under 0.25 points or a record under 52.4% means turn it off with a decision note (the report says so).
4. **The college script uses per-play efficiency and tempo** (research 23's T1: PPA per play and success rate for and against, plays run
   and faced, one tempo term, garbage time removed), from cached CFBD advanced stats refreshed with the lines (`sources.cfbd_advanced`,
   one call per 12 hours). **Changed from the item as written:** item 4 said "trained on FBS against FBS games only". I checked that before
   switching: on FBS-against-FBS test games 2023-2026, training on FBS games only was no better than training on every lined game (squared
   error on team points 130.30 against 130.04, sides 262.94 against 261.83, totals 258.27 against 258.31; totals bets at 4+ 330-323 against
   382-356). So the live fit uses every lined game, exactly the model research 23 tested. The lane stays shown. Because a news pick is "news
   is what clears the bar", a different base number can change which news picks are issued; the money rules do not change. Kill: rerun the
   walk-forward in January with all of 2026; revert to points per game if the blend is worse than the old model's.
5. **No:** college full-game picks from the college script stay shown only, not staked like the NFL's (decision 0019). Revisit in August
   with item 3's record.
6. **College matchup and luck blocks** on the research agent's sheet (`models/college_context.py`): per-play efficiency, success rate,
   tempo, last four games, schedule toughness and points against efficiency, with FBS ranks. Context only; the college guide says they are
   never the reason to clear a CHECK. Remove if the agent cites them as one.
7. **2027 early-season test written down** in research 23 ("Pre-registered for 2027"). Paper only, judged on 2027 weeks 1 to 4.
8. **No:** no college props model (nothing to bet it at).
