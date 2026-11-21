# Phase 0: Red-team of the betting engine plan

Written 2026-11-21 (Mountain). Nothing has been built. This document is for you to approve, edit or kill.

How to read the confidence in this document: most figures were read on the source page during this research. Where a figure is from memory, a search snippet, or my own arithmetic, the text says so. A few things could not be found at all and are listed as gaps, not papered over.

## Verdict

The draft spec has the right first instinct (log odds and measure closing line value before modeling) and the wrong center of gravity. It spends four of five phases on building your own models, and the evidence says a one-person public-data model almost never beats NFL, CFB or NBA closing lines: in the 2024 college football season not one of 55 tracked computer systems beat the closing line against the spread at a profitable rate, and the best NFL public model (nfelo) is within 0.01 points of the close on average error. The edge that is actually documented for individuals is price, not prediction: betting a slow book's number when it is better than a sharp book's fair price, worth roughly 2 to 4% in multi-book studies. Your situation has one hard problem the spec skips: you bet at a single pay-per-head book that no feed carries, so nobody, including you, knows yet whether its lines lag the market, by how long, or in which direction it shades. That is the first thing to measure, and it costs almost nothing. The second finding is about your current betting: on published numbers, 13-point teasers (about −16% per ticket), moneyline parlays of big favorites (about −10 to −15%), same-game stacks (−10 to −20% or worse) and most bought points are leaks, and a +$1,640 run over 145 bets cannot tell you otherwise. So the revised plan is: first audit the 145 bets you already made against sharp prices (days, not weeks), then run a small logger and alert system built around your book and the fixed times lines open, and only build models later, as a tool for deciding which openers to look at first, blended with the market rather than competing with it.

## 1. Is the approach sound, and where is the edge?

**Sound in principle, with honest economics.** A good bettor sustains about 2 to 4% return on money wagered. At $25 a bet and 1,000 bets a year, a true 3% edge is about +$750 expected, with a swing of about ±$755 from luck alone (my arithmetic). The odds feed will cost $360 to $700 a year. This system will not pay for itself through new winnings at this stake size. It pays for itself by stopping leaks, which are much larger than any edge you will find (section 4), and by telling you the truth about whether you have an edge before you raise stakes.

**How long until results mean anything.** At standard −110 pricing:

| Bets | Luck swing in return | Chance a true 54% bettor is still losing |
|---|---|---|
| 145 | ±7.9% | 35% |
| 500 | ±4.3% | 23% |
| 1,000 | ±3.0% | 15% |
| 2,500 | ±1.9% | 5% |

It takes about 1,450 bets for a true 55% bettor's results to clearly separate from break-even, and about 3,800 for a 54% bettor. This is why the system has to measure price quality (did you beat the sharp closing price), which settles in hundreds of bets, and not just wins and losses.

**Ranking: realistic edge against build effort, for one book and $25 units.**

| Rank | Where | Realistic edge | Effort | The catch |
|---|---|---|---|---|
| 1 | Stop the negative bets (section 4) | Saves 10 to 16% on the money now going into those bets | None | Requires accepting the math over a hot streak |
| 2 | Price shopping against a sharp fair line, no model | 2 to 4% in multi-book studies; recent realized results about half of expected | Low | All the sourced numbers are soccer and golf with many books. With one book you get a fraction of the chances. Adding even two legal Colorado books changes this more than any code |
| 3 | Teasers done correctly (Wong legs only) | About break-even to +5% at −120, negative at −130 or worse | Low | Depends entirely on your book's pay table, which I do not have |
| 4 | Player props, comparing your book to a consensus of other books | Softest market by practitioner agreement; no measured return found | Medium | No sharp reference book for props, closing line value "doesn't mean anything in props" (Unabated), winners get limited fast |
| 5 | Derivatives (first half, team totals, alt lines) | Unknown. Only unsourced claims of formula pricing | Medium | No data either way. Alt lines through 3 and 7 are occasionally mispriced |
| 6 | Early-week openers | Real at the market-making book, unknown at yours | Medium | See below |
| 7 | Small-conference CFB | Unknown. The logic (low limits, less attention) is sound; I found no measurement | High | Needs a model with preseason priors |
| 8 | Your own model against mainline closing spreads and totals | About zero before the vig | Very high | Section 3 |

**On openers, which is your stated problem.** The opener at Circa is a deliberately soft number posted at low limits ($3,000 on Sunday against about $40,000 by Saturday) so sharp groups can correct it; Circa's own bookmaker says "I value my opinion for about two seconds, until the bettors start to go." Closing lines are measurably more accurate than openers (college football average error 12.31 at open against 11.78 at close this season). So yes, early numbers are weaker. Three cautions:

