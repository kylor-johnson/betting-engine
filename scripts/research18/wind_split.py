import json,sys
from engine.models import script
rows=script.build_features(adjust=True)
wind={}
for r in rows:
    wind[r["game_id"]]=(r["wind"] or 0) if not r["dome"] else 0
D=json.load(open(sys.argv[1]))["True"]["game"]
for thr in (4,5):
  for lab,cond in (("wind>=10",lambda w:w>=10),("wind<10",lambda w:w<10)):
    for side in ("under","over"):
        W=L=0
        for g in D:
            d=g["own_total"]-g["total"]
            if abs(d)<thr or (d<0)!=(side=="under") or not cond(wind.get(g["game_id"],0)): continue
            r=(g["actual_total"]-g["total"])*(1 if d>0 else -1)
            W+=r>0;L+=r<0
        print(thr,lab,side,W,L)
