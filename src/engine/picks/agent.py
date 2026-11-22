"""The scheduled research run: build numbers, let Claude research and decide, then alert.

Order of work:
  1. code builds the slate sheet
  2. Claude (headless) researches the flagged games, edits adjustments.yaml if needed,
     and writes the decisions file: status and reasons only
  3. code rebuilds the slate from fresh prices, renders the card, and sends alerts for what changed
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engine import config
from engine.alerts import telegram
from engine.odds import snapshots as snap
from engine.odds.espn import SourceError
from engine.picks import card, slate

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_runs (ts_utc TIMESTAMP, reason VARCHAR, ok BOOLEAN, note VARCHAR);
CREATE TABLE IF NOT EXISTS engine_picks (
  pick_key VARCHAR PRIMARY KEY, game VARCHAR, pick VARCHAR, status VARCHAR, book_line DOUBLE, price DOUBLE,
  fair DOUBLE, value DOUBLE, dont_bet_past VARCHAR, first_issued_utc TIMESTAMP, updated_utc TIMESTAMP, kickoff_utc TIMESTAMP);
CREATE TABLE IF NOT EXISTS engine_pick_events (
  ts_utc TIMESTAMP, pick_key VARCHAR, game VARCHAR, pick VARCHAR, status VARCHAR, book_line DOUBLE, price DOUBLE,
  fair DOUBLE, value DOUBLE, pinnacle_line DOUBLE);
"""
PROMPT_FILE = config.ROOT / "ops" / "agent_prompt.md"
LOG_DIR = Path.home() / "Library" / "Logs" / "betting-engine"


def today_mt(cfg) -> str:
    return datetime.now(config.display_tz(cfg)).strftime("%Y-%m-%d")


def decisions_path(day: str) -> Path:
    return config.ROOT / "docs" / "cards" / "decisions" / f"{day}-nfl.yaml"


def find_claude(cfg) -> str:
    path = (cfg.get("agent") or {}).get("claude_path") or shutil.which("claude")
    if not path or not Path(path).exists():
        raise SourceError("the `claude` command was not found; set agent.claude_path in config.yaml")
    return path


def run_claude(cfg, reason: str, day: str) -> tuple[bool, str]:
    claude = find_claude(cfg)
    now_mt = datetime.now(config.display_tz(cfg)).strftime("%Y-%m-%d %H:%M MT")
    prompt = PROMPT_FILE.read_text().replace("{{REASON}}", reason).replace("{{DAY}}", day).replace("{{NOW}}", now_mt)
    env = dict(os.environ)
    env["UV_PROJECT_ENVIRONMENT"] = str(config.ROOT / ".venv.nosync")
    env["PATH"] = f"{Path(claude).parent}:/opt/homebrew/bin:/usr/bin:/bin:" + env.get("PATH", "")
    cmd = [claude, "-p", prompt, "--permission-mode", "acceptEdits", "--allowedTools",
           "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch", "Bash(uv run engine:*)"]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        res = subprocess.run(cmd, cwd=str(config.ROOT), env=env, capture_output=True, text=True,
                             timeout=(cfg.get("agent") or {}).get("timeout_minutes", 25) * 60)
    except subprocess.TimeoutExpired:
        return False, "the research run timed out"
    (LOG_DIR / f"agent_{datetime.now():%Y-%m-%d_%H%M}.log").write_text(
        f"reason: {reason}\nexit: {res.returncode}\n--- output\n{res.stdout}\n--- errors\n{res.stderr}\n")
    if res.returncode != 0:
        return False, f"the research run exited with code {res.returncode}: {(res.stderr or res.stdout).strip()[-300:]}"
    return True, (res.stdout or "").strip()[-600:]


def changes(prev: dict[str, dict], rows: list[dict]) -> list[str]:
    """Alert lines for what changed since the last card. prev: pick_key -> {status, pick, ...}."""
    out = []
    for r in rows:
        key = f"{r['event_id']}|{r['market']}|{r['side']}"
        old = prev.get(key, {}).get("status")
        new = r["status"]
        live_old, live_new = old in ("Bet", "Conditional"), new in ("Bet", "Conditional")
        head = f"{r['pick']} ({int(r['price']):+d}) | {r['game']}"
        if live_new and not live_old:
            lines = [f"NEW {new.upper()}: {head}",
                     f"{r['units']:g}u (${r['dollars']:g}). Don't bet past: {r['dont_bet_past'] or 'this number'}. "
                     f"Edge {r['edge_points']:+.1f} pts, {100 * r['value']:+.1f}%."]
            d = r["decision"]
            if new == "Conditional":
                lines.append(f"Only if: {d['condition']}")
            lines.append(f"Why: {' '.join(str(d['reasons']['matchup']).split())}")
            out.append("\n".join(lines))
        elif live_old and live_new and old != new:
            out.append(f"{'CONDITIONAL IS NOW A BET' if new == 'Bet' else 'BET IS NOW CONDITIONAL'}: {head}\n"
                       f"Don't bet past: {r['dont_bet_past'] or 'this number'}."
                       + (f"\nOnly if: {r['decision']['condition']}" if new == "Conditional" else ""))
        elif live_old and not live_new:
            why = r.get("downgraded") or " ".join(str(r["decision"].get("why_pass", "")).split())
            out.append(f"WITHDRAWN: {prev[key].get('pick', r['pick'])} | {r['game']}\n{why}")
    return out


