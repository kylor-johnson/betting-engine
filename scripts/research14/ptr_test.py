"""College: do ~50 public rating systems (Prediction Tracker archive) beat the close? Walk-forward."""
import pandas as pd, numpy as np, sys, glob

frames = []
for y in range(2015, 2026):
    d = pd.read_csv(f"data.nosync/raw/tracker/archive/ncaa{y}.csv"); d["season"] = y; frames.append(d)
df = pd.concat(frames, ignore_index=True)
df = df[df.line.notna() & df.actual.notna()].copy()
print("games with line+actual:", len(df), df.groupby("season").size().to_dict())
# sanity: line vs actual
print("MAE line:", (df.actual - df.line).abs().mean().round(2), " corr(line,actual)", df[["line","actual"]].corr().iloc[0,1].round(3))
# what is lineopen?
o = df[df.lineopen.notna()]
print("lineopen rows", len(o), "MAE open", (o.actual-o.lineopen).abs().mean().round(2), "MAE close", (o.actual-o.line).abs().mean().round(2),
      "mean |open-close|", (o.lineopen-o.line).abs().mean().round(2), "share equal", (o.lineopen==o.line).mean().round(3))
syscols = [c for c in df.columns if c.startswith("line") and c not in ("line","lineopen")]
cover = lambda r: np.sign(r)
df["res"] = df.actual - df.line     # >0 = home covered
def ats(sel, side):
    r = df.loc[sel, "res"] * side.loc[sel]
    w, l = (r > 0).sum(), (r < 0).sum()
    return w, l
out = []
for test in range(2019, 2026):
    tr = df[df.season < test]; te = df[df.season == test]
    # predictor 1: average of systems minus line (lineavg is PT's own average)
    for name in ["lineavg", "linemedian"]:
        x_tr = (tr[name] - tr.line); y_tr = tr.res; m = x_tr.notna()
        b = np.polyfit(x_tr[m], y_tr[m], 1)
        x_te = te[name] - te.line; pred = b[0]*x_te + b[1]
        for thr in (1.0, 2.0, 3.0):
            sel = pred.abs() >= thr
            r = (te.res * np.sign(pred))[sel]
            out.append(dict(test=test, pred=name, slope=round(b[0],3), thr=thr, n=int(sel.sum()), w=int((r>0).sum()), l=int((r<0).sum()),
                            mse_close=round((te.res**2).mean(),1), mse_adj=round(((te.res-pred.fillna(0))**2).mean(),1)))
o = pd.DataFrame(out)
print(o[o.thr==1.0][["test","pred","slope","mse_close","mse_adj"]].to_string(index=False))
g = o.groupby(["pred","thr"])[["n","w","l"]].sum(); g["pct"] = (g.w/(g.w+g.l)).round(3); print(g)
# per system: raw disagreement >=3 vs close, held-out 2019-2025 (no fitting): count systems beating 52.4%
rows=[]
for c in syscols:
    t = df[(df.season>=2019) & df[c].notna()]
    d = t[c]-t.line; sel = d.abs()>=3
    r = (t.res*np.sign(d))[sel]; w,l=(r>0).sum(),(r<0).sum()
    if w+l>=300: rows.append((c,w,l,round(w/(w+l),3)))
rows.sort(key=lambda x:-x[3]); print("systems with >=300 bets at 3+ gap vs close, 2019-2025:", len(rows)); print(rows[:8]); print("above 52.4%:", sum(r[3]>0.524 for r in rows))
# multiple-testing check: best system's out-of-sample (pick best on 2015-2020, test 2021-2025)
rows2=[]
for c in syscols:
    t = df[(df.season.between(2015,2020)) & df[c].notna()]; d=t[c]-t.line; sel=d.abs()>=3; r=(t.res*np.sign(d))[sel]
    w,l=(r>0).sum(),(r<0).sum()
    if w+l>=300: rows2.append((c,w/(w+l)))
best = sorted(rows2,key=lambda x:-x[1])[:5]; print("best 5 on 2015-2020:", [(c,round(p,3)) for c,p in best])
for c,_ in best:
    t = df[(df.season>=2021) & df[c].notna()]; d=t[c]-t.line; sel=d.abs()>=3; r=(t.res*np.sign(d))[sel]
    print("  ", c, "2021-25:", (r>0).sum(), "-", (r<0).sum())
# early season: weeks <=4
for lab, cond in [("weeks 1-4", df.week<=4), ("weeks 5+", df.week>4)]:
    t = df[(df.season>=2019) & cond & df.lineavg.notna()]; d=t.lineavg-t.line
    for thr in (2,3,5):
        sel=d.abs()>=thr; r=(t.res*np.sign(d))[sel]; print(lab, "avg vs close gap>=",thr, (r>0).sum(),"-",(r<0).sum())
# opener: bet open where avg disagrees with open; grade vs result and CLV
t = df[(df.season>=2019) & df.lineopen.notna() & df.lineavg.notna() & (df.lineopen!=0)]
d = t.lineavg - t.lineopen
for thr in (2,3,5):
    sel=d.abs()>=thr; side=np.sign(d)[sel]
    res_open = (t.actual - t.lineopen)[sel]*side; clv = ((t.line - t.lineopen)[sel]*side)
    print("opener gap>=",thr, "n",sel.sum(), "W-L at open", (res_open>0).sum(), "-", (res_open<0).sum(), "avg CLV pts", round(clv.mean(),2))
