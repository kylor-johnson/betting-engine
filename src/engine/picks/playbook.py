"""Playbook picks for NFL full-game markets (PLAYBOOK.md steps 3 to 5; decisions 0018 and 0019).

On every hourly read:
  1. our team points for every upcoming NFL game come from the game-script model (src/engine/models/script.py), fitted on every completed game;
  2. our number is pulled toward the market by the playbook's starting weights (`playbook.weights` in config.yaml). Kylor chose these over the
     walk-forward weights, which were zero for 2024 to 2026 (research 15, decision 0019);
  3. each Wagerhouse market (side, game total, team totals) is priced from that number with the same landing tables as the rest of the engine,
     and gets an edge: our chance of winning (pushes left out) minus the chance Wagerhouse's price needs;
  4. grades: A = clears the minimum edge and its principle has passed a test (none yet); B = clears the minimum edge; C = the best of the rest.
     A pick whose own number is far from the market is marked CHECK and held as C until the research agent clears it (not built yet);
  5. one position per game (the biggest edge), at most `max_per_week` staked picks per NFL week;
  6. stakes: A 1 unit, B 0.5 unit; half size for the first `half_size_weeks` weeks after `live_since`; paper again if staked picks are down
     `stop_loss_units` (decision 0018);
  7. A and B picks are frozen at the Wagerhouse number the first time they qualify, sent to Telegram, and graded on the result and against
     Pinnacle's last line before kickoff. C picks are only shown on the card.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine import config
from engine.odds import snapshots as snap
from engine.odds.math import american_to_decimal
from engine.picks.pricing import Landing, bell_rows

SCHEMA = """
CREATE TABLE IF NOT EXISTS playbook_picks (
  pick_key VARCHAR PRIMARY KEY, first_seen_utc TIMESTAMP, sport VARCHAR, event_id VARCHAR, game VARCHAR, market VARCHAR, side VARCHAR,
  pick VARCHAR, line DOUBLE, price DOUBLE, grade VARCHAR, edge DOUBLE, our_line DOUBLE, market_line DOUBLE, own_line DOUBLE, units DOUBLE,
  dollars DOUBLE, dont_bet_past VARCHAR, kickoff_utc TIMESTAMP, nfl_week VARCHAR, why VARCHAR, rule_version VARCHAR);
CREATE TABLE IF NOT EXISTS playbook_grades (
  pick_key VARCHAR PRIMARY KEY, home_score INTEGER, away_score INTEGER, result VARCHAR, profit_units DOUBLE, pinnacle_close DOUBLE,
  clv_points DOUBLE, clv_chance DOUBLE, graded_utc TIMESTAMP);
