# Handoff: review the college football model (written Tue Nov 24, 2026)

Paste the prompt at the bottom into a fresh Claude Code session opened in this folder. Set `UV_PROJECT_ENVIRONMENT=.venv.nosync` in every
shell.

## Why this exists

Kylor, Nov 24, after asking why college produces nothing: "i feel like we did a lot of work on the nfl model and it was neglected for ncaa
if we're just using news". He wants three things:

1. A review of the college model against everything the NFL model got and college did not.
2. Deep research on how successful college bettors and public raters handicap, and where their methods differ from the NFL for a reason.
3. A POV: where the college model should change, what is missing from the NFL work, and what college-specific methods should be added.

Earlier he said "CFB has been HEAVILY neglected" (Nov 23). That complaint is still open.

## What is already established (checked Nov 24, verify anything you lean on)

**The two models are not built the same.**

| | NFL (`src/engine/models/script.py`, 443 lines) | College (`src/engine/models/college_script.py`, 153 lines) |
|---|---|---|
| Data | nflverse play-by-play, 2015-2026 | CollegeFootballData cached JSON: games, lines, passing, venues only |
| Offense and defense form | EPA per play, success rate, points per drive | Points scored and allowed per game |
| Pace | Drives per game, own and allowed | None |
| Play calling | Pass rate over expected in neutral game states | None |
| Schedule | Each game corrected for the opponent's form (research 17) | Opponents' points form as a regression input only |
| Situation | Home, a different starting QB, wind and rain at kickoff | Home, neutral site |
| Last season | Counts as 3 games | Counts as 2 games, less from week 3 |
| Tested additions | Research 17: schedule adjustment, outlier half weight, injury clusters, referee totals | None beyond wind (research 20, failed) |
| Props | Live and staked | None (Pinnacle college props not read) |
| Teasers | Wong teasers, staked | Tested: 71.1% legs, below break-even (research 14) |

The college docstring says "the free tier has no play-level data, so there is no pace or pass-rate term". `PLAYBOOK.md` section 5 says
college pace and efficiency come "from CollegeFootballData (free tier: lines, scores, basic stats, PPA)". **These contradict each other.**
Check what the CFBD free tier really gives today (plays, drives, PPA, advanced season and game stats, returning production, talent
composite, recruiting, SP+ / FPI / Elo ratings endpoints) and its call limit. `CFBD_API_KEY` is set in `.env`; never print it.

**Neither model beat the market. The difference in staking is a choice, not a result.**

- NFL: the fitted weight on our number fell to zero for 2024-2026 and the blend improved squared error by about 0.1% (research 15). Kylor
  chose to bet it anyway at the playbook's starting weights to build a record (decision 0019).
- College: weight about zero in 2023-2026 (research 16), so full-game picks were made shown only. The game totals were slightly better
  (51.2% at a 4+ point disagreement, 605-576), noted as "a lead to watch".
- So college got a thinner model and a stricter rule. Part of the review is whether that asymmetry is right.

**College work already done (do not repeat it, build on it):**

- Research 14, section 2c: about 60 public rating systems (the Massey composite set) against the close, 8,283 games: failed. One hint:
  in weeks 1 to 4 since the transfer portal (2021-2025), where the systems' average was 2+ points off the close, the side they liked
  covered only 188-251. It is pre-registered as a 2027 forward test (research 14, item 11) using CFBD returning production and transfers.
  Find out which systems were in that set. If SP+, FPI or FEI were, testing them alone again is mostly repetition.
- Research 20: college wind totals failed (decision 0032).
- Research 21, corrected by research 22: a starter ruled out before the game is worth about 4 points, about 5 for a weak passer. About 1
  point of it moves after the opener. That is more than an NFL starter (2.5 to 2.7). So "news counts less in college" is not true for QBs.
- Research 14: in the NFL, the official injury report including practice participation failed as a model input (2,389 games). Non-QB
  injuries were not measured for college at all.
- College news picks (decision 0029) and the college agent guide (`ops/agent_prompt_college.md`) are live. This week's CHECK verdicts in
  `docs/cards/decisions/2026-11-24-college-checks.yaml` show how holds look.

## Your job, in order

### 1. Parity inventory (code and data, no opinions yet)

For every NFL input, test, lane and agent instruction, say whether college has it, has a weaker version, or lacks it, and whether the data
exists free. Sources: both model files, `PLAYBOOK.md`, `config.yaml` (`playbook`, `parity`, `lanes`), `docs/lanes/STATUS.md` (parity
table), research 15 to 18, both agent guides. Settle the CFBD contradiction above with real API calls (a few, not hundreds).

### 2. Deep research: how college is handicapped well

Start from the list Kylor pasted (below). For each: what the method actually uses, what is published versus claimed, and what evidence
exists that it beats the **closing line**, not just ranks teams. Read the primary sources, not summaries. Mark every claim [DATA], [CLAIM]
or [OPINION], with a link, as research 14a and 18a do.

Then answer the question that matters: **where does college differ from the NFL for a structural reason?** Candidates to check, not
conclusions:

