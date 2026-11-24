# 0033: The final audit's yes-list (2026-11-24)

Kylor, Nov 24: "yes to all, do 1-10" to the 12 questions in research 22. Replaces the parts of decisions 0027, 0029 and 0030 named below.
Every document that quoted the old rule is updated in the same commit.

1. **A failed Telegram send is retried, not lost.** The send error is caught and the message is saved as not delivered. Every read resends any
   staked pick or teaser ticket, for a game not yet started, that has not reached Telegram, marked "SENT LATE". The delivery checks (checks 1
   and 2) then run on every read: one `system` line per pick still undelivered, and one per $0 pick sent as a bet. (`playbook.resend_undelivered`,
   `checks.delivery_problems`.) Replaces 0030's "once a day" for those two checks. Picks issued before messages were saved (Nov 23,
   before about 6pm MT) are never resent: they have no record, but most reached Telegram, and a second copy could mean a second bet.
2. **The stop counts from `live_since`** (midnight Mountain on that date), for playbook picks and teaser tickets. Restarting a stop is
   "set `playbook.live_since` to the restart day". (`playbook.down_units`, `live_since_utc`.)
3. **In college and NBA, the news-pick test runs before one pick per game is chosen.** A bigger script-only pick, which cannot be staked in
   those lanes, no longer hides the news pick on the same game. (`playbook.grade_all`.)
4. **News counts only after a Pinnacle read since the news.** An unchanged pre-news line proves nothing when Pinnacle took the game down or
   no read has run since. The entry shows "not applied: no Pinnacle read since the news yet" and the next read decides.
   (`slate.unpriced_part`.) Amends 0029.
5. **College starter ruled out before the game: about 4 points** (4.1 on 811 games where he threw no passes). The "above 5 needs a reason"
   rule is dropped; a weak-passing starter's absence was worth about 5. Research 21's 3.5 mixes in-game injuries and benchings the market
   could not know. (`ops/agent_prompt_college.md`, PLAYBOOK college section.)
6. **NFL quarterback news is counted once.** The game script's backup-quarterback flag is on only when the news adds nothing to our number by
   itself (Pinnacle has priced it, or the entry cannot count); while it is added as unpriced points, the flag is off. The NFL guide now
   sizes a starter out at 2.5 to 2.7 points (research 14, 2b). (`playbook.qb_out`.)
7. **A pick past a cap is issued as paper** with the cap as its reason, on the tracker and in the 9am recap, never dropped. Caps still count
   paper picks. (`playbook.run`, `_issue_props`.)
8. **CANCELLED message.** Every read, for each delivered staked playbook pick whose game has not started: carry Pinnacle's move since the pick
   into our number at the playbook weight; if the bet at its sent line and price is now under half the minimum edge (the same test that set
   "don't bet past"), send "CANCELLED, DO NOT BET" once. Props: the same edge test on Pinnacle's latest chance, or a line moved against it.
   The pick stays frozen and on the record; a bet already placed is kept. Nov 23 picks with no delivery record are checked too. Teaser tickets are not cancelled: their message already says to
   bet only while each leg is in range. (`playbook.cancel_moved`.)
9. **The research agent runs only read-only engine commands:** `slate`, `news`, `injuries`, `matchup`, `card`, `reporters`, `status` (no
   options) and `playbook --dry-run`. It can no longer issue or send picks, send status, log bets or take the lock. (`agent.AGENT_TOOLS`.)
10. **One research schedule.** The launchd job now matches `config.yaml` `agent.schedule`: 8:15 every day, plus 6:45 pm Sunday. Kylor reloads
    it once with launchctl (README).
11. **Half a unit on every playbook pick stays** until a principle passes its test and earns an A. Teaser tickets stay at 1 unit.
12. **Teaser pushes:** Kylor confirmed Wagerhouse refunds a 2-team teaser when a leg pushes. The engine's rule (a pushed leg = no action on
    the ticket) stands.
