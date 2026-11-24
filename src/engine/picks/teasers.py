"""NFL Wong teasers, paper first (review 14 section 2f and 3; Kylor approved 2026-11-23; decision 0014).

Why: Wagerhouse pays -110 on a 2-team, 6-point teaser (his own tickets: to-win / risk = 0.909), so each leg must win 72.4%. NFL favorites of
-7.5 to -8.5 and underdogs of +1.5 to +2.5, teased through both 3 and 7, won 75.8% on 264 legs in 2023-2026 with the total at 49 or lower, and
75 to 79% in every era since 2010 (nflverse closes; `scripts/research14/teaser.py`). The edge comes from how NFL games land on 3 and 7, not from a
price gap or a forecast. It is the opposite of the 13-point teasers the audit graded as a leak.

What this does:
  * On every read, each NFL game side at Wagerhouse whose spread is in a Wong range and whose total is at or under `teasers.max_total` is frozen
    the first time it is seen (`teaser_legs`): the Wagerhouse number, the teased number, the total, the kickoff, the rule version. Never updated.
  * Each leg is graded after the game at its teased number (W, L, P), with Pinnacle's last spread before kickoff stored for reference.
  * Legs are paired in the order they were first seen, within the same NFL week (Tuesday to Monday) and from different games, into 2-team tickets
    for the record. A ticket wins only if both legs win; a push leg makes the ticket a one-leg bet, graded as void here (house rules vary).
  * Real money since 2026-11-23 (Kylor: "yes", decision 0019): whenever two open legs from different games are not yet in a ticket, a 2-team
    ticket is formed and sent to Telegram as an A pick (1 NFL unit; the NFL stop counts teaser tickets, and the weekly cap applies; decision 0027).
    `teasers.real_money: false` turns it back to paper. The kill rule: fewer than 72.4% of legs win after 150 graded, or Wagerhouse's 2-team 6-point
    price is no longer -110 (checked by Kylor, recorded in config as `teasers.price`).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine.odds import snapshots as snap

SCHEMA = """
CREATE TABLE IF NOT EXISTS teaser_legs (
  leg_key VARCHAR PRIMARY KEY, first_seen_utc TIMESTAMP, event_id VARCHAR, game VARCHAR, side VARCHAR, team VARCHAR,
  line DOUBLE, teased_line DOUBLE, total DOUBLE, kickoff_utc TIMESTAMP, nfl_week VARCHAR, rule_version VARCHAR);
CREATE TABLE IF NOT EXISTS teaser_tickets (
  ticket_key VARCHAR PRIMARY KEY, sent_utc TIMESTAMP, leg_a VARCHAR, leg_b VARCHAR, units DOUBLE, dollars DOUBLE, price DOUBLE, text VARCHAR);
CREATE TABLE IF NOT EXISTS teaser_grades (
  leg_key VARCHAR PRIMARY KEY, team_margin INTEGER, result VARCHAR, pinnacle_close DOUBLE, graded_utc TIMESTAMP);
"""
DEFAULTS = {"enabled": True, "real_money": True, "points": 6.0, "price": -110, "max_total": 49.0,
            "favorite": [-8.5, -7.5], "underdog": [1.5, 2.5], "kill_after_legs": 300}


def settings(cfg: dict) -> dict:
    return {**DEFAULTS, **(cfg.get("teasers") or {})}


def breakeven(price: float) -> float:
    """Per-leg win rate a 2-team teaser at this American price needs."""
    dec = 1 + (100 / abs(price) if price < 0 else price / 100)
    return (1 / dec) ** 0.5


def nfl_week(kick: datetime) -> str:
    """NFL weeks run Tuesday to Monday; label a week by its Tuesday (UTC date, shifted 10 hours so Monday night stays in its week)."""
    d = (kick - timedelta(hours=10)).date()
    return (d - timedelta(days=(d.weekday() - 1) % 7)).isoformat()


def eligible(spread: float | None, total: float | None, st: dict) -> bool:
    """`spread` is this side's own spread (negative = favorite)."""
    if spread is None or total is None or total > st["max_total"]:
        return False
    lo, hi = st["favorite"]
    ulo, uhi = st["underdog"]
    return lo <= spread <= hi or ulo <= spread <= uhi