- You cannot bet Circa's opener. What matters is whether your book copies that number before or after it gets corrected. Some local books post lines late specifically to avoid early sharp money. Nothing published answers this for your book.
- About three-quarters of NFL games move 1.5 points or less from open to close. The value is in the roughly 25% that move 2 points or more, and it exists only before the move. After a move is complete, the direction it went predicts nothing.
- A line having moved does not prove the early number was good for you. In the one large study of this (Buchdahl, October 2026, 62,000 bets, not football), most "value" logged more than 24 hours out at low limits did not hold up at the close.

## 2. What the best actually do

**Billy Walters.** Power ratings updated as 90% old rating plus 10% latest true performance. Quarterback worth about a touchdown, top non-quarterbacks 2.5 to 3 points, most players about zero; clusters of injuries at one position group matter more than single ones. Home field now under 1 point, down from the traditional 3. Prices half points by key number (3 highest, then 6, 7, 14). Bets 1 to 3% of bankroll scaled to edge. Favorites early, underdogs late. What does not transfer: he ran rooms of staff 14 hours a day and proxies betting millions a week. (His exact half-point chart is from memory here, not verified: 3 = 8%, 7 = 6%, 6 and 14 = 5%, 10 = 4%.)

**Collin Wilson.** Ratings built from advanced metrics, coaching changes and roster continuity. The repeatable part: after each game he moves both teams toward where the closing line had them, with only a small adjustment for the result. Havoc (tackles for loss, forced fumbles, passes defended as a rate) matched against havoc allowed. Success rate over raw results. Turnover margin treated as luck that will reverse, which is the "buy low, sell high" idea.

**Haralabos Voulgaris.** Early edge was one structural flaw (books split NBA totals evenly by half). Books fixed it and he lost a third of his bankroll in a month. Then a possession-level simulation built with a full-time quant over two years, plus a separate model for lineups and minutes. Returns of 5 to 6% on 1,000+ bets a season, and his own summary: "My capability to make money is decreasing every year."

**Rufus Peabody.** The most copyable. He does not trust his model over the market: his blend is 45% model, 55% market. He needs about a 2-point gap in the NFL before betting. He concedes injuries to the market. For props he projects game flow, then usage, then the full distribution, and notes books price the median. Models decay (his old baseball model "wouldn't make money now"). His first advice for small bettors is line shopping.

**Alan Boston.** Feel and program knowledge, college basketball. Does not chase closing line value: if the market always moves your way, you are doing what everyone else does.

**Abnormally Distributed.** Anonymous, machine-learning PhD, originates in golf and NFL props. Says he cannot beat NFL sides on Sunday morning, so he works early in the week in small markets. Asks why a market moved, and admits he moves the smallest ones himself.

**Bill Benter.** The modeling discipline, from his 1994 paper. Never bet the raw model: combine it with the public odds in a second step, because the raw model is wrong in the public's direction whenever they disagree. Judge a model by what it adds on top of the market, not by its accuracy alone (a tipster model as accurate as his added almost nothing). Test only on data the model never saw. Full Kelly is "unwise" because overestimating your edge by 2x turns growth negative; use a half or a third.

**Ed Feng.** Ratings from margin of victory adjusted for schedule. Turnovers are nearly all noise (early forced-fumble rate explains under 1% of later rate). Switched from yards per play to opponent-adjusted success rate because big plays are largely random.

**Unabated and Captain Jack Andrews.** The top-down method: take the market-making books as truth (Pinnacle for NFL, Circa for college, Bookmaker/CRIS for most US sports), strip the vig, and bet slower books that are off that number. Closing line value is "a comfort, not a crutch." Size at half or quarter Kelly, or flat 1% if you are unsure of your edge.

**Where they disagree.**

- *Is closing line value the goal?* Spanky and the Pinnacle school say yes. Andrews says only in liquid markets, and not in props. Peabody says prop closes can be worse than openers. Boston says no. The data adds a sharper point: in a study of 3,670 NBA games, bettors averaging 5% closing line value at soft books made 0.2%, because beating a closing price that still has vig in it does not clear the vig. **Conclusion for you: measure it, but only against the vig-free sharp close, only on sides, totals and moneylines, and treat it as a compass, not proof.**
- *Build your own number or follow the sharp books?* Walters, Voulgaris, Benter and Peabody build. Spanky and Unabated's entry path follow. The ones who build still pull their number most of the way to the market.
- *Early or late?* Walters: favorites early, dogs late. Peabody: the opener is "pretty irrelevant" because no money is behind it. Benter: as late as possible. There is no consensus, which means it is something to test on your own log, not a rule to hard-code.
- *Human judgment?* Boston and Walters heavy, Benter and late Voulgaris none.
- *Sizing?* Nobody uses full Kelly.

