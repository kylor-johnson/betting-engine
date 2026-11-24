"""Three paper lanes (decision 0036, item 13; research 24, tests L1, F1 and D1b). $0, never sent, never staked.

- **L1, Wagerhouse trailing Pinnacle** (NFL, college, NBA): on each read, where Wagerhouse's full-game spread or total is 1+ point better
  for one side than Pinnacle's current number (0.5 when it crosses 3 or 7 in the NFL), a paper pick at Wagerhouse's number and price.
- **F1, early-week NFL numbers against public ratings**: Sunday 5pm to Tuesday 6am Mountain, where The Prediction Tracker's average of
  public systems and Wagerhouse's NFL spread differ by 1.5+ points, a paper pick on the ratings' side at Wagerhouse's number. Research 24
  test F1: the line moved toward the ratings 69.5% of the time in 2023-2025.
- **D1b, NFL derivatives**: our script's disagreement with Pinnacle's full-game line, carried into Pinnacle's first-half spread and total
  (0.62 and 0.47 of it, research 04 test E) and into game team totals (our blended team points), priced on bell curves (first-half margin
  9.88, first-half total 8.62, team points 9.0; 2022-2025); a paper pick at 4%+ of win chance, frozen at Pinnacle's line and price.

Every pick is frozen at first sight and graded after the game on closing-line value against Pinnacle's last read before the start (win
chance at the frozen line, minus the chance its price needed) and on the result. `docs/lanes/PAPER-LANES.md` shows each lane's record,
average closing-line value with its 95% range, the luck range and the kill rule (150 graded: off unless closing-line value is above zero).
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from statistics import NormalDist

from engine import config
from engine.odds import snapshots as snap
from engine.odds.math import american_to_decimal, no_vig, touches_key

SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_lane_picks (
  key VARCHAR PRIMARY KEY, lane VARCHAR, sport VARCHAR, event_id VARCHAR, game VARCHAR, market VARCHAR, period VARCHAR, side VARCHAR,
  line DOUBLE, price DOUBLE, ref_line DOUBLE, ours DOUBLE, edge DOUBLE, issued_utc TIMESTAMP, kick_utc TIMESTAMP, note VARCHAR);
CREATE TABLE IF NOT EXISTS paper_lane_grades (
  key VARCHAR PRIMARY KEY, close_line DOUBLE, clv DOUBLE, result VARCHAR, graded_utc TIMESTAMP);
"""
REPORT = config.ROOT / "docs" / "lanes" / "PAPER-LANES.md"
LANES = {"L1": "Wagerhouse trailing Pinnacle", "F1": "Early-week NFL against public ratings", "D1b": "NFL derivatives (halves, team totals)"}
SD = {("spread", "1st Half"): 9.88, ("total", "1st Half"): 8.62, ("team_total", "Game"): 9.0}
FRESH = timedelta(minutes=75)          # both books' numbers must come from the last read


def settings(cfg: dict) -> dict:
    c = ((cfg.get("models") or {}).get("paper_lanes") or {})
    return {"enabled": bool(c.get("enabled", False)), "l1": bool(c.get("l1", True)), "f1": bool(c.get("f1", True)), "d1b": bool(c.get("d1b", True)),
            "l1_points": float(c.get("l1_points", 1.0)), "l1_key_points": float(c.get("l1_key_points", 0.5)),
            "f1_gap": float(c.get("f1_gap", 1.5)), "d1b_edge": float(c.get("d1b_edge", 0.04)), "kill_after": int(c.get("kill_after", 150))}


def need(price: float) -> float:
    return 1 / american_to_decimal(price)


