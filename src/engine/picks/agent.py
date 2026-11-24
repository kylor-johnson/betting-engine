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

from engine import config, lanes
from engine.alerts import telegram
from engine.odds import snapshots as snap
from engine.odds.espn import SourceError
from engine.picks import card, slate

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_runs (ts_utc TIMESTAMP, reason VARCHAR, ok BOOLEAN, note VARCHAR);
CREATE TABLE IF NOT EXISTS engine_picks (
  pick_key VARCHAR PRIMARY KEY, game VARCHAR, pick VARCHAR, status VARCHAR, book_line DOUBLE, price DOUBLE,
  fair DOUBLE, value DOUBLE, dont_bet_past VARCHAR, first_issued_utc TIMESTAMP, updated_utc TIMESTAMP, kickoff_utc TIMESTAMP);
ALTER TABLE engine_picks ADD COLUMN IF NOT EXISTS rule_version VARCHAR;
CREATE TABLE IF NOT EXISTS engine_pick_events (
  ts_utc TIMESTAMP, pick_key VARCHAR, game VARCHAR, pick VARCHAR, status VARCHAR, book_line DOUBLE, price DOUBLE,
  fair DOUBLE, value DOUBLE, pinnacle_line DOUBLE);
ALTER TABLE engine_pick_events ADD COLUMN IF NOT EXISTS rule_version VARCHAR;
"""
PROMPT_FILE = config.ROOT / "ops" / "agent_prompt.md"
LOG_DIR = Path.home() / "Library" / "Logs" / "betting-engine"


WIND_LOG = """
CREATE TABLE IF NOT EXISTS wind_forecasts (
  ts_utc TIMESTAMP, event_id VARCHAR, game VARCHAR, kickoff_utc TIMESTAMP, hours_to_kickoff DOUBLE, wind_mph DOUBLE, temp_f DOUBLE,
  precip_mm DOUBLE, model_points DOUBLE, used BOOLEAN, book_total DOUBLE, pinnacle_total DOUBLE);
