import pandas as pd, numpy as np
G = pd.read_csv("data.nosync/raw/nflverse_games.csv")
G = G[(G.season >= 2010) & G.result.notna() & G.spread_line.notna()].copy()
rows = []
for _, g in G.iterrows():
    sl = g.spread_line                     # + = home favored by sl
    for side in ("home", "away"):
        line = -sl if side == "home" else sl   # this side's spread (negative = favored)
        margin = g.result if side == "home" else -g.result
        rows.append(dict(season=g.season, line=line, margin=margin, total=g.total_line, home=side=="home"))
L = pd.DataFrame(rows)
def leg(df, pts):
    v = df.margin + df.line + pts
    return (v > 0).sum(), (v < 0).sum(), (v == 0).sum()
wong = L[L.line.between(-8.5, -7.5) | L.line.between(1.5, 2.5)]
print("2-team 6-pt teaser at Wagerhouse pays -110 (to_win/risk 0.909 in his history) -> break-even per leg 72.4%; 6.5-pt 2-team -120 -> 73.9%")
for lab, lo, hi in [("2010-2014", 2010, 2014), ("2015-2019", 2015, 2019), ("2020-2022", 2020, 2022), ("2023-2026", 2023, 2026)]:
    for tl, tcond in [("all totals", wong.total > 0), ("total <= 49", wong.total <= 49), ("total > 49", wong.total > 49)]:
        d = wong[(wong.season.between(lo, hi)) & tcond]
        w, l, p = leg(d, 6); print(f"{lab} {tl:12s} legs {w+l+p:4d}  won {w/(w+l):.3f}")
    print()
# by group 2018-2026
d = wong[wong.season >= 2018]
for lab, c in [("favs -7.5..-8.5", d.line < 0), ("dogs +1.5..+2.5", d.line > 0)]:
    w, l, p = leg(d[c], 6); print("2018-2026", lab, w, l, p, round(w/(w+l), 3))
# non-Wong legs for contrast
nw = L[(L.season >= 2018) & ~(L.line.between(-8.5, -7.5) | L.line.between(1.5, 2.5))]
w, l, p = leg(nw, 6); print("2018-2026 non-Wong legs", round(w/(w+l), 3), w+l)
# key numbers: share of games decided by exactly 3 / 7 when closing spread is 2.5-3.5 and 6.5-7.5, 2018-2026
G2 = G[G.season >= 2018]
a = G2.spread_line.abs(); m = G2.result.abs()
for s in (2.5, 3, 3.5, 6.5, 7, 7.5):
    sub = G2[a == s]; print(f"close {s}: games {len(sub)}, fav wins by exactly 3: {((sub.result*np.sign(sub.spread_line))==3).mean():.3f}, by exactly 7: {((sub.result*np.sign(sub.spread_line))==7).mean():.3f}")
