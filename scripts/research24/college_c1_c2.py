"""Research 24, tests C1 (Bennett small-conference reaction) and C2 (fade last season's SP+ top 25 in weeks 1-4), as pre-registered
in commit fccd765. Cached CollegeFootballData only (data.nosync/raw/cfbd, cfbd_review); the line is the engine's own provider order.

uv run python scripts/research24/college_c1_c2.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from engine.models.college_script import _line

RAW = Path(__file__).resolve().parents[2] / "data.nosync" / "raw"
POWER = {"SEC", "Big Ten", "Big 12", "ACC"}


def games() -> list[dict]:
    out = []
    for y in range(2021, 2027):
        out += [g for g in json.loads((RAW / "cfbd" / f"cfbd_lines_{y}.json").read_text()) if g.get("seasonType") == "regular"]
    return sorted(out, key=lambda g: (g.get("startDate") or "", g["id"]))


def power(team: str, conf: str | None, season: int) -> bool:
    return conf in POWER or (conf == "Pac-12" and season <= 2023) or team == "Notre Dame"


def fbs(g: dict, side: str) -> bool:
    return g.get(f"{side}Classification") == "fbs"


def rec(w: int, l: int) -> str:
    n = w + l
    return f"{w}-{l} ({100 * w / n:.1f}%, z {(w - n / 2) / math.sqrt(n / 4):+.2f})" if n else "0-0"


def c1() -> None:
    last: dict[tuple[int, str], float] = {}          # (season, team) -> last miss against its own closing spread
    res = {"small": {}, "power": {}}
    for g in games():
        ln = _line(g)
        hs, as_ = g.get("homeScore"), g.get("awayScore")
        if ln is None or hs is None or as_ is None or not (fbs(g, "home") and fbs(g, "away")):
            continue
        y, h, a, sp = g["season"], g["homeTeam"], g["awayTeam"], float(ln["spread"])
        both_small = not power(h, g.get("homeConference"), y) and not power(a, g.get("awayConference"), y)
        both_power = power(h, g.get("homeConference"), y) and power(a, g.get("awayConference"), y)
        vote = 0                                       # +1 = bet home, -1 = bet away
        for team, s in ((h, 1), (a, -1)):
            m = last.get((y, team))
            if m is None:
                continue
            if m >= 14:
                vote += s
            elif m <= -14:
                vote -= s
        r = (hs - as_) + sp                            # home result against the closing spread (CFBD spread is the home spread)
        if vote and r != 0 and (both_small or both_power):
            bucket = res["small" if both_small else "power"].setdefault(y, [0, 0])
            bucket[0 if (r > 0) == (vote > 0) else 1] += 1
        last[(y, h)] = r
        last[(y, a)] = -r
    for k, by in res.items():
        w = sum(v[0] for v in by.values())
        l = sum(v[1] for v in by.values())
        early = [sum(by.get(y, [0, 0])[i] for y in (2021, 2022, 2023)) for i in (0, 1)]
        late = [sum(by.get(y, [0, 0])[i] for y in (2024, 2025, 2026)) for i in (0, 1)]
        print(f"C1 {'both small-conference (judged)' if k == 'small' else 'both power (control)'}: {rec(w, l)}; "
              f"2021-23 {rec(*early)}; 2024-26 {rec(*late)}; by season " + ", ".join(f"{y} {v[0]}-{v[1]}" for y, v in sorted(by.items())))


def c2() -> None:
    by: dict[int, list[int]] = {}
    for g in games():
        y = g["season"]
        if (g.get("week") or 99) > 4:
            continue
        spf = RAW / "cfbd_review" / f"sp_{y - 1}.json"
        if not spf.exists():
            continue
        sp = [t for t in json.loads(spf.read_text()) if t.get("team") and t.get("rating") is not None and t["team"] != "nationalAverages"]
        top = {t["team"] for t in sorted(sp, key=lambda t: -t["rating"])[:25]}
        ln = _line(g)
        hs, as_ = g.get("homeScore"), g.get("awayScore")
        if ln is None or hs is None or as_ is None or not (fbs(g, "home") and fbs(g, "away")):
            continue
        h, a = g["homeTeam"], g["awayTeam"]
        if (h in top) == (a in top):
            continue                                   # neither, or both
        r = (hs - as_) + float(ln["spread"])
        if r == 0:
            continue
        fade_home = h in top
        b = by.setdefault(y, [0, 0])
        b[0 if (r < 0) == fade_home else 1] += 1
    w, l = sum(v[0] for v in by.values()), sum(v[1] for v in by.values())
    print(f"C2 fade last season's SP+ top 25, weeks 1-4 vs FBS: {rec(w, l)}; by season " + ", ".join(f"{y} {v[0]}-{v[1]}" for y, v in sorted(by.items())))


if __name__ == "__main__":
    c1()
    c2()
