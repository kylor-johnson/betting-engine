"""Playbook picks: NFL, NBA and college; sides, totals, team totals and props (PLAYBOOK.md steps 3 to 5; decisions 0018, 0019, 0021, 0022).

Per sport (`playbook.sports.<SPORT>` in config.yaml): which game-script model feeds it (NFL `script`, NBA `nba_script`, college
`college_script`), whether full-game picks are staked or only shown (`full_game: stake | show`), whether props run, caps per week or per day.

On every hourly read:
  1. our team points for every upcoming NFL game come from the game-script model (src/engine/models/script.py), fitted on every completed game;
  2. our number is pulled toward the market by the playbook's starting weights (`playbook.weights` in config.yaml). Kylor chose these over the
     walk-forward weights, which were zero for 2024 to 2026 (research 15, decision 0019);
  3. each Wagerhouse market (side, game total, team totals) is priced from that number with the same landing tables as the rest of the engine,
     and gets an edge: our chance of winning (pushes left out) minus the chance Wagerhouse's price needs;
  4. grades: A = clears the minimum edge and its principle has passed a test (none yet); B = clears the minimum edge; C = the best of the rest.
     A pick whose own number is far from the market is marked CHECK and held as C until the research agent clears it in the checks file;
  5. one full-game position per game (the biggest edge), capped per week (NFL, college) or per day (NBA); props capped per game and period;
  6. stakes: A 1 unit, B 0.5 unit; half size for the first `half_size_weeks` weeks after `live_since`; paper again if staked picks are down
     `stop_loss_units` (decision 0018);
  7. A and B picks are frozen at the Wagerhouse number the first time they qualify, sent to Telegram, and graded on the result and against
     Pinnacle's last line before kickoff. C picks are only shown on the card.

Research 18 / decision 0025 (Kylor approved 2026-11-23):
  * paper mode: `full_game: paper` and `props_stake: false` issue, freeze and grade A/B picks exactly as before, at $0 (`units` 0, the
    grade's size kept in `nominal_units`); they are not sent to Telegram. Caps count paper picks too, so the paper record has the same volume;
  * one unit per game: a staked pick that would take the money already on that game (playbook picks plus teaser tickets with a leg in it)
    past one unit of the sport is issued as paper instead;
  * never into a move: a pick whose side Pinnacle has moved against since it was first priced (1+ point on a side, total or team total;
    10+ points of chance, or the line, on a prop) drops to C;
  * a CHECK "clear" needs `because` (a positive, sourced reason the market is wrong) and `market_assumes` (what the current number already
    prices); "nothing found" does not clear. Cleared picks are staked like any other B pick since decision 0027 (paper under 0025/0026);
  * NBA (config `playbook.calibrate_props`) props are re-centred on outcomes before the blend (models/calibrate.py);
  * props and team totals are graded against Pinnacle's last price before the start (no-vig chance of our bet minus the chance our price
    needed), and every message is saved to `alerts_sent`.

Decision 0027 (research 19, Kylor: "fix it"):
  * weekly cap: staked dollars across every sport and teaser ticket, Monday to Sunday Mountain, stay under `playbook.weekly_cap_dollars`;
    a pick past it is issued as paper and named in the 9am recap;
  * the NFL stop counts teaser tickets as well as NFL playbook picks (`down_units`);
  * every pick carries `price_edge`: the edge it would have if our number were the market's, i.e. the part that is only Wagerhouse's price
    against Pinnacle. The rest of the edge is the handicap. The message shows both.
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
CREATE TABLE IF NOT EXISTS playbook_candidates (
  cand_key VARCHAR PRIMARY KEY, first_seen_utc TIMESTAMP, sport VARCHAR, event_id VARCHAR, market VARCHAR, side VARCHAR, line DOUBLE,
  price DOUBLE, grade VARCHAR, edge DOUBLE, own_value DOUBLE, market_value DOUBLE, kickoff_utc TIMESTAMP, game VARCHAR, outcome DOUBLE, graded_utc TIMESTAMP);
CREATE TABLE IF NOT EXISTS playbook_grades (
  pick_key VARCHAR PRIMARY KEY, home_score INTEGER, away_score INTEGER, result VARCHAR, profit_units DOUBLE, pinnacle_close DOUBLE,
  clv_points DOUBLE, clv_chance DOUBLE, graded_utc TIMESTAMP);
ALTER TABLE playbook_picks ADD COLUMN IF NOT EXISTS nominal_units DOUBLE;
ALTER TABLE playbook_grades ADD COLUMN IF NOT EXISTS nominal_profit DOUBLE;
ALTER TABLE playbook_picks ADD COLUMN IF NOT EXISTS price_edge DOUBLE;
"""
PICK_COLS = ("pick_key, first_seen_utc, sport, event_id, game, market, side, pick, line, price, grade, edge, our_line, market_line, own_line, "
             "units, dollars, dont_bet_past, kickoff_utc, nfl_week, why, rule_version, nominal_units, price_edge")
GRADE_COLS = "pick_key, home_score, away_score, result, profit_units, pinnacle_close, clv_points, clv_chance, graded_utc, nominal_profit"
DEFAULTS = {"enabled": True, "weights": {"team_total": 0.4, "total": 0.35, "side": 0.25, "prop": 0.5},
            "min_edge": {"team_total": 0.03, "total": 0.03, "side": 0.03, "prop": 0.04},
            "check_points": {"team_total": 4.0, "total": 4.0, "side": 3.0, "prop": 0.15},
            "units": {"A": 1.0, "B": 0.5}, "half_size_weeks": 0, "live_since": "2026-11-24", "stop_loss_units": 10.0, "show_c": 5,
            "game_cap_units": 1.0, "move_points": 1.0, "move_chance": 0.10, "calibrate_props": ["NBA"], "props_stake": True,
            "weekly_cap_dollars": 0.0}


SPORT_DEFAULTS = {
    "NFL": {"full_game": "stake", "props": True, "period": "week", "max_per_period": 5, "props_per_period": 10, "props_per_game": 2,
            "team_total_sd": 9.0, "lane": "nfl_sides_totals", "props_lane": "nfl_props"},
    "NBA": {"full_game": "show", "props": True, "period": "day", "max_per_period": 2, "props_per_period": 4, "props_per_game": 2,
            "team_total_sd": 10.5, "check_points": {"side": 4.0, "total": 6.0, "team_total": 5.0}, "lane": "nba_sides_totals", "props_lane": "nba_props"},
    "College": {"full_game": "show", "props": False, "period": "week", "max_per_period": 5, "props_per_period": 0, "props_per_game": 0,
                "team_total_sd": 11.0, "check_points": {"side": 6.0, "total": 7.0, "team_total": 6.0}, "lane": "college_sides_totals", "props_lane": None},
}


def settings(cfg: dict, sport: str = "NFL") -> dict:
    """Shared playbook settings, overlaid with this sport's defaults and its `playbook.sports.<SPORT>` overrides."""
    pc = cfg.get("playbook") or {}
    sp = {**SPORT_DEFAULTS.get(sport, {}), **((pc.get("sports") or {}).get(sport) or {})}
    out = {**DEFAULTS, **{k: v for k, v in pc.items() if k != "sports"}, **{k: v for k, v in sp.items() if not isinstance(v, dict)}}
    for k in ("weights", "min_edge", "check_points", "units"):
        out[k] = {**DEFAULTS[k], **(pc.get(k) or {}), **(SPORT_DEFAULTS.get(sport, {}).get(k) or {}), **(sp.get(k) or {})}
    out["sport"] = sport
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
    if st["half_size_weeks"] and now < start + timedelta(weeks=st["half_size_weeks"]):
        u /= 2
        note += f", half size until {(start + timedelta(weeks=st['half_size_weeks'])):%b %-d}"
    return u, round(u * unit, 2), note


TT_RANGE = {"NFL": (3, 50), "College": (0, 75), "NBA": (70, 165)}


