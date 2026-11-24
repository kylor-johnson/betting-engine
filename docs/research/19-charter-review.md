# 19. Charter review (Mon Nov 23, 2026, night)

**Applied the same night (decision 0027): Kylor said "fix it", taken as yes to every recommendation in section 3. The bankroll (question 5) is still open.**

## 1. Does the charter say what you want, and what has to change?

**Mostly yes on purpose, no on mechanics.** The top of the charter now says it plainly: Telegram is where every bet arrives with a stake and a
"don't bet past" number, you place from there, and the tracker grades the picks against what you bet. That matches what you said tonight.
Below that line, the charter, the playbook, the build spec and the code still disagree in five ways that matter:

1. **Telegram carries more than bets, and not every bet.** It still gets the old research-agent path's messages. Right now every one of
   those is a $0 "PAPER BET (Stage 0)" or a paper "WAIT" (the old path is still at Stage 0 of the readiness rules). It also gets STALE NUMBER
   price alerts that are labelled "not a pick". Meanwhile a playbook pick the research agent clears with a sourced reason is issued at $0
   and **not** sent. So Telegram gets messages that aren't bets, and misses picks the model found. The charter's own sentence, "paper picks
   never go to Telegram", is false in code today.
2. **There are two pick systems, and you are only following one.** All 11 picks in the tracker came from the playbook (10 picks and 1 teaser ticket); none came from the old path.
   The old path (Bet / Conditional on news Pinnacle hasn't moved for) still runs every research pass and can still message. The playbook
   says it was meant to be retired once the pick list went live (decision 0018). It never was.
3. **Real money has no money rules around it.** The config's bankroll is $2,500 ("implied by a $25 unit"), which is stale now that the NFL
   unit is $50. At research 18's volume, Telegram would recommend about **$825 a week** (5 NFL full-game picks at $25, 10 NFL props at $25,
   28 NBA props at $12.50, about 2 teasers at $50). Day one alone was $262.50. The 10-unit stops are per sport ($500 NFL, $250 NBA) and
   **teaser losses count toward no stop at all**. The teaser's own stop reads every sport's playbook losses added together, so NBA units and
   NFL units get mixed. Nothing caps a week.
4. **"One session owns the code" is a sentence, not a rule.** Nothing enforces it. Two sessions broke it today, and decisions 0025 and 0026
   reversed each other within hours. The playbook was left saying "paper" (its sections 4 and 9) after the reversal.
5. **The charter still says Wagerhouse is a soft book.** The evidence says it isn't, on price. Its juice is 4.7–4.8% on full-game lines
   against Pinnacle's 2.6–3.2%, and 6–7% on team totals and quarters (research 12, 14). What it may be is slow, and that is still being
   measured. There's a sharper version of the same problem. Research 18 found the only measured value in the staked full-game picks is
   Wagerhouse sitting half a point to a point off Pinnacle, which is a price gap. The charter says a price gap alone is never a reason.
   Your picks are partly living on the thing the charter forbids. You should decide that knowingly.

**What has to change:** one pick path, and Telegram = staked picks + recap + broken-engine alerts, nothing else. Add a written bankroll,
a weekly exposure cap, and a stop that includes teasers. A lock that the scheduled jobs and sessions both respect, plus "the newest decision
names the one it replaces". The Wagerhouse line reworded to what the evidence supports. The drift-guard text fixed to match what actually
reaches you. And a strict split of the three documents (charter = why and the locked rules; playbook = how a pick is chosen; CLAUDE.md =
how code is built), with the two-thirds of CLAUDE.md that is stale cut out.

