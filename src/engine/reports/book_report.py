"""How Wagerhouse's lines compare with the market, from the stored snapshots."""
from __future__ import annotations

from statistics import mean


def build(con) -> str:
    rows = con.execute("""
        SELECT w.sport, w.event_id, w.ts_utc, w.home_spread, m.home_spread, w.total, m.total
        FROM line_snapshots w JOIN line_snapshots m
          ON w.event_id = m.event_id AND w.ts_utc = m.ts_utc
        WHERE w.source = 'wagerhouse' AND m.source = 'draftkings'""").fetchall()
    polls = con.execute("SELECT count(*), sum(CASE WHEN ok THEN 1 ELSE 0 END), min(ts_utc), max(ts_utc) FROM polls").fetchone()
    out = ["# Wagerhouse against the market\n"]
    if not rows:
        return "\n".join(out + ["No paired readings yet. Run `engine poll --force` or wait for the schedule.\n"])
    out.append(f"{polls[0]} reads ({polls[1]} good) between {polls[2]:%b %-d %H:%M} and {polls[3]:%b %-d %H:%M} UTC. "
               f"{len(rows)} paired readings on {len({r[1] for r in rows})} games.\n")
    out.append("| Sport | Paired readings | Same spread | Avg gap when different | Favorite lays more at Wagerhouse | Same total | Total higher at Wagerhouse |")
    out.append("|---|---|---|---|---|---|---|")
    for sport in sorted({r[0] for r in rows}):
        rs = [r for r in rows if r[0] == sport]
        sp = [(r[3], r[4]) for r in rs if r[3] is not None and r[4] is not None]
        tt = [(r[5], r[6]) for r in rs if r[5] is not None and r[6] is not None]
        same = sum(a == b for a, b in sp)
        gaps = [abs(a - b) for a, b in sp if a != b]
        fav_more = sum(abs(a) > abs(b) for a, b in sp if a != b and a * b > 0)
        t_same = sum(a == b for a, b in tt)
        t_high = sum(a > b for a, b in tt)
        pc = lambda n, d: f"{100 * n / d:.0f}%" if d else "n/a"
        out.append(f"| {sport} | {len(rs)} | {pc(same, len(sp))} | {mean(gaps):.2f} pts | "
                   f"{pc(fav_more, len(gaps))} of gaps | {pc(t_same, len(tt))} | {pc(t_high, len(tt) - t_same)} of gaps |"
                   if gaps else f"| {sport} | {len(rs)} | {pc(same, len(sp))} | none | n/a | {pc(t_same, len(tt))} | {pc(t_high, len(tt) - t_same)} of gaps |")
    # lag: market moved between two reads; did Wagerhouse move in the same read?
    seq = con.execute("""
        SELECT event_id, source, ts_utc, home_spread FROM line_snapshots
        WHERE home_spread IS NOT NULL ORDER BY event_id, ts_utc""").fetchall()
    by: dict = {}
    for eid, src, ts, hs in seq:
        by.setdefault(eid, {}).setdefault(src, []).append((ts, hs))
    moved = followed = 0
    for eid, d in by.items():
        mk, wh = d.get("draftkings", []), dict(d.get("wagerhouse", []))
        for (t0, a), (t1, b) in zip(mk, mk[1:]):
            if a != b and t0 in wh and t1 in wh:
                moved += 1
                followed += wh[t0] != wh[t1]
    out.append("")
    out.append(f"Lag: the market spread changed between two reads {moved} times; Wagerhouse changed in the same read "
               f"{followed} of those." if moved else "Lag: no market moves captured between reads yet.")
    out.append("\nThis needs about three weeks of reads before it means much.\n")
    return "\n".join(out)