def _team_land(st: dict) -> Landing:
    lo, hi = TT_RANGE.get(st.get("sport", "NFL"), (0, 165))
    return Landing(bell_rows("total", st["team_total_sd"], lo, hi), "total", window=0.25, min_n=100)


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
                pe = edge_of(ls, -g["mkt_margin"], g["wh_spread"], side, price)[0]
                out.append({**_base(g), "market": "side", "side": side, "pick": f"{team} {show * g['wh_spread']:+g}", "line": g["wh_spread"],
                            "price": price, "edge": e, "p": p, "price_edge": pe, "our_line": -our_margin, "market_line": -g["mkt_margin"], "own_line": -g["own_margin"],
                            "check": abs(g["own_margin"] - g["mkt_margin"]) > st["check_points"]["side"], "land": ls})
        if g.get("wh_total") is not None and g.get("mkt_total") is not None and g.get("wh_over") is not None:
            our_total = g["mkt_total"] + w["total"] * (g["own_total"] - g["mkt_total"])
            for side, price in (("over", g["wh_over"]), ("under", g["wh_under"])):
                if price is None:
                    continue
                e, p = edge_of(lt, our_total, g["wh_total"], side, price)
                pe = edge_of(lt, g["mkt_total"], g["wh_total"], side, price)[0]
                out.append({**_base(g), "market": "total", "side": side, "pick": f"{side.title()} {g['wh_total']:g}", "line": g["wh_total"],
                            "price": price, "edge": e, "p": p, "price_edge": pe, "our_line": our_total, "market_line": g["mkt_total"], "own_line": g["own_total"],
                            "check": abs(g["own_total"] - g["mkt_total"]) > st["check_points"]["total"], "land": lt})
        for who in ("home", "away"):
            tt = g.get(f"wh_tt_{who}")
            if not tt or g.get(f"own_{who}") is None:
                continue
            mkt = g.get(f"mkt_tt_{who}") or tt["line"]
            if mkt is None:
                continue
            ours = mkt + w["team_total"] * (g[f"own_{who}"] - mkt)
            team = g[who]
            for side, price in (("over", tt["over"]), ("under", tt["under"])):
                if price is None:
                    continue
                e, p = edge_of(tl, ours, tt["line"], side, price)
                pe = edge_of(tl, mkt, tt["line"], side, price)[0]
                out.append({**_base(g), "market": "team_total", "side": f"{who}_{side}", "pick": f"{team} team total {side} {tt['line']:g}",
                            "line": tt["line"], "price": price, "edge": e, "p": p, "price_edge": pe, "our_line": ours, "market_line": mkt, "own_line": g[f"own_{who}"],
                            "check": abs(g[f"own_{who}"] - mkt) > st["check_points"]["team_total"], "land": tl, "tt_side": side})
    return out


def _base(g: dict) -> dict:
    return {"event_id": g["event_id"], "game": f"{g['away']} at {g['home']}", "kick": g["kick"], "home": g["home"], "away": g["away"],
            "own_home": g.get("own_home"), "own_away": g.get("own_away"), "mkt_home": g.get("mkt_home"), "mkt_away": g.get("mkt_away")}


def key_of(c: dict) -> str:
    return f"{c['event_id']}|{c['market']}|{c['side']}"


NOTHING_FOUND = ("nothing found", "found nothing", "no news", "nothing else", "nothing on", "did not find", "could not find", "no reason")


def valid_clear(v: dict) -> bool:
    """A CHECK clear counts only with a positive, sourced reason the market is wrong and a statement of what the market's number already
    prices (research 18, worry 4; Kylor 2026-11-23 on UCLA +7: 'there needs to be some reasoning as to why the line is at what it is')."""
    if str(v.get("verdict", "")).lower() != "clear":
        return False
    because, assumes, src = (str(v.get(k) or "").strip() for k in ("because", "market_assumes", "source"))
    if len(because) < 20 or len(assumes) < 10 or not src.startswith("http"):
        return False
    return not any(w in because.lower() for w in NOTHING_FOUND)


def grade_all(cands: list[dict], st: dict, passed: set[str] = frozenset(), checks: dict | None = None) -> list[dict]:
    """Grade, keep one position per game, sort by edge. `checks` maps a pick key to the research agent's verdict on a CHECK pick. Pure."""
    checks = checks or {}
    best: dict[str, dict] = {}
    for c in cands:
        clears = c["edge"] >= st["min_edge"][c["market"]]
        verdict = checks.get(key_of(c)) or {}
        cleared = c["check"] and valid_clear(verdict)
        c["cleared"] = bool(cleared)
        c["grade"] = ("A" if c["market"] in passed else "B") if clears and (not c["check"] or cleared) else "C"
        if clears and c["check"] and not cleared:
            if str(verdict.get("verdict", "")).lower() == "clear":
                c["note"] = "CHECK held: a clear needs a positive sourced reason (`because`) and what the number already prices (`market_assumes`)"
            else:
                c["note"] = ("CHECK held: " + str(verdict.get("why", "")).strip()) if verdict else \
                    "CHECK: our number is far from the market; held until the research agent finds what the market knows"
        else:
            c["note"] = ("CHECK cleared: " + str(verdict.get("because", "")).strip()) if cleared else ""
        k = c["event_id"]
        if k not in best or (c["grade"] < best[k]["grade"]) or (c["grade"] == best[k]["grade"] and c["edge"] > best[k]["edge"]):
            best[k] = c
    return sorted(best.values(), key=lambda c: (c["grade"], -c["edge"]))


def load_checks(now: datetime, cfg: dict, sport: str = "NFL") -> dict:
    """The research agent's verdicts on CHECK picks: docs/cards/decisions/<day>-<sport>-checks.yaml (today and yesterday, today wins)."""
    import yaml
    tz = config.display_tz(cfg)
    out = {}
    for d in (now - timedelta(days=1), now):
        p = config.ROOT / "docs" / "cards" / "decisions" / f"{d.astimezone(tz):%Y-%m-%d}-{sport.lower()}-checks.yaml"
        if p.exists():
            try:
                for c in (yaml.safe_load(p.read_text()) or {}).get("checks", []) or []:
                    if c.get("key") and c.get("verdict") in ("clear", "hold"):
                        out[str(c["key"])] = c
            except Exception:
                continue
    return out


# ---------- props (PLAYBOOK step 3, item 1) ----------

def american(dec: float) -> int:
    return int(round((dec - 1) * 100)) if dec >= 2 else int(round(-100 / (dec - 1)))


