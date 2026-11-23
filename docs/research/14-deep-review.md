# 14. Deep review: where real money could come from, and what to build, stop and change

Written Monday Nov 23, 2026, Mountain, by an outside-review session. No engine code, config or schedule was changed. State reviewed: commit `19b5a89`, working tree clean at the start. Every test below is walk-forward (each season judged only on rules fitted to earlier seasons) and compared against the closing line. Scratch scripts are in this session's scratchpad (`work/`); I'll move them into `scripts/` if you say so.

---

## The answer first: where could real money come from, and how sure am I?

**At $25 a bet, no part of this engine is likely to make "real money" in the sense of a second income. Over a season, the realistic upside of everything that has evidence behind it is a few hundred dollars. The two places with real evidence are not models at all.**

1. **Wong teasers at your book: the strongest evidence in this review.** Wagerhouse pays −110 on a 2-team, 6-point teaser (that is what your own tickets show: to-win ÷ risk = 0.909). At −110 each leg needs to win 72.4% of the time. NFL favorites of 7.5 to 8.5 and underdogs of 1.5 to 2.5, teased through both 3 and 7, won **75.8% on 264 legs in 2023 to 2026** when the total was 49 or lower, and 75 to 79% in every era since 2010. The rule was published in 2001, so every one of those seasons is out of sample for it. Expected value is about +10% per ticket at the recent rate and zero if the true rate is 72.4%. The underdog legs (+1.5 to +2.5) carry most of it; the "total 49 or lower" filter is weaker than its reputation (section 1). It's also small: about 2 tickets a week, roughly **$90 to $175 a season** at $25 to $50. **How sure:** about 65% that it is still a real edge at Wagerhouse today. The doubts are the small recent sample, books that quietly re-price these teasers, and the 2023 to 2026 rate being the lowest of the four eras.
2. **Being faster than Wagerhouse after news: the only edge that fits your "be the one holding +10" goal, and still unproven.** When a starting quarterback is newly out, the NFL line moved **2.4 to 2.7 points** between the opener and the close (669 games, 2023 to 2025). Injury news explains about 15% of all weekly line movement. A bet placed before your book moves on that news is worth roughly +10% or more. Our own logs caught Wagerhouse trailing Pinnacle by 1 to 6 hours on 4 of 15 NFL moves, but that is two days of hourly reads. In the NFL these events are rare (about one quarterback a week across the league). NBA availability news is daily, so if this edge exists, **NBA is where its volume is**. **How sure:** about 40% that Wagerhouse trails often enough, and by enough minutes, for you to act by hand at least 20 times a season. This is the most important thing to measure in the next four weeks.
3. **Wind unders: real in history, fading.** The re-run today matches the write-up: Unders went 321-221 on held-out seasons since 2019, but only 75-63 since 2024. Using the day-before forecast since 2024 they went 96-77 at a 1-point edge and 44-44 at a 2-point edge. **How sure:** about 40% that it still pays after the market's adjustment. Keep it at a half-unit Conditional, as it is.
4. **Your own models against the closing line: almost certainly not.** Today I ran three more tests the handoff asked for, and all three failed: the official NFL injury report including practice participation (2,389 games), college football's ~60 public rating systems (8,283 games), and NBA rest, travel and schedule density (4,194 games). That makes eight failures in eight tries. **How sure:** under 5% that a free-data model beats Pinnacle's full-game close in any of the three sports.

**The biggest dollar figure isn't a model.** From the audit (`01-bet-audit.md`), you risked $14,023 in 11 weeks. At the prices the audit measured (−4.5% to −6.1% per dollar), that volume costs about **$630 to $860 in expectation**, more than every edge above combined would make in a season. That is arithmetic, not advice about how to bet. It's the yardstick for what the engine is worth to you.

**What I'd do:** keep one engine with shared plumbing and three sport lanes, each with its own edge to prove. Make the speed measurement and the stale-number alerts the core of NFL, NBA and college. Add a Wong-teaser lane if you say yes (written case below). Freeze model-building on full-game sides and totals.

---

## Contents

1. What the best bettors and the research actually say (with sources)
2. Tests run today on our own historical data
3. Is the premise right?
4. Split the sports or not?
5. Ranked list: build, stop, change (each with its test and kill number)
6. Each lane after this plan
7. Four-week schedule
8. Corrections to the engine's own text
9. What this review could not do

---

## 1. What the best bettors and the research actually say

A research agent opened about 50 sources for this section; its full brief, with a quote and a tag for every claim, is `docs/research/14a-sources.md`. I did not reopen the pages myself. Tags: **[DATA]** the source shows data; **[ASSERTED]** stated without data; **[FOLKLORE]** widely repeated, no traceable source. "(not opened)" means only a search snippet was seen. Pick sellers and affiliate pages were discarded.

### What each school actually does

