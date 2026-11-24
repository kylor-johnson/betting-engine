# 0025: Research 18 follow-ups: paper for everything but teasers, and the week-1 and week-2 fixes (2026-11-23)

Kylor, after `docs/research/18-model-evaluation.md`: "1. NFL unit = $50; NBA unit = $25 → unless you think it should be weighted
differently / 2. sure / 3. yes". Then, on the UCLA +7 Conditional: "there needs to be some reasoning as to why the line is at what it is
right now".

**Units are unchanged** (NFL $50, NBA $25, college $25). The weighting is by lane, not by size: a lane gets units only when the
evidence supports it.

**Switched to paper (issued, frozen, graded at $0, not sent to Telegram):**
- NFL full-game playbook picks (sides, totals, team totals): `playbook.sports.NFL.full_game: paper`.
- NFL and NBA playbook props: `props_stake: false`.
- Why: research 18. The script earns no weight against the close. The NFL totals lead was the actual-wind input. The props forward test
  gives the model weight 0.1 (NFL), and the NBA model had an Under bias.

**Restart rules (research 18, ranked list):**

| Lane | Restart when | Stays stopped when |
|---|---|---|
| Full-game | Average closing-line value of at least +2.4 points of win chance on 100 picks | Below +1 at 100 picks |
| Props | The blend's lower 95% bound beats Pinnacle by log loss on 300 props, and the picks' closing-line value is above zero after the price | |

**Real money stays on:** NFL Wong teasers, 1 NFL unit ($50) a ticket. Judged at 300 legs against 72.4%. Favorite legs are watched
separately.

**Built (week 1):**
- **One unit a game.** Staked picks plus teaser tickets with a leg in the game. A pick past the cap is issued as paper.
- **Closing grades.** Props and team totals are graded against Pinnacle's last read before the start: the no-vig chance of our exact bet
  minus the chance our price needed.
- **Messages kept.** Every playbook and teaser message is saved in `alerts_sent`, sent or paper.
- **CHECK clears.** A clear needs `because` (a positive, sourced reason), `market_assumes` (what the number already prices) and a source
  link. "Nothing found" is a hold. Cleared picks are paper.
- **What the number already prices.** Every agent Bet and Conditional needs `reasons.priced_in`. Without it the card makes it a Pass.

**Built (week 2):**
- **Never into a move.** A pick is not issued if Pinnacle has moved against its side since we first priced it: 1 point on a side, total or
  team total; on a prop, 10 points of chance or a line move.
- **NBA props re-centred on outcomes** before the blend (`models/calibrate.py`, `playbook.calibrate_props: [NBA]`). It is a per-stat shift
  in log odds, shrunk toward the all-stat shift by 100 props.
- **NBA news-timed props, a paper test** (`picks/news_props.py`, `docs/lanes/NEWS-PROPS.md`).
  - It fires when a regular who played his team's last game is ruled out, within 90 minutes of the first Out signal, and the re-centred
    model beats Pinnacle's price by 4+ points.
  - It is graded on closing-line value. Pass: above +4 points over 100 picks.
  - Limit: it runs on the hourly read, not the 10-minute fast reads, so some picks come up to an hour after the news.

**Not done (not approved yet):**
- re-fitting the weights by log loss;
- the no-vig line as the market reference;
- the NBA team-points curve width;
- re-training the NFL script without the actual-weather inputs;
- measuring a college quarterback's value from CollegeFootballData, which `priced_in` would use instead of a range.
