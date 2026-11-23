# 0016: Research runs on change, one guide per sport, faster NBA and college reads (2026-11-23)

Kylor approved: "3. yes" (review 14, section 5, items 3, 4, 6 and 8).

- **Lag in minutes.** `engine wh-edge` section 4 times every Pinnacle move seen inside the fast-read windows (0.5 point in football, 1.0 in the NBA) and gives a keep / kill / too-early verdict against the rule in decision 0015.
- **College** joins the stale-number alerts (`stale.sports`; landing table from cached CollegeFootballData closes) and gets fast-read windows Friday 1-3:30pm and Saturday 7:30-10:30am and 11:30am-1:30pm Mountain.
- **NBA fast reads** now run from 2 hours before the day's first tip to 15 minutes after it (`burst.sports.NBA.before_first_start`), when the official report's Outs land, instead of three fixed windows. The 10am/3pm/5pm ESPN watcher is unchanged.
- **Run on change.** Fixed research runs cut to 8:15am daily and 6:45pm Sunday (NFL openers), from four on Sunday and two on other days. Runs still start on quarterback news, the NBA watcher, a new NFL slate, and now on any new stale number (for that sport, cooldown applies), from the hourly or the fast reads.
- **One guide per sport.** `ops/agent_prompt.md` is the shared part; `ops/agent_prompt_nfl.md`, `_college.md` and `_nba.md` say which reasons count in each sport. Matchup, luck and efficiency numbers are context, never a Bet reason on their own (every model built from them failed against the close). Removed false lines: the wind record "214-147 / 48-46" (not produced by any test), "ratings absorb 10% a week" (there are no ratings in the fair line), and "back-to-backs are in the sheet" (they are noted, not adjusted).

Nothing was switched off in a lane's inputs or models; the drift-guard table changes only by adding the teaser lane (decision 0014).