"""
DEFAULTS = {"enabled": True, "weights": {"team_total": 0.4, "total": 0.35, "side": 0.25},
            "min_edge": {"team_total": 0.03, "total": 0.03, "side": 0.03},
            "check_points": {"team_total": 4.0, "total": 4.0, "side": 3.0},
            "units": {"A": 1.0, "B": 0.5}, "half_size_weeks": 3, "live_since": "2026-11-24", "stop_loss_units": 10.0,
            "max_per_week": 5, "show_c": 5, "team_total_sd": 9.0}


def settings(cfg: dict) -> dict:
    out = {**DEFAULTS, **(cfg.get("playbook") or {})}
    for k in ("weights", "min_edge", "check_points", "units"):
        out[k] = {**DEFAULTS[k], **((cfg.get("playbook") or {}).get(k) or {})}
    return out


def chance_needed(price: float) -> float:
    return 1 / american_to_decimal(price)


def edge_of(land: Landing, fair: float, line: float, side: str, price: float) -> tuple[float, float]:
    """(edge, win chance without pushes) for a bet at `line` and `price` when our fair line is `fair`."""
    win, push, lose = land.probs(fair, line, side)
    p = win / (win + lose) if win + lose else 0.0
    return p - chance_needed(price), p


def stake(st: dict, grade: str, now: datetime, down_units: float, unit: float) -> tuple[float, float, str]:
    """(units, dollars, note) for a pick of this grade today."""
    if grade not in st["units"]:
        return 0.0, 0.0, "not staked"
    if down_units <= -abs(st["stop_loss_units"]):
        return 0.0, 0.0, f"paper: playbook picks are down {down_units:.1f} units (stop at {st['stop_loss_units']:g}); Kylor restarts"
    u = st["units"][grade]
    start = datetime.fromisoformat(st["live_since"]).replace(tzinfo=timezone.utc)
    note = f"{grade} pick"
    if now < start + timedelta(weeks=st["half_size_weeks"]):
        u /= 2
        note += f", half size until {(start + timedelta(weeks=st['half_size_weeks'])):%b %-d}"
    return u, round(u * unit, 2), note


def _team_land(st: dict) -> Landing:
    return Landing(bell_rows("total", st["team_total_sd"], 3, 50), "total", window=0.25, min_n=100)


def candidates(games: list[dict], st: dict, lands: tuple[Landing, Landing]) -> list[dict]:
    """Every priced bet for these games. Each game dict carries our and the market's numbers and Wagerhouse's lines. Pure."""
    ls, lt = lands
    tl = _team_land(st)
    out = []
    w = st["weights"]
    for g in games:
        # side: lines are the HOME spread (negative = home favored); margins are home minus away
        if g.get("wh_spread") is not None and g.get("mkt_margin") is not None:
            our_margin = g["mkt_margin"] + w["side"] * (g["own_margin"] - g["mkt_margin"])
            for side, price, team, show in (("home", g["wh_home_price"], g["home"], 1), ("away", g["wh_away_price"], g["away"], -1)):
                if price is None:
                    continue
                e, p = edge_of(ls, -our_margin, g["wh_spread"], side, price)
                out.append({**_base(g), "market": "side", "side": side, "pick": f"{team} {show * g['wh_spread']:+g}", "line": g["wh_spread"],
                            "price": price, "edge": e, "p": p, "our_line": -our_margin, "market_line": -g["mkt_margin"], "own_line": -g["own_margin"],
                            "check": abs(g["own_margin"] - g["mkt_margin"]) > st["check_points"]["side"], "land": ls})
        if g.get("wh_total") is not None and g.get("mkt_total") is not None:
            our_total = g["mkt_total"] + w["total"] * (g["own_total"] - g["mkt_total"])
            for side, price in (("over", g["wh_over"]), ("under", g["wh_under"])):
                if price is None:
                    continue
                e, p = edge_of(lt, our_total, g["wh_total"], side, price)
                out.append({**_base(g), "market": "total", "side": side, "pick": f"{side.title()} {g['wh_total']:g}", "line": g["wh_total"],
                            "price": price, "edge": e, "p": p, "our_line": our_total, "market_line": g["mkt_total"], "own_line": g["own_total"],
                            "check": abs(g["own_total"] - g["mkt_total"]) > st["check_points"]["total"], "land": lt})
        for who in ("home", "away"):
            tt = g.get(f"wh_tt_{who}")
            if not tt or g.get(f"own_{who}") is None:
                continue
            mkt = g.get(f"mkt_tt_{who}") or tt["line"]
            ours = mkt + w["team_total"] * (g[f"own_{who}"] - mkt)
            team = g[who]
            for side, price in (("over", tt["over"]), ("under", tt["under"])):
                if price is None:
                    continue
                e, p = edge_of(tl, ours, tt["line"], side, price)
                out.append({**_base(g), "market": "team_total", "side": f"{who}_{side}", "pick": f"{team} team total {side} {tt['line']:g}",
                            "line": tt["line"], "price": price, "edge": e, "p": p, "our_line": ours, "market_line": mkt, "own_line": g[f"own_{who}"],
                            "check": abs(g[f"own_{who}"] - mkt) > st["check_points"]["team_total"], "land": tl, "tt_side": side})
    return out


def _base(g: dict) -> dict:
    return {"event_id": g["event_id"], "game": f"{g['away']} at {g['home']}", "kick": g["kick"], "home": g["home"], "away": g["away"],
            "own_home": g.get("own_home"), "own_away": g.get("own_away"), "mkt_home": g.get("mkt_home"), "mkt_away": g.get("mkt_away")}


def key_of(c: dict) -> str:
    return f"{c['event_id']}|{c['market']}|{c['side']}"


def grade_all(cands: list[dict], st: dict, passed: set[str] = frozenset(), checks: dict | None = None) -> list[dict]:
    """Grade, keep one position per game, sort by edge. `checks` maps a pick key to the research agent's verdict on a CHECK pick. Pure."""
    checks = checks or {}
    best: dict[str, dict] = {}
    for c in cands:
        clears = c["edge"] >= st["min_edge"][c["market"]]
        verdict = checks.get(key_of(c)) or {}
        cleared = c["check"] and str(verdict.get("verdict", "")).lower() == "clear"
        c["grade"] = ("A" if c["market"] in passed else "B") if clears and (not c["check"] or cleared) else "C"
        if clears and c["check"] and not cleared:
            c["note"] = ("CHECK held: " + str(verdict.get("why", "")).strip()) if verdict else \
                "CHECK: our number is far from the market; held until the research agent finds what the market knows"
        else:
            c["note"] = ("CHECK cleared: " + str(verdict.get("why", "")).strip()) if cleared else ""
        k = c["event_id"]
        if k not in best or (c["grade"] < best[k]["grade"]) or (c["grade"] == best[k]["grade"] and c["edge"] > best[k]["edge"]):
            best[k] = c
    return sorted(best.values(), key=lambda c: (c["grade"], -c["edge"]))