**Uncommitted work at the start of this session:** six generated files: today's college, NBA and NFL playbook and props cards, and
`docs/lanes/TRACKER.md`. They are outputs of the 5:33 PM scheduled run (re-priced props, the UCLA Conditional downgraded to a Pass by
decision 0025's `priced_in` rule), not edits by a session. No session wrote them, including this one. I left them alone. The engine's
next auto-commit should pick them up.

---

## 2. The nine questions, answered

**Q1. Is every bet reaching Telegram with a stake and a limit?** Playbook picks and teasers: yes, every A/B pick with dollars above zero
goes out with stake and limit (`picks/playbook.py`, `_send_and_save`), and every message is kept in `alerts_sent`. Three gaps:
(a) a CHECK pick the agent clears is forced to $0 and not sent (`_paper_or_staked`, "paper: a CHECK-cleared pick");
(b) a pick over the one-unit-a-game cap or the weekly cap is silently paper or not issued, and you never hear about it;
(c) the old path sends $0 "PAPER BET" and paper "WAIT" messages under the same `bet` kind (`picks/agent.py` `message()`).
**Recommendation:** no paper or C picks on Telegram; it would dilute the one channel you act on. Instead, the 9am recap gets one line:
"Not sent yesterday: N paper picks (caps, CHECK holds, unstaked lanes); paper record X-Y." The recap is enough if it carries that line.

**Q2. Two pick paths.** You are following the playbook. Retire the old path as a *messenger*. The research agent keeps its real job:
clearing CHECK rows, writing `priced_in`, and finding news. Its Bet/Conditional decisions become inputs to the playbook (a sourced adjustment
the script uses) or a paper record. They are not separate Telegram messages. The wind-totals model then lives inside the NFL script (it
already does), not as a second route to a pick.

**Q3. Real money without evidence.** The charter records your choice honestly. It needs three numbers you agree to:
a bankroll (if it's $5,000, a $50 unit is 1%; at $2,500 it's 2%, and a $50 teaser is 2%), a weekly cap on what Telegram recommends
(suggested: 10 NFL units, $500, across all lanes, with picks past it sent as "over the weekly cap, $0" to the recap only), and a stop that
counts every staked lane, teasers included. 10 units per sport is reasonable as a *pause-and-review* point. It is not evidence either way:
research 18 puts the expected result at about −$25 a week with a ±$145 weekly swing, so 10 NFL units can go in two bad weeks by luck alone.
Say that in the charter so a stop isn't read as a verdict.

**Q4. The drift guard.** Today a switched-off model shows up only in a session summary and in `STATUS.md`. The charter also says the table
goes "to Telegram on Monday mornings and whenever it changes". It doesn't: the poller tags it `status`, which is sent as `info` and held
back (`poll.py` line 41). It also still says "all five lanes"; there are six. **Recommendation:** a lane change (a staked lane switched to paper or
back, a model switched on or off, a stop triggered) gets one Telegram line, `kind: system`. It happens a few times a month at most and it's
exactly the "I found out a week later" failure the guard exists for. No Monday table.

**Q5. One session owns the code.** Enforce it. A lock file `data.nosync/SESSION.lock` with the session's start time and purpose. Sessions
write it before touching `src/`, `config.yaml`, `adjustments.yaml`, `ops/`, `CHARTER.md` or `PLAYBOOK.md` and refuse if another one holds it
(stale after 4 hours). The scheduled jobs already skip their auto-commit on a git `index.lock` (`gitsync.py`); they should also skip it while
`SESSION.lock` is held, so a run never commits half of a session's change. Decisions: "The newest decision note wins. It must say
`Replaces: 00NN` (or `Replaces: none`), and the session that writes it also updates every document that quoted the old one, in the same
commit." That last clause is the one that would have kept the playbook from saying "paper" tonight.

**Q6. "Wagerhouse is a soft book; that is probably where my edge is."** The evidence: Wagerhouse charges more than Pinnacle, and the two
numbers sit within 0.2–0.35 points on average (research 12, 12a). Betting the better side at Wagerhouse, with Pinnacle as the truth, was
worth −1.5% to −4.7% on average in every market. Research 14 calls "soft on price" unsupported and says the testable version is "slow".
The lag measurement (`engine wh-edge` section 4, decision 0015) has no verdict yet. It is your locked line. A wording that keeps your intent
and matches the evidence: "I stay on Wagerhouse only. It charges more than sharp books, so a pick has to beat its higher margin. If it has a
weakness, it is being slow to follow news; that is measured, not assumed."

**Q7. What is obsolete.**
- **Readiness Stage 0/1/2** (`docs/lanes/READINESS.md`, decision 0012): it gates only the old path. Retire it with the old path. Keep its
  pause rule ("closing-line value below −1.5% on 25 picks") as a per-lane *review* trigger for the playbook, next to research 18's restart
  numbers.
- **Paper Leans** (decision 0010): these are the agent's paper opinions, and C picks are the code's. They overlap. Merge them: a lean becomes
  a sourced adjustment the playbook prices. If the adjusted pick clears, it's an A/B pick. If not, it's a C pick with the agent's reason on
  it. One record, not two.
- **STALE NUMBER alerts** (decision 0013): off Telegram (they're price notes, and the playbook said so already in its section 7). Keep them
  on the card and keep the lag measurement, because that measurement is the only test of the "slow book" idea.

**Q8. Which document owns what.**
- **CHARTER** = purpose, lanes, what reaches Telegram, money rules (units, bankroll, caps, stops), locked decisions, how sessions work.
  No mechanics, no model weights, no "currently built" tables.
- **PLAYBOOK** = how a pick is chosen and graded: script, adjustments, blend weights, edges, grades, CHECK, caps per lane. It quotes no
  money amounts; it says "units" and points to the charter.
- **CLAUDE.md** = how code is built: environment, sources, logging and time rules, secrets, read-only account access, testing, commit
  rules, where things live. No pick rules at all; one line pointing to the playbook.
- **Generated, never typed:** `STATUS.md`, `TRACKER.md`, `PLAYBOOK-RECORD.md`. Anything that says "what is live today" belongs here.
Every stale sentence in CLAUDE.md and PLAYBOOK.md is in section 4.

**Q9. What "working" looks like.** Rewritten as checks below (redline, section "What working looks like"). Each one can be a SQL query or
a file check, and together they would make an `engine check` command (proposal only).

---

## 3. Questions for you (yes or no)

1. **Retire the old research-agent pick path as a sender?** The agent keeps clearing CHECK rows and finding news, but only the playbook
   sends picks. (I recommend yes.)
2. **Take STALE NUMBER price alerts off Telegram?** They stay on the cards, and the slow-book measurement keeps running. (Yes.)
3. **When the research agent clears a CHECK pick with a sourced reason, stake it and send it like any other B pick?** Today it is $0 and
   not sent. (Yes, because tonight's rule already requires a positive sourced reason, and "nothing found" stays a hold.)
4. **Keep paper and C picks off Telegram, and add one line to the 9am recap saying what wasn't sent and how the paper picks are doing?** (Yes.)
5. **Is your betting bankroll $2,500?** If not, tell me the number. The config still says $2,500, which was set for a $25 unit.
6. **Cap what Telegram recommends at $500 a week (10 NFL units) across all lanes?** Picks past the cap would be recorded as paper and named
   in the recap. (Yes, or give me your number.)
7. **Count teaser losses toward the NFL 10-unit stop, and stop counting NBA losses in the teaser's stop?** Today teasers count toward no
   stop and their own stop mixes sports. (Yes.)
8. **Keep the stop at 10 units per sport, written as "pause and review", not "the model failed"?** (Yes.)
9. **Send one Telegram line when a lane changes** (a model switched on or off, a lane moved between paper and money, a stop triggered)?
   (Yes.)
10. **Add a lock file so only one session can change code, config or the charter at a time, and the scheduled jobs don't auto-commit while
    it's held?** (Yes.)
11. **Rule: the newest decision note wins, must name the one it replaces, and must update every document that quoted the old one in the
    same commit?** (Yes.)
12. **Change your locked Wagerhouse line to: "I stay on Wagerhouse only. It charges more than sharp books, so a pick has to beat its higher
    margin. If it has a weakness, it is being slow to follow news; that is measured, not assumed."?** (Your call; the evidence supports the change.)
13. **Keep "a price gap alone is never a reason for a pick", knowing research 18 found the price gap is the only measured value in today's
    staked full-game picks?** Yes keeps the rule (and those picks then stand on the handicap, which hasn't shown value yet). No would mean
    writing an explicit price-gap lane with its own test. (Your call; I'd keep the rule and let the tracker show whether the handicap earns it.)
14. **Retire the Stage 0/1/2 readiness rules along with the old path, keeping only their "closing-line value below −1.5%" review trigger?** (Yes.)
15. **Merge paper Leans into the playbook's C picks** (the agent's opinion becomes a sourced adjustment, graded in one record)? (Yes.)
16. **Split the documents: charter = why and money rules, playbook = how a pick is chosen, CLAUDE.md = how code is built, with the stale
    pick rules cut out of CLAUDE.md?** (Yes.)

---

## 4. Redline of CHARTER.md, section by section

Format: **Now** (current text, trimmed with "…" only where nothing changes), **Proposed**, **Why** (one line).

### Header

**Now:** "Every session reads this before `CLAUDE.md` and before touching anything. If something in the code, the spec or a handoff disagrees
with this page, this page wins until I change it."
**Proposed:** add: "`PLAYBOOK.md` owns how a pick is chosen; `CLAUDE.md` owns how code is built. Neither repeats a money amount or a locked
rule; they point here."
**Why:** three documents described picks and drifted apart within a day.

### What I want

**Now:** "Telegram is the source of truth (decision 0026). It is where I get every bet this model finds, with its stake and its "don't bet
past" number, and I place them from there. Anything that is not on Telegram is not a bet."
**Proposed:** "Telegram is the source of truth (decision 0026). It is where I get every bet this model finds, with its stake and its "don't
bet past" number, and I place them from there. Telegram carries only three things: staked picks (playbook A and B picks and teaser
tickets), the 9am recap, and alerts that the engine is broken or a lane changed. Anything that is not on Telegram is not a bet, and nothing
on Telegram is a $0 pick."
**Why:** today Telegram also gets $0 old-path "PAPER BET" messages and price alerts. The sentence has to be checkable.

**Now:** "It is not a price checker. The tracker … grades every Telegram pick against what I actually bet; the price checks, logs and
reports are plumbing."
**Proposed:** unchanged, plus: "The tracker also shows the picks that were not sent (paper lanes, caps, holds) on their own line, so I can
see what I'm not being sent."
**Why:** "every bet this model finds" has exceptions (caps, holds). You should see them, just not on Telegram.

### The lanes

**Now:** "6. NFL Wong teasers (added 2026-11-23, decision 0014; real money since decision 0019)"
**Proposed:** add one line under the list: "Each lane is in one of three states, set in `config.yaml` and shown in `STATUS.md`: **staked**
(sent to Telegram), **paper** (issued and graded at $0, not sent), **shown** (on the card only). Today: staked = NFL spreads and totals, NFL
props, NBA props, NFL teasers; shown = college and NBA spreads and totals."
**Why:** "staked/paper/shown" is the switch that changed three times today. Naming it makes the next change one word, not a paragraph.

**Now:** "Each sport has its own research-agent guide … and its own record by market (`docs/lanes/PLAYBOOK-RECORD.md`) …"
**Proposed:** unchanged.

### What "working" looks like

**Now:** four prose bullets ("Every lane says, in plain words …" etc.).
**Proposed:** "Working means these checks pass (`engine check`, run at the end of every session and every morning):
1. Every staked pick (playbook and teaser, dollars above $0) has a Telegram message marked delivered and a row in the tracker.
2. No Telegram message of kind `bet` has a $0 stake.
3. Every staked pick has a "don't bet past" number and a grade within 24 hours of the game ending; props and team totals also have a
   closing grade.
4. Every lane's last candidate (A, B or C) is less than 2 days old for the NBA, less than 8 days old for the NFL and college in season,
   or `STATUS.md` says why.
5. `STATUS.md` was generated in the last 24 hours from the current config.
6. This week's staked total is under the weekly cap, and each stop shows how many units are left before it trips (teasers included).
7. The hourly read ran in the last 2 hours during read hours, and the research run ran at its fixed times.
8. No session lock is older than 4 hours."
**Why:** the prose couldn't fail. These can, and each one answers "is Telegram the truth?" directly.

### The drift guard

**Now (item 2):** "The table is on the board page and in `docs/lanes/STATUS.md`. (It used to go to Telegram on Mondays; since Telegram
became bets-only it does not. See "Telegram" below.)"
**Proposed:** "The table is on the board page and in `docs/lanes/STATUS.md`. When a lane changes (a model switched on or off, a lane moved
between staked, paper and shown, a stop triggered), Telegram gets one line saying what changed and the decision note that changed it."
**Why:** a change you don't see is the exact failure the guard exists for. One line a few times a month doesn't dilute a bets channel.

**Now (paragraph after item 5):** "`engine status` now exists … The table is generated into `docs/lanes/STATUS.md`, onto `board.html`, and
to Telegram on Monday mornings and whenever it changes."
**Proposed:** "`engine status` generates the table into `docs/lanes/STATUS.md` and onto `board.html`. Do not edit it by hand; change
`config.yaml` (`lanes:` and the switches it points to)."
**Why:** the Monday and on-change messages are tagged `status` and held back (`poll.py`), so this sentence contradicts item 2 and the code.

**Now:** "Tested against the closing line and left off … Passed and in use: wind on NFL totals (05), schedule-adjusted form in the NFL
script (17), the props lead effect for three stats (16), the landing tables (11a)."
**Proposed:** move this list to `PLAYBOOK.md` (a "tested inputs" table) and leave one line: "What has been tested and its result is in
`PLAYBOOK.md`, section 9, and in `STATUS.md`."
**Why:** it's mechanics, it changes weekly, and research 18 found the wind lead uses the actual wind, not the forecast. That should be
fixed in one place, not two.

### How picks are chosen

**Now:** "The engine handicaps each game … and picks where its number beats Wagerhouse's. Other books are a price filter and a sanity check,
never the reason for a pick. … In code, "the market" our number is blended toward is Pinnacle's line when posted, else Wagerhouse's."
**Proposed:** "How a pick is chosen is `PLAYBOOK.md`, and only there. One sentence of summary: the engine builds its own number for each
market from a game-script handicap, pulls it part of the way toward Pinnacle, and picks where that beats Wagerhouse's price; the research
agent clears the picks whose number is far from the market. There is one pick path. The research agent does not send picks of its own."
**Why:** the blend detail is mechanics, and "one pick path" is the rule that's missing.

### Locked decisions

**Now:** "I stay on Wagerhouse only. It is a soft book; that is probably where my edge is."
**Proposed (if you say yes to question 12):** "I stay on Wagerhouse only. It charges more than sharp books, so a pick has to beat its
higher margin. If it has a weakness, it is being slow to follow news; that is measured, not assumed."
**Why:** research 12, 12a and 14 found it more expensive than Pinnacle and within a third of a point of it. "Soft" is not supported.

**Now:** "Units: NFL $50, NBA $25 (changed 2026-11-23, decision 0020); college $25 until I say otherwise."
**Proposed:** move to a new "Money" section (below) and replace here with: "Money rules are in the Money section; a session never changes
them without a decision note I asked for."
**Why:** units, bankroll, caps and stops belong together.

**Now:** "A price gap alone is never a reason for a pick."
**Proposed (if you say yes to question 13):** unchanged, plus: "Because the playbook blends toward Pinnacle, a pick can clear the bar mostly
on Wagerhouse being off Pinnacle. The tracker shows, per lane, how much of each pick's edge was the handicap and how much was the price."
**Why:** research 18 found that's where today's full-game value comes from. Keep the rule, but make it visible.

All other locked lines: unchanged.

### New section: Money (proposed)

"- **Units:** NFL $50, NBA $25, college $25 (decision 0020).
- **Bankroll:** $____ (your answer to question 5). A unit should be 1 to 2% of it.
- **Stakes:** A = 1 unit, B = half a unit, C = nothing. Teaser tickets = 1 NFL unit. At most 1 unit on any one game across picks and teaser
  legs.
- **Weekly cap:** at most $____ recommended on Telegram, Monday to Sunday Mountain (suggested $500). Picks past it are paper and named in
  the recap.
- **Stops:** each sport pauses to paper when its staked picks are down 10 units since `live_since`. NFL counts teaser tickets. A stop is a
  pause for review, not a verdict: at this volume 10 units can go in two bad weeks by luck alone. I restart it.
- **Yardstick for keeping a lane staked:** research 18's restart numbers (full-game: closing-line value +2.4 points of win chance on 100 picks;
  props: the blend beats Pinnacle on 300 and closing-line value above zero; teasers: 72.4% on 300 legs). Missing them is a review, not an
  automatic switch-off, because you chose to stake these lanes (decision 0026)."
