# Handoff: evaluate the picks engine, research deeply, and tune it

Written 2026-11-22 (Mountain). Paste the short prompt at the bottom into a fresh Claude Code session opened in this folder. Everything it needs is in files here.

## What I want from you

I'm Kylor (Denver, Mountain time). Over two days another session built me a betting engine. I want a fresh pair of eyes to do three things, in this order:

1. **Evaluate what was built.** Read the code and the research, run it, and tell me plainly what is sound, what is weak, and what is wrong. Don't defend it; you didn't build it.
2. **Do deep research** on how elite handicappers actually find bets, with primary sources, aimed at the specific gaps listed below. I use Warren Sharp's write-ups as inspiration for what the analysis under the hood should look like. He clearly has information and a market effect I don't, but I want to get closer.
3. **Tune the model** based on evidence: change weights, thresholds, inputs and markets only where a test supports it.

Write your findings to `docs/research/04-evaluation.md`, end with a proposed tuning plan, and **stop for my approval before changing any code**. I'm technical but not a quant. Explain modeling choices in plain English.

## What I actually want the engine to be

- An agent that does the research on a schedule and tells me when there is a bet to place, early enough that I'm the one holding the good number.
- Real handicapping under the hood: unit against unit, schedule-adjusted, splits by span, injuries, weather, situational edges, what top bettors do.
- **Not** a tool that mostly notices my book is half a point off another book. That is an input, not a reason to bet.
- It must account for **player props** and smaller markets (quarters, halves, team totals). Right now it does not.
- My book, Wagerhouse, is a soft pay-per-head book and much worse than the legal books. Its lines may be sloppier in the small markets. That is probably where my edge is, and nobody has measured it yet.

## Read these first, in this order

1. `CLAUDE.md` — the spec and the rules that bind every session.
2. `docs/research/00-red-team.md` — the original research: where individual bettors find edge, what the pros do, what my own betting was leaking.
3. `docs/research/01-picks-engine.md` — the picks engine design and a grade of a hand-built card.
4. `docs/research/02-totals-model.md` — a totals model that was built, tested and failed.
5. `docs/research/03-sharp-style-handicapping.md` — what Sharp's write-ups do, where he actually bets, and a sides model that also failed its test.
6. `docs/research/01-bet-audit.md` — an audit of my own 310 bets this season.
7. `docs/decisions/` — four short decision notes.
8. `README.md` — every command.
9. `docs/cards/` — the cards produced so far, and `ops/agent_prompt.md`, the research agent's instructions.

Then read the code in `src/engine/picks/` (slate, pricing, ratings, history, matchup, totals, card, agent, news, board) and run it: `uv run engine slate --sport NFL`, `uv run engine matchup TEN DAL`, `uv run engine totals-test`, `uv run engine spread-test`, `uv run engine board`, `uv run pytest`.

## What exists today

- **Line reads** of Wagerhouse (read-only, from my account), Pinnacle and DraftKings, hourly 7am to 5pm Mountain, stored in `data.nosync/engine.duckdb`.
- **A slate sheet** per sport (NFL, college football, NBA): a fair line blended from Pinnacle with the vig removed (55%) and a model (45%), the edge at my book using how real games land on each margin, and a "don't bet past" number.
- **The model side** is ratings backed out of the market's own closing lines, averaged with about 50 public rating systems (football only), plus hand-entered adjustments in `adjustments.yaml`.
- **A research agent** (a headless Claude run, 8:15am and 3:15pm daily plus Sunday evening) that researches the flagged sides and sets Bet, Conditional or Pass with reasons. Code owns every number; the agent cannot type a line or a stake.
- **A matchup layer for the NFL** from play-by-play: each offense and defense on EPA, success rate, third down, red zone, drive results, pass rate over expected, first-quarter and first-half scoring, schedule strength, and last-four-games splits.
- **A quarterback news watcher** on the NFL injury feed, hourly.
- **Telegram messages** that lead with the instruction, and `board.html`, a page showing current picks.

## What is locked. Do not reopen these without asking me.

- I stay on Wagerhouse only. No other books.
- No paid data.
- The engine never places bets. I place every bet by hand.
- Pregame NFL, college football and NBA. No live betting, baseball or hockey.
- Unit is $25. Engine picks are 1 unit, 0.5 for a Conditional, until 100 are graded.
- Code owns the numbers; the agent owns research and judgment.
- Betting splits and reverse line movement are never a reason for a pick.
- Every pick has a "don't bet past" number.
- A model is allowed to drive picks only after a walk-forward test shows it adds something on top of the market.

## What has been tested, and the results

- A totals model from pace, drives and success rate: 918 games, 2022 to 2026. It added nothing to the closing total. Best blend: 100% market.
- A sides model from opponent-adjusted EPA per play: same 918 games. It added nothing to the closing spread. Best blend: 100% market.
- My own bets: 310 wagers, net −$57, no sign of beating the closing price, live betting −$427.

## Known weaknesses. Start your evaluation here.

