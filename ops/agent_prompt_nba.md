## NBA guide

**What counts here.** Availability news that Wagerhouse has not priced: a rotation player ruled out or cleared, timestamped, ideally from the official NBA injury report or a team beat writer. That is the only NBA reason with evidence behind it. The closing line already carries rest, travel, back-to-backs and who is missing (docs/research/14-deep-review.md, 2d; docs/research/13-nba-absences.md), so their value is only in being early.

**Availability.** Run `uv run engine injuries --sport NBA` (add `--team <name>` to narrow it). For each flagged game, find which rotation players are out or questionable tonight and when that was published. A star out is worth roughly 3 to 6 points, a starter 1 to 2, a bench player about zero. Write `news_at` from the source; the engine counts only the part Pinnacle has not moved for since then, so size the entry as the full effect. Pinnacle prices back-to-backs; never add them. Every entry needs a real source link; remove entries for games already played.

**Props.** The NBA props model is testing only. Never issue a prop.