## 3. Where the draft spec breaks

### Data

- **The Odds API at $30 does not cover "every 15 minutes."** The $30 plan is 20,000 credits a month. Polling three sports around the clock every 15 minutes costs 26,000 to 52,000. It fits only if polling is limited to the hours that matter and uses a named list of up to 10 books (about 7,600 a month). Five-minute polling needs the $59 plan.
- **Pinnacle is there but is not real-time.** It is in the European region only, and the provider states the odds are taken from Pinnacle's public website and "may incur a delay." Pinnacle closed its own API to the public in July 2025.
- **Circa, Bookmaker and Heritage are not in the feed.** The cheapest verified source with both Pinnacle and Circa is $299 a month. Not worth it at this bankroll.
- **Offshore books that are in the feed:** BetOnline, LowVig, Bovada, MyBookie, BetUS, BetAnySports, plus DraftKings and FanDuel. No pay-per-head book is in any feed.
- **Historical closing lines:** The Odds API has snapshots every 5 minutes since September 2022 (every 10 back to mid-2020). Three seasons for all three sports is roughly 120,000 to 240,000 credits (my estimate), so one month of the $119 plan. Free alternatives: CollegeFootballData has opening and closing lines free; the nflverse schedule file has a spread and total of undocumented source; the old SportsbookReview archives appear to be gone; there is no clean free NBA source.
- **`nfl_data_py` is dead.** Archived September 2025. The replacement is `nflreadpy`, which returns polars tables.
- **CollegeFootballData** is maintained. The free tier is 1,000 calls a month; plan on the $5 to $10 tier.
- **`nba_api`** is maintained, but the NBA's site blocks most cloud servers. It works from a home connection, which ties the NBA piece to your Mac.
- **The exit test ("one full week with no gaps")** will fail on a laptop that sleeps. launchd does not run jobs while the Mac is asleep.

### Your book

Wagerhouse is a login-only site on a white-label platform I could not match to a named vendor. No reviews, no public odds, and no evidence about which market book its lines follow. I found no published measurement of how pay-per-head books lag or shade. What this does to the draft spec:

- The alert "a retail book is off the sharp line by 1.5 points" tells you about books you do not bet at. As written, it is noise.
- The fix is to treat your book as the thing being measured. Every time you bet or check a line, the number you saw at Wagerhouse gets logged with a timestamp next to the sharp price at that moment. Within two to three weeks that shows when your book posts, how long it lags, which feed book it tracks most closely, and which way it shades. That log decides whether a stale-line edge exists for you at all.
- Scraping behind your login would automate this, but it puts the account at risk, and with a credit-style book the risk is being cut off or not paid with no recourse. I recommend against it. Manual capture, made as quick as a text message, is enough.
- Until the log says otherwise, the starting proxies are BetOnline, LowVig, Bovada and BetAnySports. This is a guess to be replaced by measurement.

### Modeling traps

- **The Phase 2 exit test is close to unpassable and partly meaningless.** "Beat the closing spread on average error" is something almost no public system does. "Positive closing line value on paper bets at the opener" tests against a low-limit number at a book you cannot bet.
- **Small samples.** Three NFL seasons is about 855 games. Any filtered angle ("road dogs off a bye in wind") has a few dozen cases and proves nothing. Mid-season results are noise: 26 of 59 NFL systems are above break-even right now, against 8 of 52 for all of 2024.
- **Look-ahead leaks.** Season-long ratings joined to early-season games (SP+ and similar ratings blend in preseason priors that fade week by week, so a final rating knows the future). Opponent adjustments computed on the full season. Free line files that mix openers and closers. A hand-kept quarterback table "backtested" with injuries you now know about.
- **Double-counting.** The spec says not to, then has ratings, havoc, turnover luck, pace and manual situational adjustments, all of which overlap with each other and with what the market already prices. Benter's test is the guard: a factor earns its place only if it adds something on top of the market line.
- **CFB sparsity.** About 134 teams, 12 games, heavy roster turnover. Without preseason priors (returning production, recent history, recruiting) a model is unusable through September, which is exactly when lines are softest.
- **NBA speed.** "Under 60 seconds from injury report to recalculated line" means racing automated bettors for a price at a book you have to check by hand. The realistic version is narrower: catch the cases where your book has not reposted after an injury-report update. Reports now update every 15 minutes on game days.
- **Reverse line movement and bets-versus-money splits.** The one academic test (college football totals, 2005 to 2016) found following reverse line movement is not profitable. Public splits come from one or two books. Syndicates deliberately move lines the wrong way first. These should not be built.
- **Sizing.** Quarter Kelly on a 2% edge at −110 is about half a unit. With a floor of half a unit and a cap of three, the formula is theater at this bankroll. Flat one unit, two at most, is simpler and matches what Unabated recommends when you are unsure of your edge.

