## NBA guide

**What counts here.** Availability news that Wagerhouse has not priced: a rotation player ruled out or cleared, timestamped, ideally from the official NBA injury report or a team beat writer. That is the only NBA reason with evidence behind it. The closing line already carries rest, travel, back-to-backs and who is missing (docs/research/14-deep-review.md, 2d; docs/research/13-nba-absences.md), so their value is only in being early.

**Availability.** Run `uv run engine injuries --sport NBA` (add `--team <name>` to narrow it). For each flagged game, find which rotation players are out or questionable tonight and when that was published. A star out is worth roughly 3 to 4 points, a starter 1 to 2, a bench player about zero (not measured). The engine refuses an NBA entry larger than 4 points (decision 0036). Write `news_at` from the source; the engine counts only the part Pinnacle has not moved for since then, so size the entry as the full effect. Pinnacle prices back-to-backs; never add them. Every entry needs a real source link; remove entries for games already played.

**News (decisions 0029, 0035).** NBA full-game picks are staked since decision 0035 (Kylor's choice), and sourced news Pinnacle has not priced moves their number. Every starter ruled out or returning that you can source, with the time it broke (`news_at`), goes in `adjustments.yaml` the same run; then run `uv run engine news --sport NBA`. Speed is the edge: an entry after Pinnacle moved counts for nothing.

**Props.** Never issue a prop in the decisions file: playbook prop picks are issued by code (B picks, paper at $0 since decision 0038).

**Playbook CHECK picks (PLAYBOOK.md, decision 0022).** Open `docs/cards/{{DAY}}-nba-playbook.md` (or the latest one). Each row marked CHECK clears the edge, but the model's number (team points from pace and efficiency, or a player's projection from minutes) is far from the market. For each one, find out whether the market knows something the model does not: a player ruled out, questionable, returning or on a minutes limit; a starter resting; a trade. The models know box scores and the official injury report, not tonight's coach's plan. Then write `docs/cards/decisions/{{DAY}}-nba-checks.yaml`:

```
checks:
  - key: "<the Key column, exactly>"
    verdict: clear        # ONLY with a positive, sourced reason the market is wrong (decision 0025)
    because: "<what you found that the market has wrong, with when it was published>"
    market_assumes: "<what the current number already prices: who it assumes plays, which news it has already moved for>"
    why: "<one sentence: what you checked>"
    source: "<a page you opened, https://...>"
  - key: "..."
    verdict: hold         # you found what the market knows (name it, with the time it was published), OR you found nothing
    why: "..."
    source: "..."
```

**"I found nothing" is a hold, not a clear.** A CHECK row means the model is far from a market that is usually right, and the model cannot
see most news, so finding nothing is what you would expect when the gap is noise. The code ignores a clear without `because`,
`market_assumes` and a source link, or whose `because` says nothing was found. A cleared pick is staked and sent like any other B pick
(decision 0027), so clear only what you would put money on.

Never write a number. Full-game NBA picks are staked (decision 0035), so a clear verdict puts money on the pick: clear only what you would bet.
