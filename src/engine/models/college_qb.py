"""What a college starting quarterback is worth to the market (research 21; the parity cell "player value" for college).

Free CollegeFootballData only: per-game passing lines by conference (who threw the most passes = who started) and the cached closing and
opening lines. For each team-game:
  * the established starter is the passer with the most attempts in the team's EARLIER games this season, if he threw at least
    `SHARE` of them (a clear starter) over at least `MIN_PRIOR` games;
  * the game is "starter out" when someone else threw the most passes.
The market's discount: per season, team ratings are fitted on closing spreads of games where every team's established starter started
(ridge least squares, home edge); in a starter-out game, how far the closing spread sits from those ratings, in the starter's team's points.
Also: how much of that sat in the opener versus moved after it (news timing; the speed edge news picks live on).

Descriptive, not a betting model: it uses the whole season's ratings, so it measures what the market charged, which is the number the
research agent needs for an `adjustments.yaml` entry.
"""
from __future__ import annotations

import json
import time
import urllib.request
from collections import defaultdict
from statistics import mean, median

from engine import config

CFBD = "https://api.collegefootballdata.com"
CACHE = config.DATA / "raw" / "cfbd"
OUT = config.DATA / "models" / "college_qb_value.json"
CONFS = ("ACC", "AAC", "B12", "B1G", "CUSA", "Ind", "MAC", "MWC", "PAC", "SEC", "SBC")
P4 = {"ACC", "Big 12", "Big Ten", "SEC", "Pac-12"}
SEASONS = range(2021, 2027)
SHARE, MIN_PRIOR = 0.6, 2
BOOKS = ("DraftKings", "consensus", "ESPN Bet", "Bovada", "William Hill (New Jersey)")


