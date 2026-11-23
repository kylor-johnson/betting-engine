"""NBA game script and team points (PLAYBOOK.md, NBA section; decision 0022).

The NBA script is pace and efficiency: how many possessions a game will have and how many points each team scores per possession, from the
ESPN box scores of EARLIER games only (`nba_data`). Per team: decayed averages of possessions (FGA + 0.44 FTA + turnovers, a standard estimate
without offensive rebounds), points per possession, and the same allowed on defense; plus home and the second night of a back-to-back.
Last season counts as `PRIOR_GAMES` games at the start of a season.

Team points = a ridge regression on those inputs, fitted on earlier seasons (same machinery as the NFL script, `script.ridge`). The weight
our number earns against the market is fitted one season back, exactly as in research 15, and reported by `walk_forward`.
Not in: who is missing tonight (box scores only show it after the game, which would leak; live, the props model handles absences).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from engine.models import nba_data
from engine.models.script import fit_weight, predict, ridge

DECAY = 0.9
PRIOR_GAMES = 5.0
KEYS = ("poss", "ppp")
FEATURES = ("o_poss", "o_ppp", "d_poss", "d_ppp", "opp_o_poss", "opp_o_ppp", "opp_d_poss", "opp_d_ppp", "home", "b2b", "opp_b2b")


def _team_box(g: dict) -> dict[str, dict]:
    out = {}
    for team in (g["home"], g["away"]):
        ps = [p for p in g["players"] if p["team"] == team and p.get("min", 0) > 0]
        pts = sum(p.get("pts", 0) for p in ps)
        poss = sum(p.get("fga", 0) for p in ps) + 0.44 * sum(p.get("fta", 0) for p in ps) + sum(p.get("tov", 0) for p in ps)
        out[team] = {"pts": pts, "poss": poss}
    return out


class _Run:
    def __init__(self):
        self.w = 0.0
        self.o = defaultdict(float)
        self.d = defaultdict(float)

    def add(self, o: dict, d: dict):
        self.w = self.w * DECAY + 1
        for k in KEYS:
            self.o[k] = self.o[k] * DECAY + o[k]
            self.d[k] = self.d[k] * DECAY + d[k]

    def mean(self, side: str, k: str):
        return (self.o if side == "o" else self.d)[k] / self.w if self.w else None


def _pre(runs, finals, s, team) -> dict:
    r, prev = runs.get((s, team)), finals.get((s - 1, team))
    out = {"games": r.w if r else 0.0}
    for side in ("o", "d"):
        for k in KEYS:
            cur = r.mean(side, k) if r else None
            pv = prev[side][k] if prev else None
            wc = r.w if r else 0.0
            if cur is None:
                out[f"{side}_{k}"] = pv
            elif pv is None:
                out[f"{side}_{k}"] = cur
            else:
                out[f"{side}_{k}"] = (cur * wc + pv * PRIOR_GAMES) / (wc + PRIOR_GAMES)
    return out


def build(state: dict | None = None) -> list[dict]:
    """One row per team per game with a closing line: pre-game form, the market's implied team points and the real points."""
    games = [g for g in nba_data.load() if g.get("players")]
    runs, finals, last_day = {}, {}, {}
    out = []
    for g in games:
        s = g["season"]
        box = _team_box(g)
        if box[g["home"]]["poss"] <= 0 or box[g["away"]]["poss"] <= 0:
            continue
        day = date.fromisoformat(g["date"])
        b2b = {t: int(last_day.get(t) is not None and (day - last_day[t]).days == 1) for t in (g["home"], g["away"])}
        if g.get("home_spread") is not None and g.get("total") is not None:
            hs, tot = g["home_spread"], g["total"]
            imp = {g["home"]: tot / 2 - hs / 2, g["away"]: tot / 2 + hs / 2}
            pre = {t: _pre(runs, finals, s, t) for t in (g["home"], g["away"])}
            for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
                row = {"event_id": g["event_id"], "season": s, "team": t, "opp": o, "home": int(t == g["home"]), "implied": imp[t],
                       "points": box[t]["pts"], "spread": -hs, "total": tot, "b2b": b2b[t], "opp_b2b": b2b[o], "games": pre[t]["games"]}
                for k in KEYS:
                    row[f"o_{k}"], row[f"d_{k}"] = pre[t][f"o_{k}"], pre[t][f"d_{k}"]
                    row[f"opp_o_{k}"], row[f"opp_d_{k}"] = pre[o][f"o_{k}"], pre[o][f"d_{k}"]
                out.append(row)
        for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
            ob = {"poss": box[t]["poss"], "ppp": box[t]["pts"] / box[t]["poss"]}
            db = {"poss": box[o]["poss"], "ppp": box[o]["pts"] / box[o]["poss"]}
            runs.setdefault((s, t), _Run()).add(ob, db)
            r = runs[(s, t)]
            finals[(s, t)] = {side: {k: r.mean(side, k) for k in KEYS} for side in ("o", "d")}
            last_day[t] = day
    if state is not None:
        state.update(runs=runs, finals=finals, last_day=last_day)
    return out


