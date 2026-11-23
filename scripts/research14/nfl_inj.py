"""NFL: does the official injury report (who is Out/Doubtful/Questionable, and final practice status), weighted by
each player's recent snap share, predict results against the CLOSING spread and total? Walk-forward by season."""
import pandas as pd, numpy as np, sys, re, json
import sys; R = "data.nosync/raw/nflverse"
norm = lambda s: re.sub(r"[^a-z]", "", re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", str(s).lower()))
snaps = pd.concat([pd.read_parquet(f"data.nosync/raw/nflverse/snaps/snap_counts_{y}.parquet") for y in range(2018, 2027)])
snaps["key"] = snaps.player.map(norm)
snaps["pct"] = snaps[["offense_pct", "defense_pct"]].max(axis=1)
snaps["wk"] = snaps.week + np.where(snaps.game_type == "REG", 0, 100)
inj = pd.concat([pd.read_parquet(f"{R}/injuries_{y}.parquet") for y in range(2018, 2027)])
inj["key"] = inj.full_name.map(norm)
inj["wk"] = inj.week + np.where(inj.game_type == "REG", 0, 100)
# team abbreviations: snaps use pfr-ish? align a few
fix = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"}
for d in (snaps, inj): d["team"] = d.team.replace(fix)
# importance: mean snap pct over the player's last 3 games played earlier in the same season
snaps = snaps.sort_values(["season", "key", "team", "wk"])
snaps["imp"] = snaps.groupby(["season", "key", "team"]).pct.transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
for d in (snaps, inj): d["wk"]=d["wk"].astype("int64"); d["season"]=d["season"].astype("int64")
m = inj.copy()
# use rolling mean of last 3 played games before this week
roll = snaps[["season", "team", "key", "wk"]].copy(); roll["r3"] = snaps.groupby(["season", "key", "team"]).pct.transform(lambda x: x.rolling(3, min_periods=1).mean())
m = pd.merge_asof(m.sort_values("wk"), roll.sort_values("wk").rename(columns={"wk": "rwk"}), left_on="wk", right_on="rwk",
                  by=["season", "team", "key"], allow_exact_matches=False, direction="backward")
m["imp"] = m.r3.fillna(0)
m["gap"] = m.wk - m.rwk            # weeks since he last played (1 = played last week)
print("injury rows", len(m), "matched to snaps", m.r3.notna().mean().round(3))
grp = {"QB": "QB", "T": "OL", "G": "OL", "C": "OL", "OL": "OL", "WR": "SK", "TE": "SK", "RB": "SK", "FB": "SK",
       "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "LB": "LB", "OLB": "LB", "ILB": "LB", "MLB": "LB",
       "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB", "DB": "DB"}
m["g"] = m.position.map(grp)
m = m[m.g.notna()]
st = m.report_status.fillna(""); pr = m.practice_status.fillna("")
m["cls"] = np.select([st.isin(["Out", "Doubtful"]),
                      (st == "Questionable") & pr.str.startswith("Did Not"),
                      (st == "Questionable") & pr.str.startswith("Limited"),
                      (st == "Questionable")], ["out", "q_dnp", "q_lim", "q_full"], "none")
m["fresh"] = (m.gap == 1)          # played last week: news this week
# QB: only count the starter (imp >= .5)
m.loc[(m.g == "QB") & (m.imp < 0.5), "imp"] = 0
feats = []
for (s, w, t), d in m[m.cls != "none"].groupby(["season", "wk", "team"]):
    f = {"season": s, "wk": w, "team": t}
    for g in ["QB", "OL", "SK", "DL", "LB", "DB"]:
        f[f"out_{g}"] = d[(d.cls == "out") & (d.g == g)].imp.sum()
        f[f"outfresh_{g}"] = d[(d.cls == "out") & (d.g == g) & d.fresh].imp.sum()
    for c in ["q_dnp", "q_lim", "q_full"]:
        f[c] = d[d.cls == c].imp.sum()
    feats.append(f)
F = pd.DataFrame(feats)
G = pd.read_csv("data.nosync/raw/nflverse_games.csv")
G = G[(G.season >= 2018) & G.result.notna() & G.spread_line.notna()].copy()
G["wk"] = G.week + np.where(G.game_type == "REG", 0, 100)
for d in ("home", "away"):
    G = G.merge(F.add_prefix(d[0] + "_").rename(columns={f"{d[0]}_season": "season", f"{d[0]}_wk": "wk", f"{d[0]}_team": f"{d}_team"}),
                on=["season", "wk", f"{d}_team"], how="left")
G = G.fillna({c: 0 for c in G.columns if c[:2] in ("h_", "a_")})
cols = [c[2:] for c in G.columns if c.startswith("h_")]
X = pd.DataFrame({c: G["h_" + c] - G["a_" + c] for c in cols})       # home missing minus away missing
XT = pd.DataFrame({c: G["h_" + c] + G["a_" + c] for c in cols})      # both teams, for totals
G["res"] = G.result - G.spread_line          # >0 home covered
G["tres"] = G.total - G.total_line           # >0 over
print("games", len(G), G.groupby("season").size().to_dict())
print("avg missing per team-game (Out/Doubtful snap-share sum):", round(G[[f"h_out_{g}" for g in ['QB','OL','SK','DL','LB','DB']]].sum(axis=1).mean(), 2))
def wf(Xm, y, label, ridge=50.0):
    rows = []; bets = {1.0: [], 1.5: [], 2.0: []}
    for test in range(2021, 2027):
        tr = G.season < test; te = G.season == test
        A = np.c_[np.ones(tr.sum()), Xm[tr].values]; lam = np.eye(A.shape[1]) * ridge; lam[0, 0] = 0
        b = np.linalg.solve(A.T @ A + lam, A.T @ y[tr].values)
        p = np.c_[np.ones(te.sum()), Xm[te].values] @ b
        yt = y[te].values
        rows.append((test, te.sum(), round((yt ** 2).mean(), 1), round(((yt - p) ** 2).mean(), 1)))
        for t in bets:
            sel = np.abs(p) >= t; r = yt[sel] * np.sign(p[sel]); bets[t] += list(r)
    print(f"\n== {label}: season, games, MSE vs close, MSE after adjustment")
    for r in rows: print("  ", r)
    tot = (sum(r[1]*r[2] for r in rows)/sum(r[1] for r in rows), sum(r[1]*r[3] for r in rows)/sum(r[1] for r in rows))
    print("   pooled MSE close %.2f, adjusted %.2f" % tot)
    for t, r in bets.items():
        r = np.array(r); w, l = (r > 0).sum(), (r < 0).sum(); print(f"   bets |pred|>={t}: {w}-{l} ({w/max(1,w+l):.3f})")
    return b
b = wf(X, G.res, "SIDES: injury features vs closing spread")
print("   last-fit coefficients (pts per 1.0 snap-share, home missing minus away):", dict(zip(["const"] + cols, np.round(b, 2))))
# OLS full-sample with t-stats for reading
import statsmodels.api as sm
o = sm.OLS(G.res, sm.add_constant(X)).fit(); print(o.summary().tables[1])
bt = wf(XT, G.tres, "TOTALS: injury features (both teams) vs closing total")
o = sm.OLS(G.tres, sm.add_constant(XT)).fit(); print(o.summary().tables[1])
G[["game_id", "season", "wk", "res", "tres"] + ["h_" + c for c in cols] + ["a_" + c for c in cols]].to_parquet(f"data.nosync/reports/nfl_inj_games.parquet")