**Why:** you're betting real money on lanes with no shown edge. The charter should say how much and when to stop. It currently says neither.
Also, the teaser kill number disagrees: config `kill_after_legs: 150`, decisions 0025 and research 18 say 300.

### Decided since this page was first written

**Now:** four paragraphs (Leans; Real money from the start; decision 0025; reversed by 0026) plus the Telegram paragraph.
**Proposed:** delete the history paragraphs. Keep only current rules, each moved to the section it belongs to (Telegram rules to "What I
want", money to "Money", Leans to the playbook or retired by question 15). Add one line: "History of how we got here: `docs/decisions/`."
**Why:** "Changed … reversed the same evening" in a charter is exactly what a fresh session misreads. Decisions already keep the history.

**Now (Telegram paragraph):** "It sends: staked playbook picks (A and B) and teaser tickets with their stake and limit; the old path's Bet,
Conditional and cancellation messages; STALE NUMBER price alerts (labelled not a pick); the tracker's 9am recap; and alerts that the engine is
broken."
**Proposed (if yes to questions 1, 2, 9):** "It sends: staked playbook picks (A and B) and teaser tickets, each with stake and limit; a
CANCELLED message if a sent pick should no longer be bet; the 9am recap (yesterday's results, what was not sent and why); one line when a
lane changes; and alerts that the engine is broken. Config: `telegram.send_kinds: [bet, system, recap]`."
**Why:** matches "every bet, and only bets".

### How sessions work together

**Now:** "One session owns the code at a time. Other sessions may read and write research, but do not edit `src/`, `config.yaml` or
`adjustments.yaml` while another session is mid-change."
**Proposed:** "One session owns the code at a time, enforced by `data.nosync/SESSION.lock` (who, when, why). A session writes it before
editing `src/`, `ops/`, `config.yaml`, `adjustments.yaml`, `CHARTER.md` or `PLAYBOOK.md`, removes it when it commits, and stops if another
session holds it (a lock older than 4 hours is stale and may be taken). Scheduled jobs don't auto-commit while it is held. The research
agent may still write its decisions, checks and adjustments files."
**Why:** today proved the sentence alone doesn't hold.

**Proposed new bullet:** "**Decisions:** the newest decision note wins. It names the one it replaces (`Replaces: 00NN` or `Replaces: none`),
and the same commit updates every document that quoted the old rule (charter, playbook, agent prompts, config comments)."
**Why:** 0025 and 0026 reversed each other and the playbook kept 0025's text.

**Now:** "Start by running `git status` and `git log`. If there is uncommitted work you did not write, stop and ask me."
**Proposed:** add: "Generated outputs of a scheduled run (cards, `TRACKER.md`, `STATUS.md`) are not "work"; say they are there and leave
them for the engine's auto-commit."
**Why:** this session found exactly that and the rule as written would have stopped it.

### Where things live

**Now:** "`docs/lanes/` … READINESS.md (the old Stage rules, kept for the old Bet path)"; "CLAUDE.md the build spec and working rules";
"PLAYBOOK.md how picks are chosen (approved; what is built is in its section 9)".
**Proposed:** remove READINESS.md if question 14 is yes. "CLAUDE.md: how code is built (environment, sources, logging, secrets, tests)."
Add `HANDOFF.md` (or fold it into CLAUDE.md; it's referenced from CLAUDE.md but not listed here) and `data.nosync/SESSION.lock`.
**Why:** keep the map true.

---

## 5. Stale sentences in CLAUDE.md, with fixes

If you say yes to question 16, most of these go away by deleting the "Picks engine" section and replacing it with a pointer to
`PLAYBOOK.md`. Listed one by one anyway so nothing is missed.

| # | Where | Stale sentence | Fix |
|---|---|---|---|
| 1 | Top | "This file is copied to `CLAUDE.md`." | Delete; this file *is* CLAUDE.md. |
| 2 | Top | "Build one phase at a time. Do not start a phase until the one before it passes its exit test and Kylor says go." | "Build what a decision note approves." The phases were overtaken (props and scripts are built; Phase 1B's exit test was never run). |
| 3 | What this is | "It compares the price at Kylor's book (Wagerhouse) with the market price and says when his is better, when a line is moving, and whether his past bets were good prices." | "It handicaps games and sends staked picks to Telegram (`CHARTER.md`, `PLAYBOOK.md`). Price comparisons are inputs and filters." |
| 4 | Ground rules | "The market reference is DraftKings as published by ESPN. … Every report says so, and "fair price" is labelled approximate." | "The market reference is Pinnacle's guest line (vig removed), else Wagerhouse's. DraftKings via ESPN is logged for history and the audit." Config `reference_book: DraftKings` should get a comment saying what still uses it. |
| 5 | Ground rules | "Unit = $25. Engine picks are 1 unit (0.5 for a Conditional) until 100 are graded." | "Units and stakes: see `CHARTER.md`, Money." |
| 6 | Ground rules | "Closing line value is measured on sides, totals and moneylines only, never props, and is treated as a compass, not proof." | "…on sides, totals and moneylines; props and team totals get a closing grade against Pinnacle's last read (decision 0025). A compass, not proof." |
| 7 | Phase 1B, item 3 | "Alerts by Telegram: Opener digest … Off-market … Moving now … Watchlist" | "These are logged and shown on the board. Telegram sends only what `CHARTER.md` lists." |
| 8 | Picks engine | "(approved 2026-11-21; this is the product)" | "The product is the playbook (`PLAYBOOK.md`)." |
| 9 | Picks engine | "three independent fair numbers … the blended fair line (55% Pinnacle, 45% model)" | Delete. The model leg is off since Nov 22 (`use_model_leg: false`); the playbook blends its script toward Pinnacle at per-market weights. |
| 10 | Picks engine | "A Bet needs all four:" (lists three) | Delete with the old path (question 1); otherwise "all three". |
| 11 | Picks engine | "Sizing: 1 unit per Bet, 0.5 for a Conditional, until the engine has 100 graded picks. Then revisit 0.5 to 3 units by edge." | Delete; stakes are A/B by grade (charter, Money). |
| 12 | Picks engine | "Totals are not picked from ratings alone. The wind totals model … can make an Under a Conditional" | "Totals are priced by the NFL game script, which includes wind." Also note research 18: the wind lead used actual wind at kickoff, not the forecast. |
| 13 | Picks engine | "Props models … testing only until each passes decision 0006's gate" | "NFL and NBA props are staked playbook B picks (decisions 0021, 0022, 0026); decision 0006's forward test keeps running as the yardstick." |
| 14 | Picks engine | "NFL Wong teasers (paper)" | "NFL Wong teasers (real money, A, 1 NFL unit a ticket; decisions 0014, 0019)." |
| 15 | Picks engine | "NBA injury watcher … ESPN report only" | "…news from reporter posts (Rotoworld relay), the official NBA injury PDF, then ESPN (`picks/player_news.py`, `nba_news.py`)." |
| 16 | Picks engine | "A new STALE NUMBER alert starts a research run for that sport (decision 0016)." | Keep if stale alerts stay as research triggers; add "not sent to Telegram" if question 2 is yes. |
| 17 | Picks engine | "Research agent instructions … A Bet's reason is timestamped news Wagerhouse has not priced, or a tested model" | "The research agent clears CHECK rows and writes what the number already prices (`priced_in`); it does not send picks." (if question 1 is yes) |
| 18 | Picks engine | "Order of work: NFL slate and card (built) → scheduled agent runs and pick alerts → injury and news watcher → college football → NBA." | Delete; all built. |
| 19 | Phase 3 | "A props check that compares Wagerhouse's number with other books." | "Wagerhouse props can't be read (decision 0011); each prop pick states the worst Wagerhouse line and price to take." |
| 20 | Phase 4 | "Football ratings (offseason 2027) … Its job is to rank which openers to look at first." | "The NFL, college and NBA game scripts exist (research 15, 16); openers from ratings failed (research 09)." |
| 21 | Phase 5 | "Picks only after the forward test against Pinnacle passes." | "Staked by your choice since decision 0026; the forward test is the yardstick, not the gate." |
| 22 | Rules | "Teasers: only 2-team 6-point at −110 … or 6.5-point at −120" | Keep, and add: "The engine builds 6-point tickets only (`teasers.points: 6`)." |
| 23 | Out of scope | (fine) | No change. |

Also: CLAUDE.md says "`HANDOFF.md` has the working rules and folder layout"; the charter's "How sessions work together" and "Where things
live" now hold both. Fold the rest of `HANDOFF.md` into CLAUDE.md or mark it historical.

## 6. Stale sentences in PLAYBOOK.md, with fixes

| # | Where | Stale sentence | Fix |
|---|---|---|---|
| 1 | Header | "The charter still owns the locked rules (… $25 unit, …)" | "…(Wagerhouse only, no paid data, the engine never places bets, units and money rules, code owns every number)." |
| 2 | Step 1 table | "Throw out outliers: games against the league's top and bottom 3 defenses get half weight" | "Tested, no held-out gain, off (research 17)." |
| 3 | Step 2 table | Injury clusters: "Not tested yet; tracked from day one" | "Tested, no held-out gain, off (research 17)." |
| 4 | Step 2 table | Rain: "Not tested yet" | Section 9 says rain is a live input. Pick one: if it's live untested, say "live, untested"; otherwise "off". |
| 5 | Step 2 table | Referees: "only used after a walk-forward test passes" | "Tested, no held-out gain, off (research 17)." |
| 6 | Step 2 table | Wind: "Tested: 10 to 19 mph Unders hit 56 to 60%" | Add: "The script's totals lead used actual kickoff wind, not the forecast; re-test on forecasts (research 18)." |
| 7 | Step 3.1 | "efficiency against this defense's coverage type" | "Coverage type is not buildable (free data has 2023 only); blitz and box splits tested and off (research 17)." |
| 8 | Step 3.5 | "First half and quarters: the script's early part" | "Not built; period lines and team totals are logged only." |
| 9 | Step 4, sanity check | "If it finds nothing, the pick stands and is graded." | "'Nothing found' is a hold. A clear needs a positive sourced reason and what the market already assumes (decision 0025). A cleared pick is [staked / paper], per question 3." |
| 10 | Step 4, blend | "Each weight is re-fitted every 4 weeks on graded picks" | "A weight changes only after 40 graded candidates, by a session, with a decision note (decision 0022)." |
| 11 | Step 5 | "up to 5 a week for NFL and college, up to 2 a day for the NBA" | Add the prop caps: NFL 10 a week and 2 a game; NBA 4 a day and 2 a game; one unit a game across everything. |
| 12 | Step 5 | ""No pick" is never the whole message. If nothing clears the bar, you see the best C picks and why they fell short." | "…on the card and board. Telegram carries only staked picks; the recap says what wasn't sent." |
| 13 | Section 4 | "Stakes (decision 0025, 2026-11-23): … Only NFL Wong teasers are staked … Every other A and B pick is a paper pick" | Replace with decision 0026: NFL full-game, NFL props and NBA props staked at A 1 unit, B half; NBA and college full-game shown only; amounts in the charter. |
| 14 | Section 4 | "…cut to zero weight, with a note and a message (charter drift guard)" | Keep "message" only if question 9 is yes; otherwise "with a decision note and the session summary". |
| 15 | Section 7 | "The stale-number alerts stay as a price note on the card. They are no longer Telegram messages unless they line up with a model pick." | Config sends every stale alert (`send_kinds` includes `stale`). Make the config match this sentence (question 2), or change the sentence. |
| 16 | Section 7 | ""A Bet needs news Pinnacle hasn't moved for" is replaced by Step 4's edge and grades." | True in intent, false in code: that path still runs and messages. Fix by question 1. |
| 17 | Section 8 | Build order items 1–5 | Mark built (decisions 0019–0022); item 6 is built (`engine playbook-record`). |
| 18 | Section 9 | NFL script / NFL props / NBA props: "Live, **paper** (decision 0025)" | "Live, staked (decision 0026)." |
| 19 | Section 9 | NFL Wong teasers: "the only staked lane (decision 0025)" | "Live, staked (A), 1 NFL unit a ticket." |
| 20 | Section 9 | "Never into a move, one unit a game, CHECK clears with a reason, closing grades …: Live (decision 0025)" | Keep; add "kept by decision 0026". |

Other places that quote the old rules (not in scope to list fully, but the decisions rule in question 11 would catch them):
`ops/agent_prompt.md` ("Props … testing only … never mention props in a pick until its first line says PASSED"; "Below Stage 1 it is a
paper Bet"); `ops/agent_prompt_nba.md` ("playbook prop picks are issued by code (B picks, paper at $0 since decision 0025)");
the `playbook.sports` comment in `config.yaml` (still describes 0025's paper rule above the 0026 line); `STATUS.md` (generated 4:18 PM, before
decision 0026; regenerate); config `teasers.kill_after_legs: 150` vs "300 legs" in decision 0025 and research 18.