def load_checks(now: datetime, cfg: dict) -> dict:
    """The research agent's verdicts on CHECK picks: docs/cards/decisions/<day>-nfl-checks.yaml (today and yesterday, today wins)."""
    import yaml
    tz = config.display_tz(cfg)
    out = {}
    for d in (now - timedelta(days=1), now):
        p = config.ROOT / "docs" / "cards" / "decisions" / f"{d.astimezone(tz):%Y-%m-%d}-nfl-checks.yaml"
        if p.exists():
            try:
                for c in (yaml.safe_load(p.read_text()) or {}).get("checks", []) or []:
                    if c.get("key") and c.get("verdict") in ("clear", "hold"):
                        out[str(c["key"])] = c
            except Exception:
                continue
    return out


def why(c: dict) -> str:
    h, a = c["home"], c["away"]
    ours = f"our handicap {a} {c['own_away']:.1f}, {h} {c['own_home']:.1f}" if c.get("own_home") is not None else "our handicap"
    mkt = f"market {a} {c['mkt_away']:.1f}, {h} {c['mkt_home']:.1f}" if c.get("mkt_home") is not None else ""
    return (f"{ours} ({mkt}). Blended at the playbook weight, our {c['market'].replace('_', ' ')} number is {c['our_line']:.1f} "
            f"against Wagerhouse's {c['line']:g}; win chance {100 * c['p']:.1f}% against {100 * chance_needed(c['price']):.1f}% needed.")


# ---------- live: gather inputs from the database ----------

def _latest(con, source: str, now: datetime) -> dict[str, tuple]:
    rows = con.execute(f"""SELECT {snap.COLS} FROM line_snapshots s WHERE source=? AND sport='NFL' AND start_utc > ?
                           AND ts_utc = (SELECT max(ts_utc) FROM line_snapshots t WHERE t.source=s.source AND t.event_id=s.event_id)""",
                       [source, now.replace(tzinfo=None)]).fetchall()
    return {r[3]: r for r in rows}


def _team_totals(con, source: str) -> dict[tuple[str, str, str], dict]:
    rows = con.execute("""SELECT home, away, description, line, price_a, price_b FROM derivative_snapshots d
                          WHERE source=? AND sport='NFL' AND market='team_total' AND period='Game'
                          AND ts_utc = (SELECT max(ts_utc) FROM derivative_snapshots e WHERE e.source=d.source AND e.home=d.home AND e.away=d.away
                                        AND e.market=d.market AND e.period=d.period)""", [source]).fetchall()
    return {(h, a, desc): {"line": line, "over": o, "under": u} for h, a, desc, line, o, u in rows}


