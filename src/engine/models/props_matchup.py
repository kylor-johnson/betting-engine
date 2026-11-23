"""Matchup layer for NFL props from free charting data (PLAYBOOK step 3 item 1; research 17; decision 0023).

Coverage type (man or zone) is free only for 2023 (nflverse participation), so it cannot be tested on later seasons or used live. FTN charting
(nflverse, free, 2022 on) has blitzers and defenders in the box on every play, so the matchup terms are:
  * passing yards: a quarterback's yards per attempt against the blitz and without it (his earlier games), weighted by how often THIS defense
    blitzes, against how often he has faced the blitz;
  * rushing yards: a runner's yards per carry against a stacked box (8+) and a light one, weighted by how often this defense stacks the box.
The ratio (expected yards per play this game / his usual yards per play) multiplies the props projection, raised to a power `g` fitted on 2023
and kept only if it lowers 2024-2026 squared error by 0.1% or more. Everything uses earlier games only. Cached per season.
"""
from __future__ import annotations

import json
from collections import defaultdict

import duckdb

from engine import config
from engine.models import props

RAW = config.DATA / "raw" / "nflverse"
CACHE = config.DATA / "models"
FIRST = 2022
SHRINK_PLAYS = 80          # player splits shrink toward his overall rate by this many plays
SHRINK_DEF = 150           # defense rates shrink toward the league by this many plays
GRID = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5)
MIN_GAIN = 0.001
STATS = {"passing_yards": "pass", "rushing_yards": "rush"}


def plays(last: int) -> list[tuple]:
    files = [(RAW / f"pbp_{y}.parquet", RAW / "ftn" / f"ftn_charting_{y}.parquet") for y in range(FIRST, last + 1)]
    files = [(p, f) for p, f in files if p.exists() and f.exists()]
    pf = ", ".join(f"'{p}'" for p, _ in files)
    ff = ", ".join(f"'{f}'" for _, f in files)
    return duckdb.connect().execute(f"""
        SELECT p.season, p.week, p.game_id, p.defteam,
               CASE WHEN p.pass_attempt = 1 AND coalesce(p.sack, 0) = 0 THEN 'pass' WHEN p.rush_attempt = 1 THEN 'rush' END AS kind,
               CASE WHEN p.pass_attempt = 1 THEN p.passer_player_id ELSE p.rusher_player_id END AS pid,
               coalesce(CASE WHEN p.pass_attempt = 1 THEN p.passing_yards ELSE p.rushing_yards END, 0) AS yds,
               CASE WHEN p.pass_attempt = 1 THEN coalesce(f.n_blitzers, 0) > 0 ELSE coalesce(f.n_defense_box, 0) >= 8 END AS hard
        FROM read_parquet([{pf}], union_by_name=true) p
        JOIN read_parquet([{ff}], union_by_name=true) f ON f.nflverse_game_id = p.game_id AND f.nflverse_play_id = p.play_id
        WHERE p.season_type IN ('REG', 'POST') AND (p.pass_attempt = 1 OR p.rush_attempt = 1)
        ORDER BY p.season, p.week, p.game_id""").fetchall()


class State:
    """Running totals, updated game by game (no look-ahead)."""

    def __init__(self):
        self.pl = defaultdict(lambda: {"pass": [0, 0.0, 0, 0.0], "rush": [0, 0.0, 0, 0.0]})   # n_hard, yds_hard, n_easy, yds_easy
        self.df = defaultdict(lambda: {"pass": [0, 0], "rush": [0, 0]})                          # hard plays, all plays (by season, team)
        self.lg = {"pass": [0, 0], "rush": [0, 0]}

    def factor(self, pid: str, season: int, defteam: str, kind: str) -> float | None:
        p = self.pl.get(pid)
        if p is None:
            return None
        nh, yh, ne, ye = p[kind]
        n = nh + ne
        if n < 30:
            return None
        overall = (yh + ye) / n
        ypp_h = (yh + overall * SHRINK_PLAYS / 2) / (nh + SHRINK_PLAYS / 2)
        ypp_e = (ye + overall * SHRINK_PLAYS / 2) / (ne + SHRINK_PLAYS / 2)
        faced = nh / n
        lg_rate = self.lg[kind][0] / self.lg[kind][1] if self.lg[kind][1] else faced
        cur, prev = self.df[(season, defteam)][kind], self.df[(season - 1, defteam)][kind]
        h, a = cur[0] + 0.5 * prev[0], cur[1] + 0.5 * prev[1]
        rate = (h + lg_rate * SHRINK_DEF) / (a + SHRINK_DEF)
        usual = faced * ypp_h + (1 - faced) * ypp_e
        expect = rate * ypp_h + (1 - rate) * ypp_e
        return expect / usual if usual > 0 else None

    def add_game(self, rows: list[tuple]):
        for season, _, _, defteam, kind, pid, yds, hard in rows:
            if kind is None or pid is None:
                continue
            p = self.pl[pid][kind]
            if hard:
                p[0] += 1
                p[1] += yds
            else:
                p[2] += 1
                p[3] += yds
            d = self.df[(season, defteam)][kind]
            d[0] += int(hard)
            d[1] += 1
            self.lg[kind][0] += int(hard)
            self.lg[kind][1] += 1


