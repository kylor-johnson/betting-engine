# Handoff: check that every sport and bet type runs on today's rules (Nov 24, 2026, evening)

**What to do:** check that every sport and bet type the engine touches runs on the rules decided today (decisions 0036 and 0037). Fix the
plain gaps under the lock, then commit and push. Bring Kylor only the items marked **Kylor decides**, each as one plain yes/no question with
the number behind it.

Read first:
- `CHARTER.md`, `PLAYBOOK.md`, `CLAUDE.md`.
- `docs/decisions/0036-audit-24-yes-list.md` and `docs/decisions/0037-nba-pregame-half-hourly-reads.md`.
- `docs/research/24-full-audit.md` and `docs/research/24b-props-variant.md`.

Rules:
- Every shell sets `UV_PROJECT_ENVIRONMENT=.venv.nosync`.
- Open the database read-only: `engine.odds.snapshots.connect(Path(...), read_only=True)`, which takes a `Path`, not a string.
- Take `uv run engine lock take "..."` before editing `src/`, `ops/`, `config.yaml`, `adjustments.yaml`, `CHARTER.md` or `PLAYBOOK.md`.
- Units, never dollars, in anything Kylor reads.
- A named handicapper is never an input.

## What changed today

The live jobs run from the working tree, so all of it is live.

- **Decision 0036 (Kylor's yes to research 24, items 1-13):**
  - Props blend weight: 0.15 NFL, 0.25 NBA.
  - NBA spreads and totals are shown only, and NBA news picks are off.
  - News counts toward the CHECK distance and is capped (NFL 3, college 5.5, NBA 4 points).
  - Pinnacle's earliest read in the 12 hours before the news is the baseline for "already priced".
  - Our number is built on Pinnacle's line with its price lean taken out (`pin_fair`; picks issued before 23:00 UTC Nov 24 keep the old
    comparison).
  - The NFL script is fitted without actual weather and uses a forecast-wind term.
  - NBA team-total curve: 11.5.
  - Stops and the review line count from Nov 23.
  - Units first everywhere.
  - Reads run to 9pm, and the NBA watcher also runs at 6:30pm.
  - A pick Pinnacle has moved against is demoted before one pick per game is chosen.
  - A pick that is paper only because of the one-unit-a-game rule takes no cap slot.
  - Props pay at the limit price, with void rules.
  - Three paper lanes: L1, F1 and D1b.
- **Commit a5453f3:** the CANCELLED prop message says when Pinnacle has not moved.
- **Decision 0037 (commit 2b44f19):** full reads every 30 minutes in the 3 hours before an NBA tip (`read_pregame_hours: {NBA: 3}`).
  Checked live: the 7:03pm Nov 24 read ran.

## Job 1: a grid of sport × bet type, one row each, checked against the code (not the docs)

Rows:
- NFL, College and NBA, each with: spread, total, team total and moneyline (where issued).
- NFL props and NBA props.
- NFL teasers.
- The paper lanes: L1 (all three sports), F1, D1b, college openers, and NFL and NBA news props.

For each row, confirm from the code path that issues and grades it:
1. **Weight and edge settings:** the weight against Pinnacle, the minimum edge and the CHECK distance in force (`playbook.settings(cfg, sport)`),
   and whether they match 0036.
2. **Market reference:** does it use `pin_fair` (sides, totals, team totals), or Pinnacle's no-vig chance (props)? Any place still on the raw
   line is a miss. Check `cancel_reason`, `limit_value`, the CANCELLED path, the paper lanes and the card text.