"""


def log_wind(con, sheet: dict, ts) -> int:
    """Store the forecast the wind model used at each read, with the totals at that moment. Audit item 24: the wind model was tested on
    realized wind; this builds the history needed to test it on the forecast that was actually available at bet time."""
    con.execute(WIND_LOG)
    n = 0
    for g in sheet.get("games", []):
        for m in g["markets"]:
            w = m.get("wind_model") if m["market"] == "total" else None
            if not w:
                continue
            con.execute("INSERT INTO wind_forecasts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        [ts, g["event_id"], g["game"], datetime.fromisoformat(g["start_utc"]).astimezone(timezone.utc).replace(tzinfo=None),
                         w.get("hours_to_kickoff"), w.get("wind_mph"), w.get("temp_f"), w.get("precip_mm"), w.get("points"), bool(w.get("used")),
                         m.get("book_line"), m.get("pinnacle_line")])
            n += 1
    return n


def today_mt(cfg) -> str:
    return datetime.now(config.display_tz(cfg)).strftime("%Y-%m-%d")


def decisions_path(day: str, sport: str = "NFL") -> Path:
    return config.ROOT / "docs" / "cards" / "decisions" / f"{day}-{sport.lower()}.yaml"


def card_path(day: str, sport: str) -> Path:
    return config.ROOT / "docs" / "cards" / f"{day}-{sport.lower()}.md"


def find_claude(cfg) -> str:
    path = (cfg.get("agent") or {}).get("claude_path") or shutil.which("claude")
    if not path or not Path(path).exists():
        raise SourceError("the `claude` command was not found; set agent.claude_path in config.yaml")
    return path


def run_claude(cfg, reason: str, day: str, sport: str) -> tuple[bool, str]:
    claude = find_claude(cfg)
    now_mt = datetime.now(config.display_tz(cfg)).strftime("%Y-%m-%d %H:%M MT")
    prompt = PROMPT_FILE.read_text().replace("{{REASON}}", reason).replace("{{DAY}}", day).replace("{{NOW}}", now_mt)
    guide = config.ROOT / "ops" / f"agent_prompt_{sport.lower()}.md"     # one guide per sport (decision 0016)
    prompt = prompt.replace("{{SPORT_GUIDE}}", guide.read_text() if guide.exists() else "")
    prompt = prompt.replace("{{SPORT}}", sport).replace("{{sport}}", sport.lower())
    env = dict(os.environ)
    env["UV_PROJECT_ENVIRONMENT"] = str(config.ROOT / ".venv.nosync")
    env["PATH"] = f"{Path(claude).parent}:/opt/homebrew/bin:/usr/bin:/bin:" + env.get("PATH", "")
    cmd = [claude, "-p", prompt, "--permission-mode", "default", "--allowedTools",
           "Read", "Write(docs/cards/decisions/**)", "Edit(docs/cards/decisions/**)", "Write(docs/leans/decisions/**)", "Edit(docs/leans/decisions/**)", "Edit(adjustments.yaml)", "Glob", "Grep", "WebSearch", "WebFetch", "Bash(uv run engine:*)"]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        res = subprocess.run(cmd, cwd=str(config.ROOT), env=env, capture_output=True, text=True,
                             timeout=(cfg.get("agent") or {}).get("timeout_minutes", 25) * 60)
    except subprocess.TimeoutExpired:
        return False, "the research run timed out"
    (LOG_DIR / f"agent_{sport.lower()}_{datetime.now():%Y-%m-%d_%H%M}.log").write_text(
        f"reason: {reason}\nexit: {res.returncode}\n--- output\n{res.stdout}\n--- errors\n{res.stderr}\n")
    if res.returncode != 0:
        return False, f"the research run exited with code {res.returncode}: {(res.stderr or res.stdout).strip()[-300:]}"
    return True, (res.stdout or "").strip()[-600:]


def _when(kick, tz) -> str:
    local = kick.astimezone(tz)
    today = datetime.now(tz).date()
    day = "today" if local.date() == today else "tomorrow" if (local.date() - today).days == 1 else f"{local:%a %b %-d}"
    return f"{day} {local:%-I:%M %p}"


def _limit(r: dict) -> str:
    """The number part of the don't-bet-past limit: 'Thunder +2.5' -> '+2.5'."""
    lim = r.get("dont_bet_past") or r["pick"]
    return lim.rsplit(" ", 1)[-1]


def _why(d: dict) -> str:
    text = (d.get("summary") or (d.get("reasons") or {}).get("situation") or "").strip()
    return " ".join(str(text).split())


def message(r: dict, kind: str, tz, sport: str, next_check: str = "", stage: int | None = None) -> str:
    """One pick message. The first line is always the instruction.
    `stage` is this sport's betting-readiness stage (readiness.py). Below Stage 1 nothing is staked, and Conditionals are never staked at any
    stage, so the message must not tell Kylor to put money on them (fixed 2026-11-23: it said "Bet $12.5 ONLY IF" on a paper Conditional)."""
    d = r["decision"]
    bet = f"{r['pick']} ({int(r['price']):+d})"
    game = f"{r['game']}, {_when(r['kick'], tz)}"
    paper = stage is not None and stage < 1
    if kind in ("bet", "now_bet"):
        if paper:
            head = "OLD PATH, $0 RECORD (not a bet; decision 0027)" + (" (the condition was met)" if kind == "now_bet" else "")
            stake = "Stake: $0. The research agent's news decisions are graded as a record; picks come from the playbook."
        else:
            head = "BET NOW" if kind == "bet" else "BET NOW (the condition was met)"
            stake = f"Stake: ${r['dollars']:g}"
        return (f"{sport} · {head}\n{bet}\n{game}\n{stake}\n"
                f"Check your book first. Skip it if the number is worse than {_limit(r)}.\nWhy: {_why(d)}")
    if kind in ("wait", "now_wait"):
        head = "WAIT, DO NOT BET YET" if kind == "wait" else "HOLD OFF: this is no longer a bet until the condition below is met"
        cond = " ".join(str(d["condition"]).split())
        follow = f"\nI will message again{next_check} with BET NOW or CANCELLED."
        if stage is not None:
            what = (f"Paper only (Conditionals are never staked under the readiness rules). It turns into a {'paper ' if paper else ''}Bet ONLY IF: {cond}")
        else:
            what = f"Bet ${r['dollars']:g} ONLY IF: {cond}"
        return (f"{sport} · {head}\n{bet}\n{game}\n{what}\n"
                f"Even then, skip it if your book is worse than {_limit(r)}.{follow}\nWhy: {_why(d)}")
    why = r.get("downgraded") or " ".join(str(d.get("why_pass", "")).split())
    return f"{sport} · CANCELLED, DO NOT BET\n{r['pick']}\n{r['game']}\n{why}"


