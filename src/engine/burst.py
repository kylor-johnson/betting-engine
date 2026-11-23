"""Fast reads in the windows where news lands (plan item 3, docs/research/12a-reading-2026-11-23.md).

The hourly read cannot say how many minutes Wagerhouse trails Pinnacle after a move. In a few short windows this reads Wagerhouse and
Pinnacle full-game lines every ten minutes (NFL only by default) and stores them as ordinary line snapshots, so the speed table in
`engine wh-edge` gets minute-level resolution and grading gets a nearer closing line.

It is deliberately light: no DraftKings, no props, no alerts, no research runs. Windows are in `config.yaml` (`burst:`), Mountain time:
Wednesday to Friday afternoon for practice reports, Sunday and the weekday-night games for inactives (about 90 minutes before kickoff).
A daily cap bounds the number of Wagerhouse sign-ins. A failed burst read is recorded in `burst_reads` and never alerts: the hourly
heartbeat is the alarm, and a fast read is a measurement, not a safety net.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine import config
from engine.odds import espn
from engine.odds import snapshots as snap
from engine.odds.wagerhouse import Wagerhouse

SCHEMA = "CREATE TABLE IF NOT EXISTS burst_reads (ts_utc TIMESTAMP, sport VARCHAR, ok BOOLEAN, wagerhouse_games INTEGER, pinnacle_games INTEGER, note VARCHAR);"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def in_window(cfg: dict, now: datetime, sport: str = "NFL") -> str | None:
    """The window ('HH:MM-HH:MM') this sport's fast reads are in right now (Mountain time), or None.
    `burst.sports.<SPORT>.windows` maps weekday to windows."""
    bc = cfg.get("burst") or {}
    if not bc.get("enabled"):
        return None
    local = now.astimezone(config.display_tz(cfg))
    sc = (bc.get("sports") or {}).get(sport) or {}
    for w in (sc.get("windows") or {}).get(DAYS[local.weekday()], []) or []:
        a, b = (x.strip() for x in str(w).split("-"))
        start = local.replace(hour=int(a[:2]), minute=int(a[3:5]), second=0, microsecond=0)
        end = local.replace(hour=int(b[:2]), minute=int(b[3:5]), second=0, microsecond=0)
        if start <= local <= end:
            return str(w)
    return None


def collect_light(wh: Wagerhouse, sport: str, now: datetime) -> tuple[list[snap.Snap], list[str]]:
    """Wagerhouse and Pinnacle full-game lines for one sport; the same matching as the hourly read, without the DraftKings calls."""
    from engine.picks import sources
    snaps, problems = [], []
    lines = [l for l in wh.lines(sport) if l.start and l.start > now]
    if not lines:
        return snaps, problems
    events = espn.upcoming(sport, now.date() - timedelta(days=1), now.date() + timedelta(days=snap.LOOKAHEAD_DAYS[sport]))
    sharp = {}
    for sl in sources.pinnacle(sport):
        near = [e for e in events if abs((e.start - sl.start).total_seconds()) < 12 * 3600]
        ev, how = espn.find_event(near, sl.away, sl.home)
        if ev is not None and how == "both teams":
            sharp[ev.event_id] = sl
    for l in lines:
        ev = snap.match_event(l, events)
        if ev is None:
            problems.append(f"{sport}: could not match {l.away} at {l.home} to an ESPN game")
            continue
        snaps.append(snap.Snap(now, snap.WH, sport, ev.event_id, l.away, l.home, ev.start, l.home_spread, l.home_spread_price,
                               l.away_spread_price, l.home_ml, l.away_ml, l.total, l.over_price, l.under_price))
        sl = sharp.get(ev.event_id)
        if sl is not None:
            snaps.append(snap.Snap(now, snap.SHARP, sport, ev.event_id, l.away, l.home, ev.start, sl.home_spread, sl.home_spread_price,
                                   sl.away_spread_price, sl.home_ml, sl.away_ml, sl.total, sl.over_price, sl.under_price))
    return snaps, problems


def reads_today(con, cfg: dict, now: datetime, sport: str = "NFL") -> int:
    con.execute(SCHEMA)
    local = now.astimezone(config.display_tz(cfg))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).replace(tzinfo=None)
    return con.execute("SELECT count(DISTINCT ts_utc) FROM burst_reads WHERE ts_utc >= ? AND sport = ?", [start, sport]).fetchone()[0]


def run(force: bool = False) -> tuple[int, list[str]]:
    cfg, env = config.load_config(), config.load_env()
    now = datetime.now(timezone.utc)
    bc = cfg.get("burst") or {}
    configured = list((bc.get("sports") or {}).keys())
    todo, out = [], []
    con = snap.connect(config.DB)
    try:
        for sport in configured:
            if not force and in_window(cfg, now, sport) is None:
                continue
            used, cap = reads_today(con, cfg, now, sport), int(((bc["sports"][sport] or {}).get("max_reads_per_day", 40)))
            if used >= cap and not force:
                out.append(f"{sport}: daily cap reached ({used} of {cap} fast reads); nothing read.")
                continue
            todo.append(sport)
    finally:
        con.close()
    if not todo:
        return 0, out or ["Outside the fast-read windows; nothing read."]
    allsnaps, rows = [], []
    wh = Wagerhouse(env.get("WAGERHOUSE_USER", ""), env.get("WAGERHOUSE_PASSWORD", ""))
    for sport in todo:
        try:
            s, problems = collect_light(wh, sport, now)
            allsnaps += s
            rows.append((now.replace(tzinfo=None), sport, True, sum(x.source == snap.WH for x in s), sum(x.source == snap.SHARP for x in s), "; ".join(problems)[:300]))
            out.append(f"{sport}: {rows[-1][3]} Wagerhouse and {rows[-1][4]} Pinnacle lines" + (f" ({len(problems)} unmatched)" if problems else ""))
        except Exception as e:      # recorded, never alerted
            msg = str(e) if isinstance(e, espn.SourceError) else f"{type(e).__name__}: {e}"
            rows.append((now.replace(tzinfo=None), sport, False, 0, 0, msg[:300]))
            out.append(f"{sport}: read failed: {msg}")
    con = snap.connect(config.DB)       # open only to write, after the network reads
    try:
        con.execute(SCHEMA)
        if allsnaps:
            snap.save(con, allsnaps)
        con.executemany("INSERT INTO burst_reads VALUES (?,?,?,?,?,?)", rows)
    finally:
        con.close()
    return (0 if all(r[2] for r in rows) else 1), out