def prop_candidates(games: list[dict], pm, priced: list[dict], st: dict, sport: str = "NFL", shifts: dict | None = None) -> list[dict]:
    """Props from the NFL props model with the game script fed in: the player's projection is re-scaled from the market's implied team points
    to our blended team points (same power the props model fitted per stat), re-priced on the props model's own distribution, then blended
    with Pinnacle's no-vig chance at the playbook's prop weight. Prices are Pinnacle's: Wagerhouse prop lines are not readable (decision 0011),
    so each pick carries the worst Wagerhouse line and price at which it is still a bet."""
    by_teams = {(g["away"], g["home"]): g for g in games}
    w, wt = st["weights"]["prop"], st["weights"]["team_total"]
    lead_params, match_params = {}, {}
    if sport == "NFL":
        try:
            from engine.models import props_matchup, props_script
            lead_params = props_script.load(pm.season)
            match_params = props_matchup.load(pm.season)      # blitz and box splits: tested, not used today (research 17)
        except Exception:
            lead_params, match_params = {}, {}
    out = []
    for r in priced:
        g = by_teams.get((r["away"], r["home"]))
        stat = r["stat"]
        if g is None or stat not in pm.params or r.get("projection") is None:
            continue
        is_home = r["team"] == _abbr(g["home"], sport)
        imp = g["mkt_home"] if is_home else g["mkt_away"]
        own = g["own_home"] if is_home else g["own_away"]
        if imp is None:
            continue
        ours_pts = imp + wt * (own - imp)
        alpha = pm.params[stat][1] if sport == "NFL" else NBA_POINTS_POWER     # NBA: rates scale with team points at power 0.5 (research 08)
        proj = r["projection"] * ((ours_pts / imp) ** alpha if imp > 0 and ours_pts > 0 else 1.0)
        lead_note = ""
        if sport == "NFL" and lead_params:
            from engine.models import props_script
            m_home = g["mkt_margin"] + st["weights"]["side"] * (g["own_margin"] - g["mkt_margin"])
            margin = m_home if is_home else -m_home
            f = props_script.factor(lead_params, stat, margin)
            if abs(f - 1) > 0.002:
                proj *= f
                lead_note = f"; game script: expected margin {margin:+.1f} ({f - 1:+.1%} on the projection)"
            if stat in ("passing_yards", "rushing_yards") and match_params.get(stat, {}).get("use"):
                from engine.models import props_matchup
                opp = _abbr(g["away"] if is_home else g["home"], sport)
                mf = props_matchup.live_factor(pm.season, r["player_id"], opp, stat, match_params)
                if abs(mf - 1) > 0.002:
                    proj *= mf
                    lead_note += f"; matchup ({'blitz' if stat == 'passing_yards' else 'box'} splits) {mf - 1:+.1%}"
        model_p = pm.dists[stat].p_over(proj, r["line"])
        if shifts:
            from engine.models import calibrate
            model_p = calibrate.apply(model_p, shifts, stat)        # re-centred on outcomes (research 18, item 5)
        mkt = r["market_p_over"]
        our_over = mkt + w * (model_p - mkt)
        for side, price, p in (("over", r["over_price"], our_over), ("under", r["under_price"], 1 - our_over)):
            if price is None:
                continue
            e = p - chance_needed(price)
            worst = american(1 / max(1e-6, p - st["min_edge"]["prop"] / 2))
            label = r.get("label") or stat.replace("_", " ")
            out.append({"event_id": g["event_id"], "game": f"{g['away']} at {g['home']}", "kick": g["kick"], "home": g["home"], "away": g["away"],
                        "market": "prop", "side": side, "player_id": r["player_id"], "stat": stat, "line": r["line"], "price": price,
                        "pick": f"{r['player']} {side} {r['line']:g} {label}", "edge": e, "p": p, "our_line": proj, "market_line": mkt,
                        "price_edge": (mkt if side == "over" else 1 - mkt) - chance_needed(price),
                        "home_name": r["home"], "away_name": r["away"],
                        "own_line": model_p, "check": abs(model_p - mkt) >= st["check_points"]["prop"], "worst_price": worst,
                        "team_note": f"{r['team']} at {ours_pts:.1f} points in our script against {imp:.1f} in the market{lead_note}",
                        "model_note": f"typical outcome {round(pm.dists[stat].median(proj), 1):g} against a line of {r['line']:g}; chance over: ours {100 * our_over:.0f}%, "
                                      f"Pinnacle {100 * mkt:.0f}%" + (f"; {r['news']}" if r.get("news") else "")})
    return out


NBA_POINTS_POWER = 0.5


def _abbr(name: str, sport: str = "NFL") -> str | None:
    if sport == "NBA":
        from engine.models.nba_props import NAME_TO_ABBR
        return NAME_TO_ABBR.get(name)
    from engine.models.props import TEAM_NAMES
    return TEAM_NAMES.get(name)


def prop_key(c: dict) -> str:
    return f"prop|{c['player_id']}|{c['stat']}|{c['side']}|{c['line']:g}|{c['event_id']}"


def grade_props(cands: list[dict], st: dict, checks: dict | None = None) -> list[dict]:
    """B if it clears the prop edge and is not CHECK (or CHECK cleared); one side per player and stat. Pure."""
    checks = checks or {}
    best: dict[tuple, dict] = {}
    for c in cands:
        clears = c["edge"] >= st["min_edge"]["prop"]
        v = checks.get(prop_key(c)) or {}
        cleared = c["check"] and valid_clear(v)
        c["cleared"] = bool(cleared)
        c["grade"] = "B" if clears and (not c["check"] or cleared) else "C"
        if cleared:
            c["note"] = "CHECK cleared: " + str(v.get("because", ""))
        elif clears and c["check"]:
            c["note"] = ("CHECK held: a clear needs `because` and `market_assumes`" if str(v.get("verdict", "")).lower() == "clear" else
                         ("CHECK held: " + str(v.get("why", ""))) if v else "CHECK: the model and Pinnacle disagree by 15+ points of chance; held until researched")
        else:
            c["note"] = ""
        k = (c["player_id"], c["stat"])
        if k not in best or (c["grade"], -c["edge"]) < (best[k]["grade"], -best[k]["edge"]):
            best[k] = c
    return sorted(best.values(), key=lambda c: (c["grade"], -c["edge"]))


def why(c: dict) -> str:
    if c["market"] == "prop":
        return f"{c['model_note']}; {c['team_note']}. Win chance {100 * c['p']:.1f}% against {100 * chance_needed(c['price']):.1f}% at Pinnacle's price."
    h, a = c["home"], c["away"]
    ours = f"our handicap {a} {c['own_away']:.1f}, {h} {c['own_home']:.1f}" if c.get("own_home") is not None else "our handicap"
    mkt = f"market {a} {c['mkt_away']:.1f}, {h} {c['mkt_home']:.1f}" if c.get("mkt_home") is not None else ""
    return (f"{ours} ({mkt}). Blended at the playbook weight, our {c['market'].replace('_', ' ')} number is {c['our_line']:.1f} "
            f"against Wagerhouse's {c['line']:g}; win chance {100 * c['p']:.1f}% against {100 * chance_needed(c['price']):.1f}% needed.")


# ---------- live: gather inputs from the database ----------

def _latest(con, source: str, now: datetime, sport: str = "NFL") -> dict[str, tuple]:
    rows = con.execute(f"""SELECT {snap.COLS} FROM line_snapshots s WHERE source=? AND sport=? AND start_utc > ?
                           AND ts_utc = (SELECT max(ts_utc) FROM line_snapshots t WHERE t.source=s.source AND t.event_id=s.event_id)""",
                       [source, sport, now.replace(tzinfo=None)]).fetchall()
    return {r[3]: r for r in rows}


def _team_totals(con, source: str, sport: str = "NFL") -> dict[tuple[str, str, str], dict]:
    rows = con.execute("""SELECT home, away, description, line, price_a, price_b FROM derivative_snapshots d
                          WHERE source=? AND sport=? AND market='team_total' AND period='Game'
                          AND ts_utc = (SELECT max(ts_utc) FROM derivative_snapshots e WHERE e.source=d.source AND e.home=d.home AND e.away=d.away
                                        AND e.market=d.market AND e.period=d.period)""", [source, sport]).fetchall()
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


def _game_dict(eid, w, p, own_h, own_a, tt_wh, tt_pin) -> dict:
    """Shared shape for every sport: our team points, the market's (Pinnacle when posted, else Wagerhouse) and Wagerhouse's lines."""
    _, _, _, _, away, home, start, hs, hsp, asp, _, _, tot, op, up = w
    m_spread = p[7] if p and p[7] is not None else hs
    m_total = p[12] if p and p[12] is not None else tot
    imp_h, imp_a = (m_total / 2 - m_spread / 2, m_total / 2 + m_spread / 2) if m_total is not None else (None, None)
    g = {"event_id": eid, "home": home, "away": away, "kick": start.replace(tzinfo=timezone.utc),
         "own_home": own_h, "own_away": own_a, "own_margin": own_h - own_a, "own_total": own_h + own_a,
         "mkt_home": imp_h, "mkt_away": imp_a, "mkt_margin": -m_spread, "mkt_total": m_total,      # totals None until a total is posted
         "wh_spread": hs, "wh_home_price": hsp, "wh_away_price": asp, "wh_total": tot, "wh_over": op, "wh_under": up}
    for who in ("home", "away"):
        t = tt_wh.get((home, away, who))
        if t and t["line"] is not None:
            g[f"wh_tt_{who}"] = t
            tp = tt_pin.get((home, away, who))
            g[f"mkt_tt_{who}"] = tp["line"] if tp and tp["line"] is not None else None
    return g


def market_implied(w, p, fallback_total: float | None = None) -> tuple[float, float | None, float, float] | None:
    """(home spread, total, home implied, away implied) from Pinnacle when posted, else Wagerhouse. With no total posted anywhere, the implied
    points use `fallback_total` (a league-typical total): they only label the script, they are not a feature of the points model."""
    hs = w[7]
    if hs is None:
        return None
    m_spread = p[7] if p and p[7] is not None else hs
    m_total = p[12] if p and p[12] is not None else w[12]
    t = m_total if m_total is not None else fallback_total
    if t is None:
        return None
    return m_spread, m_total, t / 2 - m_spread / 2, t / 2 + m_spread / 2


