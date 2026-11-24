import duckdb, math, random, sys
c=duckdb.connect(sys.argv[1],read_only=True)
rows=c.execute("""with g as (select coalesce(sport,'NFL') sp,*, row_number() over (partition by coalesce(sport,'NFL'),player_id,stat,home,away order by ts_utc) rf
  from prop_evals where outcome is not null and outcome<>line and market_p_over is not null and model_p_over is not null and over_price is not null and under_price is not null)
 select sp, market_p_over, model_p_over, (outcome>line)::int, over_price, under_price, stat from g where rf=1""").fetchall()
def dec(a): return 1+a/100 if a>0 else 1+100/abs(a)
def ll(p,y): p=min(max(p,1e-4),1-1e-4); return -(y*math.log(p)+(1-y)*math.log(1-p))
random.seed(1)
for sp in ("NFL","NBA"):
    R=[r for r in rows if r[0]==sp]; n=len(R)
    hold=sum(1/dec(r[4])+1/dec(r[5])-1 for r in R)/n
    overs=sum(r[3] for r in R); mk=sum(r[1] for r in R)/n; md=sum(r[2] for r in R)/n
    d=[ll(r[1]+.5*(r[2]-r[1]),r[3])-ll(r[1],r[3]) for r in R]
    m=sum(d)/n; bs=[]
    for _ in range(2000):
        s=[random.choice(d) for _ in range(n)]; bs.append(sum(s)/n)
    bs.sort()
    print(f"{sp}: n={n} pinnacle hold {hold*100:.1f}% | overs hit {overs}/{n}={overs/n:.3f}, pinnacle says {mk:.3f}, model says {md:.3f} | blend-minus-pinnacle logloss {m:+.4f} 95% [{bs[50]:+.4f},{bs[1950]:+.4f}]")
print(c.execute("select sport,market,pick,price,grade,round(edge,3),dollars,kickoff_utc from playbook_picks order by first_seen_utc").fetchall())
