# 0001: No paid odds feed

Date: 2026-11-21. Decided by Kylor.

**Decision.** Use only free data: Wagerhouse lines and history from Kylor's own account, ESPN's public scoreboard and odds pages (DraftKings open, close, current), and The Odds API free tier (500 credits a month) for occasional Pinnacle checks.

**Why.** At $25 units a realistic edge is a few hundred dollars a year; a $30 to $59 feed would eat most of it. ESPN was tested on 2026-11-21 and returns opening and closing spread, total and moneyline for finished and upcoming NFL, college football and NBA games.

**Cost of the decision.** DraftKings follows the market and is not a sharp book, so "fair price" is rougher than it would be against Pinnacle. ESPN's pages are public but undocumented and can change without notice; the fetcher must fail loudly when a field goes missing.

**Revisit when** stakes or volume grow enough that a sharp reference would pay for itself.
