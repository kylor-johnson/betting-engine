"""Research 23 test-only module: the pre-registered college tests T1 to T5 (docs/research/23-cfb-model-review.md).

Not used by any live path. Reads CollegeFootballData pulls in `data.nosync/raw/cfbd_review/` (per-game advanced stats with garbage time
removed and kept, last season's final SP+, returning production, talent) and the same cached games and closing lines as research 16.
Method is research 16's: ridge fitted on earlier seasons, blend weight fitted one season back, test seasons 2023 to 2026.
"""
from __future__ import annotations

import json
from collections import defaultdict

from engine import config
from engine.models import college_script as cs
from engine.models.script import fit_weight, predict, ridge

REVIEW = config.DATA / "raw" / "cfbd_review"
DECAY, PRIOR_GAMES, LAM = 0.85, 2.0, 50.0
POWER = {"SEC", "Big Ten", "Big 12", "ACC", "Pac-12"}
STATS = ("pf", "pa", "oppa", "dppa", "osr", "dsr", "opl", "dpl")
BASE = ("o_pts", "d_pts", "opp_o_pts", "opp_d_pts", "home", "neutral")
EFF = ("o_ppa", "d_ppa", "o_sr", "d_sr", "o_pl", "d_pl", "opp_o_ppa", "opp_d_ppa", "opp_o_sr", "opp_d_sr", "opp_o_pl", "opp_d_pl", "ppa_x_plays")
PRIOR = ("sp_o", "sp_d", "ret", "tal", "opp_sp_o", "opp_sp_d", "opp_ret", "opp_tal")
THRESH = {"team": 3.5, "total": 4.0, "side": 3.0}
TESTS = (2023, 2024, 2025, 2026)


def _load(name: str):
    return json.loads((REVIEW / name).read_text())


def _adv(garbage: bool) -> dict:
    tag = "all" if garbage else "gt"
    out = {}
    for s in range(2020, 2027):
        for r in _load(f"adv_{s}_{tag}.json"):
            o, d = r.get("offense") or {}, r.get("defense") or {}
            if not o.get("plays") or not d.get("plays") or o.get("ppa") is None or d.get("ppa") is None:
                continue
            out[(str(r["gameId"]), r["team"])] = {"oppa": o["ppa"], "dppa": d["ppa"], "osr": o["successRate"], "dsr": d["successRate"],
                                                  "opl": float(o["plays"]), "dpl": float(d["plays"])}
    return out


