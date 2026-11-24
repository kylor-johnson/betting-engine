# Handoff: one final audit of tonight's rebuild (written Mon Nov 23, 2026, late night Mountain)

Paste the prompt at the bottom into a fresh Claude Code session opened in this folder. Set `UV_PROJECT_ENVIRONMENT=.venv.nosync` in every
shell.

## Why this exists

On Nov 23 one session reviewed the charter (research 19) and then, on Kylor's "fix it", "do it" and "keep going", rebuilt how picks reach
him. Decisions 0027 to 0032 in one evening:

- **0027** one pick path (the playbook); Telegram = staked picks, the 9am recap, system lines; CHECK-cleared picks staked; NFL stop counts
  teasers; review line; edge split (price against handicap) on every pick; readiness stages and paper Leans retired; session lock
  (`engine lock`); charter, playbook and CLAUDE.md split by ownership.
- **0028** units only (no dollar cap, no bankroll); lane-change messages compare money state, inputs and models, not table wording.
- **0029** sourced news in `adjustments.yaml` moves the playbook number by the part Pinnacle has not priced (every sport); college news picks
  staked in a shown-only lane.
- **0030** `engine check` (daily, one Telegram line on failure), "News on this card" and `engine news`, the sport parity table and rule,
  NBA news picks.
- **0031** college quarterback value measured (research 21, about 3.5 points); tracker page rebuilt after picks and hourly at night.
- **0032** college wind totals failed on day-before forecasts (research 20: 57-53 at a 1-point edge, 2024-2026); nothing switched on,
  the wiring prepared in case it passed was removed, the college weather parity cell says failed.

Kylor's standing complaints that this work answers, in his words: Telegram "is the place where i use this whole model to place the bets you
find, that is the source of truth"; "CFB has been HEAVILY neglected"; "we keep losing focus between all three sports"; keep tracker.html up
to date. One session built and reviewed all of it, so it has not had an outside read. That is your job.

## Read, in this order

1. `CHARTER.md`, `PLAYBOOK.md`, `CLAUDE.md` (the three must not disagree; each says what it owns).
2. `docs/research/19-charter-review.md` (what was proposed), then decisions `docs/decisions/0027` to `0032` (what was done).
3. `docs/research/20-college-wind.md` and `21-college-qb-value.md`.
4. `git log --oneline 8056a23..HEAD` and the diff of `src/` over that range. The main files: `src/engine/picks/playbook.py`
   (`apply_news`, `is_news_pick`, `_paper_or_staked`, `down_units`, `week_staked`, `edge_split`, `lane_events`, `news_section`),
   `src/engine/picks/teasers.py`, `src/engine/picks/agent.py`, `src/engine/poll.py` (`refresh_tracker`, the daily check, the lane events,
   the tracker rebuild after picks), `src/engine/lanes.py` (`lane_state`, `structure`, `diff_text`, the parity table),
   `src/engine/checks.py`, `src/engine/session_lock.py`, `src/engine/gitsync.py`, `src/engine/bets/tracker.py`, `src/engine/models/college_qb.py`,
   `src/engine/models/college_wind.py`, `src/engine/models/weather.py`.
5. What Kylor sees: `docs/lanes/STATUS.md` (lane table and parity table), `docs/lanes/CHECKS.md`, `docs/lanes/TRACKER.md`, `tracker.html`,
   today's `docs/cards/*-playbook.md`, `config.yaml` (`telegram`, `playbook`, `teasers`, `parity`, `agent`, `leans`).
6. The research agent's instructions: `ops/agent_prompt.md` and `ops/agent_prompt_{nfl,college,nba}.md`.

## What to audit (take nothing here as settled; check each against the code and the live database, read-only)

1. **Telegram is the truth.** Trace every `telegram.send` call. Can anything with a $0 stake go out as `bet`? Can a staked pick fail to go
   out (CHECK-cleared, news picks, teasers, caps, stop)? Do the old path's messages, stale alerts, NO BETS and lane tables stay off unless
   their kind is listed? Does `engine check` catch a miss?
