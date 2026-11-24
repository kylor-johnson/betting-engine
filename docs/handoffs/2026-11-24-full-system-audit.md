# Handoff: the full audit — every part, why it is built that way, and outside research for all three sports (written Tue Nov 24, 2026, ~3:30pm Mountain)

Paste the prompt at the bottom into a fresh Claude Code session opened in this folder. Set `UV_PROJECT_ENVIRONMENT=.venv.nosync` in every
shell. This is a long job. Use subagents for the research legs and for reading code in parallel, but you write the verdicts yourself and
you check every number a subagent hands you before it goes in the note.

## Why this exists

Kylor, Nov 24: "create a fresh handoff for a new session to audit this model. it CANNOT be lazy, it needs to review EVERYTHING and then
also why it's that way and built that way." Earlier audits each looked at one evening's work (research 11, 14, 19, 22) or one sport (23).
Nobody has read the whole engine end to end since it was rebuilt around the playbook (decision 0018). In five days it went from
nothing to 35 decision notes, 115 commits and six staked lanes. Some of it was built in a hurry and fixed the same night.

He also pays for Warren Sharp's picks until **today, Nov 24**, and wants that material used one last time: as a red team for our model,
not as an input. His words: "THIS IS JUST ONE HANDICAPPER SO WE'RE NOT JUST TRYING TO DIRECTLY COPY (UNLESS WE SHOULD) BUT MEANT TO GIVE
THE OTHER AGENT A SENSE FOR FEEDBACK TO TUNE THE MODEL. THEN IT ALSO NEEDS TO DO DEEEEEEEEEP RESEARCH ON OTHER MODELS AND HANDICAPPERS VIA
SEARCHING AND THEN THE SAME FOR THE NBA." And: Wagerhouse does not offer some of Sharp's markets as straight bets (first quarter, half
team totals, most props), "but you should still suggest them if you see an edge so we can keep tuning the model."

Standing rules that do not change (memory and the charter): the engine never places bets; no paid data; units, never dollars, in what
Kylor reads; a named handicapper is an example to red-team, never an input and never the reason for a pick; plain English, first line
says what he needs to do.

## The four jobs

### Job 1. Audit every part, and say why it is that way

Go through the engine part by part. For each part, write down:

- **What it does**, from the code, not the docs.
- **Why it is built that way**: the decision note and research note behind it, quoted with their numbers. If no note explains it, say
  so: that is a finding.
- **Whether that reason still holds** today: the data it rested on, the sample size, look-ahead, whether a later decision undercut it,
  and whether the live record since agrees.
