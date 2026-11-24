# 23a — College football methods: source research

Researched 2026-11-24. Tags: [DATA] = a number I read on a primary or tracked page; [CLAIM] = stated by the author or a vendor and not checked by anyone independent; [OPINION] = judgement. "Not opened" means paywalled, blocked or gone; the claim then rests on a search snippet and is marked that way.

Bottom line first:
- I found **no public, multi-season, third-party record of any rating system beating the closing college line**. The best independent check, The Prediction Tracker, shows the updated (near-closing) line has the lowest error of every system it tracks, and the named computer systems sit around 47–53% against the spread season to season.
- The academic paper that tests this directly (Fair & Oster) found that the computer ranking systems, alone or combined, add **no information beyond the final Las Vegas spread**.
- The inefficiency evidence that survives is narrow:
  - older favorite/home-underdog biases;
  - mismatches between power-conference and small-conference teams (2002–2011);
  - last season's top 10 overvalued in their next opener (2008–2016);
  - non-Power-5 reaction to large misses on the spread (2006–2018);
  - team totals near zero (censoring).
- Each comes from one paper. None is shown to persist after about 2018.

---

## 1. SP+ (Bill Connelly, ESPN)

**Inputs**
- [CLAIM] SP+ is "a tempo- and opponent-adjusted measure of college football efficiency" and is predictive, not a résumé ranking. Connelly's ESPN wording, quoted in syndication: https://www.saturdaydownsouth.com/news/college-football/bill-connelly-releases-espns-final-sp-rankings-of-2022-season/
- [CLAIM] It grew out of the Five Factors: efficiency (success rate), explosiveness, field position, finishing drives and turnovers. On pre-bowl 2013 data, the team that won each factor won the game:
  - explosiveness (PPP): 86%
  - success rate: 83%
  - finishing drives: 75%
  - turnover margin: 73%
  - field position: 72%
  - Source thread: https://groups.google.com/g/study-hall-cfb-data/c/MOW54F8yvMk
  - Field position piece: https://www.footballstudyhall.com/2014/1/30/5361594/college-football-five-factors-field-position
  - These are in-game associations, not predictions.
- [CLAIM] How SP+ treats garbage time: I could not open a current primary method page. ESPN's SP+ explainer is paywalled or I could not find it.

**How preseason SP+ is built**
- [CLAIM] Three parts, weighted by how predictive each is: returning production, recent recruiting and recent history.
  - Last year's SP+ plus the returning-production adjustment is about two-thirds of the formula.
  - Recruiting's weight "has diminished significantly" (2026) because transfers drive roster turnover.
  - A transfer's production from his old team counts in both the numerator and denominator for his new team.
  - Recruiting averages include incoming transfers' recruiting ranks.
  - ESPN (paywalled; syndicated summaries): https://abc7.com/post/what-returning-production-looks-like-2026-college-football-season/18754857/ and https://africa.espn.com/college-football/insider/story/_/id/39511969/college-football-2024-preseason-sp+-rankings-takeaways
- [CLAIM] Defensive returning production is weighted roughly:
  - snaps: 66%
  - tackles: 19%
  - tackles for loss: 15%
  - Source: https://www.on3.com/teams/texas-longhorns/news/texas-returning-production-2025
- [CLAIM] One secondary source gives "returning production 60%, recruiting ~14%, recent history (3 seasons) the rest." The source page returned 403, so this is unverified: https://on3.com/teams/south-carolina-gamecocks/news/south-carolina-football-espn-analystics-spplus
- **In-season fade:** not found. I found no primary statement of how fast the preseason weight decays in SP+. The full weights are behind ESPN+.

