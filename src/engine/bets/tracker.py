"""The tracker: every Telegram recommendation next to what Kylor actually bet, from Nov 23, 2026 (Kylor: "use the telegram recommendations,
compared with my actual wagers (starting from today), so i can see how this model is doing and also as a grader").

Three questions, answered from the database and the account history:
  1. How is the model doing? Every staked recommendation (playbook picks and teaser tickets), graded at the number and stake it was sent with.
  2. How is Kylor doing? Every wager placed since the start date, graded by the account itself (won, lost, net).
  3. How closely were the picks followed? Each recommendation is matched to his wagers on the same game, market and side: did he bet it,
     at a better or worse number and price than the one sent, inside the "don't bet past" limit, at the stake sent?
Wagers with no matching recommendation are listed as his own bets.

Data: graded wagers come from the account's history report, synced by the hourly read twice a day (first read from 8am and from 5pm).
The report does not return open bets (asking for `graded: 0` returns graded ones; checked Nov 23), so a bet appears once it is graded. Matching is by team names, market and side;
props by player name, stat words and over/under. An unmatched wager is never forced onto a pick.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from engine import config
from engine.bets.history import Wager, load_wagers

START = "2026-11-23"           # Mountain date the tracking starts (Kylor, Nov 23)
MASTER = config.DATA / "raw" / "wagerhouse_graded_master.json"


SYNONYMS = {"3pt": "threes", "3": "threes", "three": "threes", "rebs": "rebounds", "reb": "rebounds", "asts": "assists", "ast": "assists",
            "pts": "points", "yds": "yards", "td": "touchdowns", "tds": "touchdowns", "rec": "receptions", "fg": "", "shots": "", "made": "",
            "total": "", "player": ""}
MANUAL = config.DATA / "tracker" / "open_bets.yaml"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (s or "").lower())).strip()


def stat_words(s: str) -> set[str]:
    return {SYNONYMS.get(w, w) for w in norm(s).split()} - {""}


def same_team(a: str, b: str) -> bool:
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    ta, tb = set(a.split()), set(b.split())
    return len(ta & tb) >= 1 and (ta & tb) - {"state", "st", "university", "the", "of", "new", "los", "angeles", "san"} != set()


@dataclass
class Rec:
    key: str
    kind: str                 # pick, teaser
    sport: str
    sent: datetime
    game: str
    market: str               # side, total, team_total, prop, teaser
    side: str
    pick: str
    line: float | None
    price: float | None
    dollars: float
    limit: str | None
    kick: datetime
    result: str | None        # W L P, None = not graded
    profit_units: float | None
    unit: float
    legs: list[dict] = field(default_factory=list)   # teaser: [{"team", "line", "game"}]
    paper: bool = False       # issued at $0 (decision 0025): graded at the grade's size, never sent to Telegram
    matched: list[Wager] = field(default_factory=list)

    @property
    def model_dollars(self) -> float | None:
        return None if self.profit_units is None else round(self.profit_units * self.unit, 2)


def recommendations(con, cfg: dict, since: datetime) -> list[Rec]:
    out = []
    try:
        cols = {r[0] for r in con.execute("DESCRIBE playbook_picks").fetchall()}
        gcols = {r[0] for r in con.execute("DESCRIBE playbook_grades").fetchall()}
        nom = "coalesce(p.nominal_units, p.units)" if "nominal_units" in cols else "p.units"
        nprof = "coalesce(g.nominal_profit, g.profit_units)" if "nominal_profit" in gcols else "g.profit_units"
        rows = con.execute(f"""SELECT p.pick_key, p.sport, p.first_seen_utc, p.game, p.market, p.side, p.pick, p.line, p.price, p.dollars,
                                      p.dont_bet_past, p.kickoff_utc, g.result, {nprof}, p.units, {nom}
                               FROM playbook_picks p LEFT JOIN playbook_grades g USING (pick_key)
                               WHERE {nom} > 0 AND p.first_seen_utc >= ? ORDER BY p.first_seen_utc""", [since.replace(tzinfo=None)]).fetchall()
    except Exception:
        rows = []
    for k, sport, sent, game, market, side, pick, line, price, dollars, lim, kick, res, pu, units, nominal in rows:
        unit = config.unit_for(cfg, sport)
        paper = not units
        out.append(Rec(k, "pick", sport, sent.replace(tzinfo=timezone.utc), game, market, side, pick, line, price,
                       round(nominal * unit, 2) if paper else dollars, lim, kick.replace(tzinfo=timezone.utc), res, pu, unit, paper=paper))
    try:
        trows = con.execute("""SELECT t.ticket_key, t.sent_utc, t.leg_a, t.leg_b, t.units, t.dollars, t.price,
                                      a.team, a.line, a.game, a.kickoff_utc, b.team, b.line, b.game, b.kickoff_utc, ga.result, gb.result
                               FROM teaser_tickets t JOIN teaser_legs a ON a.leg_key = t.leg_a JOIN teaser_legs b ON b.leg_key = t.leg_b
                               LEFT JOIN teaser_grades ga ON ga.leg_key = t.leg_a LEFT JOIN teaser_grades gb ON gb.leg_key = t.leg_b
                               WHERE t.sent_utc >= ? ORDER BY t.sent_utc""", [since.replace(tzinfo=None)]).fetchall()
    except Exception:
        trows = []
    for tk, sent, la, lb, units, dollars, price, ta, lna, gma, ka, tb, lnb, gmb, kb, ra, rb in trows:
        res = pu = None
        if ra and rb:
            res = "L" if "L" in (ra, rb) else "P" if "P" in (ra, rb) else "W"
            pu = -units if res == "L" else 0.0 if res == "P" else units * (100 / abs(price) if price < 0 else price / 100)
        legs = [{"team": ta, "line": lna, "game": gma}, {"team": tb, "line": lnb, "game": gmb}]
        out.append(Rec(tk, "teaser", "NFL", sent.replace(tzinfo=timezone.utc), f"{gma} + {gmb}", "teaser", "", f"Teaser {ta} {lna + 6:+g} / {tb} {lnb + 6:+g}",
                       None, price, dollars, None, max(ka, kb).replace(tzinfo=timezone.utc), res, pu, config.unit_for(cfg, "NFL"), legs))
    return out


def manual_wagers(path: Path = MANUAL) -> list[Wager]:
    """Open wagers entered by hand from the site's open-bets screen (the account API only returns graded wagers). Status 'O' = open."""
    import yaml
    from zoneinfo import ZoneInfo
    from engine.bets.history import Leg
    if not path.exists():
        return []
    out = []
    for i, b in enumerate((yaml.safe_load(path.read_text()) or {}).get("bets", []) or []):
        acc = datetime.fromisoformat(b["accepted"]).replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
        legs = [Leg(j + 1, l["kind"], "", l.get("team1", ""), l.get("team2", ""), l.get("chosen", ""), l.get("line"), l.get("line"), 0.0,
                    float(l.get("teaser", 0)), l.get("ou", ""), l.get("price"), None, "", "Game") for j, l in enumerate(b.get("legs", []))]
        w = Wager(900000000 + i, 1, b.get("type", "S"), "pregame", acc, float(b["risk"]), float(b.get("to_win", 0)), 0.0, 0.0, "O", False,
                  "", b.get("desc", ""), "", legs)
        w.ignore = bool(b.get("ignore"))
        w.note = b.get("note", "")
        out.append(w)
    return out