def vector(r: dict) -> list[float] | None:
    x = [r.get(k) for k in FEATURES]
    return None if any(v is None for v in x) else [float(v) for v in x]


def live_row(state: dict, season: int, team: str, opp: str, home: int, implied: float, day: date) -> dict:
    pre, po = _pre(state["runs"], state["finals"], season, team), _pre(state["runs"], state["finals"], season, opp)
    ld = state["last_day"]
    row = {"season": season, "team": team, "opp": opp, "home": home, "implied": implied, "games": pre["games"],
           "b2b": int(ld.get(team) is not None and (day - ld[team]).days == 1), "opp_b2b": int(ld.get(opp) is not None and (day - ld[opp]).days == 1)}
    for k in KEYS:
        row[f"o_{k}"], row[f"d_{k}"], row[f"opp_o_{k}"], row[f"opp_d_{k}"] = pre[f"o_{k}"], pre[f"d_{k}"], po[f"o_{k}"], po[f"d_{k}"]
    return row


def fit_live(rows: list[dict], lam: float = 50.0):
    use = [r for r in rows if r["games"] >= 3 and vector(r) is not None]
    return ridge([vector(r) for r in use], [r["points"] for r in use], lam)


def walk_forward(rows: list[dict] | None = None, lam: float = 50.0) -> dict:
    """Train on earlier seasons; the blend weight is fitted on the last training season with a model trained before it."""
    from engine.models.script import _pairs
    rows = rows if rows is not None else build()
    use = [r for r in rows if r["games"] >= 3 and vector(r) is not None]
    seasons = sorted({r["season"] for r in use})
    out = {"seasons": [], "team": [], "game": []}
    for s in seasons[2:]:
        tr = [r for r in use if r["season"] < s]
        te = [r for r in use if r["season"] == s]
        inner_tr = [r for r in tr if r["season"] < s - 1]
        inner_te = [r for r in tr if r["season"] == s - 1]
        model = ridge([vector(r) for r in tr], [r["points"] for r in tr], lam)
        inner = ridge([vector(r) for r in inner_tr], [r["points"] for r in inner_tr], lam)
        own_i = [predict(inner, vector(r)) for r in inner_te]
        for r in inner_te:
            r["game_id"] = r["event_id"]
        gi = _pairs(inner_te, own_i)
        w_team = fit_weight(own_i, [r["implied"] for r in inner_te], [r["points"] for r in inner_te])
        w_total = fit_weight([a["own_total"] for a in gi], [a["total"] for a in gi], [a["actual_total"] for a in gi])
        w_side = fit_weight([a["own_margin"] for a in gi], [a["mkt_margin"] for a in gi], [a["actual_margin"] for a in gi])
        own = [predict(model, vector(r)) for r in te]
        for r, o in zip(te, own):
            r["game_id"] = r["event_id"]
            out["team"].append({"season": s, "implied": r["implied"], "own": o, "blend": r["implied"] + w_team * (o - r["implied"]), "points": r["points"]})
        for a in _pairs(te, own):
            a.update(season=s, blend_total=a["total"] + w_total * (a["own_total"] - a["total"]),
                     blend_margin=a["mkt_margin"] + w_side * (a["own_margin"] - a["mkt_margin"]))
            out["game"].append(a)
        out["seasons"].append({"season": s, "w_team": round(w_team, 3), "w_total": round(w_total, 3), "w_side": round(w_side, 3), "n_team": len(te)})
    return out
