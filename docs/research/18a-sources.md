# 18a: Evidence brief for the independent model review (extends 14a)

Compiled 2026-11-23. This brief builds on `docs/research/14a-sources.md` and doesn't repeat it. Where 14a already covers a source (Benter 1994, Kaunitz 2017, Levitt 2004, Whelan on CLV, Pinho, Moskowitz, the Massachusetts limiting data, Buchdahl's Kelly simulation, 4for4 and PFF on props), it is cited as "(14a §x)". This brief adds new sources, a fresh own calculation, and the implications for the model as it is described now:
- a game script for sides, totals, team totals and props;
- blend weights of 0.25 (sides), 0.35 (totals), 0.4 (team totals) and 0.5 (props) on its own number;
- a bet when the edge is at least 3-4%.

**Tags**
- **SHOWN:** the source presents data or a reproducible calculation.
- **ASSERTED:** a credible person states it without data.
- **FOLKLORE:** widely repeated, with no traceable source.

I opened every URL listed unless it says "not opened". "Own calc" means I computed it from nflverse `games.csv` (consensus closing lines), downloaded today.

---

## 1. How serious bettors and public research build side, total and prop models

- **Market-first construction dominates.** In the 2019 golf study, Data Golf's own model lost 0.92% a bet when it bet every positive edge against 11 books (106,204 matchups, 2019-20). It made money only at an edge threshold of 5% or more, peaking at +4.43% at 8%. Its no-vig Pinnacle closing lines were the most accurate of any book. **SHOWN.** https://datagolf.com/analyzing-betting-odds
- **A structural model can be better calibrated and still add nothing.** A 2026 study ran a Dixon-Coles model against the Serie A no-vig close (7,220 matches, 7 test seasons):
  - The market won all 7 seasons (RPS 0.1905 vs 0.1972).
  - The model was better calibrated (slope 0.995 vs 1.103), but the market discriminated better.
  - A shots-based variant earned weight 0.35 against the goals model but 0 against the market.
  
  **SHOWN.** https://arxiv.org/abs/2608.11505
