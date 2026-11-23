"""Commit what the scheduled jobs write (cards, decisions, adjustments, the generated status page).

The scheduler used to leave these uncommitted all day, so "uncommitted work" could mean a person's or a job's.
Now the job commits its own outputs, by path, so it never sweeps up a person's unfinished edits to src/.
A failure is reported, never fatal, and never retried in a loop.
"""
from __future__ import annotations

import subprocess
from datetime import datetime

from engine import config

PATHS = ["docs/cards", "adjustments.yaml", "docs/lanes/STATUS.md", "docs/leans"]


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=config.ROOT, capture_output=True, text=True, timeout=60)


def commit_generated(label: str = "") -> str:
    """Returns one line saying what happened."""
    if (config.ROOT / ".git" / "index.lock").exists():
        return "Auto-commit skipped: another git command is running (index.lock)."
    try:
        PATHS_NOW = [p for p in PATHS if (config.ROOT / p).exists()]
        dirty = _git("status", "--porcelain", "--", *PATHS_NOW).stdout.strip()
        if not dirty:
            return "Auto-commit: nothing new to commit."
        add = _git("add", "--", *PATHS_NOW)
        if add.returncode:
            return f"Auto-commit failed at add: {add.stderr.strip()[:200]}"
        stamp = datetime.now(config.display_tz(config.load_config())).strftime("%a %b %-d %-I:%M %p MT")
        msg = f"Scheduled run outputs, {stamp}{' (' + label + ')' if label else ''} [automatic commit by the engine]"
        done = _git("commit", "-m", msg, "--", *PATHS_NOW)
        if done.returncode:
            return f"Auto-commit failed: {(done.stderr or done.stdout).strip()[:200]}"
        return "Auto-commit: scheduled-run outputs committed."
    except Exception as e:
        return f"Auto-commit failed: {type(e).__name__}: {e}"