def chance(mean: float, line: float, sd: float, side: str, market: str) -> float:
    """Win chance (pushes split out) for a bet on a normal outcome. Spreads: `mean` is the home margin, `line` the HOME spread, side
    home/away. Totals and team totals: `mean` is points, side over/under."""
    nd = NormalDist(mean, sd)
    cut = -line if market == "spread" else line
    if cut == int(cut):
        lo, hi = nd.cdf(cut - 0.5), nd.cdf(cut + 0.5)
    else:
        lo = hi = nd.cdf(cut)
    above, below = 1 - hi, lo
    p_above = above / (above + below) if above + below else 0.5
    return p_above if side in ("home", "over") else 1 - p_above


def fair_mean(line: float, price_a: float | None, price_b: float | None, sd: float, market: str) -> float:
    """The outcome mean a two-way price implies: the line moved by the no-vig lean (price_a = home or over)."""
    base = -line if market == "spread" else line
    if price_a is None or price_b is None:
        return base
    p = min(max(no_vig(price_a, price_b)[0], 0.02), 0.98)
    return base + sd * NormalDist().inv_cdf(p)


def _latest(con, sport: str, source: str, now: datetime) -> dict:
    rows = con.execute("""SELECT event_id, ts_utc, away, home, start_utc, home_spread, home_spread_price, away_spread_price, total, over_price,
                                 under_price FROM (SELECT *, row_number() OVER (PARTITION BY event_id ORDER BY ts_utc DESC) rn
                                 FROM line_snapshots WHERE source = ? AND sport = ? AND start_utc > ?) WHERE rn = 1""",
                       [source, sport, now.astimezone(timezone.utc).replace(tzinfo=None)]).fetchall()
    return {r[0]: r for r in rows}


def _freeze(con, p: dict, now: datetime) -> bool:
    if con.execute("SELECT 1 FROM paper_lane_picks WHERE key = ?", [p["key"]]).fetchone():
        return False
    con.execute("INSERT INTO paper_lane_picks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [p["key"], p["lane"], p["sport"], p["event_id"], p["game"], p["market"], p["period"], p["side"], p["line"], p["price"],
                 p.get("ref_line"), p.get("ours"), p.get("edge"), now.astimezone(timezone.utc).replace(tzinfo=None), p["kick"], p.get("note", "")])
    return True


# ---------- L1 ----------
def l1_picks(wh, pin, sport: str, st: dict) -> list[dict]:
    """Paper picks for one game where Wagerhouse is better than Pinnacle by the lane's margin. Rows as `_latest` returns them."""
    eid, _, away, home, start, hs, hsp, asp, tot, op, up = wh
    _, _, _, _, _, phs, _, _, ptot, _, _ = pin
    out = []
    if hs is not None and phs is not None:
        d = hs - phs                    # positive: the home side gets more at Wagerhouse
        need_pts = st["l1_key_points"] if sport == "NFL" and touches_key(phs, hs) else st["l1_points"]
        if abs(d) >= need_pts:
            side = "home" if d > 0 else "away"
            price = hsp if side == "home" else asp
            if price is not None:
                out.append({"market": "spread", "side": side, "line": hs, "price": price, "ref_line": phs,
                            "note": f"Wagerhouse {hs:+g}, Pinnacle {phs:+g} (home spread)"})
    if tot is not None and ptot is not None and abs(tot - ptot) >= st["l1_points"]:
        side = "under" if tot > ptot else "over"
        price = up if side == "under" else op
        if price is not None:
            out.append({"market": "total", "side": side, "line": tot, "price": price, "ref_line": ptot,
                        "note": f"Wagerhouse {tot:g}, Pinnacle {ptot:g}"})
    for p in out:
        p.update(key=f"L1|{sport}|{eid}|{p['market']}|{p['side']}", lane="L1", sport=sport, event_id=eid, game=f"{away} at {home}",
                 period="Game", kick=start)
    return out


