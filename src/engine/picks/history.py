"""Per-sport history: ratings from the market's own closing lines, and how games land."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from engine import config
from engine.odds import espn
from engine.odds.espn import SourceError
from engine.picks import ratings, sources
from engine.picks.pricing import Landing, bell_rows

NFLVERSE_TO_ESPN = {"LA": "LAR", "WAS": "WSH"}


@dataclass
class History:
    spread_rating: dict[str, float]     # team key -> points better than average
    total_tendency: dict[str, float]
    avg_total: float | None
    games_used: int
    land_spread: Landing
    land_total: Landing
    key: callable                       # ESPN team dict -> team key used in the ratings
    note: str = ""


def nfl(now: datetime, hfa: float) -> History:
    rows = sources.nfl_games(config.DATA / "raw" / "nflverse_games.csv")
    played = [r for r in rows if r["result"] not in ("", None) and r["spread_line"] not in ("", None)]
    season = max(int(r["season"]) for r in played)
    cur = [r for r in played if int(r["season"]) == season and r["game_type"] == "REG" and r["total_line"] not in ("", None)]
    last = max(int(r["week"]) for r in cur)
    games = [{"home": NFLVERSE_TO_ESPN.get(r["home_team"], r["home_team"]), "away": NFLVERSE_TO_ESPN.get(r["away_team"], r["away_team"]),
              "home_margin": float(r["spread_line"]), "total": float(r["total_line"]), "weeks_ago": last - int(r["week"]),
              "neutral": r.get("location") == "Neutral"} for r in cur]
    sr, tt, avg, n = ratings.fit(games, hfa)
    hist = [r for r in played if int(r["season"]) >= 2015]
    return History(sr, tt, avg, n,
                   Landing([(-float(r["spread_line"]), float(r["result"])) for r in hist], "spread", window=1.0),
                   Landing([(float(r["total_line"]), float(r["total"])) for r in hist if r["total_line"] not in ("", None)], "total", window=3.0),
                   key=lambda team: team["abbreviation"])


def college(now: datetime, hfa: float, env: dict) -> History:
    cache = config.DATA / "raw" / "cfbd"
    key = env.get("CFBD_API_KEY", "")
    year = now.year if now.month >= 8 else now.year - 1
    seasons = {y: sources.cfbd_lines(y, key, cache, current=(y == year)) for y in range(year - 5, year + 1)}
    cur, landing_spread, landing_total = [], [], []
    for y, games in seasons.items():
        for g in games:
            line = sources.cfbd_line(g)
            if line is None or g.get("homeScore") is None or g.get("awayScore") is None:
                continue
            margin = g["homeScore"] - g["awayScore"]
            landing_spread.append((float(line["spread"]), float(margin)))
            if line.get("overUnder") is not None:
                landing_total.append((float(line["overUnder"]), float(g["homeScore"] + g["awayScore"])))
            if y == year and g.get("seasonType") == "regular":
                cur.append((g, line))
    if not cur:
        raise SourceError("CollegeFootballData has no played games with lines this season")
    last = max(g["week"] for g, _ in cur)
    games = [{"home": str(g["homeTeamId"]), "away": str(g["awayTeamId"]), "home_margin": -float(l["spread"]),
              "total": l.get("overUnder"), "weeks_ago": last - g["week"], "neutral": False} for g, l in cur]
    sr, tt, avg, n = ratings.fit(games, hfa, min_games=200)
    return History(sr, tt, avg, n, Landing(landing_spread, "spread", window=1.5, min_n=600),
                   Landing(landing_total, "total", window=3.0, min_n=600), key=lambda team: str(team["id"]),
                   note="College ratings come from this season's closing lines; teams with few lined games sit near average.")


def nba(now: datetime, hfa: float, sd: dict, days: int = 35) -> History:
    cache = config.DATA / "raw" / "espn"
    games = []
    today = now.date()
    for back in range(1, days + 1):
        day = today - timedelta(days=back)
        for e in espn.scoreboard("NBA", day, cache):
            if not e.completed:
                continue
            odds = espn.event_odds(e, cache)
            c = odds.close if odds else None
            if c is None or c.home_spread is None:
                continue
            games.append({"home": str(e.home["id"]), "away": str(e.away["id"]), "home_margin": -c.home_spread,
                          "total": c.total, "weeks_ago": back // 7, "neutral": e.neutral})
    sr, tt, avg, n = ratings.fit(games, hfa, decay=0.85, min_games=60)
    return History(sr, tt, avg, n,
                   Landing(bell_rows("spread", sd["spread"], -25, 25), "spread", window=0.25, min_n=100),
                   Landing(bell_rows("total", sd["total"], 180, 270), "total", window=0.25, min_n=100),
                   key=lambda team: str(team["id"]),
                   note=f"NBA ratings come from the last {days} days of closing lines; basketball has no key numbers, so a bell curve prices the half points.")


def load(sport: str, now: datetime, cfg: dict, env: dict) -> History:
    hfa = cfg["picks"]["home_field"][sport]
    if sport == "NFL":
        return nfl(now, hfa)
    if sport == "College":
        return college(now, hfa, env)
    if sport == "NBA":
        return nba(now, hfa, cfg["margin_sd"]["NBA"])
    raise ValueError(sport)
