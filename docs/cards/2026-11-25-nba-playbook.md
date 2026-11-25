# NBA playbook picks

How these are made: PLAYBOOK.md. Our team points come from the NBA game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.25). Full-game picks: staked. Props: staked. Units: $25; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.

**Record:** 3-3-0, +0.17 units at the grade's size (-0.26 staked), closing-line value -3.0% win chance; 1 open.

## Issued (frozen at the number shown; $0 = paper)

| Pick | Game | Grade | Stake | Don't bet past | Start (MT) | Why |
|---|---|---|---|---|---|---|
| Los Angeles Clippers team total over 111 (-115) | Los Angeles Clippers at Memphis Grizzlies | B | $12.5 | Los Angeles Clippers team total over 111 | Wed 6:00 PM | our handicap Los Angeles Clippers 115.9, Memphis Grizzlies 120.3 (market Los Angeles Clippers 110.9, Memphis Grizzlies 117.6). Blended at the playbook weight, our team total number is 112.9 against Wagerhouse's 111; win chance 56.9% against 53.5% needed. |

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-nba-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`; a clear also needs `because`, a positive reason the market is wrong, and `market_assumes`, what the current number already prices); a cleared one is issued and staked like any other B pick on the next read (decision 0027).

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Over 217 (-110) | Sacramento Kings at Golden St Warriors | +4.6% | 220.1 / 217.7 / 224.6 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401909324|total|over` |
| New York Knicks -3 (-110) | Cleveland Cavaliers at New York Knicks | +3.8% | -4.7 / -3.0 / -9.8 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401909319|side|home` |
| Over 222 (-110) | Chicago Bulls at Charlotte Hornets | +3.7% | 224.6 / 221.0 / 231.1 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401909318|total|over` |
| Under 225.5 (-110) | San Antonio Spurs at Portland Trail Blazers | +2.1% | 223.5 / 225.1 / 220.5 | under the minimum edge | `401909325|total|under` |
| Over 222.5 (-110) | Minnesota Timberwolves at Oklahoma City Thunder | +1.6% | 224.3 / 222.0 / 228.4 | under the minimum edge | `401909320|total|over` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| Meleek Thomas over 7.5 Points (Pinnacle -136) | Cleveland Cavaliers at New York Knicks | +2.4% | typical outcome 11.9 against a line of 7.5; chance over: ours 60%, Pinnacle 54% | under the minimum edge | `prop|5041951|pts|over|7.5|401909319` |
| Josh Giddey over 8.5 Assists (Pinnacle -105) | Chicago Bulls at Charlotte Hornets | +1.6% | typical outcome 9 against a line of 8.5; chance over: ours 53%, Pinnacle 48%; out: Norman Powell (+6% on the projection) | under the minimum edge | `prop|4871145|ast|over|8.5|401909318` |
| Meleek Thomas over 1.5 Threes Made (Pinnacle +108) | Cleveland Cavaliers at New York Knicks | +1.2% | typical outcome 2 against a line of 1.5; chance over: ours 49%, Pinnacle 45% | under the minimum edge | `prop|5041951|fg3m|over|1.5|401909319` |
| Darius Garland over 18.5 Points (Pinnacle -110) | Los Angeles Clippers at Memphis Grizzlies | +1.1% | typical outcome 20.9 against a line of 18.5; chance over: ours 54%, Pinnacle 49% | under the minimum edge | `prop|4396907|pts|over|18.5|401909321` |
| Mikel Brown under 16.5 Points (Pinnacle -128) | Brooklyn Nets at Milwaukee Bucks | +0.7% | typical outcome 12 against a line of 16.5; chance over: ours 43%, Pinnacle 47%; out: Nolan Traore (+3% on the projection) | under the minimum edge | `prop|5101761|pts|under|16.5|401909322` |
| Brook Lopez over 12.5 Points (Pinnacle +106) | Los Angeles Clippers at Memphis Grizzlies | +0.6% | typical outcome 14 against a line of 12.5; chance over: ours 49%, Pinnacle 45% | under the minimum edge | `prop|3448|pts|over|12.5|401909321` |
| Grayson Allen over 12.5 Points (Pinnacle -114) | Chicago Bulls at Charlotte Hornets | +0.5% | typical outcome 14 against a line of 12.5; chance over: ours 54%, Pinnacle 50%; out: Ryan Kalkbrenner; listed Questionable (official report); not adjusted (+2% on the projection) | under the minimum edge | `prop|3135045|pts|over|12.5|401909318` |
| Kenrich Williams over 8.5 Points (Pinnacle -114) | Minnesota Timberwolves at Oklahoma City Thunder | +0.4% | typical outcome 10 against a line of 8.5; chance over: ours 54%, Pinnacle 50%; out: Jaylin Williams, Aday Mara (+5% on the projection) | under the minimum edge | `prop|3133626|pts|over|8.5|401909320` |
| James Harden over 2.5 Threes Made (Pinnacle +118) | Cleveland Cavaliers at New York Knicks | +0.4% | typical outcome 3 against a line of 2.5; chance over: ours 46%, Pinnacle 43% | under the minimum edge | `prop|3992|fg3m|over|2.5|401909319` |
| Zach Edey over 8.5 Points (Pinnacle -118) | Los Angeles Clippers at Memphis Grizzlies | +0.4% | typical outcome 10 against a line of 8.5; chance over: ours 54%, Pinnacle 51%; out: Cameron Boozer, Jerami Grant (+6% on the projection) | under the minimum edge | `prop|4600663|pts|over|8.5|401909321` |

## News on this card (adjustments.yaml)

No sourced news entries match games on this card. News is how a shown-only lane gets a staked pick, so an empty section in a busy news week is worth a look.

## Paper lanes ($0, not sent; decision 0036; record in docs/lanes/PAPER-LANES.md)

| Lane | Bet | Price | Why |
|---|---|---|---|
| Wagerhouse trailing Pinnacle | Under 232.5 (Brooklyn Nets at Milwaukee Bucks) | -110 | Wagerhouse 232.5, Pinnacle 231.5 |
| Wagerhouse trailing Pinnacle | Under 229.5 (Los Angeles Clippers at Memphis Grizzlies) | -110 | Wagerhouse 229.5, Pinnacle 228.5 |
| Wagerhouse trailing Pinnacle | Under 223.5 (Phoenix Suns at Houston Rockets) | -110 | Wagerhouse 223.5, Pinnacle 222.5 |
| Wagerhouse trailing Pinnacle | Under 218 (Sacramento Kings at Golden St Warriors) | -110 | Wagerhouse 218, Pinnacle 217 |
