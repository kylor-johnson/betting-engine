# 24. Full audit (Nov 24, 2026): pre-registered tests, written before running any of them

This commit holds only the Job 3 tests from `docs/handoffs/2026-11-24-full-system-audit.md`. The full audit note replaces this page in the
next commit, with the results under each test. Nothing below has been run on the data it names. Sources for every outside claim are in
`24a-sources.md` (next commit). Free data only. Bets at -110 unless a price is given; pushes are dropped.

**Multiple testing.** There are six tests. The four run on history now; two are forward tests that only start. Research 24a (NFL leg,
Vandenbruaene et al. 2022: more than 600 published betting strategies, none survives a correction for testing many ideas) recommends a
z-score of 3 or more for a new idea. Each test below states its bar. A replication of something already found elsewhere gets a z of 2;
a new idea needs both 52.4% and the season-by-season condition.

**What was already looked at, so it cannot be a test here.** The research agents graded these on their own before this was written, so
they are findings, not tests: Prediction Tracker NBA systems 2021-22 to 2025-26 (BPI 53.8% against the opener); college systems against
the opener by era 2010-2026; NFL totals trends (high totals, primetime, Thursday, Week 1); college home field and totals at the close.
Test N1 below uses NBA seasons that agent did not open.

## Test F1 (NFL). Do public ratings predict the move from opener to close?

- **Idea** (24a NFL leg, test 3; research 03 "early in the week"): where the ratings disagree with the opener, the line moves their way, and
  the opener is beatable.
- **Data:** The Prediction Tracker's free files `nfl23.csv`, `nfl24.csv`, `nfl25.csv` (2023, 2024, 2025 seasons): `lineopen`, `line`
  (updated, close to the close), `lineavg` (the average of every system) and the scores. Sign convention: fixed before grading by which
  sign of `line` agrees with the home margin across all games.
- **Rule:** where `lineavg` differs from `lineopen` by 1.5 points or more, bet the side `lineavg` favours at `lineopen`. Graded against the
  result at `lineopen`. Also: did `line` move from `lineopen` toward `lineavg`?
- **Bar:** 150+ bets pooled; 52.4% or better against the opener; no season under 50%; and the line moved toward the ratings in more than
  55% of the games where it moved, with z of 3 or more. ESPN's FPI (`lineespn`) is reported beside it, not judged.
- **If it passes:** a paper lane for early-week NFL numbers at Wagerhouse in the direction of public ratings (Sunday night and Monday), graded
  on closing-line value against Pinnacle. **If it fails:** public ratings are priced into the opener; no early-week ratings work.

## Test N1 (NBA). A rating that knows who plays, against the opener, on seasons nobody here has looked at

- **Idea** (24a NBA leg): ESPN BPI, which adjusts for who is playing, went 53.8% against the opener on 3,697 games in 2021-22 to 2025-26
  but 50.6% against the close. If that holds on other seasons, the value is in pricing who plays before the opener does.
- **Data:** The Prediction Tracker's free `nba18.csv`, `nba19.csv`, `nba20.csv` (2018-19, 2019-20, 2020-21), the only earlier files with a
  BPI column (`lineespn`). Columns `lineopen`, `line`, scores. Sign fixed as in F1.
- **Rule:** where `lineespn` differs from `lineopen` by 1.5 points or more, bet BPI's side at `lineopen`; also grade the same bet at `line`.
- **Bar (a replication):** 150+ bets; 52.4% or better at the opener with z of 2 or more against 50%; no season under 50%.
- **If it passes:** the forward half (the timing check) is worth building on paper: our NBA number with the official report's Outs, against
  Wagerhouse's first number, timestamped, graded on closing-line value. **If it fails:** the 53.8% was a feature of those five seasons or
  of when the site captures its numbers, and the NBA opener idea is closed.
- **Known weakness, stated now:** the site does not say when it captures BPI or the opener. A pass cannot rule out that BPI was captured
  after news the opener did not have; that is why a pass only opens a forward test.

## Test C1 (college). Small-conference games under-react to a big miss (Bennett 2021, out of sample)

- **Idea:** Bennett (Applied Economics Letters 2021, 2006-2018): after a big miss against the spread, backing the team that beat it wins
  54.2% when both teams are outside the Power 5. Never tested on games after 2018.
