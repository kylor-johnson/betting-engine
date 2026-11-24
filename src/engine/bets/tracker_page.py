"""tracker.html: the tracker as a page (Kylor, Nov 23: "what is pending, what is done, what are results by day, week").

Built from the same data as docs/lanes/TRACKER.md (`tracker.py`), rewritten on every hourly read and by `engine tracker`. One file, no
network: the data is embedded as JSON and the page filters it in the browser (range, sport, view). Not committed (it holds the live record).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engine import config
from engine.bets import tracker as tr

PATH = config.ROOT / "tracker.html"


def _wager(w, tz) -> dict:
    settled = w.status in ("W", "L", "X")
    leg = w.legs[0] if w.legs else None
    return {"placed": w.accepted.astimezone(tz).isoformat(), "desc": w.description, "risk": w.risk, "to_win": w.to_win,
            "status": {"W": "won", "L": "lost", "X": "push"}.get(w.status, "open"), "net": round(w.net, 2) if settled else None,
            "price": None if leg is None else leg.price, "line": None if leg is None else leg.line,
            "type": "live" if w.channel == "live" else "builder" if w.channel == "builder" else {"T": "teaser", "P": "parlay"}.get(w.type_code, "straight"),
            "ignored": bool(getattr(w, "ignore", False)), "note": getattr(w, "note", "")}


def _week_label(d: datetime) -> str:
    start = (d - timedelta(days=(d.weekday() - 1) % 7)).date()
    return f"Week of {start:%b %-d}"


def data(con, cfg: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    tz = config.display_tz(cfg)
    since = datetime.fromisoformat(tr.START).replace(tzinfo=tz).astimezone(timezone.utc)
    recs = tr.recommendations(con, cfg, since)
    ws = tr.wagers(since)
    own = tr.match(recs, ws)
    clv = {}
    try:
        clv = {k: c for k, c in con.execute("SELECT pick_key, clv_chance FROM playbook_grades WHERE clv_chance IS NOT NULL").fetchall()}
    except Exception:
        pass
    picks = []
    for r in recs:
        if r.result:
            status = "settled"
        elif r.kick <= now:
            status = "live"
        else:
            status = "upcoming"
        follow = tr.grade_follow(r)
        flags = []
        if "PAST THE LIMIT" in follow:
            flags.append("past limit")
        if "worse" in follow:
            flags.append("worse number")
        if "better" in follow:
            flags.append("better number")
        if r.kind == "pick" and r.price is not None and r.matched and r.matched[0].legs and r.matched[0].legs[0].price is not None:
            if tr._dec(r.matched[0].legs[0].price) < tr._dec(r.price) * 0.97 and "PAST THE LIMIT" not in follow:
                flags.append("worse price")
        if "stake $" in follow:
            flags.append("stake off")
        mine = [_wager(w, tz) for w in r.matched]
        settled_mine = [m for m in mine if m["net"] is not None]
        kick_local = r.kick.astimezone(tz)
        picks.append({
            "id": r.key, "kind": r.kind, "sport": r.sport, "market": {"side": "Spread", "total": "Total", "team_total": "Team total", "prop": "Prop",
                                                                     "teaser": "Teaser"}.get(r.market, r.market),
            "pick": r.pick, "game": r.game, "sent": r.sent.astimezone(tz).isoformat(), "kick": kick_local.isoformat(),
            "day": kick_local.date().isoformat(), "week": _week_label(kick_local), "price": r.price, "limit": r.limit or "",
            "stake": r.dollars, "status": status, "result": {"W": "won", "L": "lost", "P": "push"}.get(r.result or "", None),
            "model_net": r.model_dollars, "clv": clv.get(r.key), "bet": bool(mine), "follow": follow.replace("bet: ", "") if mine else "not bet",
            "flags": flags, "you_risk": round(sum(m["risk"] for m in mine), 2),
            "you_net": round(sum(m["net"] for m in settled_mine), 2) if mine and len(settled_mine) == len(mine) else None, "wagers": mine})
    others = [_wager(w, tz) for w in own]
    ignored = [_wager(w, tz) for w in ws if getattr(w, "ignore", False)]
    for o in others + ignored:
        d = datetime.fromisoformat(o["placed"])
        o["day"], o["week"] = d.date().isoformat(), _week_label(d)
    return {"updated": now.astimezone(tz).isoformat(), "start": tr.START, "today": now.astimezone(tz).date().isoformat(),
            "week": _week_label(now.astimezone(tz)), "units": {s: config.unit_for(cfg, s) for s in ("NFL", "NBA", "College")},
            "picks": picks, "others": others, "ignored": ignored}


def build(con, cfg: dict, now: datetime | None = None) -> Path:
    d = data(con, cfg, now)
    PATH.write_text(TEMPLATE.replace("__DATA__", json.dumps(d).replace("</", "<\\/")))
    return PATH


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bet Tracker</title><meta http-equiv="refresh" content="900">
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#14171c;--muted:#667085;--line:#e4e7ec;--soft:#f1f3f6;--win:#0f8a4b;--winbg:#e6f6ee;--loss:#c4321f;--lossbg:#fdecea;
--push:#7a5af5;--pushbg:#f0ecff;--open:#b26a00;--openbg:#fff4e0;--live:#0b6bcb;--livebg:#e7f1fc;--accent:#14171c}
@media (prefers-color-scheme:dark){:root{--bg:#0e1116;--card:#161a21;--ink:#e8eaed;--muted:#98a2b3;--line:#262c36;--soft:#1d222b;--win:#3ccf8e;--winbg:#12301f;
--loss:#ff7a66;--lossbg:#3a1712;--push:#a996ff;--pushbg:#251f45;--open:#f5b44c;--openbg:#3a2a0e;--live:#5aa9ff;--livebg:#0f2742;--accent:#e8eaed}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,BlinkMacSystemFont,"SF Pro Text",Inter,Segoe UI,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:20px 16px 60px}
header{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:16px}
h1{font-size:26px;margin:0;letter-spacing:-.02em}.sub{color:var(--muted);font-size:13px}
.controls{display:flex;flex-wrap:wrap;gap:8px}.seg{display:inline-flex;background:var(--soft);border-radius:10px;padding:3px}
.seg button{border:0;background:transparent;color:var(--muted);padding:6px 12px;border-radius:8px;font:inherit;font-size:13px;cursor:pointer}
.seg button.on{background:var(--card);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.08);font-weight:600}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0 18px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.kpi .lab{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}.kpi .big{font-size:28px;font-weight:700;letter-spacing:-.02em;margin:4px 0 2px}
.kpi .row{display:flex;justify-content:space-between;font-size:13px;color:var(--muted)}.pos{color:var(--win)}.neg{color:var(--loss)}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin-bottom:14px;overflow-x:auto}
.tabs button{border:0;background:none;color:var(--muted);font:inherit;padding:10px 12px;border-bottom:2px solid transparent;cursor:pointer;white-space:nowrap}
.tabs button.on{color:var(--ink);border-color:var(--accent);font-weight:600}.count{background:var(--soft);border-radius:99px;padding:1px 7px;font-size:12px;margin-left:4px}
.group{margin:18px 0 8px;font-size:13px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.05em}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin-bottom:10px;display:grid;grid-template-columns:1fr auto;gap:6px 16px}
.pick{font-weight:650;font-size:16px}.game{color:var(--muted);font-size:13px}.meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:4px}
.tag{font-size:11.5px;border-radius:6px;padding:2px 7px;background:var(--soft);color:var(--muted);font-weight:600}
.badge{font-size:12px;border-radius:99px;padding:3px 10px;font-weight:700;white-space:nowrap}
.won{background:var(--winbg);color:var(--win)}.lost{background:var(--lossbg);color:var(--loss)}.push{background:var(--pushbg);color:var(--push)}
.open{background:var(--openbg);color:var(--open)}.live{background:var(--livebg);color:var(--live)}.warn{background:var(--lossbg);color:var(--loss)}.good{background:var(--winbg);color:var(--win)}
.right{text-align:right;display:flex;flex-direction:column;align-items:flex-end;gap:6px}.money{font-variant-numeric:tabular-nums;font-weight:650}
.you{grid-column:1/-1;border-top:1px dashed var(--line);padding-top:8px;display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;color:var(--muted)}
.you b{color:var(--ink);font-weight:600}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;font-variant-numeric:tabular-nums}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);font-size:14px}th{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;background:var(--soft)}
tr:last-child td{border-bottom:0}td.n{text-align:right}th.n{text-align:right}
.empty{color:var(--muted);padding:30px;text-align:center;background:var(--card);border:1px dashed var(--line);border-radius:14px}
.note{color:var(--muted);font-size:13px;margin-top:16px}
@media (max-width:820px){.kpis{grid-template-columns:repeat(2,1fr)}.card{grid-template-columns:1fr}.right{align-items:flex-start;flex-direction:row;flex-wrap:wrap}}
@media (max-width:420px){.kpi .big{font-size:22px}h1{font-size:22px}}
</style></head><body><div class="wrap">
<header><div><h1>Bet Tracker</h1><div class="sub" id="upd"></div></div>
<div class="controls"><div class="seg" id="range"><button data-v="today">Today</button><button data-v="week">This week</button><button data-v="all" class="on">All</button></div>
<div class="seg" id="sport"><button data-v="all" class="on">All</button><button data-v="NFL">NFL</button><button data-v="NBA">NBA</button><button data-v="College">College</button></div></div></header>
<section class="kpis" id="kpis"></section>
<nav class="tabs" id="tabs"></nav>
<main id="view"></main>
<p class="note">The <b>model</b> is graded at the number and stake each Telegram message sent. <b>You</b> are graded by your account: bets appear when you enter them from
the open-bets screen and are replaced by the account's own result once they settle. Grades on each pick: <span class="badge good">as sent</span>
<span class="badge good">better number</span> <span class="badge warn">worse number</span> <span class="badge warn">past limit</span> <span class="badge open">stake off</span>.</p>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
let S={range:'all',sport:'all',tab:'open'};
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const $=s=>document.querySelector(s), fmt$=v=>v==null?'—':(v<0?'−':'+')+'$'+Math.abs(v).toFixed(2).replace(/\.00$/,''), plain$=v=>'$'+(+v).toFixed(2).replace(/\.00$/,'');
const cls=v=>v==null?'':v>0?'pos':v<0?'neg':'', price=p=>p==null?'':(p>0?'+':'')+p;
const tFmt=iso=>{const d=new Date(iso);return d.toLocaleString([], {weekday:'short',hour:'numeric',minute:'2-digit'})};
const dayFmt=s=>{const d=new Date(s+'T12:00:00');return d.toLocaleDateString([], {weekday:'long',month:'short',day:'numeric'})};
function inRange(x,dayKey){if(S.range==='all')return true;if(S.range==='today')return x[dayKey||'day']===D.today||x.status==='live';return x.week===D.week}
function rows(){return D.picks.filter(p=>(S.sport==='all'||p.sport===S.sport)&&inRange(p))}
function others(){return D.others.filter(o=>inRange(o)).filter(o=>S.sport==='all'||(o.desc||'').toLowerCase().includes(S.sport==='NBA'?'basketball':'football')||S.sport==='all')}
function rec(list,key){const w=list.filter(x=>x[key]==='won').length,l=list.filter(x=>x[key]==='lost').length,p=list.filter(x=>x[key]==='push').length;return `${w}-${l}${p?'-'+p:''}`}
function kpis(){const P=rows(),set=P.filter(p=>p.status==='settled'),mNet=set.reduce((a,p)=>a+(p.model_net||0),0),mRisk=set.reduce((a,p)=>a+p.stake,0);
 const bet=P.filter(p=>p.bet),bSet=bet.filter(p=>p.you_net!=null),yNet=bSet.reduce((a,p)=>a+p.you_net,0),yRisk=bSet.reduce((a,p)=>a+p.you_risk,0);
 const O=others(),oSet=O.filter(o=>o.net!=null),oNet=oSet.reduce((a,o)=>a+o.net,0);
 const openRisk=P.filter(p=>p.status!=='settled').reduce((a,p)=>a+p.you_risk,0)+O.filter(o=>o.net==null).reduce((a,o)=>a+o.risk,0);
 const clvs=set.map(p=>p.clv).filter(v=>v!=null),clv=clvs.length?clvs.reduce((a,b)=>a+b,0)/clvs.length:null;
 const youRec=bSet.map(p=>({r:p.you_net>0?'won':p.you_net<0?'lost':'push'}));
 const mOut=P.filter(p=>p.status!=='settled').reduce((a,p)=>a+p.stake,0), yOut=bet.filter(p=>p.you_net==null).reduce((a,p)=>a+p.you_risk,0);
 const big=(n,net,out)=>n?`<div class="big ${cls(net)}">${fmt$(net)}</div>`:`<div class="big" style="color:var(--muted)">${plain$(out)}<span style="font-size:14px;font-weight:500"> out, none settled</span></div>`;
 $('#kpis').innerHTML=`
 <div class="kpi"><div class="lab">Model</div>${big(set.length,mNet,mOut)}
  <div class="row"><span>${rec(set,'result')} · ${set.length} settled</span><span>${mRisk?((mNet/mRisk)*100).toFixed(1)+'% ROI':''}</span></div>
  <div class="row"><span>${P.length} picks sent</span><span>${clv==null?'':'CLV '+(clv*100).toFixed(1)+'%'}</span></div></div>
 <div class="kpi"><div class="lab">You, on its picks</div>${big(bSet.length,yNet,yOut)}
  <div class="row"><span>${rec(youRec,'r')} · ${bSet.length} settled</span><span>${yRisk?((yNet/yRisk)*100).toFixed(1)+'% ROI':''}</span></div>
  <div class="row"><span>Followed ${bet.length} of ${P.length}</span><span>${P.filter(p=>p.flags.includes('past limit')).length} past limit</span></div></div>
 <div class="kpi"><div class="lab">You, your own bets</div>${oSet.length?`<div class="big ${cls(oNet)}">${fmt$(oNet)}</div>`:`<div class="big" style="color:var(--muted)">${O.length?plain$(O.reduce((a,o)=>a+o.risk,0)):'$0'}<span style="font-size:14px;font-weight:500"> ${O.length?'out':'none placed'}</span></div>`}
  <div class="row"><span>${rec(oSet,'status')} · ${oSet.length} settled</span><span>${O.length} placed</span></div><div class="row"><span>not on the model's list</span></div></div>
 <div class="kpi"><div class="lab">Open now</div><div class="big">${plain$(openRisk)}</div>
  <div class="row"><span>${P.filter(p=>p.status==='upcoming').length} upcoming · ${P.filter(p=>p.status==='live').length} in play</span></div><div class="row"><span>at risk, your bets</span></div></div>`}
function badge(p){if(p.status==='settled')return `<span class="badge ${p.result}">${p.result.toUpperCase()}</span>`;if(p.status==='live')return '<span class="badge live">IN PLAY</span>';return '<span class="badge open">PENDING</span>'}
function grade(p){if(!p.bet)return '<span class="badge open">not bet</span>';let b=[];if(!p.flags.length)b.push('<span class="badge good">as sent</span>');
 p.flags.forEach(f=>b.push(`<span class="badge ${f==='better number'?'good':(f==='stake off'||f==='worse price')?'open':'warn'}">${f}</span>`));return b.join(' ')}
function card(p){const w=p.wagers.map(x=>`${plain$(x.risk)} ${x.line!=null?'at '+x.line:''} ${price(x.price)} · <b class="${x.net==null?'':cls(x.net)}">${x.net==null?'open, to win '+plain$(x.to_win):fmt$(x.net)}</b>`).join(' &nbsp;|&nbsp; ');
 return `<div class="card"><div><div class="pick">${esc(p.pick)}${p.price!=null&&p.kind==='pick'?' <span class="game">('+price(p.price)+')</span>':''}</div>
  <div class="game">${esc(p.game)} · ${tFmt(p.kick)}</div><div class="meta"><span class="tag">${p.sport}</span><span class="tag">${p.market}</span>
  ${p.limit?`<span class="tag">don't bet past: ${esc(p.limit)}</span>`:''}<span class="tag">sent ${tFmt(p.sent)}</span></div></div>
  <div class="right">${badge(p)}<div class="money">Model ${p.model_net==null?plain$(p.stake)+' stake':`<span class="${cls(p.model_net)}">${fmt$(p.model_net)}</span>`}</div></div>
  <div class="you"><span>You: ${grade(p)}</span>${p.bet?`<span>${w}</span><span>${esc(p.follow)}</span>`:''}</div></div>`}
function grouped(list,keyFn,labelFn){const g={};list.forEach(p=>{(g[keyFn(p)]=g[keyFn(p)]||[]).push(p)});return Object.keys(g).sort().map(k=>`<div class="group">${labelFn(k)} · ${g[k].length}</div>`+g[k].map(card).join('')).join('')}
function summaryTable(key,label){const P=rows(),g={};P.forEach(p=>{(g[p[key]]=g[p[key]]||[]).push(p)});const ks=Object.keys(g).sort().reverse();
 if(!ks.length)return '<div class="empty">Nothing in this range yet.</div>';
 return `<table><tr><th>${label}</th><th class="n">Picks</th><th class="n">Model</th><th class="n">Model $</th><th class="n">You followed</th><th class="n">Your record</th><th class="n">Your $</th><th class="n">Open</th></tr>`+
 ks.map(k=>{const L=g[k],s=L.filter(p=>p.status==='settled'),m=s.reduce((a,p)=>a+(p.model_net||0),0),y=L.filter(p=>p.you_net!=null),yn=y.reduce((a,p)=>a+p.you_net,0);
  return `<tr><td>${key==='day'?dayFmt(k):k}</td><td class="n">${L.length}</td><td class="n">${s.length?rec(s,'result'):'—'}</td><td class="n ${cls(m)}">${s.length?fmt$(m):'—'}</td>
  <td class="n">${L.filter(p=>p.bet).length}/${L.length}</td><td class="n">${y.length?rec(y.map(p=>({r:p.you_net>0?'won':p.you_net<0?'lost':'push'})),'r'):'—'}</td>
  <td class="n ${cls(yn)}">${y.length?fmt$(yn):'—'}</td><td class="n">${L.filter(p=>p.status!=='settled').length}</td></tr>`}).join('')+'</table>'}
function marketTable(){const P=rows().filter(p=>p.status==='settled'),g={};P.forEach(p=>{const k=p.sport+' · '+p.market;(g[k]=g[k]||[]).push(p)});const ks=Object.keys(g).sort();
 if(!ks.length)return '<div class="empty">No settled picks yet. Results appear here by sport and market as games finish.</div>';
 return `<table><tr><th>Sport · market</th><th class="n">Settled</th><th class="n">Record</th><th class="n">Model $</th><th class="n">ROI</th><th class="n">CLV</th></tr>`+ks.map(k=>{const L=g[k],m=L.reduce((a,p)=>a+(p.model_net||0),0),r=L.reduce((a,p)=>a+p.stake,0),c=L.map(p=>p.clv).filter(v=>v!=null);
 return `<tr><td>${k}</td><td class="n">${L.length}</td><td class="n">${rec(L,'result')}</td><td class="n ${cls(m)}">${fmt$(m)}</td><td class="n">${r?(m/r*100).toFixed(1)+'%':'—'}</td><td class="n">${c.length?(c.reduce((a,b)=>a+b,0)/c.length*100).toFixed(1)+'%':'—'}</td></tr>`}).join('')+'</table>'}
function otherRows(list){if(!list.length)return '<div class="empty">None in this range.</div>';
 return `<table><tr><th>Placed</th><th>Bet</th><th>Type</th><th class="n">Risk</th><th class="n">Result</th></tr>`+list.map(o=>`<tr><td>${tFmt(o.placed)}</td><td>${esc(o.desc)}${o.note?'<div class="sub">'+esc(o.note)+'</div>':''}</td><td>${o.type}</td><td class="n">${plain$(o.risk)}</td><td class="n ${cls(o.net)}">${o.net==null?'<span class="badge open">open</span>':fmt$(o.net)}</td></tr>`).join('')+'</table>'}
function render(){kpis();const P=rows(),open=P.filter(p=>p.status!=='settled'),done=P.filter(p=>p.status==='settled'),O=others();
 const T=[['open','Pending',open.length],['settled','Settled',done.length],['day','By day',null],['week','By week',null],['market','By market',null],['mine','Your other bets',O.length]];
 $('#tabs').innerHTML=T.map(([k,l,n])=>`<button data-t="${k}" class="${S.tab===k?'on':''}">${l}${n!=null?`<span class="count">${n}</span>`:''}</button>`).join('');
 let h='';
 if(S.tab==='open')h=open.length?grouped(open.sort((a,b)=>a.kick.localeCompare(b.kick)),p=>p.status==='live'?'0':p.day,k=>k==='0'?'In play':dayFmt(k)):'<div class="empty">Nothing pending.</div>';
 if(S.tab==='settled')h=done.length?grouped(done.sort((a,b)=>b.kick.localeCompare(a.kick)),p=>p.day,dayFmt):'<div class="empty">Nothing settled yet. Results land the morning after each game.</div>';
 if(S.tab==='day')h=summaryTable('day','Day');if(S.tab==='week')h=summaryTable('week','Week');if(S.tab==='market')h=marketTable();
 if(S.tab==='mine')h=otherRows(O)+(D.ignored.length?'<div class="group">Left out of the model comparison</div>'+otherRows(D.ignored):'');
 $('#view').innerHTML=h;
 document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>{S.tab=b.dataset.t;render()})}
document.querySelectorAll('#range button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#range button').forEach(x=>x.classList.remove('on'));b.classList.add('on');S.range=b.dataset.v;render()});
document.querySelectorAll('#sport button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#sport button').forEach(x=>x.classList.remove('on'));b.classList.add('on');S.sport=b.dataset.v;render()});
$('#upd').textContent='Updated '+new Date(D.updated).toLocaleString([], {weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})+' · tracking since '+D.start+' · units: NFL $'+D.units.NFL+', NBA $'+D.units.NBA;
render();
</script></body></html>
"""
