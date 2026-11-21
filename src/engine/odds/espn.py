"""ESPN public scoreboard and odds (DraftKings lines). Free, undocumented.

Fails loudly: a missing field raises, it is never silently skipped.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

LEAGUES = {
    "NFL": ("football", "nfl", ""),
    "College": ("football", "college-football", "&groups=80&limit=400"),
    "NBA": ("basketball", "nba", ""),
}
UA = {"User-Agent": "Mozilla/5.0"}


class SourceError(RuntimeError):
    """A data source is down or returned something unusable."""


def _get(url: str, tries: int = 3) -> dict:
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise SourceError(f"ESPN request failed after {tries} tries: {url} ({last})")


@dataclass
class Event:
    event_id: str
    league: str
    start: datetime          # UTC
    home: dict               # ESPN team dict
    away: dict
    completed: bool
    neutral: bool = False


def scoreboard(league: str, day: date, cache_dir: Path | None = None) -> list[Event]:
    sport, slug, extra = LEAGUES[league]
    ymd = day.strftime("%Y%m%d")
    cache = cache_dir / f"scoreboard_{league}_{ymd}.json" if cache_dir else None
    if cache and cache.exists():
        data = json.loads(cache.read_text())
    else:
        data = _get(f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{slug}/scoreboard?dates={ymd}{extra}")
        if "events" not in data:
            raise SourceError(f"ESPN scoreboard for {league} {ymd} has no 'events' field")
        if cache and day < datetime.now(timezone.utc).date():
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data))
    out = []
    for e in data["events"]:
        comp = e["competitions"][0]
        teams = {c["homeAway"]: c["team"] for c in comp["competitors"]}
        out.append(Event(
            event_id=e["id"],
            league=league,
            start=datetime.strptime(e["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc),
            home=teams["home"],
            away=teams["away"],
            completed=bool(e.get("status", {}).get("type", {}).get("completed")),
            neutral=bool(comp.get("neutralSite")),
        ))
    return out


def _num(s) -> float | None:
    """'+6.5' -> 6.5, 'EVEN' -> 100 (a price), 'PK' -> 0 (a line)."""
    if s is None:
        return None
    t = str(s).strip().upper()
    if t in ("EVEN", "EV"):
        return 100.0
    if t in ("PK", "PICK", "PICK'EM"):
        return 0.0
    try:
        return float(t)
    except ValueError:
        return None


@dataclass
class Lines:
    """One book's line at one moment (open or close), from the home side's view."""
    home_spread: float | None
    home_spread_price: float | None
    away_spread_price: float | None
    home_ml: float | None
    away_ml: float | None
    total: float | None
    over_price: float | None
    under_price: float | None


@dataclass
class EventOdds:
    provider: str
    open: Lines
    close: Lines
    current: Lines | None = None


def _lines(item: dict, when: str) -> Lines:
    h = (item.get("homeTeamOdds") or {}).get(when) or {}
    a = (item.get("awayTeamOdds") or {}).get(when) or {}
    t = item.get(when) or {}

    def g(d: dict, key: str) -> float | None:
        return _num((d.get(key) or {}).get("american"))

    return Lines(
        home_spread=g(h, "pointSpread"),
        home_spread_price=g(h, "spread"),
        away_spread_price=g(a, "spread"),
        home_ml=g(h, "moneyLine"),
        away_ml=g(a, "moneyLine"),
        total=g(t, "total"),
        over_price=g(t, "over"),
        under_price=g(t, "under"),
    )


def event_odds(ev: Event, cache_dir: Path | None = None) -> EventOdds | None:
    """Opening and closing lines for a game. None when ESPN lists no odds."""
    sport, slug, _ = LEAGUES[ev.league]
    cache = cache_dir / f"odds_{ev.league}_{ev.event_id}.json" if cache_dir else None
    if cache and cache.exists():
        data = json.loads(cache.read_text())
    else:
        data = _get(
            f"https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{slug}"
            f"/events/{ev.event_id}/competitions/{ev.event_id}/odds"
        )
        if "items" not in data:
            raise SourceError(f"ESPN odds for event {ev.event_id} has no 'items' field")
        if cache and ev.completed:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data))
    if not data["items"]:
        return None
    item = data["items"][0]
    return EventOdds(
        provider=(item.get("provider") or {}).get("name", "unknown"),
        open=_lines(item, "open"),
        close=_lines(item, "close"),
        current=_lines(item, "current"),
    )


def upcoming(league: str, start: date, end: date) -> list[Event]:
    """Games scheduled between two dates (inclusive), one request per day. Never cached."""
    out: dict[str, Event] = {}
    day = start
    while day <= end:
        for e in scoreboard(league, day, None):
            out[e.event_id] = e
        day += timedelta(days=1)
    return list(out.values())


# --- team name matching -----------------------------------------------------

ALIASES = {
    "mississippi": "ole miss",
    "miami florida": "miami",
    "miami fl": "miami",
    "miami ohio": "miami oh",
    "southern cal": "usc",
    "north carolina state": "nc state",
    "central florida": "ucf",
    "southern methodist": "smu",
    "brigham young": "byu",
    "louisiana state": "lsu",
    "texas christian": "tcu",
    "la clippers": "los angeles clippers",
    "pittsburgh": "pitt",
    "connecticut": "uconn",
    "massachusetts": "umass",
    "hawaii": "hawai'i",
    "san jose state": "san josé state",
    "louisiana lafayette": "louisiana",
    "ul monroe": "ul monroe",
    "appalachian state": "app state",
    "south florida": "south florida",
    "florida international": "fiu",
    "texas san antonio": "utsa",
    "texas el paso": "utep",
    "nevada las vegas": "unlv",
    "alabama birmingham": "uab",
}


def norm(name: str) -> str:
    s = name.lower().replace("&amp;", "&")
    s = re.sub(r"[.’]", "", s)
    s = re.sub(r"\bst\b", "state", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIASES.get(s, s)


def team_names(team: dict) -> set[str]:
    out = set()
    for k in ("location", "displayName", "shortDisplayName", "abbreviation", "name"):
        v = team.get(k)
        if v:
            out.add(norm(v))
    return out


def find_event(events: list[Event], team1: str, team2: str) -> tuple[Event | None, str]:
    """Match a game by both team names. Returns (event, how)."""
    a, b = norm(team1), norm(team2)
    both, one = [], []
    for e in events:
        names_h, names_a = team_names(e.home), team_names(e.away)
        hit_a = a in names_h or a in names_a
        hit_b = b in names_h or b in names_a
        if hit_a and hit_b:
            both.append(e)
        elif hit_a or hit_b:
            one.append(e)
    if len(both) == 1:
        return both[0], "both teams"
    if not both and len(one) == 1:
        return one[0], "one team"
    return None, "no match" if not (both or one) else "ambiguous"


def side_of(ev: Event, team: str) -> str | None:
    t = norm(team)
    if t in team_names(ev.home):
        return "home"
    if t in team_names(ev.away):
        return "away"
    return None
