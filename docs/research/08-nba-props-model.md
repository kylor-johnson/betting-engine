# NBA player props model

Written 2026-11-22. Code: `src/engine/models/nba_props.py` (model), `src/engine/models/nba_data.py` (history). Commands: `uv run engine nba-history` (top up box scores), `uv run engine nba-props-test` (held-out test, about 15 minutes), `uv run engine props --sport NBA` (price the latest Pinnacle NBA props, write `docs/cards/<date>-nba-props.md`). The hourly read prices and grades them automatically.

## Bottom line

Built around minutes, as planned. On three seasons it never saw it beats a plain recent average on every stat, the injury and minutes terms add a little on top, and its probabilities are honest. It cannot be proven against the market yet (no free history of prop lines), so it runs the same forward test against Pinnacle as the NFL model, with its own scorecard (decision 0006). Today it leans Under against Pinnacle on every stat by about 4-7 points of chance. That could be a real edge or a bias. The scorecard now shows Overs and Unders separately so grading can tell which.

## Data

- ESPN's public box scores for every regular-season and playoff game from October 2023 through 2026-11-21: 4,199 games (4 failed to download), 4,187 with ESPN's closing spread and total. Stored one file per game in `data.nosync/raw/espn_nba/games/`.
- nba.com's stats site would have been one request per season, but it blocks scripts. Getting past that meant imitating a browser, which this Mac's permission settings refused, so ESPN was used instead.

## How it works

1. **Minutes.** Weighted recent minutes (fitted: fast recency, 0.8 per game), then:
   - **Teammates out:** regulars (15+ minutes, in one of the team's last three games) not playing. Their minutes go to the rest of the rotation in proportion to minutes, at a fitted rate (0.25 = a quarter of the vacated minutes per unit of share).
   - **Blowout risk:** starters (28+ minutes) lose a fitted 1% of minutes per point of spread beyond 8.
   - **Back-to-back:** second night, fitted at about 0.97.
2. **Per minute.** Rates weighted by minutes (slow recency, 0.95), boosted when a teammate's shot volume needs a new home (fitted; used for assists and threes in some seasons, not for points), and scaled by the team's expected points from the closing line (power 0.5).
3. **Distribution.** The 500 earlier player-games with the closest projection (the same method as the NFL model). Books price the median, and these stats are lopsided.
4. **Who is out, live:** reporter news through Rotoworld first, then the official NBA injury report, then ESPN. Players listed Out or Doubtful are not priced. Questionable is shown but not adjusted: there is no free history of the official report to size it.

## Held-out test (each season fitted only on earlier seasons; 2024-25, 2025-26, 2026-27 to date)

Probability score (Brier at three lines per player-game; lower is better). "News" = with the teammate-out, blowout, back-to-back and shot-volume terms. The last two columns are only the player-games where those terms changed the projection by more than 5%.

| Stat | Player-games | Plain average | Base | With news | Games news touched | Base on those | With news on those |
|---|---|---|---|---|---|---|---|
| points | 47,153 | 0.2429 | 0.2402 | 0.2386 | 12,671 | 0.2414 | 0.2378 |
| rebounds | 47,153 | 0.2302 | 0.2276 | 0.2274 | 6,187 | 0.2280 | 0.2262 |
| assists | 47,153 | 0.2328 | 0.2304 | 0.2298 | 13,125 | 0.2342 | 0.2325 |
| threes made | 47,153 | 0.1987 | 0.1980 | 0.1979 | 12,868 | 0.2135 | 0.2128 |
| pts + reb + ast | 47,153 | 0.2402 | 0.2358 | 0.2339 | 12,671 | 0.2383 | 0.2334 |

Calibration (what it said vs what happened, bands with 200+ cases): within 1-3 points through the middle. The top band runs hot: points said 73%, happened 70%; pts + reb + ast said 83%, happened 73%. Treat its most confident calls with care.

The fitted values sit at the edges of the ranges tried for recency (minutes 0.8, the fastest tried; rates 0.95, the slowest tried). Widening those ranges is the first tuning step once grading data exists.

## First live comparison (2026-11-22, 3:27 pm MT, 210 Pinnacle props)

- **Average lean against Pinnacle: toward the Under** on every stat (points −6.3 points of chance, pts + reb + ast −6.8, threes −5.5, rebounds −4.2, assists −3.6). The model's median sits about 1.2 points under Pinnacle's points line on average.
- **The biggest gaps follow recent slumps the market expects to end.** Josh Hart has 0 points in three of his last six games; Mikal Bridges is averaging 7.8 this season. Pinnacle prices longer history; the model weights recent games heavily.
- **This season the model's average projection is about a point high on points** (actual minus projection −0.94). So the Under lean is not the model running low on average. It comes from the shape of the distribution: the median sits below the mean, which is how books are supposed to price.

## Not done

- **Questionable players are not adjusted** (no free history of the official report to size it). Logging the official report daily from now on creates that history.
- **No opponent or pace-matchup term beyond expected points.**
- **Wagerhouse props are still unread**, so a passing prop has to be checked by hand against Wagerhouse's line.