def finalize(cfg, env, day: str, send: bool = True) -> tuple[list[str], Path]:
    """Fresh prices, render the card, alert on changes, log picks."""
    sheet = slate.build_nfl(days_ahead=(cfg.get("agent") or {}).get("days_ahead", 8))
    slate.save(sheet)
    dpath = decisions_path(day)
    if not dpath.exists():
        raise SourceError(f"the research run left no decisions file at {dpath.relative_to(config.ROOT)}")
    decisions, note = card.load_decisions(dpath)
    text, rows = card.build(sheet, decisions, note, cfg, strict=False)
    out = config.ROOT / "docs" / "cards" / f"{day}.md"
    out.write_text(text)
    now = datetime.now(timezone.utc)
    ts = now.replace(tzinfo=None)
    con = snap.connect(config.DB)
    try:
        con.execute(SCHEMA)
        prev = {r[0]: {"status": r[1], "pick": r[2]} for r in con.execute(
            "SELECT pick_key, status, pick FROM engine_picks WHERE kickoff_utc > ?", [ts]).fetchall()}
        alerts = changes(prev, rows)
        pin = {g["event_id"]: g["markets"][0].get("pinnacle_line") for g in sheet["games"]}
        for r in rows:
            key = f"{r['event_id']}|{r['market']}|{r['side']}"
            kick = r["kick"].astimezone(timezone.utc).replace(tzinfo=None)
            if key in prev or r["status"] != "Pass":
                first = con.execute("SELECT first_issued_utc FROM engine_picks WHERE pick_key=?", [key]).fetchone()
                con.execute("DELETE FROM engine_picks WHERE pick_key=?", [key])
                con.execute("INSERT INTO engine_picks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            [key, r["game"], r["pick"], r["status"], r["book_line"], r["price"], r["fair"], r["value"],
                             r["dont_bet_past"], first[0] if first else ts, ts, kick])
                if prev.get(key, {}).get("status") != r["status"]:
                    con.execute("INSERT INTO engine_pick_events VALUES (?,?,?,?,?,?,?,?,?,?)",
                                [ts, key, r["game"], r["pick"], r["status"], r["book_line"], r["price"], r["fair"],
                                 r["value"], pin.get(r["event_id"]) if r["market"] == "spread" else None])
            # arm the watchlist at the number that would make a pass a bet
            if r["status"] == "Pass" and not r["numbers_say_bet"] and r.get("limit_line") is not None and r["market"] == "spread":
                team = r["pick"].rsplit(" ", 1)[0]
                target = r["limit_line"] if r["side"] == "home" else -r["limit_line"]
                if not con.execute("SELECT 1 FROM watchlist WHERE active AND team=? AND market='spread' AND target=?", [team, target]).fetchone():
                    nid = con.execute("SELECT coalesce(max(id), 0) + 1 FROM watchlist").fetchone()[0]
                    con.execute("INSERT INTO watchlist VALUES (?,?,?,?,?,?,?,?)", [nid, ts, team, "spread", target, -115.0, f"engine {day}", True])
    finally:
        con.close()
    sent = []
    for a in alerts:
        msg = f"{a}\nCard: docs/cards/{day}.md"
        if send:
            telegram.send(env, msg)
        sent.append(msg)
    return sent, out


def run(reason: str, send: bool = True, skip_research: bool = False) -> tuple[int, list[str]]:
    cfg, env = config.load_config(), config.load_env()
    day = today_mt(cfg)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    lines: list[str] = []
    con = snap.connect(config.DB)
    con.execute(SCHEMA)
    con.close()

    def record(ok: bool, note: str):
        c = snap.connect(config.DB)
        try:
            c.execute("INSERT INTO agent_runs VALUES (?,?,?,?)", [now, reason, ok, note[:500]])
        finally:
            c.close()

    try:
        sheet = slate.build_nfl(days_ahead=(cfg.get("agent") or {}).get("days_ahead", 8))
        slate.save(sheet)
        if not skip_research:
            ok, note = run_claude(cfg, reason, day)
            if not ok:
                raise SourceError(note)
            lines.append(note)
        sent, path = finalize(cfg, env, day, send)
        lines.append(f"Card: {path.relative_to(config.ROOT)}. {len(sent)} alert(s).")
        lines += sent
        record(True, f"{len(sent)} alerts")
        return 0, lines
    except Exception as e:
        msg = str(e) if isinstance(e, SourceError) else f"{type(e).__name__}: {e}"
        record(False, msg)
        if send:
            try:
                telegram.send(env, f"Research run FAILED ({reason}): {msg[:600]}")
            except SourceError:
                pass
        return 1, lines + [f"Research run FAILED: {msg}"]


def cooled_down(con, now: datetime, minutes: int) -> bool:
    con.execute(SCHEMA)
    last = con.execute("SELECT max(ts_utc) FROM agent_runs").fetchone()[0]
    return last is None or (now.replace(tzinfo=None) - last) > timedelta(minutes=minutes)


def spawn(reason: str) -> None:
    """Start a research run in the background (used by the hourly read when news lands)."""
    env = dict(os.environ)
    env["UV_PROJECT_ENVIRONMENT"] = str(config.ROOT / ".venv.nosync")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = open(LOG_DIR / "agent.log", "a")
    subprocess.Popen(["/opt/homebrew/bin/uv", "run", "--project", str(config.ROOT), "engine", "agent", "--reason", reason],
                     cwd=str(Path.home()), env=env, stdout=log, stderr=log, start_new_session=True)
