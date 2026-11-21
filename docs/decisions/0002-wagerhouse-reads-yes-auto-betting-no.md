# 0002: The engine reads the Wagerhouse account; it does not place bets

Date: 2026-11-21.

**Decided by Kylor:** the engine may sign in to his Wagerhouse account on a schedule to read posted lines and bet history.

**Limits.** Read-only. A handful of reads a day in the hours lines open, paced like a person, never a constant poll. The login lives in `.env` and is never printed or logged. Wagerhouse is a credit account with an agent; the risk being managed is the book noticing automated sign-ins and cutting the account off.

**Raised by Kylor, not built:** letting the engine place bets itself when it sees a strong early lean while he is away.

**Why not now (Claude's recommendation, open to Kylor overruling).**
- Nothing has shown an edge yet. The season to date is about break-even, and the reference price is a market-following book. An automatic bettor acting on an unproven signal loses money without anyone watching.
- A bug or a bad data read places real bets on credit that cannot be undone.
- Automated betting is the fastest way to get an account closed.

**Revisit after** Phase 1B's exit test, if the measurements show a repeatable gap. If built then: a hard stake cap, a daily cap on number of bets, one specific rule at a time, and an alert for every bet placed.
