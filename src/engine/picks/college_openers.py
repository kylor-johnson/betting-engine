"""College openers on paper (research 23 T4, decision 0034).

Research 23 found the college script's own number knows something Wagerhouse-style openers miss: from the opener the line moved toward our
number by about 0.3 points on sides and 0.4 on totals (2023-2026), too little to beat -110 on its own. This module keeps a forward record of
that signal at the book Kylor actually uses, at $0:

- On each hourly read, every college game Wagerhouse has posted for the first time in the last `max_age_hours` gets our own number (the
  college script, not blended) compared with Wagerhouse's FIRST number we saw. Where we differ by `side_points`+ on the side or
  `total_points`+ on the total, a paper pick is frozen at that first number. One pick per game and market, frozen forever.
- After the game: the move from that number to the close (Pinnacle's last number before kickoff, else Wagerhouse's) in our direction, and
  the result at the frozen number.
- `docs/lanes/COLLEGE-OPENERS.md` shows the record, the average move, the luck range and the kill rule: after `kill_after` graded picks,
  an average move under `min_move` points or a record under 52.4% means turn it off.

Nothing here reaches Telegram or stakes anything.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from engine import config
from engine.odds import snapshots as snap

SCHEMA = """
CREATE TABLE IF NOT EXISTS college_opener_picks (
  key VARCHAR PRIMARY KEY, event_id VARCHAR, game VARCHAR, market VARCHAR, side VARCHAR, opener_line DOUBLE, opener_ts TIMESTAMP,
  own DOUBLE, issued_utc TIMESTAMP, kick_utc TIMESTAMP);
CREATE TABLE IF NOT EXISTS college_opener_seen (event_id VARCHAR, market VARCHAR, ts_utc TIMESTAMP, PRIMARY KEY (event_id, market));
CREATE TABLE IF NOT EXISTS college_opener_grades (
  key VARCHAR PRIMARY KEY, close_line DOUBLE, move DOUBLE, result VARCHAR, graded_utc TIMESTAMP);
"""
REPORT = config.ROOT / "docs" / "lanes" / "COLLEGE-OPENERS.md"


def settings(cfg: dict) -> dict:
    c = ((cfg.get("models") or {}).get("college_openers") or {})
    return {"enabled": bool(c.get("enabled", False)), "side_points": float(c.get("side_points", 3.0)),
            "total_points": float(c.get("total_points", 4.0)), "max_age_hours": float(c.get("max_age_hours", 72)),
            "kill_after": int(c.get("kill_after", 150)), "min_move": float(c.get("min_move", 0.25))}


def _first_numbers(con, now: datetime, max_age: float) -> list[tuple]:
    """Wagerhouse's first stored college number for every game not yet started, per market (it often posts the spread before the total), if
    first seen within max_age hours. Rows: (event, away, home, start, home spread or None, total or None, first seen)."""
    since = (now - timedelta(hours=max_age)).replace(tzinfo=None)
    out = []
    for col in ("home_spread", "total"):
        for eid, away, home, start, line, ts in con.execute(f"""
            SELECT s.event_id, s.away, s.home, s.start_utc, s.{col}, s.ts_utc
            FROM line_snapshots s
            JOIN (SELECT event_id, min(ts_utc) AS first_ts FROM line_snapshots
                  WHERE source=? AND sport='College' AND {col} IS NOT NULL GROUP BY 1) f
              ON f.event_id = s.event_id AND f.first_ts = s.ts_utc
            WHERE s.source=? AND s.sport='College' AND s.start_utc > ? AND f.first_ts >= ? AND s.{col} IS NOT NULL""",
                                                               [snap.WH, snap.WH, now.replace(tzinfo=None), since]).fetchall():
            out.append((eid, away, home, start, line, None, ts) if col == "home_spread" else (eid, away, home, start, None, line, ts))
    return out


def picks_for(first: tuple, own_margin: float, own_total: float, st: dict) -> list[dict]:
    """The paper picks for one game: our number against Wagerhouse's first number. own_margin is home minus away."""
    eid, away, home, start, hs, tot, ts = first
    out = []
    if hs is not None:
        d = own_margin - (-hs)
        if abs(d) >= st["side_points"]:
            out.append({"market": "side", "side": "home" if d > 0 else "away", "opener_line": hs, "own": own_margin})
    if tot is not None:
        d = own_total - tot
        if abs(d) >= st["total_points"]:
            out.append({"market": "total", "side": "over" if d > 0 else "under", "opener_line": tot, "own": own_total})
    for p in out:
        p.update(key=f"{eid}|{p['market']}|{p['side']}", event_id=eid, game=f"{away} at {home}", opener_ts=ts, kick_utc=start)
    return out


