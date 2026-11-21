# Picks engine: research, red-team and proposed design

Written 2026-11-21 (Mountain). Nothing in this document is built. It ends with a design for you to approve, edit or kill.

Confidence: figures were read on the source page during this research unless marked "from memory" or "search result only". Gaps are listed near the end.

## The short version

The goal is an agent that does the handicapping on a schedule and alerts you when there is a bet. That is buildable, and the free data turned out better than expected: Pinnacle's lines are readable for free from this Mac, so the engine gets a genuinely sharp reference price. The blunt part: no one-person system out-predicts the closing line on NFL and college sides, and the pros I read say the same about themselves in the markets they avoid. What an agent can realistically do is have a number for every game before the week starts, notice when your book or the market is off that number for a reason that is not yet priced (mostly quarterback and cluster-injury news, wind, and overreaction to one result), tell you the price where the bet stops being good, and pass on everything else. Expect zero to five bets most weeks and many slates with none. Today's card shows why the design matters: every bet on it was issued at exactly the closing number, four of six reasons leaned on betting splits, and at least three of its numbers did not match the market or your book.

## 1. What an elite week looks like

A synthesis of the people who have described their process in their own words.

| When | What they do | Who |
|---|---|---|
| Sunday night | Log every injury from the day. Flag misleading results (turnover luck, late-down luck). Have numbers ready if betting openers | Pizzola, Walters, R.J. White |
| Monday | Review last week's bets and timing. Coaches' press conferences for injury severity. College numbers get bet Monday 9 to 11am ET as limits rise | Spanky, Walters ("start your homework Monday morning") |
| Tuesday | Numbers are final. Pick targets, each with a price. College sides Tuesday, totals Wednesday | Pizzola, "MrPeanutButter" |
| Wednesday to Friday | Practice and availability reports, quarterbacks first. NFL lines "swing greatly in the final 48 hours" | Pizzola, Unabated |
| Game day | Full-game sides and totals are the most efficient market of the week. Little left but derivatives | Krackomberger, Unabated |

Specific, repeatable methods:

- **Walters.** Slow ratings (90% old, 10% latest game). Injuries priced in points, with cluster order: pass catchers, defensive line, offensive line, defensive backs. Upgrade a team that just lost by 19 or more. Half-unit steps from 0.5 to 3 units, 3% cap. His published factor chart could not be verified on any page I could open.
- **Pizzola.** Does not finalize a number until Tuesday morning. Asks "why did this team get bet today?" for every move. Warns that lookahead and opening lines have such low limits that people anchor on them wrongly.
- **Spanky.** Makes no numbers at all; reads the market and tries to get ahead of it. Says the NFL is not profitable for him and that "$500 bets, that doesn't work" for his style.
- **Krackomberger.** "I'm going to lose 43 out of 100 bets, maybe even 45." The whole edge is five to seven bets in a hundred. Sizes 1 to 2%. If your only book has a bad number, do not bet the game.
- **Brad Powers (college).** Start from last year's rating, or an average of SP+, FPI and Sagarin. Adjust each position group −3 to +3. The transfer portal matters more than freshmen. If your ratings are far from the market late in the season, fix your ratings.
- **Peabody** (from the first research doc). Blend 45% model, 55% market. Needs about 2 points of difference in the NFL to bet.
- **Fezzik.** Ratings in half-point steps against an average team; home field 1.5 to 2; ratings assume the expected quarterback.

Where they disagree:

- **When to bet.** Sunday-night openers (White, PFF), Monday morning (Spanky), Tuesday after numbers are final (Pizzola). No consensus, so the engine logs timing and lets results decide.
- **Which sport.** Spanky bets college and skips the NFL. Pizzola is the reverse.
- **Own number or the market's.** Spanky trades lines only. Pizzola, Powers and Fezzik make numbers, then pull back toward the market.
- **Betting splits.** Sports Insights and VSiN sell them. Pizzola, Ed Miller, Jack Miller and James Holzhauer reject them. The only defense with data (one college season, one unnamed book) found fading worked when the line moved *with* the money, the opposite of reverse line movement.