### Build order

Phase 1 before any model is right. But the spec's Phase 1 leaves out the two things that matter most (your book's own lines, and your existing bet history), and Phases 2 to 4 are in the wrong order for the calendar: the college football regular season ends in two weeks and the NFL in early January, so a football model built now gets validated on bowls and playoffs. Football modeling is an offseason project. The NBA is the live sport for the next seven months.

The faster path to the biggest edge is the audit in section 5: it uses bets you already placed.

## 4. Red-team of your current betting

First, the scale problem. +$1,640 on 145 bets is about 65 units. If those were flat $25 bets, that would be a 45% return, which does not happen. So either you are risking much more than $25 on the big favorites (laying $100 to $200 to win $25), or a few parlays carried the month. Either way the result is not evidence of edge. Example: someone betting −500 favorites that truly win 80% of the time (a 4% loser) still shows a profit over 20 bets 41% of the time.

| Bet type | Verdict | Cost per dollar staked | What would make it positive |
|---|---|---|---|
| Straight moneyline favorites, −300 to −800 | Leaking | About 4 to 6% | Your price beats the vig-free sharp price (for example −400 when fair is −430). All NFL favorites 2006 to 2018 returned −6.2%, worse than underdogs |
| Moneyline parlays of big favorites | Leaking more | About 10 to 15% for three legs | Only if every leg is individually a good price. Three −400 legs at 3.7% hold each is −10.6% |
| Alt lines at −300 to −800 | Probably leaking | About 4 to 8% (from memory, no hard data found) | NFL only, where the alt crosses 3 and 7 and the book prices by flat formula. One benchmark: for a +2.5 dog, +8.5 at better than −282 has value |
| Bought points | Mostly leaking | About 1 to 3% per purchase | NFL on or off 3 at 10 to 15 cents. On or off 7 at 10 cents is about neutral. Never in the NBA. Fair price of the half point on 3 is 18 cents, on 7 about 11 |
| 13-point teasers (4 teams, ties lose) | Leaking badly | About 16% | Each leg must win 87.4% at −140. NFL sides teased 13 points covered 83.7%. No selection rule found that closes that gap |
| 10-point teasers (3 teams) | Leaking badly | About 13% | Needs 81.7% per leg; history is 78.1% |
| Wong teasers (2 teams, 6 points, NFL, through both 3 and 7) | Best of the group | About break-even to +5% at −120; negative at −130 | Favorites of −7.5 to −8.5 or dogs of +1.5 to +2.5, total 49 or lower, never college or NBA, never totals. Legs have won 72.5 to 77% depending on the era. Needs 73.9% per leg at −120 |
| Same-game prop stacks | Leaking | 10 to 20% or more (soft sourcing) | Only if the book multiplies correlated legs as if independent |

For scale, real sportsbook results: parlays held 16 to 23% across six states in 2025, against 4 to 6% for straight bets.

**What this means in dollars (illustration, not your actual numbers).** If $500 a week goes through 13-point teasers and favorite parlays at about 13%, that is $65 a week, or roughly $1,100 over a season, which is more than a realistic year of edge at $25 units.

The honest answer on your big favorites specifically is "probably losing 4 to 6%, but checkable." The audit below checks it.

## 5. The minimum version that would have caught what you missed

Two pieces, in this order.

**The audit (a few days, about $30).** Take the ~145 bets you already made. For each one, pull the historical sharp price at the minute you bet and at the close, strip the vig, and compare. The output answers the question you asked: by bet type, did you get a better or worse price than the fair one, how much did you pay in vig, and what would the same bets have cost at the opener. It also shows, game by game, how far the number had already moved before you bet. This is roughly 3,000 to 9,000 feed credits, inside the $30 plan.

**The catcher (about a week of building).** Lines open at known times, so this is a schedule, not a constant monitor:

