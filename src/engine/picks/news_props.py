"""NBA news-timed props, a paper test (research 18, "what to build"; decision 0025).

The idea: when a regular is ruled out, the NBA props model moves his minutes and shots to his teammates. If Pinnacle has not moved those
teammates' props yet, the model's number is the early number. This is the one piece of the props model that clearly beat a plain average on
held-out seasons (research 08: points and pts+reb+ast), and the thin prop market does not pass news through quickly.

On every NBA props read:
  * a prop is a candidate when its projection names a teammate out ("out: ..." in the model's news), that teammate PLAYED in his team's last
    game (so the absence is new, not a long-term injury), and the first Out signal for him (official report, reporter post through Rotoworld,
    or the injury watcher) is no older than `window_min` minutes;
  * the model's chance (re-centred by models/calibrate.py) is compared with Pinnacle's no-vig chance at this read; the side the model favours
    is logged as a paper pick when it clears `min_edge` at Pinnacle's price;
  * Pinnacle's chance at the last read BEFORE the news is stored too, so we can see whether Pinnacle had already moved.

Graded on the result and on closing-line value: Pinnacle's no-vig chance of our side at its last read before tip (same line) minus its chance
when we logged it. Pass (decision 0025): average closing-line value above +4 points of chance over 100 picks. Never staked, never sent.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS news_prop_picks (
  pick_key VARCHAR PRIMARY KEY, first_seen_utc TIMESTAMP, sport VARCHAR, game VARCHAR, away VARCHAR, home VARCHAR, player_id VARCHAR,
  player VARCHAR, team VARCHAR, stat VARCHAR, side VARCHAR, line DOUBLE, price DOUBLE, pin_p_side DOUBLE, pin_p_side_before DOUBLE,
  model_p_side DOUBLE, edge DOUBLE, news VARCHAR, news_utc TIMESTAMP, minutes_after_news DOUBLE, kickoff_utc TIMESTAMP,
  close_p_side DOUBLE, clv DOUBLE, outcome DOUBLE, result VARCHAR, graded_utc TIMESTAMP);
"""
DEFAULTS = {"enabled": True, "window_min": 90, "min_edge": 0.04, "pass_clv": 0.04, "pass_n": 100}


def settings(cfg: dict) -> dict:
    return {**DEFAULTS, **(((cfg.get("playbook") or {}).get("news_props")) or {})}


def _dec(a: float) -> float:
    return 1 + a / 100 if a > 0 else 1 + 100 / abs(a)


def out_names(news: str) -> list[str]:
    """'out: A, B; second night...' -> ['A', 'B']."""
    for part in (news or "").split(";"):
        part = part.strip()
        if part.startswith("out:"):
            return [n.strip() for n in part[4:].split(",") if n.strip()]
    return []


def first_out_signal(con, name: str, now: datetime, hours: float = 36.0) -> datetime | None:
    """Earliest Out/Doubtful/not-playing signal for this player in the last `hours`, from every NBA news source we log."""
    from engine.models.props import norm_name
    n = norm_name(name)
    since = (now - timedelta(hours=hours)).replace(tzinfo=None)
    times = []
    for sql in ("SELECT min(ts_utc) FROM nba_injury_changes WHERE new_status IN ('Out', 'Doubtful') AND ts_utc >= ? AND {name} = ?",
                "SELECT min(coalesce(source_utc, posted_utc, seen_utc)) FROM player_news WHERE sport = 'NBA' AND signal = 'not playing' "
                "AND seen_utc >= ? AND {name} = ?",
                "SELECT min(seen_utc) FROM nba_official_status WHERE status IN ('Out', 'Doubtful') AND seen_utc >= ? AND {name} = ?"):
        col = "name" if "player_news" not in sql else "player"
        try:
            rows = con.execute(sql.replace("{name}", f"lower({col})").replace("lower(name) = ?", "lower(name) = ?"),
                               [since, n]).fetchall()
        except Exception:
            rows = []
        if not rows or rows[0][0] is None:
            # names are stored in different forms; fall back to a normalised comparison in Python
            try:
                tab = "nba_injury_changes" if "nba_injury_changes" in sql else "player_news" if "player_news" in sql else "nba_official_status"
                tcol = "ts_utc" if tab == "nba_injury_changes" else "coalesce(source_utc, posted_utc, seen_utc)" if tab == "player_news" else "seen_utc"
                cond = ("new_status IN ('Out', 'Doubtful')" if tab == "nba_injury_changes" else
                        "sport = 'NBA' AND signal = 'not playing'" if tab == "player_news" else "status IN ('Out', 'Doubtful')")
                seen = "ts_utc" if tab == "nba_injury_changes" else "seen_utc"
                cand = con.execute(f"SELECT {col}, {tcol} FROM {tab} WHERE {cond} AND {seen} >= ?", [since]).fetchall()
                hits = [t for nm, t in cand if nm and norm_name(str(nm)) == n and t is not None]
                if hits:
                    times.append(min(hits))
            except Exception:
                pass
        else:
            times.append(rows[0][0])
    times = [t if isinstance(t, datetime) else None for t in times]
    times = [t for t in times if t is not None]
    return min(times).replace(tzinfo=timezone.utc) if times else None


