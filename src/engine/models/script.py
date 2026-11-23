"""NFL game script and team points (PLAYBOOK.md steps 1 to 3; decision 0018).

For every team in every game this builds, from play-by-play of EARLIER games only:
  * offense and defense form: EPA per play, success rate, points per drive (the opponent's defensive form is a separate input, so the
    regression weighs one against the other; form is not yet adjusted for the schedule each team faced);
  * pace: drives per game (own and allowed);
  * pass rate over expected in neutral situations (score within 7, first three quarters);
  * the game's situation: home, starting quarterback different from the team's usual starter, wind and rain at kickoff.

It then predicts each team's points. Two numbers are reported:
  * `own`: our number from the handicap alone (no market input);
  * `blend`: the market's implied team points moved toward `own` by a weight fitted on earlier seasons only.

The weight is the honest answer to "how much should our number count against the market" (PLAYBOOK step 4). It is fitted per market
(team total, game total, side) on seasons before the test season, and reported on seasons it never saw.

Form is a decayed average of this season's earlier games (newest weigh most) plus last season's average counted as `PRIOR_GAMES` games.
Not yet done (PLAYBOOK step 1): half weight for games against the best and worst units, and schedule adjustment.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

import duckdb

from engine import config

RAW = config.DATA / "raw" / "nflverse"
GAMES_CSV = config.DATA / "raw" / "nflverse_games.csv"
DECAY = 0.85
PRIOR_GAMES = 3.0
STATS = ("epa", "sr", "ppd", "drives", "proe")
TD_POINTS = 6.95


def team_games(first: int = 2015, last: int = 2026) -> list[dict]:
    """One row per team per game: what the offense did (and, from the opponent's row, what the defense allowed)."""
    con = duckdb.connect()
    files = ", ".join(f"'{RAW / f'pbp_{y}.parquet'}'" for y in range(first, last + 1) if (RAW / f"pbp_{y}.parquet").exists())
    rows = con.sql(f"""
        WITH p AS (SELECT * FROM read_parquet([{files}], union_by_name=true)
                   WHERE posteam IS NOT NULL AND season_type IN ('REG','POST')),
        plays AS (
          SELECT game_id, season, week, posteam AS team, defteam AS opp,
                 avg(epa) FILTER (WHERE (pass=1 OR rush=1) AND epa IS NOT NULL) AS epa,
                 avg(success) FILTER (WHERE (pass=1 OR rush=1) AND success IS NOT NULL) AS sr,
                 avg(pass_oe) FILTER (WHERE pass_oe IS NOT NULL AND abs(score_differential) <= 7 AND qtr <= 3) AS proe,
                 count(*) FILTER (WHERE pass=1 OR rush=1) AS n
          FROM p GROUP BY 1,2,3,4,5),
        drives AS (
          SELECT game_id, posteam AS team, count(*) AS drives,
                 sum(CASE fixed_drive_result WHEN 'Touchdown' THEN {TD_POINTS} WHEN 'Field goal' THEN 3 ELSE 0 END) AS dpts
          FROM (SELECT DISTINCT game_id, posteam, fixed_drive, fixed_drive_result FROM p WHERE fixed_drive IS NOT NULL) GROUP BY 1,2)
        SELECT plays.*, drives.drives, drives.dpts FROM plays JOIN drives USING (game_id, team)
        ORDER BY season, week, game_id
    """).fetchall()
    cols = ("game_id", "season", "week", "team", "opp", "epa", "sr", "proe", "n", "drives", "dpts")
    out = []
    for r in rows:
        d = dict(zip(cols, r))
        for k in ("epa", "sr", "proe", "dpts"):
            d[k] = None if d[k] is None else float(d[k])
        d["ppd"] = (d["dpts"] / d["drives"]) if d["drives"] else None
        out.append(d)
    return out


def _games_meta() -> dict[str, dict]:
    con = duckdb.connect()
    rows = con.sql(f"""SELECT game_id, season, week, game_type, home_team, away_team, home_score, away_score, spread_line, total_line,
                              home_qb_id, away_qb_id, roof, stadium_id, gameday, gametime, location
                       FROM read_csv_auto('{GAMES_CSV}') WHERE season >= 2015""").fetchall()
    cols = ("game_id", "season", "week", "game_type", "home", "away", "hs", "as_", "spread", "total", "hqb", "aqb", "roof", "stadium", "day", "time", "location")
    return {r[0]: dict(zip(cols, r)) for r in rows}


@dataclass
class Form:
    """Running decayed averages for one team-season, offense and defense."""
    w: float = 0.0
    off: dict = field(default_factory=lambda: defaultdict(float))
    dfn: dict = field(default_factory=lambda: defaultdict(float))
    qbs: dict = field(default_factory=lambda: defaultdict(int))

    def add(self, off: dict, dfn: dict, weight: float = 1.0):
        self.w = self.w * DECAY + weight
        for k in STATS:
            if off.get(k) is not None:
                self.off[k] = self.off[k] * DECAY + weight * off[k]
            if dfn.get(k) is not None:
                self.dfn[k] = self.dfn[k] * DECAY + weight * dfn[k]

    def mean(self, side: str, k: str):
        d = self.off if side == "off" else self.dfn
        return d[k] / self.w if self.w else None


def build_features(first_test: int = 2017) -> list[dict]:
    """For every game from 2016 on: both teams' pre-game form, situation, the market's implied team points and the real points."""
    tg = team_games()
    meta = _games_meta()
    by_game = defaultdict(dict)
    for r in tg:
        by_game[r["game_id"]][r["team"]] = r
    order = sorted(by_game, key=lambda g: (meta[g]["season"], meta[g]["week"] if meta[g]["game_type"] == "REG" else 100 + meta[g]["week"], g) if g in meta else (0, 0, g))
    forms: dict[tuple[int, str], Form] = {}
    season_avg: dict[tuple[int, str], dict] = {}
    league: dict[int, dict] = defaultdict(lambda: defaultdict(list))
    wind = _weather()
    out = []
    for gid in order:
        m = meta.get(gid)
        if m is None or len(by_game[gid]) != 2:
            continue
        s = m["season"]
        rows = by_game[gid]
        feats = {}
        for team, opp in ((m["home"], m["away"]), (m["away"], m["home"])):
            if team not in rows:
                break
            feats[team] = _pre(forms, season_avg, league, s, team)
            feats[team]["opp_pre"] = _pre(forms, season_avg, league, s, opp)
        if len(feats) == 2 and m["spread"] is not None and m["total"] is not None and m["hs"] is not None:
            imp_h = m["total"] / 2 + m["spread"] / 2        # nflverse spread_line: + = home favored
            imp_a = m["total"] / 2 - m["spread"] / 2
            w = wind.get(gid, (None, None))
            for team, opp, imp, pts, qb, home in ((m["home"], m["away"], imp_h, m["hs"], m["hqb"], 1), (m["away"], m["home"], imp_a, m["as_"], m["aqb"], 0)):
                f, fo = feats[team], feats[opp]
                usual = max(forms[(s, team)].qbs.items(), key=lambda x: x[1])[0] if (s, team) in forms and forms[(s, team)].qbs else None
                out.append({"game_id": gid, "season": s, "week": m["week"], "team": team, "opp": opp, "home": home, "neutral": int(m["location"] == "Neutral"),
                            "implied": imp, "points": pts, "spread": m["spread"], "total": m["total"],
                            "backup_qb": int(usual is not None and qb is not None and qb != usual),
                            "wind": w[0], "rain": w[1], "dome": int((m["roof"] or "") in ("dome", "closed")),
                            **{f"o_{k}": f["off"].get(k) for k in STATS}, **{f"d_{k}": fo["dfn"].get(k) for k in STATS},
                            "o_drives_opp": fo["off"].get("drives"), "games": f["games"]})
        # update forms after the game (no look-ahead)
        for team, opp in ((m["home"], m["away"]), (m["away"], m["home"])):
            if team not in rows or opp not in rows:
                continue
            o, d = rows[team], rows[opp]
            off = {k: o.get(k) for k in STATS}
            dfn = {"epa": d["epa"], "sr": d["sr"], "ppd": d["ppd"], "drives": d["drives"], "proe": None}
            fm = forms.setdefault((s, team), Form())
            fm.add(off, dfn)
            q = m["hqb"] if team == m["home"] else m["aqb"]
            if q:
                fm.qbs[q] += 1
            for k in STATS:
                if off.get(k) is not None:
                    league[s][k].append(off[k])
            season_avg[(s, team)] = {"off": {k: fm.mean("off", k) for k in STATS}, "dfn": {k: fm.mean("dfn", k) for k in STATS}}
    return out


def _pre(forms, season_avg, league, s, team) -> dict:
    """Pre-game form: this season's decayed average blended with last season's final average (worth PRIOR_GAMES games)."""
    fm = forms.get((s, team))
    prev = season_avg.get((s - 1, team))
    lg = {k: (sum(v) / len(v)) for k, v in league[s - 1].items()} if league.get(s - 1) else {}
    res = {"off": {}, "dfn": {}, "games": 0 if fm is None else fm.w}
    for side in ("off", "dfn"):
        for k in STATS:
            cur = fm.mean(side, k) if fm else None
            pv = (prev or {}).get(side, {}).get(k) if prev else None
            if pv is None:
                pv = lg.get(k)
            wc = fm.w if fm else 0.0
            if cur is None and pv is None:
                res[side][k] = None
            elif cur is None:
                res[side][k] = pv
            elif pv is None:
                res[side][k] = cur
            else:
                res[side][k] = (cur * wc + pv * PRIOR_GAMES) / (wc + PRIOR_GAMES)
    return res


def _weather() -> dict[str, tuple[float | None, float | None]]:
    """Wind (mph) and rain (mm) at kickoff for open-air games, from the cached Open-Meteo archive the wind model uses."""
    from engine.models import wind_totals
    try:
        gs = wind_totals.outdoor_games(2015)
        wind_totals.attach_weather(gs)
        return {g.game_id: (g.wind, g.precip) for g in gs}
    except Exception:
        return {}


FEATURES = ("o_epa", "o_sr", "o_ppd", "o_drives", "o_proe", "d_epa", "d_sr", "d_ppd", "d_drives", "o_drives_opp",
            "home", "backup_qb", "wind6", "rain")


def vector(r: dict) -> list[float] | None:
    x = []
    for k in FEATURES:
        if k == "wind6":
            v = max(0.0, (r["wind"] or 0.0) - 6.0) if not r["dome"] else 0.0
        elif k == "rain":
            v = min(r["rain"] or 0.0, 10.0) if not r["dome"] else 0.0
        else:
            v = r.get(k)
        if v is None:
            return None
        x.append(float(v))
    return x


def ridge(X: list[list[float]], y: list[float], lam: float) -> tuple[list[float], list[float], list[float]]:
    """Ridge regression on standardised features. Returns (coef, means, sds); intercept is coef[0]."""
    n, p = len(X), len(X[0])
    mu = [sum(r[j] for r in X) / n for j in range(p)]
    sd = [max(1e-9, math.sqrt(sum((r[j] - mu[j]) ** 2 for r in X) / n)) for j in range(p)]
    Z = [[1.0] + [(r[j] - mu[j]) / sd[j] for j in range(p)] for r in X]
    k = p + 1
    A = [[sum(Z[i][a] * Z[i][b] for i in range(n)) + (lam if a == b and a > 0 else 0.0) for b in range(k)] for a in range(k)]
    bvec = [sum(Z[i][a] * y[i] for i in range(n)) for a in range(k)]
    return _solve(A, bvec), mu, sd


def _solve(A, b):
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[piv] = M[piv], M[c]
        for r in range(n):
            if r != c and M[c][c]:
                f = M[r][c] / M[c][c]
                M[r] = [M[r][j] - f * M[c][j] for j in range(n + 1)]
    return [M[i][n] / M[i][i] for i in range(n)]


def predict(model, x: list[float]) -> float:
    coef, mu, sd = model
    return coef[0] + sum(coef[j + 1] * (x[j] - mu[j]) / sd[j] for j in range(len(x)))


def fit_weight(own: list[float], mkt: list[float], y: list[float]) -> float:
    """Least-squares weight w in y ≈ mkt + w (own - mkt), clipped to [0, 1]."""
    num = sum((o - m) * (t - m) for o, m, t in zip(own, mkt, y))
    den = sum((o - m) ** 2 for o, m in zip(own, mkt))
    return max(0.0, min(1.0, num / den)) if den else 0.0


def walk_forward(rows: list[dict] | None = None, first_test: int = 2019, last_test: int = 2026, min_games: float = 2.0, lam: float = 50.0) -> dict:
    """For each test season: fit the points model and the blend weights on earlier seasons (from 2016), score on the test season."""
    rows = rows if rows is not None else build_features()
    usable = [r for r in rows if r["season"] >= 2016 and r["games"] >= min_games and vector(r) is not None]
    out = {"seasons": [], "team": [], "game": []}
    for s in range(first_test, last_test + 1):
        tr = [r for r in usable if r["season"] < s]
        te = [r for r in usable if r["season"] == s]
        if not te or len(tr) < 500:
            continue
        model = ridge([vector(r) for r in tr], [r["points"] for r in tr], lam)
        # blend weights fitted on the training seasons' own in-sample predictions would be biased: fit them on the last training season
        # with a model trained on the seasons before it (one-step walk-forward inside the training window)
        inner_tr = [r for r in tr if r["season"] < s - 1]
        inner_te = [r for r in tr if r["season"] == s - 1]
        inner = ridge([vector(r) for r in inner_tr], [r["points"] for r in inner_tr], lam) if len(inner_tr) > 500 else model
        own_i = [predict(inner, vector(r)) for r in inner_te]
        w_team = fit_weight(own_i, [r["implied"] for r in inner_te], [r["points"] for r in inner_te])
        g_i = _pairs(inner_te, own_i)
        w_total = fit_weight([a["own_total"] for a in g_i], [a["total"] for a in g_i], [a["actual_total"] for a in g_i])
        w_side = fit_weight([a["own_margin"] for a in g_i], [a["mkt_margin"] for a in g_i], [a["actual_margin"] for a in g_i])
        own = [predict(model, vector(r)) for r in te]
        for r, o in zip(te, own):
            out["team"].append({"season": s, "implied": r["implied"], "own": o, "blend": r["implied"] + w_team * (o - r["implied"]), "points": r["points"]})
        for a in _pairs(te, own):
            a.update(season=s, blend_total=a["total"] + w_total * (a["own_total"] - a["total"]),
                     blend_margin=a["mkt_margin"] + w_side * (a["own_margin"] - a["mkt_margin"]))
            out["game"].append(a)
        out["seasons"].append({"season": s, "w_team": round(w_team, 3), "w_total": round(w_total, 3), "w_side": round(w_side, 3), "n_team": len(te)})
    return out


def _pairs(rows: list[dict], own: list[float]) -> list[dict]:
    by = defaultdict(dict)
    for r, o in zip(rows, own):
        by[r["game_id"]]["home" if r["home"] else "away"] = (r, o)
    out = []
    for gid, d in by.items():
        if "home" not in d or "away" not in d:
            continue
        (h, oh), (a, oa) = d["home"], d["away"]
        out.append({"game_id": gid, "total": h["total"], "own_total": oh + oa, "actual_total": h["points"] + a["points"],
                    "mkt_margin": h["spread"], "own_margin": oh - oa, "actual_margin": h["points"] - a["points"]})
    return out


def summary(res: dict) -> dict:
    """Squared error of market, own and blend, and betting records at the market number where the blend disagrees."""
    def mse(xs, k, t):
        return sum((x[k] - x[t]) ** 2 for x in xs) / len(xs) if xs else None

    def rec(xs, pred, mkt, act, thr):
        w = l = 0
        for x in xs:
            d = x[pred] - x[mkt]
            if abs(d) < thr:
                continue
            r = (x[act] - x[mkt]) * (1 if d > 0 else -1)
            w += r > 0
            l += r < 0
        return w, l

    T, G = res["team"], res["game"]
    return {
        "team": {"n": len(T), "mse_market": mse(T, "implied", "points"), "mse_own": mse(T, "own", "points"), "mse_blend": mse(T, "blend", "points"),
                 "bets": {t: rec(T, "own", "implied", "points", t) for t in (1.5, 2.5, 3.5)}},
        "total": {"n": len(G), "mse_market": mse(G, "total", "actual_total"), "mse_own": mse(G, "own_total", "actual_total"),
                  "mse_blend": mse(G, "blend_total", "actual_total"), "bets": {t: rec(G, "own_total", "total", "actual_total", t) for t in (2.0, 3.0, 4.0)}},
        "side": {"n": len(G), "mse_market": mse(G, "mkt_margin", "actual_margin"), "mse_own": mse(G, "own_margin", "actual_margin"),
                 "mse_blend": mse(G, "blend_margin", "actual_margin"), "bets": {t: rec(G, "own_margin", "mkt_margin", "actual_margin", t) for t in (2.0, 3.0, 4.0)}},
        "weights": res["seasons"],
    }
