# 0024: The tracker: model picks against Kylor's real wagers (2026-11-23)

Kylor: "let's start tracking these bets... use the telegram recommendations, compared with my actual wagers (starting from today), so i can
see how this model is doing and also as a grader."

- `src/engine/bets/tracker.py`, `engine tracker`, output `docs/lanes/TRACKER.md` (auto-committed), a section on the board, and a 9am
  Telegram recap (`telegram.send_kinds` now includes `recap`).
- **Model record:** every staked recommendation since Nov 23 (playbook picks and teaser tickets) at the number and stake sent.
- **Kylor's record:** every wager accepted since Nov 23, from the account's own grading, split into bets that follow a pick and his own bets.
- **Grader:** each pick is matched to his wagers on the same game, market and side (props by player, stat and over/under; teasers by both
  legs) and graded: not bet, or bet at the same / a better / a worse number, price against the price sent, stake against the stake sent.
- **Limit found:** the site's history report does not return open bets (asking for ungraded wagers returns graded ones), so a bet appears once
  it is graded. The history is synced on the first read after 8am and after 5pm.
