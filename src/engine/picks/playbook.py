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
  5. one full-game position per game (the biggest edge; in a shown-only lane, news picks first), capped per week (NFL, college) or per
     day (NBA); props capped per game and period. A pick past a cap is issued as paper (decision 0033);
  6. stakes: A 1 unit, B 0.5 unit (no playbook principle has passed a test, so every playbook pick is B today); `half_size_weeks` is 0 (off,
     decision 0020); paper again if staked picks are down `stop_loss_units` (decision 0018);
  7. A and B picks are frozen at the Wagerhouse number the first time they qualify; staked ones are sent to Telegram (shown-lane picks become
     C unless they are news picks, paper picks are held back), and graded on the result and against
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

Decision 0033 (research 22, Kylor: "yes to all, do 1-10"):
  * a failed send is saved undelivered and `resend_undelivered` sends it again on every read until the game starts;
  * `cancel_moved` sends one CANCELLED message for a sent pick that Pinnacle's move has taken past half the minimum edge;
  * the stop counts from `live_since` (`live_since_utc`); news needs a Pinnacle read after it; the NFL script's quarterback flag is off
    while the same news is added as unpriced points (`qb_out`); picks past a cap are paper.
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
ALTER TABLE playbook_picks ADD COLUMN IF NOT EXISTS paper_reason VARCHAR;
ALTER TABLE playbook_picks ADD COLUMN IF NOT EXISTS limit_price DOUBLE;
ALTER TABLE playbook_picks ADD COLUMN IF NOT EXISTS blend_weight DOUBLE;
ALTER TABLE playbook_candidates ADD COLUMN IF NOT EXISTS last_own_value DOUBLE;
ALTER TABLE playbook_candidates ADD COLUMN IF NOT EXISTS last_market_value DOUBLE;
ALTER TABLE playbook_candidates ADD COLUMN IF NOT EXISTS last_seen_utc TIMESTAMP;
"""
# Picks made paper only because their game already carries a unit do not use up a weekly or daily cap slot (decision 0036).
COUNTS_FOR_CAP = "NOT (coalesce(dollars, 0) = 0 AND coalesce(paper_reason, '') LIKE '%already on this game%')"
PICK_COLS = ("pick_key, first_seen_utc, sport, event_id, game, market, side, pick, line, price, grade, edge, our_line, market_line, own_line, "
             "units, dollars, dont_bet_past, kickoff_utc, nfl_week, why, rule_version, nominal_units, price_edge")
GRADE_COLS = "pick_key, home_score, away_score, result, profit_units, pinnacle_close, clv_points, clv_chance, graded_utc, nominal_profit"
DEFAULTS = {"enabled": True, "weights": {"team_total": 0.4, "total": 0.35, "side": 0.25, "prop": 0.5},
            "min_edge": {"team_total": 0.03, "total": 0.03, "side": 0.03, "prop": 0.04},
            "check_points": {"team_total": 4.0, "total": 4.0, "side": 3.0, "prop": 0.15},
            "units": {"A": 1.0, "B": 0.5}, "half_size_weeks": 0, "live_since": "2026-11-24", "stop_loss_units": 10.0, "show_c": 5,
            "game_cap_units": 1.0, "move_points": 1.0, "move_chance": 0.10, "calibrate_props": ["NBA"], "props_stake": True,
            "weekly_cap_dollars": 0.0}


# team_total_sd: the spread of team points around the market's number. NBA 11.5 since decision 0036 (measured 11.46 on 2,892 team-games;
# 10.5 overstated NBA team-total edges by about 9%); NFL 9.0 and college 11.0 match their measured 9.13 and 10.98 (research 18, 24).
SPORT_DEFAULTS = {
    "NFL": {"full_game": "stake", "props": True, "period": "week", "max_per_period": 5, "props_per_period": 10, "props_per_game": 2,
            "team_total_sd": 9.0, "lane": "nfl_sides_totals", "props_lane": "nfl_props"},
    "NBA": {"full_game": "show", "props": True, "period": "day", "max_per_period": 2, "props_per_period": 4, "props_per_game": 2,
            "team_total_sd": 11.5, "check_points": {"side": 4.0, "total": 6.0, "team_total": 5.0}, "lane": "nba_sides_totals", "props_lane": "nba_props"},
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


def shown_reason(st: dict) -> str:
    """Why a lane is shown only, from config (`playbook.sports.<SPORT>.shown_reason`), so the card says what the decision says."""
    return st.get("shown_reason") or "its walk-forward test lost"


def chance_needed(price: float) -> float:
    return 1 / american_to_decimal(price)


def limit_value(st: dict, market: str, price: float) -> float:
    """The expected profit per $1 at which "don't bet past" stops: half the minimum edge in win chance, times the price's decimal
    odds, because Landing.limit walks on profit and CANCELLED tests chance edge (decision 0033 item 8: the same test; audit 24)."""
    return st["min_edge"][market] / 2 * american_to_decimal(price)


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
            our_margin = g["mkt_margin"] + w["side"] * (g["own_margin"] - g["mkt_margin"]) + g.get("adj_margin", 0.0)
            for side, price, team, show in (("home", g["wh_home_price"], g["home"], 1), ("away", g["wh_away_price"], g["away"], -1)):
                if price is None:
                    continue
                e, p = edge_of(ls, -our_margin, g["wh_spread"], side, price)
                pe = edge_of(ls, -g["mkt_margin"], g["wh_spread"], side, price)[0]
                ne = e - edge_of(ls, -(our_margin - g.get("adj_margin", 0.0)), g["wh_spread"], side, price)[0]
                out.append({**_base(g), "market": "side", "side": side, "pick": f"{team} {show * g['wh_spread']:+g}", "line": g["wh_spread"],
                            "price": price, "edge": e, "p": p, "price_edge": pe, "news_edge": ne, "our_line": -our_margin, "market_line": -g["mkt_margin"], "own_line": -g["own_margin"],
                            "check": abs(g["own_margin"] + g.get("adj_margin", 0.0) - g["mkt_margin"]) > st["check_points"]["side"], "land": ls})
        if g.get("wh_total") is not None and g.get("mkt_total") is not None and g.get("wh_over") is not None:
            our_total = g["mkt_total"] + w["total"] * (g["own_total"] - g["mkt_total"]) + g.get("adj_total", 0.0)
            for side, price in (("over", g["wh_over"]), ("under", g["wh_under"])):
                if price is None:
                    continue
                e, p = edge_of(lt, our_total, g["wh_total"], side, price)
                pe = edge_of(lt, g["mkt_total"], g["wh_total"], side, price)[0]
                ne = e - edge_of(lt, our_total - g.get("adj_total", 0.0), g["wh_total"], side, price)[0]
                out.append({**_base(g), "market": "total", "side": side, "pick": f"{side.title()} {g['wh_total']:g}", "line": g["wh_total"],
                            "price": price, "edge": e, "p": p, "price_edge": pe, "news_edge": ne, "our_line": our_total, "market_line": g["mkt_total"], "own_line": g["own_total"],
                            "check": abs(g["own_total"] + g.get("adj_total", 0.0) - g["mkt_total"]) > st["check_points"]["total"], "land": lt})
        for who in ("home", "away"):
            tt = g.get(f"wh_tt_{who}")
            if not tt or g.get(f"own_{who}") is None:
                continue
            mkt = g.get(f"mkt_tt_{who}") or tt["line"]
            if mkt is None:
                continue
            sgn = 1 if who == "home" else -1
            ours = mkt + w["team_total"] * (g[f"own_{who}"] - mkt) + sgn * g.get("adj_margin", 0.0) / 2 + g.get("adj_total", 0.0) / 2
            team = g[who]
            for side, price in (("over", tt["over"]), ("under", tt["under"])):
                if price is None:
                    continue
                e, p = edge_of(tl, ours, tt["line"], side, price)
                pe = edge_of(tl, mkt, tt["line"], side, price)[0]
                ne = e - edge_of(tl, ours - sgn * g.get("adj_margin", 0.0) / 2 - g.get("adj_total", 0.0) / 2, tt["line"], side, price)[0]
                out.append({**_base(g), "market": "team_total", "side": f"{who}_{side}", "pick": f"{team} team total {side} {tt['line']:g}",
                            "line": tt["line"], "price": price, "edge": e, "p": p, "price_edge": pe, "news_edge": ne, "our_line": ours, "market_line": mkt, "own_line": g[f"own_{who}"],
                            "check": abs(g[f"own_{who}"] + sgn * g.get("adj_margin", 0.0) / 2 + g.get("adj_total", 0.0) / 2 - mkt) > st["check_points"]["team_total"],
                            "land": tl, "tt_side": side})
    return out


def _base(g: dict) -> dict:
    return {"event_id": g["event_id"], "game": f"{g['away']} at {g['home']}", "kick": g["kick"], "home": g["home"], "away": g["away"],
            "own_home": g.get("own_home"), "own_away": g.get("own_away"), "mkt_home": g.get("mkt_home"), "mkt_away": g.get("mkt_away"),
            "news": list(g.get("news") or [])}


def is_news_pick(c: dict, st: dict) -> bool:
    """True when unpriced sourced news is what takes this pick over the minimum edge: without the news it would not clear."""
    ne = c.get("news_edge") or 0.0
    return ne > 0 and c["edge"] >= st["min_edge"][c["market"]] and c["edge"] - ne < st["min_edge"][c["market"]]


# The largest news adjustment the playbook accepts, in points (decision 0036). Above it the entry counts for nothing and the card says so:
# the agent sizes news, code owns the number, and one typed entry must not be able to make a pick by itself. NFL starter out is 2.5 to
# 2.7 (research 14); a college starter about 4, a weak passer about 5 (research 21, 22); an NBA star roughly 3 to 6 (agent guide, untested).
MAX_NEWS_POINTS = {"NFL": 3.0, "College": 5.5, "NBA": 4.0}


def apply_news(con, games: list[dict], sport: str, now: datetime) -> list[str]:
    """Sourced news from `adjustments.yaml` moves our number, but only the part Pinnacle has not moved for since the news broke
    (`slate.unpriced_part`; decision 0029). Each game gets `adj_margin` (home margin, points), `adj_total` and `news` lines. Pure apart from
    reading the file and Pinnacle's stored lines. Returns problems to log; a bad file is reported, never half-applied."""
    from engine.odds import espn
    from engine.picks import slate
    try:
        adjs = slate.load_adjustments()
    except Exception as e:
        return [f"playbook {sport}: adjustments.yaml not used ({type(e).__name__}: {e})"]
    if not adjs:
        return []
    by_game = {}
    for a in adjs:
        by_game.setdefault(espn.norm(str(a["game"])), []).append(a)
    try:
        hist = _pin_history(con, sport)
    except Exception as e:
        return [f"playbook {sport}: Pinnacle history unreadable, news not applied ({type(e).__name__})"]
    for g in games:
        mine = by_game.get(espn.norm(f"{g['away']} at {g['home']}"), [])
        rows = hist.get(g["event_id"], [])
        now_sp = rows[-1][1] if rows else None
        now_tot = rows[-1][2] if rows else None
        for a in mine:
            cap = MAX_NEWS_POINTS.get(sport)
            try:
                pts = float(a["points"])
            except (TypeError, ValueError):
                pts = None
            if pts is None or (cap is not None and abs(pts) > cap):
                g.setdefault("news", []).append(
                    f"News, {a.get('team') or a['market']} {a.get('points')} (not applied: larger than the {cap:g}-point limit for {sport}, "
                    f"decision 0036; split it or size it down with a reason): {' '.join(str(a['reason']).split())} [{a['source']}]")
                continue
            if a["market"] == "spread":
                t = espn.norm(str(a["team"]))
                if t not in (espn.norm(g["home"]), espn.norm(g["away"])):      # never skip silently (CLAUDE.md): say why it did not count
                    g.setdefault("news", []).append(
                        f"News, {a.get('team')} {float(a['points']):+g} (not applied: team matches neither {g['away']} nor {g['home']} as "
                        f"Wagerhouse names them): {' '.join(str(a['reason']).split())} [{a['source']}]")
                    continue
                sign = 1 if t == espn.norm(g["home"]) else -1
            else:
                sign = 1
            left, status = slate.unpriced_part(a, rows, now_sp, now_tot, sign)
            who = a.get("team") if a["market"] == "spread" else "total"
            g.setdefault("news", []).append(f"News, {who} {float(a['points']):+g} ({status}): {' '.join(str(a['reason']).split())} [{a['source']}]")
            if left:
                if a["market"] == "spread":
                    g["adj_margin"] = g.get("adj_margin", 0.0) + sign * left
                else:
                    g["adj_total"] = g.get("adj_total", 0.0) + left
    return []