def legs_from(snaps: list, now: datetime, st: dict) -> list[dict]:
    """Eligible legs in one read's Wagerhouse NFL snapshots. Pure."""
    out = []
    for s in snaps:
        if s.source != snap.WH or s.sport != "NFL" or s.start is None or s.start <= now or s.home_spread is None:
            continue
        for side, team, spread in (("home", s.home, s.home_spread), ("away", s.away, -s.home_spread)):
            if eligible(spread, s.total, st):
                out.append({"key": f"{s.event_id}|{side}", "event_id": s.event_id, "game": f"{s.away} at {s.home}", "side": side, "team": team,
                            "line": spread, "teased": spread + st["points"], "total": s.total, "kick": s.start})
    return out


def scan(cfg: dict, con, snaps: list, now: datetime, send: bool = True) -> list[str]:
    """Freeze new eligible legs from this read. Never raises into the read. send=False (poll --no-send) never reaches Telegram."""
    st = settings(cfg)
    if not st["enabled"]:
        return []
    out = []
    try:
        con.execute(SCHEMA)
        from engine import version
        rv = version.stamp(cfg, con)
        for leg in legs_from(snaps, now, st):
            if con.execute("SELECT 1 FROM teaser_legs WHERE leg_key=?", [leg["key"]]).fetchone():
                continue
            con.execute("INSERT INTO teaser_legs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        [leg["key"], now.replace(tzinfo=None), leg["event_id"], leg["game"], leg["side"], leg["team"], leg["line"], leg["teased"],
                         leg["total"], leg["kick"].astimezone(timezone.utc).replace(tzinfo=None), nfl_week(leg["kick"]), rv])
            out.append(f"teaser leg (paper): {leg['team']} {leg['line']:+g} -> {leg['teased']:+g}, total {leg['total']:g}, {leg['game']}")
        out += tickets_to_send(cfg, con, now, send=send)
    except Exception as e:
        out.append(f"teaser scan failed: {type(e).__name__}: {e}")
    return out


def tickets_to_send(cfg: dict, con, now: datetime, send: bool = True, sender=None) -> list[str]:
    """Pair open legs (not yet in a ticket, different games, first seen first) into 2-team tickets and alert. Real money only if enabled."""
    st = settings(cfg)
    if not st.get("real_money"):
        return []
    from engine import config
    from engine.picks import playbook
    used = {r[0] for r in con.execute("SELECT leg_a FROM teaser_tickets UNION SELECT leg_b FROM teaser_tickets").fetchall()}
    legs = [r for r in con.execute("SELECT leg_key, event_id, game, team, line, teased_line, total, kickoff_utc FROM teaser_legs "
                                   "WHERE kickoff_utc > ? ORDER BY first_seen_utc", [now.replace(tzinfo=None)]).fetchall() if r[0] not in used]
    out, tz = [], config.display_tz(cfg)
    down = playbook.down_units(con, "NFL", cfg)      # NFL picks plus teaser tickets, in NFL units (decision 0027)
    while len(legs) >= 2:
        a = legs.pop(0)
        j = next((i for i, b in enumerate(legs) if b[1] != a[1]), None)
        if j is None:
            break
        b = legs.pop(j)
        unit = config.unit_for(cfg, "NFL")
        units, dollars, note = playbook.stake(playbook.settings(cfg), "A", now, down, unit)
        cap = playbook.settings(cfg)["game_cap_units"] * unit
        if dollars > 0 and any(playbook.game_exposure(con, ev) + dollars > cap + 1e-9 for ev in (a[1], b[1])):
            units, dollars, note = 0.0, 0.0, f"paper: a game in this ticket already carries money; the cap is one unit (${cap:g}) a game (decision 0025)"
        elif dollars > 0:
            weekly = playbook.over_weekly_cap(con, cfg, dollars, now)
            if weekly:
                units, dollars, note = 0.0, 0.0, weekly
        fav, dog = st["favorite"], st["underdog"]
        lines = []
        for leg in (a, b):
            k = leg[7].replace(tzinfo=timezone.utc).astimezone(tz)
            lines.append(f"{leg[3]} {leg[5]:+g} (from {leg[4]:+g}), {leg[2]}, {k:%a %-I:%M %p} MT")
        head = "TEASER BET (A)" if dollars > 0 else "PAPER TEASER (A), DO NOT BET"
        text = (f"NFL · {head}\n2-team {st['points']:g}-point teaser at {st['price']:+d}:\n" + "\n".join(lines) +
                f"\nStake: ${dollars:g} ({note})\nOnly if each leg is still an underdog of {dog[0]:+g} to {dog[1]:+g} or a favorite of {fav[0]:g} to {fav[1]:g} "
                f"at Wagerhouse before teasing, and the 2-team {st['points']:g}-point price is still {st['price']:+d}.\n"
                f"Why: these legs cross 3 and 7; they won 75.8% in 2023-2026 against {breakeven(st['price']):.1%} needed (decision 0014).")
        con.execute("INSERT INTO teaser_tickets VALUES (?,?,?,?,?,?,?,?)", [f"{a[0]}+{b[0]}", now.replace(tzinfo=None), a[0], b[0], units, dollars, st["price"], text])
        out.append(text)
        delivered = False
        if send and units > 0:
            from engine.alerts import telegram
            try:        # a failed send is saved as not delivered and sent again on the next read (research 22, finding 1)
                delivered = (sender or telegram.send)(config.load_env(), text, "nfl_teasers", kind="bet")
            except Exception as e:
                out.append(f"NOT SENT ({type(e).__name__}: {e}); the next read sends it again: teaser {a[0]}+{b[0]}")
        try:        # keep every ticket's text (research 18: sent picks were not saved anywhere)
            con.execute("CREATE TABLE IF NOT EXISTS alerts_sent (key VARCHAR PRIMARY KEY, ts_utc TIMESTAMP, kind VARCHAR, text VARCHAR, delivered BOOLEAN)")
            con.execute("INSERT INTO alerts_sent VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING",
                        [f"teaser|{a[0]}+{b[0]}", now.replace(tzinfo=None), "bet" if units > 0 else "paper", text, bool(delivered)])
        except Exception:
            pass
    return out


