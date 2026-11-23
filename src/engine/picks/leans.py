"""Paper Leans: the agent's best handicapped opinions, clearly unproven, never staked (Kylor, 2026-11-23: "leans paper-only").

Why this exists: a model can drive a Bet only after it beats the closing line, and almost nothing has. Leans test whether the
agent's *judgment* beats the close, with every opinion logged at the number it was issued at and graded the same way as a Bet.

The rules are in code, not in the prompt:
  * The agent writes only: game, market, side, reason_type, reason (the written handicap), source, and for news a `news_at` time,
    for a forecast a `forecast_line` (where it expects Pinnacle to close). It cannot type a line, price, stake or "don't bet past".
  * Code stamps the Wagerhouse number and price from the slate sheet and the "don't bet past" number.
  * One of three reasons only: `news` (timestamped; Pinnacle must have a stored line from before the news and must not have
    moved for it yet), `forecast` (where the number is going and why), `weather` (a wind or weather case, totals only).
    A price gap alone, betting splits and reverse line movement are never a reason.
  * At most `leans.max_per_lane_per_week` per lane per Mountain-time week (Monday to Sunday).
  * A lean is fixed when issued. It is never re-stamped, edited or removed, so the record cannot be flattered later.
  * Graded on closing-line value against Pinnacle, then result, and whether Kylor bet it at the stated number (`engine lean --bet KEY`).
  * Never staked. Not to be bet until `leans.promote_after_graded` are graded and the average closing-line value is above zero.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import yaml

from engine import config
from engine.odds import snapshots as snap
from engine.odds.espn import SourceError

SCHEMA = """
CREATE TABLE IF NOT EXISTS leans (
  lean_key VARCHAR PRIMARY KEY, issued_utc TIMESTAMP, week VARCHAR, sport VARCHAR, event_id VARCHAR, game VARCHAR,
  market VARCHAR, side VARCHAR, pick VARCHAR, book_line DOUBLE, price DOUBLE, dont_bet_past_line DOUBLE, dont_bet_past VARCHAR,
  pinnacle_line DOUBLE, reason_type VARCHAR, reason VARCHAR, source VARCHAR, news_at VARCHAR, pinnacle_before_news DOUBLE,
  forecast_line DOUBLE, kickoff_utc TIMESTAMP, bet_at_stated BOOLEAN);
CREATE TABLE IF NOT EXISTS lean_grades (
  lean_key VARCHAR PRIMARY KEY, pinnacle_close DOUBLE, clv_points DOUBLE, result VARCHAR, home_score INTEGER, away_score INTEGER,
  forecast_hit BOOLEAN, graded_utc TIMESTAMP);
"""
REASON_TYPES = ("news", "forecast", "weather")
FORBIDDEN = ("line", "price", "price_paid", "odds", "stake", "units", "edge", "value", "dont_bet_past", "book_line", "fair")
# a reason that is only one of these is a locked-out reason (CHARTER.md)
BANNED_REASON = re.compile(r"sharp money|reverse line|line movement|betting splits|bets? (?:vs|versus) money|public (?:is|are) (?:on|betting)|steam|price gap|better than (?:pinnacle|draftkings)", re.I)
DEFAULTS = {"enabled": True, "paper_only": True, "max_per_lane_per_week": 3, "max_pinnacle_move_since_news": 0.5, "promote_after_graded": 50}


def settings(cfg: dict) -> dict:
    return {**DEFAULTS, **(cfg.get("leans") or {})}


def decisions_path(day: str, sport: str):
    return config.ROOT / "docs" / "leans" / "decisions" / f"{day}-{sport.lower()}.yaml"


def week_of(when_utc: datetime, tz) -> str:
    """Monday (Mountain time) that starts the week this moment falls in, as YYYY-MM-DD."""
    local = when_utc.astimezone(tz)
    return (local - timedelta(days=local.weekday())).strftime("%Y-%m-%d")


def _news_time(raw) -> datetime | None:
    try:
        return datetime.strptime(str(raw or "").replace(" MT", "").strip(), "%Y-%m-%d %H:%M").replace(
            tzinfo=ZoneInfo("America/Denver")).astimezone(timezone.utc)
    except ValueError:
        return None


def _favorable_move(market: str, side: str, before: float, now: float) -> float:
    """Points Pinnacle has moved in the side's favour (more negative for a home spread, higher for an over...)."""
    if market == "spread":
        return (before - now) if side == "home" else (now - before)
    return (now - before) if side == "over" else (before - now)