def unmatched_news(games: list[dict]) -> list[str]:
    """adjustments.yaml entries whose `game` matches none of these games as Wagerhouse names them ("Away at Home"). Such an entry counts for
    nothing and was invisible before the final audit (research 22): it is listed so the research agent can fix the names."""
    from engine.odds import espn
    from engine.picks import slate
    names = {espn.norm(f"{g['away']} at {g['home']}") for g in games}
    try:
        adjs = slate.load_adjustments()
    except Exception:
        return []
    return [str(a["game"]) for a in adjs if espn.norm(str(a["game"])) not in names]


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


def grade_all(cands: list[dict], st: dict, passed: set[str] = frozenset(), checks: dict | None = None, mover=None) -> list[dict]:
    """Grade, keep one position per game, sort by edge. `checks` maps a pick key to the research agent's verdict on a CHECK pick.
    `mover(c)` returns a note when Pinnacle has moved against the pick; it is applied BEFORE one position per game is chosen, so a pick
    the market moved past does not hide a good pick on another market of the same game (decision 0036). Pure apart from `mover`."""
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
        if st.get("full_game") == "show" and c["grade"] in ("A", "B"):
            # decided per candidate, BEFORE one pick per game: a bigger script-only pick that cannot be staked must not hide the news
            # pick on the same game (research 22, finding 3; Kylor 2026-11-24)
            if st.get("news_picks") and is_news_pick(c, st):
                c["news_pick"] = True
                c["note"] = (c["note"] + " " if c["note"] else "") + \
                    "News pick: sourced news Pinnacle has not priced is what clears the bar (decision 0029)."
            else:
                c["grade"], c["note"] = "C", (c["note"] + " " if c["note"] else "") + \
                    f"Shown only: {st.get('sport', '')} full-game picks are not staked ({shown_reason(st)}; config playbook.sports.{st.get('sport', '')}.full_game)."
        if mover is not None and c["grade"] in ("A", "B"):
            moved = mover(c)
            if moved:
                c["grade"], c["note"] = "C", (c["note"] + " " if c["note"] else "") + moved
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
            except Exception as e:     # never skip silently (CLAUDE.md): the card says the file was unreadable (audit 24)
                out[f"_error|{p.name}"] = {"verdict": "error", "because": f"{p.name} could not be read: {type(e).__name__}: {e}"}
                continue
    return out


def checks_file_problems(checks: dict) -> list[str]:
    """Problem lines for checks files that could not be read (their clears and holds were not applied)."""
    return [v["because"] for k, v in checks.items() if k.startswith("_error|")]


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
                         ("CHECK held: " + str(v.get("why", ""))) if v else f"CHECK: the model and Pinnacle disagree by {100 * st['check_points']['prop']:.0f}+ points of chance; held until researched")
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
    news = [n for n in (c.get("news") or []) if "not applied" not in n and "priced:" not in n]
    return (f"{ours} ({mkt}). Blended at the playbook weight" + (", plus sourced news Pinnacle has not priced" if news else "") +
            f", our {c['market'].replace('_', ' ')} number is {c['our_line']:.1f} "
            f"against Wagerhouse's {c['line']:g}; win chance {100 * c['p']:.1f}% against {100 * chance_needed(c['price']):.1f}% needed." +
            ("".join(" " + n for n in news) if news else ""))


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


def _qb_entries() -> list[dict]:
    """adjustments.yaml entries saying a team's quarterback is out (an NFL spread entry of 2.5+ points naming a quarterback change)."""
    try:
        from engine.picks import slate
        out = []
        for a in slate.load_adjustments():
            if a.get("market") == "spread" and abs(float(a.get("points") or 0)) >= 2.5:
                txt = str(a.get("reason", "")).lower()
                if any(w in txt for w in ("starts", "starter", "quarterback", " qb", "out ")):
                    out.append(a)
        return out
    except Exception:
        return []


