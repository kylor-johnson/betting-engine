"""NFL injury feed: store every player's status and report what changed since the last look."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from engine.odds.espn import SourceError

URLS = {"NFL": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries",
        "NBA": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"}
URL = URLS["NFL"]
SCHEMA = """
CREATE TABLE IF NOT EXISTS injury_status (
  player_id VARCHAR PRIMARY KEY, team VARCHAR, name VARCHAR, pos VARCHAR, status VARCHAR,
  updated VARCHAR, comment VARCHAR, seen_utc TIMESTAMP);
CREATE TABLE IF NOT EXISTS injury_changes (
  ts_utc TIMESTAMP, player_id VARCHAR, team VARCHAR, name VARCHAR, pos VARCHAR,
  old_status VARCHAR, new_status VARCHAR, comment VARCHAR);
"""
# statuses that matter for a line, worst first
SERIOUS = ("Out", "Injured Reserve", "Doubtful", "Questionable", "Suspension")


@dataclass
class Player:
    player_id: str
    team: str
    name: str
    pos: str
    status: str
    updated: str
    comment: str


def fetch(sport: str = "NFL") -> list[Player]:
    if sport not in URLS:
        raise SourceError(f"there is no machine-readable injury feed for {sport}; search for the team's report instead")
    try:
        with urllib.request.urlopen(urllib.request.Request(URLS[sport], headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
            data = json.load(r)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise SourceError(f"ESPN NFL injury feed failed: {type(e).__name__}") from None
    if "injuries" not in data:
        raise SourceError("ESPN NFL injury feed has no 'injuries' field")
    out = []
    for t in data["injuries"]:
        for i in t.get("injuries", []):
            a = i.get("athlete") or {}
            pid = str(a.get("id") or f"{t.get('displayName')}|{a.get('displayName')}")
            out.append(Player(pid, t.get("displayName", ""), a.get("displayName", ""),
                              (a.get("position") or {}).get("abbreviation", ""), i.get("status", ""),
                              (i.get("date") or "")[:16], (i.get("shortComment") or "").strip()))
    if not out:
        raise SourceError("ESPN NFL injury feed came back empty")
    return out


@dataclass
class Change:
    player: Player
    old_status: str | None      # None = not on the list before

    @property
    def matters(self) -> bool:
        """A quarterback whose availability got worse or better."""
        if self.player.pos != "QB":
            return False
        was = self.old_status in SERIOUS
        now = self.player.status in SERIOUS
        return (was != now) or (was and now and self.old_status != self.player.status)

    def text(self) -> str:
        p = self.player
        before = self.old_status or "not listed"
        return f"{p.team} {p.pos} {p.name}: {before} → {p.status}" + (f"\n{p.comment}" if p.comment else "")


def diff(previous: dict[str, str], players: list[Player]) -> list[Change]:
    """previous: player_id -> status. Returns every status change, in feed order."""
    return [Change(p, previous.get(p.player_id)) for p in players if previous.get(p.player_id) != p.status]


def check(con, now: datetime) -> tuple[list[Change], bool]:
    """Fetch, compare with what is stored, store. Returns (changes, first_run)."""
    con.execute(SCHEMA)
    prev = dict(con.execute("SELECT player_id, status FROM injury_status").fetchall())
    players = fetch()
    first = not prev
    changes = [] if first else diff(prev, players)
    ts = now.replace(tzinfo=None)
    con.execute("DELETE FROM injury_status")
    con.executemany("INSERT INTO injury_status VALUES (?,?,?,?,?,?,?,?)",
                    [(p.player_id, p.team, p.name, p.pos, p.status, p.updated, p.comment, ts)
                     for p in {q.player_id: q for q in players}.values()])
    if changes:
        con.executemany("INSERT INTO injury_changes VALUES (?,?,?,?,?,?,?,?)",
                        [(ts, c.player.player_id, c.player.team, c.player.name, c.player.pos, c.old_status,
                          c.player.status, c.player.comment) for c in changes])
    return changes, first