def load(path) -> list[dict]:
    """Read and shape-check the agent's file. Anything it may not set is an error, not silently dropped."""
    data = yaml.safe_load(path.read_text()) or {}
    out = []
    for d in data.get("leans", []) or []:
        for k in FORBIDDEN:
            if k in d:
                raise SourceError(f"leans file may not set '{k}' (code stamps numbers): {d.get('game')}")
        for k in ("game", "market", "side", "reason_type", "reason", "source"):
            if not str(d.get(k, "")).strip():
                raise SourceError(f"lean is missing '{k}': {d.get('game')}")
        out.append(d)
    return out


def _find_side(sheet: dict, d: dict):
    for g in sheet["games"]:
        if g["game"].lower() == str(d["game"]).lower():
            for m in g["markets"]:
                if m["market"] == d["market"]:
                    for s in m.get("sides", []):
                        if s["side"] == d["side"]:
                            return g, m, s
    return None, None, None


def check(d: dict, cfg: dict, sheet: dict, pin_hist: dict, now: datetime) -> tuple[dict | None, str]:
    """Stamp one lean or say why not. Returns (row fields, '') or (None, reason)."""
    ls = settings(cfg)
    g, m, s = _find_side(sheet, d)
    if s is None:
        return None, "no such game, market and side on today's slate (or the book has not posted it)"
    if datetime.fromisoformat(g["start_utc"]) <= now:
        return None, "the game has started"
    if d["reason_type"] not in REASON_TYPES:
        return None, f"reason_type must be one of {REASON_TYPES}"
    if BANNED_REASON.search(str(d["reason"])):
        return None, "the reason leans on line movement, splits, a price gap or sharp money, which are never reasons (CHARTER.md)"
    if len(str(d["reason"]).split()) < 25:
        return None, "the written handicap is under 25 words; say what you found, why it matters and what the market is missing"
    if not str(d["source"]).startswith("http") and d["reason_type"] != "forecast":
        return None, "needs a source link (a page you opened)"
    pin_before = None
    if d["reason_type"] == "news":
        when = _news_time(d.get("news_at"))
        if when is None:
            return None, "news needs news_at ('YYYY-MM-DD HH:MM MT') from the source, not from now"
        if when > now:
            return None, "news_at is in the future"
        col = 1 if m["market"] == "spread" else 2
        base = [r for r in pin_hist.get(g["event_id"], []) if r[0] <= when and r[col] is not None]
        if not base:
            return None, "no Pinnacle line stored from before the news, so it cannot be shown that Pinnacle has not moved for it"
        pin_before = base[-1][col]
        pin_now = m.get("pinnacle_line")
        if pin_now is None:
            return None, "no Pinnacle line now"
        moved = _favorable_move(m["market"], s["side"], pin_before, pin_now)
        if moved > ls["max_pinnacle_move_since_news"]:
            return None, f"Pinnacle already moved {moved:g} points toward this side since the news (limit {ls['max_pinnacle_move_since_news']:g}); it is priced"
    if d["reason_type"] == "weather" and m["market"] != "total":
        return None, "weather leans are totals only"
    forecast = d.get("forecast_line")
    if d["reason_type"] == "forecast":
        try:
            forecast = float(forecast)
        except (TypeError, ValueError):
            return None, "a forecast needs forecast_line: the number you expect Pinnacle to close at"
    else:
        forecast = None
    # don't bet past: the landing-table limit when the numbers themselves clear the bar, otherwise the number as issued
    limit = s.get("limit_line") if s.get("numbers_say_bet") and s.get("limit_line") is not None else m["book_line"]
    team_or_side = s["pick"].rsplit(" ", 1)[0]
    show = (lambda x: x if s["side"] == "home" else -x) if m["market"] == "spread" else (lambda x: x)
    dbp = f"{team_or_side} {show(limit):+g}" if m["market"] == "spread" else f"{team_or_side} {limit:g}"
    return {"event_id": g["event_id"], "game": g["game"], "market": m["market"], "side": s["side"], "pick": s["pick"],
            "book_line": m["book_line"], "price": s["price"], "dont_bet_past_line": limit, "dont_bet_past": dbp,
            "pinnacle_line": m.get("pinnacle_line"), "reason_type": d["reason_type"], "reason": " ".join(str(d["reason"]).split()),
            "source": str(d["source"]), "news_at": d.get("news_at"), "pinnacle_before_news": pin_before, "forecast_line": forecast,
            "kickoff_utc": datetime.fromisoformat(g["start_utc"]).astimezone(timezone.utc).replace(tzinfo=None)}, ""


