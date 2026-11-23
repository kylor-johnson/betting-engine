# 0013: STALE NUMBER alerts (2026-11-23)

Kylor: "the line is at 47.5, bet it before it moves to 48.5... this model seems useless and only geared on injury news or weather." The engine already compared Wagerhouse with Pinnacle on every game but only messaged for Bets, and the agent passes a price gap with no reason (locked rule). This adds a separate, honest alert type.

**What fires.** On each hourly read and each fast read, for NFL and NBA full-game sides and totals: Wagerhouse's number and price against Pinnacle's no-vig fair price, priced with how real games land (3 and 7 matter), at the engine's own 2% bar (`picks.min_value`). Message: "STALE NUMBER (a price alert, NOT a pick)", with the Wagerhouse number, Pinnacle's, the value, and a "don't bet past" number.

**What it is not.** Not a Bet. No reason is known; the research agent has not looked at it. It does not change the locked rule that a price gap alone is never a reason for a pick, and it is never staked by the engine or counted in the Bets record. A gap over 3 points is treated as a data mismatch.

**Limits.** One alert per game, market, side and Wagerhouse number; 10 a day; College not covered. Telegram kind `stale` (`telegram.send_kinds`); remove it from the list to silence them.

**Tracking.** Each alert is frozen in `stale_alerts` and graded on the result and against Pinnacle's last line before kickoff (`stale_grades`). `engine stale` prints the record. Not part of the go/no-go criteria (0012) until it has a record; the aim is to find out whether stale numbers beat the close.
