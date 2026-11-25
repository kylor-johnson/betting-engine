# NBA playbook picks

How these are made: PLAYBOOK.md. Our team points come from the NBA game-script model; our number is pulled toward the market at the playbook's starting weights (side 0.25, game total 0.35, team total 0.4, props 0.25). Full-game picks: staked. Props: staked. Units: $25; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.

**Record:** 3-3-0, +0.17 units at the grade's size (-0.26 staked), closing-line value -3.0% win chance; 2 open.

## Issued (frozen at the number shown; $0 = paper)

| Pick | Game | Grade | Stake | Don't bet past | Start (MT) | Why |
|---|---|---|---|---|---|---|
| Charlotte Hornets team total over 112.5 (-115) | Chicago Bulls at Charlotte Hornets | B | $12.5 | Charlotte Hornets team total over 113 | Wed 5:00 PM | our handicap Chicago Bulls 113.8, Charlotte Hornets 117.3 (market Chicago Bulls 109.1, Charlotte Hornets 112.4). Blended at the playbook weight, our team total number is 114.4 against Wagerhouse's 112.5; win chance 56.8% against 53.5% needed. |
| Los Angeles Clippers team total over 111 (-115) | Los Angeles Clippers at Memphis Grizzlies | B | $12.5 | Los Angeles Clippers team total over 111 | Wed 6:00 PM | our handicap Los Angeles Clippers 115.9, Memphis Grizzlies 120.3 (market Los Angeles Clippers 110.9, Memphis Grizzlies 117.6). Blended at the playbook weight, our team total number is 112.9 against Wagerhouse's 111; win chance 56.9% against 53.5% needed. |

## Best of the rest (C: shown, not staked)

CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in `docs/cards/decisions/<date>-nba-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`; a clear also needs `because`, a positive reason the market is wrong, and `market_assumes`, what the current number already prices); a cleared one is issued and staked like any other B pick on the next read (decision 0027).

| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |
|---|---|---|---|---|---|
| Over 218.5 (-110) | Chicago Bulls at Charlotte Hornets | +6.6% | 222.5 / 217.8 / 231.1 | CHECK held: Charlotte has Dennis Schroder (hamstring) out (Nov 24 15:32 MT), Grayson Allen questionable with a concussion (15:29 MT), Ryan Kalkbrenner doubtful (15:33 MT) and Kon Knueppel out since Nov 8. Chicago has Norman Powell and Caleb Wilson out and Jalen Smith questionable. The market total prices a thin lineup our script cannot see, and I found nothing saying it is wrong. | `401909318|total|over` |
| Over 215 (-110) | Sacramento Kings at Golden St Warriors | +5.8% | 218.5 / 215.2 / 224.6 | CHECK held: The market knows about missing players the NBA script cannot see. Golden State is without Stephen Curry (oblique tear, re-evaluated in two weeks, feed Nov 12 10:03 MT), Jimmy Butler, Kristaps Porzingis and Moses Moody. Brandon Williams (Nov 24 13:58 MT) and Yaxel Lendeborg (Nov 24 16:20 MT) are questionable. Sacramento has Maxime Raynaud out (Nov 24 21:21 MT). DraftKings' total fell from its opener, which fits that. I found nothing saying the low total is wrong. | `401909324|total|over` |
| Over 228 (-110) | Los Angeles Clippers at Memphis Grizzlies | +4.4% | 231.0 / 228.3 / 236.1 | CHECK: our number is far from the market; held until the research agent finds what the market knows | `401909321|total|over` |
| New York Knicks -4 (-110) | Cleveland Cavaliers at New York Knicks | +3.1% | -5.7 / -4.3 / -9.8 | CHECK held: New York has OG Anunoby (calf) and Jordan Clarkson (foot) out, and Karl-Anthony Towns, Josh Hart and Miles McBride questionable, all on the feed Nov 24 14:50 to 14:56 MT. Pinnacle is a shorter Knicks favorite than DraftKings' opener, so the market has moved for this. Our script cannot see who is injured, so the gap is the news, not an edge. | `401909319|side|home` |
| Over 223 (-110) | Minnesota Timberwolves at Oklahoma City Thunder | +1.7% | 224.9 / 223.0 / 228.4 | under the minimum edge | `401909320|total|over` |

## Props: best of the rest (C: shown, not staked)