**Billy Walters (power ratings, player values, key numbers, timing).** The book's full text could not be opened; these come from an ESPN excerpt and summaries.
- Home field "generally thought" 3 points, about 2.5 over 1974-2022, under 1 point in the last four seasons [ASSERTED] (https://www.espn.com/sports-betting/story/_/id/38207435/how-bet-football-guide-nfl-ncaa-games-more).
- Ratings update as 90% old rating plus 10% latest true performance; a quarterback about a touchdown, top non-quarterbacks 2.5 to 3, most players about zero [ASSERTED, Covers' paraphrase] (https://www.covers.com/guides/betting-tips-from-pro-sports-bettor-billy-walters).
- "3 has the highest value, followed by 6, 7 and 14"; favorites early, underdogs late; 1 unit = 1% of bankroll, 3 units at most [ASSERTED] (https://realbillywalters.com/handicapping-system/, his own consulting site). No half-point values were found on any page opened.
- His edge was partly execution: runners, deliberately moving lines, an information network; books refused him [ASSERTED] (https://www.espn.com/espn/feature/story/_/id/12280555 ; https://www.espn.com/espn/otl/story/_/id/22946649/world-best-most-feared-sports-gambler-game-us-supreme-court-considers-legalizing-craft-espn).
- **What transfers to you:** the player-value scale (which our test 2b roughly reproduces: a quarterback moves a line about 2.7 points during the week) and the key-number weighting (already in `pricing.py`). **What does not:** the information network and execution, which were most of the edge.

**Warren Sharp and published analysts (one example).** His site claims 1,781-1,295 (58%) since 2006 and 63% on totals, with no audit, no pick timestamps, no closing-line comparison and no prices [ASSERTED; absence of audit verified on the page] (https://www.sharpfootballanalysis.com/lifetime-betting-records/). Our own replication of his public method failed twice (`02`, `03`). Not an input, per your instruction.

**Bob Voulgaris (NBA).** His first edge was structural: books split full-game totals about evenly between halves, plus three coaches' end-of-game habits he had "nailed perfectly" [ASSERTED]. Books fixed it, and he lost a third of his bankroll in a month. He then built a possession simulator (Ewing), a minutes-and-lineups projector feeding it, and a roster database, at over 1,000 bets a season, reporting 6%+ then 5.14% ROI and blaming the decline on books learning from his bets [ASSERTED, self-reported] (https://www.espn.com/blog/playbook/dollars/post/_/id/2935/meet-the-worlds-top-nba-gambler). About 95% of his bets were totals, and he tracked referees [ASSERTED] (https://www.espn.com/blog/truehoop/post/_/id/4966/a-professional-gambler-s-take-on-the-tim-donaghy-scandal). **Lesson:** NBA edges came from structure and minutes projection built by a full-time team, and they decayed. Nothing documented here is buildable from free data in weeks.

**Bill Benter (model blended with the market).** Full text read (https://www.Gwern.net/doc/statistics/decision/1994-benter.pdf).
- The public odds are "a sophisticated estimate"; where his model and the public disagreed, outcomes landed closer to the public [DATA].
- The fix is a second-stage logit blending the model's out-of-sample probability with the public's; fit (pseudo-R²) public 0.1218, model 0.1245, combined 0.1396, and the value is the gain over the public alone [DATA].
- A tipster model as good as his on its own added nothing once blended [DATA].
- Overestimating the edge by 2× makes full Kelly's growth zero, which is "easily done in practice"; use 1/2 to 1/3 Kelly [ASSERTED, standard math].
- **This is exactly the test the engine already runs** (blend weight on the model above zero, `04` Test A and the props gate). Every full-game model has scored zero on it.

**Closing-line value and Pinnacle as the reference.**
- Pinnacle's own page calls CLV "one of the strongest indicators" of a sharp bettor and "a key factor in whether your account gets limited" at recreational books; NFL opening limits about $3,000, rising past $100,000 by kickoff [ASSERTED, interested party] (https://www.pinnacle.com/betting-resources/en/educational/what-is-closing-line-value-clv-in-sports-betting).
- Buchdahl, 158,092 soccer matches: Pinnacle's no-vig close is "highly efficient" on average, and open-to-close price changes predict profit with a slope near 1 [DATA] (https://www.pinnacle.com/betting-resources/en/educational/how-to-solve-a-problem-like-efficiency-part-one/rn8j5rnqj2p8t68p ; https://football-data.co.uk/blog/pinnacle_efficiency.php).
- **Against:** Whelan, 3,670 NBA games: several positive-CLV groups still lost money, and one with 5% CLV returned about 0.2%. CLV must clear the vig [DATA] (https://www.karlwhelan.com/?p=2595). Moskowitz (J. Finance), 100,000+ contracts in four leagues: momentum-driven moves from open to close are "completely reversed by the game outcome" [DATA] (https://conference.nber.org/conf_papers/f92072/f92072.pdf). A recent soccer sample found realized returns about half of CLV-implied [DATA, small] (https://networked.substack.com/p/a-view-from-the-pinnacle).
- **For the engine:** grade CLV against Pinnacle's no-vig close (done) and require it to clear Wagerhouse's extra ~2% margin, not just be positive. That is the reason for item 12 in section 5.

**Soft books, stale lines, steam and limits.**
- Kaunitz, Zhong and Kreiner, with no model at all: bet when a soft book's odds beat the consensus-implied probability by 5%. 56,435 historical bets returned +3.5% (random bets −3.3%); bets 1 to 5 hours before kickoff +9.9%; about 30% of signals had already gone stale by the time they checked; real money: 265 bets at +8.5%, then the books "started to severely limit our accounts" [DATA] (https://arxiv.org/abs/1710.02824). **This is the most direct evidence for the speed lane** (soccer, many books).
- Massachusetts regulator: 0.64% of accounts limited; operators list "winning/beating closing line value" as a reason [DATA, primary] (https://massgaming.com/wp-content/uploads/Meeting-Materials-9.30.25-OPEN.pdf).
- Soft books following Pinnacle: medians of 6 to 13 minutes (1xBet) and 47 to 67 minutes (Bet365) on 28 soccer fixtures [DATA, small, from an odds-API vendor] (https://oddspapi.io/blog/soft-book-lag-pinnacle/). That is the kind of number section 5 item 3 must produce for Wagerhouse.
- **Risk for you:** if the speed lane works, winning at a pay-per-head book can get the account limited. At $25 that's unlikely to matter, but it is real.

**Market efficiency research.**
- NFL: Levitt's contest data show books shade prices to bettor bias [DATA, one 2001 season] (https://www.stat.berkeley.edu/users/aldous/157/Papers/Levitt_Gambling_2004.pdf). Home field drifted from 2.9 to 2.2 points over 2000-2019 and barely persists by team [DATA] (https://nfeloapp.com/analysis/an-initial-exploration-of-home-field-advantage-in-the-nfl/). Borghesi found totals did not fully price heat, wind and rain (1984-2004) [DATA, abstract only] (https://econpapers.repec.org/RePEc:taf:apfiec:v:18:y:2008:i:12:p:947-953). That matches our wind result and its decay. **No study was found on whether practice participation is priced**; our 2a says it is, at the close.
- NBA: openers are significantly off when a player is absent, but "no profitable strategy exists when wagering at the closing line" (Dare, Dennis and Paul 2015) [DATA, abstract only] (https://ideas.repec.org/a/eee/finlet/v13y2015icp130-136.html). That is the same answer as our `13` and 2d, and it points at the open, before the move. Rest and back-to-back effects: no peer-reviewed study found; practitioner figures conflict [FOLKLORE].
- College: favorites overpriced in 1985-2003 [DATA, old] (https://www.aeaweb.org/conference/2010/retrieve.php?pdfid=406). Power-conference teams beat non-power opponents by more than the spread [DATA, abstract only] (https://ideas.repec.org/a/buc/jpredm/v7y2013i2p29-41.html). Last season's top 10 overvalued in the next opener (not opened, paywall: https://link.springer.com/10.1007/s11293-019-09611-y). That last one fits our early-season hint in 2c.

**Teasers and key numbers.**
- Break-even per leg, 2-team 6-point: 72.4% at −110 and 73.8% at −120 [DATA, arithmetic]. Wong legs ran about 74 to 75% in 1999-2010, except away favorites [DATA, secondary] (https://www.teamrankings.com/blog/sports-betting/teasers-betting-nfl-key-numbers-wong). Wong's book: Huntington Press (https://huntingtonpress.com/?p=2357).
- The 2015 extra-point move cut extra-point success from 99.2% to 94.1% and raised margins of 6 and 8 by 2.4 points combined [DATA] (https://www.covers.com/nfl/key-numbers). Covers' "totals 49 or lower adds about 1%" is [ASSERTED] (https://www.covers.com/nfl/teaser-strategy).
- The agent's own check of nflverse closes found Wong legs at 76.0% for 2020-2026, home favorites the weakest leg (71.6%), and the low-total filter flat since 2015 (76.1% against 76.0%). My split (2f) shows it helping in each era, but on small cells. **Treat the total filter as unproven and the underdog legs as the strong half.**

**Kelly and sample size.**
- Buchdahl's simulation, 1,000 bets at −110 with a true 2.5% edge: about a 34% chance of being down at the end even when sized correctly; sizing as if the edge were 5% gives over an 8% chance of losing 90% of the bankroll [DATA] (https://football-data.co.uk/blog/kelly_staking.php).
- Full Kelly on a model weaker than the book went broke in 100% of NBA runs; fractional Kelly had no ruin [DATA] (https://ar5iv.labs.arxiv.org/html/2107.08827).
- Telling a true 54% bettor from break-even by results alone takes roughly 3,600 to 5,900 bets [arithmetic]. That is why closing-line value is the only scorecard that can work this season.

**Player props.** Small limits keep props inefficient: "a couple 100 dollars, maybe 500" (a pro on Pinnacle's podcast) [ASSERTED] (https://www.pinnacle.com/betting-resources/en/educational/the-journey-to-becoming-a-successful-bettor-pinnacle-betting-podcast/5df2lxwl4gqtlfhb). Season-long unders were 63% (2021, n=269) and 60% (2022, n=335) and fading [DATA, small] (https://www.4for4.com/2023/preseason/key-winning-season-long-player-props). The usual explanations for an Under bias ("the public bets overs", median against mean) have no primary data [FOLKLORE]. So the NBA model's Under lean is a bias to check, not a known edge.

### What the sources add up to

1. Every serious modeller treats the market as the prior and judges a model only by what it adds on top (Benter). Our eight tests say our models add nothing at the close.
2. Documented edges for individuals are **early** (the opener and the first hours after news, before the sharp books' limits rise) or **structural** (teasers, Voulgaris's half-split). The close is efficient on average.
3. Soft books copy sharp books with a measurable lag, and betting the stale number is the best-documented no-model edge. It is also the fastest route to being limited.
4. **Could not open:** Review-Journal and Action Network (blocked), the Walters book text, Buchdahl's book, a 2001 Las Vegas Sun teaser column, and several 404s. The full list is in `14a-sources.md`.

---

## 2. Tests run today on our own historical data

Rules for all of them: fit on earlier seasons only, test on later seasons, compare with the closing line at −110 (break-even 52.4%), and report how many variants were tried. "MSE" is the average squared miss, where lower is better. A model "adds something" only if its MSE beats the close's on seasons it never saw.

### 2a. NFL: the official injury report, including practice participation, against the close (failed)

**What I built.** For every team and week from 2018 to 2026, I took every player on the official report (nflverse `injuries_*.parquet`) and weighted him by his snap share over his last three games (nflverse snap counts, downloaded today; 90% of report rows matched a snap record). Then I added it up by position group (QB, offensive line, skill players, defensive line, linebackers, defensive backs), split by Out or Doubtful, "newly out" (he played last week), and Questionable with the final practice marked Did Not Participate, Limited, or Full. I fitted one ridge regression on earlier seasons and tested on 2021 to 2026.

| Target | Games tested | MSE, close | MSE, close + injuries | Bets at 1.0 / 1.5 / 2.0 point edges |
|---|---|---|---|---|
| Closing spread | 1,586 | 158.38 | 159.73 (worse) | 249-235 (51.4%) / 133-104 (56.1%) / 46-48 (48.9%) |
| Closing total | 1,586 | 171.22 | 170.96 | 222-206 (51.9%) / 97-97 / 41-46 |

Variants tried: 2 targets × 3 thresholds, one penalty setting. The one bucket above 52.4% (133-104) sits between two coin-flip buckets, which is what noise looks like. No coefficient was reliably different from zero except "skill players out" on sides (t = −2.3 in-sample, and it didn't survive held out).

**What it means.** By kickoff, the closing line has priced the injury report, practice participation included. The input the handoff hoped was unused is already in the price.

**What it can't prove.** Whether the line is slow to absorb the report *during the week*. That is the next test.

### 2b. NFL: how much of the week's line movement is injury news? (a measurement, not a model)

From the ESPN BET openers the engine already caches (669 games, 2023 to 2025; `openers.py`): the average move from open to close was 1.19 points, 31% of games moved 1.5 or more and 12% moved 3 or more.

| Injury news that week (from 2a) | Move from open to close |
|---|---|
| Starting QB newly out (played last week) | **−2.68 points per QB** (t = −8.5); 35 games, average 2.43 points toward the healthier side |
| Each other starter newly out (per full-snap player) | −0.30 points (t = −4.4) |
| Each Questionable player who was limited or missed practice | −0.12 points (t = −3.1) |

Injury news explains about 15% of the week's moves (R² 0.152). **This is the size of the prize for being early:** on a quarterback change, a bet at the pre-news number is worth about 2.5 points, which is roughly 7 percentage points of win chance in the NFL. It is only worth anything if your book is still on the old number when you see the news. Whether it is gets measured in section 5, item 3.

### 2c. College: ~60 public rating systems against the close (failed), with one hint

Data: The Prediction Tracker's season archives `ncaa2015.csv` to `ncaa2025.csv` (fetched today; 8,283 games with a line and a result). Each row carries the line, the result, PT's own average of the systems (`lineavg`), the median, about 60 individual systems, and a `lineopen` column. `lineopen` behaves like a real opener: average miss 12.46 against 12.34 for the close, average move 1.58 points.

- **Systems' average or median against the close, walk-forward 2019 to 2025:** the fitted slope stayed between −0.05 and +0.08, and the MSE after adjusting was the same as or worse than the close's in every season. At a 1-point predicted edge it produced 7 bets, and at 2 points, none.
- **Each system on its own, 2019 to 2025, betting whenever it was 3+ points off the close:** 61 systems had 300 or more such bets, and only one was above 52.4% (Dokter, 984-894, 52.4%; Burdorf 231-201, 53.5% on fewer). Picking the best five on 2015 to 2020 and testing them on 2021 to 2025 gave 950-1015, 932-1026, 830-901, all losing. This is what a lucky winner looks like.
- **At the opener:** where the systems' average disagreed with `lineopen` by 3 or more, the line moved our way by 1.05 points on average, but betting the opener went 839-770 (52.1%). By 5 or more: 1.95 points of movement, 276-276. **Treat the movement as look-ahead.** The file does not record when each system published, and many publish late in the week, after the line has moved. As the plan already warned (`10-plan.md`, Test 4), a leaky test that fails is a real fail.
- **The hint: weeks 1 to 4, in the transfer-portal era.** Where the systems' average was 2+ points off the close in the first four weeks, the side the systems liked covered 248-243 over 2015 to 2020 (a coin flip), but **188-251 over 2021 to 2025** (42.8%). Four of those five seasons went against the systems, and 2025 went 48-44 the other way. A plausible story: since the one-time transfer rule (2021), ratings that lean on last season mislead early, and even the close hasn't fully moved off them. **This was found by slicing, after looking**, so it is a hypothesis, not a result. The test is to write the rule down now and run it untouched in weeks 1 to 4 of 2027, adding returning-production and transfer data from CollegeFootballData (free tier) as a second input.

Variants tried for 2c: 2 predictors × 3 thresholds, a 61-system scan, a best-5 hold-out, early/late × 3 thresholds, opener × 3 thresholds, and a by-season split. All are reported here.

### 2d. NBA: rest, travel and schedule density against the close (failed)

From 4,194 ESPN box scores with closing lines (`nba_data.py`, seasons labelled 2024 to 2027), for each team and game: back-to-back, days of rest, games in the last 4 and 7 days, travel distance on short rest, time zones crossed in each direction, road-trip length, and visitors on a back-to-back at Denver or Utah. Walk-forward: train on earlier seasons, test 2025, 2026 and 2027.

| Target | MSE, close | MSE, close + schedule | Bets at 1.0 / 1.5 / 2.0 |
|---|---|---|---|
| Closing spread | 194.33 | 194.33 | 324-315 / 133-122 / 63-54 |
| Closing total | 323.56 | 326.82 (worse) | 774-808 / 521-547 / 339-355 |

Simple slices for the record: home team on a back-to-back against a rested visitor, 218-246 against the close (n 468); visitor on a back-to-back, 250-247; visitor on a back-to-back at altitude, 21-22. **The close prices rest and travel**, which matches the earlier finding for absences (`13-nba-absences.md`). The status table's line "Pinnacle prices them" is now tested, not assumed. Caveat: these are ESPN's closing lines (DraftKings-type), not Pinnacle's, so if anything they are softer than what you compare against.

### 2e. Totals and weather (re-run, plus what cannot be tested)

`engine model-test wind`, re-run today: fitted on 2010 to 2018 at −0.361 points per mph above 6 mph. Held out since 2019: Unders at 1+ points 321-221 (59.2%), at 2+ points 156-104. By season: 54-37, 36-33, 51-32, 57-29, 48-27, then **33-34 (2024), 28-19 (2025), 14-10 (2026)**. Note: on squared error, full-size wind is slightly worse than the close since 2019 (167.6 against 167.42). It gets the direction right, but the size is now too large. Using the day-before forecast (493 games since 2024): 96-77 at 1+ points, 66-56 at 1.5+, 44-44 at 2+.

**Can't be tested further today:** the forecast available *when you would bet* (Wednesday to Friday) for seasons before 2024. Open-Meteo's archive of previous forecast runs starts too late. The engine began storing its own forecasts with the totals on Nov 23 (`wind_forecasts`, 8 rows). College weather has no history in the repo.

### 2f. Teasers and key numbers (known math, checked on our data)

Wagerhouse prices, from your graded tickets (`wagers.teaser_name`): "WH 6/4 MIX" 2-team pays 0.909 (−110), "WH 6.5/4.5 MIX" 2-team 0.833 (−120), "WH 7/5 MIX" 2-team 0.714 (−140), and "WH 4tm 13pt" 0.714. The break-even per leg is 72.4% for 6 points at −110 and 73.9% for 6.5 points at −120.

NFL Wong legs (closing favorite −7.5 to −8.5, or underdog +1.5 to +2.5, teased 6 points), nflverse closes:

| Seasons | All totals | Total 49 or lower | Total above 49 |
|---|---|---|---|
| 2010-2014 | 73.9% (206 legs) | 76.9% (172) | 58.8% (34) |
| 2015-2019 | 76.7% (302) | 77.7% (249) | 71.7% (53) |
| 2020-2022 | 77.7% (193) | 78.9% (142) | 74.5% (51) |
| 2023-2026 | 74.9% (303) | **75.8% (264)** | 69.2% (39) |

For contrast: every other NFL leg won 69.5% (4,121 legs, 2018 to 2026). The underdog legs were stronger than the favorite legs (77.2% on 400 against 71.3% on 202, 2018 to 2026). College Wong-range legs won 71.1% (1,280) and NBA 4-point legs 63.0% (8,388): **neither clears its break-even, so the teaser lane is NFL only.** Variants tried: 4 eras × 3 total splits, plus the college and NBA checks.

**Buying points is not an edge at your prices.** At a closing −3, 9.4% of NFL games (2018 to 2026) land exactly on 3. Buying −3 to −2.5 at −130 is worth −3.2% per dollar, against −4.1% for −3 at −110. That's slightly less bad, still negative, and at −135 it is worse (−4.8%). Off 7 (about 7% of games), it is worse still.

---

## 3. Is the premise right?

**The premise in the engine today:** Pinnacle's no-vig line is the truth. Look for places where Wagerhouse is slow or loose against it, and only bet those that also have a handicapping reason.

**What's right about it.** Using a sharp book's no-vig price as fair is the method with the best evidence for an individual (section 1). Code owning every number, freezing every pick and grading on closing-line value are exactly right. So is refusing to treat a price gap alone as a pick *inside a model's lane*.

**What's wrong or unfinished about it.**

1. **"Wagerhouse is a soft book, so that's where my edge is" is not supported on price.** Two days of matched reads show the opposite of soft: Wagerhouse's juice is 4.7 to 4.8% on full-game lines against Pinnacle's 2.6 to 3.2%, and 6.3 to 7.0% on quarters and team totals, with the two numbers within 0.2 to 0.35 points (`12-wagerhouse-vs-pinnacle.md`, re-run today with the same result). A pay-per-head book copies a market line and adds margin. What it may still be is **slow**: a copier is behind the source by however long its feed or its manager takes. Speed is the testable form of "soft".
2. **"Every Bet needs a handicapping reason" contradicts the evidence in one specific place.** The matchup, luck and efficiency reasons the agent prompt asks for have failed every test against the close (`02`, `03`, `04`, and 2a to 2d here). Requiring them as a Bet reason invites story-fitting: a well-written handicap for a side that has no edge. The two reasons with evidence are (a) **news Wagerhouse hasn't priced yet** and (b) **a tested model** (wind). The locked rule "a price gap alone is never a pick" should stay. But when the gap comes with a timestamped reason (Pinnacle moved on news at 10:12 and Wagerhouse hasn't moved), that *is* the reason, and no matchup paragraph should be required. I'm not proposing to reopen the locked rule, only to say which reasons count.
3. **Teasers sit outside the frame entirely.** Their edge comes from the shape of NFL scoring around 3 and 7, not from a price gap or a forecast, so the current lanes can't see them. The spec already allows exactly one teaser ("2-team 6.5-point at −120, NFL sides, both legs crossing 3 and 7", `CLAUDE.md`, rules section), but only as a calculator on your own bets, never as an engine pick. Your book's 2-team **6-point at −110** is cheaper (72.4% break-even per leg against 73.9%), so the spec line should name it. Your earlier instruction not to copy your own strategy covered 13-point teasers and moneyline parlays. Those are the leaks, and 6-point Wong teasers are the mathematical opposite. **Written case for a yes/no:** add a sixth lane, "NFL Wong teasers". Code finds the eligible legs at Wagerhouse's number (favorite −7.5 to −8.5 or underdog +1.5 to +2.5, total ≤ 49), freezes them, and pairs them into 2-team 6-point teasers. Paper first for three weeks, then the same staging as other picks. Kill it if 150 forward legs win under 72.4%, or if Wagerhouse moves its 2-team 6-point price off −110.

**Probability-weighted view** (my judgment from the evidence above, not a calculation):

| Framing | Chance it pays at $25 units | Rough season value if it does |
|---|---|---|
| Own model beats Pinnacle's full-game close (any sport) | under 5% | n/a |
| Wong teasers at −110 | ~65% | $90 to $175 |
| Speed: Wagerhouse trails Pinnacle on news, and you can act by hand | ~40% | $100 to $400, mostly NBA |
| Wind unders, forecast-based | ~40% | $25 to $75 (few games, half unit) |
| Props model beats Pinnacle *and* Wagerhouse props are readable | ~10% | unknown; not bettable today |
| Wagerhouse quarters, halves and team totals mispriced | ~10% | small; their juice is 6 to 7% |
| College early-season priors (2027) | ~20% | $50 to $150 |

**A more promising framing than the one in the charter:** "The engine finds the moments when Wagerhouse is behind the market, and the few bet types where the math is in your favor at Wagerhouse's own prices, and tells you within minutes." It is a speed-and-structure engine with handicapping as the explanation layer, not the reason. That is closer to how documented winners at soft books describe their work (Kaunitz et al. and the Pinnacle/Buchdahl material in section 1) than a model-first engine is.

---

## 4. Split the sports or not?

**Recommendation: one engine, one repo, shared plumbing; three separate sport lanes, each with its own edge hypothesis, agent prompt, schedule, evidence threshold and weekly checklist. Props stay as their own two lanes.** Don't split into separate repos or separate agents with separate code. The shared parts are the parts that are working: `pricing.py` landing tables (calibrated in `11a`), `grade.py`, `leans.py`, `stale.py`, freezing and versioning. Duplicating them would create the drift the charter is trying to stop.

**Why the sports lag each other today.** It isn't the code layout. It's that the agent prompt and the build effort follow one idea (handicap the NFL), and the NFL is where the most free data is. Evidence: the agent prompt has five NFL-specific paragraphs (injuries, outside opinions, matchup, luck, totals) and one sentence each for NBA and college (`ops/agent_prompt.md`). NBA's injury watcher runs three times a day, which can't test a speed edge measured in minutes. College has no edge hypothesis at all in config.

**Each sport's real edge hypothesis:**

| Sport | Primary hypothesis | Secondary | What to stop |
|---|---|---|---|
| NFL | Wong teasers (if approved); speed on quarterback and cluster news | Wind unders (half unit) | Matchup and luck paragraphs as Bet reasons |
| College | Speed on quarterback news and bowl opt-outs (Wagerhouse is slower to copy 60+ games a week?) | Early-season priors, forward test in 2027 | Public systems as an input (failed, 2c) |
| NBA | Speed on availability news (official report every 15 minutes; Rotoworld median 5 minutes) | Props Under lean (forward test only) | Rest, travel and back-to-back adjustments (priced, 2d) |

**How to stop one sport starving the others:**

1. **Separate agent prompts**: `ops/agent_prompt_nfl.md`, `_college.md`, `_nba.md`, each listing only the reasons that sport's evidence supports. A shared header carries the locked rules.
2. **A per-sport weekly checklist**, generated by `engine status` into each lane folder (`docs/lanes/<lane>/WEEK.md`): reads taken, alerts fired, picks issued and graded, closing-line value, Wagerhouse lag measured (minutes), and one line saying "work done on this lane this week". A lane with no work line for two weeks shows red on the board.
3. **Per-sport evidence thresholds** in `config.yaml` `go_live:` keyed by lane, because 10 NBA picks come in days and 10 NFL picks take weeks. For example: NBA Stage 1 at 25 graded, NFL at 10, college at 10 plus bowls.
4. **Measure closing-line value in win chance, not points.** A point is worth about 3% at an NFL 3, 2% in college and 2.5% in the NBA. Comparing lanes in points flatters the sports with less key-number weight. `pricing.py` already converts.
5. **One session owns code, but each week's plan names one task per sport**, and the summary at the end of every session says what each sport got.

---

## 5. Ranked list: build, stop, change

Ranked by expected money per hour of work, my estimate. Each item has the test that would prove it and the number that kills it. Nothing here is started; all of it waits for your yes.

| # | Kind | What | Hours | Test that proves it | Kill number |
|---|---|---|---|---|---|
| 1 | **Change** (yours, not code) | Treat the engine's Stage rules as the whole betting plan. Live bets, Wagerhouse props without a model, 13-point teasers and parlays are the −4.5% to −13% part of the audit | 0 | The weekly report already measures it | n/a. This is the largest dollar item in the review ($630 to $860 per 11 weeks at the audit's volume) |
| 2 | **Build** (needs your yes) | **NFL Wong teaser lane** (paper first): code finds eligible legs at Wagerhouse's number, freezes, grades | 4 to 6 | Forward legs at Wagerhouse numbers win ≥ 72.4%; history already 75.8% on 264 | Under 72.4% after 150 forward legs, or Wagerhouse's 2-team 6-point price moves off −110 |
| 3 | **Build** | **Lag measurement in minutes**: for every Pinnacle move ≥ 0.5 (NFL/college) or ≥ 1.0 (NBA), the time until Wagerhouse matches, using the existing 10-minute burst reads. Add college to `stale.py` and burst windows | 3 to 4 | Median lag ≥ 20 minutes on ≥ 30% of moves, over ≥ 60 moves | Wagerhouse matches within one 10-minute read on 80%+ of moves |
| 4 | **Change** | **NBA burst windows follow the official injury report** (every 15 minutes on game days) for the 2 hours before the first tip, not three fixed watcher times | 2 | Same as 3, NBA only; plus STALE alerts' closing-line value | Same as 3 |
| 5 | **Change** | **Stale-number alerts become the main bet path for speed**: a STALE alert *with* a timestamped Pinnacle move and a news item in the window becomes a Bet candidate (agent checks the news, code owns the number). Rewrite decision 0013's "not a pick" for that case only. Your yes needed, since it touches the locked "price gap" rule in spirit | 3 | Average closing-line value of these alerts ≥ +1.5% win chance over ≥ 40 alerts | ≤ 0 after 40 alerts; or under 50% of alerts still at the alerted number when you check by hand (not actionable) |
| 6 | **Change** | **Agent prompt rewrite, one per sport** (section 4). Drop matchup and luck as Bet reasons (keep them as "why the line is here"). Fix the false lines listed in section 8 | 2 | Cards stop showing "the handicap favors X, Pass" stories; agent runs shorter | n/a (correctness) |
| 7 | **Stop** | **Building full-game models for sides or totals from public data** in any sport. Eight failures, three of them today | saves time | n/a | Reopen only with a new *kind* of input the close demonstrably lacks |
| 8 | **Stop** | **Agent runs that repeat Pass.** Run on change (news, new slate, a Pinnacle move with Wagerhouse unmoved) plus one fixed early run per slate (Sunday evening NFL, morning NBA). Already proposed in `10-plan.md` §5; still not done (four Sunday runs in `config.yaml`) | 1 | n/a | n/a |
| 9 | **Keep, tighten** | **Wind unders** at half unit, Conditional, as today. Grade on stored forecasts | 0.5 | Forecast-based Unders at 1+ points ≥ 52.4% over the rest of 2026 plus 2027 (target ≥ 40 games) | Under 50% after 40 forecast-based games, or squared error worse than the close on 2026 to 2027 at half size |
| 10 | **Keep, deprioritize** | **Props forward tests**: no more build time until a gate passes. Even a pass can't be bet without Wagerhouse prop lines (decision 0011) | 0 | Existing gate (300 graded, blend weight > 0, 5%+ disagreements win money) | Blend weight 0 at 300 graded, per sport; and the NBA Under lean must win on both Overs and Unders separately |
| 11 | **Build later** (Aug 2027) | **College early-season priors**: pre-register now (weeks 1 to 4, systems' average ≥ 2 off the close, bet against it) and add CFBD returning production and transfer counts | 6 | ≥ 52.4% on 2027 weeks 1 to 4, at the close and at Wagerhouse's number | Under 50% in 2027, or under 52.4% over 2027 and 2028 together |
| 12 | **Change** | **Go/no-go rules (decision 0012):** keep the stages and the closing-line value gate. Change three things: measure closing-line value in win chance, not points; set thresholds per lane (item 4.3); require a Pinnacle close on every graded pick (now possible for NBA) | 2 | n/a | n/a |
| 13 | **Housekeeping** | A stray `.venv` folder was created inside iCloud (Nov 23, 12:18). iCloud marks it hidden, which breaks `uv run` for any shell without `UV_PROJECT_ENVIRONMENT=.venv.nosync`. The scheduled jobs set it and are fine. Delete the stray folder, and add `export UV_PROJECT_ENVIRONMENT=.venv.nosync` to `~/.zshrc` as the README says | 0.1 | `uv run engine --help` works in a fresh shell | n/a |

**Sizing and bankroll.**

- **Stay flat.** Kelly sizing needs a probability you trust, and the engine has none for sides yet. The only calibrated pieces are the landing tables, which turn a *given* fair line into a probability; they don't make the fair line right. Over-estimating your edge by 2× under full Kelly gives zero growth, and more than that is negative (Benter, and the Kelly material in section 1). Flat stakes are the honest choice until 100 graded picks have positive closing-line value. After that, cap at quarter-Kelly computed from the *closing-line-value-implied* edge, not the engine's issued edge.
- **Correlation.** Treat a side and a total in the same game as one position (done, `card.py`). Treat both legs of a teaser as one stake. A news event that moves several markets in one game is one bet, not three.
- **Half-unit Stage 1:** right. Ten picks show the process works, not an edge. Keep the 2-unit weekly cap.

---

## 6. Each lane after this plan

| Lane | Will evaluate | Will not | What makes it say "make this bet" |
|---|---|---|---|
| NFL sides and totals | Wagerhouse against Pinnacle every read; lag after Pinnacle moves (minutes); unpriced news with a timestamp; wind on forecasts (half unit) | Own ratings, matchup or luck as a reason; practice reports as a model input (priced, 2a); line movement or splits | Pinnacle has moved on timestamped news, Wagerhouse is still on the old number, and the value clears 2% at Wagerhouse's price (Bet, 1 unit at Stage 2). Or wind ≥ 1 point on the forecast within 60 hours (Conditional, half unit) |
| NFL Wong teasers (new, if approved) | Every eligible leg at Wagerhouse's number, total ≤ 49 | Totals legs, college or NBA legs, 13-point or 3+ team teasers | Two eligible legs from different games at −110, frozen at the number. Paper for 3 weeks, then staged like other picks |
| College sides and totals | Same speed measurement as NFL (added to stale and burst); quarterback and bowl opt-out news with timestamps | Public rating systems (failed, 2c); weather; early-season priors until Aug 2027 | Same as NFL: Pinnacle moved on news, Wagerhouse hasn't, value ≥ 2% |
| NBA sides and totals | Lag after the official report changes (15-minute cadence, 2 hours before first tip); Wagerhouse against Pinnacle | Rest, travel, back-to-backs (priced, 2d); absences at the close (priced, `13`) | A rotation player's status changes, Pinnacle moves, Wagerhouse hasn't, value ≥ 2% |
| NFL props | Pinnacle props scored and graded (forward test) | Any pick; Wagerhouse props | Nothing until the gate passes *and* Wagerhouse prop lines are readable |
| NBA props | Same; Over and Under scored separately | Same | Same |

---

## 7. Four-week schedule

Calendar: NFL weeks 12 to 15 (Thanksgiving Thursday Nov 26), college conference championships the weekend of Dec 5 and bowls from mid-December, NBA nightly. Each week ends with `engine status`, the per-lane checklist, and one line per sport in the session summary.

| Week | Build or change (after your yes) | Measured that week |
|---|---|---|
| **1: Nov 23 to 29** | Items 3 and 4 (lag in minutes, NBA windows follow the official report); item 6 (prompt fixes, at least section 8's false lines); item 2 on paper if you say yes. Thanksgiving: 3 NFL games and a full college Friday and Saturday | Number of Pinnacle moves seen per sport and minutes until Wagerhouse matched; Wong legs found (expect about 4); stale alerts and their closing-line value; wind forecasts stored |
| **2: Nov 30 to Dec 6** | Item 5 (stale-with-news as a Bet candidate) if week 1 shows Wagerhouse lags; item 8 (run on change); college conference championship week in the burst windows | First lag table with ≥ 30 moves (NBA should get there first); Wong paper legs graded; first Stage-0 graded picks with closing lines |
| **3: Dec 7 to 13** | Item 12 (go/no-go in win chance, per-lane thresholds). Prepare bowl-season reads: opt-out news is the college speed test | Lag table ≥ 60 moves → decide items 3 to 5: keep or kill on the numbers in section 5. NFL props reach 300 graded around here (gate decision). Wong paper record after 3 weeks (about 12 legs: too few to judge, the clock keeps running) |
| **4: Dec 14 to 20** | Bowls start: college speed lane live. Wind: last outdoor cold-weather stretch, the most wind games of the year | Stage 1 eligibility per lane; NBA props gate (300 graded already, so decide on the full rule); written mid-review: which speed lanes are real, by the kill numbers |

After week 4: NFL playoffs (fewer games, sharper market; expect fewer speed chances), bowls through early January, NBA continues. The college priors test waits for August 2027.

---

## 8. Corrections to the engine's own text (false or stale today)

None of these reaches Telegram, so none is urgent enough to fix without your yes. Each is a one-line fix.

1. **`ops/agent_prompt.md` step 3** says wind Unders went "214-147 on 2019-2026 … only 48-46 since 2024". No research file or test produces those numbers; the re-run today gives 321-221 and 75-63 (`05-model-first-picks.md` agrees). The same wrong figures are in this review's handoff. Fix: quote the generated numbers, or none.
2. **`ops/agent_prompt.md` step 2, NFL** tells the agent to "count only the part the ratings have not absorbed (they move about 10% a week)". The fair line has been Pinnacle since Nov 22; there are no ratings in it. Fix: "count only the part Pinnacle has not moved for since `news_at`" (which is what the code does).
3. **`ops/agent_prompt.md` step 2, NBA** says back-to-backs are "already in the sheet automatically". The sheet only notes them; the adjustment was removed on Nov 23 (`slate.py:177`). Harmless but untrue. Fix: "Pinnacle prices back-to-backs; do not add them."
4. **`ops/agent_prompt.md`, NFL handicap paragraph** says "A Bet's `matchup` reason must come from this". Every matchup-style model failed against the close (section 2). Fix as in item 6 above.
5. **`docs/lanes/STATUS.md` and the charter table** say NBA rest and travel are "priced by Pinnacle" without a test. That is now tested (2d), so the wording can cite it.

---

## 9. What this review could not do

- **Kylor's separate red-team document** (sections 1 to 9) was not in the repo, and I worked without it, as the handoff said. Only its checklist, summarized in `11-audit.md`, was used.
- **No test of the speed edge** is possible from history: no free archive of Wagerhouse, Pinnacle or news timestamps exists before Nov 21. It can only be measured forward, which is why it leads the schedule.
- **No historical prop lines, no historical openers at Wagerhouse.** The NFL opener test (2b) uses ESPN BET openers as a stand-in.
- **The Prediction Tracker file does not record when each system published**, so every opener result in 2c may contain look-ahead.
- **ESPN's NBA closes are not Pinnacle's.** The NBA tests compare against a softer close than the engine uses.
- **Small samples in our own logs**: 2 days of matched Wagerhouse/Pinnacle reads, 3 fast reads, 0 graded Leans, 1 graded pick. Nothing in this review about Wagerhouse's speed is a finding yet.
