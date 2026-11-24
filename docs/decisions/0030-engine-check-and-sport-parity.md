# 0030: engine check, news you can see, and one shape for all three sports (2026-11-23, night)

Replaces: none. Extends decision 0029 (NBA news picks on).

Kylor: "do it, if the CFB model is in the same shape as what you are building for NFL as it seems we keep losing focus between all three
sports..."

- **Sport parity table** (`parity:` in config.yaml, printed in `docs/lanes/STATUS.md`): the same components for NFL, college and NBA (game
  script, player value, news source, weather, props model, teasers, research-agent guide, plus money state, props and news-pick switches read
  from config). Every cell is live, testing, failed, not_buildable, not_applicable or planned, with a note. A blank is a failed check.
  **Rule for sessions:** anything built for one sport says in the same commit what the other two get, or updates their parity cell with the
  reason they don't.
- **NBA news picks on** (`playbook.sports.NBA.news_picks: true`), same as college: NBA full-game picks are shown only, so a side or total is
  staked only when sourced news Pinnacle has not priced is what clears the bar. Parity with college; NFL full-game is staked anyway.
- **`engine check`** (`src/engine/checks.py`, `docs/lanes/CHECKS.md`): the charter's "What working looks like" as ten checks (staked picks
  delivered, no $0 pick sent as a bet, limits, grading on time, every lane in season has a recent candidate, STATUS fresh, stops, scheduled
  reads and research runs, session lock, parity), plus a warning row for news entries without `news_at`. Runs on the first hourly read after
  7am; one Telegram `system` line only when something fails.
- **News you can see:** every playbook card ends with "News on this card": each `adjustments.yaml` entry for its games and whether it counted,
  and why not. `engine news [--sport]` prints the same for the research agent, which now runs it after any change to `adjustments.yaml` and
  fixes entries without `news_at` (step 4 of `ops/agent_prompt.md`). Tonight two NFL quarterback entries (Maye, Jackson) count for nothing
  because they have no `news_at`.

Tests: `tests/test_checks_parity.py`.
