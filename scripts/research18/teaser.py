import duckdb, sys, math
c=duckdb.connect()
g=c.execute(f"select season, game_type, spread_line, total_line, result from read_csv_auto('{sys.argv[1]}') where result is not null and spread_line is not null").fetchall()
def legs(rows, totmax=None):
    out=[]
    for s,gt,sp,tot,res in rows:
        if totmax and tot is not None and tot>totmax: continue
        # home spread from home perspective: home line = -sp ; home covers teased if res + (-sp) + 6 > 0
        for line,margin,kind in ((-sp,res,'home'),(sp,-res,'away')):
            # line: this team's spread (negative=favorite)
            if -8.5<=line<=-7.5 or 1.5<=line<=2.5:
                v=margin+line+6
                if v!=0: out.append((s,v>0,'fav' if line<0 else 'dog'))
    return out
def wilson(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return c-h,c+h
for lab,f in (('2001-2014',lambda s:2001<=s<=2014),('2015-2022',lambda s:2015<=s<=2022),('2023-2026',lambda s:s>=2023),('2015-2026',lambda s:s>=2015)):
  for tm in (None,49):
    L=[x for x in legs([r for r in g if f(r[0])],tm)]
    for k in ('all','fav','dog'):
      LL=[x for x in L if k=='all' or x[2]==k]
      n=len(LL);w=sum(x[1] for x in LL)
      if n: lo,hi=wilson(w,n); print(f"{lab} tot<={tm} {k}: {w}/{n} = {w/n:.3f}  95% {lo:.3f}-{hi:.3f}  ticketEV@-110 = {((w/n)**2*(1+100/110)-1)*100:+.1f}%")
