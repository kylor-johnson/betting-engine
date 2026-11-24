import duckdb, math, sys
c=duckdb.connect(sys.argv[1],read_only=True)
rows=c.execute("""
with g as (select coalesce(sport,'NFL') sp,*, row_number() over (partition by coalesce(sport,'NFL'),player_id,stat,home,away,line order by ts_utc) rf,
  row_number() over (partition by coalesce(sport,'NFL'),player_id,stat,home,away,line order by ts_utc desc) rl
  from prop_evals where outcome is not null and outcome<>line and market_p_over is not null and model_p_over is not null and over_price is not null and under_price is not null)
select sp, stat, rf=1 as first, line, over_price, under_price, market_p_over, model_p_over, (outcome>line)::int y, player_id, home from g where rf=1 or rl=1""").fetchall()
def dec(a): return 1+a/100 if a>0 else 1+100/abs(a)
def ll(p,y): p=min(max(p,1e-4),1-1e-4); return -(y*math.log(p)+(1-y)*math.log(1-p))
for which in (True,False):
  for sp in ('NFL','NBA'):
    R=[r for r in rows if r[0]==sp and r[2]==which]
    # dedupe: one per player/stat/game (take first line seen)
    seen=set();RR=[]
    for r in R:
      k=(r[9],r[1],r[10])
      if k in seen: continue
      seen.add(k);RR.append(r)
    R=RR;n=len(R)
    if not n: continue
    Lm=sum(ll(r[6],r[8]) for r in R)/n; Lo=sum(ll(r[7],r[8]) for r in R)/n
    Lb=sum(ll(r[6]+.5*(r[7]-r[6]),r[8]) for r in R)/n
    # best blend weight by log loss
    best=min(((sum(ll(r[6]+w/20*(r[7]-r[6]),r[8]) for r in R)/n,w/20) for w in range(0,21)))
    # simulate playbook rule: blend .5, edge>=4% at pinnacle price, and at a WH-like price (each side 1/dec + extra 2.5% vig)
    out={}
    for lab,extra in (('pinnacle',0.0),('wh_est',0.025)):
      bets=0;prof=0.0;w=0
      for r in R:
        p=r[6]+.5*(r[7]-r[6])
        for side,pr,ps,yy in (('o',r[4],p,r[8]),('u',r[5],1-p,1-r[8])):
          need=1/dec(pr)+extra
          if ps-need>=0.04:
            d=1/need
            bets+=1; w+=yy; prof+= (d-1) if yy else -1
      out[lab]=(bets,w,round(prof,1),round(prof/bets*100,1) if bets else None)
    # under share
    print(f"{sp} {'first-seen' if which else 'last-seen'} n={n} logloss pinnacle={Lm:.4f} model={Lo:.4f} blend.5={Lb:.4f} best_w={best[1]} ({best[0]:.4f}) rule:{out}")