## 2. Factors: what gets points, what gets a flag, what gets nothing

The rule against double-counting: efficiency stats, pace, returning production and coaching quality live inside the rating and are never added again. Only things newer than the rating, or specific to this game, get their own adjustment.

| Factor | Default value | Where it goes | Confidence |
|---|---|---|---|
| Home field, NFL | 1.7 points (down about a point since 2002) | Rating | High |
| Home field, college | 2.5 | Rating | Medium |
| Home court, NBA | about 2.2 (from memory) | Rating | Medium |
| NFL quarterback out | 1 to 7 by tier, measured against that team's backup | Game adjustment | High |
| College quarterback out | No published table; set by hand per case | Game adjustment | Low |
| Star non-quarterback | 0.5 to 1.0, capped at 1 | Game adjustment | Low |
| Cluster injury (3+ linemen, top corners, receiver room) | 1 to 2 total (from memory) | Game adjustment | Low |
| Wind, totals only | About −2 points at 10 to 15 mph, −3 at 16 to 25, −7 above 25 | Game adjustment | Medium |
| NFL bye week | 0.3 (it was 2.2 before 2011; the market still prices about 1) | Game adjustment | Medium |
| NBA back-to-back | −1.2 | Game adjustment | Medium |
| Fumble luck, turnover luck, opponent three-point luck | Regress 90 to 100% | Cleans the rating | High |
| Key numbers | Measured push rates: 9.1% on 3, 7.0% on 7, 6.4% on 10 | Pricing | High |
| Altitude | Inside Denver's and Utah's home field | Rating | Low |

Gets a flag on the card but no points, because the evidence says it is priced or noise: letdown, lookahead, sandwich and revenge spots, rivalry, bowl motivation, lame-duck coaches, West-coast teams in early games, opponent off Monday night, NBA referee crews, cold and rain on totals. The one situational angle with a rigorous result is teams that have clinched a top seed and may rest starters.

Two findings that cut against your list:

- **Wind is the one weather effect the market appears to under-price.** Unders hit 56% against the close at 10 to 15 mph in one 2,720-game database. One source, so treat it as promising, not proven.
- **Bye weeks are over-priced by the market,** not under-priced.

## 3. Timing

- Openers are deliberately soft, low-limit numbers. At $25 a bet you are never limited, so early betting suits you, but only if you already have a number.
- The big moves in a football week are usually information, mostly quarterback news. Three of today's card games moved 2 to 6 points during the week for that reason.
- Once a move is complete, its direction predicts nothing. Betting a number that used to be good is the mistake you called out in your feedback.
- A move you cannot explain is not a signal by itself. Syndicates sometimes move a line the wrong way first.

## 4. What would make this elite, and what is realistic

Realistic for one person with an agent and free data:

- **Coverage and discipline.** A number for every game by Sunday night, every week, and a written price limit on every pick.
- **Speed on public news against a slower book.** Your book copies the market. Each time it is slow to follow a quarterback report, there is a window.
- **Small stakes.** You fit under any opening limit.
- **Thin games.** Smaller-conference college games get less attention, and news is slower to reach the line.
- **Honest grading.** Every pick logged at issue and graded against Pinnacle's close, so we know within a couple of hundred picks whether the engine helps.

Not realistic:

- Beating Pinnacle's closing NFL side on prediction alone. In 2024 no tracked computer system beat the college closing line at a profitable rate.
- Private injury information. The pros who win on news have staff and sources.
- Machine-readable college injuries. The four big conferences publish availability reports through a web app; outside them there is nothing structured. The agent has to search for quarterback status game by game.
- A guarantee. Krackomberger is content with $101 or $102 back per $100 bet. At $25 units and three bets a week, a 2% edge is about $80 a season. The engine's larger value to you is the bets it stops.

