## NFL guide

**What counts here.** Timestamped quarterback and injury news Wagerhouse has not priced, and the wind totals model. Practice participation and the injury report are already in the closing line by kickoff (docs/research/14-deep-review.md, 2a), so their value is only in being early: news from the last few hours that Wagerhouse has not followed. A starting quarterback newly out moved lines about 2.5 points during the week (14, 2b). **Size an entry for a starter out at 2.5 to 2.7 points** (measured over 669 games, 2023 to 2025); more needs a specific written reason, and the engine refuses an NFL entry larger than 3 points (decision 0036). The game script's own backup-quarterback flag is switched off while your entry is counted as unpriced news, so do not shrink the entry to allow for it.

**Availability.** Run `uv run engine injuries`. For every game, compare the quarterback situation with `adjustments.yaml`. A starting quarterback who is out, doubtful or newly back and not in the file gets an entry, with `news_at` from the source. The engine counts only the part Pinnacle has not moved for since `news_at`, so size the entry as the full effect; do not try to net out the market yourself. Remove entries for games already played and fix entries that are now wrong. Every entry needs a real source link. If two sources conflict, say so and use the more recent one.

**Outside opinions.** Do not rely on Sharp Football Analysis or any other pick seller. Never cite a published pick, a pick count or an outside "impact" score, and do not use their pages to size an injury. Cite the primary source (the official injury report, the play-by-play numbers on the sheet).

**Context, not reasons.** Each game has a `matchup` block (unit against unit from play-by-play; `uv run engine matchup AWAY HOME` prints it) and a `luck` block (fumble recovery share, turnover margin, red-zone rate, points per drive against success rate). Use them to explain why a line is where it is and to tell a real mispricing from a number the market moved for a reason. Quote numbers and ranks in the `matchup` reason. They are never the reason for a Bet. `efficiency_total_for_context_only` is never a reason for a totals pick.

**Wind.** When a total carries `model: wind`, the numbers flag it because of the tested wind model (record and its weakening since 2024: docs/research/05-model-first-picks.md and 14, 2e; quote only numbers you read there). It is a Conditional at most: issue it unless something sourced kills it (roof closed, game moved, forecast changed), with the condition "forecast still at or above <wind_mph rounded down> mph two hours before kickoff". Say plainly it is the wind model's pick.

**Playbook CHECK picks (PLAYBOOK.md, decision 0019).** Open `docs/cards/{{DAY}}-nfl-playbook.md` (or the latest one). Each row marked CHECK clears the edge, but the game-script model's own number is far from the market. For each one, find out whether the market knows something the model does not: a quarterback or key player out or returning, a suspension, a weather change, a team resting starters. The model only knows past play-by-play, the usual starter and the wind forecast. Then write `docs/cards/decisions/{{DAY}}-nfl-checks.yaml`:

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

Never write a number. A verdict on a game already played is ignored.

**Teasers.** The Wong-teaser lane runs in code (docs/cards/<date>-nfl-teasers.md) and sends its own tickets. Do not issue teasers in the decisions file.
