# 24a. Sources: outside models, handicappers and market efficiency, NFL, college and NBA (Nov 24, 2026)

Extends 14a, 18a and 23a; does not repeat them (Walters, Benter, Voulgaris, Buchdahl, Whelan, Kaunitz, Levitt, the Massachusetts limits
data, Wong teasers and the 4for4/PFF prop data are there). Three research helpers, one per sport, about 240 searches and page reads;
I checked the numbers used in `24-full-audit.md` and re-ran the one that became a test (N1, which failed to replicate).

**Tags.** [DATA] a public record, a paper with numbers, or a calculation from free files (named). [CLAIM] a seller's or author's own
record, or a search snippet only. [OPINION] judgement. "Own calc" means a helper computed it from the file named; the scripts were in the
session scratchpad and are not kept, so treat own-calc figures as leads unless they appear in `24-full-audit.md` with a kept script.

## Across all three sports

- **More than 600 published simple betting strategies (NFL, NBA, college, AFL): none significantly profitable after costs once corrected for
  testing many ideas; profit shrinks as sample size grows.** They recommend |z| > 3 as the bar. Vandenbruaene, De Ceuster & Annaert, *Journal
  of Sports Economics* 23(7), 2022. [DATA] https://repository.uantwerpen.be/docstore/d:irua:11659
- **Experts and computer systems against the spread: 50%, not better than chance** (70 experts, 32 systems, about 18,000 forecasts). Song,
  Boulier & Stekler, *International Journal of Forecasting* 2007. [DATA] https://ideas.repec.org/a/eee/intfor/v23y2007i3p405-413.html
- **Soft books follow Pinnacle with a lag.** Soccer only: median 6-13 minutes (1xBet) and 47-87 (Bet365) [DATA] https://oddspapi.io/blog/soft-book-lag-pinnacle/ ;
  a vendor says 10 seconds to 90 minutes, typically 5-15, in the US [CLAIM] https://sportsbookish.com/research/how-sportsbooks-reprice-without-news .
  **No NFL, college or NBA lag study exists; our own logs are the only way to measure Wagerhouse** (test L1).

## NFL

**Rating systems, graded by a third party (The Prediction Tracker, against the midweek line)** [DATA] https://www.thepredictiontracker.com/nflresults.php?year=23 , ?year=24 , ?year=25

| System | 2023 | 2024 | 2025 |
|---|---|---|---|
| Updated line | 49.4%, error 10.00 (lowest) | 47.7%, 9.78 | 50.4%, 9.69 (lowest) |
| nfelo | not tracked | 42.1% (237 games) | 46.1% |
| ESPN FPI | 48.9% | 50.2% | 44.0% |
| Sagarin | 42.8% | 47.5% | 47.7% |
| Massey | 42.6% | 48.2% | 45.3% |

- Each year's top system changes (53.0%, 55.9%, 54.3%); with about 60 systems on about 285 games, a best near 55% is chance. [OPINION, arithmetic]
- Free per-game files with opener, midweek, updated line and every system's line: `https://www.thepredictiontracker.com/nflYY.csv`. [DATA] Used in test F1.
- **nfelo's own record** (self-hosted; play selection not stated): 54.9% against the close 2009-2026, average closing-line value 5.85%, but
  close ATS 51.5% / 48.1% / 52.4% in 2023-2025 and value per play 13.2% → 3.2% → 2.6%. It weights the market at 65% itself. [CLAIM]
  https://www.nfeloapp.com/games/nfl-model-performance ; https://www.nfeloapp.com/analysis/using-market-regression-to-improve-prediction-accuracy-in-the-nfl/
- **538 Elo, QB Elo, ESPN FPI against moneylines** (Robbins, East Carolina): −3.7% (2014-2022), −6.7%, −2.5%; best in each model's first
  public year; "the odds are more accurate than the models". [DATA] https://myweb.ecu.edu/robbinst/PDFs/Betting%20on%20FPI%20-%20DSI.pdf
