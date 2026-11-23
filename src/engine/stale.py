"""STALE NUMBER alerts: Wagerhouse is behind the sharp market on a full-game side or total (Kylor, 2026-11-23).

"The line is 47.5 and Pinnacle says 48.5: get it before it moves." When Wagerhouse's number or price is better than Pinnacle's fair price by the
engine's own bar (picks.min_value, 2%), priced with how real games land on 3 and 7, a message goes to Telegram, labelled a PRICE ALERT, NOT A PICK:
no reason is known, so the research agent has not looked at it. It stays inside the locked rule that a price gap alone is never a reason for a pick;
an alert is not a pick. Each alert is frozen at the number shown and graded on the result and against Pinnacle's close, so the record shows whether
stale numbers are worth chasing (`engine stale`).

Limits: one alert per game, market, side and Wagerhouse number; at most `stale.max_per_day` a day; the sports in `stale.sports` (NFL, NBA and,
since 2026-11-24, College, whose landing table comes from the cached CollegeFootballData closes). Pinnacle is the reference. A big gap (over `stale.max_gap_points`) is treated as a data mismatch, not an opportunity.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine import config
from engine.alerts import telegram
from engine.odds import snapshots as snap
from engine.odds.math import no_vig
from engine.picks.pricing import Landing, bell_rows

SCHEMA = """
CREATE TABLE IF NOT EXISTS stale_alerts (
  alert_key VARCHAR PRIMARY KEY, ts_utc TIMESTAMP, sport VARCHAR, event_id VARCHAR, game VARCHAR, market VARCHAR, side VARCHAR, pick VARCHAR,
  wh_line DOUBLE, price DOUBLE, pinnacle_line DOUBLE, value DOUBLE, limit_line DOUBLE, dont_bet_past VARCHAR, kickoff_utc TIMESTAMP, rule_version VARCHAR);
CREATE TABLE IF NOT EXISTS stale_grades (
  alert_key VARCHAR PRIMARY KEY, pinnacle_close DOUBLE, clv_points DOUBLE, result VARCHAR, graded_utc TIMESTAMP);
