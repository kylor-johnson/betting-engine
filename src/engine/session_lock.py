"""One session owns the code at a time (CHARTER, "How sessions work together"; decision 0027).

`data.nosync/SESSION.lock` names who holds it, when it was taken and why. A session takes it (`engine lock take "why"`) before editing
src/, ops/, config.yaml, adjustments.yaml, CHARTER.md or PLAYBOOK.md, and releases it (`engine lock release`) after it commits. A lock older
than `STALE_HOURS` is stale and may be taken over. Scheduled jobs do not auto-commit while a fresh lock is held, so a run never commits
half of a session's change. The research agent's own files (decisions, checks, adjustments) are still written; they wait for the next commit.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine import config

STALE_HOURS = 4


def path():
    return config.DATA / "SESSION.lock"


def read() -> dict | None:
    """{'session', 'started' (UTC datetime or None), 'raw'} or None when no lock file exists."""
    p = path()
    if not p.exists():
        return None
    raw = p.read_text()
    out = {"session": "", "started": None, "raw": raw.strip()}
    for line in raw.splitlines():
        k, _, v = line.partition(":")
        if k.strip() == "session":
            out["session"] = v.strip()
        elif k.strip() == "started":
            try:
                out["started"] = datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
            except ValueError:
                pass
    return out


def held(now: datetime | None = None) -> dict | None:
    """The lock if a fresh one is held, else None (no file, or older than STALE_HOURS, or unreadable time counts as fresh)."""
    lk = read()
    if lk is None:
        return None
    now = now or datetime.now(timezone.utc)
    if lk["started"] is not None and now - lk["started"] > timedelta(hours=STALE_HOURS):
        return None
    return lk


def take(why: str, now: datetime | None = None, force: bool = False) -> str:
    now = now or datetime.now(timezone.utc)
    cur = held(now)
    if cur and not force:
        return f"REFUSED: another session holds the lock ({cur['session']}, since {cur['started']}). Stop and ask Kylor."
    path().parent.mkdir(parents=True, exist_ok=True)
    path().write_text(f"session: {why}\nstarted: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
    return f"Lock taken: {why}"


def release() -> str:
    if path().exists():
        path().unlink()
        return "Lock released."
    return "No lock was held."
