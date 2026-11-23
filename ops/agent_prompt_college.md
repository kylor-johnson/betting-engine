## College football guide

**What counts here.** Timestamped quarterback news (and, in bowl season, opt-outs and transfer-portal departures) that Wagerhouse has not priced. College has no model of its own: about 60 public rating systems were tested and add nothing against the close (docs/research/14-deep-review.md, 2c). Never cite a rating system as a reason.

**Availability.** There is no injury feed. For each flagged game, search for the starting quarterback's status and the conference availability report (SEC, Big Ten, Big 12, ACC publish them in the days before the game). In bowl season, search for opt-outs and portal entries among starters. A quarterback out is 3 to 7 points depending on the drop to the backup. Write `news_at` from the source. If you cannot confirm a status from a page you opened, do not enter it. Every entry needs a real source link; remove entries for games already played.

**Context, not reasons.** Weather, travel, motivation and "letdown spots" are context. None has a tested effect here; none makes a Bet on its own.


**Playbook CHECK picks (PLAYBOOK.md, decision 0022).** Open `docs/cards/{{DAY}}-college-playbook.md` (or the latest one). Each row marked CHECK clears the edge, but the college script's number (points scored and allowed so far) is far from the market. For each one, find out whether the market knows something the model does not: a quarterback out or returning, opt-outs and transfer-portal departures in bowl season, a coaching change, weather. Then write `docs/cards/decisions/{{DAY}}-college-checks.yaml`:

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

Never write a number. Full-game college picks are shown only, not staked (research 16); a clear verdict records your research but stakes nothing until Kylor switches college on.