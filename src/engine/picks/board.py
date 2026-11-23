"""A plain web page showing the current picks. Rebuilt after every research run."""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from engine import config
from engine.picks import card

BOARD = config.ROOT / "board.html"
LABEL = {"NFL": "NFL", "College": "College football", "NBA": "NBA"}
CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#14181f;--mut:#667085;--line:#e4e7ec;--go:#0a7a3d;--gobg:#e7f6ec;--wait:#9a5b00;--waitbg:#fff4dc;--no:#667085;--nobg:#eef0f3}
@media (prefers-color-scheme:dark){:root{--bg:#0f1216;--card:#181c22;--ink:#eef1f5;--mut:#98a2b3;--line:#2a303a;--go:#4ade80;--gobg:#10301d;--wait:#fbbf24;--waitbg:#33270a;--no:#98a2b3;--nobg:#20252d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:920px;margin:0 auto;padding:24px 16px 64px}h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:36px 0 12px}
.sub{color:var(--mut);font-size:14px}.pick{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:12px 0}
.tag{display:inline-block;font-weight:700;font-size:13px;letter-spacing:.04em;padding:4px 10px;border-radius:999px}
.go .tag{color:var(--go);background:var(--gobg)}.wait .tag{color:var(--wait);background:var(--waitbg)}.none .tag{color:var(--no);background:var(--nobg)}
.go{border-left:6px solid var(--go)}.wait{border-left:6px solid var(--wait)}
.bet{font-size:24px;font-weight:700;margin:10px 0 2px}.game{color:var(--mut);margin-bottom:12px}
.row{display:flex;gap:28px;flex-wrap:wrap;margin:10px 0}.row div{min-width:120px}.k{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}.v{font-size:18px;font-weight:600}
.cond{background:var(--waitbg);border-radius:10px;padding:10px 14px;margin:10px 0;font-weight:600}.why{margin-top:10px}
details{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:10px 0;padding:0 16px}summary{cursor:pointer;padding:14px 0;font-weight:600}
table{width:100%;border-collapse:collapse;font-size:14px;margin:0 0 14px}th,td{text-align:left;padding:7px 8px;border-top:1px solid var(--line);white-space:nowrap}th{color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase}
td.g{white-space:normal}.close li{margin:8px 0}.wrap{overflow-x:auto}
"""


def _e(x) -> str:
    return html.escape(str(x))


def _latest_decisions(sport: str) -> Path | None:
    files = sorted((config.ROOT / "docs" / "cards" / "decisions").glob(f"*-{sport.lower()}.yaml"))
    return files[-1] if files else None


def _limit(r) -> str:
    return (r.get("dont_bet_past") or r["pick"]).rsplit(" ", 1)[-1]


def _when(kick, tz) -> str:
    local, today = kick.astimezone(tz), datetime.now(tz).date()
    day = "Today" if local.date() == today else "Tomorrow" if (local.date() - today).days == 1 else f"{local:%a %b %-d}"
    return f"{day} {local:%-I:%M %p}"


def _num(x, signed=True) -> str:
    if x is None:
        return "–"
    return f"{x:+g}" if signed else f"{x:g}"


def _lanes_html(cfg) -> str:
    from engine import lanes
    from engine.odds import snapshots as snap
    try:
        con = snap.connect(config.DB)
        try:
            return lanes.table_html(cfg, con)
        finally:
            con.close()
    except Exception as e:
        return f"<p class=sub>Lane status could not be read: {_e(type(e).__name__)}: {_e(e)}</p>"


def _leans_html(cfg, tz) -> str:
    from engine.odds import snapshots as snap
    from engine.picks import leans
    try:
        con = snap.connect(config.DB)
        try:
            rows = leans.open_leans(con)
            head = f"<p class=sub>{_e(leans.summary_text(cfg, con))}</p>"
        finally:
            con.close()
    except Exception as e:
        return f"<p class=sub>Leans could not be read: {_e(type(e).__name__)}: {_e(e)}</p>"
    items = "".join(f"<li><b>{_e(r['pick'])} ({int(r['price']):+d})</b> <span class=sub>{_e(r['game'])}, {_e(r['reason_type'])}. "
                    f"Don't bet past {_e(r['dont_bet_past'])}.</span><br>{_e(r['reason'])}</li>" for r in rows)
    return head + ("<ul class=close>" + items + "</ul>" if items else "<p class=sub>No open Leans.</p>")


def _grades_html(tz) -> str:
    """Graded engine picks: totals by status, then the latest ten. Read-only; failures show on the page."""
    from engine.odds import snapshots as snap
    from engine.picks import grade
    try:
        con = snap.connect(config.DB)
        try:
            lines = grade.summary(con, config.load_config())
            rows = con.execute("SELECT pick, game, status, result, clv_points, profit_units, issued_line, price FROM engine_pick_grades "
                               "ORDER BY graded_utc DESC, pick LIMIT 10").fetchall()
        finally:
            con.close()
    except Exception as e:
        return f"<p class=sub>Grading could not be read: {_e(type(e).__name__)}: {_e(e)}</p>"
    out = "<ul class=close>" + "".join(f"<li>{_e(l)}</li>" for l in lines) + "</ul>"
    if rows:
        out += ("<div class=wrap><table><tr><th>Pick</th><th>Status</th><th>Result</th><th>Points vs Pinnacle close</th><th>Units</th></tr>"
                + "".join(f"<tr><td class=g>{_e(r[0])}<br><span class=sub>{_e(r[1])}</span></td><td>{_e(r[2])}</td><td>{_e(r[3])}</td>"
                          f"<td>{"n/a" if r[4] is None else format(r[4], "+.1f")}</td><td>{r[5]:+.2f}</td></tr>" for r in rows) + "</table></div>"
                "<p class=sub>Points vs Pinnacle close: positive means the number you could have had beat the sharp book's last line. "
                "A compass, not proof. Passes show what passing was worth; no money was risked on them.</p>")
    else:
        out += "<p class=sub>No pick has been graded yet; a pick is graded after its game ends.</p>"
    return out


def build() -> Path:
    cfg = config.load_config()
    tz = config.display_tz(cfg)
    now = datetime.now(tz)
    bets, waits, close, tables, stale = [], [], [], [], []
    for sport in ("NFL", "College", "NBA"):
        sp = config.DATA / "slates" / f"{sport}_latest.json"
        if not sp.exists():
            continue
        sheet = json.loads(sp.read_text())
        built = datetime.fromisoformat(sheet["built_utc"]).astimezone(tz)
        rows = []
        dpath = _latest_decisions(sport)
        if dpath and sheet["games"]:
            decisions, _ = card.load_decisions(dpath)
            _, rows = card.build(sheet, decisions, "", cfg, strict=False)
        rows = [r for r in rows if r["kick"] > now]
        for r in rows:
            r["sport"] = sport
            (bets if r["status"] == "Bet" else waits if r["status"] == "Conditional" else close).append(r)
        if (now - built).total_seconds() > 6 * 3600:
            stale.append(f"{LABEL[sport]} numbers are from {built:%a %-I:%M %p}")
        trs = []
        for g in sheet["games"]:
            kick = datetime.fromisoformat(g["start_utc"]).astimezone(tz)
            if kick < now:
                continue
            s = g["markets"][0]
            best = max(s.get("sides", []), key=lambda x: x["value"], default=None)
            lean = f"{_e(best['pick'])} ({100 * best['value']:+.1f}%)" if best and best["value"] > 0 else "–"
            trs.append(f"<tr><td class=g>{_e(g['away'])} at {_e(g['home'])}</td><td>{_when(kick, tz)}</td>"
                       f"<td>{_num(s.get('book_line'))}</td><td>{_num(s.get('pinnacle_line'))}</td><td>{_num(s.get('fair_line'))}</td><td>{lean}</td></tr>")
        if trs:
            tables.append(f"<details><summary>{LABEL[sport]}: all {len(trs)} games and their numbers (updated {built:%a %-I:%M %p})</summary><div class=wrap><table>"
                          "<tr><th>Game</th><th>Start</th><th>Your book</th><th>Pinnacle</th><th>Fair line</th><th>Numbers lean to</th></tr>"
                          + "".join(trs) + "</table></div><p class=sub>Lines are the home team's spread: a minus sign means the home team is favored. "
                          "\"Numbers lean to\" is only where the math points; it is not a pick without a reason behind it.</p></details>")

    def pick_card(r, cls, tag):
        d = r["decision"]
        cond = f"<div class=cond>Bet only if: {_e(' '.join(str(d['condition']).split()))}</div>" if r["status"] == "Conditional" else ""
        return (f"<div class='pick {cls}'><span class=tag>{tag}</span> <span class=sub>{LABEL[r['sport']]}</span>"
                f"<div class=bet>{_e(r['pick'])} <span class=sub>({int(r['price']):+d})</span></div>"
                f"<div class=game>{_e(r['game'])} · {_when(r['kick'], tz)}</div>{cond}"
                f"<div class=row><div><div class=k>Stake</div><div class=v>${r['dollars']:g}</div></div>"
                f"<div><div class=k>Skip if worse than</div><div class=v>{_e(_limit(r))}</div></div>"
                f"<div><div class=k>Edge</div><div class=v>{r['edge_points']:+.1f} pts</div></div></div>"
                f"<div class=why><b>Why:</b> {_e(' '.join(str(d.get('summary') or d['reasons']['situation']).split()))}</div>"
                f"<div class=why><b>What kills it:</b> {_e(' '.join(str(d['reasons']['kills_it']).split()))}</div></div>")

    parts = [f"<h1>Betting board</h1><div class=sub>Updated {now:%A %b %-d, %-I:%M %p} Mountain. This page refreshes itself. "
             f"Unit ${cfg['unit']}. You place every bet yourself.</div>"]
    if stale:
        parts.append(f"<div class=sub>Note: {_e('; '.join(stale))}.</div>")
    parts.append("<h2>Bet now</h2>")
    parts.append("".join(pick_card(r, "go", "BET NOW") for r in bets) or
                 "<div class='pick none'><span class=tag>NOTHING TO BET</span><div class=why>No pick clears the bar right now. That is the normal state.</div></div>")
    if waits:
        parts.append("<h2>Waiting on something (do not bet yet)</h2>" + "".join(pick_card(r, "wait", "WAIT") for r in waits))
    if close:
        parts.append("<h2>Came close, and why not</h2><ul class=close>" + "".join(
            f"<li><b>{_e(r['pick'])}</b> <span class=sub>({LABEL[r['sport']]}, {_when(r['kick'], tz)})</span><br>"
            f"{_e(r.get('downgraded') or ' '.join(str(r['decision'].get('why_pass', '')).split()))}</li>" for r in close) + "</ul>")
    parts.append("<h2>The five lanes: what each one looks at, and its record</h2>" + _lanes_html(cfg))
    parts.append("<h2>Paper Leans (unproven, never staked)</h2>" + _leans_html(cfg, tz))
    parts.append("<h2>How the engine's picks have done</h2>" + _grades_html(tz))
    parts.append("<h2>Every game</h2>" + ("".join(tables) or "<p class=sub>No games priced yet.</p>"))
    page = ("<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            "<meta http-equiv=refresh content=120><title>Betting board</title><style>" + CSS + "</style></head><body><main>"
            + "".join(parts) + "</main></body></html>")
    BOARD.write_text(page)
    return BOARD
