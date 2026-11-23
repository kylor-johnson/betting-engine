# 16. NBA and college game scripts, the props lead effect, and the NBA Under lean (Nov 23, 2026)

Same method as research 15: points models fitted on earlier seasons only; the weight our number earns against the market is fitted one season
back inside the training window and used on the test season. Bets are at the closing number where our own number disagrees.

## NBA: pace and points per possession (`src/engine/models/nba_script.py`)

Per team, decayed averages from earlier box scores: possessions (FGA + 0.44 FTA + turnovers), points per possession, the same allowed, the
opponent's, home, and both teams' second-night-of-a-back-to-back. Test seasons 2025-26 and 2026-27 (2,872 team-games, 1,431 games).

| Market | Squared error: market | Our number alone | Blend | Bets where we disagree (2+/3+/4+ for totals and sides) |
|---|---|---|---|---|
| Team points | 131.66 | 145.77 | 131.66 | 1.5+: 909-935; 3.5+: 447-428 |
| Game total | 328.90 | 360.47 | 328.90 | 500-518; 401-421; 314-344 |
| Side | 198.15 | 223.37 | 198.15 | 441-479; 346-355; 253-272 |

Fitted weight on our number: 0 in both test seasons, every market. **Decision: NBA full-game picks are shown, not staked** (config
`playbook.sports.NBA.full_game: show`). They are below a coin flip where they disagree most.

## College: points scored and allowed (`src/engine/models/college_script.py`)

Free CollegeFootballData only (no play-level data): decayed points for and against, the opponents' form, home and neutral. Test seasons
2023-2026 (8,932 team-games, 4,324 games).

| Market | Squared error: market | Our number alone | Blend | Bets where we disagree |
|---|---|---|---|---|
| Team points | 120.50 | 134.98 | 120.49 | 1.5+: 2843-2813; 3.5+: 1295-1326 |
| Game total | 252.25 | 263.18 | 252.20 | 2+: 1265-1213; 3+: 874-851; 4+: 605-576 (51.2%) |
| Side | 230.31 | 275.21 | 230.43 | 1493-1458; 1211-1184; 931-927 |

Fitted weights: team 0.02 to 0.09, side 0 to 0.06, **game total 0.10 to 0.28 in every test season**. The totals weight is the one consistent
sign of anything in this whole series; its bets (51.2% at 4+) still do not clear -110. **Decision: college full-game picks are shown, not
staked**, and the totals weight is a lead to watch on graded candidates.

## Props: game script by lead (`src/engine/models/props_script.py`)

For each NFL stat, projection x exp(b x expected margin), b fitted on 2019-2022, kept only where it lowers held-out (2023-2026) squared error by
0.1% or more. Kept: carries (b +0.0029 per point: favorites' backs get about 0.3% more per point of spread), pass attempts (-0.0015) and
receiving yards (-0.0011). Dropped: the other eight stats. The effect is small because the props model's team-points scaling already carries
most of it. Live, the expected margin is our blended margin from the game script.

## The NBA props model's Under lean

The props model leans Under on most NBA stats. Graded so far (one row per prop, Pinnacle prices): at a 5%+ disagreement, Unders 71-57 (+0.7
units), Overs 14-9 (+4.5). Under the playbook rule (blend at 0.5, 4%+ edge): Unders 15-10, Overs 1-1. Small samples, not losing; watched on
the per-principle record (`engine playbook-record`), not blocked.

## Variants tried

NBA and college: one specification each, one penalty setting, three thresholds per market. Props lead: one term per stat, eleven stats.