def _pin_history(con, sport: str) -> dict[str, list]:
    """Pinnacle's stored side and total per game, oldest first: {event_id: [(ts UTC, home spread, total)]}."""
    hist: dict[str, list] = {}
    for eid, ts, sp, tot in con.execute("SELECT event_id, ts_utc, home_spread, total FROM line_snapshots WHERE source = ? AND sport = ? "
                                        "ORDER BY ts_utc", [snap.SHARP, sport]).fetchall():
        hist.setdefault(eid, []).append((ts.replace(tzinfo=timezone.utc), sp, tot))
    return hist


def qb_out(entries: list[dict], rows: list, home: str, away: str, team: str) -> bool:
    """The game script's backup-quarterback flag for `team`. On when an entry says its quarterback is out AND the news adds nothing to our
    number by itself (Pinnacle has priced it, or it cannot be counted). Off while the news is being added as unpriced points, so the same
    absence is not counted twice (research 22, finding 6; Kylor 2026-11-24)."""
    from engine.odds import espn
    from engine.picks import slate
    game = espn.norm(f"{away} at {home}")
    for a in entries:
        if espn.norm(str(a.get("team"))) != espn.norm(team):
            continue
        if espn.norm(str(a.get("game"))) != game:
            return True                     # apply_news will not count it for this game, so the script carries it
        sign = 1 if espn.norm(team) == espn.norm(home) else -1
        left, _ = slate.unpriced_part(a, rows, rows[-1][1] if rows else None, rows[-1][2] if rows else None, sign)
        if not left:
            return True
    return False


def _fair_line(line, price_a, price_b, land) -> float | None:
    """A line plus its price lean, as one number (decision 0036): -3 at -125/+105 is about -3.5, not -3. price_a is the home side
    (spreads) or the over (totals and team totals). Without both prices the line is used as it is."""
    if line is None:
        return None
    if price_a is None or price_b is None or land is None:
        return line
    from engine.odds.math import no_vig
    try:
        return land.fair_from_price(line, no_vig(price_a, price_b)[0])
    except Exception:
        return line


def _lands(sport: str | None) -> tuple:
    """(spread, total, team-total) landing tables for turning a Pinnacle price into a fair line; (None, None, None) when unknown."""
    if not sport:
        return None, None, None
    try:
        from engine import stale
        cfg = config.load_config()
        ls, lt = stale.landings(sport, cfg)
        return ls, lt, _team_land(settings(cfg, sport))
    except Exception:
        return None, None, None


def pin_fair(p, w, sport: str | None) -> tuple[float | None, float | None]:
    """The market reference (home spread, total): Pinnacle's line moved by its price lean when posted, else Wagerhouse's line as it is."""
    ls, lt, _ = _lands(sport)
    m_spread = _fair_line(p[7], p[8], p[9], ls) if p and p[7] is not None else w[7]
    m_total = _fair_line(p[12], p[13], p[14], lt) if p and p[12] is not None else w[12]
    return m_spread, m_total


def _game_dict(eid, w, p, own_h, own_a, tt_wh, tt_pin, sport: str | None = None) -> dict:
    """Shared shape for every sport: our team points, the market's (Pinnacle when posted, else Wagerhouse) and Wagerhouse's lines."""
    _, _, _, _, away, home, start, hs, hsp, asp, _, _, tot, op, up = w
    m_spread, m_total = pin_fair(p, w, sport)
    tland = _lands(sport)[2]
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
            g[f"mkt_tt_{who}"] = _fair_line(tp["line"], tp.get("over"), tp.get("under"), tland) if tp and tp["line"] is not None else None
    return g


def market_implied(w, p, fallback_total: float | None = None, sport: str | None = None) -> tuple[float, float | None, float, float] | None:
    """(home spread, total, home implied, away implied) from Pinnacle when posted, else Wagerhouse. With no total posted anywhere, the implied
    points use `fallback_total` (a league-typical total): they only label the script, they are not a feature of the points model."""
    hs = w[7]
    if hs is None:
        return None
    m_spread, m_total = pin_fair(p, w, sport)
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
        mi = market_implied(w, pin.get(eid), 228.0, sport="NBA")
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
        games.append(_game_dict(eid, w, pin.get(eid), own[1], own[0], tt_wh, tt_pin, sport="NBA"))
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
        mi = market_implied(w, pin.get(eid), 52.0, sport="College")
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
        games.append(_game_dict(eid, w, pin.get(eid), own[1], own[0], tt_wh, tt_pin, sport="College"))
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
    qb_entries = _qb_entries()
    try:
        pin_hist = _pin_history(con, "NFL") if qb_entries else {}
    except Exception:
        pin_hist = {}
    season = max(r["season"] for r in rows)
    games = []
    for eid, w in wh.items():
        _, _, _, _, away, home, start, hs, hsp, asp, _, _, tot, op, up = w
        ha, aa = TEAM_NAMES.get(home), TEAM_NAMES.get(away)
        if not ha or not aa or hs is None or tot is None:
            problems.append(f"playbook: skipped {away} at {home} (team name or line missing)")
            continue
        p = pin.get(eid)
        m_spread, m_total = pin_fair(p, w, "NFL")     # market reference: Pinnacle's line and price when posted, else Wagerhouse (decision 0036)
        imp_h, imp_a = m_total / 2 - m_spread / 2, m_total / 2 + m_spread / 2
        wd, rn = wind.get(eid, (None, None))
        own = {}
        for team, opp, is_home, imp in ((ha, aa, 1, imp_h), (aa, ha, 0, imp_a)):
            r = script.live_row(state, season, team, opp, is_home, imp, -m_spread, m_total,
                                backup_qb=int(qb_out(qb_entries, pin_hist.get(eid, []), home, away, home if is_home else away)), wind=wd, rain=rn, dome=0 if wd is not None else 1)
            v = script.vector(r)
            own[is_home] = script.predict(model, v) if v else None
        if None in own.values():
            problems.append(f"playbook: no form for {away} at {home}")
            continue
        wpts = script.forecast_wind_points(wd)      # forecast wind, split evenly between the teams (decision 0036)
        own = {k: v + wpts / 2 for k, v in own.items()}
        g = {"event_id": eid, "home": home, "away": away, "kick": start.replace(tzinfo=timezone.utc),
             "own_home": own[1], "own_away": own[0], "own_margin": own[1] - own[0], "own_total": own[1] + own[0],
             "mkt_home": imp_h, "mkt_away": imp_a, "mkt_margin": -m_spread, "mkt_total": m_total,
             "wh_spread": hs, "wh_home_price": hsp, "wh_away_price": asp, "wh_total": tot, "wh_over": op, "wh_under": up}
        tland = _lands("NFL")[2]
        for who, name in (("home", home), ("away", away)):
            t = tt_wh.get((home, away, who))
            if t and t["line"] is not None:
                g[f"wh_tt_{who}"] = t
                tp = tt_pin.get((home, away, who))
                g[f"mkt_tt_{who}"] = _fair_line(tp["line"], tp.get("over"), tp.get("under"), tland) if tp and tp["line"] is not None else None
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
        _backfill(con)
        from engine import stale, version
        lands = stale.landings(sport, cfg)
        games, problems = live_games(con, now, sport)
        out += problems
        out += apply_news(con, games, sport, now)
        checks = load_checks(now, cfg, sport)
        out += [f"PROBLEM: {m}; its clears and holds were not applied" for m in checks_file_problems(checks)]
        graded = grade_all(candidates(games, st, lands), st, checks=checks,      # shown-only lanes: news picks kept, the rest C
                           mover=lambda c: moved_against(con, c, sport, st))
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
        down = down_units(con, sport, cfg)
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
            units, dollars, note = stake(st, c["grade"], now, down, unit)
            if st.get("max_per_period") and con.execute(f"SELECT count(*) FROM playbook_picks WHERE sport=? AND market <> 'prop' AND nfl_week=? AND {COUNTS_FOR_CAP}",
                           [sport, per]).fetchone()[0] >= st["max_per_period"]:      # 0 = no cap (decision 0041)      # past the cap: paper, named in the recap (research 22, 7)
                units, dollars, note = 0.0, 0.0, f"paper: past the cap of {st['max_per_period']} full-game picks per {st['period']}"
            units, dollars, note, nominal = _paper_or_staked(con, st, c, units, dollars, note, unit, full_game=True, now=now, cfg=cfg)
            # limit() walks on expected profit per $1; half the minimum edge is win chance. Profit = decimal odds x chance edge, so
            # convert, or "don't bet past" and CANCELLED (which tests chance edge) disagree (audit 24; decision 0033 item 8 says same test).
            _, lim = c["land"].limit(c["our_line"], c["line"], c["side"] if c["market"] != "team_total" else c["tt_side"], c["price"],
                                     limit_value(st, c["market"], c["price"]))
            dbp = None if lim is None else _show(c, lim)
            _insert_pick(con, [key, now.replace(tzinfo=None), sport, c["event_id"], c["game"], c["market"], c["side"], c["pick"], c["line"], c["price"],
                               c["grade"], c["edge"], c["our_line"], c["market_line"], c["own_line"], units, dollars, dbp,
                               c["kick"].astimezone(timezone.utc).replace(tzinfo=None), per, why(c), rv, nominal, c.get("price_edge")])
            # the weight in force at issue, so a later weight change can never cancel this pick (the FAIR_SINCE principle)
            con.execute("UPDATE playbook_picks SET blend_weight = ?, paper_reason = ? WHERE pick_key = ?",
                        [float(st["weights"][c["market"]]), note if dollars <= 0 else None, key])
            head = f"PLAYBOOK BET ({c['grade']})" if dollars > 0 else f"PLAYBOOK PAPER PICK ({c['grade']}), DO NOT BET"
            msg = (f"{sport} · {head}\n{c['pick']} ({int(c['price']):+d})\n{c['game']}, {c['kick'].astimezone(tz):%a %-I:%M %p} MT\n"
                   f"Stake: {config.units_text(units, dollars)} ({note})\nDon't bet past {dbp or 'this number'}.\n{edge_split(c)}\nWhy: {why(c)}" + (f"\n{c['note']}" if c.get("note") else ""))
            out.append(msg)
            fail = _send_and_save(con, env, msg, st["lane"], key, now, send and dollars > 0)
            if fail:
                out.append(fail)
        out += _issue_props(con, cfg, env, props_graded, st, now, down, unit, rv, tz, send)
        return out, card(con, cfg, graded, st, now, props_graded if st["props"] else None, games)
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
            # the frozen first numbers stay for the weight re-fit; this read's numbers go beside them for D1b, which must carry today's
            # disagreement, not the first read's (tuning check, research 25)
            con.execute("UPDATE playbook_candidates SET last_own_value = ?, last_market_value = ?, last_seen_utc = ? WHERE cand_key = ?",
                        [own, mkt, now.replace(tzinfo=None), key])
            continue
        con.execute("INSERT INTO playbook_candidates VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [key, now.replace(tzinfo=None), sport, c["event_id"], c["market"], side, c["line"], c["price"], c["grade"], c["edge"],
                     own, mkt, c["kick"].astimezone(timezone.utc).replace(tzinfo=None), c["game"], None, None, own, mkt, now.replace(tzinfo=None)])
        n += 1
    return n