2. **The news path (0029) is the riskiest change.** `apply_news` adds the agent's points at full size after the blend, only for the part
   Pinnacle has not moved since `news_at`. Look for double counting (news the script or props already see; an entry for news older than the
   Pinnacle history; a side entry and a total entry for the same news), wrong signs (home/away), team-name matching misses (`espn.norm`
   against Wagerhouse names), and whether a news pick in a shown-only lane can be staked on a stale entry. Is the 3.5-point college number
   (research 21) used consistently in the guides?
3. **Money.** Units by sport, A/B stakes, one unit a game, per-lane caps, the NFL stop counting teasers (`down_units`, `teaser_profit_units`:
   push handling, units), the weekly cap off (`weekly_cap_dollars: 0`), the review line. Any path where real money is recommended that the
   charter does not allow?
4. **Research quality.** Research 20 (college wind) and 21 (college QB value): look-ahead, leakage, sample, the claims each makes against its
   numbers. Re-run the scripts if a number looks wrong (`uv run python -m engine.models.college_wind`, `... college_qb`; both use cached data).
5. **The drift guard and parity.** Does a real lane change produce one short Telegram line and wording changes none? Is the parity table
   complete and true for each sport (open each cited research note)? Is anything built for one sport tonight missing its line for the other
   two?
6. **Docs against code.** Every sentence in CHARTER.md, PLAYBOOK.md, CLAUDE.md, README.md and the agent prompts that describes behaviour:
   is it what the code does? List each false sentence with its fix.
7. **Operations.** The lock (`engine lock`, auto-commit skip, stale after 4 hours), the tracker refresh outside read hours, the daily check
   (does it run before the 8:15 research run and page Kylor for something the agent will fix?), DuckDB lock contention between the hourly
   read, fast reads, the NBA watcher and research runs.
8. **Tests.** `uv run pytest`. Are the new tests testing behaviour or just echoing the code? Which risky path has no test?

## Deliverable

`docs/research/22-final-audit.md`: first line says what Kylor needs to decide; then a half-page verdict ("is what was built tonight what he
asked for, and is it safe to run with real money tomorrow?"); then findings ranked by money at risk, each with file and line, what happens,
and the fix; then false doc sentences with fixes; then a short yes/no list for Kylor in plain words. Fix only what is plainly a bug with no
judgment call (a wrong sign, a crash, a false sentence) after `uv run engine lock take "final audit fixes"`, with a test, and list each fix.
Anything that changes money, what reaches Telegram, or a locked rule: propose only. Commit, release the lock, and push to
`kylor-johnson/betting-engine` (Kylor asked for the GitHub repo to stay current). Never commit `.env`.

Rules: plain English, Kylor is technical but not a quant and reads on his phone. Start with `git status` and `git log`; generated card and
tracker files from scheduled runs are not unfinished work.

---

## Prompt to paste into the fresh session

```
Read CHARTER.md, PLAYBOOK.md and CLAUDE.md, then docs/handoffs/2026-11-24-final-audit.md, and do what it says.
Run git status and git log first and tell me if there is uncommitted work you did not write (generated cards and tracker files from the
scheduled runs don't count). Set UV_PROJECT_ENVIRONMENT=.venv.nosync in every shell.

This is one final outside audit of everything built on Nov 23 (decisions 0027 to 0032). One session built and checked all of it; I want a
fresh read before real money runs on it. The bar: Telegram is where I get every bet this model finds and I place them from there; the tracker
grades those picks against what I bet; college and NBA get the same care as the NFL.

Write docs/research/22-final-audit.md as the handoff says. Fix only plain bugs (with a test and the code lock); propose anything that touches
money, Telegram or a locked rule. Commit, release the lock, push to GitHub, and give me the verdict and the yes/no list.
```
