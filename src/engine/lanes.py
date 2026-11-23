"""The lanes (five from the charter, plus NFL Wong teasers since 2026-11-24) and the generated status table (CHARTER.md, drift guard).

Everything here is built from `config.yaml` (the `lanes:` section and the switches it points to) and the
database. Nothing about a lane is typed by hand in a card, a message or the status table.
"""
from __future__ import annotations

import hashlib
from datetime import timezone
from pathlib import Path

from engine import config

STATUS_WORDS = {
    "passed": "passed a test",
    "passed_weak": "passed a test, weaker lately",
    "testing": "still being tested",
    "failed": "tested, failed, switched off",
    "overridden": "ON by Kylor's choice; its walk-forward test gave it no weight",
}


def _get(cfg: dict, dotted: str):
    cur = cfg
    for part in dotted.split("."):
        cur = (cur or {}).get(part) if isinstance(cur, dict) else None
    return cur


def lanes(cfg: dict) -> dict:
    return cfg.get("lanes") or {}


def model_on(cfg: dict, m: dict) -> bool:
    """A model is on only if it has a switch and the switch is on. Failed models have no switch: they are off."""
    if m.get("status") == "failed":
        return False
    return bool(_get(cfg, m["switch"])) if m.get("switch") else False


def inputs_on(lane: dict) -> list[str]:
    return [k for k, v in (lane.get("inputs") or {}).items() if v.get("enabled")]


def can_produce(cfg: dict, lane: dict) -> str:
    """What can produce a pick in this lane today, from its switches and test results."""
    pc = cfg.get("picks") or {}
    if lane["kind"] == "teaser":
        from engine.picks import teasers
        st = teasers.settings(cfg)
        if not st["enabled"]:
            return "Nothing (switched off)."
        if st.get("real_money"):
            return (f"A 2-team {st['points']:g}-point teaser (A pick, real money) whenever two qualifying legs are open; judged at "
                    f"{st['kill_after_legs']} graded legs against {teasers.breakeven(st['price']):.1%} (decisions 0014, 0019).")
        return (f"Nothing staked. Paper teasers only, until {st['kill_after_legs']} legs are graded and at least "
                f"{teasers.breakeven(st['price']):.1%} win (decision 0014).")
    if lane["kind"] == "props":
        need = ((cfg.get("models") or {}).get("props") or {}).get("min_graded", 300)
        return f"Nothing. Testing only until {need} props are graded and the test is passed."
    parts = []
    news = [k for k in ("news_adjustments", "injury_news") if (lane.get("inputs") or {}).get(k, {}).get("enabled")]
    if news:
        parts.append("a Bet or Conditional on news Pinnacle has not yet moved for")
    for name, m in (lane.get("models") or {}).items():
        if model_on(cfg, m) and m["status"] in ("passed", "passed_weak"):
            cap = ((cfg.get("models") or {}).get(name) or {}).get("max_status", "Bet")
            parts.append(f"{name.replace('_', ' ')} ({cap} at most)")
        elif model_on(cfg, m) and m["status"] == "overridden":
            parts.append(f"{name.replace('_', ' ')} (B picks, half a unit; real money)")
    if not parts:
        return "Nothing."
    stake = f"Bet {pc.get('max_units', 1)} unit, Conditional {pc.get('conditional_units', 0.5)} unit"
    return "; ".join(parts) + f". {stake}. A price gap alone cannot."


