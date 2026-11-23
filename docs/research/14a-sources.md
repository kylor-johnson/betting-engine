# Evidence brief: sources for a betting-model review

Compiled 2026-11-23. Scope: pregame NFL / CFB / NBA sides, totals and player props; one soft offshore book; Pinnacle no-vig as the reference price; free data only.

**Tags**
- **[DATA]**: the source shows data or a reproducible calculation.
- **[ASSERTED]**: stated without data.
- **[FOLKLORE]**: widely repeated, with no traceable source.

I opened and read every URL cited here unless it is marked "(not opened)". PDFs were downloaded and their text extracted locally. Tout, pick-seller and affiliate pages are excluded unless a claim is about that seller's own track record. Where that happens, the page is labelled as self-reported.

**Two calculations of my own**, from nflverse `games.csv` (free; consensus closing lines; https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv). They are labelled **[DATA: own calc]**:
- Section 7: wind and totals.
- Section 8: teasers and key numbers.

The sample-size arithmetic in section 9 is mine too.

---

## 1. Billy Walters

**Caveat on sources.** No full text of *Gambler* (2023) was available. What I could read:
- An ESPN excerpt.
- Walters' own site, which sells consulting.
- Secondary summaries from Covers and Shortform.
- ESPN long-form profiles from 2015 and 2018.

Nothing found gives his actual half-point table or his per-player numbers in a primary source.

