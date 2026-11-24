"""`engine check`: the charter's "What working looks like", as checks that can fail (decision 0030).

Run at the end of every session and on the first hourly read after 7am Mountain. Checks 1 and 2 (delivery) also run on every read,
after the resend of anything undelivered (`delivery_problems`; research 22). Writes docs/lanes/CHECKS.md. On the scheduled run, one
Telegram `system` line is sent only when something fails, once per day.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from engine import config

SAVED_SINCE = datetime(2026, 11, 24, 1, 0)      # UTC: alerts_sent keeps playbook and teaser messages from decision 0025 (Nov 23, ~6pm MT)
IN_SEASON = {"NFL": ((9, 1), (2, 15)), "College": ((8, 20), (1, 20)), "NBA": ((10, 15), (6, 20))}
MAX_AGE_DAYS = {"NFL": 8, "College": 8, "NBA": 2}


def _in_season(sport: str, d) -> bool:
    (m1, d1), (m2, d2) = IN_SEASON[sport]
    md = (d.month, d.day)
    return md >= (m1, d1) or md <= (m2, d2)


def run(con, cfg: dict, now: datetime | None = None) -> list[tuple[str, bool, str]]:
    """[(check, passed, detail)]."""
    from engine import lanes, session_lock
    now = now or datetime.now(timezone.utc)
    naive = now.replace(tzinfo=None)
    out = []

    def q(sql, args=()):
        try:
            return con.execute(sql, list(args)).fetchall()
        except Exception as e:
            return e

    # 1. every staked pick reached Telegram
    rows = q("""SELECT p.pick FROM playbook_picks p LEFT JOIN alerts_sent a ON a.key = 'playbook|' || p.pick_key
                WHERE p.dollars > 0 AND p.first_seen_utc >= ? AND coalesce(a.delivered, false) = false""", [SAVED_SINCE])
    trows = q("""SELECT t.ticket_key FROM teaser_tickets t LEFT JOIN alerts_sent a ON a.key = 'teaser|' || t.ticket_key
                 WHERE t.dollars > 0 AND t.sent_utc >= ? AND coalesce(a.delivered, false) = false""", [SAVED_SINCE])
    if isinstance(rows, Exception) or isinstance(trows, Exception):
        out.append(("Every staked pick reached Telegram", False, f"could not read: {rows if isinstance(rows, Exception) else trows}"))
    else:
        miss = [r[0] for r in rows] + [f"teaser {r[0]}" for r in trows]
        out.append(("Every staked pick reached Telegram", not miss, "all delivered" if not miss else "not delivered: " + "; ".join(miss[:5])))

    # 2. nothing on Telegram is a $0 pick
    rows = q("SELECT key FROM alerts_sent WHERE kind = 'bet' AND delivered AND (text LIKE '%Stake: $0 %' OR text LIKE '%Stake: 0 units%') AND ts_utc >= ?", [SAVED_SINCE])
    ok = not isinstance(rows, Exception) and not rows
    out.append(("No $0 pick sent as a bet", ok, "none" if ok else f"{rows}"))

    # 3. limits and grading
    # A read error fails the check with its reason; it used to crash here slicing the error (audit 24).
    rows = q("SELECT pick FROM playbook_picks WHERE dollars > 0 AND (dont_bet_past IS NULL OR dont_bet_past = '')")
    if isinstance(rows, Exception):
        out.append(("Every staked pick has a don't-bet-past number", False, f"could not read: {rows}"))
    else:
        out.append(("Every staked pick has a don't-bet-past number", not rows, "all have one" if not rows else f"missing on: {rows[:5]}"))
    late = q("""SELECT p.sport, p.pick FROM playbook_picks p LEFT JOIN playbook_grades g USING (pick_key)
                WHERE g.pick_key IS NULL AND p.dollars > 0 AND p.kickoff_utc < ?""", [naive - timedelta(hours=28)])   # staked (charter, check 3)
    if isinstance(late, Exception):
        out.append(("Every staked pick graded within a day of the game", False, f"could not read: {late}"))
    else:
        out.append(("Every staked pick graded within a day of the game", not late, "none late" if not late else f"{len(late)} late, e.g. {late[0]}"))

    # 4. every lane in season has a recent candidate
    stale = []
    for sport in ("NFL", "College", "NBA"):
        if not _in_season(sport, now.date()):
            continue
        for label, cond in (("full-game", "market <> 'prop'"), ("props", "market = 'prop'")):
            if label == "props" and sport == "College":
                continue
            r = q(f"SELECT max(first_seen_utc) FROM playbook_candidates WHERE sport = ? AND {cond}", [sport])
            last = None if isinstance(r, Exception) else r[0][0]
            if last is None or naive - last > timedelta(days=MAX_AGE_DAYS[sport]):
                stale.append(f"{sport} {label} (last {last:%b %d} )" if last else f"{sport} {label} (never)")
    r = q("SELECT max(first_seen_utc) FROM teaser_legs")
    last = None if isinstance(r, Exception) else r[0][0]
    if _in_season("NFL", now.date()) and (last is None or naive - last > timedelta(days=8)):
        stale.append("NFL teasers")
    out.append(("Every lane in season has a recent candidate", not stale, "all recent" if not stale else "quiet: " + ", ".join(stale)))

    # 5. status table fresh
    sp = config.ROOT / "docs" / "lanes" / "STATUS.md"
    age = (now.timestamp() - sp.stat().st_mtime) / 3600 if sp.exists() else None
    out.append(("STATUS.md generated in the last 24 hours", age is not None and age < 24,
                "missing" if age is None else f"{age:.0f} hours old"))

    # 6. money rules visible
    try:
        from engine.picks import playbook
        downs = {s: playbook.down_units(con, s, cfg) for s in ("NFL", "NBA", "College")}
        tripped = [s for s, d in downs.items() if d <= -abs(playbook.settings(cfg, s)["stop_loss_units"])]
        out.append(("No stop tripped", not tripped, ", ".join(f"{s} {d:+.1f}u" for s, d in downs.items())
                    + (f"; TRIPPED: {', '.join(tripped)}" if tripped else "")))
    except Exception as e:
        out.append(("No stop tripped", False, f"could not read: {type(e).__name__}"))

    # 7. scheduled reads and research runs
    local = now.astimezone(config.display_tz(cfg))
    hours = cfg["read_hours"]["sunday" if local.weekday() == 6 else "other"]
    r = q("SELECT max(ts_utc) FROM line_snapshots WHERE source = 'wagerhouse'")
    last = None if isinstance(r, Exception) else r[0][0]
    if local.hour in hours and local.hour > min(hours):
        ok = last is not None and naive - last < timedelta(hours=2)
        out.append(("Hourly read ran in the last 2 hours", ok, f"last read {last:%a %H:%M} UTC" if last else "never"))
    else:
        out.append(("Hourly read ran in the last 2 hours", True, "outside read hours"))
    r = q("SELECT max(ts_utc) FROM agent_runs WHERE ok")      # a finished, successful run; "started" rows (ok NULL) and failures don't count (audit 24)
    last = None if isinstance(r, Exception) else r[0][0]
    out.append(("A research run finished in the last 26 hours", last is not None and naive - last < timedelta(hours=26),
                f"last {last:%a %H:%M} UTC" if last else "never"))

    # 8. session lock
    lk = session_lock.read()
    stale_lock = lk is not None and session_lock.held(now) is None
    out.append(("No stale session lock", not stale_lock, "none held" if lk is None else ("STALE: " if stale_lock else "held: ") + lk["session"]))

    # 9. news entries the playbook cannot count (a warning: the research agent fixes these on its next run, decision 0029)
    try:
        from engine.picks import slate
        missing = [f"{a['game']} ({a.get('team') or a['market']})" for a in slate.load_adjustments() if not a.get("news_at")]
        out.append(("News entries carry news_at (warning only)", True,
                    "all do" if not missing else f"WARNING, {len(missing)} not counted: " + "; ".join(missing[:4])))
    except Exception as e:
        out.append(("News entries carry news_at (warning only)", False, f"adjustments.yaml unreadable: {e}"))

    # 10. sport parity
    pp = lanes.parity_problems(cfg)
    out.append(("Every sport has every component (parity)", not pp, "complete" if not pp else "; ".join(pp[:5])))
    return out


def delivery_problems(con) -> list[tuple[str, str]]:
    """Checks 1 and 2 on every read, after the resend (research 22, finding 1; Kylor 2026-11-24): (alert key, system text), one per staked
    pick that still has not reached Telegram and one per $0 pick sent as a bet. Keys are per pick, so each reaches Telegram once."""
    out = []
    try:
        for key, pick in con.execute("""SELECT p.pick_key, p.pick FROM playbook_picks p LEFT JOIN alerts_sent a ON a.key = 'playbook|' || p.pick_key
                                        WHERE p.dollars > 0 AND p.first_seen_utc >= ? AND coalesce(a.delivered, false) = false""",
                                     [SAVED_SINCE]).fetchall():
            out.append((f"undelivered|{key}", f"NOT DELIVERED (check the bot): the staked pick {pick} has not reached Telegram, even after a "
                                              "resend. The engine tries again on every read until the game starts."))
        for (key,) in con.execute("""SELECT t.ticket_key FROM teaser_tickets t LEFT JOIN alerts_sent a ON a.key = 'teaser|' || t.ticket_key
                                     WHERE t.dollars > 0 AND t.sent_utc >= ? AND coalesce(a.delivered, false) = false""", [SAVED_SINCE]).fetchall():
            out.append((f"undelivered|teaser|{key}", f"NOT DELIVERED (check the bot): the teaser ticket {key} has not reached Telegram, even "
                                                     "after a resend. The engine tries again on every read until the first game starts."))
        for (key,) in con.execute("SELECT key FROM alerts_sent WHERE kind = 'bet' AND delivered AND (text LIKE '%Stake: $0 %' OR text LIKE '%Stake: 0 units%') AND ts_utc >= ?",
                                  [SAVED_SINCE]).fetchall():
            out.append((f"zero-bet|{key}", f"A $0 pick was sent as a bet ({key}). It is paper: do not bet it. A session must find out why."))
    except Exception as e:
        out.append((f"delivery-check-failed|{type(e).__name__}", f"The delivery check could not read the database: {type(e).__name__}: {e}"))
    return out


def markdown(results: list[tuple[str, bool, str]], now: datetime, cfg: dict) -> str:
    stamp = now.astimezone(config.display_tz(cfg)).strftime("%a %b %-d, %-I:%M %p")
    fails = [r for r in results if not r[1]]
    head = f"**{len(fails)} failing.**" if fails else "**All passing.**"
    return ("# Checks (generated by `engine check`; do not edit)\n\n"
            f"Run {stamp} MT. The charter's \"What working looks like\" as checks that can fail. {head}\n\n"
            "| Check | | Detail |\n|---|---|---|\n"
            + "\n".join(f"| {name} | {'pass' if ok else '**FAIL**'} | {detail} |" for name, ok, detail in results) + "\n")


def write(con, cfg: dict, now: datetime | None = None) -> tuple[Path, list]:
    now = now or datetime.now(timezone.utc)
    res = run(con, cfg, now)
    p = config.ROOT / "docs" / "lanes" / "CHECKS.md"
    p.write_text(markdown(res, now, cfg))
    return p, res


def telegram_text(results: list[tuple[str, bool, str]]) -> str | None:
    fails = [r for r in results if not r[1]]
    if not fails:
        return None
    return "CHECK FAILED (not a bet)\n" + "\n".join(f"- {n}: {d}" for n, _, d in fails) + "\nDetails: docs/lanes/CHECKS.md"
