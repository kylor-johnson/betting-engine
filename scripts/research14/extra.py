import sys, pandas as pd, numpy as np
import sys; sys.path.insert(0, "src")
# college Wong-style legs (PTR: line = home margin expected, actual = home margin)
P = pd.concat([pd.read_csv(f"data.nosync/raw/tracker/archive/ncaa{y}.csv").assign(season=y) for y in range(2015, 2026)])
P = P[P.line.notna() & P.actual.notna()]
legs = pd.concat([pd.DataFrame({"season": P.season, "spread": -P.line, "margin": P.actual}),      # home: spread = -expected margin
                  pd.DataFrame({"season": P.season, "spread": P.line, "margin": -P.actual})])
w = legs[legs.spread.between(-8.5, -7.5) | legs.spread.between(1.5, 2.5)]
v = w.margin + w.spread + 6; print("College Wong-range legs 2015-2025, 6 pts:", len(w), "won %.3f" % ((v > 0).sum() / ((v > 0).sum() + (v < 0).sum())))
v = legs.margin + legs.spread + 6; print("College all legs 6 pts: won %.3f" % ((v > 0).sum() / ((v > 0).sum() + (v < 0).sum())))
# college early-season fade-the-systems by season
P["res"] = P.actual - P.line
e = P[(P.week <= 4) & P.lineavg.notna() & (P.season >= 2015)]
d = e.lineavg - e.line; sel = d.abs() >= 2
r = (e.res * np.sign(d))[sel]
print("College weeks 1-4, systems' average 2+ off the close: side the systems like covered, by season:")
print(pd.DataFrame({"s": e.season[sel], "w": (r > 0), "l": (r < 0)}).groupby("s")[["w", "l"]].sum().T.to_string())
# NBA 4-point teaser legs
from engine.models import nba_data
rows = []
for g in nba_data.load():
    if g.get("home_spread") is None: continue
    hp = sum(p.get("pts", 0) for p in g["players"] if p["team"] == g["home"]); ap = sum(p.get("pts", 0) for p in g["players"] if p["team"] == g["away"])
    if hp == 0: continue
    rows += [hp - ap + g["home_spread"] + 4, ap - hp - g["home_spread"] + 4]
v = np.array(rows); print("NBA 4-pt teaser legs (all sides, ESPN close):", len(v), "won %.3f" % ((v > 0).sum() / ((v > 0).sum() + (v < 0).sum())))