def wagers(since: datetime) -> list[Wager]:
    """Every wager accepted since `since`: graded ones from the account history, plus open ones entered by hand. A hand entry is dropped
    once a graded wager with the same accepted minute and risk appears."""
    ws = []
    if MASTER.exists():
        try:
            ws = [w for w in load_wagers(MASTER) if w.accepted and w.accepted >= since]
        except ValueError:
            ws = []
    seen = {(w.accepted.replace(second=0, microsecond=0), round(w.risk, 2)) for w in ws}
    for w in manual_wagers():
        if w.accepted >= since and (w.accepted.replace(second=0, microsecond=0), round(w.risk, 2)) not in seen:
            ws.append(w)
    for w in ws:
        if not hasattr(w, "ignore"):
            w.ignore, w.note = False, ""
    return sorted(ws, key=lambda w: w.accepted)


def _game_teams(game: str) -> tuple[str, str]:
    a, _, h = game.partition(" at ")
    return a.strip(), h.strip()


def _leg_matches(rec: Rec, leg, w: Wager) -> bool:
    away, home = _game_teams(rec.game)
    in_game = (same_team(leg.team1, away) or same_team(leg.team2, away) or same_team(leg.chosen, away)) and \
              (same_team(leg.team1, home) or same_team(leg.team2, home) or same_team(leg.chosen, home))
    desc = norm(w.description)
    if rec.market == "prop":
        # Wagerhouse: team1 = player, team2 = stat ("Nico Collins/Receptions O 4½"); the pick: "Stefon Diggs under 4.5 Receptions"
        m = re.match(r"^(.*) (over|under) [\d.]+ (.*)$", rec.pick)
        if not m:
            return False
        player, ou = norm(m.group(1)), m.group(2)
        last = player.split()[-1] if player else ""
        want, have = stat_words(m.group(3)), stat_words(leg.team2)
        same_stat = want == have if {"points", "rebounds", "assists"} & (want | have) else bool(want & have)
        return bool(last) and last in norm(leg.team1 + " " + leg.chosen + " " + desc) and same_stat and \
            ((leg.over_under or "").upper() == ou[0].upper() or ou in desc)
    if not in_game:
        return False
    if rec.market == "side":
        team = home if rec.side == "home" else away
        return leg.kind == "spread" and same_team(leg.chosen, team)
    if rec.market == "total":
        return leg.kind == "total" and (leg.over_under or "").upper() == rec.side[0].upper()
    if rec.market == "team_total":
        who, ou = rec.side.split("_")
        team = home if who == "home" else away
        return leg.kind == "team_total" and (leg.over_under or "").upper() == ou[0].upper() and (same_team(leg.chosen, team) or team.split()[-1].lower() in desc)
    return False


