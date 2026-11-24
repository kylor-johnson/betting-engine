# 18. Independent evaluation of the live betting model (Nov 23, 2026)

Written by a fresh session acting as an outside reviewer. I re-ran every walk-forward test the live picks rely on, built my own teaser and wind
checks straight from the raw nflverse file, tested the props models against Pinnacle on everything graded so far, and read the code that sends
the picks. The sources are in `18a-sources.md`; the scripts are in `scripts/research18/`. **Nothing in code, config or schedules was changed.**

## The answer: which bets should I keep making with real money, and how sure am I?

**Keep one lane on real money: the NFL Wong teasers.** It is the only lane where the evidence is independent of this engine and points the right
way. Underdog and favorite legs that cross 3 and 7 won 76.3% of the time from 2015 to 2026 (607 of 796 legs on closing lines), against 72.4%
needed at Wagerhouse's -110. A $50 ticket is worth about **+$3 on average** (my central estimate is +6% a ticket, with a range from about -1% to
+13%). I'm fairly sure it's positive, though not certain: the edge is about 3 to 4 points of win rate per leg, and favorite legs have been weak
since 2023 (42-24).

**Move everything else to paper: NFL sides, totals and team totals, NFL props and NBA props.** Keep issuing those picks and grading them, but
don't put money on them. I'm confident none of them is profitable as built. My estimate is **-2% to -6% per bet** at Wagerhouse's prices:

- **Full-game NFL picks.** The model's own number adds nothing over the market, as the earlier tests already found. The one "lead" (NFL totals)
  turns out to be the wind input, measured with the actual wind at kickoff instead of the forecast you'd have had when betting. Take the weather
  out and that lead goes from 175-136 to 122-133. The full-game picks that win on average do so because Wagerhouse's number was half a point to a
  point off Pinnacle's, not because of the handicap.
- **Props.** Against Pinnacle, the NFL props model is worse than Pinnacle alone. The best weight to give it is 0.1, not the 0.5 in use. The NBA
  props model has a measured lean toward the Under: it expected 89 Overs out of 209 and 103 hit. Half of that lean goes straight into the live
  picks.
- **A pattern in today's picks.** Several props became bets *because Pinnacle moved away from the model*. Josh Allen's over 244.5 passing yards
  went from -114 to +148 during the day while the model stayed at 51%, so the engine bet into the move.

At the current volume (about 5 NFL full-game picks, 10 NFL props and 28 NBA props a week, plus teasers) the expected result is **about -$25 a
week**, with a swing of about ±$145 in any one week. Four weeks of results can't tell a good lane from a bad one either way. Only closing-line
value can, and it isn't measured yet for props or team totals.

**How sure am I:**
- Very sure on the full-game lanes. Eight years held out, the result reproduces exactly, and the one lead comes from a look-ahead input.
- Fairly sure on props. The samples are small (150 NFL, 209 NBA), but the props weight is 0.1 for NFL, and the NBA Under bias is about two
  standard errors.
- Fairly sure on teasers. Twelve seasons of data, and the rule was written before the data.

### Today's live picks are not what the message says

The decision rules say I flag this at the top. Each pick below is shown at the weight its own test supports: 0 for full-game markets, 0.1 for
NFL props, 0.35 for NBA props. "Edge" is win chance above what the price needs.

| Pick (stake) | Edge in the message | Edge at the tested weight | Why |
|---|---|---|---|
| Commanders team total under 24 -105 ($25) | +4.2% | about +1% | Wagerhouse is half a point off Pinnacle's 23.5. That is the real value. |
| Falcons-Vikings under 42.5 -110 ($25) | +4.1% | about +0.6% | Wagerhouse is a point off Pinnacle's 41.5. The model's 38.5 adds nothing tested. |
| Titans +15 -110 ($25) | +4.0% | about -1.5% | A CHECK pick, cleared because the agent found "nothing" (see worry 4) |
| Ja'Marr Chase under 0.5 TD +123 ($25) | +4.4% | about -0.5% (−3% at the +111 floor) | Also: Wagerhouse may not offer a "No" on anytime TD at all |
| Stefon Diggs under 4.5 rec +109 ($25) | +5.1% | about -0.4% | Same game as the two picks above (worry 3) |
| DeVonta Smith under 64.5 rec yds -114 ($25) | +4.1% | about -1.8% | |
| Josh Allen over 244.5 pass yds +148 ($25) | +4.0% | about -1% | Pinnacle moved from -114 to +148 against it during the day |
| Donovan Mitchell under 36.5 PRA -108 ($12.50) | +4.1% | about +2% at Pinnacle, 0 at the -117 floor | NBA Under bias |
| Coby White under 1.5 threes +146 ($12.50) | +4.0% | about +1.9% at Pinnacle, below 0 at +134 | NBA Under bias |
| Brook Lopez over 12.5 pts +118 ($12.50) | +5.8% | about +3.4% at Pinnacle, below 0 at +101 | CHECK cleared on "nothing found". Pinnacle drifted from +103 to +118 against it. |