def log_l1(con, cfg: dict, now: datetime, st: dict) -> int:
    n = 0
    for sport in ("NFL", "College", "NBA"):
        wh, pin = _latest(con, sport, snap.WH, now), _latest(con, sport, snap.SHARP, now)
        cutoff = now.astimezone(timezone.utc).replace(tzinfo=None) - FRESH
        for eid, w in wh.items():
            p = pin.get(eid)
            if p is None or w[1] < cutoff or p[1] < cutoff:
                continue
            for pk in l1_picks(w, p, sport, st):
                n += _freeze(con, pk, now)
    return n


# ---------- F1 ----------
def f1_window(cfg: dict, now: datetime) -> bool:
    """Sunday 5pm to Tuesday 6am Mountain: the early-week numbers, before the week's public ratings are priced in."""
    loc = now.astimezone(config.display_tz(cfg))
    return (loc.weekday() == 6 and loc.hour >= 17) or loc.weekday() == 0 or (loc.weekday() == 1 and loc.hour < 6)


def f1_pick(avg_home_margin: float, wh_home_spread: float, gap: float) -> str | None:
    """'home' or 'away' when the ratings' home margin and Wagerhouse's differ by `gap`+ points, else None."""
    d = avg_home_margin - (-wh_home_spread)
    if abs(d) < gap:
        return None
    return "home" if d > 0 else "away"


def _ratings(cfg: dict, now: datetime) -> list[dict]:
    """Today's Prediction Tracker NFL file: from the dated copy if one was saved today, else fetched (and saved)."""
    import csv
    from engine.picks import sources
    d = config.DATA / "raw" / "tracker"
    p = d / f"NFL_{datetime.now(timezone.utc):%Y-%m-%d}.csv"
    if not p.exists():
        return sources.tracker("NFL", d)
    out = []
    for r in csv.DictReader(p.open()):
        try:
            out.append({"home": r["home"].strip(), "road": r["road"].strip(), "avg_home_margin": float(r["lineavg"])})
        except (KeyError, ValueError):
            continue
    return out


def log_f1(con, cfg: dict, now: datetime, st: dict) -> int:
    if not f1_window(cfg, now):
        return 0
    from engine.odds import espn
    from engine.picks import slate
    wh = _latest(con, "NFL", snap.WH, now)
    if not wh:
        return 0
    events = espn.upcoming("NFL", now.date(), now.date() + timedelta(days=9))
    by_eid = {}
    for t in _ratings(cfg, now):
        e = slate._find(events, t["home"], t["road"])
        if e:
            by_eid[e.event_id] = t
    n = 0
    for eid, w in wh.items():
        t = by_eid.get(eid)
        hs = w[5]
        if t is None or hs is None:
            continue
        side = f1_pick(t["avg_home_margin"], hs, st["f1_gap"])
        if side is None:
            continue
        price = w[6] if side == "home" else w[7]
        if price is None:
            continue
        n += _freeze(con, {"key": f"F1|NFL|{eid}|spread", "lane": "F1", "sport": "NFL", "event_id": eid, "game": f"{w[2]} at {w[3]}",
                           "market": "spread", "period": "Game", "side": side, "line": hs, "price": price, "ref_line": -t["avg_home_margin"],
                           "ours": t["avg_home_margin"], "kick": w[4],
                           "note": f"ratings home margin {t['avg_home_margin']:+.1f}, Wagerhouse home spread {hs:+g}"}, now)
    return n


