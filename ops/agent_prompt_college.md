## College football guide

**What counts here.** Timestamped quarterback news (and, in bowl season, opt-outs and transfer-portal departures) that Wagerhouse has not priced. College has no model of its own: about 60 public rating systems were tested and add nothing against the close (docs/research/14-deep-review.md, 2c). Never cite a rating system as a reason.

**Availability.** There is no injury feed. For each flagged game, search for the starting quarterback's status and the conference availability report (SEC, Big Ten, Big 12, ACC publish them in the days before the game). In bowl season, search for opt-outs and portal entries among starters. A quarterback out is 3 to 7 points depending on the drop to the backup. Write `news_at` from the source. If you cannot confirm a status from a page you opened, do not enter it. Every entry needs a real source link; remove entries for games already played.

**Context, not reasons.** Weather, travel, motivation and "letdown spots" are context. None has a tested effect here; none makes a Bet on its own.


**Playbook CHECK picks (PLAYBOOK.md, decision 0022).** Open `docs/cards/{{DAY}}-college-playbook.md` (or the latest one). Each row marked CHECK clears the edge, but the college script's number (points scored and allowed so far) is far from the market. For each one, find out whether the market knows something the model does not: a quarterback out or returning, opt-outs and transfer-portal departures in bowl season, a coaching change, weather. Then write `docs/cards/decisions/{{DAY}}-college-checks.yaml`:

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

Never write a number. Full-game college picks are shown only, not staked (research 16); a clear verdict records your research but stakes nothing until Kylor switches college on.