def _qb_out_teams() -> set[str]:
    """Teams whose quarterback is out per adjustments.yaml (an NFL spread entry of 2.5+ points naming a quarterback change)."""
    try:
        from engine.picks import slate
        out = set()
        for a in slate.load_adjustments():
            if a.get("market") == "spread" and abs(float(a.get("points") or 0)) >= 2.5:
                txt = str(a.get("reason", "")).lower()
                if any(w in txt for w in ("starts", "starter", "quarterback", " qb", "out ")):
                    out.add(a.get("team"))
        return out
    except Exception:
        return set()


def live_games(con, now: datetime) -> tuple[list[dict], list[str]]:
    from engine.models import script
    from engine.models.props import TEAM_NAMES
    problems = []
    state: dict = {}
    rows = script.build_features(state=state)
    model = script.fit_live(rows)
    wh, pin = _latest(con, snap.WH, now), _latest(con, snap.SHARP, now)
    tt_wh, tt_pin = _team_totals(con, "Wagerhouse"), _team_totals(con, "Pinnacle")
    try:
        wind = {r[0]: (r[1], r[2]) for r in con.execute("SELECT event_id, arg_max(wind_mph, ts_utc), arg_max(precip_mm, ts_utc) FROM wind_forecasts GROUP BY 1").fetchall()}
    except Exception:
        wind = {}
    qb_out = _qb_out_teams()
    season = max(r["season"] for r in rows)
    games = []
    for eid, w in wh.items():
        _, _, _, _, away, home, start, hs, hsp, asp, _, _, tot, op, up = w
        ha, aa = TEAM_NAMES.get(home), TEAM_NAMES.get(away)
        if not ha or not aa or hs is None or tot is None:
            problems.append(f"playbook: skipped {away} at {home} (team name or line missing)")
            continue
        p = pin.get(eid)
        m_spread = p[7] if p and p[7] is not None else hs           # market reference: Pinnacle when posted, else Wagerhouse
        m_total = p[12] if p and p[12] is not None else tot
        imp_h, imp_a = m_total / 2 - m_spread / 2, m_total / 2 + m_spread / 2
        wd, rn = wind.get(eid, (None, None))
        own = {}
        for team, opp, is_home, imp in ((ha, aa, 1, imp_h), (aa, ha, 0, imp_a)):
            r = script.live_row(state, season, team, opp, is_home, imp, -m_spread, m_total,
                                backup_qb=int((home if is_home else away) in qb_out), wind=wd, rain=rn, dome=0 if wd is not None else 1)
            v = script.vector(r)
            own[is_home] = script.predict(model, v) if v else None
        if None in own.values():
            problems.append(f"playbook: no form for {away} at {home}")
            continue
        g = {"event_id": eid, "home": home, "away": away, "kick": start.replace(tzinfo=timezone.utc),
             "own_home": own[1], "own_away": own[0], "own_margin": own[1] - own[0], "own_total": own[1] + own[0],
             "mkt_home": imp_h, "mkt_away": imp_a, "mkt_margin": -m_spread, "mkt_total": m_total,
             "wh_spread": hs, "wh_home_price": hsp, "wh_away_price": asp, "wh_total": tot, "wh_over": op, "wh_under": up}
        for who, name in (("home", home), ("away", away)):
            t = tt_wh.get((home, away, who))
            if t and t["line"] is not None:
                g[f"wh_tt_{who}"] = t
                tp = tt_pin.get((home, away, who))
                g[f"mkt_tt_{who}"] = tp["line"] if tp and tp["line"] is not None else None
        games.append(g)
    return games, problems


def nfl_week(kick: datetime) -> str:
    from engine.picks.teasers import nfl_week as w
    return w(kick)


