"""The live model-picks page (Kylor, Nov 23: "a live tracker ... so it updates the picks, only the ones you recommended via the model and not
the ones I placed myself").

Built from the same records as tracker.html (`tracker.recommendations`), but it holds only what the model sent to Telegram: staked playbook
picks and staked teaser tickets, each with its stake, limit, result and closing-line value. Nothing from the Wagerhouse account (no wagers, no
balances, no "did you bet it") and no paper picks. Rebuilt with the tracker and pushed to Vercel (`public_tracker` in config.yaml) when it changed.

The page is public to anyone with the link (a free Vercel project cannot be password-protected); the project name is random and the page
asks search engines not to index it.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engine import config
from engine.bets import tracker as tr

DEFAULTS = {"enabled": True, "project": "model-picks-fb0112", "min_minutes": 10,
            "vercel": "/Users/kylorjohnson/.nvm/versions/node/v25.2.1/bin/vercel"}
MARKETS = {"side": "Spread", "total": "Total", "team_total": "Team total", "prop": "Prop", "teaser": "Teaser"}


def settings(cfg: dict) -> dict:
    return {**DEFAULTS, **(cfg.get("public_tracker") or {})}


def site_dir(cfg: dict) -> Path:
    return config.DATA / "public_tracker" / settings(cfg)["project"]


def data(con, cfg: dict, now: datetime | None = None) -> dict:
    """Model picks only. Pure apart from reading the database."""
    now = now or datetime.now(timezone.utc)
    tz = config.display_tz(cfg)
    since = datetime.fromisoformat(tr.START).replace(tzinfo=tz).astimezone(timezone.utc)
    clv = {}
    try:
        clv = {k: c for k, c in con.execute("SELECT pick_key, clv_chance FROM playbook_grades WHERE clv_chance IS NOT NULL").fetchall()}
    except Exception:
        pass
    picks = []
    for r in tr.recommendations(con, cfg, since):
        if r.paper or not r.dollars:
            continue                         # only what reached Telegram as a bet
        status = "settled" if r.result else "live" if r.kick <= now else "upcoming"
        kick = r.kick.astimezone(tz)
        picks.append({"sport": r.sport, "market": MARKETS.get(r.market, r.market), "pick": r.pick, "game": r.game,
                      "price": r.price, "limit": r.limit or "", "stake": r.dollars, "units": round(r.dollars / r.unit, 2) if r.unit else None,
                      "sent": r.sent.astimezone(tz).isoformat(), "kick": kick.isoformat(), "day": kick.date().isoformat(),
                      "status": status, "result": {"W": "won", "L": "lost", "P": "push"}.get(r.result or ""),
                      "net": r.model_dollars if r.kind == "pick" else (None if r.profit_units is None else round(r.profit_units * r.unit, 2)),
                      "net_units": None if r.profit_units is None else round(r.profit_units, 2), "clv": clv.get(r.key)})
    picks.sort(key=lambda p: p["kick"], reverse=True)
    return {"updated": now.astimezone(tz).isoformat(), "start": tr.START, "picks": picks}


def html(d: dict) -> str:
    return TEMPLATE.replace("__DATA__", json.dumps(d).replace("</", "<\\/"))


def build(con, cfg: dict, now: datetime | None = None) -> tuple[Path, str]:
    """Write the site folder; returns (folder, hash of the picks) so a publish happens only when the picks changed."""
    d = data(con, cfg, now)
    out = site_dir(cfg)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html(d))
    (out / "vercel.json").write_text(json.dumps({"headers": [{"source": "/(.*)", "headers": [
        {"key": "X-Robots-Tag", "value": "noindex, nofollow"}, {"key": "Cache-Control", "value": "no-store"}]}]}))
    (out / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    return out, hashlib.sha256(json.dumps(d["picks"], sort_keys=True).encode()).hexdigest()


def publish(con, cfg: dict, force: bool = False, runner=subprocess.run) -> str:
    """Build, and deploy to Vercel when the picks changed (or `force`), at most every `min_minutes`. Never raises into a read."""
    st = settings(cfg)
    if not st["enabled"]:
        return "Live picks page: off (config public_tracker.enabled)."
    try:
        folder, h = build(con, cfg)
        stamp = folder.parent / f".{st['project']}.published"
        last = json.loads(stamp.read_text()) if stamp.exists() else {}
        now = datetime.now(timezone.utc).timestamp()
        if not force and (last.get("hash") == h or now - last.get("ts", 0) < 60 * st["min_minutes"]):
            return ""
        vercel = st["vercel"]
        env = {**os.environ, "PATH": f"{Path(vercel).parent}:{os.environ.get('PATH', '/usr/bin:/bin')}"}
        tok = config.load_env().get("VERCEL_TOKEN")
        cmd = [vercel, "deploy", str(folder), "--prod", "--yes"] + (["--token", tok] if tok else [])
        res = runner(cmd, capture_output=True, text=True, timeout=180, env=env)
        if res.returncode != 0:
            err = (res.stderr or res.stdout or "").strip().splitlines()
            why = next((l for l in err if "credential" in l.lower() or "login" in l.lower()), err[-1] if err else "no output")
            return f"Live picks page not published: {why[:200]}"
        url = next((l.strip() for l in reversed((res.stdout or "").splitlines()) if l.strip().startswith("https://")), "")
        stamp.write_text(json.dumps({"hash": h, "ts": now, "url": url}))
        return f"Live picks page published{': ' + url if url else ''}."
    except Exception as e:
        return f"Live picks page failed: {type(e).__name__}: {e}"


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><meta http-equiv="refresh" content="300">
<title>Model Picks</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#14171c;--muted:#667085;--line:#e4e7ec;--soft:#f1f3f6;--win:#0f8a4b;--winbg:#e6f6ee;
--loss:#c4321f;--lossbg:#fdecea;--push:#6b5bd2;--pushbg:#f0ecff;--open:#9a5b00;--openbg:#fff4e0;--live:#0b6bcb;--livebg:#e7f1fc}
@media (prefers-color-scheme:dark){:root{--bg:#0e1116;--card:#161a21;--ink:#e8eaed;--muted:#98a2b3;--line:#262c36;--soft:#1d222b;
--win:#3ccf8e;--winbg:#12301f;--loss:#ff7a66;--lossbg:#3a1a16;--push:#b4a6ff;--pushbg:#251f45;--open:#ffbf5c;--openbg:#33270f;--live:#6cb4ff;--livebg:#10263d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:760px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:4px 0 2px}.sub{color:var(--muted);font-size:13px;margin-bottom:14px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}
.stat b{display:block;font-size:18px;font-variant-numeric:tabular-nums}.stat span{color:var(--muted);font-size:12px}
.bar{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.bar button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:5px 12px;font-size:13px;cursor:pointer}
.bar button.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin:16px 0 6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:8px;display:flex;gap:10px;justify-content:space-between}
.pick{font-weight:600}.meta{color:var(--muted);font-size:13px}.right{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.tag{display:inline-block;border-radius:6px;padding:1px 8px;font-size:12px;font-weight:600}
.won{background:var(--winbg);color:var(--win)}.lost{background:var(--lossbg);color:var(--loss)}.push{background:var(--pushbg);color:var(--push)}
.upcoming{background:var(--openbg);color:var(--open)}.live{background:var(--livebg);color:var(--live)}
.empty{color:var(--muted);padding:20px 0;text-align:center}
@media (max-width:520px){.stats{grid-template-columns:repeat(2,1fr)}}
</style></head><body><main>
<h1>Model picks</h1>
<div class="sub" id="sub"></div>
<div class="stats" id="stats"></div>
<div class="bar" id="sports"></div>
<div id="list"></div>
<script>
const D=__DATA__;
const fmt=n=>(n<0?'-':'+')+'$'+Math.abs(n).toFixed(2).replace(/\.00$/,'');
const price=p=>p==null?'':(p>0?'+':'')+Math.round(p);
const when=s=>new Date(s).toLocaleString([], {weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let sport='All';
function render(){
  const ps=D.picks.filter(p=>sport==='All'||p.sport===sport);
  const done=ps.filter(p=>p.result);
  const w=done.filter(p=>p.result==='won').length,l=done.filter(p=>p.result==='lost').length,pu=done.filter(p=>p.result==='push').length;
  const net=done.reduce((a,p)=>a+(p.net||0),0), risk=done.reduce((a,p)=>a+(p.result==='push'?0:p.stake),0);
  const clv=ps.filter(p=>p.clv!=null);
  document.getElementById('stats').innerHTML=[
    [`${w}-${l}${pu?'-'+pu:''}`,'record'],[done.length?fmt(net):'$0','net'],[risk?((net/risk*100).toFixed(1)+'%'):'—','return on stakes'],
    [clv.length?((clv.reduce((a,p)=>a+p.clv,0)/clv.length*100).toFixed(1)+'%'):'—',`closing-line value (${clv.length})`]
  ].map(([b,s])=>`<div class="stat"><b>${b}</b><span>${s}</span></div>`).join('');
  const groups=[['Upcoming','upcoming'],['In play','live'],['Settled','settled']];
  let html='';
  for(const [title,key] of groups){
    const g=ps.filter(p=>p.status===key); if(!g.length) continue;
    if(key==='upcoming') g.sort((a,b)=>a.kick.localeCompare(b.kick));
    html+=`<h2>${title} (${g.length})</h2>`+g.map(p=>{
      const tag=p.result?`<span class="tag ${p.result}">${p.result}</span>`:`<span class="tag ${p.status}">${p.status==='live'?'in play':'open'}</span>`;
      const res=p.net!=null?`<div>${fmt(p.net)}</div>`:'';
      return `<div class="card"><div><div class="pick">${esc(p.pick)} ${p.market!=='Teaser'?`<span class="meta">(${price(p.price)})</span>`:''}</div>
      <div class="meta">${esc(p.sport)} · ${esc(p.market)} · ${esc(p.game)}</div>
      <div class="meta">${when(p.kick)}${p.limit?' · don\'t bet past '+esc(p.limit):''}${p.clv!=null?' · CLV '+(p.clv*100).toFixed(1)+'%':''}</div></div>
      <div class="right">${tag}<div>$${p.stake}</div>${res}</div></div>`}).join('');
  }
  document.getElementById('list').innerHTML=html||'<div class="empty">No picks sent yet.</div>';
}
const sports=['All',...new Set(D.picks.map(p=>p.sport))];
document.getElementById('sports').innerHTML=sports.map(s=>`<button data-s="${s}">${s}</button>`).join('');
document.querySelectorAll('#sports button').forEach(b=>b.onclick=()=>{sport=b.dataset.s;document.querySelectorAll('#sports button').forEach(x=>x.classList.toggle('on',x===b));render()});
document.querySelector('#sports button').classList.add('on');
document.getElementById('sub').textContent=`Every pick the model sent to Telegram since ${D.start}, graded at the stake and number sent. Updated ${when(D.updated)}; refreshes every 5 minutes.`;
render();
</script></main></body></html>
"""