One-line fix if you agree: set `playbook.units` to 0 for B picks (or `full_game: show` and a props stake of 0), which keeps every pick on
the card and in the record as paper. The teaser lane is separate (`teasers.real_money`) and stays on.

## What is live, graded

EV is my estimate of profit per $1 staked at Wagerhouse's real price. For props, that price is Bet Builder, which we can't read; I assume it
carries 2 to 4 points more margin than Pinnacle.

| Lane | Stake today | EV per bet (central, range) | $ per bet | How sure | Verdict |
|---|---|---|---|---|---|
| NFL Wong teasers | $50 a ticket | **+6%** (-1% to +13%) | about +$3 | Fairly | **Real money** |
| NFL sides | $25 | -3% (-5% to +1%) | about -$0.75 | Very | Paper |
| NFL game totals | $25 | -2% (-4.5% to +1.5%) | about -$0.50 | Very | Paper |
| NFL team totals | $25 | -2% (-5% to +2%) | about -$0.50 | Fairly | Paper (and start grading against the close) |
| NFL props | $25 | -5% (-8% to -1%) | about -$1.25 | Fairly | Paper |
| NBA props | $12.50 | -6% (-10% to -2%) | about -$0.75 | Fairly | Paper. Fix the Under bias first. |
| NBA full-game (shown only) | none | -4.5% (the juice) | n/a | Very | Nothing. Keep it off. |
| College full-game (shown only) | none | -4% (totals slightly better) | n/a | Fairly | Nothing (college totals are a lead to watch, on paper) |
| Wind unders (old path, paper) | none | about 0% (-4% to +6%) | n/a | Low | Paper |

Where the full-game lanes are slightly positive, the reason is that Wagerhouse is a half point to a point off Pinnacle when the pick fires. The
charter says a price gap alone is never a reason for a pick. I'm not reopening that rule, but you should know it is the only thing in these
lanes that has measured value.

## The ten worries, answered

**1. Staking against the evidence.**
- At weight 0 (what the tests support), a full-game pick's true win chance is Pinnacle's at Wagerhouse's line. When the two books agree, that is
  -4.5% a bet.
- My re-run of research 15/17 matches exactly: totals at 4+ points of disagreement go 175-136, sides 189-182, team totals at 3.5+ go 214-194.
- I replayed the live rule (blend at the starting weight, 3% edge) on 2019-2026 closing numbers. With no Wagerhouse gap:
  - totals produced 5 picks in 1,722 games that didn't need a CHECK;
  - sides went 25-27.
- So almost every un-CHECKed full-game pick needs Wagerhouse to be off Pinnacle.
- Estimate: -3% for sides, -2% for totals and team totals.
- **Yes, negative.**

**2. Prop prices are Pinnacle's.**
- The edges are overstated twice:
  - The weight. The forward test, first price seen per prop, gives:

    | Sport | Graded props | Pinnacle log loss | Model alone | Blend at 0.5 | Best weight |
    |---|---|---|---|---|---|
    | NFL | 150 | 0.6967 | 0.7194 | 0.7007 | 0.1 |
    | NBA | 209 | 0.6888 | 0.6955 | 0.6868 | 0.35 |

    Paired bootstrap of the blend minus Pinnacle (negative = the blend is better):
    - NFL: +0.008, 95% interval -0.010 to +0.027.
    - NBA: -0.002, 95% interval -0.014 to +0.012.

    Neither sport shows the model helping.
  - The price. Pinnacle's own prop margin is 4.8% (NFL) and 7.0% (NBA). Bet Builder is worse.
- The "worst Wagerhouse price" is the price where the 0.5-blend edge falls to 2%. At the tested weight, that price is below break-even on every
  prop issued today.