- 130+ FBS teams and much bigger talent gaps; FCS games; blowouts and garbage time distort per-game points (which is all our model uses).
- Tempo varies far more than in the NFL, so per-play efficiency times plays should beat points per game.
- Roster churn: transfer portal, returning production, coaching changes, early-season priors.
- Market efficiency by tier: is the close weaker for Group of 5 games, early-week numbers, small conferences, or late-season games with
  motivation questions? Wagerhouse limits and which games it posts matter here.
- Home field by venue, travel, altitude, rivalry and letdown spots, bowl opt-outs and portal exits.
- Key numbers are flatter than the NFL, so a point is worth about 2% instead of 3% (research 14). That changes edge sizes and teasers.

Kylor's list (pasted Nov 24; treat it as a starting point to verify, not as facts):

<pasted_list>
Publicly documented models: Bill Connelly's SP+ (ESPN; the "Five Factors": efficiency, explosiveness, field position, finishing drives,
turnovers; book "Study Hall"). Brian Fremeau's FEI (drive-based efficiency). Kenneth Massey's ratings. Wesley Colley's Colley Matrix
(paper). Ed Feng's The Power Rank (opponent and pace adjustments). Jeff Sagarin's ratings including "predictor" (Elo-style and points-based,
full formula not published). FiveThirtyEight's college football Elo / forecast (less active later). ESPN FPI (documented by ESPN Stats &
Info).
Handicappers who share part of their process: Phil Steele (returning starters, experience, turnover margin regression). Dr. Bob (Bob Stoll,
statistical modeling, high level). Billy Walters, memoir "Gambler" (computer-model operation, no formulas). Lem Banker (philosophy, line
shopping).
Background: "Who's #1?" by Langville and Meyer (the math of rating systems). Stanford Wong, "Sharp Sports Betting".
Caveat from the list: the truly profitable models are generally not published; most public models rank or predict rather than beat the
spread; tout records are self-reported and hard to verify.
</pasted_list>

Project rule: a named handicapper is an example to red-team, never an input and never a reason for a pick (Kylor's standing instruction).
Dr. Bob has a long publicly tracked record; check what is actually verifiable.

### 3. Test before you recommend

Anything you recommend as a model change needs a walk-forward test first, with the same method as research 15 and 16: fit on earlier seasons,
weight fitted one season back, report squared error against the close and the record at Wagerhouse-like numbers where we disagree. Write the
rule down in the research note **before** you look at the test season. Slicing after looking makes a hypothesis, not a result (research 14
2c is the example). Likely first tests, if the data is free:

- Per-play efficiency (PPA or EPA, success rate) times tempo, in place of points per game.
- Garbage time removed (CFBD flags it, or use score and quarter).
- Returning production, talent composite and the transfer portal as priors, with last season faded on a schedule.
- Market tier: does a weak model still win where the close is weak (Group of 5, early week, game totals)? This is where college may
  differ most from the NFL.

Report failures as plainly as passes. Eight free-data model tests have failed so far (research 14); the honest prior is that the next one
does too. A failed test that rules out an idea is useful.

### 4. Write the POV

Write `docs/research/23-cfb-model-review.md`. The first line tells Kylor what to answer, in plain English (he reads on his phone). Then:

- **Where college fell behind the NFL**, ranked by expected value, with the evidence for each.
- **What college handicappers do differently, and why**, kept only where the reason is structural and testable.
- **What you tested and what it showed.**
- **A yes/no list for Kylor**, each item with cost (hours) and a kill number, like research 14's plan table. Include whether college should
  be staked at the playbook's starting weights the way the NFL is (decision 0019), and what that would risk.

Do not change `src/`, `config.yaml`, `ops/`, `CHARTER.md` or `PLAYBOOK.md` until Kylor says yes. A rule change needs a decision note, and
the same commit updates every document that quoted the old rule (CLAUDE.md). Test code belongs in `src/engine/models/` as a test-only
module (like `college_wind.py`), and adding it needs the lock.

## Rules (from CLAUDE.md, CHARTER.md)

- `uv run engine lock take "why"` before editing `src/`, `ops/`, `config.yaml`, `adjustments.yaml`, `CHARTER.md` or `PLAYBOOK.md`;
  `uv run engine lock release` after committing. The engine runs on a schedule in the background; don't fight it.
- Never commit `.env` or print anything from it. The engine never places bets.
- Plain English for Kylor: no decision or research numbers without saying what they were. Units, not dollars.
- Keep `uv run pytest -q` green (264 tests as of commit 77a4a43). Commit and push when done, with the attribution line the session gives.

## Prompt to paste

```
Read docs/handoffs/2026-11-24-cfb-model-review.md and do it. Kylor thinks the college football model was neglected next to the NFL one
and wants (1) a parity inventory, (2) deep research on how successful college handicappers and public raters work and where college
differs from the NFL for a structural reason, (3) walk-forward tests of the best free-data ideas, written down before you look, and
(4) a POV in docs/research/23-cfb-model-review.md with a yes/no list. Read CHARTER.md, PLAYBOOK.md and CLAUDE.md first. Don't change
src/, config.yaml, ops/, CHARTER.md or PLAYBOOK.md until Kylor says yes, except test-only model code under the lock. First line of the
note tells Kylor what to answer, in plain English.
```
