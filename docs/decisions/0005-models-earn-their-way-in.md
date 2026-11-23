# 0005: Models earn their way into the fair line one market at a time

Date: 2026-11-22. Follows the handoff `docs/handoffs/2026-11-22-model-first-picks.md`.

**Decision.**
- Full-game sides: the old model leg stays off (`picks.use_model_leg: false`). Test A (`docs/research/04-evaluation.md`, 2,663 games) found it adds nothing over the closing spread, and nothing since has changed that.
- Models go where they win. Each candidate model is tested walk-forward (fit on earlier seasons only, test on later seasons it never saw) against the market. One that passes moves the fair line in code, under `models:` in `config.yaml`, with its own cap on status. One that fails gets weight 0 and a note in `docs/research/`.
- **Wind totals model: in, capped at Conditional.** Unders it picked on 2019-2026 seasons it never saw went 320-220 (59.3%, +70.9 units at -110). Since 2024 it is weaker: 74-62, and 94-76 using the day-before forecast instead of the actual weather; at full size it made squared error worse on 2024-2026. So it runs at half its fitted size and can produce a Conditional (half a unit), never a Bet. Revisit after the 2026 season or after 30 graded wind picks.
- **First-half habit model: out (weight 0).** 2,111 held-out games: a team's first-half scoring habit adds almost nothing beyond the first-half number implied by the full-game line.
- **Early-number opener model: out (2026-11-23).** Ratings from earlier closes or scores do not predict where the opener goes. Held out: college 2023-2026 (about 3,100 games) and NFL 2024-2025 (477 games), at 49-51% against the final score at the opener. `docs/research/09-early-number-openers.md`.
- Code now does the with-and-without check for model-driven totals: a side is marked `model: wind` only when the bet exists because of the wind model, and the card refuses a Bet on it.

**Why.** Kylor wants a pick that comes from the engine's own model. The locked rule is that a model drives picks only after it beats the market on held-out seasons. Wind is the only candidate so far that does.

**What changes for the agent.** Wind is computed in code from Open-Meteo, so the agent no longer enters wind in `adjustments.yaml` (that would count it twice). A side flagged by the wind model is issued as a Conditional unless something sourced kills it.