3. **Stake path:** staked, shown or paper, as 0036 says. NBA full game must never send a `bet` message, and NBA news picks must be off.
4. **Caps and one-unit-a-game:** `COUNTS_FOR_CAP` is applied here.
5. **Grading:**
   - closing-line value is computed;
   - props pay at `limit_price`;
   - voids follow `VOID_AFTER_HOURS`;
   - the result reaches the tracker, `TRACKER.md`, `tracker.html` and the Vercel page (only sent picks, never Kylor's own wagers).
6. **Timing:** a read runs close enough to the start to issue, CANCEL and take a closing price. College evening games and NFL
   Thursday, Sunday night and Monday night games count here, not only NBA.
7. **The card and the Telegram text say the same thing as the code.** Generated sentences come from config.

Write the grid to `docs/research/25-tuning-check.md`, with a verdict per row: OK / fixed (commit) / Kylor decides.

## Known gaps to check first (found Nov 24; not fixed)

1. **Stale text about the NBA watcher.**
   - `src/engine/picks/nba_news.py` line 3 still says it runs "three times a day (10:00, 15:00 and 17:00)".
   - The parity table in `docs/lanes/STATUS.md` (built by `engine status`) says "watcher at 10am, 3pm, 5pm; fast reads before first tip".
   - Both should say 10am, 3pm, 5pm and 6:30pm, plus half-hourly full reads in the 3 hours before any tip (0037).
   - Find where that cell's text is built and fix it at the source.
2. **NBA fast reads follow only the day's first tip** (`burst.py` `before_first_start`). On Nov 24 that meant none after 5:15pm for the 8pm
   games. Decision 0037 covers picks, but the stale-number scan and the research trigger on change still skip late games. This is a plain fix
   only if it stays within `max_reads_per_day` (NBA 25). Otherwise **Kylor decides**.
3. **The props weight change hit picks issued under the old weight.**
   - John Collins over 1.5 threes was sent at weight 0.5 and cancelled at 0.25 the same day. Pinnacle had not moved; the edge went from +4.6%
     to +1.1%.
   - Sides and totals have `FAIR_SINCE` so a rule change cannot cancel an older pick. Props have no equivalent.
   - Decide whether a prop's cancel test should use the weight in force when it was sent. This is a plain bug if it is the same principle as
     `FAIR_SINCE`. The note must say why.
4. **Props grading lag.** At the 7:33pm read the Pistons–Magic game was final and the team total graded, but Collins' prop did not grade. Find
   whether the box score was not posted yet or the prop lookup missed. Check it graded by the next morning.
5. **Unfixed plain bugs from research 24:**
   - the missed-read alarm fires only after 20 hours;
   - `down_units` swallows errors;
   - poll holds the database lock during network reads (this matters more now that NBA nights read twice an hour);
   - no CFBD cache fallback;
   - the dry-run temp database is never deleted.

## Job 2: Kylor decides (bring the number, not a recommendation dressed as a fact)

- **NBA props are staked, but the evidence is weak.**
  - On the paper suggestions (5%+ disagreement) the NBA props model is 71-72, −11.9 units.
  - Live staked NBA props: 1-2, closing-line value −3.0% on 3.
  - Research 24b found the best weight 0.15-0.20.
  - Ask whether NBA props should stay staked until the review line (−1.5% on 25 graded) decides, or go to paper now.
- **NFL props.** With true first reads, the best weight is 0.00 (24b). Live is 0.15 and 2-0, with closing-line value −2.1% on 2. Same
  question.
- **College props:** no lane. Is that still fine? The parity table says "planned".
- Anything Job 1 finds that changes a rule.

## Kylor's own bets, for context only (never inputs)

- Titans +15 and John Collins over 1.5 threes, both placed on the earlier model.
- An Orlando Magic team total **Under**, taken by mistake against the model's Over 105. The model's Over lost and his Under won.
- The tracker matches only same-side bets (`tracker._leg_matches`), so his Under counts as his own bet, not as following the model. Leave it.

## Finish

- `uv run pytest` must pass.
- Run `uv run engine status` and check the table against what changed.
- Commit to main, release the lock and push to `kylor-johnson/betting-engine`.
- Tell Kylor in plain English what each sport and bet type can and cannot do now, and list only the yes/no questions.