# ---------- D1b ----------
def d1b_picks(game: str, eid: str, kick, ours: dict, derivs: list[tuple], w: dict, min_edge: float) -> list[dict]:
    """`ours`: own and market values from the playbook's candidates for this game (side = home margin, total, tt_home, tt_away).
    `derivs`: Pinnacle rows (market, period, description, line, price_a, price_b). Pure."""
    out = []
    for market, period, desc, line, pa, pb in derivs:
        if line is None or pa is None or pb is None:
            continue
        sd = SD.get((market, period))
        if sd is None:
            continue
        if market == "spread" and "side" in ours:
            own, mkt = ours["side"]
            mean = fair_mean(line, pa, pb, sd, "spread") + 0.62 * w["side"] * (own - mkt)
            sides = (("home", pa), ("away", pb))
        elif market == "total" and "total" in ours:
            own, mkt = ours["total"]
            mean = fair_mean(line, pa, pb, sd, "total") + 0.47 * w["total"] * (own - mkt)
            sides = (("over", pa), ("under", pb))
        elif market == "team_total" and f"tt_{desc}" in ours:
            own, mkt = ours[f"tt_{desc}"]
            mean = fair_mean(line, pa, pb, sd, "total") + w["team_total"] * (own - mkt)
            sides = (("over", pa), ("under", pb))
        else:
            continue
        m = "spread" if market == "spread" else "total"
        for side, price in sides:
            e = chance(mean, line, sd, side, m) - need(price)
            if e >= min_edge:
                who = f" {desc}" if market == "team_total" else ""
                out.append({"key": f"D1b|NFL|{eid}|{market}|{period}|{desc}|{side}", "lane": "D1b", "sport": "NFL", "event_id": eid, "game": game,
                            "market": market, "period": period, "side": f"{desc}_{side}" if desc else side, "line": line, "price": price,
                            "ref_line": line, "ours": mean, "edge": e, "kick": kick,
                            "note": f"{period}{who} {market.replace('_', ' ')}: ours {mean:.1f} against Pinnacle {line:g} ({price:+.0f}), {100 * e:+.1f}%"})
    return out


def log_d1b(con, cfg: dict, now: datetime, st: dict) -> int:
    from engine.picks import playbook
    pst = playbook.settings(cfg, "NFL")
    naive = now.astimezone(timezone.utc).replace(tzinfo=None)
    cands = con.execute("""SELECT event_id, game, market, side, own_value, market_value, kickoff_utc FROM (
                             SELECT *, row_number() OVER (PARTITION BY event_id, market, side ORDER BY first_seen_utc DESC) rn
                             FROM playbook_candidates WHERE sport = 'NFL' AND kickoff_utc > ?) WHERE rn = 1""",
                        [naive]).fetchall()
    games: dict[str, dict] = {}
    for eid, game, market, side, own, mkt, kick in cands:
        if own is None or mkt is None:
            continue
        g = games.setdefault(eid, {"game": game, "kick": kick, "ours": {}})
        if market in ("side", "total"):
            g["ours"][market] = (own, mkt)
        elif market == "team_total":
            g["ours"]["tt_" + side.split("_")[0]] = (own, mkt)
    n = 0
    for eid, g in games.items():
        away, home = g["game"].split(" at ", 1)
        derivs = con.execute("""SELECT market, period, description, line, price_a, price_b FROM (
                                  SELECT *, row_number() OVER (PARTITION BY market, period, description ORDER BY ts_utc DESC) rn
                                  FROM derivative_snapshots WHERE source = 'Pinnacle' AND sport = 'NFL' AND home = ? AND away = ? AND ts_utc > ?)
                                WHERE rn = 1 AND ((market IN ('spread', 'total') AND period = '1st Half') OR (market = 'team_total' AND period = 'Game'))""",
                             [home, away, naive - FRESH]).fetchall()
        for p in d1b_picks(g["game"], eid, g["kick"], g["ours"], derivs, pst["weights"], st["d1b_edge"]):
            n += _freeze(con, p, now)
    return n


# ---------- grading ----------
def _close(con, p: dict) -> tuple | None:
    """(line, price_a, price_b) of Pinnacle's last read before the start for this pick's market."""
    if p["period"] == "Game" and p["market"] in ("spread", "total"):
        cols = "home_spread, home_spread_price, away_spread_price" if p["market"] == "spread" else "total, over_price, under_price"
        return con.execute(f"SELECT {cols} FROM line_snapshots WHERE source = ? AND event_id = ? AND ts_utc < ? AND {cols.split(',')[0]} IS NOT NULL "
                           "ORDER BY ts_utc DESC LIMIT 1", [snap.SHARP, p["event_id"], p["kick_utc"]]).fetchone()
    away, home = p["game"].split(" at ", 1)
    desc = p["side"].split("_")[0] if p["market"] == "team_total" else ""
    return con.execute("""SELECT line, price_a, price_b FROM derivative_snapshots WHERE source = 'Pinnacle' AND sport = ? AND home = ? AND away = ?
                          AND market = ? AND period = ? AND description = ? AND ts_utc < ? ORDER BY ts_utc DESC LIMIT 1""",
                       [p["sport"], home, away, p["market"], p["period"], desc, p["kick_utc"]]).fetchone()