- The limit should be computed at the tested weight with a full 4% margin, or props shouldn't be staked.

**3. Correlation.**
- Real, and larger than the handoff said: there are three positions on Bengals-Commanders tonight ($75).
  - The Commanders team total under.
  - The Commanders' Stefon Diggs under 4.5 receptions.
  - Ja'Marr Chase under 0.5 touchdowns.
- All three win in the same low-scoring script.
- Thorp's two-bet result: perfectly correlated bets should together add up to one Kelly bet (18a §5).
- Fix: cap the total stake on one game at one unit across full-game, props and teaser legs. Or treat the same team's total, player props and
  teaser leg as one position.

**4. CHECK clearing by the agent.**
- On today's files the agent held 13 picks and cleared 4:
  - NBA: 3 of 12. Two were cleared on "nothing found" (Cissoko, Lopez); the third because the Embiid absence is already in the model.
  - NFL: 1 of 5, the Titans side, cleared on "nothing found".
- Its holds were good: real quarterback changes and stars out.
- Its clears turn missing evidence into a bet. A CHECK means the model is 3+ points (side) or 15+ points of chance (prop) from a market that
  is usually right, and the model can't see most news. "I found nothing" is the expected result when the gap is noise, so it should not release
  the pick.
- The backtest shows the rule doesn't fix itself either. The CHECK-only totals picks won 107-79 at the close in 2019-26, but that group is the
  same as the wind-driven 5+ disagreements (worry 6).
- Fix: "clear" needs a positive, sourced reason the market is wrong. A cleared pick stays at most paper until 50 cleared picks show a positive
  closing-line value.