def record(con, cfg: dict, lane: dict) -> dict:
    """Graded record and the date of the last pick, from the database."""
    out = {"graded": 0, "line": "", "last_pick": None}
    sport = lane["sport"]
    if lane["kind"] == "teaser":
        from engine.picks import teasers
        try:
            rec = teasers.record(con, cfg)
            last = con.execute("SELECT max(first_seen_utc) FROM teaser_legs").fetchone()[0]
        except Exception as e:
            return {**out, "line": f"Teaser record unavailable: {type(e).__name__}"}
        out.update(graded=rec["graded"], last_pick=last, line=teasers.record_text(rec, cfg))
        return out
    if lane["kind"] == "props":
        from engine.models import props
        pc = (cfg.get("models") or {}).get("props") or {}
        try:
            from engine import version
            pv = version.props_version(cfg)
            sc = props.scorecard(con, pc.get("edge", 0.05), sport=sport, version=pv)
            n = sc.get("graded", 0)
            paper = props.paper_text(props.paper_record(con, sport, pv))
        except Exception as e:
            return {**out, "line": f"Props record unavailable: {type(e).__name__}"}
        need = pc.get("min_graded", 300)
        out.update(graded=n, line=f"No bets. {n} of {need} props graded for the current model version. {paper}")
        return out
    try:
        w, l, p, units, clv = con.execute(
            "SELECT count(*) FILTER (result='W'), count(*) FILTER (result='L'), count(*) FILTER (result='P'), "
            "coalesce(sum(profit_units),0), avg(clv_points) FROM engine_pick_grades "
            "WHERE sport=? AND status IN ('Bet','Conditional')", [sport]).fetchone()
        passes = con.execute("SELECT count(*) FROM engine_pick_grades WHERE sport=? AND status='Pass'", [sport]).fetchone()[0]
        last = con.execute(
            "SELECT max(e.ts_utc) FROM engine_pick_events e JOIN (SELECT DISTINCT event_id, sport FROM line_snapshots) s "
            "ON split_part(e.pick_key,'|',1)=s.event_id WHERE s.sport=? AND e.status<>'Pass'", [sport]).fetchone()[0]
    except Exception:
        return {**out, "line": "Record unavailable (database not readable right now)."}
    n = w + l + p
    clv_txt = "closing-line value n/a" if clv is None else f"average {clv:+.2f} points vs Pinnacle close"
    out.update(graded=n, last_pick=last)
    out["line"] = (f"{w}-{l}-{p} on {n} graded pick(s), {units:+.2f} units, {clv_txt}" if n else "0-0, no graded picks yet")
    if passes:
        out["line"] += f"; {passes} flagged Pass(es) graded"
    return out


def rows(cfg: dict, con) -> list[dict]:
    out = []
    for key, lane in lanes(cfg).items():
        models = [{"name": n, "on": model_on(cfg, m), "status": m["status"], "words": STATUS_WORDS[m["status"]],
                   "note": m.get("note", ""), "doc": m.get("doc", "")} for n, m in (lane.get("models") or {}).items()]
        rec = record(con, cfg, lane) if con is not None else {"line": "n/a", "last_pick": None, "graded": 0}
        out.append({"key": key, "title": lane["title"], "short": lane["short"], "sport": lane["sport"], "kind": lane["kind"],
                    "inputs_on": [(k, v["text"]) for k, v in (lane.get("inputs") or {}).items() if v.get("enabled")],
                    "inputs_off": [(k, v["text"]) for k, v in (lane.get("inputs") or {}).items() if not v.get("enabled")],
                    "models": models, "can_produce": can_produce(cfg, lane),
                    "not_evaluating": lane.get("not_evaluating", []), "record": rec})
    return out


def table_markdown(cfg: dict, con) -> str:
    """The charter's status table, generated. One row per lane."""
    head = ["| Lane | Inputs switched on | Models (test result) | What can produce a pick today | Record | Last pick |", "|---|---|---|---|---|---|"]
    body = []
    for r in rows(cfg, con):
        ins = "; ".join(k.replace("_", " ") for k, _ in r["inputs_on"]) or "none"
        off = ("; off: " + ", ".join(k.replace("_", " ") for k, _ in r["inputs_off"])) if r["inputs_off"] else ""
        models = "<br>".join(f"{m['name'].replace('_', ' ')}: {'ON' if m['on'] else 'off'}, {m['words']}" for m in r["models"]) or "none"
        last = r["record"]["last_pick"]
        last_txt = "never" if last is None else last.replace(tzinfo=timezone.utc).astimezone(config.display_tz(cfg)).strftime("%a %b %-d")
        body.append(f"| {r['title']} | {ins}{off} | {models} | {r['can_produce']} | {r['record']['line']} | {last_txt} |")
    return "\n".join(head + body)