def changes(prev: dict[str, dict], rows: list[dict], tz=None, sport: str = "", next_check: str = "", stage: int | None = None) -> list[str]:
    """Messages for what changed since the last card. prev: pick_key -> {status, pick}."""
    from zoneinfo import ZoneInfo
    tz = tz or ZoneInfo("America/Denver")
    out = []
    for r in rows:
        key = f"{r['event_id']}|{r['market']}|{r['side']}"
        old = prev.get(key, {}).get("status")
        new = r["status"]
        live_old, live_new = old in ("Bet", "Conditional"), new in ("Bet", "Conditional")
        if live_new and not live_old:
            out.append(message(r, "bet" if new == "Bet" else "wait", tz, sport, next_check, stage))
        elif live_old and live_new and old != new:
            out.append(message(r, "now_bet" if new == "Bet" else "now_wait", tz, sport, next_check, stage))
        elif live_old and not live_new:
            out.append(message(r, "cancel", tz, sport))
    return out


def next_check_text(cfg, now_local) -> str:
    """' at the 3:15 PM check' for the next scheduled research run today, if there is one."""
    sched = (cfg.get("agent") or {}).get("schedule") or {}
    for hhmm in sched.get("sunday" if now_local.weekday() == 6 else "other", []):
        h, m = (int(x) for x in str(hhmm).split(":"))
        slot = now_local.replace(hour=h, minute=m, second=0, microsecond=0)
        if slot > now_local:
            return f" after the {slot:%-I:%M %p} check"
    return " after the next check"


