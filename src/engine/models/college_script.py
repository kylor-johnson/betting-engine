"""College football game script and team points (PLAYBOOK.md, college section; decision 0022).

Free data only: CollegeFootballData's cached seasons (scores, closing lines; `data.nosync/raw/cfbd`). Per team, from EARLIER games only:
decayed points scored and allowed per game, each read next to the opponents' own form so the regression can weigh schedule; home and
neutral site. Last season counts as `PRIOR_GAMES` games, and less from week 3 on as this season builds up (the transfer portal makes last
season a weaker guide, research 14 2c). No play-by-play: the free tier has no play-level data, so there is no pace or pass-rate term.

Team points = ridge regression fitted on earlier seasons; the weight our number earns against the market is fitted one season back and
reported by `walk_forward` (same method as research 15).
"""
from __future__ import annotations

import json
from collections import defaultdict

from engine import config
from engine.models.script import fit_weight, predict, ridge

CACHE = config.DATA / "raw" / "cfbd"
DECAY = 0.85
PRIOR_GAMES = 2.0
FEATURES = ("o_pts", "d_pts", "opp_o_pts", "opp_d_pts", "home", "neutral")
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


def event_teams() -> dict[str, tuple[int, int, int]]:
    """ESPN event id -> (home team id, away team id, neutral) for every cached game, played or not (CollegeFootballData uses ESPN ids)."""
    return {str(g["id"]): (g["homeTeamId"], g["awayTeamId"], int(bool(g.get("neutralSite")))) for g in _games()}


class _Run:
    def __init__(self):
        self.w, self.o, self.d = 0.0, 0.0, 0.0

    def add(self, o: float, d: float):
        self.w = self.w * DECAY + 1
        self.o = self.o * DECAY + o
        self.d = self.d * DECAY + d


def _pre(runs, finals, s, team) -> dict:
    r, prev = runs.get((s, team)), finals.get((s - 1, team))
    wc = r.w if r else 0.0
    out = {"games": wc}
    for k, cur in (("o", r.o / r.w if r and r.w else None), ("d", r.d / r.w if r and r.w else None)):
        pv = prev[k] if prev else None
        if cur is None:
            out[k] = pv
        elif pv is None:
            out[k] = cur
        else:
            out[k] = (cur * wc + pv * PRIOR_GAMES) / (wc + PRIOR_GAMES)
    return out


def build(state: dict | None = None) -> list[dict]:
    runs, finals = {}, {}
    out = []
    for g in _games():
        if g.get("seasonType") not in ("regular", "postseason"):
            continue
        s, h, a = g["season"], g["homeTeamId"], g["awayTeamId"]
        hs_, as_ = g.get("homeScore"), g.get("awayScore")
        if hs_ is None or as_ is None:
            continue
        ln = _line(g)
        if ln is not None:
            spread, tot = float(ln["spread"]), float(ln["overUnder"])        # CFBD spread: home spread (negative = home favored)
            imp = {h: tot / 2 - spread / 2, a: tot / 2 + spread / 2}
            ph, pa = _pre(runs, finals, s, h), _pre(runs, finals, s, a)
            neutral = int(bool(g.get("neutralSite")))
            for t, o, pt, po, pts in ((h, a, ph, pa, hs_), (a, h, pa, ph, as_)):
                out.append({"event_id": str(g["id"]), "game_id": str(g["id"]), "season": s, "team": t, "opp": o, "home": int(t == h and not neutral),
                            "neutral": neutral, "implied": imp[t], "points": float(pts), "spread": -spread, "total": tot, "games": pt["games"],
                            "o_pts": pt["o"], "d_pts": pt["d"], "opp_o_pts": po["o"], "opp_d_pts": po["d"], "_is_home": int(t == h)})
        for t, o, pf, pa_ in ((h, a, hs_, as_), (a, h, as_, hs_)):
            runs.setdefault((s, t), _Run()).add(float(pf), float(pa_))
            r = runs[(s, t)]
            finals[(s, t)] = {"o": r.o / r.w, "d": r.d / r.w}
    if state is not None:
        state.update(runs=runs, finals=finals)
    return out


def vector(r: dict) -> list[float] | None:
    x = [r.get(k) for k in FEATURES]
    return None if any(v is None for v in x) else [float(v) for v in x]


def live_row(state: dict, season: int, team: int, opp: int, is_home: int, neutral: int, implied: float) -> dict:
    pt, po = _pre(state["runs"], state["finals"], season, team), _pre(state["runs"], state["finals"], season, opp)
    return {"season": season, "team": team, "opp": opp, "home": int(is_home and not neutral), "neutral": neutral, "implied": implied,
            "games": pt["games"], "o_pts": pt["o"], "d_pts": pt["d"], "opp_o_pts": po["o"], "opp_d_pts": po["d"]}


def fit_live(rows: list[dict], lam: float = 50.0):
    use = [r for r in rows if r["games"] >= 2 and vector(r) is not None]
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


def walk_forward(rows: list[dict] | None = None, lam: float = 50.0) -> dict:
    rows = rows if rows is not None else build()
    use = [r for r in rows if r["games"] >= 2 and vector(r) is not None]
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