def log(con, cfg: dict, now: datetime, games: list[dict] | None = None) -> list[str]:
    """Freeze new paper picks. `games` = playbook.live_games(con, now, 'College')[0] (passed in to avoid a second model fit)."""
    st = settings(cfg)
    if not st["enabled"]:
        return []
    con.execute(SCHEMA)
    firsts = _first_numbers(con, now, st["max_age_hours"])
    if not firsts:
        return []
    if games is None:
        from engine.picks import playbook
        games, _ = playbook.live_games(con, now, "College")
    own = {str(g["event_id"]): (g["own_home"] - g["own_away"], g["own_home"] + g["own_away"]) for g in games}
    done = {(r[0], r[1]) for r in con.execute("SELECT event_id, market FROM college_opener_picks").fetchall()}
    seen = done | {(r[0], r[1]) for r in con.execute(
        "SELECT event_id, market FROM college_opener_seen").fetchall()}
    n = 0
    for f in firsts:
        eid = str(f[0])
        if eid not in own:
            continue
        market = "side" if f[4] is not None else "total"
        if (eid, market) in seen:
            continue
        con.execute("INSERT OR IGNORE INTO college_opener_seen VALUES (?,?,?)", [eid, market, now.replace(tzinfo=None)])
        for p in picks_for(f, *own[eid], st):
            con.execute("INSERT OR IGNORE INTO college_opener_picks VALUES (?,?,?,?,?,?,?,?,?,?)",
                        [p["key"], p["event_id"], p["game"], p["market"], p["side"], p["opener_line"], p["opener_ts"], p["own"],
                         now.replace(tzinfo=None), p["kick_utc"]])
            n += 1
    return [f"College openers: {n} new paper pick(s) frozen at Wagerhouse's first number."] if n else []


def grade_one(market: str, side: str, opener: float, close: float | None, home_pts: float, away_pts: float) -> tuple[float | None, str]:
    """(move toward us from the first number to the close, result at the first number). Side lines are the home spread."""
    sgn = 1 if side in ("home", "over") else -1
    if market == "side":
        move = None if close is None else (opener - close) * sgn      # home spread falling = market moving toward home
        x = (home_pts - away_pts + opener) * sgn
    else:
        move = None if close is None else (close - opener) * sgn
        x = (home_pts + away_pts - opener) * sgn
    return move, "W" if x > 0 else "L" if x < 0 else "P"


def _close(con, eid: str, kick, market: str):
    col = "home_spread" if market == "side" else "total"
    for src in (snap.SHARP, snap.WH):
        r = con.execute(f"SELECT {col} FROM line_snapshots WHERE source=? AND sport='College' AND event_id=? AND ts_utc < ? AND {col} IS NOT NULL "
                        "ORDER BY ts_utc DESC LIMIT 1", [src, eid, kick]).fetchone()
        if r:
            return r[0]
    return None


def grade(con, now: datetime) -> int:
    con.execute(SCHEMA)
    from engine.models import college_script
    scores = {str(g["id"]): (g.get("homeScore"), g.get("awayScore")) for g in college_script._games()}
    rows = con.execute("""SELECT p.key, p.event_id, p.market, p.side, p.opener_line, p.kick_utc FROM college_opener_picks p
                          LEFT JOIN college_opener_grades g ON g.key = p.key WHERE g.key IS NULL AND p.kick_utc < ?""",
                       [(now - timedelta(hours=4)).replace(tzinfo=None)]).fetchall()
    n = 0
    for key, eid, market, side, opener, kick in rows:
        hs, as_ = scores.get(str(eid), (None, None))
        if hs is None or as_ is None:
            continue
        move, res = grade_one(market, side, opener, _close(con, eid, kick, market), hs, as_)
        con.execute("INSERT INTO college_opener_grades VALUES (?,?,?,?,?)", [key, None, move, res, now.replace(tzinfo=None)])
        n += 1
    return n


