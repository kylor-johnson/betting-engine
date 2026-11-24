> **Historical (Nov 21, 2026).** This was the Phase 0 brief. The rules now live in `CHARTER.md` (purpose, money, sessions), `PLAYBOOK.md` (how picks are chosen) and `CLAUDE.md` (how code is built). The bankroll and unit below are out of date.

# Handoff: personal sports betting engine

You're building a personal sports betting engine for me (Kylor, Denver, Mountain time). There are two files in this folder: this handoff and BUILD_SPEC.md, a phased spec I put together in another chat. Treat the spec as a draft hypothesis, not the plan. Do not build anything until Phase 0 is done and I've approved it.

## Who I am and how I bet

- I bet NFL, college football and NBA at an offshore book, plus props and teasers. Unit = $25.
- I'm up about $1,640 over the last 4 weeks on ~145 bets. A lot of that came from big favorites (-300 to -800), alt lines, 13-point teasers and moneyline parlays. I want the system to tell me honestly whether I have an edge, not just whether I'm winning.
- My main problem: I find value late. By the time I bet, the line has moved past the good number.
- I'm technical (I run a one-person GTM stack on AI code agents) but I'm not a quant. Explain modeling decisions in plain terms.

## Phase 0: Red-team the approach (do this first, nothing gets built yet)

Do your own deep research. Don't just validate what's in BUILD_SPEC.md; try to break it. Use web search and read primary sources (practitioner writeups, papers, interviews, data provider docs), not just summaries. Spend real effort here.

Answer these, with sources:

1. Is the overall approach sound for one person with a ~$2,500 bankroll and $25 units? Where do individual bettors actually still find edge in 2026 in NFL, CFB and NBA: mainline spreads/totals, early-week openers, small-conference CFB, props, derivatives (halves, team totals), teasers, line shopping alone? Rank them by realistic edge vs. build effort.
2. What do the best handicappers and modelers actually do? Research at minimum Billy Walters, Collin Wilson, Haralabos Voulgaris, Rufus Peabody, Alan Boston, Abnormally Dist, Bill Benter (for the modeling discipline), Ed Feng (The Power Rank), and Unabated / Captain Jack Andrews on market-making and CLV. Pull out the specific, repeatable methods, and flag where they disagree (e.g., whether chasing CLV is the right goal).
3. Where does the draft spec break? Check each phase for:
   - Data reality: is The Odds API coverage, refresh rate and Pinnacle availability good enough? What does historical closing-line data actually cost, and what are the free alternatives? Are nfl_data_py, CollegeFootballData and nba_api still maintained and reliable?
   - My book: Wagerhouse isn't in any odds feed. How much does that weaken alerts, and what's the best proxy?
   - Modeling traps: overfitting, look-ahead bias, small samples, double-counting factors, CFB's 130+ team sparsity.
   - Whether the build order is right. Should Phase 1 really come before any model? Is there a faster path to the biggest edge?
4. Red-team my current betting. Using what you learn, assess heavy-favorite parlays, -300 to -800 alt lines, bought points, 13-point teasers vs. 6-6.5 point Wong teasers, and same-game prop stacks. Which have positive expectation under realistic assumptions, and which are leaking money?
5. What's the minimum viable version that would have caught the value I missed this season (lines moving from open before I bet)?

Write the result to docs/research/00-red-team.md:

- a one-paragraph verdict up top;
- findings per question;
- a revised build plan, with what you changed from BUILD_SPEC.md and why;
- open questions for me;
- sources (links) at the bottom.

Then stop and give me a short summary. I'll approve, edit or kill the plan before you write any code. Once I approve, update BUILD_SPEC.md to the revised version and copy it to CLAUDE.md so it persists across sessions.

## Where everything lives

Root folder: `~/Library/Mobile Documents/com~apple~CloudDocs/Bettng Model` (my iCloud Drive folder "Bettng Model"; the typo is intentional, keep the name).

iCloud syncs this folder. A live database or a virtualenv syncing mid-write will corrupt or conflict, so anything that changes constantly goes in a folder ending in .nosync, which iCloud skips.

```
Bettng Model/
  CLAUDE.md                  # persistent instructions (copy of the approved spec)
  BUILD_SPEC.md              # the plan; revised after Phase 0
  HANDOFF.md                 # this file
  README.md                  # how to run every command
  pyproject.toml             # uv project
  config.yaml                # thresholds, books, unit size, bankroll
  .env                       # API keys (gitignored, never printed)
  .env.example
  .gitignore
  docs/
    research/                # Phase 0 output and any later research
      00-red-team.md
    decisions/               # one short file per major decision (ADR style)
  src/engine/                # all code
    cli.py
    odds/                    # ingest, no-vig math, snapshots
    alerts/                  # Telegram, dedupe, key-number logic
    bets/                    # bet log, parser, CLV
    reports/
    models/                  # Phase 2+ only
  tests/
    fixtures/                # saved API responses for offline tests
  ops/
    launchd/                 # plist(s) for running the poller on my Mac
  data.nosync/               # DuckDB file, raw API dumps (not synced)
    engine.duckdb
    raw/
  logs.nosync/               # poller and alert logs (not synced)
  .venv.nosync/              # virtualenv; run `export UV_PROJECT_ENVIRONMENT=.venv.nosync` (put it in README)
```

Use git in this folder (git init on first run). Keep data.nosync/, logs.nosync/, .venv.nosync/ and .env in .gitignore.

## After approval: build Phase 1 only

Phase 1 is whatever the red-team says it should be. The default from the draft spec:

- odds logger;
- Telegram alerts: openers, stale retail lines vs. the sharp line, key-number crosses;
- `engine bet add "Kansas State +10 -110 20"` bet log;
- CLV tracker and weekly report;
- tests for the no-vig math, key-number logic, bet parser and CLV.

Don't start Phase 2 until Phase 1 passes its exit test and I say go.

What you'll need from me (ask when you hit each one, don't guess):

- The Odds API key (or whichever odds source the red-team picks) and which plan I'm on.
- A Telegram bot token and chat id (walk me through @BotFather).
- Which retail books to compare against as Wagerhouse proxies.
- Confirm the poller runs on my Mac via launchd; give me the plist and the commands to load it.

## Working rules

- Small commits with clear messages. Run the tests before each commit.
- Never log or print API keys.
- Store times in UTC and display them in Mountain time.
- If a data source is down or returns junk, fail loudly and alert me. Never skip silently.
- Major decisions get a short note in docs/decisions/.
- At the end of Phase 1, run a few polls, show me a sample alert and a sample report, and list anything flaky.

## Context: how I've been handicapping by hand (for later phases)

- Power ratings with Walters-style QB values: QB up to ~7 pts, top non-QBs 1-3 pts. Bet the best number. Respect key numbers 3 and 7. Favorites early, dogs late. Max 3% of bankroll per bet.
- Collin Wilson: ratings as stocks (buy low, sell high), Havoc rate.
- Market signals: reverse line movement, the gap between % of bets and % of money, closing line value.
- Turnover-luck regression, efficiency over results, weather on totals, situational spots.
- Every pick needs a "don't bet past" number. If the value is gone at the current price, it's a pass.