- **Data:** CollegeFootballData lines files cached in `data.nosync/raw/cfbd/` (2021 to 2026, regular season), with scores and conferences;
  the line is the first of Bovada, consensus, DraftKings, ESPN Bet, William Hill (the engine's own order, `college_script._line`).
- **Rule:** a team's miss = its margin plus its own closing spread in its previous FBS game this season. Back a team whose last miss was
  +14 or more; fade (bet against) a team whose last miss was -14 or worse. Only games where both teams are FBS and outside the power
  conferences (power = SEC, Big Ten, Big 12, ACC, plus the Pac-12 through 2023, plus Notre Dame). If the two teams' signals point to the same
  side, one bet; if they cancel, no bet. Bet at the closing spread.
- **Bar:** 150+ bets in 2021-2026; 52.4% or better; 50% or better in both 2021-2023 and 2024-2026. The same rule on games between two power
  teams is printed as a control, not judged.
- **If it passes:** a paper lane for small-conference sides for the rest of 2026 and 2027, kill at 52.4% after 150 graded. **If it fails:**
  small-conference "the market is slow" ideas are closed for college sides.

## Test C2 (college). Last season's top teams early in the season, faded at the close

- **Idea** (Bennett 2019, research 14 2c, 23 T3): the market overrates last season's best teams in September, more so since the portal.
- **Data:** the same lines files; last season's final SP+ from `data.nosync/raw/cfbd_review/sp_<year-1>.json` (2020 to 2025).
- **Rule:** in weeks 1 to 4, bet against every team in last season's SP+ top 25 when it plays an FBS team that is not also in it, at the
  close.
- **Bar:** 150+ bets in 2021-2026; 52.4% or better; 2026 not under 50%.
- **If it passes:** a second input to the 2027 early-season paper test already written in research 23. **If it fails:** September is about
  specific rosters, not reputation; the 2027 test stays as written.

## Test L1 (all three sports, forward). Does Wagerhouse trail Pinnacle long enough to bet?

- **Idea** (research 12, 14; 24a all three legs): the one edge every outside source agrees a small bettor can keep is a soft book slow to
  follow the sharp one.
- **Data:** our own Wagerhouse and Pinnacle reads (hourly, plus the fast reads), from Nov 25, 2026.
- **Rule:** a paper pick, frozen at Wagerhouse's number, whenever Wagerhouse's full-game spread or total is 1 point or more better for one
  side than Pinnacle's current number (0.5 on the NFL's 3 and 7). Graded on Pinnacle's closing line, as win chance after Wagerhouse's price.
- **Bar:** 150+ paper picks per sport; average closing-line value above zero with the 95% range above zero. Report how many minutes
  Wagerhouse took to follow.
- **If it passes:** Kylor decides whether it becomes a staked lane; the charter's "a price gap alone is never a reason" would need his
  change. **If it fails:** Wagerhouse keeps up, and every lane has to beat Pinnacle on the handicap alone.
- **Not built in this session** (it is a new paper lane; Kylor's yes first). `engine wh-edge` and the stale-number log already measure the
  price gap; this test is that log graded with a rule fixed in advance.

## Test D1 (NFL, forward). Our script's halves and team totals against Pinnacle's derivative lines (Job 4's paper lane)

- **Idea** (Sharp's computer totals; 24a NFL leg, PFF on first-half pricing): derivative lines are set from the full-game line by a rule of
  thumb, so a full-game model's own split may find edges the full-game line does not show.
- **Rule, frozen now:** our first-half total = 1.89 + 0.47 × our full-game total; our first-half margin = 0.48 + 0.62 × our full-game margin
  (research 04, test E); our team totals = the script's blended team points. A paper pick where our number beats Pinnacle's derivative line by
  4% of win chance (the playbook's bar for halves), frozen at Pinnacle's price, graded on Pinnacle's last read before kickoff.
- **Bar:** 150 picks; average closing-line value above zero with the 95% range above zero.
- **Expected:** a null, because it re-tests the full-game script, which earns no weight against the market (research 15, 18). Stated
  now so a null is not read as bad luck.
- **Not built in this session** (Kylor's yes first; see Job 4 in the full note).