def live_games(con, now: datetime, sport: str = "NFL") -> tuple[list[dict], list[str]]:
    if sport == "NBA":
        return _live_nba(con, now)
    if sport == "College":
        return _live_college(con, now)
    return _live_nfl(con, now)


def _live_nba(con, now: datetime) -> tuple[list[dict], list[str]]:
    from zoneinfo import ZoneInfo
    from engine.models import nba_script
    from engine.models.nba_props import NAME_TO_ABBR
    problems, state = [], {}
    rows = nba_script.build(state=state)
    model = nba_script.fit_live(rows)
    from engine.models.script import predict
    season = max(r["season"] for r in rows)
    wh, pin = _latest(con, snap.WH, now, "NBA"), _latest(con, snap.SHARP, now, "NBA")
    tt_wh, tt_pin = _team_totals(con, "Wagerhouse", "NBA"), _team_totals(con, "Pinnacle", "NBA")
    east = ZoneInfo("America/New_York")
    games = []
    for eid, w in wh.items():
        away, home, start = w[4], w[5], w[6]
        ha, aa = NAME_TO_ABBR.get(home), NAME_TO_ABBR.get(away)
        mi = market_implied(w, pin.get(eid), 228.0)
        if not ha or not aa or mi is None:
            problems.append(f"playbook NBA: skipped {away} at {home} (team name or line missing)")
            continue
        day = start.replace(tzinfo=timezone.utc).astimezone(east).date()
        own = {}
        for team, opp, is_home, imp in ((ha, aa, 1, mi[2]), (aa, ha, 0, mi[3])):
            v = nba_script.vector(nba_script.live_row(state, season, team, opp, is_home, imp, day))
            own[is_home] = predict(model, v) if v else None
        if None in own.values():
            problems.append(f"playbook NBA: no form for {away} at {home}")
            continue
        games.append(_game_dict(eid, w, pin.get(eid), own[1], own[0], tt_wh, tt_pin))
    return games, problems


def _live_college(con, now: datetime) -> tuple[list[dict], list[str]]:
    from engine.models import college_script
    from engine.models.script import predict
    problems, state = [], {}
    rows = college_script.build(state=state)
    model = college_script.fit_live(rows)
    season = max(r["season"] for r in rows)
    names = college_script.event_teams()
    wh, pin = _latest(con, snap.WH, now, "College"), _latest(con, snap.SHARP, now, "College")
    tt_wh, tt_pin = _team_totals(con, "Wagerhouse", "College"), _team_totals(con, "Pinnacle", "College")
    games = []
    for eid, w in wh.items():
        teams = names.get(str(eid))
        mi = market_implied(w, pin.get(eid), 52.0)
        if teams is None or mi is None:
            continue        # FCS and games CollegeFootballData does not list are skipped quietly
        home_id, away_id, neutral = teams
        own = {}
        for team, opp, is_home, imp in ((home_id, away_id, 1, mi[2]), (away_id, home_id, 0, mi[3])):
            v = college_script.vector(college_script.live_row(state, season, team, opp, is_home, neutral, imp))
            own[is_home] = predict(model, v) if v else None
        if None in own.values():
            problems.append(f"playbook College: no form for {w[4]} at {w[5]}")
            continue
        games.append(_game_dict(eid, w, pin.get(eid), own[1], own[0], tt_wh, tt_pin))
    return games, problems


def _live_nfl(con, now: datetime) -> tuple[list[dict], list[str]]:
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


def period_key(st: dict, kick: datetime, cfg: dict) -> str:
    """NFL and college: the Tuesday-to-Monday week. NBA: the Mountain-time date."""
    if st.get("period") == "day":
        return kick.astimezone(config.display_tz(cfg)).date().isoformat()
    return nfl_week(kick)


def run(cfg: dict, env: dict, con, now: datetime, send: bool = True, props_ctx: tuple | None = None, sport: str = "NFL") -> tuple[list[str], str]:
    """Price, grade, freeze and alert for one sport. Returns (log lines, card text). Never raises into the read."""
    st = settings(cfg, sport)
    if not st["enabled"]:
        return [], ""
    out = []
    try:
        con.execute(SCHEMA)
        from engine import stale, version
        lands = stale.landings(sport, cfg)
        games, problems = live_games(con, now, sport)
        out += problems
        checks = load_checks(now, cfg, sport)
        graded = grade_all(candidates(games, st, lands), st, checks=checks)
        if st["full_game"] == "show":
            for c in graded:
                if c["grade"] in ("A", "B"):
                    c["grade"], c["note"] = "C", (c.get("note", "") + " " if c.get("note") else "") + \
                        f"Shown only: {sport} full-game picks are not staked (its walk-forward test lost; config playbook.sports.{sport}.full_game)."
        shifts = None
        if props_ctx and st["props"] and sport in (st.get("calibrate_props") or []):
            from engine.models import calibrate
            shifts = calibrate.fit(con, sport)
        props_graded = grade_props(prop_candidates(games, props_ctx[0], props_ctx[1], st, sport, shifts), st, checks) \
            if (props_ctx and st["props"]) else []
        for c in graded + props_graded:                     # never into a move (research 18, item 4)
            if c["grade"] in ("A", "B"):
                moved = moved_against(con, c, sport, st)
                if moved:
                    c["grade"], c["note"] = "C", (c.get("note", "") + " " if c.get("note") else "") + moved
        log_candidates(con, sport, graded + props_graded, now)
        down = down_units(con, sport)
        rv = version.stamp(cfg, con)
        unit = config.unit_for(cfg, sport)
        tz = config.display_tz(cfg)
        for c in graded:
            if c["grade"] not in ("A", "B"):
                continue
            key = f"{c['event_id']}|{c['market']}|{c['side']}"
            if con.execute("SELECT 1 FROM playbook_picks WHERE event_id=? AND market <> 'prop'", [c["event_id"]]).fetchone():
                continue        # one full-game position per game, frozen at first qualification
            per = period_key(st, c["kick"], cfg)
            if con.execute("SELECT count(*) FROM playbook_picks WHERE sport=? AND market <> 'prop' AND nfl_week=?",
                           [sport, per]).fetchone()[0] >= st["max_per_period"]:
                out.append(f"playbook {sport}: cap reached ({st['max_per_period']} per {st['period']}); not issued: {c['pick']}")
                continue
            units, dollars, note = stake(st, c["grade"], now, down, unit)
            units, dollars, note, nominal = _paper_or_staked(con, st, c, units, dollars, note, unit, full_game=True, now=now, cfg=cfg)
            _, lim = c["land"].limit(c["our_line"], c["line"], c["side"] if c["market"] != "team_total" else c["tt_side"], c["price"],
                                     st["min_edge"][c["market"]] / 2)
            dbp = None if lim is None else _show(c, lim)
            _insert_pick(con, [key, now.replace(tzinfo=None), sport, c["event_id"], c["game"], c["market"], c["side"], c["pick"], c["line"], c["price"],
                               c["grade"], c["edge"], c["our_line"], c["market_line"], c["own_line"], units, dollars, dbp,
                               c["kick"].astimezone(timezone.utc).replace(tzinfo=None), per, why(c), rv, nominal, c.get("price_edge")])
            head = f"PLAYBOOK BET ({c['grade']})" if dollars > 0 else f"PLAYBOOK PAPER PICK ({c['grade']}), DO NOT BET"
            msg = (f"{sport} · {head}\n{c['pick']} ({int(c['price']):+d})\n{c['game']}, {c['kick'].astimezone(tz):%a %-I:%M %p} MT\n"
                   f"Stake: ${dollars:g} ({note})\nDon't bet past {dbp or 'this number'}.\n{edge_split(c)}\nWhy: {why(c)}" + (f"\n{c['note']}" if c.get("note") else ""))
            out.append(msg)
            _send_and_save(con, env, msg, st["lane"], key, now, send and dollars > 0)
        out += _issue_props(con, cfg, env, props_graded, st, now, down, unit, rv, tz, send)
        return out, card(con, cfg, graded, st, now, props_graded if st["props"] else None)
    except Exception as e:
        return out + [f"playbook {sport} failed: {type(e).__name__}: {e}"], ""