def grade_candidates(con, scorer=None) -> int:
    """Fill the real outcome for finished candidates: home margin, total, team points, or 1/0 for a prop going over."""
    from engine.picks import grade as g
    scorer = scorer or g.final_score
    con.execute(SCHEMA)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    todo = con.execute("SELECT cand_key, sport, event_id, market, side, line, game, kickoff_utc FROM playbook_candidates WHERE outcome IS NULL AND kickoff_utc < ?",
                       [now - timedelta(hours=4)]).fetchall()
    scores, n = {}, 0
    has_props = con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='prop_evals'").fetchone()[0]
    for key, sport, eid, market, side, line, game, kick in todo:
        if market == "prop":
            if not has_props:
                continue
            parts = key.split("|")
            away, home = game.split(" at ", 1)
            row = con.execute(f"SELECT outcome FROM prop_evals WHERE sport=? AND player_id=? AND stat=? AND away=? AND home=? AND outcome IS NOT NULL AND {SAME_GAME} LIMIT 1",
                              [sport, parts[2], parts[3], away, home, _naive(kick)]).fetchone()
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
           "Luck range: how far the units could land from zero by chance alone for a bettor with no edge (two standard deviations).", "",
           "| Sport | Market | Graded picks | W-L | Units | Luck range | Closing-line value (win chance) |", "|---|---|---|---|---|---|---|"]
    for sport, market, n, w, l, units, clv, cn in rows:
        lk = luck_units(con, "p.sport = ? AND p.market = ?", [sport, market])
        out.append(f"| {sport} | {market} | {n} | {w}-{l} | {units:+.2f} | ±{lk:.2f} | {'n/a' if clv is None else f'{100 * clv:+.1f}% on {cn}'} |")
    if not rows:
        out.append("| none graded yet | | | | | | |")
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
        per = period_key(st, c["kick"], cfg)
        units, dollars, note = stake(st, c["grade"], now, down, unit)
        # past a cap: paper, named in the recap, never dropped (research 22, finding 7). Caps count paper picks too (decision 0025).
        if st.get("props_per_game") and con.execute("SELECT count(*) FROM playbook_picks WHERE market='prop' AND event_id=?", [c["event_id"]]).fetchone()[0] \
                >= st["props_per_game"]:      # 0 = no cap (decision 0041)
            units, dollars, note = 0.0, 0.0, f"paper: past the cap of {st['props_per_game']} props per game"
        elif st.get("props_per_period") and con.execute(f"SELECT count(*) FROM playbook_picks WHERE sport=? AND market='prop' AND nfl_week=? AND {COUNTS_FOR_CAP}",
                         [sport, per]).fetchone()[0] >= st["props_per_period"]:
            units, dollars, note = 0.0, 0.0, f"paper: past the cap of {st['props_per_period']} props per {st['period']}"
        units, dollars, note, nominal = _paper_or_staked(con, st, c, units, dollars, note, unit, full_game=False, now=now, cfg=cfg)
        dbp = f"{c['side']} {c['line']:g} at {c['worst_price']:+d} or better" + (" (a lower line is fine)" if c["side"] == "over" else " (a higher line is fine)")
        _insert_pick(con, [key, now.replace(tzinfo=None), sport, c["event_id"], c["game"], "prop", c["side"], c["pick"], c["line"], c["price"], c["grade"],
                           c["edge"], c["our_line"], c["market_line"], c["own_line"], units, dollars, dbp,
                           c["kick"].astimezone(timezone.utc).replace(tzinfo=None), per, why(c), rv, nominal, c.get("price_edge")])
        # a prop's profit is graded at the worst Wagerhouse price we said to take, not Pinnacle's (decision 0036)
        # ...and the blend weight in force at issue, so a later weight change can never cancel it (the FAIR_SINCE principle)
        con.execute("UPDATE playbook_picks SET limit_price = ?, paper_reason = ?, blend_weight = ? WHERE pick_key = ?",
                    [float(c["worst_price"]), note if dollars <= 0 else None, float(st["weights"]["prop"]), key])
        head = f"PLAYBOOK PROP ({c['grade']})" if dollars > 0 else f"PLAYBOOK PAPER PROP ({c['grade']}), DO NOT BET"
        msg = (f"{sport} · {head}\n{c['pick']} (Pinnacle {int(c['price']):+d})\n{c['game']}, {c['kick'].astimezone(tz):%a %-I:%M %p} MT\n"
               f"Stake: {config.units_text(units, dollars)} ({note})\nAt Wagerhouse (Bet Builder): {dbp}.\n{edge_split(c)}\nWhy: {why(c)}" + (f"\n{c['note']}" if c.get("note") else ""))
        out.append(msg)
        fail = _send_and_save(con, env, msg, st.get("props_lane"), key, now, send and dollars > 0 and bool(st.get("props_lane")))
        if fail:
            out.append(fail)
    return out


