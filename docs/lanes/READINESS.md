# Betting readiness (generated; do not edit)

**NFL: Stage 0 · College: Stage 0 · NBA: Stage 0**

Settings last changed Nov 23, 2026 UTC; 1 rule version(s) recorded in all. Engine picks since then: 0 graded, +0.00 units (a result is not evidence; the closing-line value is).

Each sport is judged on its own picks and thresholds (`go_live.per_sport` in config.yaml). Closing-line value is win chance gained against Pinnacle's close: +2.0% means the number you got was worth two percentage points of win chance (src/engine/clv.py).

## NFL: Stage 0: observe, no money

| Criterion | Have | Need | Met |
|---|---|---|---|
| Weeks since the rules were frozen | 0.0 | 3 | no |
| Graded Bets and Conditionals | 0 | 10 | no |
| Of those with a closing line | 0 | 5 | no |
| Average closing-line value (win chance) | n/a | >= +0.0% | no |
| Every pick has a don't-bet-past number | 0 missing | 0 missing | yes |
| Finished picks all graded | 0 ungraded | 0 ungraded | yes |
| Graded picks for the full unit | 0 | 100 | no |
| Average closing-line value above | n/a | > +0.0% | no |

## College: Stage 0: observe, no money

| Criterion | Have | Need | Met |
|---|---|---|---|
| Weeks since the rules were frozen | 0.0 | 3 | no |
| Graded Bets and Conditionals | 0 | 10 | no |
| Of those with a closing line | 0 | 5 | no |
| Average closing-line value (win chance) | n/a | >= +0.0% | no |
| Every pick has a don't-bet-past number | 0 missing | 0 missing | yes |
| Finished picks all graded | 0 ungraded | 0 ungraded | yes |
| Graded picks for the full unit | 0 | 100 | no |
| Average closing-line value above | n/a | > +0.0% | no |

## NBA: Stage 0: observe, no money

| Criterion | Have | Need | Met |
|---|---|---|---|
| Weeks since the rules were frozen | 0.0 | 3 | no |
| Graded Bets and Conditionals | 0 | 25 | no |
| Of those with a closing line | 0 | 15 | no |
| Average closing-line value (win chance) | n/a | >= +0.0% | no |
| Every pick has a don't-bet-past number | 0 missing | 0 missing | yes |
| Finished picks all graded | 0 ungraded | 0 ungraded | yes |
| Graded picks for the full unit | 0 | 100 | no |
| Average closing-line value above | n/a | > +0.0% | no |

## What each stage allows

- **Stage 0:** no money. Everything is logged and graded.
- **Stage 1:** $12.5 on a Bet (status Bet only) in that sport, at the Wagerhouse number or better than its "don't bet past", re-checked just before you place it. At most 2 units staked per week across all picks and sports. Log it with `engine bet add`.
- **Stage 2:** the full $25 unit; the sizing review the spec already requires after 100 graded.
- **Never bet at any stage:** Conditionals, wind totals, paper Leans (until 50 are graded with average closing-line value above zero), props (until a model passes its gate), paper teasers (until the teaser lane is judged), anything past the "don't bet past" number, anything in the first few minutes after a change of rule version.

## Pause rules (back to Stage 0, per sport)

- Average closing-line value below -1.5% win chance once 25 picks in that sport have a closing line.
- Down 10 units from the start of Stage 1 (bankroll protection, not evidence).
- Any pick bet past its limit, or a pick with no limit.
- A change to the settings that decide picks (`picks`, `models`, `leans`, `margin_sd`, `sports` in `config.yaml`): the clock and the graded count start again from that change. A code-only change is recorded as a new rule version but does not restart the clock; Kylor decides whether it should.