def log_candidates(con, sport: str, cands: list[dict], now: datetime) -> int:
    """Freeze every graded candidate (A, B and C) the first time it is seen, with our handicap's own number and the market's, so weights can be
    re-fitted on everything the model priced, not only on the picks it issued (PLAYBOOK step 4). One row per market and side per game.
    own_value / market_value: home margin (sides), total (totals), team points (team totals), chance over (props)."""
    n = 0
    for c in cands:
        if c["market"] == "prop":
            key, own, mkt = f"{sport}|{prop_key(c)}", c["own_line"], c["market_line"]
            side = c["side"]
        else:
            key = f"{sport}|{key_of(c)}"
            side = c["side"]
            own, mkt = (-c["own_line"], -c["market_line"]) if c["market"] == "side" else (c["own_line"], c["market_line"])
        if con.execute("SELECT 1 FROM playbook_candidates WHERE cand_key=?", [key]).fetchone():
            continue
        con.execute("INSERT INTO playbook_candidates VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [key, now.replace(tzinfo=None), sport, c["event_id"], c["market"], side, c["line"], c["price"], c["grade"], c["edge"],
                     own, mkt, c["kick"].astimezone(timezone.utc).replace(tzinfo=None), c["game"], None, None])
        n += 1
    return n


def grade_candidates(con, scorer=None) -> int:
    """Fill the real outcome for finished candidates: home margin, total, team points, or 1/0 for a prop going over."""
    from engine.picks import grade as g
    scorer = scorer or g.final_score
    con.execute(SCHEMA)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    todo = con.execute("SELECT cand_key, sport, event_id, market, side, line, game FROM playbook_candidates WHERE outcome IS NULL AND kickoff_utc < ?",
                       [now - timedelta(hours=4)]).fetchall()
    scores, n = {}, 0
    has_props = con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='prop_evals'").fetchone()[0]
    for key, sport, eid, market, side, line, game in todo:
        if market == "prop":
            if not has_props:
                continue
            parts = key.split("|")
            away, home = game.split(" at ", 1)
            row = con.execute("SELECT outcome FROM prop_evals WHERE sport=? AND player_id=? AND stat=? AND away=? AND home=? AND outcome IS NOT NULL LIMIT 1",
                              [sport, parts[2], parts[3], away, home]).fetchone()
            if row is None or row[0] == line:
                continue
            val = 1.0 if row[0] > line else 0.0
        else:
            if (sport, eid) not in scores:
                try:
                    scores[(sport, eid)] = scorer(sport, eid)
                except Exception:
                    scores[(sport, eid)] = None
            sc = scores[(sport, eid)]
            if sc is None:
                continue
            hs, as_ = sc
            val = (hs - as_) if market == "side" else (hs + as_) if market == "total" else (hs if side.startswith("home") else as_)
        con.execute("UPDATE playbook_candidates SET outcome=?, graded_utc=? WHERE cand_key=?", [float(val), now, key])
        n += 1
    return n


def refit(con, cfg: dict, min_n: int = 40) -> list[dict]:
    """Re-fit the weight on our number per sport and market from graded candidates (PLAYBOOK step 4): the least-squares w in
    outcome ~ market + w (ours - market). Reported with the current weight; changed only by a session, with a decision note, once `ready`."""
    from engine.models.script import fit_weight
    con.execute(SCHEMA)
    out = []
    for sport, market in con.execute("SELECT DISTINCT sport, market FROM playbook_candidates WHERE outcome IS NOT NULL ORDER BY 1, 2").fetchall():
        raw = con.execute("""SELECT cand_key, event_id, side, own_value, market_value, outcome FROM playbook_candidates WHERE sport=? AND market=?
                             AND outcome IS NOT NULL AND own_value IS NOT NULL AND market_value IS NOT NULL ORDER BY first_seen_utc""", [sport, market]).fetchall()
        seen, rows = set(), []
        for key, eid, side, own, mkt, outcome in raw:      # both sides of one market carry the same numbers: count it once
            ent = "|".join(key.split("|")[2:5]) if market == "prop" else side.split("_")[0] if market == "team_total" else ""
            if (eid, ent) in seen:
                continue
            seen.add((eid, ent))
            rows.append((own, mkt, outcome))
        w = fit_weight([r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows]) if rows else None
        cur = settings(cfg, sport)["weights"].get(market if market != "prop" else "prop")
        out.append({"sport": sport, "market": market, "n": len(rows), "fitted": None if w is None else round(w, 3), "current": cur,
                    "ready": len(rows) >= min_n})
    return out


def record_markdown(con, cfg: dict) -> str:
    rows = by_principle(con)
    out = ["# Playbook record by principle (generated by `engine playbook-record`; do not edit)", "",
           "Each principle is a sport and market. Results are staked picks; the weight re-fit uses every candidate the model priced (A, B and C), "
           "so it is not biased toward the picks that happened to be issued. A weight is changed only after 40 graded candidates, by a session, "
           "with a decision note (PLAYBOOK step 4).", "",
           "Units are at the grade's size, paper picks included (decision 0025). Closing-line value: sides and totals, win chance gained on the line; "
           "props and team totals, Pinnacle's no-vig closing chance of the bet minus the chance its price needed (above 0 = beat the close after the margin).", "",
           "| Sport | Market | Graded picks | W-L | Units | Closing-line value (win chance) |", "|---|---|---|---|---|---|"]
    for sport, market, n, w, l, units, clv, cn in rows:
        out.append(f"| {sport} | {market} | {n} | {w}-{l} | {units:+.2f} | {'n/a' if clv is None else f'{100 * clv:+.1f}% on {cn}'} |")
    if not rows:
        out.append("| none graded yet | | | | | |")
    out += ["", "## Weight re-fit from graded candidates", "", "| Sport | Market | Graded candidates | Fitted weight | Current weight | Enough to apply (40+) |",
            "|---|---|---|---|---|---|"]
    rf = refit(con, cfg)
    for r in rf:
        out.append(f"| {r['sport']} | {r['market']} | {r['n']} | {r['fitted'] if r['fitted'] is not None else 'n/a'} | {r['current']} | {'yes' if r['ready'] else 'no'} |")
    if not rf:
        out.append("| none graded yet | | | | | |")
    return "\n".join(out) + "\n"


def _issue_props(con, cfg, env, props_graded, st, now, down, unit, rv, tz, send) -> list[str]:
    out, sport = [], st["sport"]
    for c in props_graded:
        if c["grade"] not in ("A", "B"):
            continue
        key = prop_key(c)
        if con.execute("SELECT 1 FROM playbook_picks WHERE pick_key LIKE ?", [f"prop|{c['player_id']}|{c['stat']}|%|{c['event_id']}"]).fetchone():
            continue
        if con.execute("SELECT count(*) FROM playbook_picks WHERE market='prop' AND event_id=?", [c["event_id"]]).fetchone()[0] >= st["props_per_game"]:
            continue
        per = period_key(st, c["kick"], cfg)
        if con.execute("SELECT count(*) FROM playbook_picks WHERE sport=? AND market='prop' AND nfl_week=?", [sport, per]).fetchone()[0] \
                >= st["props_per_period"]:
            out.append(f"playbook {sport}: props cap reached ({st['props_per_period']} per {st['period']}); not issued: {c['pick']}")
            continue
        units, dollars, note = stake(st, c["grade"], now, down, unit)
        units, dollars, note, nominal = _paper_or_staked(con, st, c, units, dollars, note, unit, full_game=False, now=now, cfg=cfg)
        dbp = f"{c['side']} {c['line']:g} at {c['worst_price']:+d} or better" + (" (a lower line is fine)" if c["side"] == "over" else " (a higher line is fine)")
        _insert_pick(con, [key, now.replace(tzinfo=None), sport, c["event_id"], c["game"], "prop", c["side"], c["pick"], c["line"], c["price"], c["grade"],
                           c["edge"], c["our_line"], c["market_line"], c["own_line"], units, dollars, dbp,
                           c["kick"].astimezone(timezone.utc).replace(tzinfo=None), per, why(c), rv, nominal, c.get("price_edge")])
        head = f"PLAYBOOK PROP ({c['grade']})" if dollars > 0 else f"PLAYBOOK PAPER PROP ({c['grade']}), DO NOT BET"
        msg = (f"{sport} · {head}\n{c['pick']} (Pinnacle {int(c['price']):+d})\n{c['game']}, {c['kick'].astimezone(tz):%a %-I:%M %p} MT\n"
               f"Stake: ${dollars:g} ({note})\nAt Wagerhouse (Bet Builder): {dbp}.\n{edge_split(c)}\nWhy: {why(c)}" + (f"\n{c['note']}" if c.get("note") else ""))
        out.append(msg)
        _send_and_save(con, env, msg, st.get("props_lane"), key, now, send and dollars > 0 and bool(st.get("props_lane")))
    return out


