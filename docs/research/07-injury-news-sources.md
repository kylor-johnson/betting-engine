# Injury and availability news: which sources, how fast

Written 2026-11-22. Code: `src/engine/picks/player_news.py`, `src/engine/picks/nba_news.py`, reporter list `ops/reporters.yaml`. Coverage check: `uv run engine reporters`.

## Bottom line

ESPN's injury table is slow, sometimes hours behind. The engine now reads three faster sources:

1. **The official NBA injury report** (nba.com PDF, reposted every 15 minutes on game days). This is the league's own list, the one ESPN copies from. On 2026-11-22 it had P.J. Washington Doubtful while ESPN still said Day-To-Day, and Austin Reaves off the report while ESPN still said Out.
2. **Rotoworld (NBC Sports) player news, NFL and NBA.** It relays beat writers, national insiders, team accounts and the official report, each post linking the original X post. Measured from the tweet ids over the last 150 posts per sport: NBA median 5 minutes after the tweet (90th percentile 11), NFL median 13 minutes (90th percentile 71).
3. **A named reporter list** (`ops/reporters.yaml`). NFL: 85 team beat writers from Unabated's list (https://unabated.com/post/best-nfl-twitter-follows), plus Schefter, Rapoport, Pelissero, Fowler and Garafolo. NBA: two beat writers per team from a 2026-27 compilation (https://fiddlespicks.substack.com/p/nba-beat-writers-for-every-team-26), plus Shams Charania, Chris Haynes, Marc Stein, Jake Fischer, Brian Windhorst, Underdog NBA and FantasyLabs NBA. Every relayed post is tagged with who said it. An unattributed item never alerts on its own.

## What it cannot do: read X directly

- X's API costs money (no-paid-data rule). Its pages need a login and JavaScript.
- A test of X's free public embed endpoints was blocked by this Mac's permission settings. It was not attempted another way.
- So the engine sees a listed reporter's post only when Rotoworld relays it. Over two days Rotoworld relayed 9 of the 86 listed NFL reporters and 3 of the 67 NBA ones (most NBA availability news came from the official report and team accounts). Insiders like Rapoport are relayed often; most beat writers are relayed rarely.
- Options to read X directly are in the handback to Kylor. Each needs his call: the paid X API (breaks the free-data rule), allowing a test of the public embed endpoints (may break, against X's terms), or a logged-in browser session (account risk).

## How each source is used

- **NBA watcher, every 10 minutes:** official report changes and Rotoworld posts. A post saying "playing" or "not playing" alerts when the official report (or ESPN, if the official report is down) does not already show it. One message per player per direction per day, whichever source is first.
- **NFL hourly read:** Rotoworld posts on starting quarterbacks that ESPN does not show yet. These start a research run.
- **Props model:** a Rotoworld availability post from the last 36 hours overrides ESPN's status for that player.