def ingest(cfg: dict, con, sheet: dict, day: str, sport: str, pin_hist: dict | None = None, now: datetime | None = None) -> list[str]:
    """Stamp and store the agent's leans for this sport. Returns plain-text lines saying what was kept and what was refused."""
    ls = settings(cfg)
    if not ls["enabled"]:
        return []
    path = decisions_path(day, sport)
    if not path.exists():
        return []
    from engine.picks import slate
    now = now or datetime.now(timezone.utc)
    pin_hist = slate.pinnacle_history(sport) if pin_hist is None else pin_hist
    con.execute(SCHEMA)
    tz = config.display_tz(cfg)
    week = week_of(now, tz)
    out = []
    for d in load(path):
        key = f"{d['game']}|{d['market']}|{d['side']}"
        if con.execute("SELECT 1 FROM leans WHERE lean_key=?", [key]).fetchone():
            continue    # fixed when issued
        used = con.execute("SELECT count(*) FROM leans WHERE sport=? AND week=?", [sport, week]).fetchone()[0]
        if used >= ls["max_per_lane_per_week"]:
            out.append(f"REFUSED {key}: already {used} {sport} leans this week (limit {ls['max_per_lane_per_week']})")
            continue
        row, why = check(d, cfg, sheet, pin_hist, now)
        if row is None:
            out.append(f"REFUSED {key}: {why}")
            continue
        con.execute("INSERT INTO leans VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [key, now.replace(tzinfo=None), week, sport, row["event_id"], row["game"], row["market"], row["side"], row["pick"],
                     row["book_line"], row["price"], row["dont_bet_past_line"], row["dont_bet_past"], row["pinnacle_line"],
                     row["reason_type"], row["reason"], row["source"], row["news_at"], row["pinnacle_before_news"],
                     row["forecast_line"], row["kickoff_utc"], None])
        out.append(f"LEAN (paper) {row['pick']} ({int(row['price']):+d}), {row['game']}: {row['reason_type']}. Don't bet past {row['dont_bet_past']}.")
    return out


def mark_bet(con, key_part: str, bet: bool = True) -> str:
    """Record whether Kylor actually bet a lean at the stated number. key_part: any unique part of the lean key."""
    con.execute(SCHEMA)
    rows = con.execute("SELECT lean_key FROM leans WHERE lower(lean_key) LIKE ?", [f"%{key_part.lower()}%"]).fetchall()
    if len(rows) != 1:
        raise ValueError(f"{len(rows)} leans match {key_part!r}; be more specific" if rows else f"no lean matches {key_part!r}")
    con.execute("UPDATE leans SET bet_at_stated=? WHERE lean_key=?", [bet, rows[0][0]])
    return f"{rows[0][0]}: marked {'bet at the stated number' if bet else 'not bet'}"


