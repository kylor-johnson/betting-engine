# 13. NBA: does the closing spread already carry who is missing?

Generated 2026-11-23. 4194 games with a closing spread (seasons [2024, 2025, 2026, 2027]). Method and its main limit are in `src/engine/models/nba_absences.py`: absences come from the final box score, so they include scratches made after the close.

## Result

- Across all games, each extra 10 minutes of regulars missing from one side moved the result **+0.10 points** against that side relative to the closing spread (standard error 0.05, t = +2.0).
- When one side was missing a 28+ minute player and the other was not (2038 games), the healthier side beat the close by -0.02 points on average.

| Test season | Games | Slope fitted on earlier seasons | Error vs the close | Error after adjusting | Games with 20+ minutes difference | Healthier side covered |
|---|---|---|---|---|---|---|
| 2025 | 1320 | +0.06 | 188.6 | 188.6 | 809 | 409 of 809 |
| 2026 | 1307 | +0.04 | 199.3 | 199.0 | 780 | 421 of 780 |
| 2027 | 248 | +0.11 | 198.7 | 199.2 | 163 | 65 of 163 |

## How to read it

- A slope near zero, and no improvement in error after adjusting, means the closing spread already carries absences: nothing to find at the close.
- A positive slope with a stable sign across seasons means the healthier side beats the close on average. That is partly late scratches (news after the close), which cannot be traded, and possibly under-pricing, which can. This test cannot split them.
- It says nothing about how fast Pinnacle moves when news breaks, or whether Wagerhouse trails it. That is measured from our own logs (`engine wh-edge`, the injury watcher), which began Nov 21; too few events exist yet.