def _priors() -> dict:
    """(season, team) -> preseason numbers. SP+ is last season's final; returning production and talent are this season's.
    A team missing from a list gets that list's 10th percentile (teams outside the lists are mostly FCS or new to FBS)."""
    out = defaultdict(dict)
    for s in range(2021, 2027):
        lists = {
            "sp_o": {r["team"]: r["offense"]["rating"] for r in _load(f"sp_{s - 1}.json") if r.get("offense", {}).get("rating") is not None},
            "sp_d": {r["team"]: r["defense"]["rating"] for r in _load(f"sp_{s - 1}.json") if r.get("defense", {}).get("rating") is not None},
            "ret": {r["team"]: r["percentPPA"] for r in _load(f"returning_{s}.json") if r.get("percentPPA") is not None},
            "tal": {r["team"]: float(r["talent"]) for r in _load(f"talent_{s}.json") if r.get("talent")},
        }
        for k, d in lists.items():
            vals = sorted(d.values())
            low = vals[len(vals) // 10] if k != "sp_d" else vals[-(len(vals) // 10) - 1]   # defense: higher rating = worse
            out[s][k] = (d, low)
    return out


class _Run:
    def __init__(self):
        self.w = defaultdict(float)
        self.v = defaultdict(float)

    def add(self, k: str, x: float):
        self.w[k] = self.w[k] * DECAY + 1
        self.v[k] = self.v[k] * DECAY + x

    def mean(self, k):
        return self.v[k] / self.w[k] if self.w[k] else None


def _form(runs, finals, s, team) -> dict:
    r, prev = runs.get((s, team)), finals.get((s - 1, team))
    out = {"games": r.w["pf"] if r else 0.0}
    for k in STATS:
        cur, wc = (r.mean(k), r.w[k]) if r else (None, 0.0)
        pv = prev.get(k) if prev else None
        out[k] = pv if cur is None else cur if pv is None else (cur * wc + pv * PRIOR_GAMES) / (wc + PRIOR_GAMES)
    return out


def build(garbage: bool = False) -> list[dict]:
    adv, pri = _adv(garbage), _priors()
    runs, finals, out = {}, {}, []
    for g in cs._games():
        if g.get("seasonType") not in ("regular", "postseason"):
            continue
        s, h, a = g["season"], g["homeTeamId"], g["awayTeamId"]
        hs_, as_ = g.get("homeScore"), g.get("awayScore")
        if hs_ is None or as_ is None:
            continue
        gid, names = str(g["id"]), {h: g["homeTeam"], a: g["awayTeam"]}
        conf = {h: g.get("homeConference"), a: g.get("awayConference")}
        cls = {h: g.get("homeClassification"), a: g.get("awayClassification")}
        ln = cs._line(g)
        if ln is not None:
            spread, tot = float(ln["spread"]), float(ln["overUnder"])
            so, to = ln.get("spreadOpen"), ln.get("overUnderOpen")
            imp = {h: tot / 2 - spread / 2, a: tot / 2 + spread / 2}
            f = {t: _form(runs, finals, s, t) for t in (h, a)}
            neutral = int(bool(g.get("neutralSite")))
            power = [c in POWER or names[t] == "Notre Dame" for t, c in conf.items()]
            tier = "fcs" if "fcs" in cls.values() else "power" if any(power) else "g5"
            for t, o, pts in ((h, a, hs_), (a, h, as_)):
                ft, fo = f[t], f[o]
                row = {"event_id": gid, "season": s, "week": g["week"], "tier": tier, "team": t, "opp": o, "home": int(t == h and not neutral),
                       "neutral": neutral, "implied": imp[t], "points": float(pts), "spread": -spread, "total": tot, "games": ft["games"],
                       "opp_games": fo["games"], "_is_home": int(t == h),
                       "open_margin": None if so is None else -float(so), "open_total": None if to is None else float(to),
                       "o_pts": ft["pf"], "d_pts": ft["pa"], "opp_o_pts": fo["pf"], "opp_d_pts": fo["pa"],
                       "o_ppa": ft["oppa"], "d_ppa": ft["dppa"], "o_sr": ft["osr"], "d_sr": ft["dsr"], "o_pl": ft["opl"], "d_pl": ft["dpl"],
                       "opp_o_ppa": fo["oppa"], "opp_d_ppa": fo["dppa"], "opp_o_sr": fo["osr"], "opp_d_sr": fo["dsr"],
                       "opp_o_pl": fo["opl"], "opp_d_pl": fo["dpl"]}
                row["ppa_x_plays"] = None if None in (ft["oppa"], ft["opl"], fo["dpl"]) else ft["oppa"] * (ft["opl"] + fo["dpl"]) / 2
                fade = 4.0 / (4.0 + ft["games"])
                for who, tm in (("", names[t]), ("opp_", names[o])):
                    for k in ("sp_o", "sp_d", "ret", "tal"):
                        d, low = pri[s][k]
                        row[who + k] = fade * d.get(tm, low)
                out.append(row)
        for t, o, pf, pa_ in ((h, a, hs_, as_), (a, h, as_, hs_)):
            r = runs.setdefault((s, t), _Run())
            r.add("pf", float(pf))
            r.add("pa", float(pa_))
            st = adv.get((gid, names[t]))
            if st:
                for k in ("oppa", "dppa", "osr", "dsr", "opl", "dpl"):
                    r.add(k, st[k])
            finals[(s, t)] = {k: r.mean(k) for k in STATS}
    return out


def _vec(r, feats):
    x = [r.get(k) for k in feats]
    return None if any(v is None for v in x) else [float(v) for v in x]


def _pairs(rows, own):
    by = defaultdict(dict)
    for r, o in zip(rows, own):
        by[r["event_id"]]["home" if r["_is_home"] else "away"] = (r, o)
    out = []
    for d in by.values():
        if "home" in d and "away" in d:
            (h, oh), (a, oa) = d["home"], d["away"]
            out.append({"season": h["season"], "week": h["week"], "tier": h["tier"], "total": h["total"], "own_total": oh + oa,
                        "actual_total": h["points"] + a["points"], "mkt_margin": h["spread"], "own_margin": oh - oa,
                        "actual_margin": h["points"] - a["points"], "open_margin": h["open_margin"], "open_total": h["open_total"]})
    return out


def walk_forward(rows, feats, min_games: float = 2.0, test_filter=None) -> dict:
    """Research 16's walk-forward with a chosen feature list. test_filter(row) limits which test rows are scored (T3: weeks 1-4)."""
    use = [r for r in rows if min(r["games"], r["opp_games"]) >= min_games and _vec(r, feats) is not None]
    out = {"team": [], "game": [], "weights": []}
    for s in TESTS:
        tr, te = [r for r in use if r["season"] < s], [r for r in use if r["season"] == s]
        if test_filter:
            te = [r for r in te if test_filter(r)]
        itr, ite = [r for r in tr if r["season"] < s - 1], [r for r in tr if r["season"] == s - 1]
        model, inner = (ridge([_vec(r, feats) for r in x], [r["points"] for r in x], LAM) for x in (tr, itr))
        own_i = [predict(inner, _vec(r, feats)) for r in ite]
        gi = _pairs(ite, own_i)
        w = {"team": fit_weight(own_i, [r["implied"] for r in ite], [r["points"] for r in ite]),
             "total": fit_weight([a["own_total"] for a in gi], [a["total"] for a in gi], [a["actual_total"] for a in gi]),
             "side": fit_weight([a["own_margin"] for a in gi], [a["mkt_margin"] for a in gi], [a["actual_margin"] for a in gi])}
        out["weights"].append({"season": s, **{k: round(v, 3) for k, v in w.items()}})
        own = [predict(model, _vec(r, feats)) for r in te]
        for r, o in zip(te, own):
            out["team"].append({"season": s, "week": r["week"], "tier": r["tier"], "mkt": r["implied"], "own": o,
                                "blend": r["implied"] + w["team"] * (o - r["implied"]), "y": r["points"]})
        for a in _pairs(te, own):
            a["blend_total"] = a["total"] + w["total"] * (a["own_total"] - a["total"])
            a["blend_margin"] = a["mkt_margin"] + w["side"] * (a["own_margin"] - a["mkt_margin"])
            out["game"].append(a)
    return out


def market_rows(res) -> dict:
    """Per market: list of (season, week, tier, market, own, blend, actual, open)."""
    return {
        "team": [(t["season"], t["week"], t["tier"], t["mkt"], t["own"], t["blend"], t["y"], None) for t in res["team"]],
        "total": [(g["season"], g["week"], g["tier"], g["total"], g["own_total"], g["blend_total"], g["actual_total"], g["open_total"])
                  for g in res["game"]],
        "side": [(g["season"], g["week"], g["tier"], g["mkt_margin"], g["own_margin"], g["blend_margin"], g["actual_margin"], g["open_margin"])
                 for g in res["game"]],
    }


def mse(rows, i):
    return sum((r[i] - r[6]) ** 2 for r in rows) / len(rows) if rows else float("nan")


def bets(rows, thr, at: int = 3):
    """Bet at column `at` (3 = close, 7 = opener) where our own number is `thr`+ away; returns wins, losses, average move toward us."""
    w = l = 0
    moves = []
    for r in rows:
        line = r[at]
        if line is None:
            continue
        d = r[4] - line
        if abs(d) < thr:
            continue
        sgn = 1 if d > 0 else -1
        res = (r[6] - line) * sgn
        if at == 7:
            moves.append((r[3] - line) * sgn)
        if res > 0:
            w += 1
        elif res < 0:
            l += 1
    return w, l, (sum(moves) / len(moves) if moves else None)


def summary(res) -> dict:
    out = {"weights": res["weights"], "markets": {}}
    for m, rows in market_rows(res).items():
        by = {}
        for s in TESTS:
            rs = [r for r in rows if r[0] == s]
            w, l, _ = bets(rs, THRESH[m])
            by[s] = {"n": len(rs), "mse_mkt": round(mse(rs, 3), 2), "mse_own": round(mse(rs, 4), 2), "mse_blend": round(mse(rs, 5), 2), "bets": f"{w}-{l}"}
        w, l, _ = bets(rows, THRESH[m])
        out["markets"][m] = {"n": len(rows), "mse_mkt": round(mse(rows, 3), 3), "mse_own": round(mse(rows, 4), 3),
                             "mse_blend": round(mse(rows, 5), 3), "bets": (w, l), "by_season": by}
    return out