- A Telegram digest when openers post: college football Sunday around noon Mountain, NFL Sunday evening, NBA each morning.
- A "moving now" alert when the sharp price moves a point or more, or through 3 or 7, since the open, with one instruction: check your book now.
- A watchlist. Early in the week you tell it "Kansas State +10 or better." It alerts when the market is there, and when the market is leaving. This is the "don't bet past" number turned into an alarm, and it is the direct fix for finding value late.
- One-line capture of what your book is showing, so the lag gets measured as a side effect of using it.

## Revised build plan

**Phase 1A: Audit the bets already made.** Import the bet history, price each bet against the vig-free sharp line at bet time and at close, report by bet type. Done when every past bet is either priced or listed as unpriceable with the reason.

**Phase 1B: Logger, your-book capture, alerts, bet log.**

- Odds logger on The Odds API, polling only in the windows that matter, with a named book list: Pinnacle, BetOnline, LowVig, Bovada, BetAnySports, DraftKings, FanDuel. A poll a few minutes before each kickoff so the close is real.
- Fair price from Pinnacle with the vig removed, cross-checked against the other books because the Pinnacle feed can be delayed. Disagreement is flagged, not hidden.
- Bet log and your-book line capture from the command line, and optionally by texting the Telegram bot.
- Alerts: opener digests, moving-now, watchlist. The draft's "retail book off sharp" alert is dropped unless you add books that are in the feed.
- Two calculators that run on every logged bet: is this teaser leg a true Wong leg at your book's price, and was that half point worth what you paid.
- Weekly report: results, closing line value on sides, totals and moneylines only, split by bet type and by price band, with the luck range printed next to every number so a hot streak cannot pass for an edge.
- Gap detection and a heartbeat alert if a poll is missed.
- Tests for the vig removal, key numbers, bet parser, closing line value and teaser math.
- Done when: three weeks of polling with every gap explained, closing line value on every eligible bet, and a short written answer to "does my book lag the market, by how much, and which feed book does it follow."

**Phase 2: Decide where the edge is, from the measurements.** If your book lags, tune the alerts to it. If it does not, the remaining price edge is other books, and the system already supports them.

**Phase 3: NBA, the narrow version (in season now).** Injury-report change alerts for players who move a line, and a props check that compares your book's number to the consensus of feed books. No sub-minute requirement.

**Phase 4: Football ratings, offseason 2027.** NFL first, then CFB with preseason priors. The model is blended with the market from day one. It passes if it adds predictive value on top of the market line on seasons it never saw, and its job is to rank which openers you look at first. Historical backfill (one month at $119) happens here, not before.

**Phase 5: Own props model.** Only if Phase 3 shows props at your book are worth it and you are not limited.

**Sizing:** flat 1 unit, 2 at most, until there are 500 bets with measured price quality. Revisit then.

**What changed from BUILD_SPEC.md and why.**

| Draft | Revised | Why |
|---|---|---|
| Phase 1 starts with the logger | Starts with an audit of the 145 existing bets | Fastest honest answer to "do I have an edge," and uses data that already exists |
| Alerts compare retail books to the sharp line | Alerts are built around fixed open times, moves, and your watchlist; your book's line is captured by hand | Your book is in no feed; the draft's main alert was about books you do not use |
| Poll every 15 minutes, all the time, at $30 | Poll in windows with a book list | The draft's schedule costs more credits than the plan has |
| Pinnacle or Circa as the sharp book | Pinnacle with cross-checks | Circa is not available under $299 a month; the Pinnacle feed is delayed |
| Closing line value on every bet | Sides, totals, moneylines only, against the vig-free sharp close | It is not meaningful for props, and beating a vigged close does not clear the vig |
| Exit test: one week, no gaps | Three weeks, gaps explained, plus the written answer about your book | One week cannot measure lag; a laptop will have gaps |
| Phase 2 football model now, must beat the close | Offseason, blended with the market, judged on what it adds | Almost no public model beats the close; the season is nearly over |
| NBA: 60-second injury reaction | Injury-change alerts aimed at your book not reposting | Cannot out-race automated bettors, and the bet is placed by hand anyway |
| Props: build a full model last | Cheap consensus comparison first, full model only if it earns it | Low effort version tests the market before the high effort one |
| Quarter Kelly with floor and cap | Flat units | The formula produces the floor almost every time at this bankroll |
| Rules: reverse line movement, bets versus money, favorites early | Dropped the first two; the third becomes a tracked question | Evidence against the first two; the pros disagree on the third |
| `nfl_data_py` | `nflreadpy` | The former was archived in 2025 |
| Not in the draft | Teaser and bought-point calculators; luck ranges on every report | These are where the money is currently going |