def finalize(cfg, env, day: str, sport: str = "NFL", send: bool = True, reason: str = "") -> tuple[list[str], Path]:
    """Fresh prices, render the card, alert on changes, log picks."""
    sheet = slate.build(sport)
    slate.save(sheet)
    dpath = decisions_path(day, sport)
    if not dpath.exists():
        raise SourceError(f"the research run left no decisions file at {dpath.relative_to(config.ROOT)}")
    decisions, note = card.load_decisions(dpath)
    text, rows = card.build(sheet, decisions, note, cfg, strict=False)
    out = card_path(day, sport)
    out.write_text(text)
    now = datetime.now(timezone.utc)
    ts = now.replace(tzinfo=None)
    con = snap.connect(config.DB)
    try:
        con.execute(SCHEMA)
        prev = {r[0]: {"status": r[1], "pick": r[2]} for r in con.execute(
            "SELECT pick_key, status, pick FROM engine_picks WHERE kickoff_utc > ?", [ts]).fetchall()}
        tz = config.display_tz(cfg)
        stage = 0   # decision 0027: the old path is a $0 record; the readiness stages no longer gate anything
        alerts = changes(prev, rows, tz, lanes.tag(cfg, sport), next_check_text(cfg, datetime.now(tz)), stage)
        props_line = lanes.props_footer(cfg, con, sport)
        try:        # paper Leans: stamped by code, never staked, never a Telegram ping (kind "info")
            from engine.picks import leans
            lean_lines = leans.ingest(cfg, con, sheet, day, sport)
            alerts_lean = [l for l in lean_lines if l.startswith("LEAN")]
            for l in lean_lines:
                if l.startswith("REFUSED"):
                    props_line = (props_line + "\n" if props_line else "") + "Lean " + l
            sec = leans.card_section(con, sport, tz)
            if sec:
                out.write_text(text + sec)
        except Exception as e:
            lean_lines, alerts_lean = [f"Leans could not be processed: {type(e).__name__}: {e}"], []
            props_line = (props_line + "\n" if props_line else "") + lean_lines[0]
        from engine import version
        rv = version.stamp(cfg, con)
        try:
            log_wind(con, sheet, ts)
        except Exception:        # a log must never block a pick
            pass
        pin = {g["event_id"]: g["markets"][0].get("pinnacle_line") for g in sheet["games"]}
        for r in rows:
            key = f"{r['event_id']}|{r['market']}|{r['side']}"
            kick = r["kick"].astimezone(timezone.utc).replace(tzinfo=None)
            if key in prev or r["status"] != "Pass":
                first = con.execute("SELECT first_issued_utc FROM engine_picks WHERE pick_key=?", [key]).fetchone()
                con.execute("DELETE FROM engine_picks WHERE pick_key=?", [key])
                con.execute("INSERT INTO engine_picks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            [key, r["game"], r["pick"], r["status"], r["book_line"], r["price"], r["fair"], r["value"],
                             r["dont_bet_past"], first[0] if first else ts, ts, kick, rv])
                if prev.get(key, {}).get("status") != r["status"]:
                    con.execute("INSERT INTO engine_pick_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                [ts, key, r["game"], r["pick"], r["status"], r["book_line"], r["price"], r["fair"],
                                 r["value"], pin.get(r["event_id"]) if r["market"] == "spread" else None, rv])
            elif r["status"] == "Pass":
                # log every flagged Pass too, once per change, so the engine's hit rate is not measured on bets alone
                last = con.execute("SELECT status FROM engine_pick_events WHERE pick_key=? ORDER BY ts_utc DESC LIMIT 1", [key]).fetchone()
                if last is None or last[0] != "Pass":
                    con.execute("INSERT INTO engine_pick_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                [ts, key, r["game"], r["pick"], "Pass", r["book_line"], r["price"], r["fair"],
                                 r["value"], pin.get(r["event_id"]) if r["market"] == "spread" else None, rv])
            # arm the watchlist at the number that would make a pass a bet
            if r["status"] == "Pass" and not r["numbers_say_bet"] and r.get("limit_line") is not None and r["market"] == "spread":
                team = r["pick"].rsplit(" ", 1)[0]
                target = r["limit_line"] if r["side"] == "home" else -r["limit_line"]
                if not con.execute("SELECT 1 FROM watchlist WHERE active AND team=? AND market='spread' AND target=?", [team, target]).fetchone():
                    nid = con.execute("SELECT coalesce(max(id), 0) + 1 FROM watchlist").fetchone()[0]
                    con.execute("INSERT INTO watchlist VALUES (?,?,?,?,?,?,?,?)", [nid, ts, team, "spread", target, -115.0, f"engine {day}", True])
    finally:
        con.close()
    try:
        from engine.picks import board
        board.build()
    except Exception as e:      # the page is a convenience; a pick alert must not be lost over it
        alerts.append(f"Board page could not be rebuilt: {type(e).__name__}: {e}")
    sent = []
    for l in alerts_lean:
        if send:
            telegram.send(env, f"{lanes.tag(cfg, sport)} · PAPER LEAN, DO NOT BET\n" + l.removeprefix("LEAN (paper) "), kind="info")
    for a in alerts:
        msg = a
        if send:     # decision 0027: one pick path. The old path's Bet/Conditional/cancel messages are a $0 record, held back from Telegram
            telegram.send(env, msg, lanes.thread_key(cfg, sport),     # unless `agent.send_picks: true` is set again
                          kind="bet" if (cfg.get("agent") or {}).get("send_picks", False) else "info")
        sent.append(msg)
    # a short "nothing to do" note only when this run produced no pick message
    if not alerts and (cfg.get("agent") or {}).get("summary_message", True):
        waiting = [r for r in rows if r["status"] == "Conditional"]
        bets = [r for r in rows if r["status"] == "Bet"]
        passed = [r for r in rows if r["status"] == "Pass"]
        if bets or waiting:
            lines = [f"{lanes.tag(cfg, sport)} · NOTHING NEW. Checked again ({len(sheet['games'])} games)."]
            lines += [f"Still a bet: {r['pick']} ({int(r['price']):+d}), skip if worse than {_limit(r)}." for r in bets]
            lines += [f"Still waiting: {r['pick']}. Only if: {' '.join(str(r['decision']['condition']).split())}" for r in waiting]
        else:
            lines = [f"{lanes.tag(cfg, sport)} · NO BETS. Checked {len(sheet['games'])} games; nothing is worth a bet right now."]
            if passed:
                lines.append("Came close but had no real reason behind them: " + ", ".join(r["pick"] for r in passed[:6]) + ".")
        if props_line:
            lines.append(props_line)
        msg = "\n".join(lines)
        if send:
            telegram.send(env, msg, lanes.thread_key(cfg, sport), kind="info")     # held back by default: "no bets" is not a ping
        sent.append(msg)
    return sent, out