def _backfill(con) -> None:
    """Fill the decision 0036 columns for picks issued before them, once: the paper reason from the saved message, and a prop's limit
    price from its "don't bet past" text ("over 4.5 at +111 or better"). Never blocks a read."""
    import re
    try:
        con.execute("""UPDATE playbook_picks SET paper_reason = 'paper: already on this game (backfill)' WHERE paper_reason IS NULL
                       AND coalesce(dollars, 0) = 0 AND pick_key IN (SELECT substr(key, 10) FROM alerts_sent WHERE key LIKE 'playbook|%'
                       AND text LIKE '%already on this game%')""")
    except Exception:
        pass
    try:
        for key, dbp in con.execute("SELECT pick_key, dont_bet_past FROM playbook_picks WHERE market = 'prop' AND limit_price IS NULL").fetchall():
            m = re.search(r" at ([+-]\d+) or better", dbp or "")
            if m:
                con.execute("UPDATE playbook_picks SET limit_price = ? WHERE pick_key = ?", [float(m.group(1)), key])
        # props issued before blend_weight was stored: the weight is exact from the frozen numbers, since our chance over =
        # Pinnacle's + weight x (model's - Pinnacle's) and edge = our chance of the side - the chance its price needs
        for key, side, price, edge, mkt, own in con.execute("""SELECT pick_key, side, price, edge, market_line, own_line FROM playbook_picks
                                                            WHERE market = 'prop' AND blend_weight IS NULL AND edge IS NOT NULL
                                                            AND market_line IS NOT NULL AND own_line IS NOT NULL AND price IS NOT NULL""").fetchall():
            if abs(own - mkt) > 1e-9:
                p = edge + chance_needed(price)
                con.execute("UPDATE playbook_picks SET blend_weight = ? WHERE pick_key = ?",
                            [round(((p if side == "over" else 1 - p) - mkt) / (own - mkt), 4), key])
    except Exception:
        pass
    try:
        from engine.picks import grade as g
        for key, units, nominal, lp in con.execute("""SELECT p.pick_key, p.units, coalesce(p.nominal_units, p.units), p.limit_price
                                                       FROM playbook_picks p JOIN playbook_grades r USING (pick_key)
                                                       WHERE p.market = 'prop' AND p.limit_price IS NOT NULL AND r.result = 'W'""").fetchall():
            con.execute("UPDATE playbook_grades SET profit_units = ?, nominal_profit = ? WHERE pick_key = ?",
                        [g.profit(units, lp, "W") if units else 0.0, g.profit(nominal, lp, "W") if nominal else 0.0, key])
    except Exception:
        pass


def _insert_pick(con, vals: list) -> None:
    con.execute(f"INSERT INTO playbook_picks ({PICK_COLS}) VALUES ({','.join('?' * len(vals))})", vals)


def _paper_or_staked(con, st: dict, c: dict, units: float, dollars: float, note: str, unit: float, full_game: bool,
                     now: datetime | None = None, cfg: dict | None = None) -> tuple:
    """(units, dollars, note, nominal units). Paper when the lane is paper, the game already carries a unit, or the week's staked total would
    pass the weekly cap (decision 0027). A CHECK-cleared pick is staked like any other (decision 0027; it was paper under 0025)."""
    nominal = units if units else st["units"].get(c["grade"], 0.0)       # the grade's size, also when the stop-loss made it paper
    staked_lane = (st["full_game"] == "stake" or (bool(c.get("news_pick")) and bool(st.get("news_picks")))) if full_game \
        else bool(st.get("props_stake", True))
    why_paper = None
    if not staked_lane:
        why_paper = f"paper: this lane is not staked (decision 0025; config playbook.sports.{st['sport']})"
    elif dollars > 0:
        on_game = game_exposure(con, c["event_id"]) if st.get("game_cap_units") else 0.0     # 0 = no per-game cap (decision 0041)
        if st.get("game_cap_units") and on_game + dollars > st["game_cap_units"] * unit + 1e-9:
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


def week_staked_units(con, cfg: dict, now: datetime) -> float:
    """Units recommended on Telegram this week (Monday to Sunday Mountain): staked playbook picks plus teaser tickets (decision 0036)."""
    since = week_start_utc(cfg, now)
    total = 0.0
    for sql in ("SELECT coalesce(sum(units), 0) FROM playbook_picks WHERE first_seen_utc >= ? AND dollars > 0",
                "SELECT coalesce(sum(units), 0) FROM teaser_tickets WHERE sent_utc >= ? AND dollars > 0"):
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


def live_since_utc(cfg: dict | None, sport: str = "NFL") -> datetime:
    """Midnight Mountain on `playbook.live_since`, in UTC (naive). The stop counts only staked results from then on, so restarting a stop is
    "set live_since to today" (CHARTER, Money; research 22, finding 2)."""
    cfg = cfg or {}
    d = datetime.fromisoformat(str(settings(cfg, sport)["live_since"]))
    from zoneinfo import ZoneInfo
    local = d.replace(tzinfo=ZoneInfo(cfg.get("timezone_display") or "America/Denver")) if d.tzinfo is None else d
    return local.astimezone(timezone.utc).replace(tzinfo=None)


def teaser_profit_units(con, since: datetime | None = None, strict: bool = False) -> float:
    """Profit in NFL units of every graded teaser ticket that carried money (both legs graded; a push on a leg = no action on the ticket),
    sent on or after `since` (UTC, naive) when given."""
    try:
        rows = con.execute("""SELECT t.units, t.price, ga.result, gb.result FROM teaser_tickets t
                              JOIN teaser_grades ga ON ga.leg_key = t.leg_a JOIN teaser_grades gb ON gb.leg_key = t.leg_b
                              WHERE t.units > 0 AND (? IS NULL OR t.sent_utc >= ?)""", [since, since]).fetchall()
    except Exception as e:
        import duckdb
        if strict and not isinstance(e, duckdb.CatalogException):     # the stop must not read an error as +0.0 (audit 24)
            raise
        return 0.0
    out = 0.0
    for units, price, ra, rb in rows:
        if "L" in (ra, rb):
            out -= units
        elif "P" not in (ra, rb):
            out += units * (100 / abs(price) if price < 0 else price / 100)
    return out


def down_units(con, sport: str, cfg: dict | None = None) -> float:
    """Staked profit in this sport's units for the stop, counted from `live_since` (research 22, finding 2). NFL counts teaser tickets too
    (decision 0027). A missing table means nothing is graded yet (0); any other read error raises, so an unreadable stop is never
    reported as +0.0 (audit 24): callers fail loudly (the playbook run, teaser tickets, the daily check, the tracker's money lines)."""
    import duckdb
    since = live_since_utc(cfg, sport)
    try:
        pb = float(con.execute("SELECT coalesce(sum(g.profit_units), 0) FROM playbook_grades g JOIN playbook_picks p USING (pick_key) "
                               "WHERE p.sport = ? AND p.units > 0 AND p.first_seen_utc >= ?", [sport, since]).fetchone()[0])
    except duckdb.CatalogException:
        pb = 0.0
    return pb + (teaser_profit_units(con, since, strict=True) if sport == "NFL" else 0.0)


def edge_split(c: dict) -> str:
    """One line: how much of the edge is Wagerhouse's price against the market, and how much is our handicap (research 19)."""
    pe = c.get("price_edge")
    if pe is None:
        return f"Edge {100 * c['edge']:+.1f}%."
    ref = "Pinnacle's price" if c["market"] == "prop" else "the market's number"
    return (f"Edge {100 * c['edge']:+.1f}%: {100 * pe:+.1f}% from the price alone (Wagerhouse against {ref}), "
            f"{100 * (c['edge'] - pe):+.1f}% from our handicap" + (f" (of which {100 * c['news_edge']:+.1f}% is unpriced news)" if c.get("news_edge") else "") + ".")


ALERTS_SCHEMA = "CREATE TABLE IF NOT EXISTS alerts_sent (key VARCHAR PRIMARY KEY, ts_utc TIMESTAMP, kind VARCHAR, text VARCHAR, delivered BOOLEAN)"


