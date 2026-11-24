# 0027: Charter review applied: one pick path, Telegram is bets only, money rules, one session at a time (2026-11-23, night)

Replaces: the Telegram rules in decision 0026 (keeps its stakes), the "cleared CHECK picks are paper" rule in 0025, the readiness stages
in 0012 (except their review line), paper Leans in 0010, STALE NUMBER alerts on Telegram in 0013, the old path's Bet messages in 0015.

Kylor, after reading `docs/research/19-charter-review.md`: "fix it". Taken as yes to every recommendation in that review's section 3.
The one answer that needed a number he has not given is the bankroll (question 5): left unconfirmed in `config.yaml` and the charter.

**Telegram carries three things only** (`telegram.send_kinds: [bet, system, recap]`):
- staked playbook picks (A and B) and teaser tickets, each with its stake, its "don't bet past" number and its edge split;
- the 9am recap, which now also says what was not sent in the last 24 hours (paper lanes, caps, a stop) and the money rules;
- system lines: the engine is broken, or a lane changed (a model or lane switched, a stop tripped, a staked lane's closing-line value fell
  below the review line). Each lane event is sent once (`playbook.lane_events`, `poll.py`).
Held back, still on the cards and the board: STALE NUMBER price alerts, the old path's messages, NO BETS summaries, paper picks.

**One pick path: the playbook.** The research agent's Bet / Conditional / Pass decisions are kept on the card and graded as a $0 record
(`agent.send_picks: false`, `OLD PATH, $0 RECORD` in their text). The agent's main job is the playbook's CHECK rows. A CHECK pick it clears
with a positive sourced reason and what the market already assumes is staked and sent like any other B pick (was paper under 0025).

**Money rules (CHARTER, Money):**
- Weekly cap: at most $500 recommended on Telegram, Monday to Sunday Mountain, all sports and teasers (`playbook.weekly_cap_dollars`).
  A pick past it is issued as paper and named in the recap.
- The NFL stop (10 NFL units) counts teaser tickets; the teaser's stake reads the NFL stop only (it used to read every sport's losses and
  none of its own). NBA has its own 10-unit stop. A stop is a pause for review, not a verdict.
- Review line: a staked lane whose average closing-line value is below -1.5% win chance on 25 graded picks gets one REVIEW line on
  Telegram; it stays staked until a session and Kylor decide (`go_live.pause_n`, `pause_clv`, the only readiness settings still read).
- Teasers are judged at 300 graded legs (config said 150; decision 0025 and research 18 said 300).

**The price gap stays visible.** "A price gap alone is never a reason" is kept. Every pick now stores `price_edge`, the edge it would have if
our number were the market's (that part is only Wagerhouse's price against Pinnacle), and every message and the tracker show the split.
Recorded from Nov 24; earlier picks have none.

**The Wagerhouse locked line** now reads: "I stay on Wagerhouse only. It charges more than sharp books, so a pick has to beat its higher
margin. If it has a weakness, it is being slow to follow news; that is measured, not assumed." (research 12, 12a, 14).

**Retired:** the readiness stages (`docs/lanes/READINESS.md` deleted; `engine ready` kept for reference), paper Leans (`leans.enabled:
false`; sourced opinions go in `adjustments.yaml` or a CHECK verdict), the Monday lane table on Telegram (it was never delivered: held back
as `info`).

**One session owns the code, enforced.** `engine lock take "why"` writes `data.nosync/SESSION.lock`; a second session is refused; a lock
older than 4 hours is stale; scheduled jobs skip their auto-commit while a fresh lock is held. New rule: the newest decision note wins, says
what it replaces, and its commit updates every document that quoted the old rule.

**Documents:** CHARTER = purpose, Telegram, money, locked decisions, how sessions work. PLAYBOOK = how a pick is chosen. CLAUDE.md = how code
is built. Generated files say what is live.

Code: `picks/playbook.py` (weekly cap, `down_units`, `price_edge`, `edge_split`, `lane_record`, `lane_events`), `picks/teasers.py`,
`picks/agent.py`, `poll.py`, `lanes.py`, `bets/tracker.py`, `picks/board.py`, `session_lock.py`, `gitsync.py`, `cli.py`; tests in
`tests/test_review19.py` (236 pass).
