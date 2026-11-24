# 22: Final audit of the Nov 23 rebuild (decisions 0027 to 0032)

**What you need to decide:** answer the 12 yes/no questions at the bottom. Questions 1 to 3 should be answered before Tuesday's picks go out.

Written Mon Nov 23, 2026, late night, by a fresh session that did not build any of it. Read-only against the live database. Two helpers
re-ran research 20 and 21 and checked every doc sentence against the code. 249 + 2 tests pass after the fixes listed below.

## Verdict

**Is it what you asked for?** Mostly, yes. There is one pick path. Telegram carries only staked picks, the recap and system lines. No
$0 pick can go out as a bet: the send is gated on `dollars > 0`, and the daily check would catch one. College and NBA now have a real way
to a staked pick: sourced news Pinnacle has not priced. The tracker and the sport parity table exist and are honest. The research behind
the college work holds up. Every number in research 20 and 21 reproduced exactly, and neither has look-ahead in its verdict.

**Is it safe to run with real money tomorrow?** Yes, with three problems you should know about:

1. **A staked pick can be lost.** If the Telegram send fails (network blip, Telegram down), the pick is already saved, so it is never sent
   again. Nothing says so until the next morning's check, which may be after the game. *This is the main thing.*
2. **The stop cannot be restarted.** It counts every staked result ever, not since `live_since`. Once it trips, it stays tripped. Today it
   counts the Nov 23 picks too.
3. **College and NBA news picks can be lost.** The engine keeps one pick per game before it checks whether a pick is a news pick. A bigger
   script-only pick on the same game wins, is then shown-only, and the news pick never issues. College has the widest script gaps, so it
   is hit most.

None of the three sends a wrong bet. Each one silently stops a bet you should have got, or stops a restart. Money at risk is bets
missed, not bets lost.

Two things you may not have noticed:
- **Every playbook pick is a B (half a unit).** "A" needs a principle that passed a test, and the code is never told of one. So
  NFL picks are $25 and NBA and college $12.50. Only teaser tickets stake a full unit ($50). That matches the playbook's definition; it is
  just not what "A = 1 unit" suggests.
- **Ten staked picks from Nov 23, 3:51 to 5:33 pm, have no delivery record.** They were issued before messages were saved, so the
  engine cannot prove they reached you. Three of them are on Bengals at Commanders ($75 on one game). They were issued before the
  one-unit-a-game rule went live at 5:56 pm, so that is not a bug. List below; compare with your Telegram.

## Findings, ranked by money at risk

### 1. A Telegram failure loses a staked pick (proposal; touches Telegram)
`src/engine/picks/playbook.py` `_send_and_save` (about line 950) and `run` (about line 690): the pick is inserted into `playbook_picks`,
then `telegram.send` is called. If it raises (`SourceError` on any HTTP or network error), the exception escapes to `run`'s catch-all:
- no `alerts_sent` row is written;
- the rest of that read's picks are skipped;
- the next read sees the pick already exists and skips it for good.

Teasers have the same pattern (`teasers.py` `tickets_to_send`). The daily check (`checks.py` check 1) catches it on the first read after
7am the next day.
**Fix:**
- Catch the send error and save the row with `delivered = false`.
- On every read, resend any staked pick or ticket whose game has not started and whose row is not delivered (once per read, marked
  "RESENT").
- Run checks 1 and 2 on every read, not once a day.

### 2. The stop ignores `live_since`, so it can never be restarted (proposal; money rule)
`playbook.py` `down_units` and `teaser_profit_units` sum every graded staked pick with no date filter. The charter says "down 10 units
since `live_since` … I restart it". `live_since` is "2026-11-24", but Nov 23 picks count. The alert key uses `live_since`, so a restart
would only re-send the alert.
**Fix:** count only picks first issued on or after `live_since` (and teaser tickets sent on or after it). Restarting a stop is then "set
`live_since` to today".

