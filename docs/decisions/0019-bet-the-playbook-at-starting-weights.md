# 0019: Bet the playbook at its starting weights; teasers on real money (2026-11-23)

Kylor's answers after research 15 (the game-script model earned no weight against the market for 2024 to 2026):
"teasers: yes" / "bet them anyway at the playbook's starting weights" / props build: "sure".

- **NFL full-game playbook picks are live with real money** (`src/engine/picks/playbook.py`, config `playbook:`). Our team points come from the
  game-script model; our number gets the playbook's starting weights against the market (side 0.25, game total 0.35, team total 0.4), not the
  walk-forward weights (zero). A pick needs 3% more win chance than Wagerhouse's price needs. All are B picks (no principle has passed a test),
  0.5 unit, half size until Dec 15 ($6.25). One position per game, at most 5 a week, frozen at the Wagerhouse number, sent to Telegram, graded on
  result and against Pinnacle's close. `engine playbook --dry-run` shows the current list.
- **CHECK picks:** where the model's own number is 3+ points (side) or 4+ (totals) from the market, the pick is held until the research agent
  writes `clear` for it in `docs/cards/decisions/<date>-nfl-checks.yaml` (it looks for news the model cannot see). Cleared ones are issued as B.
- **Teasers on real money** (`teasers.real_money: true`): two open qualifying legs from different games form a 2-team 6-point ticket, an A pick,
  1 unit at half size ($12.50) until Dec 15, sent to Telegram.
- **Stop:** if playbook picks are down 10 units, stakes go to $0 (paper) until Kylor restarts them.
- **The honest note on record:** the walk-forward test says these full-game picks are close to a coin flip before the juice. Kylor chose to bet
  them to build a real record. The weights are re-fitted on graded picks every 4 weeks (PLAYBOOK step 4).
- **Next:** props wired to the game script (Kylor: "sure").