- **An open-source EPA model** (2021-2025, 1,344 games): spread error 10.44 against 9.78 for the close; a QB-out term made it worse. [DATA, hobbyist] https://codeberg.org/mck10/haunter-model
- DVOA/FTN, PFF Greenline, Unabated, inpredictable: no season record against the line found. [gap]

**Handicappers and contests**
- Westgate SuperContest winners at 65-76% on 85 picks in fields of 345-3,123: what chance produces. [DATA] https://www.casino.org/news/westgate-supercontest-awards-winner-nfl-contest-breaks-record/ ; random picking about −1% EV against the 8% rake [DATA, one season] https://analytics.bet/articles/ev-in-the-supercontest/
- SuperContest "top five consensus" picks 207-222-11 (2013-2018). [DATA, secondary snippet]
- Pregame.com audited at 51.67%. [DATA, journalism] https://deadspin.com/how-america-s-favorite-sports-betting-expert-turned-a-s-1782438574/
- No persistence study of contest winners found. [gap]
- Circa opens with $3,000 limits to anyone and raises them through the week. [DATA] https://africa.espn.com/chalk/story/_/id/32209480/betting-market-watch-nfl-college-football-line-moves-early-action-bookmaker-insights

**Market efficiency by market**
- **Totals unders at 47.5+:** 58.7% 1979-2000, 59.7% 2001-09, then 47.1% 2010-18. [DATA] https://mobile.aabri.com/manuscripts/193138.pdf
- **Own calc on nflverse closing totals:** primetime unders 55.1% 2018-2026 but 49%, 52%, 44% in 2024-2026 after the trend was publicised;
  Thursday, short rest and Week 1 unders unstable or gone. [DATA, own calc]
- **Opener against close, 2002-2011:** no significant difference in accuracy; about 10% of games moved 2+ points. [DATA] https://arxiv.org/abs/1211.4000
- **First halves:** first-half spreads are "almost always more than 50%" of the full-game spread and bunch on key numbers; books take a
  higher hold on halves. [DATA, seasons not stated] https://www.pff.com/news/bet-optimizing-spread-bets-with-first-half-lines . No
  peer-reviewed NFL first-half, quarter or prop study found. [gap]
- **Team totals** bunch on 17, 20, 23, 24, 27. [DATA, one season] https://www.covers.com/nfl/key-numbers

## College football

