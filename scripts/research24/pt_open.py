"""Research 24, tests F1 (NFL, lineavg) and N1 (NBA, lineespn): a rating against the opener, as pre-registered in commit fccd765.

uv run python scripts/research24/pt_open.py
Files: The Prediction Tracker's free CSVs, downloaded once to data.nosync/raw/prediction_tracker/.
"""
from __future__ import annotations

import csv
import math
import urllib.request
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "data.nosync" / "raw" / "prediction_tracker"


def rows(name: str) -> list[dict]:
    p = DIR / f"{name}.csv"
    if not p.exists():
        DIR.mkdir(parents=True, exist_ok=True)
        p.write_bytes(urllib.request.urlopen(f"https://www.thepredictiontracker.com/{name}.csv", timeout=60).read())
    return list(csv.DictReader(p.open(encoding="utf-8", errors="replace")))


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def cols(r: dict) -> tuple:
    hs = f(r.get("hscore"))
    rs = f(r.get("rscore") if "rscore" in r else r.get("vscore"))
    return hs, rs


def sign_of_line(all_rows: list[dict]) -> int:
    """+1 if a positive `line` means the home team is favoured (agrees with the home margin), else -1. Orientation only."""
    s = 0.0
    for r in all_rows:
        hs, rs = cols(r)
        ln = f(r.get("line"))
        if hs is None or rs is None or ln is None:
            continue
        s += ln * (hs - rs)
    return 1 if s > 0 else -1


def grade(files: list[str], col: str, gap: float = 1.5) -> dict:
    out = {"seasons": {}, "w": 0, "l": 0, "toward": 0, "away": 0, "wc": 0, "lc": 0}
    for name in files:
        rs_ = rows(name)
        sg = sign_of_line(rs_)
        w = l = tw = aw = wc = lc = 0
        for r in rs_:
            hs, rsc = cols(r)
            op, cl, sy = f(r.get("lineopen")), f(r.get("line")), f(r.get(col))
            if None in (hs, rsc, op, sy):
                continue
            # home-favoured margins: positive = home by that much
            op_m, sy_m = sg * op, sg * sy
            if abs(sy_m - op_m) < gap:
                continue
            home = sy_m > op_m                      # the rating likes the home side more than the opener does
            res = (hs - rsc) - op_m                 # home result against the opener
            if res == 0:
                pass
            elif (res > 0) == home:
                w += 1
            else:
                l += 1
            if cl is not None:
                cl_m = sg * cl
                mv = cl_m - op_m
                if mv != 0:
                    if (mv > 0) == home:
                        tw += 1
                    else:
                        aw += 1
                rc = (hs - rsc) - cl_m
                if rc != 0:
                    if (rc > 0) == home:
                        wc += 1
                    else:
                        lc += 1
        out["seasons"][name] = dict(sign=sg, w=w, l=l, pct=w / (w + l) if w + l else None, toward=tw, away=aw, wc=wc, lc=lc)
        for k, v in (("w", w), ("l", l), ("toward", tw), ("away", aw), ("wc", wc), ("lc", lc)):
            out[k] += v
    n = out["w"] + out["l"]
    out["pct"] = out["w"] / n if n else None
    out["z"] = (out["w"] - n / 2) / math.sqrt(n / 4) if n else None
    m = out["toward"] + out["away"]
    out["toward_pct"] = out["toward"] / m if m else None
    out["toward_z"] = (out["toward"] - m / 2) / math.sqrt(m / 4) if m else None
    nc = out["wc"] + out["lc"]
    out["close_pct"] = out["wc"] / nc if nc else None
    return out


def show(title: str, r: dict) -> None:
    print(f"\n== {title}")
    for s, v in r["seasons"].items():
        print(f"  {s}: line sign {v['sign']:+d}; at the opener {v['w']}-{v['l']} ({100 * (v['pct'] or 0):.1f}%); "
              f"line moved toward {v['toward']}, away {v['away']}; at the close {v['wc']}-{v['lc']}")
    print(f"  pooled at the opener {r['w']}-{r['l']} ({100 * r['pct']:.1f}%), z {r['z']:.2f}; moved toward {r['toward']}-{r['away']} "
          f"({100 * r['toward_pct']:.1f}%), z {r['toward_z']:.2f}; at the close {r['wc']}-{r['lc']} ({100 * r['close_pct']:.1f}%)")


if __name__ == "__main__":
    show("F1 NFL, systems average (lineavg) vs lineopen, 2023-2025", grade(["nfl23", "nfl24", "nfl25"], "lineavg"))
    show("F1 side note: ESPN FPI (lineespn), not judged", grade(["nfl23", "nfl24", "nfl25"], "lineespn"))
    show("N1 NBA, ESPN BPI (lineespn) vs lineopen, 2018-19 to 2020-21", grade(["nba18", "nba19", "nba20"], "lineespn"))
