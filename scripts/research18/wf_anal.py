import json, sys, math
from collections import defaultdict
from engine import config
from engine.stale import landings
from engine.picks.playbook import edge_of
D=json.load(open(sys.argv[1]))
ls,lt=landings("NFL",config.load() if hasattr(config,'load') else {})
def binom_p(k,n,p0):
    # one-sided P(X>=k) normal approx w/ continuity
    mu=n*p0; sd=math.sqrt(n*p0*(1-p0)); z=(k-0.5-mu)/sd
    return 0.5*math.erfc(z/math.sqrt(2)), z
for adj in ("False","True"):
    G=D[adj]["game"]
    print("=== ADJUST",adj)
    # base rate
    un=sum(g["actual_total"]<g["total"] for g in G); ov=sum(g["actual_total"]>g["total"] for g in G)
    print(f"closing-total base rate 2019-26: unders {un}-{ov} ({un/(un+ov):.3f})")
    for thr in (2,3,4,5,6):
        bys=defaultdict(lambda:[0,0]); ou={"over":[0,0],"under":[0,0]}
        for g in G:
            d=g["own_total"]-g["total"]
            if abs(d)<thr: continue
            r=(g["actual_total"]-g["total"])*(1 if d>0 else -1)
            if r==0: continue
            s=g["season"]; k=0 if r>0 else 1
            bys[s][k]+=1; ou["over" if d>0 else "under"][k]+=1
        W=sum(v[0] for v in bys.values()); L=sum(v[1] for v in bys.values())
        p52,z=binom_p(W,W+L,0.5238); p50,_=binom_p(W,W+L,0.5)
        print(f" {thr}+: {W}-{L} ({W/(W+L):.3f}) p(vs52.4%)={p52:.3f} p(vs50%)={p50:.3f} | overs {ou['over']} unders {ou['under']} | by season "+" ".join(f"{s}:{v[0]}-{v[1]}" for s,v in sorted(bys.items())))
    # live rule sim at closing number, -110: blend 0.35, 3% edge
    for w in (0.35,0.10,0.0):
        rec=[0,0]; recnc=[0,0]
        for g in G:
            our=g["total"]+w*(g["own_total"]-g["total"])
            for side in ("over","under"):
                e,p=edge_of(lt,our,g["total"],side,-110)
                if e>=0.03:
                    r=(g["actual_total"]-g["total"])*(1 if side=="over" else -1)
                    if r==0: continue
                    chk=abs(g["own_total"]-g["total"])>4
                    tgt=rec if chk else recnc
                    tgt[0 if r>0 else 1]+=1
        print(f" live rule totals w={w}: no-CHECK bets {recnc}, CHECK-only bets {rec}")
    for w in (0.25,):
        rec=[0,0];recnc=[0,0]
        for g in G:
            ourm=g["mkt_margin"]+w*(g["own_margin"]-g["mkt_margin"])
            for side in ("home","away"):
                e,p=edge_of(ls,-ourm,-g["mkt_margin"],side,-110)
                if e>=0.03:
                    r=(g["actual_margin"]-g["mkt_margin"])*(1 if side=="home" else -1)
                    if r==0: continue
                    chk=abs(g["own_margin"]-g["mkt_margin"])>3
                    (rec if chk else recnc)[0 if r>0 else 1]+=1
        print(f" live rule sides w={w}: no-CHECK bets {recnc}, CHECK-only {rec}")
