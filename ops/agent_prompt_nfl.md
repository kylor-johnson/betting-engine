## NFL guide

**What counts here.** Timestamped quarterback and injury news Wagerhouse has not priced, and the wind totals model. Practice participation and the injury report are already in the closing line by kickoff (docs/research/14-deep-review.md, 2a), so their value is only in being early: news from the last few hours that Wagerhouse has not followed. A starting quarterback newly out moved lines about 2.5 points during the week (14, 2b).

**Availability.** Run `uv run engine injuries`. For every game, compare the quarterback situation with `adjustments.yaml`. A starting quarterback who is out, doubtful or newly back and not in the file gets an entry, with `news_at` from the source. The engine counts only the part Pinnacle has not moved for since `news_at`, so size the entry as the full effect; do not try to net out the market yourself. Remove entries for games already played and fix entries that are now wrong. Every entry needs a real source link. If two sources conflict, say so and use the more recent one.

**Outside opinions.** Do not rely on Sharp Football Analysis or any other pick seller. Never cite a published pick, a pick count or an outside "impact" score, and do not use their pages to size an injury. Cite the primary source (the official injury report, the play-by-play numbers on the sheet).

**Context, not reasons.** Each game has a `matchup` block (unit against unit from play-by-play; `uv run engine matchup AWAY HOME` prints it) and a `luck` block (fumble recovery share, turnover margin, red-zone rate, points per drive against success rate). Use them to explain why a line is where it is and to tell a real mispricing from a number the market moved for a reason. Quote numbers and ranks in the `matchup` reason. They are never the reason for a Bet. `efficiency_total_for_context_only` is never a reason for a totals pick.

**Wind.** When a total carries `model: wind`, the numbers flag it because of the tested wind model (record and its weakening since 2024: docs/research/05-model-first-picks.md and 14, 2e; quote only numbers you read there). It is a Conditional at most: issue it unless something sourced kills it (roof closed, game moved, forecast changed), with the condition "forecast still at or above <wind_mph rounded down> mph two hours before kickoff". Say plainly it is the wind model's pick.

**Teasers.** The paper Wong-teaser lane runs in code (docs/cards/<date>-nfl-teasers.md). Do not issue teasers in the decisions file.
