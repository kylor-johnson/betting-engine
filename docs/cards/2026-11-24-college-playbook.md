# College playbook picks

How these are made: PLAYBOOK.md. Our team points come from the College game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.5). Full-game picks: staked. Props: off. Units: $25; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.

**Record:** no graded picks yet; 10 open.

## Issued (frozen at the number shown; $0 = paper)

| Pick | Game | Grade | Stake | Don't bet past | Start (MT) | Why |
|---|---|---|---|---|---|---|
| Akron +7.5 (-110) | Buffalo at Akron | B | $12.5 | Akron +7 | Fri 10:00 AM | our handicap Buffalo 27.4, Akron 24.0 (market Buffalo 28.0, Akron 21.0). Blended at the playbook weight, our side number is 6.1 against Wagerhouse's 7.5; win chance 57.8% against 52.4% needed. |
| Over 37 (-110) | Minnesota at Wisconsin | B | $12.5 | Over 37.5 | Fri 5:30 PM | our handicap Minnesota 15.4, Wisconsin 25.4 (market Minnesota 15.0, Wisconsin 22.5). Blended at the playbook weight, our total number is 38.7 against Wagerhouse's 37; win chance 56.8% against 52.4% needed. |
| Over 38.5 (-110) | Michigan at Ohio St | B | $12.5 | Over 39.5 | Sat 10:00 AM | our handicap Michigan 15.5, Ohio St 29.5 (market Michigan 14.2, Ohio St 24.2). Blended at the playbook weight, our total number is 40.8 against Wagerhouse's 38.5; win chance 56.5% against 52.4% needed. |
| Western Kentucky +3.5 (-110) | Kennesaw St at Western Kentucky | B | paper | Western Kentucky +3.5 | Sat 11:00 AM | our handicap Kennesaw St 27.8, Western Kentucky 26.2 (market Kennesaw St 28.0, Western Kentucky 25.0). Blended at the playbook weight, our side number is 2.7 against Wagerhouse's 3.5; win chance 56.5% against 52.4% needed. |
| Virginia +3 (-110) | Virginia at Virginia Tech | B | paper | Virginia +3 | Sat 1:00 PM | our handicap Virginia 27.3, Virginia Tech 24.4 (market Virginia 24.5, Virginia Tech 27.5). Blended at the playbook weight, our side number is -1.5 against Wagerhouse's -3; win chance 55.9% against 52.4% needed. |
| South Florida -6.5 (-110) | Tulane at South Florida | B | $12.5 | South Florida -7 | Sat 1:30 PM | our handicap Tulane 20.3, South Florida 32.0 (market Tulane 18.2, South Florida 24.8). Blended at the playbook weight, our side number is -7.8 against Wagerhouse's -6.5; win chance 57.8% against 52.4% needed. |
| Under 61.5 (-110) | SMU at Stanford | B | paper | Under 61 | Sat 1:30 PM | our handicap SMU 29.8, Stanford 25.9 (market SMU 34.5, Stanford 26.5). Blended at the playbook weight, our total number is 59.2 against Wagerhouse's 61.5; win chance 56.1% against 52.4% needed. |
| Rutgers +3 (-110) | Michigan St at Rutgers | B | paper | Rutgers +3 | Sat 2:15 PM | our handicap Michigan St 23.7, Rutgers 26.0 (market Michigan St 25.8, Rutgers 22.2). Blended at the playbook weight, our side number is 2.0 against Wagerhouse's 3; win chance 55.6% against 52.4% needed. |
| Washington St -2.5 (-110) | San Diego St at Washington St | B | $12.5 | Washington St -3 | Sat 4:30 PM | our handicap San Diego St 22.9, Washington St 28.9 (market San Diego St 21.5, Washington St 24.5). Blended at the playbook weight, our side number is -3.7 against Wagerhouse's -2.5; win chance 59.7% against 52.4% needed. |
| Over 47 (-110) | Pittsburgh at California | B | paper | Over 47.5 | Sat 5:30 PM | our handicap Pittsburgh 28.6, California 22.9 (market Pittsburgh 28.5, California 19.0). Blended at the playbook weight, our total number is 48.9 against Wagerhouse's 47; win chance 55.7% against 52.4% needed. |

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-college-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`; a clear also needs `because`, a positive reason the market is wrong, and `market_assumes`, what the current number already prices); a cleared one is issued and staked like any other B pick on the next read (decision 0027).

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Under 67 (-110) | Temple at Memphis | +4.1% | 63.7 / 65.5 / 60.3 | Not issued: Pinnacle moved 1 against this side since we first priced it (64.5 to 65.5). | `401862838|total|under` |
| Over 46.5 (-110) | UAB at North Texas | +6.7% | 50.6 / 46.0 / 59.1 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401862843|total|over` |
| Georgia Tech +36 (-110) | Georgia Tech at Georgia | +6.6% | -32.6 / -35.5 / -23.7 | CHECK held: I searched for Georgia Tech and Georgia quarterback news for this game and found no current injury report for either side. A November AJC preview names Lincoln Kienholz as Georgia Tech's starter. Finding nothing is a hold. | `401856760|side|away` |
| Clemson +5.5 (-110) | South Carolina at Clemson | +5.8% | 2.8 / 5.5 / -5.2 | CHECK held: The market knows what the points-based model cannot see. Clemson's starting quarterback Tait Reynolds tore his left meniscus against Georgia Tech on Nov 14 and is out for the season (WCSC Live5, Nov 15, 3:51 PM ET). Christopher Vizzina left that game with a concussion and was already playing through an injury, and senior Trent Pearman was next in line. Clemson's points so far were scored mostly with a quarterback who will not play, so a home underdog price with a third-string-level room is what you would expect. | `401856764|side|home` |
| Over 45.5 (-110) | Connecticut at Wyoming | +4.9% | 48.5 / 46.0 / 53.2 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401861969|total|over` |

## News on this card (adjustments.yaml)

No sourced news entries match games on this card. News is how a shown-only lane gets a staked pick, so an empty section in a busy news week is worth a look.
