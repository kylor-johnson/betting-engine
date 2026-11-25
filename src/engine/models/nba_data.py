"""NBA player game history from ESPN's public box scores, with each game's closing spread and total.

One compact JSON file per game in data.nosync/raw/espn_nba/games/, written once and never re-fetched.
`download` is paced (about four requests a second) and resumable; `load` reads everything on disk.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from engine import config
from engine.odds import espn
from engine.odds.espn import SourceError

DIR = config.DATA / "raw" / "espn_nba"
GAMES = DIR / "games"
SEASONS = {  # first day to scan, last day to scan
    2024: (date(2023, 10, 24), date(2024, 6, 20)),
    2025: (date(2024, 10, 22), date(2025, 6, 25)),
    2026: (date(2025, 10, 21), date(2026, 6, 25)),
    2027: (date(2026, 10, 20), date(2027, 6, 25)),
}
TEAMS = {"ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GS", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL",
         "MIN", "NO", "NY", "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SA", "TOR", "UTAH", "WSH"}
SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={id}"


def _get(url: str, tries: int = 3) -> dict:
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=45) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep(2 + 3 * i)
    raise SourceError(f"ESPN NBA box score unreachable ({type(last).__name__})")


def _num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def compact(summary: dict, ev: espn.Event, season: int, odds) -> dict | None:
    box = (summary.get("boxscore") or {}).get("players") or []
    if len(box) != 2:
        return None
    teams = [b["team"]["abbreviation"] for b in box]
    if any(t not in TEAMS for t in teams):
        return None            # all-star and exhibition games
    players = []
    for b in box:
        team = b["team"]["abbreviation"]
        for st in b.get("statistics", []):
            keys = st.get("keys") or []
            for a in st.get("athletes", []):
                ath = a.get("athlete") or {}
                if a.get("didNotPlay") or not a.get("stats"):
                    players.append({"id": str(ath.get("id")), "name": ath.get("displayName", ""), "team": team, "min": 0.0,
                                    "dnp": a.get("reason") or "DNP"})
                    continue
                v = dict(zip(keys, a["stats"]))
                three = str(v.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted", "0-0")).split("-")
                fg = str(v.get("fieldGoalsMade-fieldGoalsAttempted", "0-0")).split("-")
                ft = str(v.get("freeThrowsMade-freeThrowsAttempted", "0-0")).split("-")
                players.append({"id": str(ath.get("id")), "name": ath.get("displayName", ""), "team": team,
                                "starter": bool(a.get("starter")), "min": _num(v.get("minutes")), "pts": _num(v.get("points")),
                                "reb": _num(v.get("rebounds")), "ast": _num(v.get("assists")), "fg3m": _num(three[0]),
                                "fga": _num(fg[-1]), "fta": _num(ft[-1]), "tov": _num(v.get("turnovers"))})
    home = ev.home.get("abbreviation")
    away = ev.away.get("abbreviation")
    return {"event_id": ev.event_id, "season": season, "date": ev.start.astimezone(espn_tz()).date().isoformat(),
            "start_utc": ev.start.isoformat(), "home": home, "away": away,
            "home_spread": odds.close.home_spread if odds and odds.close else None,
            "total": odds.close.total if odds and odds.close else None, "players": players}


def espn_tz():
    from zoneinfo import ZoneInfo
    return ZoneInfo("America/New_York")


def _one(ev: espn.Event, season: int, pause: float) -> bool:
    path = GAMES / f"{ev.event_id}.json"
    summary = _get(SUMMARY.format(id=ev.event_id))
    time.sleep(pause)
    try:
        odds = espn.event_odds(ev, DIR / "odds")
    except SourceError:
        odds = None
    time.sleep(pause)
    c = compact(summary, ev, season, odds)
    path.write_text(json.dumps(c if c else {"skip": True, "event_id": ev.event_id}))
    return True


def download(seasons: list[int] | None = None, pause: float = 0.25, workers: int = 4, log=print) -> int:
    """Each worker waits `pause` seconds between requests (about 4 x 4 = 16 requests a second at most)."""
    from concurrent.futures import ThreadPoolExecutor
    GAMES.mkdir(parents=True, exist_ok=True)
    sb_cache = DIR / "scoreboards"
    today = date.today()
    todo: list[tuple] = []
    for season in seasons or sorted(SEASONS):
        start, end = SEASONS[season]
        day = start
        while day <= min(end, today):     # today too: same-night props grade on the evening reads (handoff 2026-11-24, gap 4); a
                                          # scoreboard is cached only once its day is past and every game final (espn.scoreboard)
            try:
                events = espn.scoreboard("NBA", day, sb_cache)
            except SourceError as e:
                log(f"{day}: scoreboard failed: {e}")
                events = []
            todo += [(ev, season) for ev in events if ev.completed and not (GAMES / f"{ev.event_id}.json").exists()]
            day += timedelta(days=1)
    log(f"{len(todo)} games to fetch")
    n = 0
    with ThreadPoolExecutor(workers) as pool:
        for ok in pool.map(lambda t: _safe(t[0], t[1], pause, log), todo):
            n += ok
    log(f"fetched {n} games")
    return n


def _safe(ev, season, pause, log) -> bool:
    try:
        return _one(ev, season, pause)
    except SourceError as e:
        log(f"{ev.event_id}: {e}")
        return False


def load() -> list[dict]:
    """Every stored game, oldest first."""
    out = []
    for p in GAMES.glob("*.json"):
        g = json.loads(p.read_text())
        if not g.get("skip"):
            out.append(g)
    return sorted(out, key=lambda g: (g["start_utc"], g["event_id"]))