def _send_and_save(con, env: dict, msg: str, lane: str | None, key: str, now: datetime, send: bool) -> str | None:
    """Send when asked, and always keep the text in alerts_sent (research 18: sent picks were not saved anywhere). A failed send is caught
    and saved as not delivered, so `resend_undelivered` sends it on the next read (research 22, finding 1). Returns a log line on failure."""
    delivered, err = False, None
    if send:
        try:
            from engine.alerts import telegram
            delivered = telegram.send(env, msg, lane, kind="bet")
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
    try:
        con.execute(ALERTS_SCHEMA)
        con.execute("INSERT INTO alerts_sent VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING",
                    [f"playbook|{key}", now.replace(tzinfo=None), "bet" if send else "paper", msg, bool(delivered)])
    except Exception:
        pass
    return f"NOT SENT ({err}); the next read sends it again: {msg.splitlines()[1] if chr(10) in msg else msg}" if err else None


def _lane_for(cfg: dict, sport: str, market: str) -> str | None:
    st = settings(cfg, sport)
    return st.get("props_lane") if market == "prop" else st.get("lane")


def resend_undelivered(con, env: dict, cfg: dict, now: datetime, sender=None) -> list[str]:
    """Every staked pick and teaser ticket that has not reached Telegram, for a game not yet started, is sent again, marked SENT LATE. Runs
    on every read (research 22, finding 1; Kylor 2026-11-24). A pick stays frozen; only its delivery is retried."""
    if sender is None:
        from engine.alerts import telegram
        sender = telegram.send
    from engine.checks import SAVED_SINCE      # picks issued before messages were saved have no row, but most did reach Telegram:
    naive = now.astimezone(timezone.utc).replace(tzinfo=None)   # resending them would risk a second bet (research 22's list of ten)
    con.execute(ALERTS_SCHEMA)
    todo = []
    try:
        for key, sport, market, pick, game, price, dollars, dbp, kick, text in con.execute(
                """SELECT p.pick_key, p.sport, p.market, p.pick, p.game, p.price, p.dollars, p.dont_bet_past, p.kickoff_utc, a.text
                   FROM playbook_picks p LEFT JOIN alerts_sent a ON a.key = 'playbook|' || p.pick_key
                   WHERE p.dollars > 0 AND p.kickoff_utc > ? AND p.first_seen_utc >= ? AND coalesce(a.delivered, false) = false
                   ORDER BY p.first_seen_utc""", [naive, SAVED_SINCE]).fetchall():
            text = text or (f"{sport} · PLAYBOOK BET\n{pick} ({int(price):+d})\n{game}\nStake: ${dollars:g}\nDon't bet past {dbp or 'this number'}.")
            todo.append((f"playbook|{key}", _lane_for(cfg, sport, market), text))
    except Exception:
        pass
    try:
        for key, text in con.execute(
                """SELECT t.ticket_key, t.text FROM teaser_tickets t LEFT JOIN alerts_sent a ON a.key = 'teaser|' || t.ticket_key
                   JOIN teaser_legs la ON la.leg_key = t.leg_a JOIN teaser_legs lb ON lb.leg_key = t.leg_b
                   WHERE t.dollars > 0 AND least(la.kickoff_utc, lb.kickoff_utc) > ? AND t.sent_utc >= ?
                   AND coalesce(a.delivered, false) = false""", [naive, SAVED_SINCE]).fetchall():
            todo.append((f"teaser|{key}", "nfl_teasers", text))
    except Exception:
        pass
    out = []
    for akey, lane, text in todo:
        head, _, rest = text.partition("\n")
        late = f"{head} · SENT LATE (it did not reach Telegram when issued)\n{rest}"
        try:
            ok = bool(sender(env, late, lane, kind="bet"))
        except Exception as e:
            out.append(f"Still not delivered ({type(e).__name__}): {head}")
            continue
        if not ok:
            continue
        if con.execute("SELECT 1 FROM alerts_sent WHERE key = ?", [akey]).fetchone():
            con.execute("UPDATE alerts_sent SET delivered = true, kind = 'bet' WHERE key = ?", [akey])
        else:
            con.execute("INSERT INTO alerts_sent VALUES (?,?,?,?,?)", [akey, naive, "bet", text, True])
        out.append(f"Sent late: {rest.splitlines()[0] if rest else head}")
    return out


# Picks issued from this time store the market line with Pinnacle's price lean in it (decision 0036). CANCELLED compares like with like:
# for older picks it reads Pinnacle's raw line, as when they were issued, so the change itself can never cancel a pick.
FAIR_SINCE = datetime(2026, 11, 24, 23, 0)


def _pin_now(con, sport: str, event_id: str, market: str, game: str, side: str, fair: bool = False, kick=None) -> float | None:
    """Pinnacle's latest number for this market: home spread, total, or a team total; with `fair`, moved by its price lean."""
    ls, lt, tl = _lands(sport) if fair else (None, None, None)
    if market in ("side", "total"):
        cols = "home_spread, home_spread_price, away_spread_price" if market == "side" else "total, over_price, under_price"
        r = con.execute(f"SELECT {cols} FROM line_snapshots WHERE source = ? AND event_id = ? AND {cols.split(',')[0]} IS NOT NULL "
                        "ORDER BY ts_utc DESC LIMIT 1", [snap.SHARP, event_id]).fetchone()
        return _fair_line(r[0], r[1], r[2], ls if market == "side" else lt) if r else None
    if market == "team_total":
        away, _, home = game.partition(" at ")
        r = con.execute("""SELECT line, price_a, price_b FROM derivative_snapshots WHERE source = 'Pinnacle' AND sport = ? AND home = ? AND away = ?
                           AND market = 'team_total' AND period = 'Game' AND description = ? AND line IS NOT NULL
                           AND (CAST(? AS TIMESTAMP) IS NULL OR {SAME_GAME}) ORDER BY ts_utc DESC LIMIT 1""".replace("{SAME_GAME}", SAME_GAME_LOOSE),
                        [sport, home, away, side.split("_")[0], _naive(kick), _naive(kick)]).fetchone()   # this game, not an earlier meeting
        return _fair_line(r[0], r[1], r[2], tl) if r else None
    return None


def cancel_reason(con, cfg: dict, row: dict, lands: tuple | None = None) -> str | None:
    """Why a sent pick should no longer be bet, or None. Full-game picks: Pinnacle's move since the pick, carried into our number at the
    playbook weight, leaves the bet at its sent line and price under half the minimum edge, the same test that set "don't bet past". Props:
    Pinnacle's chance or line has moved so the sent price is under half the minimum edge (research 22, finding 8)."""
    st = settings(cfg, row["sport"])
    half = st["min_edge"]["prop" if row["market"] == "prop" else row["market"]] / 2
    if row["market"] == "prop":
        _, pid, stat, side, line, _eid = row["pick_key"].split("|")
        away_, home_ = row["game"].split(" at ", 1)
        r = con.execute(f"""SELECT line, market_p_over FROM prop_evals WHERE coalesce(sport, 'NFL') = ? AND player_id = ? AND stat = ?
                           AND home = ? AND away = ? AND {SAME_GAME}
                           AND market_p_over IS NOT NULL AND ts_utc >= ? ORDER BY ts_utc DESC LIMIT 1""",
                        [row["sport"], pid, stat, home_, away_, _naive(row["kickoff_utc"]), row["first_seen_utc"] - timedelta(hours=12)]).fetchone()
        if not r:
            return None
        l1, m1 = r
        if l1 != float(line):
            worse = (l1 > float(line)) if side == "over" else (l1 < float(line))
            return f"Pinnacle moved the line against it ({float(line):g} to {l1:g})." if worse else None
        w = st["weights"]["prop"] if row.get("blend_weight") is None else row["blend_weight"]   # the weight it was sent under (FAIR_SINCE principle)
        over = m1 + w * (row["own_line"] - m1)
        p = over if side == "over" else 1 - over
        e = p - chance_needed(row["price"])
        if e < half:
            tail = f"at {int(row['price']):+d} the edge is {100 * e:+.1f}%, under the {100 * half:.1f}% limit."
            if round(100 * row["market_line"]) == round(100 * m1):
                return (f"Pinnacle has not moved (chance over {100 * m1:.0f}%), but our props model now counts for less against it "
                        f"({w:g}); {tail}")
            return f"Pinnacle's chance over moved from {100 * row['market_line']:.0f}% to {100 * m1:.0f}%; {tail}"
        return None
    now_mkt = _pin_now(con, row["sport"], row["event_id"], row["market"], row["game"], row["side"],
                       fair=row.get("first_seen_utc") is not None and row["first_seen_utc"] >= FAIR_SINCE, kick=row.get("kickoff_utc"))
    if now_mkt is None or row["market_line"] is None or row["our_line"] is None:
        return None
    w = st["weights"][row["market"]] if row.get("blend_weight") is None else row["blend_weight"]
    ours = row["our_line"] + (1 - w) * (now_mkt - row["market_line"])
    if lands is None:
        from engine import stale
        lands = stale.landings(row["sport"], cfg)
    land = lands[0] if row["market"] == "side" else lands[1] if row["market"] == "total" else _team_land(st)
    side = row["side"].split("_")[1] if row["market"] == "team_total" else row["side"]
    e = edge_of(land, ours, row["line"], side, row["price"])[0]
    if e < half:
        return (f"Pinnacle moved from {row['market_line']:g} to {now_mkt:g}. With that, our number is {ours:.1f} and {row['pick']} at "
                f"{int(row['price']):+d} has {100 * e:+.1f}% edge, under the {100 * half:.1f}% limit.")
    return None