**5. Look-ahead.** Each claim in the handoff, checked in the code:
- **`backup_qb` uses the real starter** (`script.py` line 158, from nflverse's `home_qb_id`). Confirmed. Removing it barely changes the totals
  result (4+: 179-154 without it), so this isn't what drives the result.
- **Wind and rain use reanalysis, i.e. the actual weather at kickoff.** Confirmed, and this is what drives the result. Without the weather inputs
  the totals lead disappears:

  | Weather inputs | Disagreement | Record | Totals error vs market |
  |---|---|---|---|
  | With | 4+ points | 175-136 | |
  | With | 3+ points | 280-247 | |
  | Without | 4+ points | 122-133 | 174.82 vs 174.72, worse than the market |
  | Without | 3+ points | 232-228 | |

  Every winning bucket is in the Unders, which is where wind lives:

  | Wind | 4+ point Unders |
  |---|---|
  | 10+ mph | 50-26 |
  | Under 10 mph | 28-23 |
- **Wind is also counted twice.** The same wind sits in the separate wind lane.
- **The injury clusters use the final report.** They are off, so this isn't live.
- **The team-total test uses implied totals, not real team-total lines.** Confirmed. With no Pinnacle team-total history it can't be redone.
  Because the weight is 0 either way, it doesn't change the verdict.
- **NBA absences.** In history they come from a missing box-score line, which matches the inactive list known before tip-off, so the leak is
  mild. Live, Questionable players aren't adjusted, so live is weaker than the test.

**6. Multiple testing.**
- By my count, research 02 to 17 ran at least 60 bucket tests on full-game markets (8 failed models, 7 script variants, each with 3 thresholds
  and 3 markets, plus NBA and college).
- The best NFL totals bucket has p = 0.09 at 4+ points and p = 0.03 at 6+, both against break-even. Neither survives even a 10-test Bonferroni
  correction (it needs p < 0.005). The schedule adjustment was also picked from seven variants on the same held-out seasons.
- Since 2024 the 4+ bucket is 58-54.
- **Nothing survives.** The teasers stand apart: the rule is from 2001, so 2015-2026 is truly out of sample. Their 607 of 796 legs is p ≈ 0.008
  against 72.4%, which survives a correction for the two or three cuts tried (era, totals filter).

**7. Pricing curves.** The bell-curve widths, compared with the measured spread of actual results around the market (from the walk-forward data):

| Sport | Width used | Width measured | Verdict |
|---|---|---|---|
| NFL team points | 9.0 | 9.1 | Fine |
| College team points | 11.0 | 11.0 | Fine |
| NBA team points | 10.5 | 11.5 | Too narrow, so it overstates NBA team-total edges by about 10% |

- NFL team scores are lumpy (17, 20, 24, 27...), and a bell curve misprices whole-number lines like 24 by about a point of chance either way.
- The market reference is wrong in another way. It takes Pinnacle's *line* and ignores Pinnacle's *price*: a -3 -125 is read as a fair -3.
  Use the no-vig line.
- The college landing tables use 2021+ results and match the measured spread, but the college stale alerts were never graded.

**8. Weight re-fits.** Least squares on points is a fair way to estimate a mean, but two things are wrong:
- **Forty candidates is far too few.** The standard error of a fitted weight at n = 40 is about 0.65 for totals, sides and team totals. The
  error is noise of about 13 points per game against a disagreement of about 3 points. Pinning a weight to ±0.1 takes about 1,500 to 1,900
  games, roughly six NFL seasons. The 4-week re-fit can't move a weight honestly.
- **For props (0/1 outcomes), least squares is the Brier score.** It's acceptable, but log loss is the standard (18a §2). Fit the weight against
  Pinnacle's no-vig *close*, not the first price seen, and use the lower confidence bound.

**9. Full units, no Kelly.**
- At a true 53% and -110, Kelly is 1.3% of bankroll. At the true edges estimated here (below 52.4%) it is zero.
- For teasers at a 74.5% leg rate, full Kelly is about 6% of bankroll a ticket, so quarter Kelly is about 1.5%. A $50 ticket fits quarter Kelly
  on a bankroll of about $3,300. If the bankroll is smaller, teasers should be smaller.
- The stop-loss isn't really a guardrail: 10 units is $500 (NFL) or $250 (NBA), and with weekly swings of about $145 it can be hit by bad luck
  or missed by bad bets.
- Flat staking is right. The size is the issue, together with staking lanes with negative EV.

**10. Drift.** Details are in the next section.
- The numbers in the message match the code.
- The claims are generated from config, as the charter requires, but describe weights the tests reject.
- Four things are out of step:
  1. The NFL and NBA props status rows say "record: No bets... Testing only until 300 props" while also saying they stake real money.
  2. The static table in `CHARTER.md` still shows props as unable to pick and wind as the only model.
  3. `PLAYBOOK.md` §4 still says "$25 unit, half size for 3 weeks".
  4. Decision 0019 still says "$6.25 until Dec 15", but config has `half_size_weeks: 0` and $50 NFL units.
- Separately, playbook and teaser messages aren't saved anywhere after they're sent (`playbook.run` calls `telegram.send` directly, unlike
  `alerts_sent`), so you can't audit what was sent.

## One live message and one card, checked against the code

**The message.** The Commanders team total under 24 (-105), issued 22:51 UTC. It isn't stored, so I rebuilt it from `playbook_picks` and
`playbook.run` (lines 546-547):

> NFL · PLAYBOOK BET (B) / Washington Commanders team total under 24 (-105) / Cincinnati Bengals at Washington Commanders, Mon 6:15 PM MT /
> Stake: $25 (B pick) / Don't bet past Washington Commanders team total under 23.5. / Why: our handicap Cincinnati Bengals 27.9, Washington
> Commanders 21.9 (market ... 30.2, ... 23.8). Blended at the playbook weight, our team total number is 22.9 against Wagerhouse's 24; win chance
> 55.4% against 51.2% needed.

Checked against config:
- **Correct:** the stake ($50 × 0.5), the "don't bet past" number (a 1.5% edge at 23.5), the weights (0.4) and the edge (4.2%).
- **Not correct:**
  - "Win chance 55.4%" holds only at a weight the test sets to 0. At 0 it's about 52%.
  - The "market 23.8" in the Why is the implied team points from the full-game line. The blend actually used Pinnacle's team total of 23.5. Two
    different "market" numbers appear in one message.
  - There will never be a closing-line grade for this pick, because team totals and props aren't graded against the close
    (`playbook.grade` sets `close = None`).

**The card.** `docs/cards/2026-11-23-nfl-playbook.md` (5:17 PM commit):
- Its rows match `playbook_picks`.
- Its header sentence is generated from config ("starting weights side 0.25..."), as the drift guard requires.
- It shows seven NFL staked picks, which the caps allow (5 full-game a week, 10 props a week, 2 props a game). Three of the seven are on one
  game.
- The teaser card matches `teaser_legs` and `teaser_tickets`. Its ticket message correctly says "only if each leg is still in range and the
  price is still -110".

## Re-runs and audits (what I ran, every variant)

| Test | How | Result |
|---|---|---|
| Research 15 and 17 (NFL script) | The engine's own `walk_forward`, `adjust` on and off | Matches the documents to the game |
| The NFL script with look-ahead removed | No QB flag; no weather; neither | No weather: the totals lead disappears (above). No QB flag: almost unchanged. Neither: 4+ 140-143 |
| Totals lead by season and side | From the re-run | 2019-22: 105-73. 2023-26: 70-63. All of it in Unders |
| The live rule replayed at the close | Starting weights, 3% edge | Totals: 5 picks without a CHECK in 8 seasons. Sides without a CHECK: 25-27 |
| Teasers | My own code on `nflverse_games.csv`, closing lines | 2015-26 legs 607-189 (76.3%). 2023-26 200-64 with the totals filter; underdogs 158-40, favorites 42-24. Pushes: 2 in 798 legs, so they don't matter |
| Teasers (research agent, separately) | nflverse, downloaded fresh | 2018-26 75.2% (CI 71.8-78.7). The totals filter makes no difference (75.1% vs 75.4%) |
| Wind (separate source) | nflverse's own game-day `wind` column, outdoor games | 10-19 mph Unders: 2015-18 139-99, 2019-23 179-106, **2024-26 59-58**. The effect looks priced since 2024 |
| Props against Pinnacle | `prop_evals`, one row per prop, first and last price seen | The table in worry 2. The NBA model's average P(over) is 0.426, against 0.493 actual and 0.480 at Pinnacle |
| Size of a re-fit weight | From the walk-forward residuals | Standard error about 0.65 at 40 candidates |

**Not re-run:**
- The NBA and college script walk-forwards (research 16). Both already lost, the code path is the same as the NFL one, and nothing staked
  depends on them.
- The props models' held-out tests against a plain average (research 06, 08). They measure calibration, not edge over the market, so they
  can't support staking either way.

## What to change, keep and stop (ranked by money at stake)

Each item names the test that proves it and the number that would kill it.

1. **STOP real money on NFL and NBA props; keep them on paper.**
   - Test: the blend against Pinnacle's no-vig *closing* prop price, by log loss, on the next 300 graded props per sport, with a bootstrap
     interval.
   - Restart: the blend's lower 95% bound beats Pinnacle, *and* the issued picks' average closing-line value exceeds Bet Builder's margin.
   - Stays stopped: the blend is not better than Pinnacle at 300.
2. **STOP real money on NFL full-game picks (sides, totals, team totals); keep them on paper.**
   - Test: closing-line value of issued picks against Pinnacle's close, at 100 picks.
   - Restart: average closing-line value at or above +2.4 points of win chance (the -110 margin).
   - Stays stopped: below +1 at 100 picks.
3. **KEEP the teasers on real money**, with two changes:
   - check Wagerhouse's 2-team 6-point price and tie rule each month;
   - size tickets at quarter Kelly for your real bankroll.
   - Test: the leg win rate on Wagerhouse's own numbers. Judge on 300 legs, not 150: a sample of 150 has a ±3.5-point error, and the edge is
     only about 3.5 points.
   - Kill: under 72.4% at 300 legs, or the price changes to -120. Watch favorite legs separately (42-24 since 2023). If they are under 70%
     at 100 more legs, make teasers underdog-only.
4. **CHANGE: never bet into a market move against us.** If Pinnacle has moved away from our side since we first priced the pick, by 10+ points
   of chance on a prop or 1+ point on a side or total, the pick drops to C.
   - Test: on `prop_evals` and `playbook_candidates`, compare picks that crossed the edge because the market moved with picks that cleared it at
     first sight, graded on closing-line value.
   - Kill: if picks made after moves show the same closing-line value as the others after 100 of each.
5. **CHANGE: fix the NBA props Under bias before anything else on NBA.** Re-center each stat so the model's average P(over) matches the
   outcomes (0.426 against 0.493 today), then re-blend.
   - Test: the next 300 graded props.
   - Kill: the bias is still beyond ±2 points of chance.
6. **CHANGE: grade props and team totals against Pinnacle's close.** The data is already logged every hour (`prop_evals`,
   `derivative_snapshots`). Without this, the scorecard for most of the staked volume doesn't exist.
