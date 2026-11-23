# 0021: Playbook props, NFL (2026-11-23)

Kylor: "yes build it" (props wired to the game script, PLAYBOOK step 3 item 1).

- Every hourly read, each Pinnacle NFL prop the props model prices is re-scaled to our blended team points (the game script, team-total
  weight 0.4) with the power the props model fitted per stat, re-priced on its own outcome distribution, and blended with Pinnacle's no-vig
  chance at the playbook prop weight (0.5). A prop pick needs 4% more win chance than Pinnacle's price needs; 15+ points of disagreement
  between the model and Pinnacle is CHECK (held until the research agent clears it in the checks file).
- B picks (0.5 unit; NFL $12.50 until Dec 15), at most 2 per game and 10 per week, one side per player and stat, frozen and sent to Telegram.
  Prices are Pinnacle's because Wagerhouse props are not readable (decision 0011): each message says the worst Wagerhouse line and price at
  which it is still a bet, to check in Bet Builder.
- Graded from nflverse stats (the props model's grading), result only; no closing price is stored for props.
- Not yet in: plays and pass rate from the script (only team points so far), coverage-type splits, NBA props in the playbook.
- The props forward test (decision 0006) keeps running unchanged on the props model itself.
