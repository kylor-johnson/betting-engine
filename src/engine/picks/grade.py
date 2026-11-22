"""Grade the engine's own picks (plan item 3, docs/research/04-evaluation.md).

Each pick is graded three ways: the result at the number it was issued at, the points gained or lost
against Pinnacle's last line before kickoff (a compass, not proof), and units won or lost, shown next
to Kylor's own record. Flagged Passes are graded too, so the hit rate is not measured on bets alone.
A game with no final score yet, or no Pinnacle close, is left ungraded and says why. Nothing is guessed.
"""
from __future__ import annotations

from datetime import datetime, timezone

from engine import config
from engine.odds import espn
from engine.odds import snapshots as snap
from engine.odds.espn import SourceError
from engine.odds.math import american_to_decimal

GRADES = """
CREATE TABLE IF NOT EXISTS engine_pick_grades (
  pick_key VARCHAR PRIMARY KEY, game VARCHAR, pick VARCHAR, status VARCHAR, sport VARCHAR, market VARCHAR,
  issued_utc TIMESTAMP, issued_line DOUBLE, price DOUBLE, units DOUBLE, pinnacle_close DOUBLE,
  clv_points DOUBLE, home_score INTEGER, away_score INTEGER, result VARCHAR, profit_units DOUBLE, graded_utc TIMESTAMP);
"""
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{slug}/summary?event={eid}"


def result(market: str, side: str, line: float, home: int, away: int) -> str:
    """W, L or P for a side at the number it was issued at. `line` is the home spread, or the total."""
    if market == "spread":
        mine = (home - away + line) if side == "home" else (away - home - line)
    elif market == "total":
        mine = (home + away - line) if side == "over" else (line - home - away)
    else:
        raise ValueError(f"cannot grade market {market!r}")
    return "W" if mine > 0 else "L" if mine < 0 else "P"


def clv_points(market: str, side: str, issued: float, close: float) -> float:
    """Points better (+) or worse (-) than Pinnacle's close, from the side's own view."""
    if market == "spread":
        return (issued - close) if side == "home" else (close - issued)
    return (close - issued) if side == "over" else (issued - close)


def profit(units: float, price: float, res: str) -> float:
    return units * (american_to_decimal(price) - 1) if res == "W" else -units if res == "L" else 0.0


def final_score(sport: str, event_id: str) -> tuple[int, int] | None:
    """(home, away) once ESPN says the game is over, else None."""
    s, slug, _ = espn.LEAGUES[sport]
    data = espn._get(SUMMARY_URL.format(sport=s, slug=slug, eid=event_id))
    try:
        comp = data["header"]["competitions"][0]
        if not comp["status"]["type"]["completed"]:
            return None
        sc = {c["homeAway"]: int(float(c["score"])) for c in comp["competitors"]}
        return sc["home"], sc["away"]
    except (KeyError, IndexError, ValueError, TypeError):
        raise SourceError(f"ESPN summary for event {event_id} has no usable final score") from None


def run(cfg, con=None, scorer=final_score) -> list[str]:
    own = con is None
    con = con or snap.connect(config.DB)
    out: list[str] = []
    try:
        con.execute(GRADES)
        pc = cfg["picks"]
        events = con.execute("""
            SELECT pick_key, game, pick, status, book_line, price, ts_utc FROM engine_pick_events ORDER BY ts_utc""").fetchall()
        issued: dict[str, tuple] = {}
        for e in events:       # first time it was a Bet or Conditional; otherwise the first Pass
            k = e[0]
            if k not in issued or (issued[k][3] == "Pass" and e[3] != "Pass"):
                issued[k] = e
        done = {r[0] for r in con.execute("SELECT pick_key FROM engine_pick_grades").fetchall()}
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for key, (_, game, pick, status, line, price, ts) in issued.items():
            if key in done:
                continue
            eid, market, side = key.split("|")
            row = con.execute("SELECT sport, start_utc FROM line_snapshots WHERE event_id=? LIMIT 1", [eid]).fetchone()
            if row is None:
                out.append(f"NOT GRADED {pick} ({game}): no line snapshots for event {eid}")
                continue
            sport, start = row
            if start > now:
                continue
            col = "home_spread" if market == "spread" else "total"
            close = con.execute(f"SELECT {col} FROM line_snapshots WHERE event_id=? AND source=? AND ts_utc<=? AND {col} IS NOT NULL "
                                "ORDER BY ts_utc DESC LIMIT 1", [eid, snap.SHARP, start]).fetchone()
            if close is None:
                out.append(f"NOT GRADED {pick} ({game}): no Pinnacle line stored before kickoff")
                continue
            score = scorer(sport, eid)
            if score is None:
                out.append(f"waiting: {pick} ({game}) has no final score yet")
                continue
            units = pc["conditional_units"] if status == "Conditional" else pc["max_units"] if status == "Bet" else 0.0
            res = result(market, side, line, *score)
            clv = clv_points(market, side, line, close[0])
            con.execute("INSERT INTO engine_pick_grades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        [key, game, pick, status, sport, market, ts, line, price, units, close[0], clv, score[0], score[1],
                         res, profit(units, price, res) if units else 0.0, now])
            out.append(f"GRADED {status} {pick} ({game}): {res}, {clv:+.1f} points vs Pinnacle close")
    finally:
        if own:
            con.close()
    return out


def summary(con, cfg) -> list[str]:
    """Plain-text results: engine picks by status, then Kylor's own record for context."""
    con.execute(GRADES)
    lines: list[str] = []
    for status in ("Bet", "Conditional", "Pass"):
        n, w, l, p, clv, units = con.execute(
            "SELECT count(*), count(*) FILTER (result='W'), count(*) FILTER (result='L'), count(*) FILTER (result='P'), "
            "avg(clv_points), coalesce(sum(profit_units),0) FROM engine_pick_grades WHERE status=?", [status]).fetchone()
        if n:
            tail = f", {units:+.2f} units" if status != "Pass" else " (not bet; shows what passing was worth)"
            lines.append(f"{status}: {w}-{l}-{p}, average {clv:+.2f} points vs Pinnacle close{tail}")
    graded = con.execute("SELECT count(*) FROM engine_pick_grades WHERE status IN ('Bet','Conditional')").fetchone()[0]
    avg = con.execute("SELECT avg(clv_points) FROM engine_pick_grades WHERE status IN ('Bet','Conditional')").fetchone()[0]
    if graded >= 100 and avg is not None and avg <= 0:
        lines.append(f"VERDICT: {graded} graded picks and they have NOT beaten Pinnacle's close on average ({avg:+.2f} points). Do not scale up.")
    else:
        lines.append(f"{graded} of 100 picks graded before sizing is revisited.")
    try:
        r = con.execute("SELECT count(*), sum(risk), sum(net) FROM wagers WHERE status IS NOT NULL").fetchone()
        if r and r[0]:
            lines.append(f"Your own bets, all history: {r[0]} wagers, ${r[2]:+,.0f} on ${r[1]:,.0f} risked.")
    except Exception:
        pass
    return lines