def _insert_pick(con, vals: list) -> None:
    con.execute(f"INSERT INTO playbook_picks ({PICK_COLS}) VALUES ({','.join('?' * len(vals))})", vals)


def _paper_or_staked(con, st: dict, c: dict, units: float, dollars: float, note: str, unit: float, full_game: bool,
                     now: datetime | None = None, cfg: dict | None = None) -> tuple:
    """(units, dollars, note, nominal units). Paper when the lane is paper, the game already carries a unit, or the week's staked total would
    pass the weekly cap (decision 0027). A CHECK-cleared pick is staked like any other (decision 0027; it was paper under 0025)."""
    nominal = units if units else st["units"].get(c["grade"], 0.0)       # the grade's size, also when the stop-loss made it paper
    staked_lane = (st["full_game"] == "stake") if full_game else bool(st.get("props_stake", True))
    why_paper = None
    if not staked_lane:
        why_paper = f"paper: this lane is not staked (decision 0025; config playbook.sports.{st['sport']})"
    elif dollars > 0:
        on_game = game_exposure(con, c["event_id"])
        if on_game + dollars > st["game_cap_units"] * unit + 1e-9:
            why_paper = f"paper: ${on_game:g} is already on this game; the cap is one unit (${st['game_cap_units'] * unit:g}) a game"
        elif now is not None:
            why_paper = over_weekly_cap(con, cfg or {}, dollars, now)
    if why_paper:
        return 0.0, 0.0, why_paper, nominal
    return units, dollars, note, nominal


def game_exposure(con, event_id: str) -> float:
    """Dollars already staked on one game: playbook picks plus teaser tickets with a leg in it (the whole ticket counts against each game)."""
    try:
        pb = con.execute("SELECT coalesce(sum(dollars), 0) FROM playbook_picks WHERE event_id = ?", [event_id]).fetchone()[0]
    except Exception:
        pb = 0.0
    try:
        tz = con.execute("""SELECT coalesce(sum(t.dollars), 0) FROM teaser_tickets t
                            WHERE t.leg_a IN (SELECT leg_key FROM teaser_legs WHERE event_id = ?)
                               OR t.leg_b IN (SELECT leg_key FROM teaser_legs WHERE event_id = ?)""", [event_id, event_id]).fetchone()[0]
    except Exception:
        tz = 0.0
    return float(pb) + float(tz)


def week_start_utc(cfg: dict, now: datetime) -> datetime:
    """Monday 00:00 Mountain of the current week, in UTC (naive), for the weekly cap."""
    local = now.astimezone(config.display_tz(cfg))
    start = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(timezone.utc).replace(tzinfo=None)


def week_staked(con, cfg: dict, now: datetime) -> float:
    """Dollars recommended on Telegram this week (Monday to Sunday Mountain): staked playbook picks plus teaser tickets."""
    since = week_start_utc(cfg, now)
    total = 0.0
    for sql in ("SELECT coalesce(sum(dollars), 0) FROM playbook_picks WHERE first_seen_utc >= ?",
                "SELECT coalesce(sum(dollars), 0) FROM teaser_tickets WHERE sent_utc >= ?"):
        try:
            total += float(con.execute(sql, [since]).fetchone()[0])
        except Exception:
            pass
    return total


def over_weekly_cap(con, cfg: dict, dollars: float, now: datetime) -> str | None:
    """A paper note if staking `dollars` now would take this week past `playbook.weekly_cap_dollars` (decision 0027), else None."""
    cap = (cfg.get("playbook") or {}).get("weekly_cap_dollars", DEFAULTS["weekly_cap_dollars"])
    if not cap:
        return None
    have = week_staked(con, cfg, now)
    if have + dollars > float(cap) + 1e-9:
        return f"paper: ${have:g} is already recommended this week; the weekly cap is ${float(cap):g} (decision 0027)"
    return None


def teaser_profit_units(con) -> float:
    """Profit in NFL units of every graded teaser ticket that carried money (both legs graded; a push on a leg = no action on the ticket)."""
    try:
        rows = con.execute("""SELECT t.units, t.price, ga.result, gb.result FROM teaser_tickets t
                              JOIN teaser_grades ga ON ga.leg_key = t.leg_a JOIN teaser_grades gb ON gb.leg_key = t.leg_b
                              WHERE t.units > 0""").fetchall()
    except Exception:
        return 0.0
    out = 0.0
    for units, price, ra, rb in rows:
        if "L" in (ra, rb):
            out -= units
        elif "P" not in (ra, rb):
            out += units * (100 / abs(price) if price < 0 else price / 100)
    return out


def down_units(con, sport: str) -> float:
    """Staked profit in this sport's units for the stop. NFL counts teaser tickets too (decision 0027)."""
    try:
        pb = float(con.execute("SELECT coalesce(sum(g.profit_units), 0) FROM playbook_grades g JOIN playbook_picks p USING (pick_key) "
                               "WHERE p.sport = ? AND p.units > 0", [sport]).fetchone()[0])
    except Exception:
        pb = 0.0
    return pb + (teaser_profit_units(con) if sport == "NFL" else 0.0)


def edge_split(c: dict) -> str:
    """One line: how much of the edge is Wagerhouse's price against the market, and how much is our handicap (research 19)."""
    pe = c.get("price_edge")
    if pe is None:
        return f"Edge {100 * c['edge']:+.1f}%."
    ref = "Pinnacle's price" if c["market"] == "prop" else "the market's number"
    return (f"Edge {100 * c['edge']:+.1f}%: {100 * pe:+.1f}% from the price alone (Wagerhouse against {ref}), "
            f"{100 * (c['edge'] - pe):+.1f}% from our handicap.")


def _send_and_save(con, env: dict, msg: str, lane: str | None, key: str, now: datetime, send: bool) -> None:
    """Send when asked, and always keep the text in alerts_sent (research 18: sent picks were not saved anywhere)."""
    delivered = False
    if send:
        from engine.alerts import telegram
        delivered = telegram.send(env, msg, lane, kind="bet")
    try:
        con.execute("CREATE TABLE IF NOT EXISTS alerts_sent (key VARCHAR PRIMARY KEY, ts_utc TIMESTAMP, kind VARCHAR, text VARCHAR, delivered BOOLEAN)")
        con.execute("INSERT INTO alerts_sent VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING",
                    [f"playbook|{key}", now.replace(tzinfo=None), "bet" if send else "paper", msg, bool(delivered)])
    except Exception:
        pass


