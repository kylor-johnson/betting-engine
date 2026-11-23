## NBA guide

**What counts here.** Availability news that Wagerhouse has not priced: a rotation player ruled out or cleared, timestamped, ideally from the official NBA injury report or a team beat writer. That is the only NBA reason with evidence behind it. The closing line already carries rest, travel, back-to-backs and who is missing (docs/research/14-deep-review.md, 2d; docs/research/13-nba-absences.md), so their value is only in being early.

**Availability.** Run `uv run engine injuries --sport NBA` (add `--team <name>` to narrow it). For each flagged game, find which rotation players are out or questionable tonight and when that was published. A star out is worth roughly 3 to 6 points, a starter 1 to 2, a bench player about zero. Write `news_at` from the source; the engine counts only the part Pinnacle has not moved for since then, so size the entry as the full effect. Pinnacle prices back-to-backs; never add them. Every entry needs a real source link; remove entries for games already played.

**Props.** Never issue a prop in the decisions file: playbook prop picks are issued by code (B picks, real money).

**Playbook CHECK picks (PLAYBOOK.md, decision 0022).** Open `docs/cards/{{DAY}}-nba-playbook.md` (or the latest one). Each row marked CHECK clears the edge, but the model's number (team points from pace and efficiency, or a player's projection from minutes) is far from the market. For each one, find out whether the market knows something the model does not: a player ruled out, questionable, returning or on a minutes limit; a starter resting; a trade. The models know box scores and the official injury report, not tonight's coach's plan. Then write `docs/cards/decisions/{{DAY}}-nba-checks.yaml`:

```
checks:
  - key: "<the Key column, exactly>"
    verdict: clear        # nothing found that explains the gap: the pick is issued on the next read
    why: "<one sentence: what you checked>"
    source: "<a page you opened>"
  - key: "..."
    verdict: hold         # you found what the market knows (name it, with the time it was published)
    why: "..."
    source: "..."
```

Never write a number. Full-game NBA picks are shown only, not staked (research 16), so spend the time on prop CHECK rows first.