**Running cost:** $30 a month for the feed to start ($59 if five-minute polling proves necessary), $5 to $10 for CollegeFootballData when Phase 4 starts, $119 once for the backfill.

## Open questions for you

1. **Can you get your bet history out of Wagerhouse?** I need, per bet: when placed, what, line, price, amount risked, amount to win, result. A copy and paste of the history screen is fine; I will parse whatever format it is. The audit depends on this.
2. **How were the big favorites staked?** Risking $25, or laying enough to win $25?
3. **Would you open two or three legal Colorado books** (DraftKings, FanDuel, BetMGM, Caesars are all in the feed)? This is the single biggest lever in the whole plan: shopping across books is the best-documented edge, alerts would work directly instead of through a proxy, and it lowers your exposure to one unregulated book. If no, the plan still works but the ceiling is lower.
4. **Wagerhouse specifics:** the teaser pay table and whether ties lose; what a half point costs, and on or off 3; when it posts NFL, college and NBA lines each week; your limits; whether it is credit with weekly settlement or you post money up front.
5. **Is the Mac on and awake all week,** or does it sleep and travel? If it sleeps, I would run the poller on a small always-on server (about $5 a month) and keep only the NBA stats piece on the Mac.
6. **Do you want to log bets by texting the Telegram bot,** in addition to the command line? It is a little more to build, and a bet log only works if logging takes five seconds.
7. **Which props do you bet,** and in which sports? That decides whether the props check in Phase 3 is worth building.
8. **Budget:** is $30 a month to start, with a possible step to $59, fine?

## Gaps in this research

- No published evidence on how pay-per-head books lag or shade, or which book Wagerhouse follows. Your own log is the only source.
- No data on what share of a line's weekly move happens in the first hours, or how often lines cross 3 or 7.
- No measured return for small-conference CFB, derivatives or props. Those rankings are judgment.
- Wong teaser results for 2022 to 2025 specifically were not found.
- Walters' exact half-point chart is from memory. Wong's and Ed Miller's books, and several Pinnacle and Action Network pages, could not be read directly.
- Exact NFL opener times by book are unverified.
- Feed reliability complaints: only competitor marketing found, nothing first-hand.

## Sources

**Market efficiency, closing line value, sample size**
- Buchdahl, Pinnacle closing odds efficiency: https://www.football-data.co.uk/blog/pinnacle_efficiency.php
- Buchdahl, Wisdom of the Crowd: https://www.football-data.co.uk/blog/wisdom_of_the_crowd.php
- Buchdahl, value retention by limit and time (Oct 2026): https://www.football-data.co.uk/blog/pinnacle_limit.php
- Buchdahl, how many bettors are sharp: https://www.football-data.co.uk/blog/how_many_bettors_are_sharp.php
- Pinho, expected against realized returns: https://networked.substack.com/p/a-view-from-the-pinnacle
- Whelan, NBA closing line value by decile: https://karlwhelan.com/?p=2595
- Data Golf, sharp against soft reference books, sample size: https://datagolf.com/analyzing-betting-odds
- Levitt 2004: https://www.stat.berkeley.edu/~aldous/157/Papers/Levitt_Gambling_2004.pdf
- White, NFL closing spread error 2002 to 2025: https://scholarship.claremont.edu/cmc_theses/4125/
- Szalkowski and Nelson, NFL lines 2002 to 2011: https://arxiv.org/abs/1211.4000
- Hold by book: https://sharpapi.io/research/hold-report
- Washington Post via IBJ, how books limit winners: https://www.ibj.com/articles/sportsbooks-say-you-can-win-big-then-they-try-to-limit-winners