def factors(last: int) -> tuple[dict, State]:
    """{(game_id, player_id, kind): ratio before that game}, and the state after the last game (for live use)."""
    st, out = State(), {}
    allp = plays(last)
    by_game = defaultdict(list)
    for r in allp:
        by_game[r[2]].append(r)
    for gid, rows in by_game.items():
        seen = {(r[5], r[4], r[3]) for r in rows if r[5] and r[4]}
        for pid, kind, defteam in seen:
            f = st.factor(pid, rows[0][0], defteam, kind)
            if f is not None:
                out[(gid, pid, kind)] = f
        st.add_game(rows)
    return out, st


def fit(last: int) -> dict:
    fac, _ = factors(last)
    rows = props.load_rows(last)
    recs = props.history_projections(rows, props.load_out_reports(last))
    res = {}
    for stat, kind in STATS.items():
        train = [r for r in recs if props.FIRST_SEASON < r["row"]["season"] <= 2022]
        d, a = props.fit_stat(train, stat)
        pool = []
        for r in recs:
            if r["row"]["season"] < 2023 or d not in r["by_decay"] or not props.ROLE[stat](r["by_decay"][d][0]):
                continue
            f = fac.get((r["row"]["game_id"], r["row"]["player_id"], kind))
            pj = props._proj_one(r, stat, d, a)
            if f is None or pj is None:
                continue
            pool.append((pj, f, float(r["row"][stat]), r["row"]["season"]))
        tune = [p for p in pool if p[3] == 2023]
        test = [p for p in pool if p[3] >= 2024]
        g = min(GRID, key=lambda g: sum((y - pj * f ** g) ** 2 for pj, f, y, _ in tune)) if tune else 0.0
        se0 = sum((y - pj) ** 2 for pj, _, y, _ in test) / max(1, len(test))
        se1 = sum((y - pj * f ** g) ** 2 for pj, f, y, _ in test) / max(1, len(test))
        res[stat] = {"g": g, "tune_n": len(tune), "test_n": len(test), "mse_base": round(se0, 2), "mse_matchup": round(se1, 2),
                     "use": g > 0 and se0 > 0 and (se0 - se1) / se0 >= MIN_GAIN}
    return res


def load(season: int) -> dict:
    p = CACHE / f"props_matchup_{season}.json"
    if p.exists():
        return json.loads(p.read_text())
    res = fit(season)
    CACHE.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res, indent=1))
    return res


_LIVE: dict = {}


def live_factor(season: int, player_id: str, defteam: str, stat: str, params: dict) -> float:
    """Multiplier for an upcoming game (1.0 where the test did not support the term or the player has too few charted plays)."""
    p = params.get(stat) or {}
    if not p.get("use"):
        return 1.0
    if season not in _LIVE:
        _LIVE[season] = factors(season)[1]
    f = _LIVE[season].factor(player_id, season, defteam, STATS[stat])
    return 1.0 if f is None else f ** p["g"]


def report(res: dict) -> str:
    out = ["| Stat | Power g (tuned on 2023) | Tuning player-games | Test player-games (2024-26) | Error without | Error with | Used |",
           "|---|---|---|---|---|---|---|"]
    for stat, r in res.items():
        out.append(f"| {stat} | {r['g']} | {r['tune_n']} | {r['test_n']} | {r['mse_base']} | {r['mse_matchup']} | {'yes' if r['use'] else 'no'} |")
    return "\n".join(out)