def grade(con, scorer=None) -> list[str]:
    from engine.picks import grade as g
    scorer = scorer or g.final_score
    con.execute(SCHEMA)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    todo = con.execute("SELECT leg_key, event_id, side, teased_line, kickoff_utc FROM teaser_legs WHERE kickoff_utc <= ? "
                       "AND leg_key NOT IN (SELECT leg_key FROM teaser_grades)", [now]).fetchall()
    out = []
    for key, eid, side, teased, kick in todo:
        score = scorer("NFL", eid)
        if score is None:
            continue
        home, away = score
        margin = (home - away) if side == "home" else (away - home)
        v = margin + teased
        res = "W" if v > 0 else "L" if v < 0 else "P"
        close = con.execute("SELECT home_spread FROM line_snapshots WHERE event_id=? AND source=? AND ts_utc<=? AND home_spread IS NOT NULL "
                            "ORDER BY ts_utc DESC LIMIT 1", [eid, snap.SHARP, kick]).fetchone()
        con.execute("INSERT INTO teaser_grades VALUES (?,?,?,?,?)", [key, margin, res, None if close is None else close[0], now])
        out.append(f"TEASER LEG GRADED {key}: {res}")
    return out


def tickets(rows: list[tuple]) -> list[tuple[str, str]]:
    """rows: (leg_key, event_id, nfl_week, result or None), in first-seen order. Pairs legs within a week from different games.
    Returns [(week, 'W'|'L'|'void'|'open')]. Pure."""
    out, waiting = [], {}
    for key, eid, week, res in rows:
        w = waiting.get(week)
        if w is None or w[1] == eid:
            if w is None:
                waiting[week] = (key, eid, res)
            continue
        a, b = w[2], res
        del waiting[week]
        if a is None or b is None:
            out.append((week, "open"))
        elif "L" in (a, b):
            out.append((week, "L"))
        elif "P" in (a, b):
            out.append((week, "void"))
        else:
            out.append((week, "W"))
    return out