| # | Claim | Tag | Source |
|---|---|---|---|
| 1.1 | NFL home field is "generally thought to be worth 3 points". His figure for 1974-2022 is "closer to 2.5". Over the last four seasons it was "less than 1 point" (he attributes much of this to COVID). | [ASSERTED] (he states data exists but shows none) | ESPN book excerpt https://www.espn.com/sports-betting/story/_/id/38207435/how-bet-football-guide-nfl-ncaa-games-more ; repeated at https://www.covers.com/guides/betting-tips-from-pro-sports-bettor-billy-walters |
| 1.2 | His teams of handicappers produce "power ratings for every NFL team—and ratings on every single player". | [ASSERTED] | ESPN excerpt (above) |
| 1.3 | Rating update rule: new rating = 90% of the old rating + 10% of a "True Game Performance Level". So one game moves a team only slightly. | [ASSERTED] (Covers' paraphrase of the book) | Covers (above) |
| 1.4 | Player values: a QB is worth about a touchdown, with the best worth more. Top non-QBs are worth roughly 2.5-3 points. At least 60% of players are valued at about zero. Injuries are the "second-most important factor". | [ASSERTED] (Covers' paraphrase) | Covers (above). Shortform's "one negative point each" example conflicts with this and looks like an illustration, not his table: https://www.shortform.com/blog/billy-walters-sports-betting/ |
| 1.5 | Key numbers: "a point spread of 3 has the highest value, followed by 6, 7 and 14". He says half points matter but gives no values on any page I could read. | [ASSERTED] | https://realbillywalters.com/handicapping-system/ (his own site, sells consulting); ESPN excerpt |
| 1.6 | Timing: "Bet favorites early and underdogs late", because public money on favorites pushes underdog numbers up toward kickoff. Watch the market-leading books (Circa, MGM, Caesars, Pinnacle). | [ASSERTED] | ESPN excerpt; Covers; realbillywalters.com |
| 1.7 | Bet sizing: 1 unit = 1% of bankroll, bets of 0.5-3 units, never more than 3% on one event. "Start with the assumption that you'll lose it all." | [ASSERTED] | Covers; Shortform |
| 1.8 | Network and execution: runners/"beards" placed bets so books could not tell who was betting. The 2015 profile describes bets placed deliberately to move lines (e.g., bet at 3, add at 3.5, then bet the other side heavily at 4). His team included handicappers, news/injury scanners and runners: "What Billy is also able to do is handicap the handicappers." | [ASSERTED] (journalism from former associates) | ESPN The Magazine 2015 https://www.espn.com/espn/feature/story/_/id/12280555 ; Shortform (above) |
| 1.9 | He says he was limited or refused by Las Vegas and offshore books and ran a separate Panama operation. | [ASSERTED] | ESPN OTL 2018 https://www.espn.com/espn/otl/story/_/id/22946649/world-best-most-feared-sports-gambler-game-us-supreme-court-considers-legalizing-craft-espn |
| 1.10 | He claims a 57% regular-season NFL win rate. | [ASSERTED] (no audit) | Yahoo Sports 2024 https://sports.yahoo.com/super-bowl-2024-vegas-legend-billy-walters-sizes-up-the-big-game-for-you-175437020.html |

**Takeaway for review.** Walters' framework is power ratings, per-player injury values, a shrinking home-field value, key numbers and the timing of when you bet. It is a coherent method but mostly undocumented in public. His edge also depended on an execution network and large limits that a solo bettor at one soft book does not have.

---

## 2. Warren Sharp, as one example of a published NFL analyst

| # | Claim | Tag | Source |
|---|---|---|---|
| 2.1 | The company's lifetime NFL record is "1,781-1,295 (58%) +391.6 Units since 2006", and its "Computer Totals" record is 739-431 (63%). | [ASSERTED] (self-reported by the seller; no third-party audit, no pick timestamps, no closing-line comparison, no stated odds or staking) | https://www.sharpfootballanalysis.com/lifetime-betting-records/ |
| 2.2 | The records page gives no methodology for the totals model ("Warren Sharp's most accurate betting model"). The "$100 bettor won $X" figures don't state the odds or book. | [DATA] (absence verified on the page) | same page |
| 2.3 | The search summary showed the same site's figures changing between page versions (e.g., an older 1,578-1,140 lifetime). | (not opened: search snippet only) | sharpfootballanalysis.com search results |

**Takeaway.** Treat the record as marketing until it is graded against Pinnacle closing lines with timestamps. That standard is in Buchdahl's tipster method (section 5.4).

---

## 3. Haralabos "Bob" Voulgaris (NBA)

| # | Claim | Tag | Source |
|---|---|---|---|
| 3.1 | His original edge, around 2002: books set each half's total by splitting the full-game total about 50/50. He also read the end-of-game management of specific coaches (Eddie Jordan, Jerry Sloan, Byron Scott): "Those were three coaches I had nailed perfectly." | [ASSERTED] (profile, no data) | ESPN Playbook https://www.espn.com/blog/playbook/dollars/post/_/id/2935/meet-the-worlds-top-nba-gambler |
| 3.2 | Books then changed how they set halftime totals. He lost a third of his bankroll in the last month of 2003-04, "tilted", and took part of 2004-05 off. | [ASSERTED] | same |
| 3.3 | His later system was built from four parts:<br>- **Ewing:** a possession-by-possession simulator running tens of thousands of simulations, with player offence and defence values adjusted for matchup and age.<br>- **"Van Gundy":** projects lineups and minutes for each player.<br>- **"Morey":** a roster database.<br>An early bug assumed 88% league free-throw shooting instead of about 75%. | [ASSERTED] (description only) | same |
| 3.4 | Results he reported: "well over 1,000 bets per season", against about 350 when betting by feel. Ewing's ROI was above 6% in 2010-11 and 5.14% in 2011-12, a drop he blamed on books adjusting to his bets. "Every time you make a bet, you're educating the people taking the bets." | [ASSERTED] (self-reported ROI) | same |
| 3.5 | About 95% of his regular-season bets were totals (full game or halves). He tracked referee foul tendencies and play-by-play with shot location. | [ASSERTED] | ESPN TrueHoop https://www.espn.com/blog/truehoop/post/_/id/4966/a-professional-gambler-s-take-on-the-tim-donaghy-scandal |

**Takeaway.** The documented core is minutes and lineups → possession simulation → totals. He also shows that a structural edge decays once books notice it. Injuries and rest aren't detailed in what I read.

---

## 4. Bill Benter (1994): combining a fundamental model with the market

Source: W. Benter, "Computer Based Horse Race Handicapping and Wagering Systems: A Report", in Hausch, Lo and Ziemba (eds.), *Efficiency of Racetrack Betting Markets*, pp. 183-198. I read the full text of the scanned chapter: https://www.Gwern.net/doc/statistics/decision/1994-benter.pdf

| # | Claim | Tag |
|---|---|---|
| 4.1 | "The odds set by the public betting yield a sophisticated estimate of the horses' win probabilities." A fundamental model "must rival the public in sophistication and comprehensiveness." | [ASSERTED] |
| 4.2 | A fundamental model's probabilities are biased relative to the market. Where the model and the public disagree, actual frequencies sit between the two, "always in the direction of being closer to the public's estimate". | [DATA] (his Tables 3-4) |
| 4.3 | The fix is a second-stage conditional logit, c_i = exp(α·f_i + β·π_i) / Σ_j exp(α·f_j + β·π_j). Here f is the log of the *out-of-sample* model probability and π is the log of the public's implied probability. α and β are fitted by maximum likelihood, and α against β measures how right the model is relative to the market. | [DATA] (method plus fitted results) |
| 4.4 | Pseudo-R² for his model: public 0.1218, fundamental model alone 0.1245, combined 0.1396. The measure of value is the gain *over the public*: ΔR² = 0.0178. | [DATA] |
| 4.5 | In a test on 2,313 races, a "tipster" model with stand-alone R² ≈ 0.1014 (about the same as his 9-factor fundamental model's 0.1016) added almost nothing once combined with the public. The second stage "would have saved that player from losing money" because it would never flag a bet. | [DATA] |
| 4.6 | Kelly sizing: "if one overestimates the advantage by more than a factor of two, Kelly betting will cause a negative rate of capital growth… Overestimating the advantage by a factor of two is easily done in practice." Full Kelly drawdowns above 50% are "common". He recommends 1/2 or 1/3 Kelly. | [ASSERTED] (the factor-of-two point is standard Kelly math) |
| 4.7 | Results: about 5 person-years to build a model with an edge, plus 5 more to make it highly profitable. About 470 races bet per year; 4 of 5 seasons profitable, with one season losing about 20% of capital. Hong Kong pools were above $10M a race, so the final odds were predictable. "No statistical calculation made" but significance is "evident". | [DATA] (summary; partial) |
| 4.8 | For horses the model can't rate, "assign them the same probability as that implied by the public." He suggests 500-1,000 races are the minimum for building and testing a model. | [ASSERTED] |

**Takeaway.** Benter's central lesson is to fit the market as a feature. Measure your model by what it adds over the market price, out of sample. Here the market price is Pinnacle no-vig. A model that looks good on its own can add nothing.

---

## 5. Closing line value (CLV), no-vig price, Pinnacle as the reference

| # | Claim | Tag | Source |
|---|---|---|---|
| 5.1 | Pinnacle's own article: positive CLV is "one of the strongest indicators" of a sharp strategy. "At recreational sportsbooks, consistently achieving CLV is a key factor in whether your account gets limited." Opening NFL limits are about $3,000, rising past $100,000 by kickoff. | [ASSERTED] (Pinnacle, an interested party) | https://www.pinnacle.com/betting-resources/en/educational/what-is-closing-line-value-clv-in-sports-betting (read via raw HTML) |
| 5.2 | Buchdahl (on Pinnacle's site), using 158,092 soccer matches and 474,278 odds: with the margin removed, odds of 2.00 win about 50%, 3.00 about 33%, 4.00 about 25%. The opening-to-closing price ratio predicts profit at the opening price with a slope close to 1. Teams that opened at 2.20 and closed at 2.00 returned about +10% to the open and 0% to the close. He also notes that a market "might be collectively efficient but masking underlying inefficiencies on a bet-by-bet basis." | [DATA] | https://www.pinnacle.com/betting-resources/en/educational/how-to-solve-a-problem-like-efficiency-part-one/rn8j5rnqj2p8t68p |
| 5.3 | Football-Data (Buchdahl), 87,960 pre-close and close pairs, 2012/13 onward: expected yield (pre-close ÷ close) against actual yield has a slope of "almost exactly 1.00". The margin was not removed, so expected runs a few points above actual. | [DATA] (chart, no R² given) | https://football-data.co.uk/blog/pinnacle_efficiency.php |
| 5.4 | Buchdahl's tipster test: expected edge = advised odds ÷ no-vig Pinnacle close. Check shorten-versus-drift counts with a chi-square test and the price gap with a t-test. One tipster had 23 of 26 tips shorten (p ≈ 1e-5), implying a 6-7% expected yield from only 26 bets. A tipster claiming 78% wins and about 55% yield had 13 of 18 tips drift, which flags the record as unreliable. | [DATA] (small case studies) | https://football-data.co.uk/blog/closing_odds.php |
| 5.5 | **Counter-evidence: CLV alone isn't enough.** Whelan, NBA moneylines, 3,670 games 2022/23-2024/25, about ten US books. Three of the five positive-CLV deciles weren't profitable on average. The ninth decile averaged 5% CLV but returned about 0.2%. Only the top decile made real money (about 11.4%). The cause is the vig: you must beat the close by more than the margin. | [DATA] (blog by an economist; consensus-median close, not Pinnacle) | https://www.karlwhelan.com/?p=2595 |
| 5.6 | **Counter-evidence: Pinnacle's close may be drifting.** Pinho, re-running Buchdahl's public football-data: from 2023/24 onward, 6,806 bets with 4.2% expected value against the Pinnacle close returned only 1.9%. The suggested cause, citing Buchdahl, is arbitrage flow pushing Pinnacle's close off its own model. He warns 7,000 bets may not be enough sample. | [DATA] (soccer, recent, preliminary) | https://networked.substack.com/p/a-view-from-the-pinnacle |
| 5.7 | Moskowitz (J. Finance 2021), over 100,000 contracts across NBA, NFL, MLB and NHL: momentum (and, weakly, value) signals move prices from open to close, and those moves are "completely reversed by the game outcome". So in those cases the close moved *away* from fair. The effects are too small to beat transaction costs. | [DATA] | https://conference.nber.org/conf_papers/f92072/f92072.pdf ; summary https://insights.som.yale.edu/insights/what-sports-betting-teaches-us-about-financial-markets |
| 5.8 | A pro on Pinnacle's podcast: CLV is "a very, very good indicator" in the major US leagues, but less meaningful for props, where limits are small (see 10.1). | [ASSERTED] | https://www.pinnacle.com/betting-resources/en/educational/the-journey-to-becoming-a-successful-bettor-pinnacle-betting-podcast/5df2lxwl4gqtlfhb |
| 5.9 | Devig method matters. Pinho uses the "constant exponent" (power) method. Buchdahl's 2016 efficiency post left the margin in. Proportional normalisation is the simplest method and over-prices longshots under favourite-longshot bias. | [ASSERTED] (no head-to-head data opened) | Pinho (5.6); football-data (5.3) |

**Takeaway.** Using Pinnacle no-vig as the reference is well supported *on average* in soccer, with large samples. The evidence for NFL, NCAAF and NBA sides specifically is thinner in what I opened. Two cautions:
1. Positive CLV must clear the soft book's margin before it means profit (Whelan).
2. The close isn't perfectly efficient (Moskowitz, Pinho).

Track CLV per market type.

---

## 6. Line shopping, stale lines, soft books lagging sharp books, limits on winners

| # | Claim | Tag | Source |
|---|---|---|---|
| 6.1 | Kaunitz, Zhong and Kreiner (2017) built no model of their own. They bet when a book's odds beat the consensus-implied probability by a margin (α = 0.05). On 10 years of closing odds (479,440 games): 56,435 bets, 44.4% hit rate, +3.5% return. A random-bet control returned -3.32%, and the strategy was 10.8 SD above it. | [DATA] | arXiv 1710.02824, full PDF https://arxiv.org/abs/1710.02824 |
| 6.2 | In a realistic simulation (bets 1-5 hours pre-kickoff), 6,994 bets returned +9.9%. In paper trading, about 30% of the dashboard odds had already changed at the book by the time they checked. Paper trading: 407 bets, +5.5%. Real money: 265 bets, +8.5% ($957.50 profit at $50 a bet). | [DATA] |  same |
| 6.3 | "A few months after we began to place bets with actual money bookmakers started to severely limit our accounts." That meant stake caps, "manual inspection", and offers below their $50 stake, which ended the experiment. Limits also bias *which* bets get filled. | [DATA] (first-hand account) | same |
| 6.4 | Massachusetts Gaming Commission data from the operators: 0.64% of accounts were limited (Dec 10, 2024). Of those, 12.7% were capped below 1% of the default and 57.6% at 1-24%. Bettors who consistently beat the close were more likely to have their stake factor lowered, and raised-limit accounts were mostly VIPs. Reasons operators gave: "Winning/beating closing line value", arbitrage, courtsiding, automation or syndicate play. | [DATA] (regulator, primary) | https://massgaming.com/wp-content/uploads/Meeting-Materials-9.30.25-OPEN.pdf ; context https://www.covers.com/industry/massachusetts-limiting-vip-programs-sports-betting-data-april-2025 |
| 6.5 | Soft-book lag study (28 soccer fixtures, Aug-Sep 2026, 1x2 market, last 24 hours before kickoff), measuring how fast soft books follow a 1% Pinnacle move. Median follow time: 1xBet 6-13 minutes, Bet365 47-67 minutes. Each beats a random-timestamp control by about 7-9x and 2-3x respectively. Within 6 hours, 1xBet followed 83-94% of moves and Bet365 59-73%. | [DATA] (small; the author sells an odds API; shows coupling, not causation) | https://oddspapi.io/blog/soft-book-lag-pinnacle/ |
| 6.6 | Pinnacle says its limits "scale with market liquidity" and that it has "no restrictions placed on winning bettors". It says mainstream books reduce limits "after a few winning bets". | [ASSERTED] (Pinnacle marketing) | https://www.pinnacle.com/betting-resources/en/educational/why-pinnacle-offers-higher-betting-limits-than-other-sportsbooks |
| 6.7 | Voulgaris' ROI decay as books adjusted (3.4), and Walters being limited (1.9). | [ASSERTED] | see sections 1 and 3 |

**Takeaway.** "Bet the soft book when it lags Pinnacle" is a documented, profitable *mechanism*, shown in Kaunitz (soccer). Its two documented failure modes:
- **Stale quotes.** About 30% of signals were already gone when checked.
- **Account limiting.** Limits follow CLV, by the operators' own admission in Massachusetts.

A one-book bettor has no fallback once limited.

---

## 7. Academic market-efficiency research

### NFL

| # | Claim | Tag | Source |
|---|---|---|---|
| 7.1 | Levitt (2004), betting-contest data, about 20,000 bets, 2001 NFL. Bookmakers "do not play the traditional role of market makers": they set prices that exploit bettor biases. Win rates: visiting favourites 47.8%, home favourites 49.1%, home underdogs 57.7%. Bettors in aggregate were expected to win 49.45%. Home underdogs covered 53.2% in NCAAF 2002 and 53.0% in NBA 2002. | [DATA] (one season, contest bettors, a 2001-era market) | https://www.stat.berkeley.edu/users/aldous/157/Papers/Levitt_Gambling_2004.pdf |
| 7.2 | Szalkowski and Nelson, 2,560 NFL games 2002-2011: home teams covered 47%, and betting home underdogs went 53.5%. | [DATA] (abstract only) | https://arxiv.org/abs/1211.4000 |
| 7.3 | Moskowitz: the open-to-close moves that get reversed are too small to beat costs (see 5.7). | [DATA] | (5.7) |
| 7.4 | Home-field decline (nfelo): the trailing 10-season NFL home-field value fell from 2.9 points (2000) to 2.2 (2019). Single seasons are noisy (2.2 in 2018, -0.9 in 2019). Team-specific home-field value barely persists (R² close to zero), and division games should be lowered. | [DATA] (blog, reproducible) | https://nfeloapp.com/analysis/an-initial-exploration-of-home-field-advantage-in-the-nfl/ |
| 7.5 | Empty stadiums: NFL home teams performed "substantially lower" with no fans and slightly worse than visitors. Partial crowds didn't differ significantly from full ones. | [DATA] (abstract only) | https://arxiv.org/abs/2104.11595 |
| 7.6 | When home advantage disappeared (Bundesliga after the COVID break), bookmakers were slow to re-price it, which allowed profitable strategies. | [DATA] (abstract only; soccer) | https://arxiv.org/abs/2008.05417 |
| 7.7 | Weather: Borghesi (2008), NFL 1984-2004. Heat, wind and rain reduce scoring, and "the market does not accurately incorporate the effects of adverse conditions into totals". A weather-aware strategy beat 52.38% out of sample. | [DATA] (abstract only) | https://econpapers.repec.org/RePEc:taf:apfiec:v:18:y:2008:i:12:p:947-953 |
| 7.8 | Covers/Roth, 2,720 outdoor games 2010-2025, unders against the closing total, by wind: under 10 mph 48%, 10-15 mph 56%, 16-25 mph 54%, 25+ mph 59%. "Bet wind games early, before the total collapses." | [DATA] (practitioner; no significance tests; no per-bucket n) | https://www.covers.com/nfl/how-wind-impacts-nfl-games |
| 7.9 | **[DATA: own calc]** nflverse, outdoor and open-roof games, game-time wind against the closing total. Under rates:<br>- 1999-2014: under 10 mph 49.6% (n≈1,954); 10-14 mph 50.5%; 15-19 mph 56.9% (n=313); 20+ mph 58.1% (n=136).<br>- 2015-2026: under 10 mph 47.6%; 10-14 mph 59.2% (n=463); 15-19 mph 58.2% (n=177); 20+ mph 50.0% (n=48).<br>**Caveats:** this is observed game wind, not the forecast available at bet time; the sample is small above 20 mph; there are no significance tests. | [DATA] | nflverse games.csv |
| 7.10 | **Injury pricing (NBA).** Dare, Dennis and Paul (2015): openers have significant errors when a player is absent, but "no profitable strategy exists when wagering at the closing line". | [DATA] (abstract only) | https://ideas.repec.org/a/eee/finlet/v13y2015icp130-136.html |
| 7.11 | **Injury pricing (NFL).** Caesars' head of football says the book undervalued backup QBs, and "The traders only react to injuries once the timeline for the absence is confirmed." Example: Bears -1.5 to +4.5 after a QB injury. | [ASSERTED] (bookmaker quotes) | https://www.espn.com/nfl/story/_/id/50111576 |
| 7.12 | **Gap.** I found no peer-reviewed study testing whether NFL practice participation (DNP/LP/FP) is priced into lines. | n/a | searches returned only injury-report pages |

### College football

| # | Claim | Tag | Source |
|---|---|---|---|
| 7.13 | Sinkey and Logan (2009), more than 11,000 games 1985-2003: the market is inefficient and favourites are systematically overpriced. Away favourites were 4.35% less likely to cover. They suggest books inflate favourite lines against "hot hand" bettors. | [DATA] (old data; working paper) | https://www.aeaweb.org/conference/2010/retrieve.php?pdfid=406 |
| 7.14 | Paul, Weinbach and Higger (2013): in AQ (power conference) vs non-AQ games, AQ teams win by *more* than the spread implies, while drawing a disproportionate share of bets. | [DATA] (abstract only) | https://ideas.repec.org/a/buc/jpredm/v7y2013i2p29-41.html |
| 7.15 | Bennett (2019, *Atlantic Economic Journal*): the previous season's top 10 are overvalued in the next season's opening game, consistent with stale preseason priors. | (not opened: Springer paywall; search snippet only) | https://link.springer.com/10.1007/s11293-019-09611-y |

### NBA

| # | Claim | Tag | Source |
|---|---|---|---|
| 7.16 | Girdner et al. (2013), NBA totals 2009-2012: "generally very efficient", except week 1, when 58.2% of games went under (an 11.1% average return betting every under). | [DATA] (abstract; old) | https://ircommons.uwf.edu/esploro/outputs/journalArticle/Early-season-NBA-overunder-bias/99380090347306600 |
| 7.17 | Uhrín et al., 16,000 NBA moneyline games 2000-2015: their model (accuracy 0.68) was *worse* than the bookmaker (0.70), and full Kelly on it went 100% bust (see 9.3). | [DATA] | https://ar5iv.labs.arxiv.org/html/2107.08827 |
| 7.18 | **Gap.** Rest and back-to-back pricing: I found no peer-reviewed study. Practitioner pages give conflicting 1-5 point effects. | [FOLKLORE] (as usually stated) | search results only |

**Takeaway.** The literature mostly finds *statistical* biases, such as home underdogs, overpriced favourites, weather in totals and week-1 NBA unders. These often come from old data and shrink or vanish at the close. Injury information is mispriced at the *open* and corrected by the close (NBA). That supports betting early on information, not models of the close.

---

## 8. Teasers and key numbers

| # | Claim | Tag | Source |
|---|---|---|---|
| 8.1 | *Sharp Sports Betting* by Stanford Wong (Huntington Press; current edition Oct 2021, 400 pp.) covers "the logic and math for making intelligent sports wagers, including analyses of parlays, teasers, and props". | [ASSERTED] (publisher page) | https://huntingtonpress.com/?p=2357 |
| 8.2 | Break-even per leg for a 2-team, 6-point teaser: -110 needs 72.4%; -120 needs 73.8%. (√(110/210) = 0.7237; √(120/220) = 0.7385.) | [DATA] (arithmetic) | https://www.teamrankings.com/blog/sports-betting/teasers-betting-nfl-key-numbers-wong |
| 8.3 | Wong-style legs 1999-2010 (as reported by TeamRankings): home favourites -7.5 to -8.5 went 128-42-3 (75%); home underdogs +1.5 to +2.5 went 120-42-2 (74%); away underdogs +1.5 to +2.5 went 170-60 (74%); away favourites -7.5 to -8.5 went 43-25 (63%). | [DATA] (secondary) | same |
| 8.4 | Covers says 15.2% of games land on 3 and 9.0% on 7. Restricting teasers to totals of 49 or less "adds about 1.0%" per leg, and road legs do 3-4.5% better than home legs. | [ASSERTED] (no sample given for the splits) | https://www.covers.com/nfl/teaser-strategy |
| 8.5 | The 2015 extra-point move cut XP success from 99.2% to 94.1%. Margins of 6 and 8 combined rose by 2.4 percentage points (2015-23 vs 2006-14). | [DATA] | https://www.covers.com/nfl/key-numbers |
| 8.6 | **[DATA: own calc]** Absolute final margin frequency, nflverse, all games:<br>- 1999-2014 (n=4,248): 3 15.3%, 6 5.3%, 7 9.3%, 8 3.3%, 10 6.0%, 14 4.7%<br>- 2015-2019 (n=1,335): 3 14.4%, 6 7.3%, 7 9.9%, 8 4.1%, 10 4.6%, 14 5.7%<br>- 2020-Nov 2026 (n=1,855): 3 15.3%, 6 6.8%, 7 7.8%, 8 4.5%, 10 4.8%, 14 4.7%<br>So 3 holds steady, 7 is lower recently, and 6 and 8 are higher since 2015. | [DATA] | nflverse games.csv |
| 8.7 | **[DATA: own calc]** Wong legs (+1.5 to +2.5 and -7.5 to -8.5, teased 6, against the consensus closing spread):<br>- 1999-2014: 470-174-4 (73.0%)<br>- 2015-2019: 230-70-2 (76.7%)<br>- 2020-2026: 377-119 (76.0%)<br>Splits for 2020-2026: away underdogs 145-41 (78.0%), home underdogs 117-34 (77.5%), away favourites 37-13 (74.0%), home favourites 78-31 (71.6%). In 2015 onward, legs with closing total ≤44 hit about the same as those above 44 (76.6% vs 76.7%; 76.1% vs 76.0%). That *contradicts* the low-total rule for this period, though it held in 1999-2014 (74.1% vs 70.8%). | [DATA] (consensus close, not the price you'd get; teaser prices and push rules vary; small cells) | nflverse games.csv |
| 8.8 | Two-team 6-point teasers once priced at -110 are now often -120 or -130 at many books, and some restrict which spreads qualify. | [ASSERTED] | search snippet (not opened) |

**Takeaway.** On closing consensus numbers since 2015, the Wong legs (about 76%) still clear the -120 break-even (73.8%) and -130 (75.2%) narrowly. That edge is lost if the soft book's numbers are worse than consensus, or if the book prices teasers off the key numbers. The "low totals" refinement isn't supported by 2015-2026 closing data.

---

## 9. Kelly, uncertainty, correlation, sample size

| # | Claim | Tag | Source |
|---|---|---|---|
| 9.1 | Benter: overestimating the edge by more than 2x makes Kelly growth negative. Use 1/2 to 1/3 Kelly. | [ASSERTED] (math) | (4.6) |
| 9.2 | Buchdahl simulation: 1,000 bets at -110 with a true 2.5% edge, staked at 2.75% Kelly, end in a loss about 34% of the time. If you *believe* 5% and stake 5.5%: P(profit) is about 50% and P(losing ≥90%) is above 8%. Half Kelly raises P(profit) from 66% to 73% and cuts P(halving the bankroll) from 10% to about 1%. | [DATA] (Monte Carlo) | https://football-data.co.uk/blog/kelly_staking.php |
| 9.3 | Uhrín et al. (2021) on horse racing, NBA and soccer. Full Kelly or max-Sharpe went bust in 100% of NBA and soccer trajectories (the model was weaker than the bookmaker). Fractional Kelly had 0% ruin in all three domains and was "the most suitable option", with the fraction tuned. They recommend "survival first" tuning. | [DATA] | https://ar5iv.labs.arxiv.org/html/2107.08827 |
| 9.4 | Chu, Wu and Swartz (2018, JQAS): with the win probability unknown, the decision-theoretic Kelly fractions are "smaller than original Kelly" and depend on the loss function. | [DATA] (abstract) | https://econpapers.repec.org/RePEc:bpj:jqsprt:v:14:y:2018:i:1:p:1-11:n:3 |
| 9.5 | Buchdahl on luck against skill: at a 10% yield, about 540 even-money bets are needed for significance. At 9/1 odds, the same confidence needs about 34% yield. 200 bets at 10% yield and 1.66 average odds give p ≈ 0.037, which is "not yet… evidence". He prefers p < 0.01 or tighter. | [DATA] (t-test shortcut) | https://football-data.co.uk/blog/luck_skill_sports_betting.php |
| 9.6 | **[DATA: own calc]** Bets at -110 (break-even 52.38%), normal approximation:<br>- True **54%**: about **3,600** bets before a 95% CI excludes break-even on average; about **5,900** for 80% power (one-sided α=0.05).<br>- True 55%: about 1,400 and 2,200.<br>- True 53%: about 25,000 and 40,000.<br>CLV converges much faster than results (5.4), which is why CLV is used as the interim metric. | [DATA] | arithmetic |
| 9.7 | **Correlation.** Benter notes the multiple-bet Kelly solution is complicated by bets that share outcomes. I found no sports-specific data on correlated props or same-game exposure. | gap | (4) |

---

## 10. Player props

| # | Claim | Tag | Source |
|---|---|---|---|
| 10.1 | Rob Pizzola on Pinnacle's podcast: props are "not really all that efficient just because the limits on props are generally so small… a couple 100 dollars, maybe 500 dollars," which keeps sharps out. | [ASSERTED] (practitioner, on a sharp book's site) | https://www.pinnacle.com/betting-resources/en/educational/the-journey-to-becoming-a-successful-bettor-pinnacle-betting-podcast/5df2lxwl4gqtlfhb |
| 10.2 | Pinnacle (soccer props): bookmakers often limit accounts that find value in player-prop markets. | (not opened: search snippet) | https://www.pinnacle.com/en/betting-articles/Soccer/soccer-goalscorer-player-props/4YYJG2TJSUH4NLCZ |
| 10.3 | 4for4, NFL *season-long* props at closing lines: unders hit 63% in 2021 (n=269) and 60% in 2022 (n=335). QB passing-yard unders hit 74% (n=58). The author says the decline reflects a market "becoming a bit sharper". | [DATA] (practitioner; small n; season-long, not weekly) | https://www.4for4.com/2023/preseason/key-winning-season-long-player-props |
| 10.4 | PFF, weekly NFL props, 2020 to mid-2022: passing-yard unders were the only category profitable to bet blind (+14.06 units). RB receiving-yard unders went +108 units. Receiving overs were "very hard to profit from". | [DATA] (no hit rates or n in text) | https://pff.com/news/nfl-betting-2022-midseason-player-prop-performance-review |
| 10.5 | Footballguys: blind unders were very profitable for about the first 6 weeks of 2022 and 2023, then roughly broke even. | [ASSERTED] (this refers to game totals in that article) | https://www.footballguys.com/article/2024-odds-and-ends-week08 |
| 10.6 | Explanations: public bettors play overs and pros play unders, and stat distributions are right-skewed (median below mean), so lines are set to median or shaded toward overs. | [FOLKLORE] (no primary data found; second-hand Peabody attributions only) | search snippets (not opened) |
| 10.7 | A Claremont thesis (FanDuel NBA prop closes, 178 players 2022-25) found no consistent directional bias. | (not opened: snippet) | https://scholarship.claremont.edu/cmc_theses/4171 |

**Takeaway.** Props are softer mainly because limits are low and books have less information about individual players. The "unders bias" has some data but small samples, mostly from 2020-2022. It appears to shrink as markets mature and early in the season. With small limits and fast account limiting, the scale available from props is tiny.

---

## Sources I could not open, or that failed

| Source | Why |
|---|---|
| Review-Journal Walters interview (https://www.reviewjournal.com/?p=2890809) | 403 |
| Action Network Walters on Rogan (https://www.actionnetwork.com/general/billy-walters-sports-betting-tips-strategies-joe-rogan-experience) | 403 |
| Action Network teaser guide (https://www.actionnetwork.com/nfl/teaser-tips-strategy-guide) | 403 |
| ESPN Chalk, September most profitable month (https://africa.espn.com/chalk/story/_/id/27435784/...) | 404 |
| Bennett 2019 (Springer) | Paywall/redirect |
| Buchdahl CLV piece mirrored on pod-*.vercel.app | 410 Gone |
| Pinnacle betting-strategy index | 404 (individual articles read via raw HTML instead) |
| Las Vegas Sun 2001 Wong teaser column | DNS failure |
| DocSports "6,967 NFL games" key-number study | Page served unrelated content; figures from search snippet only, not used |
| NFL Football Ops 2020 home-field article (operations.nfl.com) | 404. Snippet said 1.3 points in 2020 vs 3.3 in 2006; not used |
| Kuper (Berkeley undergrad thesis, one NFL season) | Opened; too weak to cite |
| Venkatesh & Bulthuis (Wharton) | Opened; about 2-point strategy, not betting |
| ESPN Magazine Voulgaris profile (es.pn/2bmMiAP) | Redirected to 404 |
| *Squares & Sharps, Suckers & Sharks* | Only bookseller listings found; no excerpt opened |
| Benter, faithful secondary summary | Not needed; primary text read |