def run(reason: str, send: bool = True, skip_research: bool = False, sport: str = "NFL") -> tuple[int, list[str]]:
    cfg, env = config.load_config(), config.load_env()
    day = today_mt(cfg)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    lines: list[str] = []
    con = snap.connect(config.DB)
    con.execute(SCHEMA)
    # mark the start so the scheduler and the cooldown see a run in progress
    con.execute("INSERT INTO agent_runs VALUES (?,?,?,?)", [now, f"{sport}: {reason}", None, "started"])
    con.close()

    def record(ok: bool, note: str):
        c = snap.connect(config.DB)
        try:
            c.execute("INSERT INTO agent_runs VALUES (?,?,?,?)", [now, f"{sport}: {reason}", ok, note[:500]])
        finally:
            c.close()

    try:
        sheet = slate.build(sport)
        slate.save(sheet)
        flagged = sum(1 for g in sheet["games"] for m in g["markets"] for s in m.get("sides", []) if s["numbers_say_bet"])
        if not sheet["games"]:
            record(True, "no games posted")
            return 0, [f"{sport}: your book has no games posted; nothing to do."]
        if not skip_research:
            ok, note = run_claude(cfg, reason, day, sport)
            if not ok:
                raise SourceError(note)
            lines.append(note)
        sent, path = finalize(cfg, env, day, sport, send, reason)
        lines.append(f"{sport} card: {path.relative_to(config.ROOT)}. {flagged} side(s) flagged by the numbers. {len(sent)} message(s).")
        lines += sent
        record(True, f"{len(sent)} messages")
        from engine import gitsync
        lines.append(gitsync.commit_generated(sport))
        return 0, lines
    except Exception as e:
        msg = str(e) if isinstance(e, SourceError) else f"{type(e).__name__}: {e}"
        record(False, msg)
        if send:
            try:
                telegram.send(env, f"{sport} research run FAILED ({reason}): {msg[:600]}", kind="system")
            except SourceError:
                pass
        return 1, lines + [f"{sport} research run FAILED: {msg}"]


def cooled_down(con, now: datetime, minutes: int, sport: str | None = None) -> bool:
    """No research run in the last `minutes` (any sport, or only `sport`'s runs when given)."""
    con.execute(SCHEMA)
    if sport:
        last = con.execute("SELECT max(ts_utc) FROM agent_runs WHERE reason LIKE ?", [f"{sport}: %"]).fetchone()[0]
    else:
        last = con.execute("SELECT max(ts_utc) FROM agent_runs").fetchone()[0]
    return last is None or (now.replace(tzinfo=None) - last) > timedelta(minutes=minutes)


def spawn(reason: str, sport: str = "NFL") -> None:
    """Start a research run in the background (used by the hourly read when news lands)."""
    env = dict(os.environ)
    env["UV_PROJECT_ENVIRONMENT"] = str(config.ROOT / ".venv.nosync")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = open(LOG_DIR / "agent.log", "a")
    subprocess.Popen(["/opt/homebrew/bin/uv", "run", "--project", str(config.ROOT), "engine", "agent", "--sport", sport, "--reason", reason],
                     cwd=str(Path.home()), env=env, stdout=log, stderr=log, start_new_session=True)