def match(recs: list[Rec], ws: list[Wager]) -> list[Wager]:
    """Attach wagers to the recommendations they follow; return the wagers that follow none."""
    used = {w.key for w in ws if getattr(w, "ignore", False)}
    for r in recs:
        for w in ws:
            if w.key in used or (w.accepted and w.accepted < r.sent - timedelta(minutes=5)):
                continue
            if r.kind == "teaser":
                if w.type_code != "T" or len(w.legs) != 2:
                    continue
                ok = all(any(same_team(l.chosen, leg["team"]) for l in w.legs) for leg in r.legs)
            else:
                ok = len(w.legs) == 1 and _leg_matches(r, w.legs[0], w)
            if ok:
                r.matched.append(w)
                used.add(w.key)
    return [w for w in ws if w.key not in used and not getattr(w, "ignore", False)]


def _limit_number(limit: str | None) -> float | None:
    if not limit:
        return None
    m = re.findall(r"[+-]?\d+(?:\.\d+)?", limit)
    return float(m[0]) if m else None


def _dec(price: float) -> float:
    return 1 + (100 / abs(price) if price < 0 else price / 100)


def past_limit(r: Rec, leg) -> str:
    """'PAST THE LIMIT' when the wager is worse than the pick's "don't bet past": a worse number than the limit for sides and totals; for props,
    at the same line, a worse price than the worst price sent (a better line is judged on the line alone)."""
    if not r.limit or leg.line is None:
        return ""
    if r.market == "prop":
        m = re.search(r"at ([+-]\d+) or better", r.limit)
        if not m or r.line is None or abs(leg.line - r.line) > 1e-9 or leg.price is None:
            return ""
        return "PAST THE LIMIT (price)" if _dec(leg.price) < _dec(float(m.group(1))) - 1e-9 else ""
    lim = _limit_number(r.limit)
    if lim is None:
        return ""
    if r.market == "side":
        own_lim = lim                                   # the limit text is in the chosen team's own spread ("Tennessee Titans +14.5")
        return "PAST THE LIMIT" if leg.line < own_lim - 1e-9 else ""
    ou = r.side.split("_")[-1]
    worse = leg.line > lim + 1e-9 if ou == "over" else leg.line < lim - 1e-9
    return "PAST THE LIMIT" if worse else ""


