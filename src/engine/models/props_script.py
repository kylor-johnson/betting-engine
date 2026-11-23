"""Game script by lead, for NFL props (PLAYBOOK step 3 item 1; decision 0022).

The props model scales a player's projection by his team's expected points, not by whether his team is expected to lead. Leaders run more and
trailers throw more, so for each stat this fits one number `b`: projection x exp(b x expected margin), expected margin in points from the
closing spread (positive = team favored). `b` is fitted on 2019 to 2022 and kept only for stats where it lowers the error on 2023 to 2026,
seasons it never saw, by at least 0.1%. In live use the expected margin is OUR blended margin from the game script, so the script's view of the game moves the
props. Results are cached per season in data.nosync/models/props_script_<season>.json and written up by `report`.
"""
from __future__ import annotations

import json
import math

from engine import config
from engine.models import props

CACHE = config.DATA / "models"
TRAIN_LAST, TEST_FIRST = 2022, 2023
MIN_GAIN = 0.001          # keep the term only if it lowers held-out squared error by at least 0.1% (smaller is noise)


def _margin(r: dict) -> float:
    return r["spread_line"] if r["team"] == r["home_team"] else -r["spread_line"]


def fit(last_season: int) -> dict:
    rows = props.load_rows(last_season)
    recs = props.history_projections(rows, props.load_out_reports(last_season))
    out = {}
    for stat in props.STATS:
        train = [r for r in recs if props.FIRST_SEASON < r["row"]["season"] <= TRAIN_LAST]
        d, a = props.fit_stat(train, stat)
        pool = [(props._proj_one(r, stat, d, a), float(r["row"][stat]), _margin(r["row"]), r["row"]["season"]) for r in recs
                if d in r["by_decay"] and props.ROLE[stat](r["by_decay"][d][0])]
        pool = [p for p in pool if p[0] is not None and p[0] > 0]
        tr = [p for p in pool if p[3] <= TRAIN_LAST]
        te = [p for p in pool if p[3] >= TEST_FIRST]
        xs = [m for _, _, m, _ in tr]
        ys = [math.log((max(y, 0.0) + 0.5) / (pj + 0.5)) for pj, y, _, _ in tr]   # rushing yards can be negative
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        var = sum((x - mx) ** 2 for x in xs)
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var if var else 0.0
        se0 = sum((y - pj) ** 2 for pj, y, _, _ in te) / len(te)
        se1 = sum((y - pj * math.exp(b * m)) ** 2 for pj, y, m, _ in te) / len(te)
        out[stat] = {"b": round(b, 5), "test_n": len(te), "mse_base": round(se0, 3), "mse_script": round(se1, 3),
                     "use": se0 > 0 and (se0 - se1) / se0 >= MIN_GAIN}
    return out


def load(season: int) -> dict:
    p = CACHE / f"props_script_{season}.json"
    if p.exists():
        return json.loads(p.read_text())
    res = fit(season)
    CACHE.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res, indent=1))
    return res


def factor(params: dict, stat: str, margin: float) -> float:
    """Multiplier on the projection for this stat at this expected margin (1.0 where the test did not support the term)."""
    p = params.get(stat) or {}
    return math.exp(p["b"] * margin) if p.get("use") else 1.0


def report(res: dict) -> str:
    out = ["| Stat | b (per point of expected margin) | Held-out player-games | Error without | Error with | Used |", "|---|---|---|---|---|---|"]
    for stat, r in res.items():
        out.append(f"| {stat} | {r['b']:+.4f} | {r['test_n']} | {r['mse_base']} | {r['mse_script']} | {'yes' if r['use'] else 'no'} |")
    return "\n".join(out)