| Prop | Game | Edge | Why | Note | Key |
|---|---|---|---|---|---|
| Cam Spencer over 9.5 Points (Pinnacle -123) | Los Angeles Clippers at Memphis Grizzlies | +3.1% | typical outcome 14 against a line of 9.5; chance over: ours 58%, Pinnacle 52%; out: Jerami Grant, Cameron Boozer (+6% on the projection) | under the minimum edge | `prop|4433083|pts|over|9.5|401909321` |
| Cam Spencer over 4.5 Assists (Pinnacle -151) | Los Angeles Clippers at Memphis Grizzlies | +2.4% | typical outcome 7 against a line of 4.5; chance over: ours 63%, Pinnacle 56%; out: Jerami Grant, Cameron Boozer (+6% on the projection) | under the minimum edge | `prop|4433083|ast|over|4.5|401909321` |
| Cam Spencer over 1.5 Threes Made (Pinnacle +112) | Los Angeles Clippers at Memphis Grizzlies | +2.2% | typical outcome 2 against a line of 1.5; chance over: ours 49%, Pinnacle 44% | under the minimum edge | `prop|4433083|fg3m|over|1.5|401909321` |
| Tyrese Proctor over 6.5 Points (Pinnacle -125) | Cleveland Cavaliers at New York Knicks | +2.1% | typical outcome 10 against a line of 6.5; chance over: ours 58%, Pinnacle 52% | under the minimum edge | `prop|5023693|pts|over|6.5|401909319` |
| Meleek Thomas over 7.5 Points (Pinnacle -146) | Cleveland Cavaliers at New York Knicks | +1.6% | typical outcome 11 against a line of 7.5; chance over: ours 61%, Pinnacle 55% | under the minimum edge | `prop|5041951|pts|over|7.5|401909319` |
| De'Aaron Fox under 25.5 Pts & Rebs & Asts (Pinnacle -144) | San Antonio Spurs at Portland Trail Blazers | +1.5% | typical outcome 18.1 against a line of 25.5; chance over: ours 39%, Pinnacle 45%; listed Questionable (official report); not adjusted | under the minimum edge | `prop|4066259|pra|under|25.5|401909325` |
| Isaiah Stewart under 3.5 Rebounds (Pinnacle +135) | Los Angeles Clippers at Memphis Grizzlies | +1.5% | typical outcome 3 against a line of 3.5; chance over: ours 56%, Pinnacle 60% | under the minimum edge | `prop|4432810|reb|under|3.5|401909321` |
| Kenrich Williams over 8.5 Points (Pinnacle +102) | Minnesota Timberwolves at Oklahoma City Thunder | +1.4% | typical outcome 10 against a line of 8.5; chance over: ours 51%, Pinnacle 46%; out: Jaylin Williams, Aday Mara (+5% on the projection) | under the minimum edge | `prop|3133626|pts|over|8.5|401909320` |
| Jaime Jaquez over 1.5 Threes Made (Pinnacle +137) | Brooklyn Nets at Milwaukee Bucks | +1.1% | typical outcome 1 against a line of 1.5; chance over: ours 43%, Pinnacle 39% | under the minimum edge | `prop|4432848|fg3m|over|1.5|401909322` |
| Jalen Brunson over 35.5 Pts & Rebs & Asts (Pinnacle -107) | Cleveland Cavaliers at New York Knicks | +1.0% | typical outcome 38.6 against a line of 35.5; chance over: ours 53%, Pinnacle 48%; out: OG Anunoby, Miles McBride (+8% on the projection) | under the minimum edge | `prop|3934672|pra|over|35.5|401909319` |

## News on this card (adjustments.yaml)

| Game | Entry | Counted? |
|---|---|---|
| Cleveland Cavaliers at New York Knicks | New York Knicks -1.5: OG Anunoby (calf) is out for Wednesday's game against Cleveland (Rotoworld relay via ESPN feed, Nov 24 14:53 MT). Starting forward out; NBA starter sized 1 to 2 | NO: not applied: no Pinnacle line stored from before the news, so it cannot be shown unpriced |

## Paper lanes ($0, not sent; decision 0036; record in docs/lanes/PAPER-LANES.md)

| Lane | Bet | Price | Why |
|---|---|---|---|
| Wagerhouse trailing Pinnacle | Over 220 (Chicago Bulls at Charlotte Hornets) | -110 | Wagerhouse 220, Pinnacle 221 |
| Wagerhouse trailing Pinnacle | Under 232.5 (Brooklyn Nets at Milwaukee Bucks) | -110 | Wagerhouse 232.5, Pinnacle 231.5 |
| Wagerhouse trailing Pinnacle | Under 229.5 (Los Angeles Clippers at Memphis Grizzlies) | -110 | Wagerhouse 229.5, Pinnacle 228.5 |
| Wagerhouse trailing Pinnacle | Under 223.5 (Phoenix Suns at Houston Rockets) | -110 | Wagerhouse 223.5, Pinnacle 222.5 |
| Wagerhouse trailing Pinnacle | Under 218 (Sacramento Kings at Golden St Warriors) | -110 | Wagerhouse 218, Pinnacle 217 |
| Wagerhouse trailing Pinnacle | Sacramento Kings +8.5 (Sacramento Kings at Golden St Warriors) | -110 | Wagerhouse -8.5, Pinnacle -7.5 (home spread) |