def record(con, cfg: dict) -> dict:
    st = settings(cfg)
    con.execute(SCHEMA)
    rows = con.execute("SELECT l.leg_key, l.event_id, l.nfl_week, g.result FROM teaser_legs l LEFT JOIN teaser_grades g USING (leg_key) "
                       "ORDER BY l.first_seen_utc").fetchall()
    w = sum(r[3] == "W" for r in rows)
    l = sum(r[3] == "L" for r in rows)
    p = sum(r[3] == "P" for r in rows)
    t = tickets(rows)
    tw, tl = sum(x[1] == "W" for x in t), sum(x[1] == "L" for x in t)
    be = breakeven(st["price"])
    dec = 1 + 100 / abs(st["price"]) if st["price"] < 0 else 1 + st["price"] / 100
    units = tw * (dec - 1) - tl
    rate = w / (w + l) if w + l else None
    real = con.execute("""SELECT t.ticket_key, t.units, t.price, ga.result, gb.result FROM teaser_tickets t
                          LEFT JOIN teaser_grades ga ON ga.leg_key=t.leg_a LEFT JOIN teaser_grades gb ON gb.leg_key=t.leg_b""").fetchall()
    rw = rl = 0
    real_units = 0.0
    for _, u, pr, a, b in real:
        if a is None or b is None:
            continue
        if "L" in (a, b):
            rl += 1
            real_units -= u
        elif "P" not in (a, b):
            rw += 1
            real_units += u * (100 / abs(pr) if pr < 0 else pr / 100)
    status = "testing"
    if w + l >= st["kill_after_legs"]:
        status = "passed" if rate >= be else "failed"
    return {"legs": len(rows), "graded": w + l + p, "w": w, "l": l, "p": p, "rate": rate, "breakeven": be, "tickets_w": tw, "tickets_l": tl,
            "units": round(units, 2), "status": status, "tickets_sent": len(real), "real_w": rw, "real_l": rl, "real_units": round(real_units, 2)}


def record_text(rec: dict, cfg: dict) -> str:
    st = settings(cfg)
    head = "Real money" if st.get("real_money") else "Paper only"
    if not rec["legs"]:
        return f"{head}. No eligible legs seen yet. Needs {rec['breakeven']:.1%} of legs to win at {st['price']:+d}."
    rate = "n/a" if rec["rate"] is None else f"{rec['rate']:.1%}"
    sent = f" Tickets sent: {rec['tickets_sent']} ({rec['real_w']}-{rec['real_l']}, {rec['real_units']:+.2f} units)." if rec.get("tickets_sent") else ""
    return (f"{head}.{sent} {rec['legs']} legs seen, {rec['graded']} graded: {rec['w']}-{rec['l']}-{rec['p']} ({rate}; needs {rec['breakeven']:.1%} at "
            f"{st['price']:+d}). Paired tickets {rec['tickets_w']}-{rec['tickets_l']}, {rec['units']:+.2f} units. Judged at {st['kill_after_legs']} graded legs.")


def card(con, cfg: dict, now: datetime) -> str:
    """docs/cards/<date>-nfl-teasers.md: this week's open legs and the record."""
    from engine import config
    st = settings(cfg)
    con.execute(SCHEMA)
    tz = config.display_tz(cfg)
    rec = record(con, cfg)
    open_legs = con.execute("SELECT game, team, line, teased_line, total, kickoff_utc, first_seen_utc FROM teaser_legs WHERE kickoff_utc > ? "
                            "ORDER BY kickoff_utc", [now.replace(tzinfo=None)]).fetchall()
    out = ["# NFL Wong teasers", "",
           f"Rule: a 2-team, {st['points']:g}-point NFL teaser at Wagerhouse's {st['price']:+d}. Each leg is a favorite of {st['favorite'][0]:g} to "
           f"{st['favorite'][1]:g} or an underdog of {st['underdog'][0]:+g} to {st['underdog'][1]:+g}, teased through 3 and 7, total at or under {st['max_total']:g}. "
           "Legs are frozen at the first Wagerhouse number seen. Why: docs/research/14-deep-review.md (2f) and decision 0014.", "",
           f"**Record:** {record_text(rec, cfg)}", "", "## Open legs", ""]
    if not open_legs:
        out.append("None right now.")
    else:
        out += ["| Game | Leg | Teased to | Total | Kickoff (MT) | First seen (MT) |", "|---|---|---|---|---|---|"]
        for game, team, line, teased, total, kick, seen in open_legs:
            k = kick.replace(tzinfo=timezone.utc).astimezone(tz)
            f = seen.replace(tzinfo=timezone.utc).astimezone(tz)
            out.append(f"| {game} | {team} {line:+g} | {team} {teased:+g} | {total:g} | {k:%a %-I:%M %p} | {f:%a %-I:%M %p} |")
        out += ["", "Tickets are formed from these legs in the order they were first seen and sent to Telegram (real money, decision 0019)."]
    return "\n".join(out) + "\n"