- **Props are priced by copying and in-house guesses, not by a market.** Ed Miller (co-author of *The Logic of Sports Betting*): "For the most part there is no real market for props." Books build prop menus by copying competitors, and moves in the main market "usually aren't distributed to any related prop markets." He predicted props would get sharper. **ASSERTED.** https://www.cardplayer.com/?p=1038608 . I could not open the book itself, and the Legal Sports Report excerpt covers only in-play betting.
- **The documented "elite" builds are player-level and simulation-based**, not team-level: Voulgaris (minutes → possessions → totals, 14a §3) and Walters (ratings for each player, 14a §1). I found no public NFL or college model with a published walk-forward record against the close. **ASSERTED.**
- **Unexpected Points** is a Substack and podcast. Its archive (https://www.unexpectedpoints.com/archive) has no betting-market posts. The 2020-22 podcast episodes mention "model-based best bets" without any record. There's nothing citable.

**Implication for this model**
- Building a game script from implied team points is the right *shape*, because it reads the market first. But what it outputs for sides and totals is mostly the market re-expressed. Any extra value it carries has to come from inputs the market doesn't have, and an internal walk-forward test already found none for sides.

## 2. Blending your own model with the market: how to estimate the weights

- **Benter fits the model and the market jointly**, by maximum likelihood in a conditional logit. The model's value is its ΔR² *over* the public, which was +0.0178 for him. A model that was decent on its own added nothing once combined with the public (14a §4). **SHOWN.**
- **Weights fitted by out-of-sample log loss land at zero against a sharp close.** In the Serie A study, log loss rose steadily as the model's weight increased, so the optimum was w = 0.000, "a boundary solution, not an optimisation artefact." **SHOWN.** https://arxiv.org/abs/2608.11505
- **Weights are higher only in thin markets.** Data Golf's best blend was about 45% model and 55% book overall (60-65% in a 2020 subset that may have been cherry-picked). For ranking books against each other, though, Pinnacle's close should get 95-100% of the weight. **SHOWN.** https://datagolf.com/analyzing-betting-odds
- **Log loss is the right scoring rule for blending.** Hubáček, Šír and Šourek show that minimising cross-entropy equals maximum likelihood, and that Kelly growth equals the market's KL divergence from the truth minus the model's. Mean squared error is maximum likelihood only under Gaussian errors. They also argue a model can profit while being *less* accurate than the market, but only if its errors are uncorrelated with the market's. **SHOWN** (theory). https://ar5iv.labs.arxiv.org/html/2010.12508 . Their 2019 International Journal of Forecasting NBA paper applies this idea to NBA 2007-14 (abstract via search only; not opened).
- **Least squares on point margins suits the spread distribution, not the weight.** The weight is estimated properly by logistic or likelihood regression of the outcome on logit(market) and logit(model). Benter's form also lets the market coefficient differ from 1, which captures favourite-longshot bias. **ASSERTED** (follows from the papers above).

**Implication for this model**
- The configured own-model weights (0.25 / 0.35 / 0.4 / 0.5) **are not supported by his own walk-forward results**, which put the model near 0 for NFL sides, team totals and NBA/college sides. With w = 0.25 and the model 8 points of probability away from the market, the "edge" is 2 points, all of it noise. Set each weight to its fitted value. Where that is about 0, the model can rank games but cannot price them.
- Fit the weights by log loss against Pinnacle's no-vig *close*, with standard errors. Use the lower confidence bound, not the point estimate. For props there are no historical lines, so the 0.5 weight is untested. Hold it at 0 until a forward test against Pinnacle supports more.

## 3. Closing-line value: how predictive it is, and how many bets are needed to judge it

- **The close predicts results well on average in big soccer samples.** The slope of expected against actual yield is about 1.00 (88k to 474k prices; 14a §5.2-5.3). **SHOWN.**
- **Positive CLV is not the same as profit.** Two sources show the gap:
  - Whelan, NBA moneylines: only the top CLV decile made money (14a §5.5).
  - Data Golf: Pinnacle's close moved about 55% of the way toward Betcris's opener when the two differed by 5%. Yet betting the opener against Pinnacle's close returned -1.09% at a 0% threshold.
  
  **SHOWN.** https://datagolf.com/analyzing-betting-odds
- **The Pinnacle close may be drifting.** Bets with +4.2% expected value against the close returned only +1.9% from 2023-24 onward (n = 6,806; 14a §5.6). **SHOWN** (preliminary).
- **CLV converges fast.** Buchdahl's case study had 23 of 26 tips shorten, p ≈ 1e-5 (14a §5.4). He has said about 50 bets can be enough at a 5% CLV. **ASSERTED.** The page with that claim is gone (410 at https://pod-d614f9k2t-pod-team.vercel.app/blog/closing-line-value--clv-demystified-by-expert-joseph-buchdahl ; not opened).
- **Own calc (arithmetic).** At -110 with a true win rate of 54%, results need about 3,600 bets to separate from break-even, and 5,900 bets for 80% power (14a §9.6). If CLV per bet has an SD of about 3-4 percentage points of probability, then 100 bets give a standard error of about 0.35 points on mean CLV. A mean CLV of 1.5 points or more would then show up within roughly 100 bets. **ASSERTED** (the SD is assumed, not measured).
- Data Golf: with 10,000 bets, chance alone can still swing ROI by 2-3%. **SHOWN.**

**Implication for this model**
- Judge each market by mean no-vig CLV against Pinnacle after about 100-200 bets. Require the CLV to exceed Wagerhouse's margin (about 2.4 points at -110 sides, more on Bet Builder props), not just to be positive.
- Results alone can't validate a 2% edge within this lifetime of bets.

## 4. Staking: Kelly, uncertainty in the edge, risk of ruin

- **Thorp's sports-betting test (1994):** a $50k bankroll returned $123k over 101 days, against about $89k expected, on about $2M of action at a typical 6% edge. He deliberately used conservative edge estimates "because… overbetting is much more severely penalized." **SHOWN** (his own account). https://www.Gwern.net/doc/statistics/decision/2006-thorp.pdf (text extracted locally)
- **Thorp's fractional-Kelly maths:**
  - Half Kelly keeps 3/4 of the growth rate.
  - The chance of doubling before halving rises from 2/3 to 8/9.
  - The chance of *ever* losing half the bankroll falls from 1/2 to 1/8. In general it is x^(2/c−1) for fraction c, so quarter Kelly gives 1/128.
  - If the true edge is half the estimate and you bet full Kelly, growth is zero. At 1.5 times Kelly you are ruined.
  
  **SHOWN** (derivation). Same source.
- **Baker and McHale (2013, *Decision Analysis*):** with the win probability estimated, the optimal stake is a *shrunken* Kelly. It beat raw Kelly out of sample in simulation and on tennis data, and they give a back-of-envelope shrinkage factor. **SHOWN** (abstract only; full text not opened). https://ideas.repec.org/a/inm/ordeca/v10y2013i3p189-199.html
- **Haghani and Dewey's coin flip.** 61 quantitatively trained subjects got a $25 bankroll and a 60% coin; Kelly is 20% a flip. Results:
  - 28% went bust and 21% reached the $250 cap.
  - The average payout was $91 against about $240 possible.
  - 67% bet tails at some point.
  
  **SHOWN.** https://ar5iv.labs.arxiv.org/html/1701.01427
- **Fractional Kelly in practice.** Fractional Kelly had 0% ruin, while full Kelly went bust in 100% of NBA trajectories (14a §9.3). Believing a 5% edge when the truth is 2.5% gives about 50% P(profit) over 1,000 bets (14a §9.2). **SHOWN.**
- **Own calc.** At -110 the Kelly fraction is f* = (0.909p − q)/0.909:
  - 54% true → 3.4% of bankroll.
  - 53% → 1.3%.
  - 52.38% → 0.
  
  A blended "3-4% edge" that is really 1-2% therefore calls for well under 1% of bankroll.

**Implication for this model**
- A flat 1 unit is right until CLV proves the edge. After that, use about quarter Kelly on the *lower confidence bound* of the edge, not the point estimate.

## 5. Correlated bets on the same game

- **Thorp's two-bet solution.** For two bets with the same edge m:
  - Independent: f* = m/(1+m²) each, almost the full single-bet Kelly.
  - Perfectly correlated: f* = m/2 each, so the *combined* stake equals one Kelly bet.
  
  He adds that correlation alone isn't enough; you need the full joint distribution. Blackjack hands at the same table, with correlation about 0.5, "should substantially reduce the Kelly fraction per hand." **SHOWN.** Thorp, above.
- **Favourites covering go with overs.** Davis, Dawson and Krieger (2018), college football 2005-15: when the favourite covers, the game is more likely to go over. Books that refuse same-game parlays may be "too conservative." **SHOWN** (abstract only; no effect sizes on the page). https://ircommons.uwf.edu/esploro/outputs/journalArticle/Correlated-parlay-betting/99380090298406600
- **Books price parlays above independence.** On Kalshi, executed parlay prices sit above the independent-leg price (12,639 cross-game parlays, 2026). **SHOWN** (abstract; prediction market, not a sportsbook). https://arxiv.org/pdf/2607.14430 (not read beyond the search abstract)
- **No public study** measures the correlation between a team total, a player prop on the same team and a teaser leg. Gap.

**Implication for this model**
- Treat a team-total over, an over on one of that team's players and a teaser leg on that team as **one position**. Cap the combined stake at a single bet's size (Thorp's ρ = 1 case) unless a simulation from the game script gives the joint distribution.
- The game script can produce that joint distribution, which is one real use for it even with a market weight of about 1.

## 6. Soft books: softer lines, shading, limits, juice

- **Prop accuracy differs by book, but not much.** On 12,624 paired NFL prop closes (OddsJam 2024), the Brier score was 0.2474 for Pinnacle, 0.2484 for ESPN BET and about 0.2490 for DraftKings and BetMGM. Pinnacle is sharpest, but the gaps are small and of uncertain significance, and the author found no over/under direction. **SHOWN.** https://shaanchanchani.github.io/articles/sportsbook-props
- **Margins vary a lot by book.** In golf, blind returns ranged from -3.31% at Pinnacle to -7.08% at Bet365. Offshore books (5Dimes, BetOnline, Bovada) "largely follow Pinnacle's prices." **SHOWN.** https://datagolf.com/analyzing-betting-odds
- **Limits.** In Massachusetts, operators' stake factors track CLV (14a §6.4). Further claims, **ASSERTED** from interviews, limited accounts and screenshots rather than book data:
  - Books can flag likely winners "within hours".
  - CLV bettors get limited even when they are net losers.
  - Prop limits for limited accounts are about $15-50.
  
  https://howgamblingworks.substack.com/p/the-truth-about-limits . BetMGM says it limits about 1% of advantage players, **ASSERTED**: https://www.covers.com/industry/true-state-of-sports-betting-part-iv-whither-the-winners-limiting-regulation-february-2025
- **Follower books post props late and cap exposure with low limits** instead of making props efficient. **ASSERTED.** This is from search snippets of Establish the Run; the site returned 403, so not opened.

**Implication for this model**
- Wagerhouse is an offshore follower book. Its main lines are probably copied from Pinnacle with a lag, so the measurable edge is that lag, not the model.
- Price Bet Builder juice explicitly. At -120/-120 the break-even is 54.5%, so a 3% blended edge on a prop may be negative after the margin.
- Expect props to be the fastest route to being limited.

## 7. Teasers after the rule changes

- **Own calc, nflverse consensus closes.** Wong legs are +1.5 to +2.5 and -7.5 to -8.5, teased 6, pushes excluded. 95% intervals in brackets:

  | Period | Record | Hit rate | 95% CI |
  |---|---|---|---|
  | 1999-2014 | 470-174 | 73.0% | 69.6-76.4 |
  | 2015-17 | 154-40 | 79.4% | 73.7-85.1 |
  | 2018-22 | 226-73 | 75.6% | 70.7-80.5 |
  | 2023-26 | 227-76 | 74.9% | 70.0-79.8 |
  | 2018-26 pooled | 453-149 | 75.2% | 71.8-78.7 |

  **SHOWN.**
- **Own calc, totals filter and favourites.**
  - Totals ≤44 against >44 in 2018-26: 75.1% vs 75.4%. **No totals effect.** Covers' "about +1% per leg at 49 or below" gives no sample (**ASSERTED**; https://www.covers.com/nfl/teaser-strategy).
  - In 2023-26, favourite legs went 52-29 (64%) and underdog legs 175-47 (79%). That is small-n, but it points the same way as Covers' "road legs +3-4.5%".
- **Break-even per leg.** Payout +100: 70.7%; -110: 72.4%; -120: 73.85%; -150: 77.5%. **SHOWN** (arithmetic). https://unabated.com/articles/profitable-nfl-teaser-bets . Unabated cites Wong's 76.1% and gives no modern sample.
- **Key numbers since the 2015 extra-point move.** Margins of 6 and 8 rose, and 7 fell to 7.8% in 2020-26 (14a §8.6). **SHOWN.** I found no data on the 2024 dynamic kickoff's effect on margins.
- **Books avoid the Wong-eligible numbers.** They shade lines away from them and grade a push as a loss. **ASSERTED** (several guides; no data).

**Implication for this model**
- His 75.8% for 2023-26 matches my 74.9% (CI 70.0-79.8). The edge over 72.4% (-110) is about 2.5 points, but the lower bound sits *below* break-even, and the leg needs Wagerhouse's number to match consensus.
- At -110 the bet is plausibly positive. At -120 it is close to break-even.
- Paper-trade at Wagerhouse's own numbers. Prefer underdog legs. Drop the totals filter.

## 8. Wind and weather totals

- **Borghesi (2008), 1984-2004:** the market under-priced adverse weather. **SHOWN** (abstract only; 14a §7.7). I found no peer-reviewed study from the 2020s.
- **Covers/Roth, 2,720 games 2010-25.** In 25+ mph wind, scoring falls about 15% and passing yards 19%. Unders against the close hit about 55% at 10 mph or more, against 48% in calm games. He also says the market is "well aware" of wind and that totals "drop quickly". No per-bucket sample or timing data. **SHOWN** (rates only) / **ASSERTED** (speed). https://www.covers.com/nfl/how-wind-impacts-nfl-games
- **Own calc (14a §7.9), 2015-26 under rates by wind:**
  - 10-14 mph: 59.2% (n = 463).
  - 15-19 mph: 58.2% (n = 177).
  - 20+ mph: 50.0% (n = 48).
  
  This uses *observed* wind against the close, which isn't available at bet time. **SHOWN** (with caveats).
- Wind forecasts are reliable about 3 days out. **ASSERTED** (meteorologist quoted by numberFire; not opened).

**Implication for this model**
- The best case is moderate wind (10-19 mph) under-reacting even at the close, which supports the small positive NFL totals weight. Strong wind looks priced in.
- Test the model on *forecast* wind at the time of the bet, against the closing total. Without that test, the effect may be partly look-ahead.

## 9. Multiple testing and backtest overfitting

- **Bailey and López de Prado (2014), the Deflated Sharpe Ratio.** The best of N trials has a positive expected maximum Sharpe even when true skill is zero, and that maximum grows with N and with the variance across trials (their Eq. 1). The deflated ratio raises the bar for a strategy that was picked from many tries. **SHOWN.** https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf (text extracted). The SSRN page (https://papers.ssrn.com/abstract=2460551) returned 403.
- **Their practical rules:**
  - Record every trial.
  - Estimate how many trials were effectively independent.
  - Hold-out data reused for selection is no longer out of sample.
  - The companion probability-of-backtest-overfitting (PBO) method is non-parametric.
  
  **SHOWN/ASSERTED.** Same source.
- **In this domain specifically:**
  - Data Golf flags that a favourable subset "was likely selected because it looked favorable" (**ASSERTED**).
  - Benter used a separate second-stage fit on out-of-sample model probabilities (14a §4).
- **Own count.** The project's own record (CLAUDE.md "Failed so far") lists at least 8 full-game models tried and 3 sports, plus thresholds and blend weights. **ASSERTED** (from project docs).

**Implication for this model**
- The surviving positives (NFL totals weight, Wong teasers, props "honest" against held-out results) were each chosen from a family of tries.
- Apply a Bonferroni-style or deflated threshold across the roughly 10-20 effective tests.
- Treat 2026-27 forward results as the only clean test, and freeze the specification before that season starts.

## 10. Player props: which markets are softest, and evidence of edges

- **Pinnacle props are only slightly sharper than US retail books** (Brier gap about 0.001-0.002; section 6). **SHOWN.** So Pinnacle no-vig is a reasonable reference for props, but it isn't strong evidence of the truth.
- **Under bias.**
  - Season-long NFL unders hit 60-63% in 2021-22, and receiving-yard unders 57% (n = 157). **SHOWN** (small n; season-long). https://www.4for4.com/2023/preseason/key-winning-season-long-player-props
  - Weekly passing-yard unders were the only blind-profitable category in 2020-22 (14a §10.4). **SHOWN.**
  - The NBA FanDuel thesis found no consistent direction (14a §10.7). The explanations (public overs; skewed distributions) are **FOLKLORE / ASSERTED**.
- **Prop markets are thin, not efficient.** Ed Miller: no real market, main-market moves don't flow through to props, and "very soon they may not be so easy to beat." **ASSERTED.**
- **No peer-reviewed or public study** shows a model beating a *sharp* prop close. Student and hobby XGBoost projects that track CLV give no audited results (e.g. https://danmikel1.github.io/nbaBetlab/, not opened beyond the search snippet). Gap.
- **Low-volume players and alternate lines are softest.** **FOLKLORE.** No data found.

**Implication for this model**
- "Honest against held-out results" is necessary, but it isn't evidence of an edge against the line. The edge has to be measured against Pinnacle prop prices captured going forward (already planned).
- Expect the real edge, if any, in Wagerhouse lagging Pinnacle on prop moves after news. Expect it to be small, low-limit and the quickest route to being limited.
- Favour unders only once his own forward data shows it.

---

### Not opened or failed
- SSRN DSR (403).
- Establish the Run (403).
- The Buchdahl CLV page on Vercel (410).
- The walrusquant teaser post (404).
- The football-data Wisdom of the Crowd results (an Excel file only).
- The full texts of Baker-McHale and Hubáček 2019 (abstracts only).
- *The Logic of Sports Betting* and *Sharp Sports Betting* (no excerpt on these topics).
- An Unabated blending article (none found).
- Sportsbook "same-game parlay" guides, excluded as operator promotional pages.
