# 0010: Leans are paper-only; Telegram pings only for bets (2026-11-23)

Kylor's words: "leans paper-only" and "it should only ping me when it has a bet for me to place".

**Leans.** `src/engine/picks/leans.py`. Code stamps the Wagerhouse number, price and "don't bet past" number; the agent writes side, reason type, a handicap of 25+ words and a source. One of three reasons: news (needs `news_at` and a stored Pinnacle line from before it; refused if Pinnacle already moved 0.5 toward the side), forecast (needs `forecast_line`), weather (totals only). Splits, line movement, sharp money and price gaps are refused. Max 3 per lane per week. Fixed once issued. Graded in `lean_grades`. Gate to bet: 50 graded and average closing-line value above zero (`leans.promote_after_graded`). `engine lean` lists them; `engine lean --bet KEY` records one you bet.

**Telegram.** `telegram.send_kinds: [bet, system]`. Held back, not deleted: NO BETS summaries, opener heads-ups, QB and NBA news, off-market gaps, watchlist hits, props, the lane table, graded picks, paper Leans. Still pings: BET NOW, WAIT/ONLY IF, HOLD OFF, CANCELLED, a failed read, a missed research slot, a failed research run. Add `info` to the list to get everything again.

**Not switched off:** the news and opener detection still run and still start research runs; only the message is held.