def clv_of(p: dict, close: tuple | None, cfg: dict) -> float | None:
    """Win chance at the frozen line if Pinnacle's close (with its price) is fair, minus the chance the frozen price needs."""
    if close is None or close[0] is None:
        return None
    side = p["side"].split("_")[-1]
    m = "spread" if p["market"] == "spread" else "total"
    if p["period"] == "Game" and p["market"] in ("spread", "total"):
        from engine import clv as clv_mod
        c = clv_mod.chance(cfg, p["sport"], m, side, p["line"], close[0])
        return None if c is None else round(c + 0.5 - need(p["price"]), 4)
    sd = SD[(p["market"], p["period"])]
    mean = fair_mean(close[0], close[1], close[2], sd, m)
    return round(chance(mean, p["line"], sd, side, m) - need(p["price"]), 4)


def result_of(p: dict, sc: tuple) -> str:
    """W, L or P. `sc` = (home 1st half, away 1st half, home final, away final)."""
    h1, a1, hf, af = sc
    side = p["side"].split("_")[-1]
    if p["market"] == "spread":
        h, a = (h1, a1) if p["period"] == "1st Half" else (hf, af)
        x = (h - a + p["line"]) * (1 if side == "home" else -1)
    elif p["market"] == "total":
        t = (h1 + a1) if p["period"] == "1st Half" else (hf + af)
        x = (t - p["line"]) * (1 if side == "over" else -1)
    else:
        pts = hf if p["side"].startswith("home") else af
        x = (pts - p["line"]) * (1 if side == "over" else -1)
    return "W" if x > 0 else "L" if x < 0 else "P"


def period_scores(sport: str, event_id: str) -> tuple | None:
    """(home 1st half, away 1st half, home final, away final) once ESPN says the game is over, else None."""
    from engine.odds import espn
    from engine.picks import grade as g
    s, slug, _ = espn.LEAGUES[sport]
    data = espn._get(g.SUMMARY_URL.format(sport=s, slug=slug, eid=event_id))
    try:
        comp = data["header"]["competitions"][0]
        if not comp["status"]["type"]["completed"]:
            return None
        by = {c["homeAway"]: c for c in comp["competitors"]}
        def half(c):
            ls = c.get("linescores") or []
            return sum(float(x.get("value", x.get("displayValue", 0)) or 0) for x in ls[:2]) if len(ls) >= 2 else None
        return half(by["home"]), half(by["away"]), int(float(by["home"]["score"])), int(float(by["away"]["score"]))
    except (KeyError, IndexError, ValueError, TypeError):
        raise espn.SourceError(f"ESPN summary for event {event_id} has no usable score") from None