def run(cfg: dict, env: dict, con, now: datetime, send: bool = True) -> tuple[list[str], str]:
    """Price, grade, freeze and alert. Returns (log lines, card text). Never raises into the read."""
    st = settings(cfg)
    if not st["enabled"]:
        return [], ""
    out = []
    try:
        con.execute(SCHEMA)
        from engine import stale, version
        lands = stale.landings("NFL", cfg)
        games, problems = live_games(con, now)
        out += problems
        graded = grade_all(candidates(games, st, lands), st, checks=load_checks(now, cfg))
        down = con.execute("SELECT coalesce(sum(profit_units), 0) FROM playbook_grades").fetchone()[0]
        rv = version.stamp(cfg, con)
        unit = cfg.get("unit", 25)
        tz = config.display_tz(cfg)
        for c in graded:
            if c["grade"] not in ("A", "B"):
                continue
            key = f"{c['event_id']}|{c['market']}|{c['side']}"
            if con.execute("SELECT 1 FROM playbook_picks WHERE event_id=?", [c["event_id"]]).fetchone():
                continue        # one position per game, frozen at first qualification
            week = nfl_week(c["kick"])
            n_week = con.execute("SELECT count(*) FROM playbook_picks WHERE nfl_week=? AND units > 0", [week]).fetchone()[0]
            if n_week >= st["max_per_week"]:
                out.append(f"playbook: weekly cap reached ({st['max_per_week']}); not issued: {c['pick']}")
                continue
            units, dollars, note = stake(st, c["grade"], now, down, unit)
            _, lim = c["land"].limit(c["our_line"], c["line"], c["side"] if c["market"] != "team_total" else c["tt_side"], c["price"],
                                     st["min_edge"][c["market"]] / 2)
            dbp = None if lim is None else _show(c, lim)
            con.execute("INSERT INTO playbook_picks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        [key, now.replace(tzinfo=None), "NFL", c["event_id"], c["game"], c["market"], c["side"], c["pick"], c["line"], c["price"],
                         c["grade"], c["edge"], c["our_line"], c["market_line"], c["own_line"], units, dollars, dbp,
                         c["kick"].astimezone(timezone.utc).replace(tzinfo=None), week, why(c), rv])
            msg = (f"NFL · PLAYBOOK BET ({c['grade']})\n{c['pick']} ({int(c['price']):+d})\n{c['game']}, {c['kick'].astimezone(tz):%a %-I:%M %p} MT\n"
                   f"Stake: ${dollars:g} ({note})\nDon't bet past {dbp or 'this number'}.\nWhy: {why(c)}" + (f"\n{c['note']}" if c.get("note") else ""))
            out.append(msg)
            if send and units > 0:
                from engine.alerts import telegram
                telegram.send(env, msg, "nfl_sides_totals", kind="bet")
        return out, card(con, cfg, graded, st, now)
    except Exception as e:
        return out + [f"playbook failed: {type(e).__name__}: {e}"], ""


def _show(c: dict, lim: float) -> str:
    if c["market"] == "side":
        team = c["home"] if c["side"] == "home" else c["away"]
        return f"{team} {(lim if c['side'] == 'home' else -lim):+g}"
    if c["market"] == "total":
        return f"{c['side'].title()} {lim:g}"
    return f"{c['pick'].rsplit(' ', 1)[0]} {lim:g}"


