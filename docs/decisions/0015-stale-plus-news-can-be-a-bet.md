# 0015: A stale number with news behind it can become a Bet, once the lag is proven (2026-11-23)

Kylor approved: "2. yes", on the condition in review 14 (section 5, item 5): after the first week shows Wagerhouse actually lags.

**What it will be.** When Wagerhouse is on an old number after Pinnacle moved, and the research agent finds timestamped news in that window that explains the move, the side may be issued as a Bet (code owns the number and the "don't bet past"; the agent owns the news check). This is the one case where the news is the reason and no matchup paragraph is required. A price gap with no news stays never a reason.

**Changed the same evening (2026-11-23): on now, as paper.** Every sport is at Stage 0, where a Bet is tracked and graded with no money, so holding these back only delayed the record. The agent may issue them as Bets now (`ops/agent_prompt.md`, step 5). The lag verdict below now decides whether they may ever carry money, together with the normal readiness rules (decision 0017).

**Original condition (now the condition for money).** When section 4 of `engine wh-edge` (docs/research/12-wagerhouse-vs-pinnacle.md) says **keep**: 60+ moves timed by the fast reads, of which 30%+ left Wagerhouse on the old number 20+ minutes. If it says **kill** (80%+ matched within 10 minutes), this decision lapses. The switch itself is not built yet; it gets built and turned on in the session that sees "keep", with a note here.

**Kill after it is on.** Average closing-line value of these Bets at or below zero win chance after 40, or fewer than half still at the alerted number when Kylor checks by hand.

**Meanwhile.** A new stale number starts a research run for that sport (decision 0016), and the agent reports the news it finds in the card's slate note, so the evidence builds before the switch.
