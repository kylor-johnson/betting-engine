"""When may real money go on an engine pick? Generated from the database, never typed (docs/decisions/0012).

Stage 0  observe: no money. Everything is tracked and graded.
Stage 1  half unit ($12.50) on engine *Bets* only (not Conditionals, Leans, props or wind totals).
Stage 2  the full unit ($25), as the spec already says, after 100 graded picks.
Pause    back to stage 0 if the evidence turns, or a rule is broken.

The criteria live in config.yaml (`go_live:`) so changing them is an event. This module only reads them and the record.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from engine import config

DEFAULTS = {"weeks_min": 3, "graded_min": 10, "clv_n_min": 5, "clv_floor": 0.0, "full_graded": 100, "full_clv_floor": 0.0,
            "pause_n": 25, "pause_clv": -0.5, "stop_loss_units": 10, "weekly_stake_cap_units": 2.0, "stage1_unit_fraction": 0.5}


def settings(cfg: dict) -> dict:
    return {**DEFAULTS, **(cfg.get("go_live") or {})}


def metrics(con, now: datetime | None = None) -> dict:
    """The facts the rules look at, from the database."""
    now = (now or datetime.now(timezone.utc)).replace(tzinfo=None)
    m = {"freeze_utc": None, "weeks": 0.0, "graded": 0, "bets": 0, "clv_n": 0, "avg_clv": None, "versions": 0,
         "missing_limit": 0, "ungraded_finished": 0, "profit_units": 0.0}
    try:
        rows = con.execute("SELECT settings_hash, first_seen_utc FROM rule_versions ORDER BY first_seen_utc").fetchall()
        if rows:
            # the clock restarts when the SETTINGS that decide picks change; a code-only commit is a new rule version but does not restart it
            start = rows[-1][1]
            for h, t in reversed(rows):
                if h != rows[-1][0]:
                    break
                start = t
            m["freeze_utc"], m["versions"] = start, len(rows)
            m["weeks"] = (now - start).total_seconds() / (7 * 86400)
    except Exception:
        pass
    if m["freeze_utc"] is None:
        return m
    try:
        g = con.execute("""SELECT count(*), count(*) FILTER (status='Bet'), count(clv_points), avg(clv_points), coalesce(sum(profit_units), 0)
                           FROM engine_pick_grades WHERE status IN ('Bet','Conditional') AND issued_utc >= ?""", [m["freeze_utc"]]).fetchone()
        m.update(graded=g[0], bets=g[1], clv_n=g[2], avg_clv=g[3], profit_units=round(g[4], 2))
        m["missing_limit"] = con.execute("SELECT count(*) FROM engine_picks WHERE status IN ('Bet','Conditional') AND dont_bet_past IS NULL").fetchone()[0]
        m["ungraded_finished"] = con.execute("""SELECT count(*) FROM engine_picks p WHERE p.status IN ('Bet','Conditional')
            AND p.kickoff_utc < ? - INTERVAL 1 DAY AND p.pick_key NOT IN (SELECT pick_key FROM engine_pick_grades)""", [now]).fetchone()[0]
    except Exception:
        pass
    return m


def stage(m: dict, rules: dict) -> tuple[int, list[tuple[str, str, str, bool]]]:
    """(stage number, [(criterion, have, need, met)]). Stage -1 means paused."""
    clv = m["avg_clv"]
    s1 = [
        ("Weeks since the rules were frozen", f"{m['weeks']:.1f}", f"{rules['weeks_min']}", m["weeks"] >= rules["weeks_min"]),
        ("Graded Bets and Conditionals", f"{m['graded']}", f"{rules['graded_min']}", m["graded"] >= rules["graded_min"]),
        ("Of those with a closing line", f"{m['clv_n']}", f"{rules['clv_n_min']}", m["clv_n"] >= rules["clv_n_min"]),
        ("Average closing-line value (points)", "n/a" if clv is None else f"{clv:+.2f}", f">= {rules['clv_floor']:+.1f}", clv is not None and clv >= rules["clv_floor"]),
        ("Every pick has a don't-bet-past number", f"{m['missing_limit']} missing", "0 missing", m["missing_limit"] == 0),
        ("Finished picks all graded", f"{m['ungraded_finished']} ungraded", "0 ungraded", m["ungraded_finished"] == 0),
    ]
    full = [("Graded picks for the full unit", f"{m['graded']}", f"{rules['full_graded']}", m["graded"] >= rules["full_graded"]),
            ("Average closing-line value above", "n/a" if clv is None else f"{clv:+.2f}", f"> {rules['full_clv_floor']:+.1f}", clv is not None and clv > rules["full_clv_floor"])]
    if clv is not None and m["clv_n"] >= rules["pause_n"] and clv < rules["pause_clv"]:
        return -1, s1 + full
    if all(c[3] for c in s1) and all(c[3] for c in full):
        return 2, s1 + full
    if all(c[3] for c in s1):
        return 1, s1 + full
    return 0, s1 + full


NAMES = {-1: "PAUSED (back to no money; review before anything else)", 0: "Stage 0: observe, no money", 1: "Stage 1: half unit on engine Bets only", 2: "Stage 2: full unit"}


def report(cfg: dict, con, now: datetime | None = None) -> str:
    rules = settings(cfg)
    m = metrics(con, now)
    st, rows = stage(m, rules)
    unit = cfg.get("unit", 25)
    out = ["# Betting readiness (generated; do not edit)", "",
           f"**{NAMES[st]}.**", ""]
    if m["freeze_utc"]:
        out.append(f"Settings last changed {m['freeze_utc']:%b %-d, %Y} UTC; {m['versions']} rule version(s) recorded in all. Engine picks since then: {m['graded']} graded, "
                   f"{m['profit_units']:+.2f} units (a result is not evidence; the closing-line value is).")
    else:
        out.append("No rule version recorded yet.")
    out += ["", "| Criterion | Have | Need | Met |", "|---|---|---|---|"]
    out += [f"| {c} | {h} | {n} | {'yes' if ok else 'no'} |" for c, h, n, ok in rows]
    half = unit * rules["stage1_unit_fraction"]
    out += ["", "## What each stage allows", "",
            f"- **Stage 0:** no money. Everything is logged and graded.",
            f"- **Stage 1:** ${half:g} on a Bet (status Bet only), at the Wagerhouse number or better than its \"don't bet past\", re-checked just before you place it. "
            f"At most {rules['weekly_stake_cap_units']:g} units staked per week across all picks. Log it with `engine bet add`.",
            f"- **Stage 2:** the full ${unit:g} unit; the sizing review the spec already requires after 100 graded.",
            "- **Never bet at any stage:** Conditionals, wind totals, paper Leans (until 50 are graded with average closing-line value above zero), props (until a model passes its gate), "
            "anything past the \"don't bet past\" number, anything in the first few minutes after a change of rule version.",
            "", "## Pause rules (back to Stage 0)", "",
            f"- Average closing-line value below {rules['pause_clv']:+.1f} points once {rules['pause_n']} picks have a closing line.",
            f"- Down {rules['stop_loss_units']:g} units from the start of Stage 1 (bankroll protection, not evidence).",
            "- Any pick bet past its limit, or a pick with no limit.",
            "- A change to the settings that decide picks (`picks`, `models`, `leans`, `margin_sd`, `sports` in `config.yaml`): the clock and the graded count start again from that change. "
            "A code-only change is recorded as a new rule version but does not restart the clock; Kylor decides whether it should.", ""]
    return "\n".join(out)


def write(cfg: dict, con) -> Path:
    path = config.ROOT / "docs" / "lanes" / "READINESS.md"
    path.write_text(report(cfg, con))
    return path
