"""College football game script and team points (PLAYBOOK.md, college section; decisions 0022 and 0034).

Free CollegeFootballData only, cached in `data.nosync/raw/cfbd`: games and closing lines (`cfbd_lines_<year>.json`) and per-game advanced
stats with garbage time removed (`cfbd_adv_<year>.json`: plays, expected points added (PPA) per play, success rate). The free tier also
has play-by-play, drives, returning production, talent and SP+ (research 23).

Per team, from EARLIER games only, decayed: points scored and allowed, offensive and defensive PPA per play, success rate for and against,
plays run and faced, each next to the opponent's same numbers so the regression can weigh schedule; one tempo term (offensive PPA per play
times the expected plays); home and neutral site. Last season counts as `PRIOR_GAMES` games. This is research 23's T1 model: more accurate
than points per game in every market, still not better than the close, so college full-game picks stay shown (research 23, decision 0034).
It is fitted on every lined game: fitting on FBS-against-FBS games only (the only ones Wagerhouse posts) was no better on those games
(decision 0034).

Team points = ridge regression fitted on earlier seasons; the weight our number earns against the market is fitted one season back and
reported by `walk_forward` (same method as research 15 and 16).
"""
from __future__ import annotations

import json
from collections import defaultdict

from engine import config
from engine.models.script import fit_weight, predict, ridge

CACHE = config.DATA / "raw" / "cfbd"
DECAY = 0.85
PRIOR_GAMES = 2.0
STATS = ("pf", "pa", "oppa", "dppa", "osr", "dsr", "opl", "dpl")
ADV = ("oppa", "dppa", "osr", "dsr", "opl", "dpl")
FEATURES = ("o_pts", "d_pts", "opp_o_pts", "opp_d_pts", "home", "neutral",
            "o_ppa", "d_ppa", "o_sr", "d_sr", "o_pl", "d_pl", "opp_o_ppa", "opp_d_ppa", "opp_o_sr", "opp_d_sr", "opp_o_pl", "opp_d_pl",
            "ppa_x_plays")
BOOKS = ("Bovada", "consensus", "DraftKings", "ESPN Bet", "William Hill (New Jersey)")


def _line(g: dict):
    lines = [l for l in g.get("lines") or [] if l.get("spread") is not None and l.get("overUnder") is not None]
    for b in BOOKS:
        for l in lines:
            if l.get("provider") == b:
                return l
    return lines[0] if lines else None


def _games() -> list[dict]:
    out = []
    for p in sorted(CACHE.glob("cfbd_lines_*.json")):
        out += json.loads(p.read_text())
    return sorted(out, key=lambda g: (g.get("startDate") or "", g["id"]))


def adv_stats(rows: list[dict]) -> dict:
    """CFBD /stats/game/advanced rows -> (game id, team name) -> per-game numbers. Rows without plays or PPA are skipped."""
    out = {}
    for r in rows:
        o, d = r.get("offense") or {}, r.get("defense") or {}
        if not o.get("plays") or not d.get("plays") or o.get("ppa") is None or d.get("ppa") is None:
            continue
        out[(str(r["gameId"]), r["team"])] = {"oppa": o["ppa"], "dppa": d["ppa"], "osr": o.get("successRate") or 0.0,
                                              "dsr": d.get("successRate") or 0.0, "opl": float(o["plays"]), "dpl": float(d["plays"])}
    return out


def _adv() -> dict:
    out = {}
    for p in sorted(CACHE.glob("cfbd_adv_*.json")):
        out.update(adv_stats(json.loads(p.read_text())))
    return out


def event_teams() -> dict[str, tuple[int, int, int]]:
    """ESPN event id -> (home team id, away team id, neutral) for every cached game, played or not (CollegeFootballData uses ESPN ids)."""
    return {str(g["id"]): (g["homeTeamId"], g["awayTeamId"], int(bool(g.get("neutralSite")))) for g in _games()}


class _Run:
    def __init__(self):
        self.w = defaultdict(float)
        self.v = defaultdict(float)

    def add(self, k: str, x: float):
        self.w[k] = self.w[k] * DECAY + 1
        self.v[k] = self.v[k] * DECAY + x

    def mean(self, k: str):
        return self.v[k] / self.w[k] if self.w[k] else None


def _form(runs, finals, s, team) -> dict:
    r, prev = runs.get((s, team)), finals.get((s - 1, team))
    out = {"games": r.w["pf"] if r else 0.0}
    for k in STATS:
        cur, wc = (r.mean(k), r.w[k]) if r else (None, 0.0)
        pv = prev.get(k) if prev else None
        out[k] = pv if cur is None else cur if pv is None else (cur * wc + pv * PRIOR_GAMES) / (wc + PRIOR_GAMES)
    return out


def _features(ft: dict, fo: dict) -> dict:
    row = {"o_pts": ft["pf"], "d_pts": ft["pa"], "opp_o_pts": fo["pf"], "opp_d_pts": fo["pa"],
           "o_ppa": ft["oppa"], "d_ppa": ft["dppa"], "o_sr": ft["osr"], "d_sr": ft["dsr"], "o_pl": ft["opl"], "d_pl": ft["dpl"],
           "opp_o_ppa": fo["oppa"], "opp_d_ppa": fo["dppa"], "opp_o_sr": fo["osr"], "opp_d_sr": fo["dsr"], "opp_o_pl": fo["opl"], "opp_d_pl": fo["dpl"]}
    row["ppa_x_plays"] = None if None in (ft["oppa"], ft["opl"], fo["dpl"]) else ft["oppa"] * (ft["opl"] + fo["dpl"]) / 2
    return row