def table_text(cfg: dict, con) -> str:
    """Phone-sized version for Telegram: one short block per lane."""
    out = []
    for r in rows(cfg, con):
        on = [m for m in r["models"] if m["on"]]
        out.append(f"{r['short']}\n  looks at: {', '.join(k.replace('_', ' ') for k, _ in r['inputs_on'])}"
                   f"\n  models on: {', '.join(m['name'].replace('_', ' ') + ' (' + m['words'] + ')' for m in on) or 'none'}"
                   f"\n  can pick: {r['can_produce']}\n  record: {r['record']['line']}")
    return "\n\n".join(out)


def structure(cfg: dict) -> dict:
    """What the table says apart from records: per lane, inputs on, each model's switch and result, what can produce a pick."""
    return {r["key"]: {"inputs_on": [k for k, _ in r["inputs_on"]],
                       "models": {m["name"]: f"{'ON' if m['on'] else 'off'}, {m['words']}" for m in r["models"]},
                       "can_produce": r["can_produce"]} for r in rows(cfg, None)}


def structure_hash(cfg: dict) -> str:
    """Changes when what a lane looks at, which models are on or their results, or what can produce a pick changes.
    Records are left out on purpose: the table is re-sent when its structure changes, not after every graded pick."""
    import json
    return hashlib.sha256(json.dumps(structure(cfg), sort_keys=True).encode()).hexdigest()[:16]


def diff_text(old: dict, new: dict) -> list[str]:
    """Plain sentences on what changed between two structures."""
    out = []
    for key in sorted(set(old) | set(new)):
        a, b = old.get(key), new.get(key)
        if a is None or b is None:
            out.append(f"{key}: lane {'added' if a is None else 'removed'}")
            continue
        for k in sorted(set(a["inputs_on"]) ^ set(b["inputs_on"])):
            out.append(f"{key}: input {k.replace('_', ' ')} switched {'on' if k in b['inputs_on'] else 'off'}")
        for m in sorted(set(a["models"]) | set(b["models"])):
            if a["models"].get(m) != b["models"].get(m):
                out.append(f"{key}: model {m.replace('_', ' ')}: {a['models'].get(m, 'not listed')} -> {b['models'].get(m, 'removed')}")
        if a["can_produce"] != b["can_produce"]:
            out.append(f"{key}: what can produce a pick changed to: {b['can_produce']}")
    return out


SCHEMA = "CREATE TABLE IF NOT EXISTS status_snapshots (ts_utc TIMESTAMP, hash VARCHAR, structure VARCHAR)"


def check_changed(con, cfg: dict, now) -> str | None:
    """Compare the structure with the last one stored. Returns the message to send if it changed (and stores the new one).
    The first ever call stores a baseline and returns None."""
    import json
    con.execute(SCHEMA)
    h, st = structure_hash(cfg), structure(cfg)
    last = con.execute("SELECT hash, structure FROM status_snapshots ORDER BY ts_utc DESC LIMIT 1").fetchone()
    if last is not None and last[0] == h:
        return None
    con.execute("INSERT INTO status_snapshots VALUES (?,?,?)", [now.replace(tzinfo=None), h, json.dumps(st, sort_keys=True)])
    if last is None:
        return None
    changes = diff_text(json.loads(last[1]), st)
    return "LANE STATUS CHANGED\n" + "\n".join(f"- {c}" for c in changes) + "\n\nNow:\n" + table_text(cfg, con)