7. **CHANGE: CHECK "clear" needs a positive, sourced reason**, not "nothing found". Cleared picks stay paper until 50 show positive
   closing-line value.
8. **CHANGE: one unit per game in total**, across full-game picks, props and teaser legs on the same team.
9. **CHANGE: remove the double count of wind.** Train the NFL script without the weather inputs, or with the day-before forecast. Leave wind to
   the wind lane, which stays paper.
   - Kill the wind lane: forecast-based 10-19 mph Unders under 52.4% over the next 60.
10. **CHANGE: re-fit weights honestly.**
    - Use log loss against the no-vig close, with standard errors, and apply the lower bound.
    - Don't change a weight on fewer than about 300 props or 1,500 games.
    - The 40-candidate rule goes.
11. **CHANGE (housekeeping):**
    - save every Telegram bet message to `alerts_sent`;
    - use Pinnacle's no-vig line, not its raw line, as the market;
    - widen the NBA team-points curve to 11.5;
    - fix the four drift items under worry 10;
    - check that Wagerhouse offers a "No" side on anytime-TD props before issuing one;
    - fix the DuckDB lock collision, which made the poll fail again tonight (`poll.err.log`).
12. **KEEP:** NBA and college full-game picks shown only. Keep logging every candidate, the one-position-per-game rule for full-game picks,
    "don't bet past" on every pick, and the drift guard.