ALTER TABLE stale_grades ADD COLUMN IF NOT EXISTS clv_chance DOUBLE;
"""
DEFAULTS = {"enabled": True, "sports": ["NFL", "NBA", "College"], "max_per_day": 10, "max_gap_points": 3.0}
_CACHE: dict = {}


def settings(cfg: dict) -> dict:
    return {**DEFAULTS, **(cfg.get("stale") or {})}


def landings(sport: str, cfg: dict) -> tuple[Landing, Landing]:
    """(spread, total) landing tables for the sport; built once per process."""
    if sport in _CACHE:
        return _CACHE[sport]
    if sport == "NFL":
        from engine.picks import sources
        rows = [r for r in sources.nfl_games(config.DATA / "raw" / "nflverse_games.csv")
                if r["result"] not in ("", None) and r["spread_line"] not in ("", None) and int(r["season"]) >= 2015]
        out = (Landing([(-float(r["spread_line"]), float(r["result"])) for r in rows], "spread", window=1.0),
               Landing([(float(r["total_line"]), float(r["total"])) for r in rows if r["total_line"] not in ("", None)], "total", window=3.0))
    elif sport == "NBA":
        sd = cfg["margin_sd"]["NBA"]
        out = (Landing(bell_rows("spread", sd["spread"], -25, 25), "spread", window=0.25, min_n=100),
               Landing(bell_rows("total", sd["total"], 180, 270), "total", window=0.25, min_n=100))
    elif sport == "College":
        from engine.models import openers      # cached CollegeFootballData closes and scores, 2021 on; no network
        games = [g for g in openers.cfb_games(2021) if g.close_margin is not None]
        out = (Landing([(-g.close_margin, g.margin) for g in games], "spread", window=1.5, min_n=600),
               Landing([(g.close_total, g.points) for g in games if g.close_total is not None], "total", window=3.0, min_n=600))
    else:
        raise ValueError(sport)
    _CACHE[sport] = out
    return out


def evaluate(w, p, lands: tuple[Landing, Landing], min_value: float, max_gap: float) -> list[dict]:
    """Candidate alerts for one game from a Wagerhouse and a Pinnacle snapshot (same read). Pure."""
    ls, lt = lands
    out = []
    specs = []
    if None not in (w.home_spread, w.home_spread_price, w.away_spread_price, p.home_spread, p.home_spread_price, p.away_spread_price):
        specs.append(("spread", ls, w.home_spread, p.home_spread, (w.home_spread_price, w.away_spread_price),
                      (p.home_spread_price, p.away_spread_price), ("home", "away")))
    if None not in (w.total, w.over_price, w.under_price, p.total, p.over_price, p.under_price):
        specs.append(("total", lt, w.total, p.total, (w.over_price, w.under_price), (p.over_price, p.under_price), ("over", "under")))
    for market, land, wl, pl, wp, pp, names in specs:
        if abs(wl - pl) > max_gap:
            continue
        try:
            fair = land.fair_from_price(pl, no_vig(*pp)[0])
            for i, side in enumerate(names):
                price = wp[i]
                val = land.value(fair, wl, side, price)
                if val < min_value:
                    continue
                _, lim = land.limit(fair, wl, side, price, min_value)
                if market == "spread":
                    show = (lambda x: x) if side == "home" else (lambda x: -x)
                    team = w.home if side == "home" else w.away
                    pick = f"{team} {show(wl):+g}"
                    dbp = None if lim is None else f"{team} {show(lim):+g}"
                    pin = f"{team} {show(pl):+g}"
                else:
                    pick = f"{side.title()} {wl:g}"
                    dbp = None if lim is None else f"{side.title()} {lim:g}"
                    pin = f"{side.title()} {pl:g}"
                out.append({"market": market, "side": side, "pick": pick, "wh_line": wl, "price": price, "pinnacle_line": pl, "pinnacle_pick": pin,
                            "value": val, "limit_line": lim, "dont_bet_past": dbp})
        except ValueError:      # too few past games near this line to price it
            continue
    return out


def message(sport_tag: str, c: dict, game: str, kick_txt: str) -> str:
    gap = ("the same number but a better price" if abs(c["wh_line"] - c["pinnacle_line"]) < 1e-9
           else f"Pinnacle has {c['pinnacle_pick']}")
    return (f"{sport_tag} · STALE NUMBER (a price alert, NOT a pick)\n{c['pick']} ({int(c['price']):+d}) at Wagerhouse; {gap}.\n{game}, {kick_txt}\n"
            f"Worth about {100 * c['value']:+.1f}% per $1 if Pinnacle is right. Don't bet past {c['dont_bet_past'] or 'this number'}.\n"
            "No reason is known: the research agent has not looked at it. Check for news first. Nothing here is staked or graded as a Bet.")


def scan(cfg: dict, env: dict, con, snaps: list, now: datetime, send: bool = True, sender=telegram.send, lands=None) -> list[str]:
    """Look at this read's Wagerhouse and Pinnacle snapshots, alert on new stale numbers. Never raises into the read."""
    st = settings(cfg)
    if not st["enabled"]:
        return []
    out = []
    try:
        con.execute(SCHEMA)
        start_day = now.astimezone(config.display_tz(cfg)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).replace(tzinfo=None)
        sent_today = con.execute("SELECT count(*) FROM stale_alerts WHERE ts_utc >= ?", [start_day]).fetchone()[0]
        from engine import lanes, version
        rv = version.stamp(cfg, con)
        pin = {s.event_id: s for s in snaps if s.source == snap.SHARP}
        min_value = cfg["picks"]["min_value"]
        tz = config.display_tz(cfg)
        for w in (s for s in snaps if s.source == snap.WH and s.sport in st["sports"]):
            p = pin.get(w.event_id)
            if p is None or w.start is None or w.start <= now:
                continue
            for c in evaluate(w, p, (lands or landings(w.sport, cfg)), min_value, st["max_gap_points"]):
                key = f"{w.event_id}|{c['market']}|{c['side']}|{c['wh_line']}"
                if con.execute("SELECT 1 FROM stale_alerts WHERE alert_key=?", [key]).fetchone():
                    continue
                if sent_today >= st["max_per_day"]:
                    out.append(f"stale alert held back (daily cap {st['max_per_day']}): {c['pick']}")
                    continue
                game = f"{w.away} at {w.home}"
                local = w.start.astimezone(tz)
                kick = f"{local:%a %-I:%M %p} MT"
                con.execute("INSERT INTO stale_alerts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            [key, now.replace(tzinfo=None), w.sport, w.event_id, game, c["market"], c["side"], c["pick"], c["wh_line"], c["price"],
                             c["pinnacle_line"], c["value"], c["limit_line"], c["dont_bet_past"], w.start.astimezone(timezone.utc).replace(tzinfo=None), rv])
                sent_today += 1
                msg = message(lanes.tag(cfg, w.sport) if cfg.get("lanes") else w.sport, c, game, kick)
                out.append(msg)
                if send:
                    sender(env, msg, lanes.thread_key(cfg, w.sport) if cfg.get("lanes") else None, kind="stale")
    except Exception as e:
        out.append(f"stale-number scan failed: {type(e).__name__}: {e}")
    return out


