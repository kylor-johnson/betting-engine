"""College matchup and luck blocks for the research agent (decision 0034, research 23 item 6). Context only, never a reason for a pick.

From the cached CollegeFootballData per-game advanced stats (`cfbd_adv_<season>.json`, garbage time removed) and the cached games, this
season only. Per team, with ranks among FBS teams (rank 1 = best for that unit):
- offense and defense expected points added (PPA) per play and success rate, season and last 4 games;
- plays per game run and faced (tempo);
- schedule toughness: the average net PPA per play of the opponents faced (rank 1 = hardest);
- luck: points per game scored and allowed minus what the team's own per-play efficiency and plays would predict (a least-squares fit across
  FBS teams this season). Positive on offense or negative on defense = scoring has run ahead of the play-by-play.
"""
from __future__ import annotations

import json
from collections import defaultdict

from engine.models import college_script as cs

HOW_TO_READ = ("Context only: every model built from numbers like these failed against the closing line (research 14, 16, 23). Rank 1 is "
               "best for that unit among FBS teams, except plays: rank 1 = most plays run, or fewest faced; plays exclude garbage time. 'last4' is "
               "the last four games; schedule rank 1 = hardest opponents; luck = points per game above (+) or below (-) what the team's "
               "per-play efficiency and plays predict.")


def _fit(xs: list[tuple[float, float]], ys: list[float]) -> tuple[float, float, float]:
    """Least squares y = a + b*x1 + c*x2 (two inputs), solved directly."""
    n = len(xs)
    if n < 10:
        return (sum(ys) / n if n else 0.0, 0.0, 0.0)
    m1, m2, my = (sum(x[0] for x in xs) / n, sum(x[1] for x in xs) / n, sum(ys) / n)
    s11 = sum((x[0] - m1) ** 2 for x in xs)
    s22 = sum((x[1] - m2) ** 2 for x in xs)
    s12 = sum((x[0] - m1) * (x[1] - m2) for x in xs)
    s1y = sum((x[0] - m1) * (y - my) for x, y in zip(xs, ys))
    s2y = sum((x[1] - m2) * (y - my) for x, y in zip(xs, ys))
    det = s11 * s22 - s12 ** 2
    if abs(det) < 1e-12:
        return (my, 0.0, 0.0)
    b = (s1y * s22 - s2y * s12) / det
    c = (s2y * s11 - s1y * s12) / det
    return (my - b * m1 - c * m2, b, c)


def _rank(vals: dict, key: str, high_good: bool) -> dict:
    order = sorted((t for t in vals if vals[t].get(key) is not None), key=lambda t: vals[t][key], reverse=high_good)
    return {t: i + 1 for i, t in enumerate(order)}


def season_blocks(games: list[dict], adv: dict, season: int) -> dict[str, dict]:
    """team id (str) -> {'matchup': {...}, 'luck': {...}} for FBS teams with 2+ games this season."""
    per = defaultdict(list)          # team id -> [(week, stats, points for, points against, opp id)]
    fbs = set()
    for g in sorted(games, key=lambda g: (g.get("startDate") or "", g["id"])):
        if g.get("season") != season or g.get("homeScore") is None or g.get("awayScore") is None:
            continue
        for t, name, cls, o, pf, pa in ((g["homeTeamId"], g.get("homeTeam"), g.get("homeClassification"), g["awayTeamId"], g["homeScore"], g["awayScore"]),
                                         (g["awayTeamId"], g.get("awayTeam"), g.get("awayClassification"), g["homeTeamId"], g["awayScore"], g["homeScore"])):
            st = adv.get((str(g["id"]), name))
            if cls == "fbs":
                fbs.add(t)
            if st:
                per[t].append((g.get("week"), st, float(pf), float(pa), o))
    agg = {}
    for t, rows in per.items():
        if t not in fbs or len(rows) < 2:
            continue
        def avg(k, rs=rows):
            return sum(r[1][k] for r in rs) / len(rs)
        last4 = rows[-4:]
        agg[t] = {"games": len(rows), "o_ppa": avg("oppa"), "d_ppa": avg("dppa"), "o_sr": avg("osr"), "d_sr": avg("dsr"),
                  "o_plays": avg("opl"), "d_plays": avg("dpl"), "o_ppa_last4": avg("oppa", last4), "d_ppa_last4": avg("dppa", last4),
                  "ppg": sum(r[2] for r in rows) / len(rows), "papg": sum(r[3] for r in rows) / len(rows), "opps": [r[4] for r in rows]}
    for t, a in agg.items():
        nets = [agg[o]["o_ppa"] - agg[o]["d_ppa"] for o in a["opps"] if o in agg]
        a["sched"] = sum(nets) / len(nets) if nets else None
    fo = _fit([(a["o_ppa"], a["o_plays"]) for a in agg.values()], [a["ppg"] for a in agg.values()])
    fd = _fit([(a["d_ppa"], a["d_plays"]) for a in agg.values()], [a["papg"] for a in agg.values()])
    ranks = {k: _rank(agg, k, hg) for k, hg in (("o_ppa", True), ("d_ppa", False), ("o_sr", True), ("d_sr", False), ("o_plays", True),
                                                 ("d_plays", False), ("o_ppa_last4", True), ("d_ppa_last4", False), ("sched", True))}
    out = {}
    for t, a in agg.items():
        def cell(k, digits=3):
            return None if a.get(k) is None else {"value": round(a[k], digits), "rank": ranks[k].get(t)}
        out[str(t)] = {
            "matchup": {"games": a["games"], "fbs_teams_ranked": len(agg),
                        "offense": {"ppa_per_play": cell("o_ppa"), "success_rate": cell("o_sr"), "ppa_per_play_last4": cell("o_ppa_last4"),
                                    "plays_per_game": cell("o_plays", 1)},
                        "defense": {"ppa_per_play_allowed": cell("d_ppa"), "success_rate_allowed": cell("d_sr"),
                                    "ppa_per_play_allowed_last4": cell("d_ppa_last4"), "plays_faced_per_game": cell("d_plays", 1)},
                        "schedule_toughness": cell("sched")},
            "luck": {"points_per_game": round(a["ppg"], 1), "points_allowed_per_game": round(a["papg"], 1),
                     "scoring_vs_efficiency": round(a["ppg"] - (fo[0] + fo[1] * a["o_ppa"] + fo[2] * a["o_plays"]), 1),
                     "allowed_vs_efficiency": round(a["papg"] - (fd[0] + fd[1] * a["d_ppa"] + fd[2] * a["d_plays"]), 1)},
        }
    return out


def current(season: int | None = None) -> dict[str, dict]:
    games = cs._games()
    season = season or max(g["season"] for g in games if g.get("homeScore") is not None)
    adv = {}
    p = cs.CACHE / f"cfbd_adv_{season}.json"
    if p.exists():
        adv = cs.adv_stats(json.loads(p.read_text()))
    return season_blocks(games, adv, season)
