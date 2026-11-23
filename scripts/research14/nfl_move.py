import sys, pandas as pd, numpy as np
sys.path.insert(0, "src")
from engine.models import openers

gs = [g for g in openers.nfl_games(first=2023) if g.open_margin is not None and g.close_margin is not None]
rows = [dict(season=g.season, wk=g.week, home=g.home, away=g.away, om=g.open_margin, cm=g.close_margin, ot=g.open_total, ct=g.close_total, margin=g.margin, pts=g.points) for g in gs]
D = pd.DataFrame(rows); print("NFL games with ESPN BET open and close:", len(D), D.groupby("season").size().to_dict())
D["move"] = D.cm - D.om
print("abs move: mean %.2f, share >=1.5: %.2f, share >=3: %.2f" % (D.move.abs().mean(), (D.move.abs()>=1.5).mean(), (D.move.abs()>=3).mean()))
I = pd.read_parquet(f"data.nosync/reports/nfl_inj_games.parquet")
G = pd.read_csv("data.nosync/raw/nflverse_games.csv")[["game_id","season","week","game_type","home_team","away_team"]]
G["wk"] = G.week + np.where(G.game_type=="REG",0,100)
I = I.merge(G, on=["game_id","season","wk"])
D = D.merge(I, left_on=["season","wk","home","away"], right_on=["season","wk","home_team","away_team"])
print("matched", len(D))
grp = ['QB','OL','SK','DL','LB','DB']
D["qb_fresh"] = D.h_outfresh_QB - D.a_outfresh_QB
D["oth_fresh"] = sum(D[f"h_outfresh_{g}"] - D[f"a_outfresh_{g}"] for g in grp if g!="QB")
D["q"] = (D.h_q_dnp + D.h_q_lim) - (D.a_q_dnp + D.a_q_lim)
import statsmodels.api as sm
o = sm.OLS(D.move, sm.add_constant(D[["qb_fresh","oth_fresh","q"]])).fit()
print(o.summary().tables[1]); print("R2 of the week's move explained by fresh injury news: %.3f" % o.rsquared)
# what share of the move is that? games with fresh starting QB out
qb = D[D.qb_fresh.abs()>=0.5]
print("games with a starting QB newly out (played last week):", len(qb), " avg move toward the healthier side: %.2f pts" % (-(qb.move*np.sign(qb.qb_fresh))).mean())