def played_last_game(model, team: str, name: str) -> bool:
    """True if this player appears in his team's most recent box score (so his absence tonight is new)."""
    from engine.models.props import norm_name
    try:
        recent = model.teams.recent[team]
        if not recent:
            return False
        last = recent[-1]
        return any(norm_name(model.names.get(p, "")) == norm_name(name) for p in last)
    except Exception:
        return False


def _pin_before(con, r: dict, before: datetime) -> float | None:
    row = con.execute("""SELECT market_p_over FROM prop_evals WHERE sport = 'NBA' AND player_id = ? AND stat = ? AND home = ? AND away = ?
                         AND line = ? AND ts_utc < ? ORDER BY ts_utc DESC LIMIT 1""",
                      [r["player_id"], r["stat"], r["home"], r["away"], r["line"], before.replace(tzinfo=None)]).fetchone()
    return None if row is None else row[0]


def log(con, cfg: dict, model, priced: list[dict], now: datetime, shifts: dict | None = None) -> list[str]:
    """Freeze new paper news-props picks from this read's priced NBA props. Pure apart from the table write. Never raises."""
    st = settings(cfg)
    if not st["enabled"]:
        return []
    from engine.models import calibrate
    con.execute(SCHEMA)
    out = []
    fresh_cache: dict[str, datetime | None] = {}
    for r in priced:
        names = out_names(r.get("news", ""))
        if not names or r.get("market_p_over") is None or r.get("model_p_over") is None:
            continue
        team = r.get("team", "")
        newest = None
        for nm in names:
            if not played_last_game(model, team, nm):
                continue
            if nm not in fresh_cache:
                fresh_cache[nm] = first_out_signal(con, nm, now)
            t = fresh_cache[nm]
            if t is not None and (newest is None or t > newest):
                newest = t
        if newest is None:
            continue
        mins = (now - newest).total_seconds() / 60
        if mins < 0 or mins > st["window_min"]:
            continue
        mp = calibrate.apply(float(r["model_p_over"]), shifts, r["stat"])
        pin = float(r["market_p_over"])
        side, price, p_model, p_pin = ("over", r["over_price"], mp, pin) if mp > pin else ("under", r["under_price"], 1 - mp, 1 - pin)
        if price is None:
            continue
        edge = p_model - 1 / _dec(price)
        if edge < st["min_edge"]:
            continue
        key = f"NBA|{r['player_id']}|{r['stat']}|{r['away']}|{r['home']}"
        if con.execute("SELECT 1 FROM news_prop_picks WHERE pick_key = ?", [key]).fetchone():
            continue
        before = _pin_before(con, r, newest)
        before_side = None if before is None else (before if side == "over" else 1 - before)
        start = r.get("start_utc")
        kick = datetime.fromisoformat(start.replace("Z", "+00:00")) if isinstance(start, str) else start
        con.execute("INSERT INTO news_prop_picks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [key, now.replace(tzinfo=None), "NBA", f"{r['away']} at {r['home']}", r["away"], r["home"], r["player_id"], r.get("player"),
                     team, r["stat"], side, r["line"], price, p_pin, before_side, p_model, edge, r.get("news", ""),
                     newest.replace(tzinfo=None), round(mins, 1), None if kick is None else kick.astimezone(timezone.utc).replace(tzinfo=None),
                     None, None, None, None, None])
        out.append(f"news prop (paper): {r.get('player')} {side} {r['line']:g} {r['stat']} at Pinnacle {int(price):+d}, edge {100 * edge:+.1f}%, "
                   f"{mins:.0f} min after the news")
    return out