def card(con, cfg: dict, graded: list[dict], st: dict, now: datetime) -> str:
    tz = config.display_tz(cfg)
    issued = con.execute("SELECT pick, game, grade, price, dollars, dont_bet_past, kickoff_utc, why FROM playbook_picks WHERE kickoff_utc > ? "
                         "ORDER BY kickoff_utc", [now.replace(tzinfo=None)]).fetchall()
    rec = record(con)
    w = st["weights"]
    out = ["# NFL playbook picks", "",
           f"How these are made: PLAYBOOK.md. Our team points come from the game-script model; our number is pulled toward the market at the playbook's "
           f"starting weights (side {w['side']}, game total {w['total']}, team total {w['team_total']}). The walk-forward test gave these markets no weight "
           "for 2024 to 2026 (research 15); Kylor chose to bet them anyway (decision 0019).", "",
           f"**Record:** {rec}", "", "## Issued (staked, frozen at the number shown)", ""]
    if issued:
        out += ["| Pick | Game | Grade | Stake | Don't bet past | Kickoff (MT) | Why |", "|---|---|---|---|---|---|---|"]
        for pick, game, grade, price, dollars, dbp, kick, wy in issued:
            out.append(f"| {pick} ({int(price):+d}) | {game} | {grade} | ${dollars:g} | {dbp or ''} | "
                       f"{kick.replace(tzinfo=timezone.utc).astimezone(tz):%a %-I:%M %p} | {wy} |")
    else:
        out.append("None open.")
    rest = [c for c in graded if c["grade"] == "C"][: st["show_c"]]
    out += ["", "## Best of the rest (C: shown, not staked)", "",
            "CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in "
            "`docs/cards/decisions/<date>-nfl-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`); a cleared one is issued as a B pick on the next read.", ""]
    if rest:
        out += ["| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |", "|---|---|---|---|---|---|"]
        for c in rest:
            out.append(f"| {c['pick']} ({int(c['price']):+d}) | {c['game']} | {100 * c['edge']:+.1f}% | {c['our_line']:.1f} / {c['market_line']:.1f} / {c['own_line']:.1f} | "
                       f"{c['note'] or 'under the minimum edge'} | `{key_of(c)}` |")
    else:
        out.append("None.")
    return "\n".join(out) + "\n"


def record(con) -> str:
    con.execute(SCHEMA)
    w, l, p, units, clv, n = con.execute("SELECT count(*) FILTER (result='W'), count(*) FILTER (result='L'), count(*) FILTER (result='P'), "
                                         "coalesce(sum(profit_units),0), avg(clv_chance), count(*) FROM playbook_grades").fetchone()
    open_n = con.execute("SELECT count(*) FROM playbook_picks WHERE pick_key NOT IN (SELECT pick_key FROM playbook_grades)").fetchone()[0]
    if not n:
        return f"no graded picks yet; {open_n} open."
    c = "closing-line value n/a" if clv is None else f"closing-line value {100 * clv:+.1f}% win chance"
    return f"{w}-{l}-{p}, {units:+.2f} units, {c}; {open_n} open."


def grade(con, cfg: dict, scorer=None) -> list[str]:
    from engine import clv as clv_mod
    from engine.picks import grade as g
    scorer = scorer or g.final_score
    con.execute(SCHEMA)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    out = []
    for key, eid, market, side, line, price, units, kick in con.execute(
            "SELECT pick_key, event_id, market, side, line, price, units, kickoff_utc FROM playbook_picks WHERE kickoff_utc <= ? "
            "AND pick_key NOT IN (SELECT pick_key FROM playbook_grades)", [now]).fetchall():
        score = scorer("NFL", eid)
        if score is None:
            continue
        hs, as_ = score
        if market == "team_total":
            who, ou = side.split("_")
            pts = hs if who == "home" else as_
            v = (pts - line) if ou == "over" else (line - pts)
            res = "W" if v > 0 else "L" if v < 0 else "P"
            close = cp = cc = None
        else:
            res = g.result("spread" if market == "side" else "total", side, line, hs, as_)
            col = "home_spread" if market == "side" else "total"
            row = con.execute(f"SELECT {col} FROM line_snapshots WHERE event_id=? AND source=? AND ts_utc<=? AND {col} IS NOT NULL "
                              "ORDER BY ts_utc DESC LIMIT 1", [eid, snap.SHARP, kick]).fetchone()
            close = None if row is None else row[0]
            mk = "spread" if market == "side" else "total"
            cp = None if close is None else g.clv_points(mk, side, line, close)
            cc = None if close is None else clv_mod.chance(cfg, "NFL", mk, side, line, close)
        prof = g.profit(units, price, res) if units else 0.0
        con.execute("INSERT INTO playbook_grades VALUES (?,?,?,?,?,?,?,?,?)", [key, hs, as_, res, prof, close, cp, cc, now])
        out.append(f"PLAYBOOK GRADED {key}: {res} ({prof:+.2f} units)")
    return out
