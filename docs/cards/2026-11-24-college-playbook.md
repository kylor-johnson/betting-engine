# College playbook picks

How these are made: PLAYBOOK.md. Our team points come from the College game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.5). Full-game picks: shown only, not staked (its walk-forward test lost; Kylor can switch it on); except news picks, where sourced news Pinnacle has not priced is what clears the bar (staked, decision 0029). Props: off. Units: $25; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.

**Record:** no graded picks yet; 0 open.

## Issued (frozen at the number shown; $0 = paper)

None open.

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-college-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`; a clear also needs `because`, a positive reason the market is wrong, and `market_assumes`, what the current number already prices); a cleared one is issued and staked like any other B pick on the next read (decision 0027).

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Clemson +5.5 (-110) | South Carolina at Clemson | +9.1% | 2.2 / 5.5 / -7.6 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401856764|side|home` |
| Rutgers +3.5 (-110) | Michigan St at Rutgers | +8.0% | 1.7 / 3.5 / -3.9 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401858542|side|home` |
| Georgia Tech +36 (-110) | Georgia Tech at Georgia | +6.5% | -32.8 / -35.5 / -24.6 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401856760|side|away` |
| Over 43 (-110) | Tulane at South Florida | +5.5% | 46.1 / 43.0 / 51.9 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401862839|total|over` |
| Over 37 (-110) | Minnesota at Wisconsin | +4.7% | 39.0 / 37.5 / 41.6 | Shown only: College full-game picks are not staked (its walk-forward test lost; config playbook.sports.College.full_game). | `401858544|total|over` |

## News on this card (adjustments.yaml)

No sourced news entries match games on this card. News is how a shown-only lane gets a staked pick, so an empty section in a busy news week is worth a look.