def _get(path: str, key: str):
    req = urllib.request.Request(CFBD + path, headers={"Authorization": "Bearer " + key, "Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def passing(year: int, key: str) -> dict[int, dict]:
    """game id -> {team: (starter id, starter name, attempts, team attempts)}. Cached per season."""
    cache = CACHE / f"cfbd_passing_{year}.json"
    if cache.exists() and (year < 2026 or time.time() - cache.stat().st_mtime < 12 * 3600):
        raw = json.loads(cache.read_text())
    else:
        raw, seen = [], set()
        for st in ("regular", "postseason"):
            for c in CONFS:
                for g in _get(f"/games/players?year={year}&seasonType={st}&conference={c}&category=passing", key):
                    if g["id"] not in seen:
                        seen.add(g["id"])
                        raw.append(g)
                time.sleep(0.3)
        cache.write_text(json.dumps(raw))
    out = {}
    for g in raw:
        teams = {}
        for t in g.get("teams") or []:
            att = {}
            names = {}
            yds = {}
            for cat in t.get("categories") or []:
                for ty in cat.get("types") or []:
                    if ty.get("name") == "YDS":
                        for a in ty.get("athletes") or []:
                            try:
                                yds[a["id"]] = int(float(a["stat"]))
                            except ValueError:
                                pass
                    if ty.get("name") == "C/ATT":
                        for a in ty.get("athletes") or []:
                            try:
                                att[a["id"]] = int(str(a["stat"]).split("/")[1])
                                names[a["id"]] = a["name"]
                            except (ValueError, IndexError):
                                pass
            if att:
                sid = max(att, key=att.get)
                teams[t["team"]] = (sid, names[sid], att[sid], sum(att.values()), t.get("conference"), yds.get(sid, 0))
        out[g["id"]] = teams
    return out


def _line(g: dict):
    lines = [l for l in g.get("lines") or [] if l.get("spread") is not None]
    for b in BOOKS:
        for l in lines:
            if l.get("provider") == b:
                return l
    return lines[0] if lines else None


def _ratings(games: list[tuple[str, str, float, bool]], lam: float = 2.0) -> tuple[dict[str, float], float]:
    """Ridge fit of implied home margin = r_home - r_away + hfa (not neutral). games = (home, away, implied margin, neutral).
    Normal equations built sparsely (each game touches three columns), solved with the engine's own solver (no numpy here)."""
    from engine.models.script import _solve
    teams = sorted({t for g in games for t in g[:2]})
    ix = {t: i for i, t in enumerate(teams)}
    k = len(teams) + 1
    A = [[0.0] * k for _ in range(k)]
    b = [0.0] * k
    for h, a, m, neu in games:
        cols = [(ix[h], 1.0), (ix[a], -1.0)] + ([] if neu else [(k - 1, 1.0)])
        for i, xi in cols:
            b[i] += xi * m
            for j, xj in cols:
                A[i][j] += xi * xj
    for i in range(k - 1):
        A[i][i] += lam
    beta = _solve(A, b)
    return {t: beta[ix[t]] for t in teams}, beta[-1]


def analyse(key: str) -> dict:
    rows = []
    for year in SEASONS:
        lp = CACHE / f"cfbd_lines_{year}.json"
        if not lp.exists():
            continue
        lines = {g["id"]: g for g in json.loads(lp.read_text())}
        pas = passing(year, key)
        order = sorted((g for g in lines.values() if g["id"] in pas), key=lambda g: (g.get("startDate") or "", g["id"]))
        hist = defaultdict(lambda: defaultdict(int))     # team -> starter id -> attempts in earlier games
        ngames = defaultdict(int)
        prior_att = defaultdict(lambda: defaultdict(int))
        prior_yds = defaultdict(lambda: defaultdict(int))
        tagged = []
        for g in order:
            l = _line(g)
            teams = pas[g["id"]]
            info = {}
            for side, team in (("home", g["homeTeam"]), ("away", g["awayTeam"])):
                t = teams.get(team)
                if not t:
                    continue
                h = hist[team]
                tot = sum(h.values())
                est = max(h, key=h.get) if h else None
                clear = est is not None and ngames[team] >= MIN_PRIOR and h[est] >= SHARE * tot
                out = clear and t[0] != est
                ypa = (prior_yds[team][est] / prior_att[team][est]) if est is not None and prior_att[team][est] else None
                info[side] = {"team": team, "out": bool(out), "clear": bool(clear), "starter": t[1], "est_ypa": ypa,
                              "backup_prior_att": prior_att[team][t[0]] if out else None, "conf": g.get(f"{side}Conference")}
            for team, t in teams.items():
                hist[team][t[0]] += t[2]
                prior_att[team][t[0]] += t[2]
                prior_yds[team][t[0]] += t[5]
                ngames[team] += 1
            if l and l.get("spread") is not None and g.get("homeClassification") == "fbs" and g.get("awayClassification") == "fbs":
                tagged.append((g, l, info))
        clean = [(g["homeTeam"], g["awayTeam"], -float(l["spread"]), bool(g.get("neutralSite"))) for g, l, info in tagged
                 if all(v["clear"] and not v["out"] for v in info.values()) and len(info) == 2]
        if len(clean) < 200:
            continue
        r, hfa = _ratings(clean)
        for g, l, info in tagged:
            h, a = g["homeTeam"], g["awayTeam"]
            if h not in r or a not in r:
                continue
            pred = r[h] - r[a] + (0 if g.get("neutralSite") else hfa)
            close = -float(l["spread"])
            opn = -float(l["spreadOpen"]) if l.get("spreadOpen") is not None else None
            for side, sign in (("home", 1), ("away", -1)):
                v = info.get(side)
                if not v or not v["clear"]:
                    continue
                other = info.get("away" if side == "home" else "home")
                if other and other["out"]:
                    continue                      # both starters out: not one team's discount
                rows.append({"season": year, "team": v["team"], "out": v["out"], "conf": v["conf"],
                             "resid_close": sign * (close - pred), "resid_open": None if opn is None else sign * (opn - pred),
                             "backup_prior_att": v["backup_prior_att"], "est_ypa": v["est_ypa"]})
    return summarize(rows)


def _stats(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    m = mean(xs)
    sd = (sum((x - m) ** 2 for x in xs) / max(1, len(xs) - 1)) ** 0.5
    return {"n": len(xs), "mean": round(m, 2), "median": round(median(xs), 2), "se": round(sd / len(xs) ** 0.5, 2)}


def summarize(rows: list[dict]) -> dict:
    ins = [r for r in rows if not r["out"]]
    outs = [r for r in rows if r["out"]]
    base = mean(r["resid_close"] for r in ins) if ins else 0.0
    def disc(sel):
        return _stats([base - r["resid_close"] for r in sel])
    def moved(sel):
        xs = [r["resid_open"] - r["resid_close"] for r in sel if r["resid_open"] is not None]
        return _stats(xs)
    p4 = [r for r in outs if r["conf"] in P4]
    g5 = [r for r in outs if r["conf"] not in P4]
    green = [r for r in outs if (r["backup_prior_att"] or 0) < 30]
    used = [r for r in outs if (r["backup_prior_att"] or 0) >= 30]
    ypas = sorted(r["est_ypa"] for r in outs if r["est_ypa"])
    cut1, cut2 = (ypas[len(ypas) // 3], ypas[2 * len(ypas) // 3]) if len(ypas) >= 30 else (0, 0)
    tiers = {f"low (under {cut1:.1f} yards an attempt)": [r for r in outs if r["est_ypa"] and r["est_ypa"] < cut1],
             f"middle ({cut1:.1f} to {cut2:.1f})": [r for r in outs if r["est_ypa"] and cut1 <= r["est_ypa"] < cut2],
             f"high ({cut2:.1f} and up)": [r for r in outs if r["est_ypa"] and r["est_ypa"] >= cut2]}
    return {"discount_by_missing_starter_ypa": {k: disc(v) for k, v in tiers.items()},
            "team_games_starter_in": len(ins), "team_games_starter_out": len(outs),
            "discount_points_all": disc(outs), "discount_power4": disc(p4), "discount_group5": disc(g5),
            "discount_backup_under_30_prior_attempts": disc(green), "discount_backup_30_plus": disc(used),
            "moved_after_open_starter_out": moved(outs), "moved_after_open_starter_in": moved(ins),
            "by_season": {s: disc([r for r in outs if r["season"] == s]) for s in sorted({r["season"] for r in outs})}}


if __name__ == "__main__":
    res = analyse(config.load_env()["CFBD_API_KEY"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
