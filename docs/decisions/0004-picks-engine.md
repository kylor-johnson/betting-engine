# 0004: The product is a picks agent; code owns the numbers

Date: 2026-11-21. Decided by Kylor after reading `docs/research/01-picks-engine.md`.

**Decision.** The engine's job is to research on a schedule and alert Kylor when there is a bet to place. Tracking exists to grade the engine. Design: code builds every number (the slate sheet); a scheduled Claude run does the research and sets Bet, Conditional or Pass with reasons; the card renderer refuses a Bet the numbers do not support.

**Kylor's answers.**
- Agent runs on his Claude plan from the Mac: yes.
- Sizing: 1 unit per Bet, 0.5 per Conditional, until 100 engine picks are graded.
- Betting splits: logged and shown, never a reason.
- CollegeFootballData free key: provided, stored in `.env`.
- Reads of his book: hourly, 7am to 5pm Mountain (when news breaks), later on Sundays for openers.

**His standard for it.** Not "the line dropped from +10 to +6.5, so someone is probably out" but being the one who holds +10. That makes early numbers and fast news the priority, ahead of more model detail.

**Why code owns the numbers.** Today's hand-built card listed K-State +7.5 when the market and his book had +10, and issued every pick at the closing number. An agent that can type a line can repeat that.

**Known limits, accepted.** Version 1's model is slow market ratings plus public systems, so most gaps it flags are news the market already priced; the agent's first job is to explain each gap, and most slates will be all Pass. Totals have no real model yet. College injuries are not machine-readable outside the big conferences.
