# Handoff: review the charter (written Monday Nov 23, 2026, night Mountain)

Paste the prompt at the bottom into a fresh Claude Code session opened in this folder. Set `UV_PROJECT_ENVIRONMENT=.venv.nosync` in every shell.

## Why this exists

In one day this project went through four framings: a price checker, a handicapping playbook, real money on everything, paper on everything
but teasers (decision 0025), and back to real money with Telegram as the source of truth (decision 0026). Two sessions edited the code at
the same time, and decisions 0025 and 0026 reversed each other within hours. Kylor's words tonight: "the idea is telegram is the place where
i use this whole model to place the bets you find, that is the source of truth." He wants one session to read the charter end to end and
tell him whether it says what he wants, so the next session builds from the right rules.

**The charter's facts were corrected tonight (commit 43e3932) without touching any locked decision.** Your job is the judgment, not the
facts: does the charter describe the product Kylor wants, are its rules consistent with each other and with how the engine actually
behaves, and what should change. **Do not edit `CHARTER.md`, code or config.** Propose; Kylor decides.

## Read, in this order

1. `CHARTER.md` (the subject), then `PLAYBOOK.md`, then `CLAUDE.md` (the build spec; older and partly stale, e.g. its picks section still
   describes a 55/45 Pinnacle blend that has been off since Nov 22).
2. Decisions `docs/decisions/0018` to `0026`, especially `0025` (paper) and `0026` (reversal).
3. `docs/research/18-model-evaluation.md` (the independent evaluation that recommended paper) and `14-deep-review.md` (the first review).
4. What Kylor actually sees: `docs/lanes/STATUS.md`, `docs/lanes/TRACKER.md` (and `tracker.html` if you open it), today's
   `docs/cards/*-playbook.md`, and `config.yaml` (`telegram.send_kinds`, `playbook:`, `teasers:`, `lanes:`).
5. The research agent's instructions: `ops/agent_prompt.md` and `ops/agent_prompt_{nfl,college,nba}.md`.
6. `git log --oneline | head -40` to see how the day went.

## Questions the charter should answer, and where it may not (check each; take nothing here as settled)

1. **Telegram as the source of truth.** Is every bet the model wants placed actually reaching Telegram, with a stake and a limit? Should
   Telegram also carry paper or C picks clearly labelled "$0, tracking only", or would that dilute it? Is the morning recap enough?
2. **Two pick paths.** The old research-agent path (Bet / Conditional on unpriced news against Pinnacle) and the playbook path (our own
   number, A/B/C) both still run and both can message. Should one be retired? Which one does Kylor think he is following?
3. **Real money without evidence.** Decision 0026 stakes lanes research 18 found no edge in. The charter records the choice. Does it also
   need an explicit bankroll (config says $2,500; a $50 teaser fits about $3,300), a weekly exposure cap, and a stop rule Kylor agrees with?
   Is the 10-unit stop per sport right?
4. **The drift guard.** Rules 2 and 3 used to promise Telegram messages; Telegram is now bets-only, so a switched-off model only shows up
   in a session summary. Is that acceptable to Kylor, or should a lane change get one Telegram line?
5. **"One session owns the code."** It was broken today (two sessions changed code at once). Should it be enforced (a lock file the
   scheduled jobs and sessions check), and should decisions get a rule like "the newest decision note wins, and it must name the one it
   replaces"?
6. **The locked line "Wagerhouse is a soft book; that is probably where my edge is."** Research 12, 14 and 18 found Wagerhouse is not soft on
   price (it charges more juice than Pinnacle) and may only be slow. It is Kylor's locked decision; say what the evidence shows and let him
   decide whether the wording changes.
7. **What is obsolete:** the Stage 0/1/2 readiness rules (`docs/lanes/READINESS.md`, decision 0012) no longer gate playbook picks; paper
   Leans (decision 0010) overlap with C picks; the STALE NUMBER alerts overlap with the playbook. Keep, merge or retire?
8. **Charter vs PLAYBOOK vs CLAUDE.md.** Three documents describe how picks work. Which one owns what? Propose a split so they cannot
   disagree again (for example: CHARTER = purpose and locked rules; PLAYBOOK = how a pick is chosen; CLAUDE.md = how code is built), and
   list every stale sentence in CLAUDE.md.
9. **What "working" looks like.** Rewrite this section as checks a session can run (for example: "every staked pick on Telegram has a row in
   the tracker"; "every lane's last pick is less than N days old or the lane says why").

## Deliverable

One document, `docs/research/19-charter-review.md`, that starts with a half-page plain-English answer to **"does the charter say what I
want, and what has to change?"**, then:
- a redline: the charter's current text next to your proposed text, section by section, each change with one line of why;
- a short list of yes/no questions for Kylor, one per judgment call, in plain words with names inline (no reference numbers);
- the stale sentences in `CLAUDE.md` and `PLAYBOOK.md`, with the fix for each.

Rules: plain English; Kylor is technical but not a quant, and reads on his phone, so the first line says what he needs to decide. Do not
edit `CHARTER.md`, `PLAYBOOK.md`, `CLAUDE.md`, code or config; propose only. Commit your document; do not push.

---

## Prompt to paste into the fresh session

```
Read CHARTER.md, PLAYBOOK.md and CLAUDE.md, then docs/handoffs/2026-11-23-charter-review.md, and do what it says.
Run git status and git log first and tell me if there is uncommitted work you did not write.
Set UV_PROJECT_ENVIRONMENT=.venv.nosync in every shell.

This is a review of the charter, not of the model. Today the project changed direction several times and two
sessions changed code at once. I want to know whether the charter now says what I want: Telegram is where I get
every bet this model finds and I place them from there; the tracker grades those picks against what I bet.

Answer the nine questions in the handoff. Write docs/research/19-charter-review.md: start with a half-page answer
to "does the charter say what I want, and what has to change?", then a section-by-section redline (current text,
proposed text, one line of why), then a short list of yes/no questions for me in plain words, then every stale
sentence in CLAUDE.md and PLAYBOOK.md with its fix. Do not edit the charter, the playbook, the spec, code or
config; propose only and wait for my answers.
```