def grade(con, now: datetime | None = None) -> int:
    """Close = Pinnacle's no-vig chance of our side at its last read before tip, same line; result from prop_evals."""
    from engine.picks.playbook import SAME_GAME_LOOSE
    con.execute(SCHEMA)
    now = (now or datetime.now(timezone.utc)).replace(tzinfo=None)
    n = 0
    for key, pid, stat, home, away, side, line, p_issue, kick in con.execute(
            "SELECT pick_key, player_id, stat, home, away, side, line, pin_p_side, kickoff_utc FROM news_prop_picks "
            "WHERE graded_utc IS NULL AND kickoff_utc < ?", [now]).fetchall():
        close = con.execute("""SELECT market_p_over FROM prop_evals WHERE sport = 'NBA' AND player_id = ? AND stat = ? AND home = ? AND away = ?
                               AND line = ? AND ts_utc < ? AND {SAME_GAME} ORDER BY ts_utc DESC LIMIT 1""".replace("{SAME_GAME}", SAME_GAME_LOOSE),
                            [pid, stat, home, away, line, kick, kick]).fetchone()
        res = con.execute("""SELECT outcome FROM prop_evals WHERE sport = 'NBA' AND player_id = ? AND stat = ? AND home = ? AND away = ?
                             AND outcome IS NOT NULL AND {SAME_GAME} LIMIT 1""".replace("{SAME_GAME}", SAME_GAME_LOOSE),
                          [pid, stat, home, away, kick]).fetchone()       # this game, not an earlier meeting (research 25)
        if res is None:
            continue
        cp = None if close is None else (close[0] if side == "over" else 1 - close[0])
        v = (res[0] - line) if side == "over" else (line - res[0])
        con.execute("UPDATE news_prop_picks SET close_p_side = ?, clv = ?, outcome = ?, result = ?, graded_utc = ? WHERE pick_key = ?",
                    [cp, None if cp is None else cp - p_issue, res[0], "W" if v > 0 else "L" if v < 0 else "P", now, key])
        n += 1
    return n


def record_markdown(con, cfg: dict) -> str:
    st = settings(cfg)
    con.execute(SCHEMA)
    n, w, l, clv, nclv = con.execute("""SELECT count(*), count(*) FILTER (result = 'W'), count(*) FILTER (result = 'L'), avg(clv), count(clv)
                                        FROM news_prop_picks WHERE graded_utc IS NOT NULL""").fetchone()
    open_n = con.execute("SELECT count(*) FROM news_prop_picks WHERE graded_utc IS NULL").fetchone()[0]
    moved = con.execute("""SELECT avg(pin_p_side - pin_p_side_before), count(pin_p_side_before) FROM news_prop_picks""").fetchone()
    verdict = ("not enough yet" if (nclv or 0) < st["pass_n"] else
               "PASSES (average closing-line value above the bar)" if clv is not None and clv > st["pass_clv"] else "FAILS")
    out = ["# NBA news-timed props, paper test (generated; do not edit)", "",
           "When a regular who played his team's last game is ruled out, the props model moves minutes and shots to his teammates. A teammate's "
           f"prop is logged here when the model's re-centred chance beats Pinnacle's price by {100 * st['min_edge']:.0f}+ points within "
           f"{st['window_min']} minutes of the first Out signal. Never staked, never sent (decision 0025).", "",
           f"Pass: average closing-line value above {100 * st['pass_clv']:+.0f} points of chance over {st['pass_n']} graded picks.", "",
           "| Graded | Record | Average closing-line value | Picks with a close | Open | Pinnacle had already moved toward us (average, points) | Verdict |",
           "|---|---|---|---|---|---|---|",
           f"| {n} | {w}-{l} | {'n/a' if clv is None else f'{100 * clv:+.1f}'} | {nclv} | {open_n} | "
           f"{'n/a' if moved[0] is None else f'{100 * moved[0]:+.1f} on {moved[1]}'} | {verdict} |", ""]
    rows = con.execute("""SELECT first_seen_utc, player, stat, side, line, price, edge, minutes_after_news, news, result, clv FROM news_prop_picks
                          ORDER BY first_seen_utc DESC LIMIT 30""").fetchall()
    if rows:
        out += ["| Logged (UTC) | Prop | Pinnacle price | Edge | Minutes after news | Why | Result | Closing-line value |", "|---|---|---|---|---|---|---|---|"]
        for ts, pl, stat, side, line, price, edge, mins, news, res, c in rows:
            out.append(f"| {ts:%a %b %-d %H:%M} | {pl} {side} {line:g} {stat} | {int(price):+d} | {100 * edge:+.1f}% | {mins:.0f} | {news} | "
                       f"{res or 'open'} | {'n/a' if c is None else f'{100 * c:+.1f}'} |")
    return "\n".join(out) + "\n"