def grade(cfg: dict, con, scorer=None) -> list[str]:
    """Grade finished leans: result at the issued number, points vs Pinnacle's close, and whether a forecast came true."""
    from engine.picks import grade as g
    scorer = scorer or g.final_score
    con.execute(SCHEMA)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    out = []
    todo = con.execute("SELECT * FROM leans WHERE lean_key NOT IN (SELECT lean_key FROM lean_grades) AND kickoff_utc <= ?", [now]).fetchall()
    cols = [c[0] for c in con.description]
    for r in (dict(zip(cols, t)) for t in todo):
        col = "home_spread" if r["market"] == "spread" else "total"
        close = con.execute(f"SELECT {col} FROM line_snapshots WHERE event_id=? AND source=? AND ts_utc<=? AND {col} IS NOT NULL "
                            "ORDER BY ts_utc DESC LIMIT 1", [r["event_id"], snap.SHARP, r["kickoff_utc"]]).fetchone()
        score = scorer(r["sport"], r["event_id"])
        if score is None:
            out.append(f"waiting: lean {r['pick']} ({r['game']}) has no final score yet")
            continue
        res = g.result(r["market"], r["side"], r["book_line"], *score)
        clv = None if close is None else g.clv_points(r["market"], r["side"], r["book_line"], close[0])
        hit = None
        if r["forecast_line"] is not None and close is not None:
            # the forecast came true if Pinnacle closed at or beyond the forecast, in the direction of the lean
            hit = _favorable_move(r["market"], r["side"], r["pinnacle_line"], close[0]) >= _favorable_move(r["market"], r["side"], r["pinnacle_line"], r["forecast_line"]) - 1e-9
        con.execute("INSERT INTO lean_grades VALUES (?,?,?,?,?,?,?,?)",
                    [r["lean_key"], None if close is None else close[0], clv, res, score[0], score[1], hit, now])
        out.append(f"LEAN GRADED {r['pick']} ({r['game']}): {res}, " + ("closing-line value n/a" if clv is None else f"{clv:+.1f} points vs Pinnacle close"))
    return out


def record(con) -> dict:
    con.execute(SCHEMA)
    n = con.execute("SELECT count(*) FROM leans").fetchone()[0]
    w, l, p, clv, ng, nclv = con.execute(
        "SELECT count(*) FILTER (result='W'), count(*) FILTER (result='L'), count(*) FILTER (result='P'), avg(clv_points), count(*), count(clv_points) FROM lean_grades").fetchone()
    bet = con.execute("SELECT count(*) FROM leans WHERE bet_at_stated").fetchone()[0]
    return {"issued": n, "graded": ng, "w": w, "l": l, "p": p, "avg_clv": clv, "clv_n": nclv, "bet": bet}


def summary_text(cfg: dict, con) -> str:
    """One paragraph, always labelled paper, never merged with the Bets record."""
    ls = settings(cfg)
    r = record(con)
    if not r["issued"]:
        return "Paper Leans: none issued yet. Never staked; they test whether the agent's judgment beats the closing line."
    clv = "closing-line value n/a" if r["avg_clv"] is None else f"average {r['avg_clv']:+.2f} points vs Pinnacle close (on {r['clv_n']})"
    gate = (f"Not to be bet until {ls['promote_after_graded']} are graded and the average closing-line value is above zero "
            f"({r['graded']} graded so far).")
    return (f"Paper Leans (never staked): {r['issued']} issued, {r['graded']} graded, {r['w']}-{r['l']}-{r['p']}, {clv}. "
            f"You bet {r['bet']} of them at the stated number. {gate}")


def open_leans(con, sport: str | None = None) -> list[dict]:
    con.execute(SCHEMA)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    q = "SELECT * FROM leans WHERE kickoff_utc > ?" + (" AND sport=?" if sport else "") + " ORDER BY kickoff_utc"
    rows = con.execute(q, [now] + ([sport] if sport else [])).fetchall()
    cols = [c[0] for c in con.description]
    return [dict(zip(cols, r)) for r in rows]


def card_section(con, sport: str, tz) -> str:
    rows = open_leans(con, sport)
    if not rows:
        return ""
    lines = ["", "## Paper Leans (unproven, never staked, do not bet)", "",
             "The agent's own opinions, logged at the number they were issued at and graded against Pinnacle's close. They are not Bets.", ""]
    for r in rows:
        kick = r["kickoff_utc"].replace(tzinfo=timezone.utc).astimezone(tz)
        lines += [f"- **{r['pick']} ({int(r['price']):+d})**, {r['game']}, {kick:%a %-I:%M %p}. Reason type: {r['reason_type']}. "
                  f"Don't bet past {r['dont_bet_past']}. {r['reason']} Source: {r['source']}"]
    return "\n".join(lines) + "\n"
