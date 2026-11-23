# 0011: Props are scored against Pinnacle only; the model's disagreements are tracked as paper suggestions (2026-11-23)

**No Wagerhouse prop lines (Kylor chose option C).** Wagerhouse's "NFL Player Props" section is thin for upcoming games; the real prop prices live in its Bet Builder tab, which is a third-party page loaded in an iframe through `getBetBuilderURL` and signed in with the account login. Reading it would add an operation to the read-only list, leave an activity-log entry on the account and send the login to a vendor we do not know, for a lane that cannot issue a pick yet. So props stay compared with Pinnacle only. Revisit with manual Bet Builder screenshots (option B) when a props model is close to passing its gate.

**Paper suggestions.** Kylor: "i dont have to actually bet them, but we should start tracking these to continue to tune the model."
- Every read, each disagreement of 5% or more between the props model and Pinnacle's price, for a game not yet started, is frozen the first time it appears in `prop_paper_picks` (line, price, model chance, market chance, model version). It is never updated.
- Graded after the game at the first-seen price, one flat unit each, pushes void. Shown on the props cards (`docs/cards/<date>-<sport>-props.md`, refreshed every hourly read) and on the lane status line.
- They are not Bets and are never alerted. They cannot be bet at Wagerhouse numbers because none are stored; the price is Pinnacle's.

**Tuning rule.** `props_version` fingerprints the props code (`props.py`, `nba_props.py`, `props_news.py`) plus `models.props` in `config.yaml`. Editing either starts a new version: the paper record and the 300-prop gate count only props priced by the current version, so a tuned model is not judged on its earlier self's predictions. Any edit to those files counts, including a non-model one. Props priced before stamping existed (Nov 22 to 23) were assigned to the first version, since those files had not changed since they were written.

**Watch:** on the first run the NBA model's paper suggestions were 98 Unders to 25 Overs. A one-sided lean is a bias to investigate before it is an edge (`docs/research/10-plan.md`, Test 3).