def build(state: dict | None = None, adv: dict | None = None) -> list[dict]:
    adv = _adv() if adv is None else adv
    runs, finals = {}, {}
    out = []
    for g in _games():
        if g.get("seasonType") not in ("regular", "postseason"):
            continue
        s, h, a = g["season"], g["homeTeamId"], g["awayTeamId"]
        hs_, as_ = g.get("homeScore"), g.get("awayScore")
        if hs_ is None or as_ is None:
            continue
        gid, names = str(g["id"]), {h: g.get("homeTeam"), a: g.get("awayTeam")}
        fbs = int(g.get("homeClassification") == "fbs" and g.get("awayClassification") == "fbs")
        ln = _line(g)
        if ln is not None:
            spread, tot = float(ln["spread"]), float(ln["overUnder"])        # CFBD spread: home spread (negative = home favored)
            imp = {h: tot / 2 - spread / 2, a: tot / 2 + spread / 2}
            f = {t: _form(runs, finals, s, t) for t in (h, a)}
            neutral = int(bool(g.get("neutralSite")))
            for t, o, pts in ((h, a, hs_), (a, h, as_)):
                out.append({"event_id": gid, "game_id": gid, "season": s, "week": g.get("week"), "team": t, "opp": o, "fbs": fbs,
                            "home": int(t == h and not neutral), "neutral": neutral, "implied": imp[t], "points": float(pts),
                            "spread": -spread, "total": tot, "games": f[t]["games"], "opp_games": f[o]["games"], "_is_home": int(t == h),
                            **_features(f[t], f[o])})
        for t, pf, pa_ in ((h, hs_, as_), (a, as_, hs_)):
            r = runs.setdefault((s, t), _Run())
            r.add("pf", float(pf))
            r.add("pa", float(pa_))
            st = adv.get((gid, names[t]))
            if st:
                for k in ADV:
                    r.add(k, st[k])
            finals[(s, t)] = {k: r.mean(k) for k in STATS}
    if state is not None:
        state.update(runs=runs, finals=finals)
    return out


def vector(r: dict) -> list[float] | None:
    x = [r.get(k) for k in FEATURES]
    return None if any(v is None for v in x) else [float(v) for v in x]


def live_row(state: dict, season: int, team: int, opp: int, is_home: int, neutral: int, implied: float) -> dict:
    ft, fo = (_form(state["runs"], state["finals"], season, x) for x in (team, opp))
    return {"season": season, "team": team, "opp": opp, "home": int(is_home and not neutral), "neutral": neutral, "implied": implied,
            "games": ft["games"], "opp_games": fo["games"], **_features(ft, fo)}


def _usable(rows: list[dict], fbs_only: bool = False) -> list[dict]:
    return [r for r in rows if min(r["games"], r["opp_games"]) >= 2 and (r["fbs"] or not fbs_only) and vector(r) is not None]


def fit_live(rows: list[dict], lam: float = 50.0):
    use = _usable(rows)
    return ridge([vector(r) for r in use], [r["points"] for r in use], lam)


def _pairs(rows: list[dict], own: list[float]) -> list[dict]:
    by = defaultdict(dict)
    for r, o in zip(rows, own):
        by[r["event_id"]]["home" if r["_is_home"] else "away"] = (r, o)
    out = []
    for d in by.values():
        if "home" in d and "away" in d:
            (h, oh), (a, oa) = d["home"], d["away"]
            out.append({"total": h["total"], "own_total": oh + oa, "actual_total": h["points"] + a["points"],
                        "mkt_margin": h["spread"], "own_margin": oh - oa, "actual_margin": h["points"] - a["points"]})
    return out


def walk_forward(rows: list[dict] | None = None, lam: float = 50.0, fbs_only: bool = False) -> dict:
    rows = rows if rows is not None else build()
    use = _usable(rows, fbs_only)
    seasons = sorted({r["season"] for r in use})
    out = {"seasons": [], "team": [], "game": []}
    for s in seasons[2:]:
        tr, te = [r for r in use if r["season"] < s], [r for r in use if r["season"] == s]
        inner_tr, inner_te = [r for r in tr if r["season"] < s - 1], [r for r in tr if r["season"] == s - 1]
        model = ridge([vector(r) for r in tr], [r["points"] for r in tr], lam)
        inner = ridge([vector(r) for r in inner_tr], [r["points"] for r in inner_tr], lam)
        own_i = [predict(inner, vector(r)) for r in inner_te]
        gi = _pairs(inner_te, own_i)
        w_team = fit_weight(own_i, [r["implied"] for r in inner_te], [r["points"] for r in inner_te])
        w_total = fit_weight([a["own_total"] for a in gi], [a["total"] for a in gi], [a["actual_total"] for a in gi])
        w_side = fit_weight([a["own_margin"] for a in gi], [a["mkt_margin"] for a in gi], [a["actual_margin"] for a in gi])
        own = [predict(model, vector(r)) for r in te]
        for r, o in zip(te, own):
            out["team"].append({"season": s, "implied": r["implied"], "own": o, "blend": r["implied"] + w_team * (o - r["implied"]), "points": r["points"]})
        for a in _pairs(te, own):
            a.update(season=s, blend_total=a["total"] + w_total * (a["own_total"] - a["total"]),
                     blend_margin=a["mkt_margin"] + w_side * (a["own_margin"] - a["mkt_margin"]))
            out["game"].append(a)
        out["seasons"].append({"season": s, "w_team": round(w_team, 3), "w_total": round(w_total, 3), "w_side": round(w_side, 3), "n_team": len(te)})
    return out