**Against-the-spread record**
- No consolidated season-by-season SP+ ATS record surfaced in any search, including several targeted searches for 2018–2025. Only fragments:
  - [CLAIM] 2018: S&P+ was 55% ATS through nine weeks, with about 13 points mean absolute error. Football Study Hall, third-party writer. The page reset the connection, so I am working from the search snippet: https://www.footballstudyhall.com/2018/11/2/18055394/college-football-projections-sp-plus
  - [CLAIM] 2021 win totals (not spreads): SP+ August projections beat Caesars win totals 60% of the time, and 74% when they differed by at least one win. The same piece said the top computer systems mostly finished under 50% ATS in 2021. The source page is gone (410), so this is a snippet: https://superwestsports.com/which-college-football-win-totals-should-you-bet-sp-helps-provide-answers
  - [CLAIM] 2026 through about October 1: "53.3% so far against every FBS vs. FBS spread." The page now returns 404, so this is a snippet: https://bvmsports.com/2026/10/01/espns-sp-projects-the-final-score-of-kentucky-at-south-carolina/
  - [DATA] Connelly posts weekly picks on X and links a spreadsheet. The weekly posts give scores, not running ATS totals: https://x.com/ESPN_BillC/status/1980041657895505977
- [DATA] SP+ is **not tracked** on The Prediction Tracker for 2025 or 2026 (see section 4), so there is no independent grade.
- **Closing-line evidence: none found.** Whether a claimed ATS figure is graded against the opening or the closing line is never stated.

**Turnover luck (Connelly) — relevant to section 5**
- [DATA] Expected turnover margin assumes:
  - 50% of fumbles recovered;
  - about 1 interception for every 4 passes defensed.
- [DATA] Teams with 2024 turnover luck of +5.5 or more: 14 teams, and 12 reversed in 2025. Their average margin fell 7.1.
- [DATA] Teams at −5.0 or worse: 22 teams, and 20 reversed. Their average margin rose 9.6.
- Source: https://abc11.com/post/turnovers-luck-2026-college-football-teams-improve/18760936/
- No market test: the article does not say whether the betting market prices this in.

## 2. FEI (Brian Fremeau)

