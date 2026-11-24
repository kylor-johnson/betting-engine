# 21. What a college starting quarterback is worth to the market (Nov 23, 2026)

**Answer: about 3.5 points.** When a college team's established starter does not start, the closing spread sits **3.7 points** worse for that
team than its market rating says (median 3.5; 1,078 team-games, 2021-2026, standard error 0.2). Power 4: 3.2. Group of 5: 4.2. The guide's old
range of 3 to 7 was too wide and too high.

**Only about 0.9 points of it moves after the opener.** Most college quarterback news is already in the number when lines open, and in games
where the starter played, open-to-close moves average zero. That is the measured size of the room a news pick has: it exists, it is small,
and it is gone the moment Pinnacle reacts. Speed matters more than the size estimate.

**Starter quality does not scale it up.** Split by the missing starter's yards per attempt in earlier games:

| Missing starter | Team-games | Market discount (points) |
|---|---|---|
| Low efficiency (under 6.6 yards an attempt) | 359 | 5.0 (se 0.4) |
| Middle (6.6 to 7.7) | 359 | 3.8 (se 0.4) |
| High (7.7 and up) | 360 | 2.3 (se 0.4) |

The opposite of the folklore. A likely reason: weak passing teams have the thinnest depth, so the drop to the backup is bigger, and good
passing offenses (system, receivers, line) keep more of their value with a backup. Do not add points for a "star" quarterback.

**Backup experience barely matters:** backups with fewer than 30 earlier attempts, 3.7; 30 or more, 3.8.

| Season | Team-games | Discount |
|---|---|---|
| 2021 | 178 | 4.95 |
| 2022 | 190 | 2.99 |
| 2023 | 193 | 4.08 |
| 2024 | 181 | 3.17 |
| 2025 | 173 | 3.26 |
| 2026 | 163 | 3.86 |

## Method

- Free CollegeFootballData: per-game passing by conference (11 FBS conferences and independents) and the cached closing and opening lines.
  `src/engine/models/college_qb.py`; output `data.nosync/models/college_qb_value.json`.
- Starter = the passer with the most attempts in the game. Established starter = most attempts in the team's earlier games this season,
  at least 60% of them, over at least 2 games. "Starter out" = someone else threw the most passes.
- Market ratings per season fitted on closing spreads of FBS games where both established starters started (ridge, home edge). The
  discount is how far the closing spread sits from those ratings in starter-out games, minus the same residual's average when the starter
  played. Games where both teams' starters were out are left out.
- Limits: descriptive, not a betting test (it uses the whole season's ratings). "Did not throw the most passes" includes injuries during a
  game, benchings and planned rotations, which dilutes the true pre-game news effect; a pre-announced absence is probably worth a little
  more than 3.7. It measures the market's price, which is what an `adjustments.yaml` entry has to match.

## What changes

- **College agent guide:** a starter out is about 3.5 points (Power 4 about 3, Group of 5 about 4); above 5 needs a specific written reason;
  no extra points for a star. `priced_in` uses this number instead of a range.
- **Parity table:** college "player value measured" goes from planned to live.


## Correction (research 22, Nov 24)

"Starter out" here is whoever threw the most passes, so it mixes true pre-game absences with in-game injuries and benchings the market could not know. Split by whether the usual starter threw at all: no passes (a pre-game absence), 811 games, 4.1 points; some passes but not the most, 267 games, 2.4 points. The value for a starter ruled out before the game is about 4, not 3.5. A weak-passing starter's absence was worth about 5 (5.3 when he sat from the start), so 5 is not a ceiling. About 1 point (not 0.9) moves after the opener, measured on a retail opener, not Pinnacle's. Decision 0033 uses these numbers.