### 3. One-pick-per-game runs before the news-pick test (proposal; money)
`playbook.py` `grade_all` keeps the best candidate per game by grade, then edge. `run` (about line 652) then demotes shown-lane A/B picks
that are not news picks to C. Say a college game has a script-only B total at +6% and a news side at +4% (the news side is the only one
that may be staked). The total wins the per-game pick, is demoted, and the news side is gone. Test coverage: none.
**Fix:** in a shown-only lane, decide news-pick status per candidate before choosing the game's best, and pick the best among the
candidates that may be staked.

### 4. "Pinnacle has not moved since the news" when Pinnacle has not been read since the news (proposal; money)
`slate.unpriced_part` compares the last Pinnacle line at or before `news_at` with the latest one stored. If Pinnacle took the game down
on the news (it often does) or our reads have not run since, both are the same pre-news line. The news counts in full as "unpriced". The
market reference used for our number is that same stale line.
**Fix:** require at least one Pinnacle read after `news_at`. Otherwise mark the entry "not applied: no Pinnacle read since the news" and
let the next read decide.

### 5. College quarterback value: 3.5 undersells a pre-game absence (proposal; agent guide)
Research 21's "starter out" means whoever threw the most passes, which includes in-game injuries and benchings the market could not know.
Split by whether the usual starter threw at all (helper re-run, cached data):

| Starter's status | Games | Points the market moved |
|---|---|---|
| Threw no passes (true pre-game absence) | 811 | 4.1 |
| Threw some passes but not the most (in-game injury or benching) | 267 | 2.4 |

The college guide's "going above 5 needs a written reason" conflicts with the note's own table. When the missing starter was the team's
weak passer, the absence was worth 5.0 overall and 5.3 when he sat from the start. Only about 1 point (not 0.9) moves after the opener,
on a retail opener, not Pinnacle's.
**Fix:**
- Change the college guide's value for a starter ruled out before the game to about 4.
- Drop the "above 5" sentence, or point it the other way.
- Add the caveat to research 21.

### 6. NFL quarterback news can count twice, and the NFL guide gives no size (proposal; money)
`playbook.py` `_qb_out_teams` turns any NFL spread entry of 2.5+ points that mentions a quarterback into `backup_qb = 1` in the game
script. It does this whether or not Pinnacle has priced the news. `apply_news` then adds the unpriced part on top. At side weight 0.25 the
script part is small, but it is a double count. The NFL guide has no point value. The old `adjustments.yaml` header said "elite 6 to 7",
while research 14 measured about 2.5 to 2.7. Tonight's entries are -5 (Maye) and -3 (Jackson), both with no `news_at`.
**Fix:**
- Feed the script's quarterback flag only from entries whose news is fully priced (or drop it).
- Put the measured 2.5 to 2.7 in the NFL guide.

### 7. Picks past a cap are dropped, not paper (proposal; recap)
PLAYBOOK and the charter say a pick past a cap is paper and named in the recap. The code skips it (`playbook.py` about lines 667 and 804).
It is only a candidate row, not on the tracker or in the recap. The per-game props cap skips silently.
**Fix:** issue it as paper with the cap as the reason.

### 8. No CANCELLED message for a sent pick (proposal; Telegram)
The charter promises "a CANCELLED message if a sent pick should no longer be bet". Playbook picks and teaser tickets are frozen and never
cancelled. Only the retired old path could cancel. Either build it (for example, when Pinnacle moves past the don't-bet-past number before
the start) or take the promise out.

### 9. The research agent can run commands that send (proposal; Telegram)
`picks/agent.py` allows `Bash(uv run engine:*)`. So the agent can run:
- `engine playbook` without `--dry-run`, which issues and sends staked picks outside the read;
- `engine status --send`;
- `engine bet add`;
- `engine lock take`.

