# 0023: Script additions tested; schedule adjustment kept (2026-11-23)

Kylor: "build the rest."

- **On:** schedule-adjusted form in the NFL game script (`script.ADJUST = True`). It lowered held-out totals error and kept the totals weight
  above zero in 2024-2026 (research 17). The live picks use it from the next read.
- **Built, tested, off:** outlier half weight, injury clusters by unit, referee total history (script); blitz and stacked-box splits for props
  (`props_matchup.py`). Each is switched by its test result, not by hand.
- **Not built:** coverage-type (man/zone) splits. The free data has them for 2023 only, so they cannot be tested or used live.
- **For Kylor's attention (no change made):** the evidence now points to NFL totals as the one full-game market with a measured lead, yet the
  playbook still weights sides and totals by its starting weights and stakes all of them. A fresh evaluation should decide whether to tilt
  stakes toward totals (handoff `docs/handoffs/2026-11-23-model-evaluation.md`).