def moved_against(con, c: dict, sport: str, st: dict) -> str | None:
    """A note if Pinnacle has moved against this side since it was first priced, else None (research 18, item 4)."""
    try:
        if c["market"] in ("side", "total"):
            col = "home_spread" if c["market"] == "side" else "total"
            rows = con.execute(f"SELECT {col} FROM line_snapshots WHERE event_id = ? AND source = ? AND {col} IS NOT NULL ORDER BY ts_utc",
                               [c["event_id"], snap.SHARP]).fetchall()
            if len(rows) < 2:
                return None
            first, last = rows[0][0], rows[-1][0]
            # home spread up = worse for home; total down = worse for the over
            against = (last - first) if c["side"] == "home" else (first - last) if c["side"] == "away" else \
                (first - last) if c["side"] == "over" else (last - first)
            if against >= st["move_points"]:
                return f"Not issued: Pinnacle moved {against:g} against this side since we first priced it ({first:g} to {last:g})."
            return None
        if c["market"] == "team_total":
            who, ou = c["side"].split("_")
            rows = con.execute("""SELECT line FROM derivative_snapshots WHERE source = 'Pinnacle' AND sport = ? AND home = ? AND away = ?
                                  AND market = 'team_total' AND period = 'Game' AND description = ? AND line IS NOT NULL ORDER BY ts_utc""",
                               [sport, c["home"], c["away"], who]).fetchall()
            if len(rows) < 2:
                return None
            first, last = rows[0][0], rows[-1][0]
            against = (first - last) if ou == "over" else (last - first)
            if against >= st["move_points"]:
                return f"Not issued: Pinnacle's team total moved {against:g} against this side ({first:g} to {last:g})."
            return None
        if c["market"] == "prop":
            rows = con.execute("""SELECT line, market_p_over FROM prop_evals WHERE coalesce(sport, 'NFL') = ? AND player_id = ? AND stat = ?
                                  AND home = ? AND away = ? AND market_p_over IS NOT NULL ORDER BY ts_utc""",
                               [sport, c["player_id"], c["stat"], c.get("home_name", c["home"]), c.get("away_name", c["away"])]).fetchall()
            if len(rows) < 2:
                return None
            (l0, p0), (l1, p1) = rows[0], rows[-1]
            if l0 != l1:
                worse = (l1 > l0) if c["side"] == "over" else (l1 < l0)
                return f"Not issued: Pinnacle moved the line against this side ({l0:g} to {l1:g})." if worse else None
            drop = (p0 - p1) if c["side"] == "over" else (p1 - p0)
            if drop >= st["move_chance"]:
                return f"Not issued: Pinnacle moved {100 * drop:.0f} points of chance against this side since we first priced it."
            return None
    except Exception:
        return None
    return None


def _show(c: dict, lim: float) -> str:
    if c["market"] == "side":
        team = c["home"] if c["side"] == "home" else c["away"]
        return f"{team} {(lim if c['side'] == 'home' else -lim):+g}"
    if c["market"] == "total":
        return f"{c['side'].title()} {lim:g}"
    return f"{c['pick'].rsplit(' ', 1)[0]} {lim:g}"


def card(con, cfg: dict, graded: list[dict], st: dict, now: datetime, props_graded: list[dict] | None = None) -> str:
    sport = st["sport"]
    tz = config.display_tz(cfg)
    issued = con.execute("SELECT pick, game, grade, price, dollars, dont_bet_past, kickoff_utc, why FROM playbook_picks WHERE sport=? AND kickoff_utc > ? "
                         "ORDER BY kickoff_utc", [sport, now.replace(tzinfo=None)]).fetchall()
    w = st["weights"]
    staked = {"stake": "staked", "paper": "paper (issued and graded, not staked; decision 0025)"}.get(
        st["full_game"], "shown only, not staked (its walk-forward test lost; Kylor can switch it on)")
    props_mode = "off" if not (st["props"] and props_graded is not None) else ("staked" if st.get("props_stake", True) else "paper (issued and graded, not staked; decision 0025)")
    out = [f"# {sport} playbook picks", "",
           f"How these are made: PLAYBOOK.md. Our team points come from the {sport} game-script model; our number is pulled toward the market at the "
           f"playbook's starting weights (side {w['side']}, game total {w['total']}, team total {w['team_total']}, props {w['prop']}). Full-game picks: {staked}. "
           f"Props: {props_mode}. Units: ${config.unit_for(cfg, sport):g}; A = 1 unit, B = half a unit; a $0 stake is a paper pick: do not bet it. "
           f"At most one unit a game across picks and teaser legs; a pick Pinnacle has moved against since we first priced it is not issued.", "",
           f"**Record:** {record(con, sport)}", "", "## Issued (frozen at the number shown; $0 = paper)", ""]
    if issued:
        out += ["| Pick | Game | Grade | Stake | Don't bet past | Start (MT) | Why |", "|---|---|---|---|---|---|---|"]
        for pick, game, grade, price, dollars, dbp, kick, wy in issued:
            out.append(f"| {pick} ({int(price):+d}) | {game} | {grade} | {'$' + format(dollars, 'g') if dollars else 'paper'} | {dbp or ''} | "
                       f"{kick.replace(tzinfo=timezone.utc).astimezone(tz):%a %-I:%M %p} | {wy} |")
    else:
        out.append("None open.")
    rest = [c for c in graded if c["grade"] == "C"][: st["show_c"]]
    out += ["", "## Best of the rest (C: shown, not staked)", "",
            f"CHECK rows clear the edge but our number is far from the market. The research agent writes a verdict for each one in "
            f"`docs/cards/decisions/<date>-{sport.lower()}-checks.yaml` (`key`, `verdict: clear` or `hold`, `why`, `source`; a clear also needs `because`, a positive "
            f"reason the market is wrong, and `market_assumes`, what the current number already prices); a cleared one is issued and staked like any other B pick on the next read (decision 0027).", ""]
    if rest:
        out += ["| Pick | Game | Edge | Our number / market / our handicap alone | Note | Key |", "|---|---|---|---|---|---|"]
        for c in rest:
            out.append(f"| {c['pick']} ({int(c['price']):+d}) | {c['game']} | {100 * c['edge']:+.1f}% | {c['our_line']:.1f} / {c['market_line']:.1f} / {c['own_line']:.1f} | "
                       f"{c['note'] or 'under the minimum edge'} | `{key_of(c)}` |")
    else:
        out.append("None.")
    if props_graded is not None:
        prest = [c for c in props_graded if c["grade"] == "C"][: st["show_c"] * 2]
        out += ["", "## Props: best of the rest (C: shown, not staked)", ""]
        if prest:
            out += ["| Prop | Game | Edge | Why | Note | Key |", "|---|---|---|---|---|---|"]
            for c in prest:
                out.append(f"| {c['pick']} (Pinnacle {int(c['price']):+d}) | {c['game']} | {100 * c['edge']:+.1f}% | {c['model_note']} | "
                           f"{c['note'] or 'under the minimum edge'} | `{prop_key(c)}` |")
        else:
            out.append("None (props are priced on each hourly read).")
    return "\n".join(out) + "\n"


def record(con, sport: str | None = None) -> str:
    con.execute(SCHEMA)
    where, args = ("WHERE p.sport=?", [sport]) if sport else ("", [])
    w, l, p_, units, clv, n, nom = con.execute(
        "SELECT count(*) FILTER (result='W'), count(*) FILTER (result='L'), count(*) FILTER (result='P'), coalesce(sum(profit_units),0), "
        f"avg(clv_chance), count(*), coalesce(sum(coalesce(nominal_profit, profit_units)), 0) FROM playbook_grades g JOIN playbook_picks p USING (pick_key) {where}",
        args).fetchone()
    open_n = con.execute(f"SELECT count(*) FROM playbook_picks p {where} {'AND' if where else 'WHERE'} pick_key NOT IN (SELECT pick_key FROM playbook_grades)",
                         args).fetchone()[0]
    if not n:
        return f"no graded picks yet; {open_n} open."
    c = "closing-line value n/a" if clv is None else f"closing-line value {100 * clv:+.1f}% win chance"
    return f"{w}-{l}-{p_}, {nom:+.2f} units at the grade's size ({units:+.2f} staked), {c}; {open_n} open."


def lane_record(con, sport: str, props: bool) -> str:
    """Staked record for one lane (full-game or props) of one sport: what Telegram sent and how it did (decision 0027, lane table)."""
    try:
        con.execute(SCHEMA)
        cond = "p.market = 'prop'" if props else "p.market <> 'prop'"
        sent = con.execute(f"SELECT count(*), max(first_seen_utc) FROM playbook_picks p WHERE p.sport=? AND p.units > 0 AND {cond}", [sport]).fetchone()
        w, l, pu, units, clv, cn = con.execute(
            "SELECT count(*) FILTER (result='W'), count(*) FILTER (result='L'), count(*) FILTER (result='P'), coalesce(sum(profit_units), 0), "
            f"avg(clv_chance), count(clv_chance) FROM playbook_grades g JOIN playbook_picks p USING (pick_key) WHERE p.sport=? AND p.units > 0 AND {cond}",
            [sport]).fetchone()
    except Exception as e:
        return f"Playbook record unavailable ({type(e).__name__})."
    c = "closing-line value n/a" if not cn else f"closing-line value {100 * clv:+.1f}% on {cn}"
    return f"Staked picks sent: {sent[0]}; graded {w}-{l}-{pu}, {units:+.2f} units, {c}."