Nothing in tonight's logs shows it doing so.
**Fix:** allow only the read-only commands it needs (`slate`, `news`, `injuries`, `matchup`, `playbook --dry-run`, `props`).

### 10. Two research schedules that disagree (proposal; you run launchctl)
- `config.yaml` `agent.schedule`: 8:15 daily, plus 6:45 pm Sunday.
- The loaded agent launchd job: Sunday 8:15, 6:45 pm and 8:45 pm; Monday, Tuesday and Saturday 8:15; Wednesday to Friday 3:15 pm.

The hourly read also starts any config slot that has not run. So Wednesday to Friday get two fixed runs, and the missed-run alert knows
only the config times.
**Fix:** make the launchd job match the config, or unload it and let the read start the fixed runs.

### 11. The daily check is weaker than the charter's list (proposal)
`checks.py`:
- runs once, inside the first successful read after 7am, so if reads are broken it never runs (the missed-read alert covers that);
- check 7's "hourly read" part always passes at 7am because 7 is the first read hour;
- the tracker row, the closing grades and the teaser grading are not checked.

The charter's list now says what the code does (fixed below).
**Fix:** run checks 1 and 2 every read (see 1). Run check 7 from 9am.

### 12. Teaser push rule not verified (question for you)
A pushed leg makes the whole ticket a push, refunded (`teaser_profit_units`, tracker). Many books grade a 2-team teaser with a push as a
loss or as "ties reduce". Check Wagerhouse's house rule.

### Smaller
- The 9am recap is not saved in `alerts_sent`. If its send fails, the rest of that read's grading block stops (`poll.py` about line 256).
- Research 20: "the close already prices it" overstates a 110-bet test. The squared-error tie is the real support. The forecast runs
  0.74 mph above actual wind. The "close" is a retail book's line from CollegeFootballData. The verdict (failed, off) stands.
- DuckDB lock errors: seven in the logs, all from code before the 180-second wait was added. None since.

## Fixed in this session (plain bugs, with tests)

1. **A news entry whose `team` matches neither team vanished with no trace.** It now shows on the card and in `engine news` as "not
   applied: team matches neither …" (`playbook.apply_news`). Test: `test_team_name_that_matches_neither_team_is_reported_not_dropped`.
2. **An entry whose `game` matches no Wagerhouse game was invisible.** College names are the risk: Wagerhouse writes "Mississippi St",
   "Miami Ohio". `engine news` now lists every entry that matches no upcoming game, and exits non-zero for them
   (`playbook.unmatched_news`). Test: `test_entry_for_a_game_wagerhouse_names_differently_is_listed`. Tonight it lists the three NBA
   entries, because those games have started or are not posted yet.
3. **The `adjustments.yaml` header described the retired ratings model** ("better than its rating", "the ratings move about 10% a week",
   "elite 6 to 7"). It now says what decision 0029 does: full effect, the engine nets out the priced part, names must match Wagerhouse's,
   sizes in the sport guides. The agent prompt says the same about names.
4. **False doc sentences** (next section).

Also built, as you asked mid-audit: **the live model-picks page** (`src/engine/bets/public_page.py`, `engine tracker-publish`,
`public_tracker` in config). It shows only the picks the model sent to Telegram, with stake, limit, result and closing-line value. It never
shows your own Wagerhouse bets or paper picks; a test fails if it even reads them. It is rebuilt with the tracker and pushed to Vercel when
the picks change, at most every 10 minutes. It needs one `vercel login` on this Mac. Test: `tests/test_public_page.py`.

## False doc sentences

Fixed (wording only, no rule changed):