def grade_follow(r: Rec) -> str:
    """Plain words on how the bet compares with the recommendation."""
    if not r.matched:
        return "not bet"
    w = r.matched[0]
    notes = []
    if r.kind == "pick" and w.legs:
        leg = w.legs[0]
        if leg.line is not None and r.line is not None and r.market in ("side", "total", "team_total", "prop"):
            if r.market == "side":
                # Wagerhouse stores the chosen team's own spread; the recommendation stores the home spread. More points = better.
                diff = leg.line - (r.line if r.side == "home" else -r.line)
            else:
                ou = r.side.split("_")[-1]
                diff = (r.line - leg.line) if ou == "over" else (leg.line - r.line)
            if abs(diff) < 1e-9:
                notes.append("same number")
            elif r.market == "prop":
                notes.append(f"line {abs(diff):g} {'better' if diff > 0 else 'worse'}")
            else:
                notes.append(f"{abs(diff):g} point{'s' if abs(diff) != 1 else ''} {'better' if diff > 0 else 'worse'}")
        if leg.price is not None and r.price is not None and leg.price != int(r.price):
            notes.append(f"price {leg.price:+d} vs {int(r.price):+d} sent")
        past = past_limit(r, leg)
        if past:
            notes.append(past)
    risk = sum(x.risk for x in r.matched)
    if r.dollars and abs(risk / r.dollars - 1) > 0.15:
        notes.append(f"stake ${risk:g} vs ${r.dollars:g} sent")
    if len(r.matched) > 1:
        notes.append(f"{len(r.matched)} wagers on it")
    return "bet: " + (", ".join(notes) if notes else "as sent")


def luck_dollars(recs: list) -> float:
    """Two-standard-deviation swing of these graded picks' results for a bettor with no edge (CLAUDE.md: every report prints
    the luck range). Risk is the stake sent; to-win from its price (-110 when a teaser or a pick has none)."""
    from engine.odds.math import luck_range
    bets = []
    for r in recs:
        if not r.result or r.result == "P" or not r.dollars:
            continue
        pr = r.price if r.price else -110
        win = r.dollars * 100 / -pr if pr < 0 else r.dollars * pr / 100
        bets.append((r.dollars, win))
    return luck_range(bets)