**Rating systems: the Prediction Tracker re-graded by era** (`ncaaYYYY.csv`, https://www.thepredictiontracker.com/ncaaarchive.html ; 3+ points from the line) [DATA, own calc]

| System | 2010-19 at opener | 2021-26 at opener | 2021-26 at close |
|---|---|---|---|
| PI-Rate Bias | 1420-1178 (54.7%) | 1154-1144 (50.2%) | 48.9% |
| Pi-Ratings | 1790-1523 (54.0%) | 1138-1124 (50.3%) | 48.1% |
| Keeper | 2412-2070 (53.8%) | 1440-1360 (51.4%) | 49.2% |
| Dokter Entropy | 50.9% | 826-717 (53.5%) | 840-757 (52.6%), the one system above 52.4% of about 50: what chance gives |
| ESPN FPI | 51.1% | 52.0% | 49.5% |

- Caveat: the files do not record when each system published, so results against the opener can carry look-ahead in both eras. The era
  comparison is fair; the levels are not. [DATA]
- **SP+** is graded only against the midweek line, by its author, between 48% and 56% by season. [CLAIM] e.g. https://x.com/ESPN_BillC/status/1201119238636949505
- **Coleman (2025, *Journal of Sports Analytics*):** a five-system blend from 29 systems, 2016-24, adds information beyond the opener, not the
  close (error 12.26 against the close's 12.06). [DATA, abstract] https://journals.sagepub.com/doi/10.1177/22150218251365223
- **A public CollegeFootballData model** claims 53.8% against the opener at 3+ points apart (2024+ holdout), with lines moving toward it
  (t = 12.6). This contradicts our research 23 T4 (801-775). [CLAIM] https://github.com/CarsonBillig/football-model
- **Makinen (VSiN) 2025, own grading:** Power Ratings 52.2% where 3+ off the close. [CLAIM] https://vsin.com/college-football/college-football-2025-results-from-the-makinen-strength-ratings/

**How much the opener moves, and what a perfect read of the move is worth** (bet at the opener in the direction the line later moved) [DATA, own calc]
- Regular season 2021-25: average move 1.29 points; 1319-1134 (53.8%).
- CollegeFootballData 2022-26: sides 54.1%, totals 57.3%.
- **Bowls:** move 2.3-2.5 points; 86-48 (64.2%) postseason 2022-25 and 118-87 (57.6%) Prediction Tracker 2021-25. Bowl openers are the one
  place the opener is clearly worse than the close (0.62 points).
- Reading: on regular-season sides, even knowing where the line will go is worth about 54%. Bowls and news are where the room is. [OPINION]

**Handicappers, contests, practitioners**
- No third-party-verified college record found. Action Network's in-app record for one expert, 53.1% on 1,425: self-logged. [CLAIM] https://www.actionnetwork.com/ncaaf/picks/top-experts
- SuperContest College 2025 winner 67.7% on 98 picks: chance, at that field size. [CLAIM/OPINION] https://www.westgateresorts.com/hotels/nevada/las-vegas/westgate-las-vegas-resort-casino/casino/supercontest-college/
- Bowl lines are "information-based" moves (opt-outs, coaching changes); books get the news from the same social media as bettors. [CLAIM] https://www.espn.com/espn/betting/story/_/id/47307193/college-football-betting-2025-bowls-lines-opt-outs-coaching-changes
- Peabody: the market overweights recent results and misreads fumble luck; his college second-half model. [CLAIM] https://www.rotowire.com/football/article/beating-the-book-qa-with-rufus-peabody-40172 ; https://thepowerrank.com/the-craft-of-sports-betting-professionals-2/

**Papers and data**
- Line moves not explained by public ratings predict results (informed money). [DATA, abstract] https://ideas.repec.org/a/taf/apfiec/v15y2005i3p143-152.html
- Following reverse line moves on college totals 2005-2016: not profitable. [DATA, abstract] https://ideas.repec.org/a/spr/jecfin/v43y2019i4d10.1007_s12197-019-09479-3.html
- After the close, no movement bucket of 100+ games is far from 50% (15,774 games since 2008). [DATA] https://betiq.teamrankings.com/college-football/betting-trends/ats-results-by-line-movement/
- **Bennett (2021):** small-conference teams after a big miss, 54.2% in 2006-2018. [DATA, abstract] https://econpapers.repec.org/RePEc:taf:apeclt:v:28:y:2021:i:12:p:1006-1009 . **Our out-of-sample test C1 (2021-2026): 48.5%, failed.**
- Home field after COVID is priced: home side against the close +0.23 ± 0.25 points (3,577 FBS games, 2022-2026). [DATA, own calc]
- NIL funding not fully priced (UNLV poster, 2026). [CLAIM] https://oasis.library.unlv.edu/gaming_institute/2026/May27/61 . Funding data is not free.

## NBA

**Rating systems** [DATA, own calc on Prediction Tracker files, https://www.thepredictiontracker.com/basketball.php ]
- 2021-22 to 2025-26, against the close, every disagreement: ESPN BPI 3149-3069 (50.6%); every other system 48.6-49.8%; none above 51% at 3+
  points apart.
- **BPI against the opener, 1.5+ apart, 2021-2026: 1989-1708 (53.8%, z 4.6). Our out-of-sample test N1 on 2018-19 to 2020-21: 900-878
  (50.6%). It did not replicate.**
- The close beats the opener every season; the average open-to-close move is 1.1-1.4 points. Betting the eventual move at the opener
  (hindsight) 55.6%; at the close 50.7%.
- EPM (Dunks & Threes): game error 11.0 in 2024-26, no comparison to the line published. [CLAIM] https://dunksandthrees.com/about/epm .
  DARKO, LEBRON, RAPTOR's archive, Net Points, Inpredictable: no record against the line. [CLAIM/gap] https://www.darko.app/ ; https://github.com/fivethirtyeight/data/tree/master/nba-raptor

**Handicappers and pros** (none verified by a third party with closing-line value [gap])
- "Minutes first, then usage; books are slow to adjust to rotation changes" (a Juice Reel bettor, promotional). [CLAIM] https://juicereel.beehiiv.com/p/player-props-mastery
- "Minutes is money. So is usage"; spreads move first, props follow quickly. [CLAIM] https://amicsta.substack.com/p/how-to-beat-nba-props
- After injury news lines "often overshoot and then return". [CLAIM] https://fiddlespicks.substack.com/p/navigating-nba-injury-news-with-an
- Beating books to injury news gets accounts limited. [CLAIM/OPINION] https://www.sportsbookreview.com/forum/sportsbooks-industry/1961672-how-do-sportsbooks-deal-with-injuries-that-affect-the-odds-significantly

**Papers and data**
- Absences: 10,555 games, the line moves away from the side with absences; openers carry errors, the close does not. [DATA, abstract] https://www.sciencedirect.com/science/article/abs/pii/S1544612315000227 . Our research 13 agrees (the close carries absences).
- Props and legal betting: FanDuel prop closes 2022-25, legal mobile betting linked to larger misses against the prop line, no consistent
  Over/Under direction. [DATA] https://scholarship.claremont.edu/cmc_theses/4171
- **2026-27 prop rules at US books:** no Unders on players expected under 12 minutes, no same-player multi-Under parlays, no "first to"
  props; earlier, no props on two-way and 10-day players. [DATA] https://www.deseret.com/sports/2026/10/16/nba-sportsbooks-agree-to-ban-several-types-of-player-prop-bets-amid-gambling-concerns/
- Rest: home teams on the second night of a back-to-back did poorly against the spread over 19 seasons (2010 paper); 1.25 points for no
  rest, 2003-2010. [DATA] https://econpapers.repec.org/RePEc:sae:jospec:v:11:y:2010:i:6:p:602-613 ; https://www.inpredictable.com/2012/02/nba-home-court-advantage-and-rest.html . Our research 14 found it priced now.
- In-play overreaction to early baskets (Betfair, 5 million transactions). In-play only, out of scope. [DATA] https://newsroom.haas.berkeley.edu/magazine/spring-2025/the-over-under-conundrum/

**Speed and limits**
- **The official injury report's PDFs are free back to January 2021** (hourly files to Dec 2025, 15-minute files since). This corrects
  research 08's "no free history". [DATA, helper probed with curl] `ak-static.cms.nba.com/referee/injury/Injury-Report_<date>_<time>.pdf`
- Report deadlines: 5pm local the day before; game-day update 11am-1pm local. [DATA] https://www.thescore.com/nba/news/3432280
- Pinnacle NBA opening limits about $5k spreads / $2k totals, raised to full by about 7am PT on game day, so its opener is a low-limit
  price. Pinnacle NBA props are "must play" since Feb 2023: a grader must void props whose player doesn't play. [DATA, dated snippet / CLAIM]
  https://www.sportsbookreview.com/forum/sportsbooks-industry/2013342-pinnacle-nba-player-props-rules-changed

## Gaps that stay open

- No timed study of soft-book against sharp-book reaction in any of the three sports (test L1 is ours).
- No peer-reviewed first-half, quarter or prop efficiency study in any of the three sports.
- No third-party-verified handicapper record with closing-line value in any of the three sports.
- When the Prediction Tracker captures its opener and its system lines (it limits what F1 can prove).
