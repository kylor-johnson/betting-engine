# Betting readiness (generated; do not edit)

**Stage 0: observe, no money.**

Settings last changed Nov 23, 2026 UTC; 1 rule version(s) recorded in all. Engine picks since then: 0 graded, +0.00 units (a result is not evidence; the closing-line value is).

| Criterion | Have | Need | Met |
|---|---|---|---|
| Weeks since the rules were frozen | 0.0 | 3 | no |
| Graded Bets and Conditionals | 0 | 10 | no |
| Of those with a closing line | 0 | 5 | no |
| Average closing-line value (points) | n/a | >= +0.0 | no |
| Every pick has a don't-bet-past number | 0 missing | 0 missing | yes |
| Finished picks all graded | 0 ungraded | 0 ungraded | yes |
| Graded picks for the full unit | 0 | 100 | no |
| Average closing-line value above | n/a | > +0.0 | no |

## What each stage allows

- **Stage 0:** no money. Everything is logged and graded.
- **Stage 1:** $12.5 on a Bet (status Bet only), at the Wagerhouse number or better than its "don't bet past", re-checked just before you place it. At most 2 units staked per week across all picks. Log it with `engine bet add`.
- **Stage 2:** the full $25 unit; the sizing review the spec already requires after 100 graded.
- **Never bet at any stage:** Conditionals, wind totals, paper Leans (until 50 are graded with average closing-line value above zero), props (until a model passes its gate), anything past the "don't bet past" number, anything in the first few minutes after a change of rule version.

## Pause rules (back to Stage 0)

- Average closing-line value below -0.5 points once 25 picks have a closing line.
- Down 10 units from the start of Stage 1 (bankroll protection, not evidence).
- Any pick bet past its limit, or a pick with no limit.
- A change to the settings that decide picks (`picks`, `models`, `leans`, `margin_sd`, `sports` in `config.yaml`): the clock and the graded count start again from that change. A code-only change is recorded as a new rule version but does not restart the clock; Kylor decides whether it should.