**What to build to get model-driven picks that could earn money.** You asked that "no pick" never be the whole answer, so this is where I'd
look:
- **News-timed props.** A player is ruled out, the model moves minutes and shots to his teammates, and Pinnacle hasn't moved yet. The NBA model's
  news terms are the one piece that clearly beat a plain average on held-out seasons (points and PRA, research 08). The thin prop market
  doesn't pass moves through quickly (Ed Miller, 18a §1).
  - Test: picks issued within 30 minutes of an Out, graded on closing-line value against Pinnacle's prop close.
  - Pass: average closing-line value above +4 points of chance over 100 picks.
  - This is a model pick, not a price gap: the number comes from our minutes model.
- **The game script as a correlation tool, not a pricing tool.** It can tell you which of several same-game bets are really one bet (item 8).

## Four-week plan (Nov 24 to Dec 21)

**Week 1 (Nov 24-30):** when you approve,
- set props and full-game B stakes to 0 (paper);
- add the one-unit-per-game cap;
- add closing grades for props and team totals;
- save sent messages;
- tighten CHECK clearing.

Teasers stay on at a size you set from your real bankroll. Thanksgiving week gives a full NFL slate to test the plumbing.

**Week 2 (Dec 1-7):**
- fix the NBA Under bias;
- add the "no betting into a move" rule;
- start the NBA news-timed props test (paper);
- re-train the NFL script without the actual-weather inputs and re-run research 15 to confirm the totals weight goes to about 0.

**Week 3 (Dec 8-14):**
- the first closing-line-value readout for every lane, at about 40-80 picks each. It isn't enough to restart anything, but enough to catch a
  lane far below zero;
- replace the weight re-fit with a log-loss fit against the no-vig close.

**Week 4 (Dec 15-21):**
- teasers reach about 50-70 graded legs; check them against the 72.4% line and favorites separately;
- written readout: which paper lanes are on track for the restart numbers in the ranked list, and which aren't.

No lane goes back to real money in these four weeks unless its closing-line value is already above its restart line on 100+ picks.

## Sources

`18a-sources.md` (research agent, every claim tagged shown / asserted / folklore, pages it could not open listed). The ones that change
decisions here:
- Data Golf's 106k-bet study (a model earns weight only in thin markets, and still needed a 5%+ edge to profit):
  https://datagolf.com/analyzing-betting-odds
- A 2026 Serie A study where the fitted model weight against the no-vig close was exactly 0: https://arxiv.org/abs/2608.11505
- Thorp's Kelly paper (correlated bets add up to one Kelly bet; overbetting is the costly error):
  https://www.Gwern.net/doc/statistics/decision/2006-thorp.pdf
- Hubáček, Šír and Šourek on fitting with log loss: https://ar5iv.labs.arxiv.org/html/2010.12508
- Bailey and López de Prado on correcting the best of many backtests: https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
- Ed Miller on props having no real market: https://www.cardplayer.com/?p=1038608
- An NFL prop study on 12,624 closing props (Pinnacle only slightly sharper; no over/under bias):
  https://shaanchanchani.github.io/articles/sportsbook-props