def lane_for(cfg: dict, sport: str, kind: str = "game") -> dict | None:
    for lane in lanes(cfg).values():
        if lane["sport"] == sport and lane["kind"] == kind:
            return lane
    return None


def card_block(cfg: dict, con, sport: str) -> list[str]:
    """The lane header printed at the top of a card: what this lane looks at and does not, and its record. Generated."""
    lane = lane_for(cfg, sport)
    if lane is None:
        return []
    r = next(x for x in rows(cfg, con) if x["title"] == lane["title"])
    on = [m for m in r["models"] if m["on"]]
    out = [f"**Lane: {r['title']}.**",
           f"- Looking at: {' '.join(t for _, t in r['inputs_on'])}",
           f"- Own models switched on: {', '.join(m['name'].replace('_', ' ') + ' (' + m['words'] + ')' for m in on) or 'none'}",
           f"- Not looking at: {', '.join(r['not_evaluating'])}.",
           f"- Can produce a pick: {r['can_produce']}",
           f"- Record: {r['record']['line']}", ""]
    return out


def props_footer(cfg: dict, con, sport: str) -> str:
    """One line on the props lane for this sport, added to the game lane's messages."""
    lane = lane_for(cfg, sport, "props")
    if lane is None:
        return ""
    return f"{lane['short']} lane: {record(con, cfg, lane)['line']}"


def thread_key(cfg: dict, sport: str, kind: str = "game") -> str | None:
    for k, lane in lanes(cfg).items():
        if lane["sport"] == sport and lane["kind"] == kind:
            return k
    return None


def tag(cfg: dict, sport: str, kind: str = "game") -> str:
    lane = lane_for(cfg, sport, kind)
    return lane["short"] if lane else sport


def table_html(cfg: dict, con) -> str:
    """The same table as a section of board.html."""
    import html
    e = html.escape
    trs = []
    for r in rows(cfg, con):
        last = r["record"]["last_pick"]
        last_txt = "never" if last is None else last.replace(tzinfo=timezone.utc).astimezone(config.display_tz(cfg)).strftime("%a %b %-d")
        models = "<br>".join(f"{e(m['name'].replace('_', ' '))}: <b>{'ON' if m['on'] else 'off'}</b>, {e(m['words'])}" for m in r["models"]) or "none"
        ins = "; ".join(e(k.replace("_", " ")) for k, _ in r["inputs_on"]) or "none"
        off = f"<br><span class=sub>off: {e(', '.join(k.replace('_', ' ') for k, _ in r['inputs_off']))}</span>" if r["inputs_off"] else ""
        trs.append(f"<tr><td class=g><b>{e(r['title'])}</b></td><td class=g>{ins}{off}</td><td class=g>{models}</td>"
                   f"<td class=g>{e(r['can_produce'])}</td><td class=g>{e(r['record']['line'])}<br><span class=sub>last pick: {last_txt}</span></td></tr>")
    return ("<div class=wrap><table><tr><th>Lane</th><th>Looks at</th><th>Models</th><th>Can produce a pick</th><th>Record</th></tr>"
            + "".join(trs) + "</table></div><p class=sub>Generated from config.yaml and the database, never typed by hand.</p>")


def write_status_file(cfg: dict, con) -> "Path":
    """docs/lanes/STATUS.md, regenerated; committed with any change to what a lane does."""
    from datetime import datetime
    path = config.ROOT / "docs" / "lanes" / "STATUS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(config.display_tz(cfg)).strftime("%a %b %-d %Y, %-I:%M %p")
    path.write_text("# Lane status (generated by `engine status`; do not edit by hand)\n\n"
                    f"Generated {stamp} Mountain from `config.yaml` (`lanes:` and the switches it points to) and the database.\n\n"
                    + table_markdown(cfg, con) + "\n\n## What each lane will not do\n\n"
                    + "\n".join(f"- **{r['title']}**: " + "; ".join(r["not_evaluating"]) for r in rows(cfg, con)) + "\n")
    return path