def new_sports(con, now: datetime) -> list[str]:
    """Sports with a stale-number alert first frozen in this read."""
    try:
        con.execute(SCHEMA)
        return [r[0] for r in con.execute("SELECT DISTINCT sport FROM stale_alerts WHERE ts_utc=?", [now.replace(tzinfo=None)]).fetchall()]
    except Exception:
        return []


def start_research(cfg: dict, con, now: datetime, sports: list[str]) -> list[str]:
    """Run on change (decision 0016): a research run for each sport with a new stale number, so the agent looks for the news behind it.
    Respects the agent's cooldown per sport. Never raises into a read."""
    out = []
    acfg = cfg.get("agent") or {}
    if not sports or not acfg.get("run_on_news", True):
        return out
    try:
        from engine.picks import agent
        con.execute(agent.SCHEMA)
        for sp in sports:
            if agent.cooled_down(con, now, acfg.get("cooldown_minutes", 90), sp):
                agent.spawn(f"stale number at Wagerhouse ({sp}): Pinnacle moved and Wagerhouse has not", sp)
                out.append(f"Started a {sp} research run: stale number at Wagerhouse.")
    except Exception as e:
        out.append(f"could not start a research run on a stale number: {type(e).__name__}: {e}")
    return out


def grade(con, scorer=None, cfg: dict | None = None) -> list[str]:
    """Result at the number shown, and points against Pinnacle's last line before kickoff (a compass, not proof)."""
    from engine.picks import grade as g
    scorer = scorer or g.final_score
    con.execute(SCHEMA)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    todo = con.execute("SELECT alert_key, sport, event_id, market, side, wh_line, kickoff_utc FROM stale_alerts WHERE kickoff_utc <= ? "
                       "AND alert_key NOT IN (SELECT alert_key FROM stale_grades)", [now]).fetchall()
    out = []
    for key, sport, eid, market, side, line, kick in todo:
        col = "home_spread" if market == "spread" else "total"
        close = con.execute(f"SELECT {col} FROM line_snapshots WHERE event_id=? AND source=? AND ts_utc<=? AND {col} IS NOT NULL ORDER BY ts_utc DESC LIMIT 1",
                            [eid, snap.SHARP, kick]).fetchone()
        score = scorer(sport, eid)
        if score is None:
            continue
        res = g.result(market, side, line, *score)
        clv = None if close is None else g.clv_points(market, side, line, close[0])
        from engine import clv as clv_mod
        ch = None if close is None else clv_mod.chance(cfg or config.load_config(), sport, market, side, line, close[0])
        con.execute("INSERT INTO stale_grades (alert_key, pinnacle_close, clv_points, result, graded_utc, clv_chance) VALUES (?,?,?,?,?,?)",
                    [key, None if close is None else close[0], clv, res, now, ch])
        out.append(f"STALE ALERT GRADED {key}: {res}" + ("" if clv is None else f", {clv:+.1f} points vs Pinnacle close")
                   + ("" if ch is None else f" ({100 * ch:+.1f}% win chance)"))
    return out


def summary_text(con) -> str:
    con.execute(SCHEMA)
    n = con.execute("SELECT count(*) FROM stale_alerts").fetchone()[0]
    if not n:
        return "Stale-number alerts: none yet."
    w, l, p, clv, cn, ng, ch = con.execute("SELECT count(*) FILTER (result='W'), count(*) FILTER (result='L'), count(*) FILTER (result='P'), "
                                           "avg(clv_points), count(clv_points), count(*), avg(clv_chance) FROM stale_grades").fetchone()
    tail = "closing-line value n/a" if clv is None else f"average {clv:+.2f} points vs Pinnacle close (on {cn})" + (
        "" if ch is None else f", {100 * ch:+.1f}% win chance")
    return f"Stale-number alerts: {n} sent, {ng} graded, {w}-{l}-{p}, {tail}. A price alert, never a Bet."