def lane_events(con, cfg: dict) -> list[tuple[str, str]]:
    """(alert key, text) for each stop that has tripped and each staked lane below its review line (decision 0027). The key is stable, so
    each event reaches Telegram once."""
    out = []
    pc = cfg.get("playbook") or {}
    gl = cfg.get("go_live") or {}
    n_min, floor = int(gl.get("pause_n", 25)), float(gl.get("pause_clv", -0.015))
    for sport in (pc.get("sports") or SPORT_DEFAULTS):
        st = settings(cfg, sport)
        down = down_units(con, sport)
        if down <= -abs(st["stop_loss_units"]):
            out.append((f"stop|{sport}|{st['live_since']}",
                        f"STOP TRIPPED (not a bet): {sport} staked picks{' and teasers' if sport == 'NFL' else ''} are down {down:.1f} units "
                        f"(stop at {st['stop_loss_units']:g}). New {sport} picks are paper until Kylor restarts them. A pause for review, not a verdict."))
        for props in (False, True):
            try:
                cond = "p.market = 'prop'" if props else "p.market <> 'prop'"
                clv, cn = con.execute(f"SELECT avg(clv_chance), count(clv_chance) FROM playbook_grades g JOIN playbook_picks p USING (pick_key) "
                                      f"WHERE p.sport=? AND p.units > 0 AND {cond}", [sport]).fetchone()
            except Exception:
                continue
            if cn and cn >= n_min and clv is not None and clv < floor:
                what = "props" if props else "full-game picks"
                out.append((f"review|{sport}|{what}|{st['live_since']}",
                            f"REVIEW (not a bet): {sport} {what} average {100 * clv:+.1f}% closing-line value on {cn} staked picks, below the "
                            f"{100 * floor:+.1f}% review line. Still staked; a session should look at this lane (docs/lanes/PLAYBOOK-RECORD.md)."))
    return out


def by_principle(con) -> list[tuple]:
    """Per-principle record (sport and market), PLAYBOOK step 4: the evidence for re-fitting weights every 4 weeks."""
    con.execute(SCHEMA)
    return con.execute("""SELECT p.sport, p.market, count(*), count(*) FILTER (result='W'), count(*) FILTER (result='L'),
                                 coalesce(sum(coalesce(nominal_profit, profit_units)), 0), avg(clv_chance), count(clv_chance)
                          FROM playbook_grades g JOIN playbook_picks p USING (pick_key) GROUP BY 1, 2 ORDER BY 1, 2""").fetchall()


def grade(con, cfg: dict, scorer=None) -> list[str]:
    """Result for every finished pick, staked or paper (paper results are kept at the grade's size in `nominal_profit`), and the closing-line
    value against Pinnacle's last read before the start. Sides and totals: points and win chance on the line (clv.py). Team totals and props
    (research 18, item 6): `clv_chance` = Pinnacle's no-vig chance of our exact bet at the close minus the chance our price needed, so a
    positive number means we beat the closing price after the margin; `clv_points` = how far the closing line moved our way."""
    from engine import clv as clv_mod
    from engine.picks import grade as g
    scorer = scorer or g.final_score
    con.execute(SCHEMA)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    has_props = con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='prop_evals'").fetchone()[0]
    out = []
    for key, sport, eid, market, side, line, price, units, kick, game, nominal in con.execute(
            "SELECT pick_key, sport, event_id, market, side, line, price, units, kickoff_utc, game, coalesce(nominal_units, units) FROM playbook_picks "
            "WHERE kickoff_utc <= ? AND pick_key NOT IN (SELECT pick_key FROM playbook_grades)", [now]).fetchall():
        if market == "prop":
            if not has_props:
                continue
            _, pid, stat, side_, _, _ = key.split("|")
            away, home = game.split(" at ", 1)
            row = con.execute("SELECT outcome FROM prop_evals WHERE sport=? AND player_id=? AND stat=? AND away=? AND home=? AND outcome IS NOT NULL LIMIT 1",
                              [sport, pid, stat, away, home]).fetchone()
            if row is None:
                continue
            v = (row[0] - line) if side_ == "over" else (line - row[0])
            res = "W" if v > 0 else "L" if v < 0 else "P"
            close, cp, cc = prop_close(con, sport, pid, stat, home, away, side_, line, price, kick)
            hs = as_ = None
        else:
            score = scorer(sport, eid)
            if score is None:
                continue
            hs, as_ = score
            if market == "team_total":
                who, ou = side.split("_")
                pts = hs if who == "home" else as_
                v = (pts - line) if ou == "over" else (line - pts)
                res = "W" if v > 0 else "L" if v < 0 else "P"
                home, away = game.split(" at ", 1)[1], game.split(" at ", 1)[0]
                close, cp, cc = team_total_close(con, cfg, sport, home, away, who, ou, line, price, kick)
            else:
                mk = "spread" if market == "side" else "total"
                res = g.result(mk, side, line, hs, as_)
                col = "home_spread" if market == "side" else "total"
                row = con.execute(f"SELECT {col} FROM line_snapshots WHERE event_id=? AND source=? AND ts_utc<=? AND {col} IS NOT NULL "
                                  "ORDER BY ts_utc DESC LIMIT 1", [eid, snap.SHARP, kick]).fetchone()
                close = None if row is None else row[0]
                cp = None if close is None else g.clv_points(mk, side, line, close)
                cc = None if close is None else clv_mod.chance(cfg, sport, mk, side, line, close)
        prof = g.profit(units, price, res) if units else 0.0
        nprof = g.profit(nominal, price, res) if nominal else 0.0
        con.execute(f"INSERT INTO playbook_grades ({GRADE_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?)", [key, hs, as_, res, prof, close, cp, cc, now, nprof])
        out.append(f"PLAYBOOK GRADED {key}: {res} ({prof:+.2f} units staked, {nprof:+.2f} at the grade's size)")
    return out


def _nv_over(po: float | None, pu: float | None) -> float | None:
    if po is None or pu is None:
        return None
    a, b = 1 / american_to_decimal(po), 1 / american_to_decimal(pu)
    return a / (a + b)


def prop_close(con, sport, pid, stat, home, away, side, line, price, kick) -> tuple:
    """(Pinnacle closing line, points our way, no-vig chance of our bet at the close minus the chance our price needed). The chance needs the
    closing line to equal ours; otherwise only the points are kept."""
    row = con.execute("""SELECT line, market_p_over FROM prop_evals WHERE coalesce(sport, 'NFL') = ? AND player_id = ? AND stat = ? AND home = ?
                         AND away = ? AND market_p_over IS NOT NULL AND ts_utc < ? ORDER BY ts_utc DESC LIMIT 1""",
                      [sport, pid, stat, home, away, kick]).fetchone()
    if row is None:
        return None, None, None
    cl, p_over = row
    pts = (cl - line) if side == "over" else (line - cl)
    if cl != line:
        return cl, pts, None
    p = p_over if side == "over" else 1 - p_over
    return cl, pts, round(p - chance_needed(price), 4)


def team_total_close(con, cfg, sport, home, away, who, ou, line, price, kick) -> tuple:
    """Same as prop_close for a team total, from Pinnacle's team-total reads; a different closing line is carried to ours on the bell curve."""
    row = con.execute("""SELECT line, price_a, price_b FROM derivative_snapshots WHERE source = 'Pinnacle' AND sport = ? AND home = ? AND away = ?
                         AND market = 'team_total' AND period = 'Game' AND description = ? AND line IS NOT NULL AND ts_utc < ?
                         ORDER BY ts_utc DESC LIMIT 1""", [sport, home, away, who, kick]).fetchone()
    if row is None:
        return None, None, None
    cl, po, pu = row
    pts = (line - cl) if ou == "under" else (cl - line)
    nv = _nv_over(po, pu)
    if nv is None:
        return cl, pts, None
    land = _team_land(settings(cfg, sport))
    fair = cl + (nv - 0.5) / land.slope(cl)                  # Pinnacle's own price moves its fair number off the posted line
    win, _, lose = land.probs(fair, line, ou)
    p = win / (win + lose) if win + lose else 0.5
    return cl, pts, round(p - chance_needed(price), 4)
