# Handoff: consolidate the reviews and give me one plan

Written Monday Nov 23, 2026, about 9am Mountain. Paste the prompt at the bottom into a fresh Claude Code session opened in this folder.

## Why this handoff exists

Three sessions have worked on this engine in two days. Two of them reviewed it this morning and reached the same conclusion from different directions. I want one fresh session to read everything, reconcile it, and give me a single plan. I'm losing early-week value while this is unsettled, so the plan has to say what happens today first.

Read `CHARTER.md` before anything else. It says what the engine is for, defines the five lanes, and sets the rule that is supposed to stop it drifting.

## Where things stand

Both reviews agree on this:

- **Spreads in all three sports are a price check.** The fair line is Pinnacle's line. The engine's own ratings were switched off because every version tested lost to the closing line. A side is flagged only when Wagerhouse differs from Pinnacle or the agent enters an injury adjustment, and the agent then passes because a price gap isn't a reason.
- **Totals:** only the wind model, only outdoor NFL games, capped at a half-unit Conditional.
- **Props:** NFL and NBA prop models exist and are scoring props against Pinnacle. Neither can issue a pick until 300 props are graded and shown to win.
- **College football is running.** It priced 66 games this morning and passed on both sides it flagged.
- **Nothing has been graded.** The engine's record is 0-0 and starts this week.

Models tested against the closing line so far:

| Model | Result | Write-up |
|---|---|---|
| Sides from market ratings and public systems | Failed (2,663 games) | `docs/research/04-evaluation.md` |
| Sides from play-by-play ratings | Failed (918 games) | `docs/research/03-sharp-style-handicapping.md` |
| Totals from pace and efficiency | Failed (918 games) | `docs/research/02-totals-model.md` |
| First-half scoring habits | Failed (2,111 games) | `docs/research/05-model-first-picks.md` |
| Early-week openers from ratings | Failed (about 3,600 games) | `docs/research/09-early-number-openers.md`, if it has been written |
| Wind on totals | Passed, weaker since 2024 | `docs/research/05-model-first-picks.md` |

## Problems found this morning

From the other session's review:

1. **The card says something false.** Its header says the fair line is "55% Pinnacle, 45% model". It is 100% Pinnacle.
2. **The public-ratings column is blank** on every game. The weekly file of about 50 computer ratings isn't updated early in the week, which is exactly when I want it.
3. **The "DraftKings open" column misleads.** For the NFL it shows a lookahead line from May, so every line looks like it moved a mile.
4. **The engine's picks are not being graded.** No grades are recorded.
5. **A pick was reported wrong.** The Bengals at Commanders Under was said to stand when the engine had already moved it to Pass.

From my review in the session that built the first version:

6. **Reads sometimes fail on a database lock.** The hourly read, the NBA watcher that runs every 10 minutes and the research runs overlap and block each other. The error is in `~/Library/Logs/betting-engine/poll.err.log`.
7. **Several sessions were editing the project at once.** There was uncommitted work this morning (`src/engine/models/openers.py`, `tests/test_openers.py`, changes to `src/engine/cli.py`, today's cards). Run `git status` first. If you find uncommitted work you did not write, do not discard it; tell me.
8. **The research agent estimates injury point values by judgment,** and an edge that exists only because of its own estimate keeps getting flagged and then passed.

## Ideas on the table

- **Five lanes,** each with its own model, status, record and Telegram topic. The charter now defines them. The split has not been built.
- **Leans.** A second tier of picks, labelled unproven: the agent's best handicapped opinions per lane, early in the week, each with a number, a "don't bet past" limit and a written handicap, at a quarter unit or on paper, all graded. I have not decided yet. Tell me what you'd do and why.
- **A college opener test with real outside ratings.** The weekly ratings file lists each game's opening line next to about 50 rating systems. It is the one input not built from the market's own lines. If past seasons of that file exist, test whether the average of those systems predicts where college openers go. That could make the college lane a real model.
- **Wagerhouse's small markets.** First-quarter, first-half and team-total lines and props are now being logged. Nobody has yet measured whether Wagerhouse is loose there against Pinnacle. That measurement may matter more than any model.

## What I want from you

1. **Read first.** `CHARTER.md`, `CLAUDE.md`, every file in `docs/research/` and `docs/decisions/`, the three handoffs in `docs/handoffs/`, `config.yaml`, today's cards in `docs/cards/`, then the code in `src/engine/`. Run `git status`, `git log`, `uv run pytest` and `uv run engine board`.
2. **Reconcile.** Where the two reviews agree, say so in a line. Where they differ or where either is wrong, say which is right and show the file that proves it.
3. **Give me one plan,** written to `docs/research/10-plan.md`, in this order:
   - **Today.** What can produce useful output for this week's games before the value is gone, with what exists right now. Be concrete about what I'd receive and when.
   - **This week.** Fix the false and misleading output, split into the five lanes, start grading, fix the database lock, build `engine status` from the charter's drift guard.
   - **Next.** Which tests to run, in order of expected payoff, and what each would unlock. Include the college opener test and the Wagerhouse small-market measurement.
   - **A recommendation on Leans,** with the case for and against.
   - **What you would stop doing.**
4. **Check the plan against the charter.** For each lane, say what it will evaluate after your plan, and what it still won't.
5. **Stop for my approval** before changing code. The only exception: if something is sending me false information right now, say so at the top and tell me the one-line fix.

## Rules

- The locked decisions are in `CHARTER.md`. Don't reopen them.
- Plain English. I'm technical but not a quant.
- A claim about the engine needs the file it came from. A claim about the world needs a link.
- No look-ahead in any test, and hold out seasons for anything tuned.
- Don't print or store logins. They live in `.env`.
- You are the only session that should edit code from here. If you see signs another session is still working (new uncommitted changes appearing), stop and tell me.
- Keep the first summary short. Lead with what I'd get today.

---

## Prompt to paste into the fresh session

```
Read CHARTER.md first, then docs/handoffs/2026-11-23-consolidate-and-plan.md, and do what the handoff says.
Run git status before anything else and tell me if there is uncommitted work you did not write.
Reconcile the two reviews, then write one plan to docs/research/10-plan.md that starts with what I can get
today for this week's games. Stop for my approval before changing code.
```