**Never tested**
- The 55% Pinnacle / 45% model blend. The number came from one bettor's interview, not from a test.
- The 2% minimum edge for flagging a side.
- The model side itself (market ratings plus public systems) against the closing line.
- Whether flagged sides beat the close. Nothing grades the engine's picks yet. Pinnacle prices are stored on every read, but no code computes closing line value for engine picks.
- The landing tables that price half points, and the bell curve used for the NBA.
- The agent's point values for injuries. They are judgment from a rough tier guide.

**Missing**
- Player props. Not built. Nobody has looked at how to read Wagerhouse's prop lines.
- First-quarter, first-half and team-total markets. Not built. This is where Sharp places most of his bets.
- Any handicapping layer for college football or the NBA. The matchup numbers are NFL only.
- An NBA news watcher. NBA injuries are only seen at the two scheduled runs.
- News faster than hourly.
- A measurement of how Wagerhouse's lines compare with the market over time. The data is being collected; nobody has analysed it.

**Thin or fragile**
- The NBA model is market ratings alone, with no second opinion.
- College ratings ignore neutral sites and treat lower-division opponents as average.
- ESPN, Pinnacle and Wagerhouse are all read through undocumented endpoints that can change.
- DraftKings' "opening" line can be months old.
- The engine has issued one Conditional and zero Bets. There is no track record.
- Eight of my past bets show as placed after kickoff on the regular site and are unexplained.

## What I want researched

Primary sources, not summaries. Mark each claim as read on the page, a search snippet, or from memory. Say plainly what you could not verify.

1. **Where does a one-person bettor at a soft book actually have an edge?** Specifically props, quarters, halves, team totals and alternate lines at pay-per-head books. How do sharp bettors attack soft props? What do they compare against when there is no sharp reference price?
2. **How do elite handicappers build a number**, step by step, for a side, a total, a first half and a player prop? Go beyond the names already covered (Walters, Wilson, Voulgaris, Peabody, Boston, Abnormally Dist, Benter, Feng, Unabated, Spanky, Krackomberger, Pizzola, Powers, Sharp). Find the people who publish method for props and derivatives.
3. **Player prop modeling with free data.** Usage, snap share, target share, opponent by position, game script, distributions for yards and receptions, why books post near the median. What is achievable from nflverse data without paid route data? What does a backtest of prop projections against real prop lines look like, and where can historical prop lines be had for free?
4. **Derivative pricing.** How first-quarter and first-half lines relate to full-game lines, where books use a fixed formula, and how to detect when a team's period splits justify a different number.
5. **Timing.** When in the week each market is softest, by sport, with evidence.
6. **What the two failed tests imply.** Were they the right tests? What inputs do serious modelers use that those models lacked? Is there any public-data input with evidence of adding to the closing line?
7. **College football and NBA handicapping** at the level of the NFL matchup layer: which free data supports it, and which factors have evidence.

## What I want tuned or decided, with a test behind each

- The blend weight and the minimum edge, from a backtest of the model side.
- Whether the model side should be replaced, extended or dropped.
- Injury point values, checked against how lines actually moved when players were ruled out.
- Which new markets to add first (props, quarters, halves, team totals), based on what Wagerhouse offers and where its lines are loosest. Reading its prop and period lines is the first step; the read-only client is in `src/engine/odds/wagerhouse.py`.
- A grading system for engine picks: result, closing line value against Pinnacle, and a comparison with my own bets.
- What the research agent should be told differently, based on reading its actual output in the cards and the logs in `~/Library/Logs/betting-engine/`.

## Rules for the work

- Fail loudly. If a source is down or a number is missing, say so; never quietly drop a factor.
- No look-ahead in any test. Each game may see only what was known before it.
- Hold out seasons when you tune anything, and report the held-out result.
- A claim about what is in the engine needs the file it came from. A claim about the world needs a link.
- Don't print or store logins. They live in `.env`.
- Wagerhouse access is read-only and paced. Don't add a constant poll.
- Small commits, tests before each commit, decisions noted in `docs/decisions/`.
- When you write anything I'll read on my phone, the first line says what to do.

## What you'll need from me

Ask only when you hit one of these, and keep working on everything else:

- My Sharp Football Analysis login, if you want to read more members' write-ups for method. I'll paste it; don't store it.
- Approval of the tuning plan before any code changes.

## Deliverable

`docs/research/04-evaluation.md` with:

- a one-paragraph verdict;
- what is sound, what is weak, what is wrong, each tied to a file;
- research findings per question, with sources;
- the tests you ran and their results, including the ones that failed;
- a tuning plan in priority order, each item with the evidence for it and how it will be tested;
- open questions for me.

Then stop and give me a short summary.

---

## Prompt to paste into the fresh session

```
Read docs/handoffs/2026-11-22-evaluate-and-tune.md in this folder and do what it says.
Start with CLAUDE.md and the research documents it lists, then the code, then run the engine.
Evaluate first, research second, propose tuning third. Write docs/research/04-evaluation.md
and stop for my approval before changing any code.
```