A risk specific to an AI agent: it can state a wrong injury or a wrong number with confidence. Your first cards had exactly this problem. The design below does not let the agent write any number.

## 5. Red-team of today's card

Lines are DraftKings as published by ESPN, plus your book where I had a reading. Results as of 4:20pm Mountain.

| Pick on the card | Card's number | Market open | Market close | Value against the close | Result |
|---|---|---|---|---|---|
| Nebraska | +3.5 | +5.5 | +3.5 | None | Won, 31-28 |
| Tulane | +6.5 | +13.5 | +7.5 | Card was a point worse than the close; you got +7.5 | Won, 28-24 |
| Michigan | +3.5 | +5.5 | +3.5 | None | Leading 10-3 in the fourth |
| Texas Tech | −4.5 | about pick'em | −4.5 | None | Leading 14-7 in the fourth |
| K-State | +7.5 | +10.5 | +10 now (your book also +10) | Card's number was 2.5 points off | Not started |
| Utah/TCU Under | 46.5 | 44.5 | 46.5 now | None | Not started |
| Iowa/Illinois Under (conditional) | 40.5 | 43.5 | 42.5 | You bet Under 41 at 9:29am | Lost, 51 points |
| BYU/Kansas Under (conditional) | 47.5 | 50.5 | 46.5 | Not bet | 60 points after three overtimes |
| Boston College | Pass | | | You bet Syracuse −3 the night before | BC won 27-15 |
| FIU | Pass | | | | FIU trailing by 11 late |

Grade: the two graded bets won, which tells us nothing. On process the card fails its own rules.

- **No bet had value against the close.** Every number was the closing number or worse. The card was issued at 9:25am Saturday, 35 minutes before the first kickoffs, after all the movement.
- **The value was earlier in the week.** Nebraska, Michigan and Tulane moved 2 to 6 points toward the card's side between open and close.
- **Four of six reasons were betting splits** ("88% of tickets", "92% of money", "96% of money moved it", "100% of tracked money"). Rule 2 says that is not enough, and the evidence agrees.
- **The injury reasons were already public.** UCLA's quarterback was ruled out Wednesday. By Saturday that was in the line.
- **At least three numbers were wrong.** K-State +7.5 when the market and your book had +10. Tulane +6.5 when the close was +7.5. "The total didn't move" on Utah/TCU when it rose two points. Different books explain some gaps, but not 2.5 points.
- **No fair line anywhere.** The card never says what the number should be. For Nebraska it admits the ratings matched the market.
- **Bets off the card.** Syracuse −3, Illinois +9, Under 41 without its condition, and five live tickets since Friday.

What the engine would have done differently:

- Sunday night it would have had a fair number for each game from ratings, and flagged Nebraska, Michigan and Tulane only if your book's opener was off that number. Whether it was, we cannot know, because nothing was reading your book then.
- Wednesday, when UCLA's quarterback was ruled out, it would have re-priced Michigan within the hour and alerted only if your book had not moved.
- Saturday morning it would have marked all six as Pass, value gone, with the price that would bring each back.

## 6. Proposed design

Two layers. Code owns every number. The agent owns the research and the judgment.

### Layer 1: code builds a slate sheet

For every NFL and college game:

1. **Prices.** Your book, DraftKings, and Pinnacle (new, free, sharp), with the first number seen and every change since.
2. **Fair line and total.** Three independent numbers shown side by side:
   - the market's own view before this week, from team ratings backed out of recent closing lines and updated slowly (Walters' 90/10);
   - an average of public rating systems (Sagarin, FPI, Massey, nfelo and about 50 others, published free each week in one file);
   - Pinnacle's current price with the vig removed.
   
   The fair line is a blend that leans on the market (Peabody's 55/45), plus this week's adjustments.
3. **Adjustments from one file you can read and edit,** `adjustments.yaml`. Each entry has the game, points, reason, source link and time. Quarterback and injury values, wind, rest. Nothing else moves the fair line.
4. **Edge.** Fair line against your book's current number, turned into a cover probability with measured football margins, so half a point on 3 counts for what it is worth.
5. **The "don't bet past" number** and the stake, calculated, not typed.

### Layer 2: the agent researches and decides

A scheduled Claude run on your Mac reads the slate sheet and works only the games where the numbers show a possible edge.

- It looks up quarterback and injury status, availability reports, weather at the stadium, and why the line moved.
- It may add an adjustment to the file, with a source link. That re-runs the pricing. It cannot type a line, a price or an edge.
- It sets Bet, Conditional or Pass. A Bet needs all four: an edge at your book's current number above the threshold, the rating average on the same side, a written reason from the allowed list that is not "the line moved", and a second check of your book's number in the same minute as the alert.
- It writes the card to `docs/cards/` and sends Telegram alerts for the four events you listed.

### Schedule (Mountain)

- Sunday evening: openers. Numbers for the whole slate.
- Monday morning: college limits rise.
- Tuesday morning: numbers final, targets set, `engine watch` armed at each "don't bet past" number.
- Thursday evening: NFL injury report and college availability reports.
- Saturday and Sunday morning: final check, at least two hours before the first kickoff.
- Any time: a line move of a point or more, or a quarterback status change, triggers a re-run for that game.
- 90 minutes before kickoff: Conditionals are confirmed or dropped.

### Grading

- Every engine pick is logged at issue with your book's number, graded on result and against Pinnacle's close.
- The weekly report shows the engine's record next to yours, plus two lists: engine picks you skipped, and bets you made that the engine passed on.
- A test set in advance: after 100 engine picks, if they have not beaten the closing line on average, the report says so and we change the method or stop.

### What stays, what changes

- Everything built stays. The current "your book is a point better" alert becomes an input to the slate sheet.
- Betting splits are logged and shown on the card but cannot be a reason for a pick. After a season we will know whether they add anything.
- NBA waits until football is working.

## Open questions for you

1. **Agent runs on your Mac.** Each scheduled run is Claude doing research for several minutes, six or so times a week plus re-runs. That uses your Claude plan. Fine?
2. **Sizing.** You asked for 0.5 to 3 units by edge. I recommend capping at 1 unit until the engine has 100 graded picks, because nothing has shown an edge yet. Which do you want?
3. **Splits as logged-only.** You listed them as an input. I want them on the card but barred as a reason. Agree?
4. **A free CollegeFootballData key.** It gives college margins, stats and stadium locations. Sign-up takes a minute and needs your email. Will you do that?
5. **More reads of your book.** Catching openers and news means reading Wagerhouse more often than five times a day on weekdays, perhaps hourly from 7am to 9pm. Acceptable?

## Gaps in this research

- Walters' factor chart and unit table: not on any page I could open.
- No readable primary source for Fezzik's method or Collin Wilson's weekly routine.
- College margins by key number: no primary table; to be computed from data.
- No point values found for altitude, special teams, fourth-down aggressiveness or college quarterbacks.
- The wind result rests on one self-published database.
- Whether the conference availability app can be read without a browser is untested.
- CollegeFootballData endpoints were not tested (no key yet).

## Sources

**Weekly process**
- Spanky: https://www.covers.com/industry/whats-the-difference-between-you-and-a-sharp-step-inside-the-mind-of-a-professional-bettor
- Spanky and Krackomberger: https://www.theringer.com/2019/06/05/gambling/sports-betting-bettors-sharps-kicked-out-spanky-william-hill-new-jersey
- Krackomberger transcript: https://www.betstamp.com/education/circles-off-episode-179-bill-krackomberger-tells-legendary-gambl
- Pizzola's NFL week: https://www.betstamp.com/education/circles-off-episode-120-how-to-beat-early-nfl-betting-lines
- Pizzola on splits: https://www.betstamp.com/education/the-downfalls-of-using-public-betting-percentages-betting-splits
- Brad Powers, college ratings: https://www.covers.com/ncaaf/how-to-build-college-football-power-ratings-tips-from-brad-powers-4-3-2026
- College bettor's week: https://sozai.app/transcript/find-your-edge-sports-betting-underdog/
- Walters: https://www.espn.com/sports-betting/story/_/id/38207435/how-bet-football-guide-nfl-ncaa-games-more and https://www.covers.com/guides/betting-tips-from-pro-sports-bettor-billy-walters
- R.J. White, ratings recipe: https://www.cbssports.com/nfl/news/nfl-betting-on-opening-lines-how-to-build-a-power-rating-system-and-why-its-crucial-to-beating-the-odds
- Fezzik ratings table: https://sicscore.com/news/steve-fezziks-nfl-power-ratings-week-8-2026
- PFF, sharp signs: https://www.pff.com/news/bet-pff-betting-101-sharp-signs-for-bettors-red-flags-to-avoid
- Jack Miller, fallacies: https://establishtherun.com/disproving-popular-sports-gambling-fallacies/
- Sports Insights, money percentages: https://www.sportsinsights.com/blog/how-can-college-football-bettors-find-value-using-our-money-percentages/
- VSiN, splits: https://vsin.com/nfl/how-to-win-using-vsin-nfl-betting-splits/
- Ed Miller on fading the public: https://sports.yahoo.com/books-to-read-why-the-logic-of-sports-betting-is-a-must-have-155411907.html

**Factors**
- Lopez and Bliss, bye, short weeks, home field: https://www.frontiersin.org/articles/10.3389/frbhe.2024.1479832/full
- NFL margins and push rates: https://www.deucescracked.com/blog/nfl-margin-of-victory-data-1999-2025
- Wind: https://www.covers.com/nfl/how-wind-impacts-nfl-games
- Key numbers: https://www.covers.com/nfl/key-numbers
- nfelo weighted EPA: https://www.nfeloapp.com/analysis/weighted-EPA-methodology-and-performance/
- nfelo home field: https://github.com/greerreNFL/nfelohfa
- Quarterback values, 2019 oddsmakers: https://thescore.com/nfl/news/1824932
- Luck metrics: https://www.pff.com/news/nfl-unsustainable-luck-which-nfl-teams-can-expect-better-or-worse-luck-in-2020
- Opponent three-point luck: https://www.theringer.com/nba/2021/2/12/22279459/nba-make-miss-3-point-shooting
- SP+ 2026: https://www.espn.com/college-football/story/_/id/49593338/final-preseason-college-football-sp+-rankings-takeaways-2026
- Team home field: https://vsin.com/the-vsin-daily/cutting-through-the-noise-on-home-field-advantage-in-nfl-college-football/

**Free data, tested 2026-11-21**
- Pinnacle guest lines: https://guest.api.arcadia.pinnacle.com/0.1/leagues/889/matchups
- Prediction Tracker files: https://www.thepredictiontracker.com/nflpredictions.csv and https://www.thepredictiontracker.com/ncaapredictions.csv
- ESPN FPI: https://site.web.api.espn.com/apis/fitt/v3/sports/football/nfl/powerindex
- nfelo ratings: https://raw.githubusercontent.com/greerreNFL/nfelo/main/output_data/elo_snapshot.csv
- NFL schedule, rest and closing lines: https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv
- NFL injuries: https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries
- Action Network scoreboard (consensus opener, splits): https://api.actionnetwork.com/web/v2/scoreboard/nfl
- Bookmaker lines: https://lines.bookmaker.eu/
- Weather: https://api.open-meteo.com/v1/forecast
- SEC availability reports: https://www.secsports.com/fbreports
- Big Ten availability reports: https://bigten.org/fb/availability-reports/
- CollegeFootballData tiers: https://collegefootballdata.com/api-tiers