def report(con, cfg: dict, now: datetime) -> str:
    st = settings(cfg)
    con.execute(SCHEMA)
    g = con.execute("""SELECT p.market, g.result, g.move FROM college_opener_picks p JOIN college_opener_grades g ON g.key = p.key""").fetchall()
    open_ = con.execute("""SELECT p.game, p.market, p.side, p.opener_line, p.own, p.kick_utc FROM college_opener_picks p
                           LEFT JOIN college_opener_grades g ON g.key = p.key WHERE g.key IS NULL ORDER BY p.kick_utc""").fetchall()
    tz = config.display_tz(cfg)
    lines = ["# College openers on paper", "",
             f"Generated {now.astimezone(tz):%a %b %-d, %-I:%M %p} MT by the hourly read. Research 23 (test T4), decision 0034. $0: never sent, never staked.", "",
             f"Every college game Wagerhouse posts gets our college script's own number against Wagerhouse's first number. Where we differ by "
             f"{st['side_points']:g}+ points on the side or {st['total_points']:g}+ on the total, a paper pick is frozen at that first number. "
             "Graded on the move to the close (Pinnacle's last number before kickoff) and on the result at the first number.", ""]
    rows = []
    for m in ("side", "total", "all"):
        sel = [x for x in g if m == "all" or x[0] == m]
        w, l, p = (sum(1 for x in sel if x[1] == r) for r in ("W", "L", "P"))
        mv = [x[2] for x in sel if x[2] is not None]
        n = w + l
        luck = f"{100 * (0.5 - 1.96 * math.sqrt(0.25 / n)):.0f}-{100 * (0.5 + 1.96 * math.sqrt(0.25 / n)):.0f}%" if n else "n/a"
        rows.append(f"| {m.title()} | {w}-{l}-{p} | {'' if not n else f'{100 * w / n:.1f}%'} | {luck} | "
                    f"{'' if not mv else f'{sum(mv) / len(mv):+.2f}'} | {len(mv)} |")
    lines += ["| Market | Record (W-L-P) | Win % | A coin flip lands in | Average move toward us (points) | Moves graded |",
              "|---|---|---|---|---|---|"] + rows + [""]
    mv_all = [x[2] for x in g if x[2] is not None]
    n_all = sum(1 for x in g if x[1] in ("W", "L"))
    if n_all >= st["kill_after"]:
        wins = sum(1 for x in g if x[1] == "W")
        avg = sum(mv_all) / len(mv_all) if mv_all else 0.0
        verdict = ("**Kill rule met: turn it off** (`models.college_openers.enabled: false`) with a decision note."
                   if avg < st["min_move"] or wins / n_all < 0.524 else "Kill rule not met: the signal is holding.")
    else:
        verdict = f"Kill rule checked at {st['kill_after']} graded picks ({n_all} so far): off if the average move is under {st['min_move']:g} points or the record is under 52.4%."
    lines += [verdict, "", "## Open", ""]
    if open_:
        lines += ["| Game | Pick | First number | Our number | Kickoff (MT) |", "|---|---|---|---|---|"]
        for game, market, side, line, own, kick in open_:
            if market == "side":
                pick = f"{'home' if side == 'home' else 'away'} {line if side == 'home' else -line:+g}"
                ours = f"home by {own:+.1f}"
            else:
                pick, ours = f"{side} {line:g}", f"{own:.1f}"
            lines.append(f"| {game} | {pick} | {line:g} | {ours} | {kick.replace(tzinfo=timezone.utc).astimezone(tz):%a %-I:%M %p} |")
    else:
        lines.append("None open.")
    return "\n".join(lines) + "\n"


def run(con, cfg: dict, now: datetime, games: list[dict] | None = None) -> list[str]:
    """Hourly read: freeze, grade, write the report. Never raises into the read."""
    if not settings(cfg)["enabled"]:
        return []
    try:
        out = log(con, cfg, now, games)
        grade(con, now)
        REPORT.write_text(report(con, cfg, now))
        return out
    except Exception as e:
        return [f"College openers failed: {type(e).__name__}: {e}"]
