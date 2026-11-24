# College playbook picks

How these are made: PLAYBOOK.md. Our team points come from the College game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.5). Full-game picks: shown only, not staked (its walk-forward test lost; Kylor can switch it on); except news picks, where sourced news Pinnacle has not priced is what clears the bar (staked, decision 0029). Props: off. Units: $25; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.

**Record:** no graded picks yet; 0 open.

## Issued (frozen at the number shown; $0 = paper)

None open.

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-college-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`; a clear also needs `because`, a positive reason the market is wrong, and `market_assumes`, what the current number already prices); a cleared one is issued and staked like any other B pick on the next read (decision 0027).

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Over 37 (-110) | Minnesota at Wisconsin | +4.7% | 39.0 / 37.5 / 41.6 | Shown only: College full-game picks are not staked (its walk-forward test lost; config playbook.sports.College.full_game). | `401858544|total|over` |
| Western Kentucky +3.5 (-110) | Kennesaw St at Western Kentucky | +4.6% | 2.6 / 3.0 / 1.2 | Shown only: College full-game picks are not staked (its walk-forward test lost; config playbook.sports.College.full_game). | `401870804|side|home` |
| Over 40 (-110) | North Dakota St at San Jose St | +4.3% | 42.1 / 41.0 / 44.1 | Shown only: College full-game picks are not staked (its walk-forward test lost; config playbook.sports.College.full_game). | `401864549|total|over` |
| Under 66.5 (-110) | Temple at Memphis | +4.2% | 63.4 / 65.5 / 59.4 | Shown only: College full-game picks are not staked (its walk-forward test lost; config playbook.sports.College.full_game). | `401862838|total|under` |
| South Florida -6.5 (-110) | Tulane at South Florida | +4.2% | -7.5 / -6.5 / -10.5 | Shown only: College full-game picks are not staked (its walk-forward test lost; config playbook.sports.College.full_game). | `401862839|side|home` |

## News on this card (adjustments.yaml)

No sourced news entries match games on this card. News is how a shown-only lane gets a staked pick, so an empty section in a busy news week is worth a look.
