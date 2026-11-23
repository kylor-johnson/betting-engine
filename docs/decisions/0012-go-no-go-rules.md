# 0012: When real money goes on an engine pick (2026-11-23)

Kylor: "i dont want to just start betting until it's in a place for us to be comfortable." These are the rules, generated each time from the record by `engine ready` (`src/engine/readiness.py`, thresholds in `config.yaml` `go_live:`, output in `docs/lanes/READINESS.md`, shown on the board and in `engine status`).

**Stage 0, observe (now).** No money. Everything is logged and graded.

**Stage 1, half unit ($12.50) on engine Bets only.** All must hold: 3 full weeks since the settings that decide picks last changed; 10 graded Bets and Conditionals since then; 5 of them with a Pinnacle closing line; average closing-line value at least zero; every pick has a "don't bet past" number; every finished pick graded. If fewer than 10 picks exist after three weeks, the clock keeps running; the bar is not lowered. At the stake: re-check the Wagerhouse number just before placing, skip if worse than "don't bet past", at most 2 units staked in a week, log it with `engine bet add`.

**Stage 2, the full $25 unit.** 100 graded picks and an average closing-line value above zero (the sizing review `CLAUDE.md` already requires).

**Never bet at any stage:** Conditionals (including wind totals) until the wind test on stored forecasts has run, paper Leans until 50 are graded with average closing-line value above zero, props until a model passes its gate, anything past its limit.

**Pause (back to Stage 0):** average closing-line value below -0.5 points once 25 picks have a closing line; down 10 units since Stage 1 began; any pick bet past its limit or with no limit; a change to the pick-deciding settings restarts the clock. A code-only change shows up as a new rule version and does not restart it automatically.

**Why these numbers.** They are a floor, not proof. Ten picks cannot show an edge; they show the process runs (limits, grading, alerts) and that the closing line is not moving against us. The stake is half a unit because the engine's only evidence until 100 picks is that closing-line value is not negative. Results in units are shown but never gate anything. Kylor may change any threshold; write a note when he does.