def grade(con, cfg: dict, now: datetime, scorer=None) -> list[str]:
    scorer = scorer or period_scores
    cols = ["key", "lane", "sport", "event_id", "game", "market", "period", "side", "line", "price", "kick_utc"]
    rows = con.execute(f"""SELECT {', '.join('p.' + c for c in cols)} FROM paper_lane_picks p LEFT JOIN paper_lane_grades g USING (key)
                           WHERE g.key IS NULL AND p.kick_utc < ?""", [(now - timedelta(hours=4)).astimezone(timezone.utc).replace(tzinfo=None)]).fetchall()
    out, cache = [], {}
    for r in rows:
        p = dict(zip(cols, r))
        k = (p["sport"], p["event_id"])
        if k not in cache:
            try:
                cache[k] = scorer(*k)
            except Exception as e:
                cache[k] = None
                out.append(f"Paper lanes: score for {p['game']} unreadable ({type(e).__name__})")
        sc = cache[k]
        if sc is None or (p["period"] == "1st Half" and (sc[0] is None or sc[1] is None)):
            continue
        close = _close(con, p)
        con.execute("INSERT INTO paper_lane_grades VALUES (?,?,?,?,?)",
                    [p["key"], None if close is None else close[0], clv_of(p, close, cfg), result_of(p, sc),
                     now.astimezone(timezone.utc).replace(tzinfo=None)])
    return out


# ---------- report, card ----------
def lane_summary(con, lane: str, sport: str | None = None) -> dict:
    q = "SELECT g.result, g.clv FROM paper_lane_picks p JOIN paper_lane_grades g USING (key) WHERE p.lane = ?" + (" AND p.sport = ?" if sport else "")
    rows = con.execute(q, [lane] + ([sport] if sport else [])).fetchall()
    w, l, pu = (sum(1 for r in rows if r[0] == x) for x in "WLP")
    cl = [r[1] for r in rows if r[1] is not None]
    n = len(cl)
    mean = sum(cl) / n if n else None
    sd = math.sqrt(sum((c - mean) ** 2 for c in cl) / (n - 1)) if n > 1 else None
    issued = con.execute("SELECT count(*) FROM paper_lane_picks WHERE lane = ?" + (" AND sport = ?" if sport else ""),
                         [lane] + ([sport] if sport else [])).fetchone()[0]
    return {"issued": issued, "w": w, "l": l, "p": pu, "n_clv": n, "clv": mean,
            "lo": None if sd is None else mean - 1.96 * sd / math.sqrt(n), "hi": None if sd is None else mean + 1.96 * sd / math.sqrt(n)}


def report(con, cfg: dict, now: datetime) -> str:
    st = settings(cfg)
    tz = config.display_tz(cfg)
    lines = ["# Paper lanes (generated; do not edit)", "",
             f"Generated {now.astimezone(tz):%a %b %-d, %-I:%M %p} MT by the hourly read. Decision 0036, research 24 (tests L1, F1, D1b). "
             "$0: never sent to Telegram, never staked.", "",
             "Each pick is frozen at first sight and graded on closing-line value: the win chance at the frozen number if Pinnacle's last read "
             "before the start is fair, minus the chance the frozen price needs (above 0 = beat the close after the price). Kill rule: at "
             f"{st['kill_after']} graded picks a lane (per sport for L1) is turned off with a decision note unless its average closing-line value "
             "is above zero with its 95% range above zero.", "",
             "| Lane | Sport | Issued | Graded W-L-P | A coin flip lands in | Closing-line value (95% range) | Kill rule |", "|---|---|---|---|---|---|---|"]
    for lane, sports in (("L1", ("NFL", "College", "NBA")), ("F1", ("NFL",)), ("D1b", ("NFL",))):
        for sport in sports:
            s = lane_summary(con, lane, sport)
            n = s["w"] + s["l"]
            luck = f"{100 * (0.5 - 1.96 * math.sqrt(0.25 / n)):.0f}-{100 * (0.5 + 1.96 * math.sqrt(0.25 / n)):.0f}%" if n else "n/a"
            clv = "n/a" if s["clv"] is None else (f"{100 * s['clv']:+.1f}%" + ("" if s["lo"] is None else f" ({100 * s['lo']:+.1f} to {100 * s['hi']:+.1f})"))
            if s["n_clv"] >= st["kill_after"]:
                kill = "**off: turn it off**" if s["lo"] is None or s["lo"] <= 0 else "passes: Kylor decides"
            else:
                kill = f"checked at {st['kill_after']} ({s['n_clv']} so far)"
            lines.append(f"| {LANES[lane]} | {sport} | {s['issued']} | {s['w']}-{s['l']}-{s['p']} | {luck} | {clv} | {kill} |")
    lines += ["", "## Open", ""]
    open_ = con.execute("""SELECT p.lane, p.sport, p.game, p.market, p.period, p.side, p.line, p.price, p.note, p.kick_utc FROM paper_lane_picks p
                           LEFT JOIN paper_lane_grades g USING (key) WHERE g.key IS NULL ORDER BY p.kick_utc LIMIT 60""").fetchall()
    if not open_:
        lines.append("None open.")
    else:
        lines += ["| Lane | Game | Bet | Price | Why | Start (MT) |", "|---|---|---|---|---|---|"]
        for lane, sport, game, market, period, side, line, price, note, kick in open_:
            lines.append(f"| {lane} {sport} | {game} | {bet_text(game, market, period, side, line)} | {int(price):+d} | {note} | "
                         f"{kick.replace(tzinfo=timezone.utc).astimezone(tz):%a %-I:%M %p} |")
    return "\n".join(lines) + "\n"


