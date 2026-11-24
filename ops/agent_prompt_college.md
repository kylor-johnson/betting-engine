## College football guide

**What counts here.** Timestamped quarterback news (and, in bowl season, opt-outs and transfer-portal departures) that Wagerhouse has not priced. College has no model of its own: about 60 public rating systems were tested and add nothing against the close (docs/research/14-deep-review.md, 2c). Never cite a rating system as a reason.

**News is how college bets get made (decision 0029).** College has no model that beats the close, so its picks come from news the market has not
priced. Every sourced entry you add to `adjustments.yaml` (with `news_at`) moves the playbook's number for that game, but only by the part
Pinnacle has not moved for since `news_at`. When that unpriced part is what takes a side or total over the bar, the playbook issues a staked
**news pick** and sends it to Telegram. So: every quarterback change, every starter opt-out or portal exit you can source, with the time it
broke, goes in `adjustments.yaml` the same run you find it. Speed is the edge: an entry written after Pinnacle has moved counts for nothing.
Look first at the games on the college playbook card and the busiest windows (Friday afternoon availability reports, Saturday mornings,
bowl opt-out announcements).

**Availability.** There is no injury feed. Search every game on this week's slate, not only flagged ones, for the starting quarterback's status and the conference availability report (SEC, Big Ten, Big 12, ACC publish them in the days before the game). In bowl season, search for opt-outs and portal entries among starters. A starter out is worth about 3.5 points to the market (Power 4 about 3, Group of 5 about 4; research 21). Going above 5 needs a specific written reason. Do not add points for a star: missing high-efficiency starters were discounted less, not more. Only about 0.9 points of a starter change usually moves after the opener, so the entry is worth something only if Pinnacle has not moved yet. Write `news_at` from the source. If you cannot confirm a status from a page you opened, do not enter it. Every entry needs a real source link; remove entries for games already played.

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