**Line timing, movement, pay-per-head**
- ESPN, Circa openers, limits, Metcalf quotes: https://www.espn.com/chalk/story/_/id/32209480/betting-market-watch-nfl-college-football-line-moves-early-action-bookmaker-insights
- ESPN, head fakes: https://www.espn.com/chalk/story/_/id/32066178/the-head-fake-game-how-sharp-bettors-fool-betting-market
- TeamRankings, NFL open-to-close moves: https://www.teamrankings.com/nfl/odds-movement/ats/movement/
- TeamRankings, NBA open-to-close moves: https://www.teamrankings.com/nba/odds-movement/ats/movement/
- Francisco and Moore, reverse line movement: https://ideas.repec.org/a/spr/jecfin/v43y2019i4d10.1007_s12197-019-09479-3.html
- Covers, NFL lookahead lines: https://www.covers.com/nfl/how-to-use-lookahead-lines
- BettorEdge, when lines come out: https://www.bettoredge.com/post/when-do-betting-lines-come-out
- AP, NBA injury reporting changes: https://www.news4jax.com/sports/2025/12/19/nba-tweaks-its-injury-reporting-rules-still-wants-changes-to-prop-betting/
- The Handle, pay-per-head economics: https://thehandle.substack.com/p/pphunderworld
- SBR forum, steam chasing: https://www.sportsbookreview.com/forum/sportsbooks-industry/867481-chasing-steam-and-limiting-books-justin7
- SBR forum, locals posting day-of lines: https://www.sportsbookreview.com/forum/sportsbooks-industry/1100053-local-only-has-day-of-event-lines
- Unabated, NFL week day by day: https://unabated.com/content/videos/nfl-betting-strategy-guide-day-by-day

**Models against the market**
- The Prediction Tracker, college football: https://www.thepredictiontracker.com/ncaaresults.php
- The Prediction Tracker, NFL: https://www.thepredictiontracker.com/nflresults.php
- nfelo model performance: https://www.nfeloapp.com/games/nfl-model-performance
- nfelo, blending with the market: https://www.nfeloapp.com/analysis/using-market-regression-to-improve-prediction-accuracy-in-the-nfl/
- nflfastR model calibration: https://opensourcefootball.netlify.app/posts/2020-09-28-nflfastr-ep-wp-and-cp-models/
- ESPN, SP+ 2026 preseason method: https://www.espn.com/college-football/story/_/id/49593338/final-preseason-college-football-sp+-rankings-takeaways-2026
- EPM: https://dunksandthrees.com/about/epm

**Practitioners**
- Benter 1994 paper: https://www.gwern.net/doc/statistics/decision/1994-benter.pdf
- Walters, ESPN excerpt: https://www.espn.com/sports-betting/story/_/id/38207435/how-bet-football-guide-nfl-ncaa-games-more
- Walters, Covers summary of the book's numbers: https://www.covers.com/guides/betting-tips-from-pro-sports-bettor-billy-walters
- Walters' site: https://realbillywalters.com/handicapping-system/
- Walters' operation: https://www.shortform.com/blog/billy-walters-sports-betting/
- Wilson, power ratings: https://www.actionnetwork.com/ncaaf/college-football-betting-power-ratings-action-network
- Wilson, advanced stats and Havoc: https://www.actionnetwork.com/ncaaf/how-to-bet-on-college-football-using-advanced-stats-to-handicap-games
- Voulgaris, ESPN profile: https://www.espn.com/blog/playbook/dollars/post/_/id/2935/meet-the-worlds-top-nba-gambler
- Peabody Q&A: https://www.rotowire.com/football/article.php?id=40172
- Peabody profile: https://www.thelines.com/professional-sports-betting-journey-bettor-rufus-peabody-2022/
- Feng's summaries of Abnormally Distributed, Boston, Voulgaris, Peabody: https://thepowerrank.com/the-craft-of-sports-betting-professionals-2/
- Boston episode: https://thepowerrank.libsyn.com/alan-boston-on-college-basketball-betting
- Feng, analytics guide: https://thepowerrank.com/2014/11/24/how-to-understand-college-football-analytics-the-ultimate-guide/
- Feng, success rate: https://thepowerrank.com/2021/10/21/5-insights-from-college-football-success-rate/
- Unabated, closing line value: https://unabated.com/articles/getting-precise-about-closing-line-value
- Unabated, the Unabated Line: https://unabated.com/post/what-is-the-unabated-line
- Unabated, market makers: https://unabated.com/articles/who-sets-the-sports-betting-line-market-makers
- Unabated, ten ways to win: https://unabated.com/articles/ten-ways-to-win-at-sports-betting-with-unabated
- Unabated, bankroll: https://unabated.com/articles/how-to-build-a-sports-betting-bankroll
- Unabated, props mistakes and limits: https://unabated.com/post/the-biggest-mistake-youre-making-when-betting-nfl-player-props
- Establish The Run, props ecosystem: https://establishtherun.com/understanding-the-current-ecosystem-of-nfl-player-props/
- Spanky interview: https://www.covers.com/industry/whats-the-difference-between-you-and-a-sharp-bettor-we-asked-spanky

