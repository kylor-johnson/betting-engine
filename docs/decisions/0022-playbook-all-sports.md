# 0022: The playbook covers NFL, NBA and college; full units from now (2026-11-23)

Kylor: "units are $50 for nfl and $25 for nba starting now. build the rest of this, BE ELITE."

- **One playbook engine for all three sports** (`src/engine/picks/playbook.py`, config `playbook.sports`). Each sport has its own game-script
  model (NFL `script.py`, NBA `nba_script.py`, college `college_script.py`), its own CHECK thresholds, its own caps (NFL and college per week,
  NBA per day) and its own card (`docs/cards/<date>-<sport>-playbook.md`) and checks file for the research agent.
- **What is staked:** NFL full-game picks (Kylor's choice, decision 0019), NFL props and NBA props (B picks). **Shown only:** NBA and college
  full-game picks, because their walk-forward tests lost outright (research 16); switching one on is `full_game: stake` in config, Kylor's call.
- **Props get the game script twice:** team points (since decision 0021) and now the expected margin (leaders run more, trailers throw more),
  used only for the three stats where it passed a held-out test (research 16).
- **Every candidate is recorded** (`playbook_candidates`, A, B and C), graded hourly, and the weights are re-fitted from all of them, not just
  the issued picks. `engine playbook-record` writes `docs/lanes/PLAYBOOK-RECORD.md` (record by sport and market, fitted against current
  weights). A weight changes only after 40 graded candidates, by a session, with a decision note.
- **Stop-loss is per sport** (10 units). No half-size period (`half_size_weeks: 0`).
- **Fixed:** a prop pick on a game no longer blocks a side or total pick on the same game.