| File | Was | Now |
|---|---|---|
| CHARTER, Telegram | the recap has "yesterday's results" | the record since Nov 23 and the last 24 hours' paper picks with reasons |
| CHARTER, checks 1, 3 to 7 | tracker row, closing grades, 24 hours, "STATUS says why", "matches config", "fixed times" | what `checks.py` does, with the gaps named |
| CHARTER, sessions | lock "enforced" | `lock take` refuses a second session; nothing else blocks an edit |
| PLAYBOOK §4, §9 | a cleared CHECK pick is staked | only in a staked lane; NBA and college full-game only as a news pick; NBA and college CHECK distances added |
| PLAYBOOK §4 | a losing principle "is cut to zero weight" with a Telegram line | by a session with a decision note; nothing automatic but the review line |
| CLAUDE.md | the agent "may write only" its files | its file edits are limited, but it can run any `engine` command, including ones that send |
| CLAUDE.md | a down source sends a `system` alert | the list of what actually reaches Telegram |
| CLAUDE.md | "every message is saved" | pick and system messages; the recap, agent messages, weekly report and stale alerts are not |
| README | weekly report "sent to Telegram"; NBA watcher "messages the news"; teaser legs "paper"; "four jobs"; research "8:15 every day" | held back; recorded on the board; real money; five jobs; both schedules named |
| playbook.py docstring | half size; "A and B picks are sent" | half size off; only staked picks are sent; every playbook pick is B today |

Not changed, because the sentence is the rule and the code is what is wrong (findings 2, 7, 8): the stop "since `live_since`", "a pick
past a cap is paper", "a CANCELLED message".

## Picks without a delivery record (Nov 23, Mountain)

All half a unit:

| Time | Pick | Stake |
|---|---|---|
| 3:51 pm | Washington Commanders team total under 24 | $25 |
| 3:59 pm | Ja'Marr Chase under 0.5 touchdowns | $25 |
| 3:59 pm | DeVonta Smith under 64.5 receiving yards | $25 |
| 4:16 pm | Donovan Mitchell under 36.5 pts + reb + ast | $12.50 |
| 4:16 pm | Coby White under 1.5 threes | $12.50 |
| 5:02 pm | Brook Lopez over 12.5 points | $12.50 |
| 5:02 pm | Under 42.5 (game 401873084) | $25 |
| 5:02 pm | Josh Allen over 244.5 passing yards | $25 |
| 5:33 pm | Tennessee Titans +15 | $25 |
| 5:33 pm | Stefon Diggs under 4.5 receptions | $25 |

## Yes / no for Kylor

1. Resend a staked pick on the next read when Telegram fails, and run the "every staked pick reached Telegram" check on every read?
   (Finding 1. Recommended: yes.)
2. Make the stop count only from `live_since`, so a restart is "set `live_since` to today"? (Finding 2. Recommended: yes.)
3. In college and NBA, let a news pick win its game even when a bigger script-only pick (which can't be staked) is on the same game?
   (Finding 3. Recommended: yes.)
4. Count news only once Pinnacle has been read after the news broke? (Finding 4. Recommended: yes.)
5. College starter ruled out before the game: about 4 points instead of 3.5, and no "above 5 needs a reason" rule for weak-passing teams?
   (Finding 5. Recommended: yes.)
6. Stop the NFL script's quarterback flag from double-counting news, and put the measured 2.5 to 2.7 points in the NFL guide?
   (Finding 6. Recommended: yes.)
7. Issue picks past a cap as paper (on the tracker and in the recap) instead of dropping them? (Finding 7. Recommended: yes.)
8. Build a CANCELLED message when Pinnacle moves past a sent pick's "don't bet past" number before the start? If no, the promise comes out
   of the charter. (Finding 8. Recommended: yes.)
9. Limit the research agent to read-only engine commands? (Finding 9. Recommended: yes.)
10. Make the research launchd job match the config schedule (8:15 daily, 6:45 pm Sunday)? You reload it with launchctl.
    (Finding 10. Recommended: yes.)
11. Is every playbook pick at half a unit what you want for now? (Nothing grades A until a principle passes its test. Teasers stay full.)
12. Does Wagerhouse grade a 2-team teaser with a pushed leg as a push (refund)? (Finding 12: check the house rules.)