**Bet-type math**
- Wizard of Odds, NFL margins, half-point prices, moneyline returns: https://wizardofodds.com/games/sports-betting/nfl/
- Wizard of Odds, teaser cover rates and pay tables: https://wizardofodds.com/games/sports-betting/appendix/10/
- Wizard of Odds, NFL teasers: https://wizardofodds.com/games/sports-betting/nfl-teaser/
- Wizard of Odds, parlays: https://wizardofodds.com/games/sports-betting/nfl-parlay/
- Wizard of Odds, buying points: https://wizardofodds.com/games/sports-betting/appendix/4/
- Unabated, profitable NFL teasers: https://unabated.com/post/profitable-nfl-teaser-bets
- Boardroom, Wong legs against Pinnacle closes: https://boardroom.tv/teaser-betting-nfl-playoffs/
- Covers, teaser strategy: https://www.covers.com/nfl/teaser-strategy
- Covers, point buying: https://www.covers.com/nfl/point-buying-strategy
- The Lines, teaser prices by book: https://www.thelines.com/nfl-bets-best-wong-teaser-odds-sports-betting-apps-promo-codes-2024/
- NFL margins by era (lower-grade source): https://www.deucescracked.com/blog/nfl-margin-of-victory-data-1999-2025
- Offshore-style teaser pay table: https://intercom.help/support-help-center/en/articles/12007138-american-football
- Covers, Nevada and New Jersey hold by bet type: https://www.covers.com/industry/sportsbooks-increased-figures-same-game-parlays-october-26-2022
- InGame, 2025 parlay hold by state: https://www.ingame.com/?p=40653

**Data sources**
- The Odds API, plans: https://the-odds-api.com/
- The Odds API, credit rules: https://the-odds-api.com/liveapi/guides/v4/
- The Odds API, books by region: https://the-odds-api.com/sports-odds-data/bookmaker-apis.html
- The Odds API, update intervals: https://the-odds-api.com/sports-odds-data/update-intervals.html
- The Odds API, historical: https://the-odds-api.com/historical-odds-data/
- SportsGameOdds pricing: https://sportsgameodds.com/pricing
- odds-api.io pricing: https://odds-api.io/pricing
- Pinnacle API closure notice: https://github.com/pinnacleapi/pinnacleapi-documentation
- nfl_data_py (archived): https://github.com/nflverse/nfl_data_py
- nflreadpy: https://github.com/nflverse/nflreadpy
- nflverse schedule fields: https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_schedules.csv
- CollegeFootballData tiers: https://collegefootballdata.com/api-tiers
- cfbd Python client: https://github.com/CFBD/cfbd-python
- nba_api: https://github.com/swar/nba_api
- nbainjuries: https://github.com/mxufc29/nbainjuries
- Open-Meteo pricing: https://open-meteo.com/en/pricing
- Telegram bot limits: https://core.telegram.org/bots/faq
- Wagerhouse login page: https://wagerhouse.ag
- Pay-per-head odds come bundled from the platform: https://www.gambling911.com/node/65383

## Addendum, 2026-11-21: answers received and a first look at the history

**Answers.** Kylor is staying on Wagerhouse only for now, and is willing to pay extra vig for adjusted lines when the value is there. Consequence: the "retail book off sharp" alert stays dropped, measuring Wagerhouse's lag stays the first job of Phase 1B, and the bought-point and alt-line pricer moves up in importance because it is the tool that says when the extra vig is worth paying.

**Bet history received** for ten weeks (9/1 through 11/10; the week of 10/6 was not included), saved unsynced at `data.nosync/raw/wagerhouse_history_2026-09-01_to_2026-11-16.txt`.

What the weekly totals in the history say (sums of Wagerhouse's own weekly results):

- Ten weeks, 275 wagers, net about **−$285**.
- First five weeks (9/1 to 9/29): −$1,513. Last five (10/13 to 11/10): +$1,228.
- 13-point teasers: 16 tickets, 8 won, 8 lost, net −$165 on about $1,413 risked (−12%). At −140 a ticket needs to win 58.3% of the time. The published leg rate (83.7%) predicts a ticket wins 49%. The record is 50%.

What the history is missing for the audit: the time each bet was placed (so bets can only be priced against the close, not against the price when placed, and live bets cannot be separated from pregame ones), the amount on the last bet of each week (cut off in the paste), the week of 10/6 and the current week.

Other things visible in the history that the plan did not assume: stakes range from $5 to $168, not a flat $25; a meaningful share of tickets look like in-game bets (several prices on the same game minutes apart); and there are baseball and hockey bets, which the engine does not cover.