- [CLAIM] Definition: the scoring advantage per non-garbage possession a team would be expected to have on a neutral field against an average opponent. Opponent-adjusted, drive-based. Glossary: https://bcftoys.squarespace.com/glossary
- [DATA] Garbage-possession rules (as of February 2021), paraphrased: https://bcftoys.squarespace.com/notes
  - A second-half possession where 8 × (losing team's remaining possessions + 1) is less than its deficit.
  - Clock-killing possessions of 2 plays or fewer.
  - Clock-killing possessions at the end of the game.
- [DATA] 10.7% of all possessions from 2007 to 2023 were classified as garbage. Same page.
- [CLAIM] All non-garbage possessions count equally. Opponent adjustment weights each opponent by possessions played. 2012 forum post: https://groups.google.com/g/study-hall-cfb-data/c/F_cx8zMb7u0
- Preseason FEI inputs and how they fade: **not found** on the pages I could open. The old `/fei` URL returns 404.
- [DATA] Graded independently on The Prediction Tracker as "FEI Projections":
  - 2025: 50.7% ATS, mean absolute error 12.31, 805 games
  - 2026 through Nov 22: 48.2% ATS, error 12.46
  - Source: https://www.thepredictiontracker.com/ncaaresults.php
- **Evidence of beating the closing line: none.**

## 3. ESPN FPI

**Inputs** (ESPN Stats & Info, about 2016): https://www.espn.com/blog/statsinfo/post/_/id/122612/an-inside-look-at-college-fpi
- [CLAIM] Opponent- and site-adjusted EPA for offense, defense and special teams, from play-by-play. Updated after each game by Bayesian regression, with earlier games re-adjusted.
- [CLAIM] Blowouts are handled by "a capping of sorts" on each component. No threshold is given.
- [CLAIM] Preseason inputs:
  - Prior EPA: the last year counts almost twice as much as each of the three years before it.
  - Returning starters: a starting QB is worth about 3.3 points per game for an average offense; a transfer QB counts half. Returning-starter data comes from Phil Steele.
  - Recruiting: a 4-year average, described as "very minor."
  - New head coach: slight regression toward the mean.
  - Preseason weight declines during the season but never reaches zero.
- [CLAIM] Game adjustments: 5.5 extra days of rest is worth +1 point; every 1,000 miles of travel costs −1 point.

**Accuracy (straight-up only)** — [CLAIM] self-reported, same page:
- FPI favorite won 75% of FBS-vs-FBS games over the last 10 seasons, "comparable to the Vegas closing line."
- Preseason-only FPI won 72% versus Vegas at 75%.
- When FPI and Vegas disagreed, the FPI favorite won 55% of the time. That is winners, not ATS.

**Independent grade** — [DATA] The Prediction Tracker:
- 2025: 48.2% ATS (762 games)
- 2026: 47.2% ATS (687 games)
- Source: https://www.thepredictiontracker.com/ncaaresults.php

**Closing line:** FPI does not beat it on any published measure.

## 4. Massey, Colley, Sagarin, The Power Rank, FiveThirtyEight Elo

**Massey**
- [CLAIM] Least-squares regression, with each game as one observation. Uses only score, venue and date. Weighted least squares can add momentum. Massey says the ratings describe past performance rather than predict.
  - https://www.masseyratings.com/theory/ls.htm
  - Thesis: https://masseyratings.com/theory/massey97.pdf

**Colley Matrix**
- [DATA] Uses wins and losses only, with no margin of victory. Starts from Laplace's rule (wins + 1, games + 2) and adjusts for schedule. Paper: https://www.colleyrankings.com/matrate.pdf
- [OPINION] With margin thrown away, it is a weak spread predictor by design.

**Sagarin**
- [CLAIM] PREDICTOR (also called PURE_POINTS) uses scores only and is "a very good PREDICTOR of future games." GOLDEN_MEAN and RECENT are other score-based methods. RATING blends all three. https://sagarin.com/sports/cfsend.htm

**The Power Rank (Ed Feng)**
- [CLAIM] Margin of victory adjusted for schedule (since 2008). Later added yards per play and a market rank built from closing spreads (2016). https://thepowerrank.com/2016/12/20/the-top-25-college-football-teams-by-the-markets/
- I found no published ATS or closing-line test.

**FiveThirtyEight college Elo**
- [CLAIM] Built to mimic the playoff selection committee, not to predict spreads. Partly reverts to the mean between seasons. https://fivethirtyeight.com/methodology/how-our-college-football-playoff-predictions-work
- 538 was shut down in 2025 (from memory, not verified here). Elo ratings are available from CFBD's `/ratings/elo`.

**Independent grades** — [DATA] The Prediction Tracker 2025 season (808 games): https://www.thepredictiontracker.com/ncaaresults.php?year=25

| System | ATS | Mean absolute error |
|---|---|---|
| Line (opening) | 51.8% | 11.89 |
| Line (updated) | 47.4% | **11.85** (lowest on page) |
| Sagarin Ratings | 52.8% | 12.08 |
| System Average | 52.8% | 11.98 |
| Massey | 49.9% | 12.39 |
| Massey Consensus | 50.1% | 12.71 |
| Best ATS: "Least Squares w/ HFA" | 56.0% (391 graded games) | 14.51 |

**[DATA] The Prediction Tracker 2026 season, through Nov 22** (695 games): https://www.thepredictiontracker.com/ncaaresults.php
- Updated line: mean absolute error 11.70, the best on the page.
- Opening line: 12.19.
- Best computer system: 11.90 (Dokter Entropy).
- Massey 48.9% ATS; Sagarin variants 47.6–50.1%; a Beck Elo 48.1%.
- No SP+, Colley, Power Rank or 538 entries.
- [OPINION] The page does not say which line the ATS column is graded against. The "Line (updated)" row has its own ATS figure (54.0% in 2026, 47.4% in 2025). That is consistent with grading against the opening line, so any computer's ATS here may be **against openers, not closers**.

**Fair & Oster — the key test**
- [DATA] "College Football Rankings and Market Efficiency," Ray Fair and John Oster: Yale working paper 2002, *Journal of Sports Economics* 8(1), 2007.
- Ranking systems carry independent information for predicting games, and an optimally weighted combination beats any single system.
- But **"none of the individual systems or the optimal combination" adds information beyond the final Las Vegas point spread**, which they call a strong test of efficiency.
- Abstract: https://ideas.repec.org/p/ysm/wpaper/amz2377.html
- Not opened: the full PDF did not render (https://cowles.yale.edu/sites/default/files/2022-08/d1381.pdf), so I could not see the list of systems or the seasons covered.

## 5. Phil Steele: experience and turnovers

- [CLAIM] "Turnovers = Turnaround": teams with plus double-digit turnover margins usually have a weaker record the next year, and the reverse. FCS version, 2026: of 80 teams in the "Going Down" box over 8 years, 55 had weaker records. https://philsteele.com/wp-content/uploads/2026/07/PG-006-FCS-TurnoversTurnaround-2026.pdf
- [DATA] Blog-level check: turnover margin correlated 0.296 year to year (2013→2014). https://mgoblog.com/comment/1473705
- [DATA] Connelly's turnover-luck reversals, 2024→2025: see the end of section 1.
- [CLAIM] FPI uses Steele's returning-starter counts as an input (section 3).
- **Market evidence: none found.** No study shows the college market under-prices turnover regression. Turnovers regress; whether the line already reflects that is untested.
- [OPINION] This is testable with CFBD data: compare prior-year turnover luck against next-year results versus the closing spread.

## 6. Dr. Bob (Bob Stoll)

**Records**
- [CLAIM] His site says:
  - CFB Best Bets 55.1% since 1999, with no win-loss total given;
  - since 2018: 326-261-19 (55.5%);
  - Strong Opinions since 2018: 184-152-3 (54.8%).
  - No third-party verifier is named on the site. http://drbobsports.com/
- [CLAIM] About page:
  - Early models used season-to-date stats plus Fourier "cycles"; the college model dates from 2004 and is re-tuned each summer.
  - The NFL model uses play-by-play.
  - About 59% NFL since 2016; about 60% "early years" from 1987; about 63% on his own bets in the mid-1980s.
  - No college percentage on this page. https://drbobsports.com/about/
- [DATA] Contemporaneous press (DRF, Dave Tuley, 2006-10-19): https://www.drf.com/news/dr-bobs-picks-moving-college-lines
  - "Last year" about 74% on a star basis.
  - 2006 to date: 19-12-3, and 40-24-7 when graded at the line after it moved.
  - Lines moved "instantaneously" after his releases; Pinnacle took his games off the board within minutes.
- [OPINION] That is evidence his releases **moved the market**: they were treated as sharp information. It is not a long-run audited record.
- The Sports Monitor of Oklahoma: no search returned any trace of it or of its tracking of Stoll. **Unverified.**

## 7. Billy Walters ("Gambler", 2023)

Only secondary summaries were available. The ESPN excerpt URL returns 404. Source for all points below: https://www.covers.com/guides/betting-tips-from-pro-sports-bettor-billy-walters
- [CLAIM] Power ratings update as 90% of the old rating plus 10% of a game's "True Game Performance Level." A separate QB rating is kept, and player values are tracked.
- [CLAIM] Home field: the conventional 3 points; really about 2.5 from 1974 to 2022; under 1 point over the last four years. He says it must be updated constantly and varies by venue. These are NFL figures.
- [CLAIM] "Bet favorites early and dogs late." Watch Circa, MGM, Caesars and Pinnacle.
- [CLAIM] Injuries are the second-largest edge:
  - QB about 7 points, the best more;
  - top non-QBs 2.5–3 points;
  - about 60% of players are worth about 0.
- [CLAIM] College: at his peak he placed about $20M on about 150 college games on a Saturday. Review-Journal: https://www.reviewjournal.com/?p=2890809
- No college-specific rating or home-field numbers were found in anything I could open.

## 8. Lem Banker; Stanford Wong, "Sharp Sports Betting" (2001)

- Banker: no college-relevant text was found online. **Not opened.**
- [CLAIM] Wong teasers are built around NFL key numbers:
  - favorites at −7.5 to −8.5 teased to −1.5 to −2.5;
  - underdogs at +1.5 to +2.5 teased to +7.5 to +8.5.
  - Secondary source: https://www.covers.com/nfl/teaser-strategy
- I could not open the book's college chapter, if it has one.
- [DATA] College teaser test, TheLines, 2021 weeks 5–13 (166 games): https://www.thelines.com/college-football-teasers-study-2021/
  - Every subset of 6-point college teaser legs fell short of the roughly 74% per-leg breakeven (at −120).
  - Wong-window underdogs went 13-4 and favorites 4-5, both tiny samples.
  - One season only. The text and table disagree on several figures.
- [OPINION] Weaker key numbers (section 10) are the structural reason college teasers lack the NFL edge.

## 9. Academic: college betting market efficiency

| Paper | Sample | Finding | Still present? |
|---|---|---|---|
| Sinkey & Logan, "Betting Markets and Market Efficiency: Evidence from College Football," AEA 2010 working paper (read the PDF) | 11,000+ games, 1985–2003; lines from Jim Feist's workbook (open vs close not stated) | [DATA] Favorites 1.86 pts less likely to cover; home 2.05 pts more; home dogs +1.92 pts; **away favorites −4.35 pts** (all as percentage-point probabilities). Books shade lines for teams that covered last week ("hot hand"). Conference dummies **not** significant. | Pre-2004 only |
| Fair & Oster, JSE 2007 | Early 2000s | Computer ratings add nothing beyond the final spread | n/a |
| Krieger, Girdner, Fodor & Kirch, "The Power of Wagering on Power Conferences," *J. Prediction Markets* 7(1):13-26, 2013 | Regular season 2002–2011 | [DATA] Power-conference teams vs mid-majors cover a majority; about **+2.94% return**; more with AP rank, spread size and week filters | No follow-up found |
| Paul, Weinbach & Higger, "The 'Large-Firm' Effect? Bettor Preferences and Market Prices in NCAA Football," *J. Prediction Markets* 7(2):29-41, 2013 (the issue 2 you cited) | Period not on abstract page | [DATA] AQ teams beat non-AQ teams more than prices imply, **and** get a disproportionate share of bets; blamed on BCS incentives | Pre-CFP era |
| Bennett, "Holdover Bias in the College Football Betting Market," *Atlantic Econ. J.* 47(1):103-110, 2019 | Opener of the next season, 2008–2016, previous final AP Top-25 team vs unranked team | [DATA] Top-25 teams covered 42.53%; driven by the **previous top 10** being overvalued (mirror text; Springer page blocked) | Not tested after 2016 |
| Bennett, "Next game reaction to mispriced betting lines in college football," *Applied Econ. Letters* 28(12):1006-1009, 2021 | 2006–2018 | [CLAIM, abstract] After a big miss vs the spread, betting on the team that beat the line wins significantly more than 50%. **Efficient for Power 5 games**; for non-P5 vs non-P5, 54.23% (one snippet) | **Best evidence that the less-known tier is less efficient** |
| Cox, Schwartz, Van Ness & Van Ness, JSE 22(3):251-273, 2021 | Period not stated | [DATA] Spreads predict winners better in the regular season than in bowls; mostly efficient; momentum (esp. negative) processed inefficiently | — |
| Kuester & Sanders, "Regional information and market efficiency," *J. Econ. & Finance* 35(1):116-122, 2011 | 4,345 games, 2000–2006; Phil Steele lines | [CLAIM, press summary] Bias when humid-region teams travel to arid regions; other games efficient | Press release now 404 |
| Traugutt & Morton, *Economics Bulletin* 42(3), 2022 | 2020-21 COVID season | [DATA] Contrarian (anti-herd) strategies above 50%; "statistically inefficient" | One abnormal season |
| Paul & Weinbach, *J. Econ. & Finance* 29(3), 2005 | College totals | [DATA] Overs over-bet; unders profitable | **Reversed** — see Francisco & Moore |
| Paul & Weinbach, *Int. Gambling Studies* 9(1), 2009 | College totals by TV status | [CLAIM] Unders more profitable in televised games | Pre-2008 |
| Francisco & Moore, *J. Econ. & Finance* 42(4):836-840, 2018 | College totals 2003–2015 | [DATA] Market "largely corrected"; always-over and always-under both unprofitable | **Current best on totals: efficient** |
| Arscott, "Market Efficiency and Censoring Bias in College Football Gambling," JSE 24(5):664-689, 2023 | About the last two decades | [DATA] Spread plus total imply team scores that are biased by the floor at 0; a team-total rule wins **over 55%** | Most recent; untested out of sample |

Sources, in table order:
- Sinkey & Logan: http://www.aeaweb.org/conference/2010/retrieve.php?pdfid=406
- Fair & Oster: https://ideas.repec.org/p/ysm/wpaper/amz2377.html
- Krieger et al.: https://ideas.repec.org/a/buc/jpredm/v7y2013i1p13-26.html
- Paul, Weinbach & Higger: https://ideas.repec.org/a/buc/jpredm/v7y2013i2p29-41.html
- Bennett 2019: https://ideas.repec.org/a/kap/atlecj/v47y2019i1d10.1007_s11293-019-09611-y.html
- Bennett 2021: https://econpapers.repec.org/RePEc:taf:apeclt:v:28:y:2021:i:12:p:1006-1009
- Cox et al.: https://ideas.repec.org/a/sae/jospec/v22y2021i3p251-273.html
- Kuester & Sanders: https://ideas.repec.org/a/spr/jecfin/v35y2011i1p116-122.html
- Traugutt & Morton: https://ideas.repec.org/a/ebl/ecbull/eb-22-00065.html
- Paul & Weinbach 2005: https://econpapers.repec.org/RePEc:spr:jecfin:v:29:y:2005:i:3:p:409-415
- Paul & Weinbach 2009: https://ideas.repec.org/a/taf/intgms/v9y2009i1p55-66.html
- Francisco & Moore: https://ideas.repec.org/a/spr/jecfin/v42y2018i4d10.1007_s12197-018-9437-y.html
- Arscott: https://econpapers.repec.org/RePEc:sae:jospec:v:24:y:2023:i:5:p:664-689

Your sub-questions:
- **(i) Group of 5, low-limit or early-season games less efficient?**
  - G5: Bennett 2021 found the effect only outside the Power 5 [CLAIM]. Krieger 2013 and Paul et al. 2013 found mispricing in power-vs-small mismatches [DATA, 2002–2011]. Sinkey & Logan found **no** conference effect for 1985–2003.
  - Limits: no paper tests limit size directly.
  - Early season: Bennett 2019 (the opener) is the only early-season evidence.
- **(ii) Favorite/home biases:** found in 1985–2003 data (away favorites overpriced). Not re-tested on recent data that I found.
- **(iii) Last season's top teams overvalued early:** yes for 2008–2016, previous top 10. Never re-tested post-portal.
- **(iv) Totals:** efficient for 2003–2015. The open angle is team totals near zero (Arscott 2023).
- **(v) Power vs non-power mismatches:** see the table. Both studies predate the College Football Playoff and NIL.

## 10. Structural differences between college and the NFL, with numbers

**Plays per game**
- [DATA] FBS 2022: 179.3 plays per game. FBS 2023 (first 4 weeks): 176.1, after the first-down clock rule. NFL 2022: about 151–155.
  - https://www.cbssports.com/college-football/news/early-returns-show-change-in-first-down-rule-hasnt-resulted-in-feared-negative-impact-on-college-football
  - https://www.espn.com/college-football/story/_/id/36255797/ncaa-approves-rule-change-run-clock-first-downs
- I found no published number for tempo variance between teams (spread across teams). [OPINION] Compute it from CFBD plays and drives.

**Garbage time**
- [DATA] 10.7% of FBS possessions from 2007 to 2023 were garbage by FEI's rules. https://bcftoys.squarespace.com/notes
- No matching NFL figure was found.

**Key numbers**
- [CLAIM] FBS margins of exactly 3 or 7: about 16% of games (3 about 9%, 7 about 7.5%), against 24.3% in the NFL. Blog source, method not shown: https://campus2canton.com/?p=17963
- [DATA] NFL margin of 3: 15.12% and 7: 9.03%, 1999–2025: https://www.deucescracked.com/blog/nfl-margin-of-victory-data-1999-2025
- [OPINION] No authoritative FBS table was found. Compute it from CFBD `/games`.

**Home field advantage**
- [DATA] 2.8 points per game (0.11 points per drive), 2005–2023, 15,618 FBS and FCS games. Only 11 of 247 stadiums differ from average, about what chance predicts. Wharton (Sabin, 2024): https://wsb.wharton.upenn.edu/?p=9411
- [CLAIM, abstract] Home advantage is "declining in the NFL and the highest levels of collegiate football." Benz, Bliss & Lopez 2024: https://arxiv.org/abs/2401.16392v2
- [DATA, one tracker] 2023: home teams won 63.6% of games with a +7.6 average margin. This is not adjusted for scheduling, since many home games are buy games.
- [CLAIM] The average FBS-vs-FBS spread was 10.44 in 2024, the lowest in 40 seasons (ESPN Research, via search snippet).

**Transfer portal and returning production**
- No published post-2021 study of early-season line accuracy was found. Only commentary that Week 1 is the "toughest week": https://www.si.com/betting/si-betting-mailbag-college-football-week-1-clemson-transfer-portal-and-betting-big-spreads-01m1pvnhxhzq
- [CLAIM] Connelly cut the recruiting weight because of transfers (section 1).
- **Gap:** testable with CFBD.

**Opening to closing movement**
- [DATA] The Prediction Tracker's mean absolute error for the opening vs updated line:
  - 2026: 12.19 vs 11.70 (closing is about 0.5 points better)
  - 2025: 11.89 vs 11.85 (about 0.04 better)
- No study of average movement size was found. CFBD `/lines` has both `spreadOpen` and `spread`, so it can be computed.

**Betting limits**
- [CLAIM] Circa's college openers: $2,000 per side and $1,000 per total. No tier split given. https://www.reviewjournal.com/?p=2139517
- [CLAIM] Bettormetrics: in-game suspensions run 8.7% longer for college than NFL (one week, 9 operators). The idea that lower-tier games run longer is the writer's speculation. https://www.casino.org/news/sportsbook-halts-on-college-games-last-longer-than-those-on-nfl/
- **I found no published limit schedule by conference tier.**

**Extreme early mismatches**
- [CLAIM] Home favorites of 36+ points in weeks 0–1, 2013–2025: 18-5 ATS on closing lines. That is 23 games and data-mined (Makinen, VSiN, via RotoWire): https://www.rotowire.com/cfootball/article/the-week-0-mismatch-index-130066

## 11. CollegeFootballData (CFBD) — free tier

**Tiers** — [DATA] https://collegefootballdata.com/api-tiers

| Tier | Price | Calls per month |
|---|---|---|
| Free | $0 | 1,000 |
| Academic (.edu) | $0 | 3,000 |
| Tier 1 | $1 | 5,000 |
| Tier 2 | $5 | 30,000 |
| Tier 3 | $10 | 75,000 |
| Tier 4 | $15 | 125,000 |
| Tier 5 | $20 | 200,000 |
| Tier 6 | $30 | 500,000 |

- Tier 1 adds opponent-adjusted metrics, weather and the live scoreboard. Tier 2 adds live play-by-play. Tier 3 and up add GraphQL.
- One key is shared with the basketball API.
- No "Tier 0" name exists; the free tier is the closest match.

**Endpoints** — [DATA] From the OpenAPI spec v5.34.0 (https://api.collegefootballdata.com/api-docs.json). In the spec, only `/games/weather` ("Requires Patreon") and `/games/{id}/preview/adjusted` (Tier 1) are flagged as paid.
- Plays and drives: `/plays`, `/plays/stats`, `/drives`, `/live/plays`
- EPA (CFBD calls it PPA): `/ppa/games`, `/ppa/teams`, `/ppa/players/*`, `/ppa/predicted`
- Advanced stats: `/stats/season/advanced`, `/stats/game/advanced`, `/stats/game/havoc`, `/game/box/advanced`
- Opponent-adjusted: `/wepa/team/season`, `/wepa/players/*`
  - The tiers page says opponent-adjusted metrics are Tier 1; the spec does not flag these. Verify with a call.
- Returning production: `/player/returning`
- Portal: `/player/portal`
- Talent composite: `/talent` (247Sports)
- Recruiting: `/recruiting/players`, `/recruiting/teams`, `/recruiting/groups`
- Ratings: `/ratings/sp`, `/ratings/sp/conferences`, `/ratings/fpi`, `/ratings/elo`, `/ratings/srs`, `/ratings/core`
  - **No FEI endpoint.**
- Lines: `/lines`, with fields `spread`, `spreadOpen`, `overUnder`, `overUnderOpen` and moneylines per provider; plus `/teams/ats`
- Win probability: `/metrics/wp/pregame`, `/metrics/wp`
- Other: `/teams/season/overview` (includes garbage-time splits), `/roster`, `/coaches`, `/venues`, `/games/media`

[OPINION] At 1,000 calls a month, season-level pulls are cheap. For example, one call to `/lines?year=` covers a whole season. Play-by-play by week across many seasons will hit the cap.

---

## Where college differs from the NFL for a structural reason

| Candidate | Evidence | Testable with free data? |
|---|---|---|
| **Tier and information gap** (G5/non-P5 games less efficient) | Bennett 2021: next-game reaction inefficient only outside the Power 5 [CLAIM, abstract]. Krieger 2013 and Paul et al. 2013: power-vs-small mismatches mispriced, 2002–2011 [DATA]. Against: Sinkey & Logan found no conference effect, 1985–2003. | **Yes.** CFBD `/lines` (open + close) + `/games` conference fields → ATS and closing-line error by tier and season. |
| **Roster churn** (preseason priors noisier post-portal) | Connelly cut recruiting weight for transfers [CLAIM]; Bennett 2019 previous-top-10 holdover, 2008–2016 [DATA]. No post-2021 test found. | **Yes.** `/player/returning`, `/player/portal`, `/talent`, `/ratings/sp` + `/lines`: early-week error vs returning production, 2015–2020 vs 2021+. |
| **Turnover luck regression** | Connelly: 32 of 36 extreme-luck teams reversed, 2024→2025 [DATA]. Steele FCS 55/80 [CLAIM]. Market pricing untested. | **Yes.** Derive expected turnovers from `/plays`; regress next-season ATS on prior luck. |
| **Weaker key numbers** (teasers and half-points worth less) | FBS 3+7 ≈ 16% vs NFL ≈ 24% [CLAIM]; 2021 college teasers failed breakeven [DATA, one season]. | **Yes.** Margin histogram from `/games`. |
| **More plays and garbage time** (more variance, blowout distortion) | 176–179 vs about 155 plays per game [DATA]; 10.7% garbage possessions [DATA]. | **Yes.** `/plays`, `/drives`, `/teams/season/overview` garbage splits. |
| **Scores floored at zero** (team totals in mismatches) | Arscott 2023: >55% rule over about two decades [DATA, abstract]. | **Partly.** CFBD has full-game totals and spreads, not team-total prices. The implied-score bias can be tested; the bet itself cannot. |
| **Home field smaller than folklore, and falling** | 2.8 points 2005–2023 [DATA]; declining at the top level [CLAIM]; stadium-specific effects mostly noise [DATA]. | **Yes.** `/games` + `/venues` + `/lines`. |
| **Lower limits and liquidity in small games** (slower price discovery) | Only Circa opener limits [CLAIM] and the 8.7% longer pauses [CLAIM]; no tier limit schedule found. | **Indirectly.** Opener-to-close movement and opener error by tier, from `/lines` `spreadOpen`. Limits themselves are not observable. |
| **Bettor money on big brands** (AQ/P4 over-bet) | Paul et al. 2013: AQ teams get a disproportionate share of bets [DATA]. | **No** with free data: no ticket or handle splits in CFBD. |

[OPINION] All the free-data tests should be scored against the **closing** spread (`/lines` `spread`), not the opener. Closing line value against the opener is a separate question. The Prediction Tracker shows the closing line's error is about 0.04–0.5 points lower than the opener's, which is the room an early bettor has to work with.

## Could not open

- ESPN SP+ method pages (ESPN+ paywall)
- Football Study Hall 2018 article (connection reset, also blocked to curl)
- superwestsports (410) and BVM Sports (404)
- Springer full texts (Bennett 2019, Francisco & Moore): login redirect
- Applied Economics Letters full text (403)
- ubplj.org (TLS error)
- Fair & Oster PDF: no text layer
- ESPN Walters excerpt (404)
- K-State press release (404)
- bcftoys `/fei` (404)
- arXiv HTML for home-field numbers (404)
- Dr. Bob's past-performance page (not fetched)
- Lem Banker and Wong book texts (none online)
- The Prediction Tracker's ATS grading rule (not stated on the page)
