**Kylor: answer yes or no to the 8 items in "What I'd like you to decide" at the bottom. My advice: yes to 1-4 and 6-7, no to 5 (staking college's own model) and 8 (college props).**

# 23. College football model review (Nov 24, 2026)

You said college was neglected next to the NFL. It was, and this note says by how much, what serious college raters do that we don't, and
what happened when I tested the best free ideas. The short version:

- **College got a much thinner model than the NFL, and part of the reason was wrong.** The college model's own comment says CollegeFootballData's
  free tier "has no play-level data". I called it today: the free key returns play-by-play, drives, per-game expected points (PPA) and
  success rate with garbage time already removed, returning production, the talent composite, last season's SP+, ESPN FPI, Elo and the
  transfer portal. So college could have had what the NFL got all along.
- **Giving it that data made the model a little better but did not beat the closing line.** Efficiency and tempo in place of points per
  game: 52.8% on game totals where we disagreed by 4+ points (621-555), 51.0% on team totals, 51.2% on sides. Squared error against the
  close: no better. That is the same outcome the NFL model had (research 15), so college and the NFL are now level, both unproven.
- **Preseason priors (returning production, talent, last season's SP+) made the first four weeks worse, not better.** But the way it lost
  points to something: in weeks 1 to 4, numbers built on last season lose against the close (46 to 48%). That fits research 14's early-season
  hint and is worth a pre-registered test in 2027, not money now.
- **Our number does see something the opener misses.** From the opener, the line moved our way by 0.3 points on sides and 0.4 on totals
  (about 1,600 and 740 bets), but betting the opener still only went 50.8% and 51.0%. The edge is real and smaller than Wagerhouse's margin.
- **The structural differences are real and mostly priced:** college margins land on 3 only 9.8% of the time (NFL 14.9%), lines move more
  from open to close (1.35 points against 1.19), and the market's weakest corners (FCS games) are not ones Wagerhouse posts.
- **Fix now, whatever else you decide:** two documents still tell the research agent a college starting QB is worth 3.5 points; research 22
  corrected that to about 4. The college agent guide has it right; the shared agent prompt and the parity note do not.

With only rivalry week, conference championships and bowls left, anything model-side mostly pays in 2027. What pays now is the news lane in
bowl season (opt-outs and portal exits), which is already live.

## 1. Parity inventory: what the NFL has and college does not

Sources: `models/script.py`, `models/college_script.py`, `PLAYBOOK.md`, `config.yaml` (`playbook`, `parity`), `docs/lanes/STATUS.md`,
research 15 to 18, `ops/agent_prompt*.md`, and live calls to CollegeFootballData (CFBD) on Nov 24.

**Settling the contradiction.** `college_script.py` says the free tier has no play-level data. `PLAYBOOK.md` section 5 says college pace and
efficiency come from CFBD's free tier. The playbook is right; the code comment is wrong. Every endpoint below answered on our free key
(HTTP 200). The free tier's limit is 1,000 calls a month (the account had 819 left this morning); one call returns a whole season of game
stats, so a season's history is about 5 calls. This review used about 40.

| Endpoint | What it gives | Used by college today |
|---|---|---|
| `games`, `lines` | scores, closing lines and **openers** (`spreadOpen`, `overUnderOpen`) from 2021 | Scores and closes only; openers unused |
| `stats/game/advanced` | per game, per team: plays, drives, PPA per play, success rate, explosiveness, line yards; `excludeGarbageTime` | No |
| `plays`, `drives` | play-by-play and drive results | No |
| `ppa/games` | PPA by down and by passing and rushing | No |
| `player/returning` | share of last season's PPA and usage that returns | No |
| `talent`, `recruiting/teams` | 247 team talent composite, recruiting class rank | No |
| `ratings/sp`, `ratings/fpi`, `ratings/elo` | SP+, FPI, Elo (final for past seasons) | No |
| `player/portal` | every transfer with origin, destination, rating | No |
| player game stats (passing) | per player | Yes, for the QB value study (research 21) |

**The inventory.** "Has" = same as NFL, "weaker" = a thinner version, "lacks" = none.

| NFL piece | College | Free data for college? |
|---|---|---|
| Play-by-play team form: EPA per play, success rate, points per drive | **Lacks** (points scored and allowed per game) | Yes: PPA, success rate, drives |
| Pace: drives and plays per game, own and allowed | **Lacks** | Yes: plays and drives per game |
| Pass rate over expected in neutral states | **Lacks** | Buildable from `plays` (no expected-pass model, we'd fit one) |
| Schedule-adjusted form (research 17, the one NFL addition that helped) | **Weaker**: opponents' points form as a regression input | Yes |
| Different starting QB flag inside the script | **Lacks** (QB comes only through the agent's `adjustments.yaml`) | Yes: CFBD passing by player (research 21 used it) |
| QB value measured | **Has**, better than the NFL (about 4 points, research 21 and 22) | |
| Wind and rain in the script | **Lacks** (college wind tested and failed, research 20; rain not tested) | Open-Meteo, free |
| Last season as a prior | **Weaker**: last season counts 2 games (NFL 3); no roster-churn input | Yes: returning production, talent, portal, last SP+ |
| Injury feed | **Lacks**: no free college injury feed; the agent searches availability reports | Conference availability reports (SEC, Big Ten, Big 12, ACC) are public pages, not a feed |
| Matchup block and luck block on the slate for the agent (context only) | **Lacks** (`picks/matchup.py`, `slate.py` are NFL-only) | Yes, from CFBD advanced stats |
| Opener messages and the opener trigger | **Lacks** (`opener_messages: [NFL]`) | Wagerhouse posts college openers; we read them hourly |
| Props model | **Lacks** (parity: planned, waits on Pinnacle college props) | CFBD player stats yes; no prop-line history |
| Teasers | Tested and failed (71.1% legs, research 14) | |
| Tested additions (schedule adjustment, outlier weight, injury clusters, referees) | **Lacks**: one specification, one test (research 16) | |
| Money state | Shown only; news picks staked (decision 0029). NFL is staked by choice on an equally failed test (decision 0019) | |
| Agent guide | Has (`ops/agent_prompt_college.md`) | |
| QB value in the shared agent prompt and the parity note | **Stale**: says 3.5 (P4 3, G5 4); research 22 says about 4, about 5 for a weak passer | |

**What college has that the NFL doesn't:** a measured QB value larger than the NFL's, and Friday and Saturday fast reads.

## 2. How college is handicapped well, and where it differs for a reason

RESEARCH_PLACEHOLDER

## 3. What I tested and what it showed

The rules were written and committed before any test ran (commit d9d268b, the section "Pre-registered tests" below). Code:
`src/engine/models/college_review.py` (test only, used by nothing live). Same method as research 16: fit on earlier seasons, the blend weight
fitted one season back, test seasons 2023 to 2026, 4,324 games. Bets at the closing number at -110, break-even 52.4%. The baseline is
research 16's model rerun in the same code (it reproduces research 16's numbers).

**Squared error against the close, pooled 2023-2026 (lower is better; the market is the bar):**

| Market | Market | Baseline blend | T1 blend (efficiency + tempo) | T1 own number alone |
|---|---|---|---|---|
| Team points | 120.64 | 120.67 | 120.73 | 133.75 (baseline 134.61) |
| Game total | 252.25 | 252.20 | 252.36 | 262.34 (baseline 263.19) |
| Side | 230.31 | 230.42 | 230.45 | 272.65 (baseline 275.24) |

**Bets at the close where our number disagrees (team 3.5+, total 4+, side 3+):**

| Market | Baseline | T1 | T1 by season (2023 / 2024 / 2025 / 2026) |
|---|---|---|---|
| Team points | 1206-1250 (49.1%) | 1267-1217 (51.0%) | 341-335 / 363-299 / 306-334 / 257-249 |
| Game total | 600-574 (51.1%) | **621-555 (52.8%)** | 208-192 / 168-119 / 139-122 / 106-122 |
| Side | 1203-1186 (50.4%) | 1201-1145 (51.2%) | 264-283 / 337-285 / 321-328 / 279-249 |

Fitted weight on our number, T1, by test season (team / total / side): 2023 0.08/0.18/0.03, 2024 0.02/0.09/0, 2025 0.16/0.42/0.08,
2026 0/0.08/0.

**T1, efficiency and tempo: failed** in all three markets. Our own number got more accurate in every market (team points 134.6 to 133.7),
and game totals passed two of the three rules (weight above zero in all 4 seasons; 52.8% on 1,176 bets), but the blend did not beat the
close. 2026 totals went 106-122. Restricted to the games Wagerhouse actually posts (FBS against FBS, see T5), T1 totals were 382-356
(51.8%; one variant, not pre-registered).

**T2, garbage time: failed** (removing it helped in 2 of 4 seasons: 2023 and 2025). It barely matters once you use per-play numbers.

**T3, preseason priors: failed, and the failure is informative.** Weeks 1 to 4 only (1,960 games):

| Market | Market | T3 blend | T3 bets | Same model without priors |
|---|---|---|---|---|
| Team points | 118.56 | 118.75 | 950-1051 (47.5%) | 1142-1258 (47.6%) |
| Game total | 241.89 | 241.81 | 400-383 (51.1%) | 338-333 |
| Side | 232.37 | 232.46 | 695-753 (48.0%) | 768-808 (48.7%) |

2026 weeks 1-4 sides went 190-225. In the first month, a number built on last season and the summer's roster data **loses** to the close on
sides and team totals, with or without priors. Research 14 found the same thing with 60 public systems (their side covered 188-251 in weeks
1-4 since 2021). Two different models, same direction: in September the close knows roster churn that last season's numbers don't. Fading
those numbers would have won about 52 to 53%, which is barely above break-even and was found by looking. **It stays a 2027 forward test.**

**T4, the early number: failed, with a real signal.** Our number against the same book's opener, 2023-2026:

| | Bets at the opener | Line move toward us, open to close |
|---|---|---|
| Sides, 3+ | 801-775 (50.8%) | +0.29 points |
| Totals, 4+ | 378-363 (51.0%) | +0.40 points |

The move is not luck (with about 1,600 bets, +0.29 is several standard errors from zero): the market does move toward our number during
the week. But 0.3 to 0.4 points in college is about 1 point of win chance, and -110 needs 2.4. So: real, too small to bet alone.

**T5, where the close is weakest: one slice passed, and it can't be bet.** 18 slices; the pass rule was 54%+ on 200+ bets and 52.4%+ in
both halves. Only **game totals in games with an FCS team** passed (239-199, 54.6%; 135-109 then 104-90). About one false pass was expected
by luck, and those games are almost all FCS against FCS: since the engine started, Wagerhouse has posted 84 college games and Pinnacle 79,
every one FBS against FBS. Late-season team totals (558-457, 55.0%) and totals (293-246, 54.4%) failed the both-halves rule: strong in
2023-24, a coin flip in 2025-26. Group of 5 games were no softer than power games (G5 sides 265-246, totals 151-158).

**Descriptive:** college margins (8,406 games, 2021-2026) land on 3 9.8% of the time, 7 8.2%, 10 4.3%; NFL (2015-2026) 14.9%, 8.6%, 4.7%.
Only 3 is much flatter. College spreads move 1.35 points on average from open to close (39% move 1.5+, 13% move 3+); totals 1.56.

**Variants tried:** the five pre-registered tests; one model specification each; one ridge penalty; the fixed thresholds. Beyond the list:
the FBS-only totals count above (one variant) and a check of whether Wagerhouse posts FCS games.

## 4. Where college fell behind, ranked by expected value

POV_PLACEHOLDER

## 5. What I'd like you to decide

DECIDE_PLACEHOLDER

## Pre-registered tests (written before looking, Nov 24, commit d9d268b)

Data, all free CollegeFootballData (CFBD), pulled Nov 24 into `data.nosync/raw/cfbd_review/` (kept apart so the live model's cache is
unchanged): per-game advanced stats with garbage time removed and with it kept (2020-2026), last season's final SP+ ratings, returning
production, team talent composite. Games and closing lines: the same cached `cfbd_lines_2021..2026.json` and the same line choice as
research 16 (`college_script._line`).

Method common to every test, identical to research 16: models fitted on earlier seasons only; the weight our number earns against the
close is fitted one season back inside the training window and used on the test season; test seasons 2023, 2024, 2025, 2026; rows need two
games of current-season form unless the test says otherwise; bets at the closing number at -110 (break-even 52.4%) where our own number
disagrees with the close by a fixed amount: **team points 3.5+, game total 4+, side 3+**. The baseline is research 16's model (points
scored and allowed), rerun in the same code so the comparison is like for like.

**T1. Efficiency and tempo in place of points per game.** Add to research 16's six inputs, for the team and for its opponent (decayed
the same way, last season counting as 2 games): offensive and defensive PPA per play (CFBD's expected points added), success rate for and
against, plays per game run and faced, and one product term: offensive PPA per play times the expected plays (average of own plays run and
the opponent's plays faced). Garbage time removed. Pass in a market only if all three hold: (a) the blend's squared error is below the
market's, pooled over 2023-2026, by at least 0.2%; (b) the fitted weight is above zero in at least 3 of the 4 test seasons; (c) the bets
at the fixed disagreement win at least 52.4% pooled, on at least 300 bets.

**T2. Garbage time.** T1 run twice, garbage time removed and kept. "Remove it" passes if our own number's squared error on team points is
lower with it removed in at least 3 of the 4 test seasons. This is a model-quality test, not a betting claim.

**T3. Preseason priors (roster churn).** T1 plus, for the team and its opponent, four numbers known before the season: last season's
final SP+ offense and defense, this season's returning production (share of last season's PPA that returns) and this season's talent
composite. Each is multiplied by a fade `4 / (4 + current-season games)` so it matters early and fades out. Rows with fewer than two
games are allowed in this test (weeks 1 and 2 use last season's final form). Judged on **CFBD weeks 1 to 4 only**. Pass: the blend's
squared error below the market's on sides or totals in weeks 1-4, bets at the fixed thresholds at least 52.4% on at least 150 bets, and
2026 (the only season not already seen by research 14's week 1-4 slice, which used 2021-2025) not below 50%. Caveat written now: the
talent composite for a season is compiled in the summer and may include late roster moves; that is mild look-ahead and is noted with the
result.

**T4. The early number (openers).** Using the T1 model with garbage time removed (chosen now, whatever T1 shows), compare our number with
the opener from the same book whose close we use (CFBD `spreadOpen`, `overUnderOpen`; 2023-2026). Bet at the opener where we disagree
by 3+ on a side or 4+ on a total, graded against the result at the opening number. Pass: at least 52.4% on at least 200 bets, and the
line moved toward our side from open to close by at least 0.25 points on average. Our inputs use only games already played, so the only
look-ahead is news that broke between the open and kickoff (that would flatter the move, not hurt it) and a few openers posted before the
previous week's game was played.

**T5. Where the close is weakest (market tier).** The T1 bets at the close, split by: both teams Group of 5; at least one power-conference
team; an FCS opponent; CFBD week 1-4, 5-9, 10 and later. 18 slices (6 splits x 3 markets), so about one false pass is expected by luck.
A slice passes only at 54%+ on 200+ bets and 52.4%+ in both halves (2023-24 and 2025-26). A pass here makes a forward test, never a
staked lane on its own.

**Descriptive, no pass/fail:** how often college final margins land exactly on 3, 7 and 10 against the NFL; how far college lines move
from open to close.

Variants: one specification per test, one ridge penalty (50, as research 16), the thresholds above. Anything tried beyond this list is
reported as a variant with its count.

Implementation notes added after writing the rules, before running: a team missing from a preseason list (mostly FCS teams and new FBS
teams) gets that list's 10th-percentile value; the tier "fcs" means at least one team is FCS, which turned out to be mostly FCS against FCS.

**T6 (added after T1-T5 ran and after the source research came back, before looking at this question; Nov 24).** Arscott (Journal of
Sports Economics, 2023) reports that because a team cannot score below zero, the team scores implied by the spread and total are biased in
mismatches. Rule written now: FBS against FBS games, 2021-2026, closing spread 21 points or more. The underdog's implied points (total / 2
minus spread / 2) against its actual points. Bet: the underdog's team total Over at the implied number. Pass: 55%+ on 200+ bets and 52.4%+
in both 2021-23 and 2024-26. Reported alongside, no pass/fail: the favorite's team total Under on the same games, and the same counts at
14+ points. Caveat: Wagerhouse prices team totals itself, so a pass means "check Wagerhouse's posted team totals in mismatches", not a bet.
