# 0029: Sourced news moves the playbook number; college news picks are staked (2026-11-23, night)

Replaces: none. Fixes a false line in decision 0027 and the agent prompt ("an opinion you can source goes in adjustments.yaml; it then moves
the numbers"): until tonight `adjustments.yaml` fed only the old slate, which no longer sends picks, so under one pick path news could not
move a pick in any sport.

Kylor: "i also feel like CFB has been HEAVILY neglected in this model." Checked: college had no tested model, no weather history, no props,
full-game picks shown only, and its one evidence-backed idea (quarterback and opt-out news, research 14) ran through the old path, now a
$0 record. Nothing college could reach Telegram.

- **News in the playbook, every sport** (`playbook.apply_news`): each sourced `adjustments.yaml` entry moves our number for its game by the
  part Pinnacle has not moved for since `news_at` (the same `slate.unpriced_part` rule the old path used). No `news_at`, or no Pinnacle line
  stored from before the news, means nothing is applied. The news is added after the blend, at full size, because the market has not priced
  it. Team totals get half of a side adjustment and half of a total adjustment. Every pick's "Why" names the news, its source and how much
  counted, and the edge split says how much of the edge is unpriced news.
- **News picks in shown-only lanes** (`playbook.sports.<SPORT>.news_picks`, on for College): a side or total is staked (B, half a unit) only
  when the unpriced news is what takes it over the minimum edge; the college script alone still never stakes. The usual guards apply:
  never into a Pinnacle move, one unit a game, per-lane caps, the stop.
- **The college agent guide** now says news is how college bets get made and asks for every sourced quarterback, opt-out and portal change
  in `adjustments.yaml` the same run it is found, with the time it broke.
- **Not measured:** how many points a college quarterback is worth. The guide's range (3 to 7) is the agent's to apply per backup; measuring it
  from CollegeFootballData is still open (listed as not done in decision 0025).
- **Running:** a college wind-totals test (`models/college_wind.py`, research 20 when it finishes), fitted on reanalysis and judged only on
  the day-before forecast for 2024-2026, so it cannot repeat the look-ahead research 18 found in the NFL script.

Tests: `tests/test_news_in_playbook.py`.
