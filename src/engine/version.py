"""Freeze stamp: which code and which settings produced a pick.

Grading week must not be contaminated by tuning. Every pick and every Lean records the commit and a fingerprint of the settings
that decide picks. If either changes, `rule_versions` gets a new row, `engine status` and the board say so, and the record can be
split by version. A pick made on uncommitted code is stamped "+edited" so it is never mistaken for a clean version.
"""
from __future__ import annotations

import hashlib
import json
import subprocess

from engine import config

SETTINGS_KEYS = ("picks", "models", "leans", "margin_sd", "sports")
SCHEMA = """
CREATE TABLE IF NOT EXISTS rule_versions (settings_hash VARCHAR, commit_id VARCHAR, first_seen_utc TIMESTAMP, note VARCHAR);
"""


def settings_hash(cfg: dict) -> str:
    blob = json.dumps({k: cfg.get(k) for k in SETTINGS_KEYS}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:10]


def commit_id() -> str:
    """Short id of the last commit that touched the code, settings or agent prompt (a docs-only commit is not a new version), with '+edited' when src/, config.yaml or the agent prompt have uncommitted changes."""
    try:
        head = subprocess.run(["git", "log", "-1", "--format=%h", "--", "src", "config.yaml", "ops/agent_prompt.md"], cwd=config.ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "src", "config.yaml", "ops/agent_prompt.md"],
                               cwd=config.ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
        return (head or "unknown") + ("+edited" if dirty else "")
    except Exception:
        return "unknown"


def stamp(cfg: dict, con=None) -> str:
    """'commit/settings' for this moment; records a new rule version in `rule_versions` when it has not been seen."""
    s, c = settings_hash(cfg), commit_id()
    if con is not None:
        con.execute(SCHEMA)
        base = c.removesuffix("+edited")
        seen = con.execute("SELECT 1 FROM rule_versions WHERE settings_hash=? AND commit_id=?", [s, base]).fetchone()
        if not seen and not c.endswith("+edited"):
            from datetime import datetime, timezone
            con.execute("INSERT INTO rule_versions VALUES (?,?,?,?)", [s, base, datetime.now(timezone.utc).replace(tzinfo=None), ""])
    return f"{c}/{s}"


def versions_text(con) -> str:
    con.execute(SCHEMA)
    rows = con.execute("SELECT settings_hash, commit_id, first_seen_utc FROM rule_versions ORDER BY first_seen_utc").fetchall()
    if not rows:
        return "Rule versions: none recorded yet."
    return f"Rule versions seen: {len(rows)}. Latest: code {rows[-1][1]}, settings {rows[-1][0]}, first used {rows[-1][2]:%Y-%m-%d %H:%M} UTC."
