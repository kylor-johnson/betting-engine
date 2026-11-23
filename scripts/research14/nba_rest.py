"""NBA: rest, schedule density and travel against the CLOSING spread and total. Walk-forward by season."""
import sys, math, pandas as pd, numpy as np
sys.path.insert(0, "src")
from engine.models import nba_data
C = {"ATL":(33.76,-84.40),"BOS":(42.37,-71.06),"BKN":(40.68,-73.97),"CHA":(35.23,-80.84),"CHI":(41.88,-87.67),"CLE":(41.50,-81.69),
 "DAL":(32.79,-96.81),"DEN":(39.75,-105.01),"DET":(42.34,-83.06),"GS":(37.77,-122.39),"HOU":(29.75,-95.36),"IND":(39.76,-86.16),
 "LAC":(33.94,-118.34),"LAL":(34.04,-118.27),"MEM":(35.14,-90.05),"MIA":(25.78,-80.19),"MIL":(43.05,-87.92),"MIN":(44.98,-93.28),
 "NO":(29.95,-90.08),"NY":(40.75,-73.99),"OKC":(35.46,-97.52),"ORL":(28.54,-81.38),"PHI":(39.90,-75.17),"PHX":(33.45,-112.07),
 "POR":(45.53,-122.67),"SAC":(38.58,-121.50),"SA":(29.43,-98.44),"TOR":(43.64,-79.38),"UTAH":(40.77,-111.90),"WSH":(38.90,-77.02)}
def km(a, b):
    (la1, lo1), (la2, lo2) = C[a], C[b]; p = math.pi/180
    h = math.sin((la2-la1)*p/2)**2 + math.cos(la1*p)*math.cos(la2*p)*math.sin((lo2-lo1)*p/2)**2
    return 12742*math.asin(math.sqrt(h))
games = [g for g in nba_data.load() if g.get("home_spread") is not None and g.get("total") is not None]
miss = {t for g in games for t in (g["home"], g["away"]) if t not in C}; print("teams missing coords:", miss)
rows = []
for g in games:
    hp = sum(p.get("pts", 0) for p in g["players"] if p["team"] == g["home"]); ap = sum(p.get("pts", 0) for p in g["players"] if p["team"] == g["away"])
    rows.append(dict(eid=g["event_id"], season=g["season"], date=pd.Timestamp(g["date"]), home=g["home"], away=g["away"], hs=g["home_spread"], tot=g["total"], hp=hp, ap=ap))
D = pd.DataFrame(rows).sort_values("date"); D = D[D.hp > 0]
print("games", len(D), D.groupby("season").size().to_dict())
# per team schedule (all games, incl. no-line ones would be better but we only have these)
long = pd.concat([D[["eid","season","date","home"]].rename(columns={"home":"team"}).assign(loc=D.home, home=1),
                  D[["eid","season","date","away"]].rename(columns={"away":"team"}).assign(loc=D.home, home=0)]).sort_values(["team","date"])
f = []
for (t, s), d in long.groupby(["team","season"]):
    d = d.reset_index(drop=True); dates = d.date.tolist(); locs = d["loc"].tolist()
    trip = 0
    for i in range(len(d)):
        rest = (dates[i]-dates[i-1]).days - 1 if i else 7
        g4 = sum(1 for j in range(i) if (dates[i]-dates[j]).days <= 4)
        g7 = sum(1 for j in range(i) if (dates[i]-dates[j]).days <= 7)
        trav = km(locs[i-1], locs[i]) if i and rest <= 1 else 0.0
        tz = (C[locs[i]][1] - C[locs[i-1]][1])/15 if i else 0
        trip = trip + 1 if d.home[i] == 0 else 0
        f.append(dict(eid=d.eid[i], team=t, rest=min(rest, 3), b2b=int(rest == 0), g4=g4, g7=g7, trav=trav/1000, tzw=max(0, -tz) if rest<=1 else 0, tze=max(0,tz) if rest<=1 else 0, trip=min(trip, 6)))
F = pd.DataFrame(f)
for side in ("home", "away"):
    D = D.merge(F.rename(columns={c: f"{side[0]}_{c}" for c in F.columns if c not in ("eid",)}).rename(columns={f"{side[0]}_team": side}), on=["eid", side])
D["alt"] = D.home.isin(["DEN","UTAH"]).astype(int)
D["res"] = (D.hp - D.ap) + D.hs     # >0 home beat the closing spread
D["tres"] = (D.hp + D.ap) - D.tot
fe = ["b2b","rest","g4","g7","trav","tzw","tze","trip"]
X = pd.DataFrame({c: D["h_"+c] - D["a_"+c] for c in fe}); X["alt_b2b"] = D.alt * D.a_b2b
XT = pd.DataFrame({c: D["h_"+c] + D["a_"+c] for c in fe})
print("home b2b share %.3f, away b2b share %.3f" % (D.h_b2b.mean(), D.a_b2b.mean()))
def wf(Xm, y, label, ridge=20.0):
    print(f"\n== {label}")
    allb = {1.0: [], 1.5: [], 2.0: []}; tot = [0, 0, 0]
    for test in sorted(D.season.unique())[1:]:
        tr = (D.season < test).values; te = (D.season == test).values
        A = np.c_[np.ones(tr.sum()), Xm[tr].values]; lam = np.eye(A.shape[1])*ridge; lam[0, 0] = 0
        b = np.linalg.solve(A.T@A + lam, A.T@y[tr].values); p = np.c_[np.ones(te.sum()), Xm[te].values]@b; yt = y[te].values
        print("  test %d: games %d, MSE close %.1f, adjusted %.1f" % (test, te.sum(), (yt**2).mean(), ((yt-p)**2).mean()))
        tot[0] += te.sum(); tot[1] += (yt**2).sum(); tot[2] += ((yt-p)**2).sum()
        for t in allb:
            sel = np.abs(p) >= t; allb[t] += list(yt[sel]*np.sign(p[sel]))
    print("  pooled MSE close %.2f, adjusted %.2f" % (tot[1]/tot[0], tot[2]/tot[0]))
    for t, r in allb.items():
        r = np.array(r); w, l = (r > 0).sum(), (r < 0).sum(); print(f"  bets |pred|>={t}: {w}-{l} ({w/max(1,w+l):.3f})")
wf(X, D.res, "SIDES: rest/density/travel vs closing spread")
wf(XT, D.tres, "TOTALS: rest/density/travel vs closing total")
import statsmodels.api as sm
o = sm.OLS(D.res, sm.add_constant(X)).fit(); print(o.summary().tables[1])
o = sm.OLS(D.tres, sm.add_constant(XT)).fit(); print(o.summary().tables[1])
# simple slices
for lab, sel in [("home b2b, away rested", (D.h_b2b==1)&(D.a_b2b==0)), ("away b2b, home rested", (D.a_b2b==1)&(D.h_b2b==0)), ("away b2b at DEN/UTAH", (D.a_b2b==1)&(D.alt==1))]:
    r = D.res[sel]; print(lab, "n", sel.sum(), "home vs close mean %.2f, home covers %d-%d" % (r.mean(), (r>0).sum(), (r<0).sum()))
