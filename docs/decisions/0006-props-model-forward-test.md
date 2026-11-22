# 0006: The props model runs, but earns picks only by beating Pinnacle going forward

Date: 2026-11-22. Kylor asked for the player props model next.

**Decision.**
- The NFL props model (`src/engine/models/props.py`) prices every Pinnacle NFL prop on every hourly read and stores it in `prop_evals`, with Pinnacle's vig-free chance at that moment. Finished props are graded from nflverse stats; a player who did not play is void.
- No prop is a pick until all three hold (config `models.props`): at least 300 graded props; a blend of model and Pinnacle has lower error than Pinnacle alone (best weight on the model above 0); and the model's 5%+ disagreements with the posted price have won money. Then props may be Conditionals (half a unit), only when Wagerhouse's line is at or better than Pinnacle's.
- The props sheet (`docs/cards/<date>-nfl-props.md`) says "testing, not bets" at the top until then. Props are never sent by Telegram while testing.

**Why.** The locked rule says a model drives picks only after it beats the market out of sample. No free history of prop lines exists, so the held-out test can only show that the model is accurate and honest about its probabilities. It shows both (`docs/research/06-props-model.md`). Beating the market has to be shown from now on.