def cancel_moved(con, env: dict, cfg: dict, now: datetime, sender=None) -> list[str]:
    """CANCELLED message, once, for a sent staked pick that should no longer be bet, before its game starts (CHARTER, Telegram; research 22,
    finding 8; Kylor 2026-11-24). The pick stays frozen and on the record: a bet already placed is kept."""
    if sender is None:
        from engine.alerts import telegram
        sender = telegram.send
    con.execute(ALERTS_SCHEMA)
    naive = now.astimezone(timezone.utc).replace(tzinfo=None)
    cols = ["pick_key", "sport", "event_id", "game", "market", "side", "pick", "line", "price", "our_line", "market_line", "own_line",
            "kickoff_utc", "first_seen_utc", "blend_weight"]
    from engine.checks import SAVED_SINCE      # picks from before messages were saved have no row but most reached Telegram: check them too
    rows = con.execute(f"""SELECT {', '.join('p.' + c for c in cols)} FROM playbook_picks p LEFT JOIN alerts_sent a ON a.key = 'playbook|' || p.pick_key
                           WHERE p.dollars > 0 AND p.kickoff_utc > ? AND (a.delivered OR (a.key IS NULL AND p.first_seen_utc < ?))
                           AND NOT EXISTS (SELECT 1 FROM alerts_sent c WHERE c.key = 'cancel|' || p.pick_key AND c.delivered)""",
                       [naive, SAVED_SINCE]).fetchall()
    out, lands = [], {}
    tz = config.display_tz(cfg) if cfg.get("timezone_display") else timezone.utc
    for r in rows:
        row = dict(zip(cols, r))
        try:
            if row["market"] != "prop" and row["sport"] not in lands:
                from engine import stale
                lands[row["sport"]] = stale.landings(row["sport"], cfg)
            why_c = cancel_reason(con, cfg, row, lands.get(row["sport"]))
        except Exception as e:
            out.append(f"cancel check failed for {row['pick']}: {type(e).__name__}: {e}")
            continue
        if not why_c:
            continue
        kick = row["kickoff_utc"].replace(tzinfo=timezone.utc).astimezone(tz)
        text = (f"{row['sport']} · CANCELLED, DO NOT BET\n{row['pick']} ({int(row['price']):+d})\n{row['game']}, {kick:%a %-I:%M %p} MT\n{why_c}\n"
                "If you already placed it, keep it: it stays on the record at the number sent.")
        try:
            ok = bool(sender(env, text, _lane_for(cfg, row["sport"], row["market"]), kind="bet"))
        except Exception as e:
            out.append(f"CANCELLED not sent ({type(e).__name__}); tried again next read: {row['pick']}")
            continue
        con.execute("INSERT INTO alerts_sent VALUES (?,?,?,?,?) ON CONFLICT (key) DO UPDATE SET delivered = excluded.delivered, ts_utc = excluded.ts_utc",
                    [f"cancel|{row['pick_key']}", naive, "cancel", text, ok])
        out.append(text)
    return out


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
                                  AND market = 'team_total' AND period = 'Game' AND description = ? AND line IS NOT NULL
                                  AND {SAME_GAME} ORDER BY ts_utc""".replace("{SAME_GAME}", SAME_GAME_LOOSE),
                               [sport, c["home"], c["away"], who, _naive(c["kick"])]).fetchall()
            if len(rows) < 2:
                return None
            first, last = rows[0][0], rows[-1][0]
            against = (first - last) if ou == "over" else (last - first)
            if against >= st["move_points"]:
                return f"Not issued: Pinnacle's team total moved {against:g} against this side ({first:g} to {last:g})."
            return None
        if c["market"] == "prop":
            rows = con.execute(f"""SELECT line, market_p_over FROM prop_evals WHERE coalesce(sport, 'NFL') = ? AND player_id = ? AND stat = ?
                                  AND home = ? AND away = ? AND {SAME_GAME} AND market_p_over IS NOT NULL ORDER BY ts_utc""",
                               [sport, c["player_id"], c["stat"], c.get("home_name", c["home"]), c.get("away_name", c["away"]), _naive(c["kick"])]).fetchall()
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


def news_section(games: list[dict]) -> list[str]:
    """Every adjustments.yaml entry that matched a game on this card, and whether it counted (decision 0029). An entry that did not count
    says why, so the research agent can fix it in the same run (most often: no `news_at`)."""
    rows = [(g, n) for g in games for n in (g.get("news") or [])]
    out = ["", "## News on this card (adjustments.yaml)", ""]
    if not rows:
        return out + ["No sourced news entries match games on this card. News is how a shown-only lane gets a staked pick, so an empty "
                      "section in a busy news week is worth a look."]
    out += ["| Game | Entry | Counted? |", "|---|---|---|"]
    for g, n in rows:
        head, _, rest = n.partition(" (")
        status, _, reason = rest.partition("): ")
        ok = "yes" if status.startswith(("unpriced", "partly")) else "NO"
        out.append(f"| {g['away']} at {g['home']} | {head.removeprefix('News, ')}: {reason[:160]} | {ok}: {status} |")
    return out


def card(con, cfg: dict, graded: list[dict], st: dict, now: datetime, props_graded: list[dict] | None = None,
         games: list[dict] | None = None) -> str:
    sport = st["sport"]
    tz = config.display_tz(cfg)
    issued = con.execute("SELECT pick, game, grade, price, dollars, dont_bet_past, kickoff_utc, why FROM playbook_picks WHERE sport=? AND kickoff_utc > ? "
                         "ORDER BY kickoff_utc", [sport, now.replace(tzinfo=None)]).fetchall()
    w = st["weights"]
    staked = {"stake": "staked", "paper": "paper (issued and graded, not staked; decision 0025)"}.get(
        st["full_game"], f"shown only, not staked ({shown_reason(st)})" +
        ("; except news picks, where sourced news Pinnacle has not priced is what clears the bar (staked, decision 0029)" if st.get("news_picks") else ""))
    props_mode = "off" if not (st["props"] and props_graded is not None) else ("staked" if st.get("props_stake", True) else "paper (issued and graded, not staked; decision 0025)")
    out = [f"# {sport} playbook picks", "",
           f"How these are made: PLAYBOOK.md. Our team points come from the {sport} game-script model; our number is pulled toward the market at the "
           f"playbook's starting weights (side {w['side']}, game total {w['total']}, team total {w['team_total']}{f", props {w['prop']}" if st["props"] else ""}). Full-game picks: {staked}. "
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
    if games is not None:
        out += news_section(games)
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
    try:
        lk = luck_units(con, f"p.sport = ? AND p.units > 0 AND {cond}", [sport])
    except Exception:
        lk = None
    luck = "" if lk is None else f" (luck range ±{lk:.2f})"
    return f"Staked picks sent: {sent[0]}; graded {w}-{l}-{pu}, {units:+.2f} units{luck}, {c}."


def lane_events(con, cfg: dict) -> list[tuple[str, str]]:
    """(alert key, text) for each stop that has tripped and each staked lane below its review line (decision 0027). The key is stable, so
    each event reaches Telegram once."""
    out = []
    pc = cfg.get("playbook") or {}
    gl = cfg.get("go_live") or {}
    n_min, floor = int(gl.get("pause_n", 25)), float(gl.get("pause_clv", -0.015))
    for sport in (pc.get("sports") or SPORT_DEFAULTS):
        st = settings(cfg, sport)
        down = down_units(con, sport, cfg)
        if down <= -abs(st["stop_loss_units"]):
            out.append((f"stop|{sport}|{st['live_since']}",
                        f"STOP TRIPPED (not a bet): {sport} staked picks{' and teasers' if sport == 'NFL' else ''} are down {down:.1f} units "
                        f"(stop at {st['stop_loss_units']:g}). New {sport} picks are paper until Kylor restarts them (set playbook.live_since to the restart day). A pause for review, not a verdict."))
        for props in (False, True):
            try:
                cond = "p.market = 'prop'" if props else "p.market <> 'prop'"
                # counted from live_since, like the stop, so a restart starts the review count again too (decision 0036)
                clv, cn = con.execute(f"SELECT avg(clv_chance), count(clv_chance) FROM playbook_grades g JOIN playbook_picks p USING (pick_key) "
                                      f"WHERE p.sport=? AND p.units > 0 AND {cond} AND p.first_seen_utc >= ?",
                                      [sport, live_since_utc(cfg, sport)]).fetchone()
            except Exception:
                continue
            if cn and cn >= n_min and clv is not None and clv < floor:
                what = "props" if props else "full-game picks"
                out.append((f"review|{sport}|{what}|{st['live_since']}",
                            f"REVIEW (not a bet): {sport} {what} average {100 * clv:+.1f}% closing-line value on {cn} staked picks, below the "
                            f"{100 * floor:+.1f}% review line. Still staked; a session should look at this lane (docs/lanes/PLAYBOOK-RECORD.md)."))
    return out


def luck_units(con, where: str, args: list) -> float:
    """Two-standard-deviation swing in units of the graded, decided picks matching `where` (on playbook_picks p), for a bettor with no
    edge at those prices (CLAUDE.md: every report prints the luck range; audit 24). Stake = the grade's size (nominal units)."""
    from engine.odds.math import luck_range
    rows = con.execute(f"""SELECT coalesce(p.nominal_units, p.units), p.price FROM playbook_grades g JOIN playbook_picks p USING (pick_key)
                           WHERE g.result IN ('W', 'L') AND {where}""", args).fetchall()
    bets = []
    for stake, price in rows:
        if not stake:
            continue
        pr = price or -110
        bets.append((stake, stake * 100 / -pr if pr < 0 else stake * pr / 100))
    return luck_range(bets)


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
    for key, sport, eid, market, side, line, price, units, kick, game, nominal, limit_price in con.execute(
            "SELECT pick_key, sport, event_id, market, side, line, price, units, kickoff_utc, game, coalesce(nominal_units, units), limit_price "
            "FROM playbook_picks WHERE kickoff_utc <= ? AND pick_key NOT IN (SELECT pick_key FROM playbook_grades)", [now]).fetchall():
        void = None
        if market == "prop":
            if not has_props:
                continue
            _, pid, stat, side_, _, _ = key.split("|")
            away, home = game.split(" at ", 1)
            row = con.execute(f"SELECT outcome FROM prop_evals WHERE sport=? AND player_id=? AND stat=? AND away=? AND home=? AND outcome IS NOT NULL AND {SAME_GAME} LIMIT 1",
                              [sport, pid, stat, away, home, _naive(kick)]).fetchone()
            if row is None:
                void = _prop_void(scorer, sport, eid, kick, now, out, game)
                if void is None:
                    continue
                res, close, cp, cc, hs, as_ = "V", None, None, None, None, None
            else:
                v = (row[0] - line) if side_ == "over" else (line - row[0])
                res = "W" if v > 0 else "L" if v < 0 else "P"
                close, cp, cc = prop_close(con, sport, pid, stat, home, away, side_, line, price, kick)
                hs = as_ = None
        else:
            try:        # one bad score must not stop the other picks' grading, the daily check or the recap (audit 24)
                score = scorer(sport, eid)
            except Exception as e:
                out.append(f"NOT GRADED {game}: score read failed ({type(e).__name__}: {e})")
                continue
            if score is None:
                if now - kick > timedelta(hours=VOID_AFTER_HOURS["postponed"]):     # postponed or cancelled: void (decision 0036)
                    con.execute(f"INSERT INTO playbook_grades ({GRADE_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                [key, None, None, "V", 0.0, None, None, None, now, 0.0])
                    out.append(f"PLAYBOOK GRADED {key}: V (no final score {VOID_AFTER_HOURS['postponed']} hours after the start: postponed or cancelled)")
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
        # props pay at the worst Wagerhouse price we said to take, not Pinnacle's (decision 0036); a void pays nothing
        pay = limit_price if (market == "prop" and limit_price is not None) else price
        prof = g.profit(units, pay, res) if units and res != "V" else 0.0
        nprof = g.profit(nominal, pay, res) if nominal and res != "V" else 0.0
        con.execute(f"INSERT INTO playbook_grades ({GRADE_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?)", [key, hs, as_, res, prof, close, cp, cc, now, nprof])
        out.append(f"PLAYBOOK GRADED {key}: {res} ({prof:+.2f} units staked, {nprof:+.2f} at the grade's size)")
    return out


# Hours after the start before an ungraded pick is void (decision 0036): a prop whose player has no stat line once the game is final
# (Pinnacle and most books: "must play"), allowing for nflverse posting stats the next day; a game with no final score at all.
VOID_AFTER_HOURS = {"NBA": 30, "NFL": 40, "College": 40, "postponed": 72}


def _prop_void(scorer, sport: str, eid: str, kick, now, out: list, game: str) -> str | None:
    """'V' when this prop's game is final (or never finished) long enough ago that a missing stat line means the player did not play."""
    if now - kick <= timedelta(hours=VOID_AFTER_HOURS.get(sport, 40)):
        return None
    try:
        score = scorer(sport, eid)
    except Exception as e:
        out.append(f"NOT GRADED {game}: score read failed ({type(e).__name__}: {e})")
        return None
    if score is not None or now - kick > timedelta(hours=VOID_AFTER_HOURS["postponed"]):
        return "V"
    return None


def _nv_over(po: float | None, pu: float | None) -> float | None:
    if po is None or pu is None:
        return None
    a, b = 1 / american_to_decimal(po), 1 / american_to_decimal(pu)
    return a / (a + b)


# A prop row belongs to this game only if its start is within 6 hours of the pick's kickoff: the same two NBA teams meet again,
# and a query by player, stat and teams alone could read the other game (audit 24).
SAME_GAME = "abs(epoch(CAST(replace(start_utc, 'Z', '') AS TIMESTAMP)) - epoch(CAST(? AS TIMESTAMP))) <= 21600"
# The same, but a row with no readable start time still matches (every stored row has one; older test rows do not). Used where the
# filter was added by the tuning check (research 25) so an earlier meeting of the same two teams is never read.
SAME_GAME_LOOSE = "coalesce(abs(epoch(try_cast(replace(start_utc, 'Z', '') AS TIMESTAMP)) - epoch(CAST(? AS TIMESTAMP))) <= 21600, true)"


def _naive(t):
    return t.astimezone(timezone.utc).replace(tzinfo=None) if getattr(t, "tzinfo", None) else t


def prop_close(con, sport, pid, stat, home, away, side, line, price, kick) -> tuple:
    """(Pinnacle closing line, points our way, no-vig chance of our bet at the close minus the chance our price needed). The chance needs the
    closing line to equal ours; otherwise only the points are kept."""
    row = con.execute("""SELECT line, market_p_over FROM prop_evals WHERE coalesce(sport, 'NFL') = ? AND player_id = ? AND stat = ? AND home = ?
                         AND away = ? AND market_p_over IS NOT NULL AND ts_utc < ? AND {SAME_GAME} ORDER BY ts_utc DESC LIMIT 1""".replace("{SAME_GAME}", SAME_GAME_LOOSE),
                      [sport, pid, stat, home, away, kick, _naive(kick)]).fetchone()
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
                         AND {SAME_GAME} ORDER BY ts_utc DESC LIMIT 1""".replace("{SAME_GAME}", SAME_GAME_LOOSE), [sport, home, away, who, kick, _naive(kick)]).fetchone()
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