def bet_text(game: str, market: str, period: str, side: str, line: float) -> str:
    away, home = game.split(" at ", 1)
    pre = "" if period == "Game" else f"{period} "
    if market == "spread":
        n = line if side == "home" else -line
        return f"{pre}{home if side == 'home' else away} {'pick' if n == 0 else f'{n:+g}'}"
    if market == "team_total":
        who, ou = side.split("_")
        return f"{pre}{home if who == 'home' else away} team total {ou} {line:g}"
    return f"{pre}{side.title()} {line:g}"


def card_block(con, cfg: dict, sport: str, now: datetime) -> str:
    """The paper-lane picks open for this sport, for the bottom of its playbook card (decision 0036: "shown on the card")."""
    try:
        con.execute(SCHEMA)
        rows = con.execute("""SELECT p.lane, p.game, p.market, p.period, p.side, p.line, p.price, p.note FROM paper_lane_picks p
                              LEFT JOIN paper_lane_grades g USING (key) WHERE g.key IS NULL AND p.sport = ? AND p.kick_utc > ?
                              ORDER BY p.kick_utc""", [sport, now.astimezone(timezone.utc).replace(tzinfo=None)]).fetchall()
    except Exception:
        return ""
    if not rows:
        return ""
    out = ["", "## Paper lanes ($0, not sent; decision 0036; record in docs/lanes/PAPER-LANES.md)", "", "| Lane | Bet | Price | Why |", "|---|---|---|---|"]
    for lane, game, market, period, side, line, price, note in rows:
        out.append(f"| {LANES[lane]} | {bet_text(game, market, period, side, line)} ({game}) | {int(price):+d} | {note} |")
    return "\n".join(out) + "\n"


def run(con, cfg: dict, now: datetime) -> list[str]:
    """Hourly read: freeze each lane's new picks, grade finished ones, write the report. Never raises into the read; never sends."""
    st = settings(cfg)
    if not st["enabled"]:
        return []
    out = []
    try:
        con.execute(SCHEMA)
    except Exception as e:
        return [f"Paper lanes failed: {type(e).__name__}: {e}"]
    for name, on, fn in (("L1", st["l1"], log_l1), ("F1", st["f1"], log_f1), ("D1b", st["d1b"], log_d1b)):
        if not on:
            continue
        try:
            n = fn(con, cfg, now, st)
            if n:
                out.append(f"Paper lane {name}: {n} new paper pick(s) frozen.")
        except Exception as e:
            out.append(f"Paper lane {name} failed: {type(e).__name__}: {e}")
    try:
        out += grade(con, cfg, now)
        REPORT.write_text(report(con, cfg, now))
    except Exception as e:
        out.append(f"Paper lanes grading or report failed: {type(e).__name__}: {e}")
    return out