def report(con, cfg: dict, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    tz = config.display_tz(cfg)
    since = datetime.fromisoformat(START).replace(tzinfo=tz).astimezone(timezone.utc)
    recs = recommendations(con, cfg, since)
    ws = wagers(since)
    own = match(recs, ws)
    paper = [r for r in recs if r.paper]
    pg = [r for r in paper if r.result]
    recs = [r for r in recs if not r.paper]
    graded = [r for r in recs if r.result]
    mw, ml, mp = (sum(r.result == x for r in graded) for x in "WLP")
    m_net = sum(r.model_dollars or 0 for r in graded)
    m_risk = sum(r.dollars for r in recs)
    p_net = sum(r.model_dollars or 0 for r in pg)
    # units first (decision 0036): each pick's result in its own sport's units
    m_u = sum(r.profit_units or 0 for r in graded)
    m_risk_u = sum(r.dollars / r.unit for r in recs if r.unit)
    p_u = sum((r.model_dollars or 0) / r.unit for r in pg if r.unit)
    luck_u = luck_dollars([SimpleNamespace(result=r.result, dollars=r.dollars / r.unit, price=r.price) for r in graded if r.unit])
    followed = [r for r in recs if r.matched]
    f_net = sum(w.net for r in followed for w in r.matched if w.status in ("W", "L", "X"))
    o_set = [w for w in own if w.status in ("W", "L", "X")]
    o_net = sum(w.net for w in o_set)
    all_net = sum(w.net for w in ws if w.status in ("W", "L", "X"))
    open_ws = [w for w in ws if w.status not in ("W", "L", "X")]
    out = ["# Tracker: the model's picks against your bets (generated; do not edit)", "",
           f"From {START} (Mountain). Updated {now.astimezone(tz):%a %b %-d, %-I:%M %p} MT. Your wagers come from the account history, which "
           "shows a bet once it is graded; open bets are entered from your open-bets screen (data.nosync/tracker/open_bets.yaml) until they settle. "
           "Picks come from what Telegram sent.", "",
           "## Scoreboard", "",
           "| | Bets | Record | Net | Notes |", "|---|---|---|---|---|",
           f"| **Model** (every staked pick, at the stake and number sent) | {len(recs)} sent, {len(graded)} graded | {mw}-{ml}-{mp} | "
           f"{m_u:+.2f}u ({'+' if m_net >= 0 else '−'}${abs(m_net):,.2f}) | {m_risk_u:g} units (${m_risk:,.2f}) recommended in all; "
           f"luck range ±{luck_u:.2f}u (±${luck_dollars(graded):,.2f}) |",
           f"| **Model, paper picks** (not sent; graded at the stake they would carry) | {len(paper)} issued, {len(pg)} graded | "
           f"{sum(r.result == 'W' for r in pg)}-{sum(r.result == 'L' for r in pg)}-{sum(r.result == 'P' for r in pg)} | "
           f"{p_u:+.2f}u ({'+' if p_net >= 0 else '−'}${abs(p_net):,.2f}) | not sent: paper lanes, the one-unit-a-game cap, the weekly cap, a stop |",
           f"| **You, on the model's picks** | {sum(len(r.matched) for r in followed)} | "
           f"{sum(w.status == 'W' for r in followed for w in r.matched)}-{sum(w.status == 'L' for r in followed for w in r.matched)} | "
           f"{'+' if f_net >= 0 else '−'}${abs(f_net):,.2f} | followed {len(followed)} of {len(recs)} picks |",
           f"| **You, your own bets** | {len(own)} | {sum(w.status == 'W' for w in o_set)}-{sum(w.status == 'L' for w in o_set)} | "
           f"{'+' if o_net >= 0 else '−'}${abs(o_net):,.2f} | not on the model's list |",
           f"| **You, everything** | {len(ws)} ({len(open_ws)} open) | {sum(w.status == 'W' for w in ws)}-{sum(w.status == 'L' for w in ws)} | "
           f"{'+' if all_net >= 0 else '−'}${abs(all_net):,.2f} | the account's own grading |", ""]
    out += money_lines(con, cfg, now)
    out += edge_split_lines(con, since)
    out += ["## Every pick sent, and what you did", "",
            "| Sent (MT) | Sport | Pick | Price sent | Don't bet past | Stake sent | Model result | You | Your result |", "|---|---|---|---|---|---|---|---|---|"]
    for r in recs:
        # units first, "void" spelled out (decision 0036 items 7 and 11)
        word = {"V": "void"}.get(r.result, r.result)
        res = "open" if r.result is None else (f"{word} ({(r.profit_units or 0):+.2f} units, {'+' if (r.model_dollars or 0) >= 0 else '−'}"
                                                f"${abs(r.model_dollars or 0):,.2f})")
        mine = "; ".join((f"{w.status} {'+' if w.net >= 0 else '−'}${abs(w.net):,.2f}" if w.status in ('W', 'L', 'X') else f"open, ${w.risk:g} at risk")
                         for w in r.matched) or "—"
        price = "" if r.price is None else f" {int(r.price):+d}"
        out.append(f"| {r.sent.astimezone(tz):%a %-I:%M %p} | {r.sport} | {r.pick} | {price.strip() or '-110'} | {r.limit or ''} | {config.units_text(r.dollars / r.unit if r.unit else 0, r.dollars)} | {res} | "
                   f"{grade_follow(r)} | {mine} |")
    if not recs:
        out.append("| | | none sent yet | | | | | | |")
    out += ["", "## Your bets that were not on the model's list", "", "| Placed (MT) | Bet | Type | Risk | Result |", "|---|---|---|---|---|"]
    for w in own:
        typ = {"S": "straight", "P": "parlay", "T": "teaser", "C": "prop", "G": "live"}.get(w.type_code, w.type_code)
        typ = "live" if w.channel == "live" else "same-game builder" if w.channel == "builder" else typ
        res = "open" if w.status not in ("W", "L", "X") else f"{w.status} {'+' if w.net >= 0 else '−'}${abs(w.net):,.2f}"
        out.append(f"| {w.accepted.astimezone(tz):%a %-I:%M %p} | {w.description[:110]} | {typ} | ${w.risk:g} | {res} |")
    if not own:
        out.append("| | none | | | |")
    ign = [w for w in ws if getattr(w, "ignore", False)]
    if ign:
        out += ["", "Left out of the model comparison (still counted in your account total): " +
                "; ".join(f"{w.description[:80]} (${w.risk:g}): {w.note}" for w in ign)]
    out += ["", "How to read it: the model line uses the stake and number sent, so it is the model's own record. Your lines use the account's "
            "real results. A pick you bet at a worse number than sent, or past its limit, shows up in the 'You' column; that is the grader."]
    return "\n".join(out) + "\n"


def money_lines(con, cfg: dict, now: datetime) -> list[str]:
    """This week's staked total against the weekly cap, and units left before each stop (CHARTER, Money; decision 0027)."""
    from engine.picks import playbook
    try:
        week = playbook.week_staked(con, cfg, now)
    except Exception:
        return []
    cap = (cfg.get("playbook") or {}).get("weekly_cap_dollars", playbook.DEFAULTS["weekly_cap_dollars"])
    cap_txt = f" of the ${float(cap):,.0f} weekly cap" if cap else " (no weekly cap)"
    try:
        week_u = playbook.week_staked_units(con, cfg, now)
    except Exception:
        week_u = None
    wtxt = f"{week_u:g} units (${week:,.2f})" if week_u is not None else f"${week:,.2f}"
    out = ["## Money rules", "", f"- This week (Monday to Sunday MT): {wtxt} recommended{cap_txt}."]
    for sport in ((cfg.get("playbook") or {}).get("sports") or playbook.SPORT_DEFAULTS):
        st = playbook.settings(cfg, sport)
        if st["full_game"] != "stake" and not (st.get("props") and st.get("props_stake", True)):
            continue
        try:
            down = playbook.down_units(con, sport, cfg)
        except Exception as e:      # never show an unreadable stop as +0.0 (audit 24)
            out.append(f"- {sport}: COULD NOT READ the staked result for the stop ({type(e).__name__}); see the read log.")
            continue
        out.append(f"- {sport}{' (with teasers)' if sport == 'NFL' else ''}: {down:+.2f} units staked result; the stop is at "
                   f"-{st['stop_loss_units']:g} ({st['stop_loss_units'] + min(down, 0):.1f} units left).")
    return out + [""]


def edge_split_lines(con, since: datetime) -> list[str]:
    """How much of the edge sent was Wagerhouse's price against the market, and how much our handicap (research 19)."""
    try:
        rows = con.execute("""SELECT market <> 'prop', count(*), avg(edge), avg(price_edge) FROM playbook_picks
                              WHERE units > 0 AND price_edge IS NOT NULL AND first_seen_utc >= ? GROUP BY 1 ORDER BY 1""",
                           [since.replace(tzinfo=None)]).fetchall()
    except Exception:
        return []
    if not rows:
        return []
    out = ["## Where the edge came from (staked picks)", "",
           "The charter says a price gap alone is never a reason. This shows how much of each staked pick's edge was only Wagerhouse's price against "
           "the market (Pinnacle's line or price), and how much was our handicap. Recorded from Nov 24 (research 19).", "",
           "| Kind | Picks | Average edge | From the price | From our handicap |", "|---|---|---|---|---|"]
    for full, n, e, pe in rows:
        out.append(f"| {'Full-game' if full else 'Props'} | {n} | {100 * e:+.1f}% | {100 * pe:+.1f}% | {100 * (e - pe):+.1f}% |")
    return out + [""]


def not_sent_line(con, now: datetime) -> str:
    """The recap's line for picks issued in the last 24 hours that were not sent, grouped by reason (decision 0027)."""
    import re
    try:
        rows = con.execute("SELECT text FROM alerts_sent WHERE kind = 'paper' AND ts_utc >= ?",
                           [(now - timedelta(hours=24)).replace(tzinfo=None)]).fetchall()
    except Exception:
        return ""
    if not rows:
        return "Not sent in the last 24 hours: none."
    why: dict[str, int] = {}
    for (t,) in rows:
        m = re.search(r"Stake: (?:\$0|0 units \(\$0\)) \((paper: )?([^;)(]*)", t or "")
        k = (m.group(2).strip() if m else "paper").split(" (decision")[0]
        k = re.sub(r"\$[\d.,]+ (is )?already", "already", k)
        why[k] = why.get(k, 0) + 1
    return f"Not sent in the last 24 hours: {len(rows)} paper pick(s): " + "; ".join(f"{n} {k}" for k, n in sorted(why.items(), key=lambda x: -x[1])) + "."


def recap(con, cfg: dict) -> str:
    """Short phone version for the morning Telegram message."""
    text = report(con, cfg)
    rows = [l for l in text.splitlines() if l.startswith("| **")]
    keep = []
    for l in rows:
        cells = [c.strip() for c in l.strip("|").split("|")]
        keep.append(f"{cells[0].replace('**', '').split(' (')[0]}: {cells[2]}, {cells[3]} ({cells[1]})")
    now = datetime.now(timezone.utc)
    lk = re.search(r"luck range (±[\d.]+u \(±\$[\d,.]+\))", text)
    if lk:      # CLAUDE.md: results always come with the luck range (audit 24: the recap had none)
        keep.append(f"Luck range on the model's graded picks: {lk.group(1)} (a result inside it can be chance)")
    extra = [not_sent_line(con, now)] + [l.removeprefix("- ") for l in money_lines(con, cfg, now) if l.startswith("- ")]
    return "TRACKER (since Nov 23)\n" + "\n".join(keep + [x for x in extra if x]) + "\nDetails: docs/lanes/TRACKER.md and the board."


def sync(env: dict, weeks: int = 1, wh=None) -> str:
    """Read-only: this week's graded wagers into the history file."""
    from engine.bets.history import merge_pull
    from engine.odds.wagerhouse import Wagerhouse
    wh = wh or Wagerhouse(env.get("WAGERHOUSE_USER", ""), env.get("WAGERHOUSE_PASSWORD", ""))
    pull = wh.graded_pull(weeks=weeks)
    master = json.loads(MASTER.read_text()) if MASTER.exists() else None
    MASTER.write_text(json.dumps(merge_pull(master, pull)))
    return f"tracker sync: {len(pull['rows'])} graded rows this week"


def write(con, cfg: dict) -> Path:
    """docs/lanes/TRACKER.md (committed) and tracker.html (the page; not committed)."""
    p = config.ROOT / "docs" / "lanes" / "TRACKER.md"
    p.write_text(report(con, cfg))
    from engine.bets import tracker_page
    tracker_page.build(con, cfg)
    return p
