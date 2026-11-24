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

from engine import config
from engine.bets.history import Wager, load_wagers

START = "2026-11-23"           # Mountain date the tracking starts (Kylor, Nov 23)
MASTER = config.DATA / "raw" / "wagerhouse_graded_master.json"


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


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
    matched: list[Wager] = field(default_factory=list)

    @property
    def model_dollars(self) -> float | None:
        return None if self.profit_units is None else round(self.profit_units * self.unit, 2)


def recommendations(con, cfg: dict, since: datetime) -> list[Rec]:
    out = []
    try:
        rows = con.execute("""SELECT p.pick_key, p.sport, p.first_seen_utc, p.game, p.market, p.side, p.pick, p.line, p.price, p.dollars,
                                     p.dont_bet_past, p.kickoff_utc, g.result, g.profit_units
                              FROM playbook_picks p LEFT JOIN playbook_grades g USING (pick_key)
                              WHERE p.units > 0 AND p.first_seen_utc >= ? ORDER BY p.first_seen_utc""", [since.replace(tzinfo=None)]).fetchall()
    except Exception:
        rows = []
    for k, sport, sent, game, market, side, pick, line, price, dollars, lim, kick, res, pu in rows:
        out.append(Rec(k, "pick", sport, sent.replace(tzinfo=timezone.utc), game, market, side, pick, line, price, dollars, lim,
                       kick.replace(tzinfo=timezone.utc), res, pu, config.unit_for(cfg, sport)))
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


def wagers(since: datetime) -> list[Wager]:
    """Every graded wager accepted since `since`, from the account history file."""
    if not MASTER.exists():
        return []
    try:
        ws = [w for w in load_wagers(MASTER) if w.accepted and w.accepted >= since]
    except ValueError:
        return []
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
        player, ou, stat = norm(m.group(1)), m.group(2), norm(m.group(3))
        last = player.split()[-1] if player else ""
        stat_words = {x for x in stat.split() if x not in ("made", "total")}
        same_stat = bool(stat_words & set(norm(leg.team2).split())) or any(x in desc for x in stat_words)
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
    used = set()
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
    return [w for w in ws if w.key not in used]


def _limit_number(limit: str | None) -> float | None:
    if not limit:
        return None
    m = re.findall(r"[+-]?\d+(?:\.\d+)?", limit)
    return float(m[0]) if m else None


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
            notes.append("same number" if abs(diff) < 1e-9 else f"{abs(diff):g} point{'s' if abs(diff) != 1 else ''} {'better' if diff > 0 else 'worse'}")
        if leg.price is not None and r.price is not None and leg.price != int(r.price):
            notes.append(f"price {leg.price:+d} vs {int(r.price):+d} sent")
    if r.dollars:
        ratio = w.risk / r.dollars
        if abs(ratio - 1) > 0.15:
            notes.append(f"stake ${w.risk:g} vs ${r.dollars:g} sent")
    if len(r.matched) > 1:
        notes.append(f"{len(r.matched)} wagers on it")
    return "bet: " + (", ".join(notes) if notes else "as sent")


def report(con, cfg: dict, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    tz = config.display_tz(cfg)
    since = datetime.fromisoformat(START).replace(tzinfo=tz).astimezone(timezone.utc)
    recs = recommendations(con, cfg, since)
    ws = wagers(since)
    own = match(recs, ws)
    graded = [r for r in recs if r.result]
    mw, ml, mp = (sum(r.result == x for r in graded) for x in "WLP")
    m_net = sum(r.model_dollars or 0 for r in graded)
    m_risk = sum(r.dollars for r in recs)
    followed = [r for r in recs if r.matched]
    f_net = sum(w.net for r in followed for w in r.matched if w.status in ("W", "L", "X"))
    o_set = [w for w in own if w.status in ("W", "L", "X")]
    o_net = sum(w.net for w in o_set)
    all_net = sum(w.net for w in ws if w.status in ("W", "L", "X"))
    open_ws = [w for w in ws if w.status not in ("W", "L", "X")]
    out = ["# Tracker: the model's picks against your bets (generated; do not edit)", "",
           f"From {START} (Mountain). Updated {now.astimezone(tz):%a %b %-d, %-I:%M %p} MT. Your wagers come from the account history, which "
           "shows a bet once it is graded (open bets are not readable); picks come from what Telegram sent.", "",
           "## Scoreboard", "",
           "| | Bets | Record | Net | Notes |", "|---|---|---|---|---|",
           f"| **Model** (every staked pick, at the stake and number sent) | {len(recs)} sent, {len(graded)} graded | {mw}-{ml}-{mp} | "
           f"{'+' if m_net >= 0 else '−'}${abs(m_net):,.2f} | ${m_risk:,.2f} recommended in all |",
           f"| **You, on the model's picks** | {sum(len(r.matched) for r in followed)} | "
           f"{sum(w.status == 'W' for r in followed for w in r.matched)}-{sum(w.status == 'L' for r in followed for w in r.matched)} | "
           f"{'+' if f_net >= 0 else '−'}${abs(f_net):,.2f} | followed {len(followed)} of {len(recs)} picks |",
           f"| **You, your own bets** | {len(own)} | {sum(w.status == 'W' for w in o_set)}-{sum(w.status == 'L' for w in o_set)} | "
           f"{'+' if o_net >= 0 else '−'}${abs(o_net):,.2f} | not on the model's list |",
           f"| **You, everything** | {len(ws)} graded | {sum(w.status == 'W' for w in ws)}-{sum(w.status == 'L' for w in ws)} | "
           f"{'+' if all_net >= 0 else '−'}${abs(all_net):,.2f} | the account's own grading |", ""]
    out += ["## Every pick sent, and what you did", "",
            "| Sent (MT) | Sport | Pick | Price sent | Don't bet past | Stake sent | Model result | You | Your result |", "|---|---|---|---|---|---|---|---|---|"]
    for r in recs:
        res = "open" if r.result is None else f"{r.result} ({'+' if (r.model_dollars or 0) >= 0 else '−'}${abs(r.model_dollars or 0):,.2f})"
        mine = "; ".join(f"{w.status if w.status in ('W', 'L', 'X') else 'open'} {('+' if w.net >= 0 else '−') + '$' + format(abs(w.net), ',.2f') if w.status in ('W', 'L', 'X') else ''}".strip()
                         for w in r.matched) or "—"
        price = "" if r.price is None else f" {int(r.price):+d}"
        out.append(f"| {r.sent.astimezone(tz):%a %-I:%M %p} | {r.sport} | {r.pick} | {price.strip() or '-110'} | {r.limit or ''} | ${r.dollars:g} | {res} | "
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
    out += ["", "How to read it: the model line uses the stake and number sent, so it is the model's own record. Your lines use the account's "
            "real results. A pick you bet at a worse number than sent, or past its limit, shows up in the 'You' column; that is the grader."]
    return "\n".join(out) + "\n"


def recap(con, cfg: dict) -> str:
    """Short phone version for the morning Telegram message."""
    text = report(con, cfg)
    rows = [l for l in text.splitlines() if l.startswith("| **")]
    keep = []
    for l in rows:
        cells = [c.strip() for c in l.strip("|").split("|")]
        keep.append(f"{cells[0].strip('*')}: {cells[2]}, {cells[3]} ({cells[1]})")
    return "TRACKER (since Nov 23)\n" + "\n".join(keep) + "\nDetails: docs/lanes/TRACKER.md and the board."


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
    p = config.ROOT / "docs" / "lanes" / "TRACKER.md"
    p.write_text(report(con, cfg))
    return p