- **What breaks it**: the failure path, with file and line.
- **Verdict**: keep, fix (bug, no judgment call), change (needs Kylor's yes), or remove.

The parts, so nothing is skipped (check this list against `find src -name '*.py'` and add anything missing):

1. **Data in.** `odds/wagerhouse.py` (read-only client, the allowed-operation list, Eastern timestamps), `odds/espn.py`,
   `odds/derivatives.py` (Pinnacle quarters, halves, team totals, props), `odds/snapshots.py` (DuckDB locking), `picks/sources.py`
   (Pinnacle guest API, CFBD incl. the new `cfbd_advanced`), `picks/history.py`, `models/nba_data.py`, `picks/player_news.py`,
   `ops/reporters.yaml`, the official NBA injury PDF reader. Question for each: what happens when it returns junk or nothing?
2. **The numbers.** `models/script.py` (NFL), `models/college_script.py` (rebuilt today, decision 0034), `models/nba_script.py`,
   `models/props*.py`, `models/nba_props.py`, `models/nba_absences.py`, `models/college_qb.py`, `models/college_context.py`,
   `models/calibrate.py`/`calibration.py`, `picks/pricing.py`, `odds/math.py` (vig removal, push chances, key numbers). Re-run each
   model's walk-forward from its research note and confirm the number in the note (research 15, 16, 17, 18, 21, 23).
3. **Choosing a pick.** `picks/playbook.py` (grades, edge, `apply_news`, `is_news_pick`, caps, the stop, `cancel_moved`), `picks/teasers.py`,
   `picks/college_openers.py`, `picks/news_props.py`, `picks/nba_news.py`, `picks/agent.py` and the four agent prompts in `ops/`, the
   CHECK files the agent writes, `adjustments.yaml`.
4. **Money.** Units by sport, A/B stakes, caps per lane, stops counted from `live_since`, teasers inside the NFL stop, decision 0035
   (college and NBA full game staked today). Is every staked lane backed by a test it passed against the closing line? Write down, lane by
   lane, the evidence that it should have money on it and the evidence against.
5. **What reaches Kylor.** `alerts/telegram.py`, `alerts/rules.py`, `telegram.send_kinds`, `resend_undelivered`, the 9am recap, `checks.py`,
   `lanes.py` (lane events, parity table), `bets/tracker*.py`, `bets/public_page.py`, the cards in `docs/cards/`, `docs/lanes/*.md`.
6. **Grading and the record.** `picks/grade.py`, `clv.py`, `bets/audit.py`, `bets/history.py`, `reports/*`. Is every pick graded against
   the right close (Pinnacle, then the fallback)? Do pushes, cancels and voids come out right? Does every report print the luck range?
7. **Running it.** `poll.py`, `burst.py`, `stale.py`, the launchd plists, `session_lock.py`, `gitsync.py` (commits generated files; does
   not push, by Kylor's choice today), `checks.py`, `version.py`/rule versions. Timing: what runs when, on what day, in which sport, and
   what is missed on a Thanksgiving week or a Wednesday NFL game (there is one this week: Packers at Rams, Wed Nov 25).
8. **The documents.** CHARTER.md, PLAYBOOK.md, CLAUDE.md, README.md, the agent prompts and the 35 decision notes. Every sentence that
   describes behaviour: is it true? Do any two decisions contradict each other without the later one saying it replaces the earlier?
9. **Tests.** `uv run pytest` (273 at last count). Which risky paths have no test? Which tests only repeat the code?

Read the history first: `git log --reverse --format='%h %ad %s' --date=short`, then decisions 0001 to 0035 in order, then the research
notes 00 to 23 in order. The "why" for most parts is in those. `HANDOFF.md` is the original brief and shows what he asked for at the start.

### Job 2. Red-team Sharp's material (the last day of access)

Everything was saved while signed in, on Nov 24, to `data.nosync/raw/sharp/2026-11-24/`: text and full-page screenshots of the dashboard
(`dashboard-full-text.txt` has every write-up, including the ones hidden in pop-ups), the NFL odds/picks, props, first-TD, same-game
parlay, implied team totals, injury report, matchups, weather, referee, xFP, defence-vs-position and red-zone pages, the college picks page
and three college game write-ups (LSU-Tennessee, Georgia-South Carolina, UCLA-Michigan; some are stale), and his lifetime records page.
The Nov 22 dashboard copy is `data.nosync/raw/sharp/dashboard_2026-11-22.txt` (Week 11 props, waves 1-5). These stay outside git
(research 03: personal reference only). After today we cannot fetch anything new from his members' pages.

Do this:

1. **List every Sharp pick we have a copy of** (Nov 22 and Nov 24 files): market, line, price, book, units, time released.
2. **Grade each against Pinnacle**: Pinnacle's no-vig chance at release (from `derivative_snapshots` and `line_snapshots`, which already
   log Pinnacle's quarters, halves, team totals and props hourly), at the close, and the result. Closing-line value is the main test;
   the win-loss record on a sample this small is luck.
3. **Take his method apart.** For each type of pick, name the method (examples below), find the outside evidence for and against it, and
   say whether our engine already has it, tested it and dropped it, or never tried it:
   - Short trend records (the Packers write-up: "12-1 with extra rest since 2022", "13-0 in the series since 2004", McVay 0-5 against
     LaFleur). Red-team point: these are picked after the fact from thousands of possible splits. Find and cite the research on trend
     mining and multiple comparisons. Our rule already says "tests never look ahead".
   - Schedule-adjusted efficiency (opponents faced since week 4): our scripts use opponent-adjusted numbers; check how, and whether the
     window choice is ours or tuned.
   - "Computer totals" with half/full-game splits and team totals. His record page claims 739-431 lifetime on these (a claim, not data
     we can check). We already log Pinnacle's half and team-total lines: test whether our NFL script's half and team split, set against
     Pinnacle's derivative lines, finds anything (pre-register first; the old first-half model failed, research 04 and 05, find out why).
   - Props on role change (Jonah Coleman after a 24-carry game; Metcalf after an ejection). Our props model lagged both (see below).
   - Weather (his weather page), referees (his referee page): compare with research 18 and 20.
4. **Write what to tune**, ranked, each with the test that would decide it. "Copy him" is allowed only if a test on data he did not
   pick says so.

#### Today's picks, read against Pinnacle at 3:30pm MT Nov 24 (prices from our own logs)

Fair = Pinnacle's chance with the vig removed. Needed = the chance the quoted price needs to break even.

| Sharp's pick (released, ET) | Pinnacle now | Fair | Needed | Edge now | What the market did after release | Our model |
|---|---|---|---|---|---|---|
| Packers 1st quarter +0.5 -150 (Nov 24 11:39am) | +0.5 -156 | 58.9% | 60.0% | -1.1% | Was -146 Sunday, -155 before his release, -156 now: no move from him | NFL script makes the Rams 7.6 better against a 2.5 market (opposite side; shown, not staked) |
| Bills team total Under 26.5 -125 (Nov 23 7:27pm) | Under -129 | 54.3% | 55.6% | -1.2% | Under went -108 to -129 | Agrees on the game: our total 43.6 against 48.5 |
| Bills-Chiefs Under 48.5 | 47.5 | 51.5% at 47.5 | 52.4% | -0.9% now | Was 50 before he released, 48.5 at release, 47.5 now: he got a point | Agrees (3.1% edge, grade C) |
| Ravens-Texans 1st half Over 23.5 (Nov 24 1:57pm) | Over -117 | 52.1% | 52.4% | -0.2% | -109 to -117 within the hour | Disagrees: our full total 45.4 against 46.5 |
| Ravens-Texans Over 46.5 | 46.5 -118 | 52.4% | 52.4% | 0% | No move | Disagrees (same) |
| Texans 1st half team total Over 13.5 -110 | Over -137 | 55.9% | 52.4% | **+3.5%** at -110 | -129 to -137 after release | No half model |
| Titans-Jaguars 1st half Over 24 | Over -120 | 52.8% | 52.4% | +0.4% | -110 to -120 within the hour | No view on the total |
| Titans-Jaguars Over 47.5 | Over -111 | 50.9% | 52.4% | -1.5% | No move | No view |
| Jonah Coleman receptions Over 3.5 +124 FD (Nov 24 12:55pm) | Over +105 | 45.5% | 44.6% at +124 | +0.9% at +124; -3.2% at +105 | Pinnacle moved +124 to +106 on Nov 23, before his release | Disagrees: our props model says 30.8% (median 3 catches) |
| Coleman receiving yards Over 20.5 -112 | 19.5, -115 both ways | under 50% at 20.5 | 52.8% | about -3% | No move | Median 19.6: no edge |
| DK Metcalf receptions Under 3.5 -160 | not posted | n/a | 61.5% | can't tell | Pinnacle has no Metcalf props (discipline review after his ejection; no suspension) | No number |

What this says, for the auditor to test rather than accept: his full-game totals did not move Pinnacle; his half and team-total lines did,
within an hour, every time (Texans half team total, both half totals, Bills team total). That is what a pick that many people copy looks
like at the softer books, and it means the price he quotes is gone fast. At the prices available now only one is clearly positive
against Pinnacle (Texans first-half team total Over 13.5 at -110, if a book still has it). Our props model was far below the market on
Jonah Coleman because it averages his season before he became the lead back (111 yards and 24 carries Sunday): that lag is a finding for
Job 1. Wagerhouse's open bets cannot be read (the history report leaves them out; `wagers` ends Nov 21), so which of these Kylor placed
is his to say.

### Job 3. Deep research: other models and handicappers, NFL, college and NBA

Run this as three parallel research legs (one subagent per sport), each told to return claims tagged [DATA] (a public record or a
paper with numbers), [CLAIM] (a seller's own record) or [OPINION], with links. Research 14a and 23a show the format and what was
already covered; do not repeat them, extend them.

For each sport find:

- **Public rating systems and models with a checkable record against the closing line or the spread**: e.g. for the NFL, nfelo,
  FiveThirtyEight's old Elo, ESPN FPI, DVOA/FTN, PFF Greenline, Massey, Sagarin, The Prediction Tracker's aggregated records; for
  college, SP+, FEI, the Prediction Tracker college records, CFBD-based public models; for the NBA, EPM, LEBRON, DARKO, RAPTOR's
  archive, BPI, Dunks & Threes, Inpredictable. What inputs each uses, and which of those inputs we have for free.
- **Handicappers and syndicates with a verified record** (verified by a third party, not by their own page), and what they say about
  where their edge comes from: openers, injuries and news speed, derivatives (halves, quarters, team totals), props, early-season priors,
  weather, rest and travel. Contest records (e.g. the Westgate SuperContest) count as public data.
- **Academic and practitioner papers** on market efficiency by market type: full game against derivatives, props, openers against close,
  NBA player-absence pricing, college early-season mispricing.
- **What a "sharp" process looks like at the scale Kylor bets**: a soft book (Wagerhouse) against a sharp reference (Pinnacle), limits,
  how quickly stale numbers get fixed.

Then turn the research into **at most eight pre-registered tests** across the three sports, written into the research note and
committed before running any of them (the way research 23 did it: commit d9d268b, then results). Free data only. Each test names its data,
its seasons, its bar (52.4% at -110, or positive closing-line value on 150+ picks) and what we do if it passes or fails. Then run them
walk-forward. NBA gets its own tests; it is not an afterthought.

### Job 4. Suggest picks Wagerhouse can't take, on paper

Kylor wants edges in markets Wagerhouse doesn't offer straight (first quarters, half team totals, props) suggested anyway, so the model
keeps learning. Propose (do not build without his yes) a paper lane: our script's split against Pinnacle's derivative lines that we
already log, frozen at the price, graded on closing-line value, shown on the card and the tracker, never sent as `bet`, with a kill
rule. Say what it would have shown on this week's slate.

## Deliverables

1. `docs/research/24-full-audit.md`. First line: what Kylor needs to answer, in plain English. Then a one-page verdict: is the engine
   doing what he asked, and is each staked lane earning its money? Then Job 1 part by part (what, why, does the reason hold, what breaks
   it, verdict), ranked by money at risk. Then Job 2's Sharp red-team. Then Job 3's tests with results. Then Job 4's proposal. Then a
   yes/no list, short, in plain words, one line each.
2. `docs/research/24a-sources.md`: the sourced research brief for all three sports, every claim tagged.
3. Fix only what is plainly a bug with no judgment call (a wrong sign, a crash, a false sentence), after
   `uv run engine lock take "full audit fixes"`, each with a test, each listed in the note. Anything that changes money, what reaches
   Telegram, or a locked rule is a proposal for Kylor.
4. Commit, release the lock, push to `kylor-johnson/betting-engine`. Never commit `.env` or anything under `data.nosync/`.

## Rules for this session

- Start with `git status` and `git log`. Generated cards, `TRACKER.md`, `STATUS.md`, `CHECKS.md` and `COLLEGE-OPENERS.md` from scheduled
  runs are not unfinished work.
- The database is shared with the live jobs: open it read-only (`engine.odds.snapshots.connect(path, read_only=True)`).
- Write down tests before you run them. A test you design after seeing the data is not a test.
- Every number in the note either comes from a command you ran (say which) or is quoted from a source (link it).
- Plain English. Kylor is technical but not a quant and reads on his phone. Units, not dollars.

---

## Prompt to paste

Read `docs/handoffs/2026-11-24-full-system-audit.md` and do all four jobs in it. Read CHARTER.md, PLAYBOOK.md and CLAUDE.md first, then
every decision note and research note in order. Kylor wants the whole engine audited, every part, with why it was built that way and
whether that reason still holds, plus a red-team of Warren Sharp's saved picks and deep outside research on other models and handicappers
for the NFL, college and the NBA, turned into pre-registered tests that you then run. Don't be lazy: no part skipped, every number
checked. Fix only plain bugs under the lock, with tests; everything else is a yes/no for Kylor in `docs/research/24-full-audit.md`, whose
first line tells him what to answer.
