"""Free inputs for the slate sheet: Pinnacle prices, public rating systems, NFL history."""
from __future__ import annotations

import csv
import io
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from engine.odds.espn import SourceError

UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/csv, */*"}
PINNACLE_LEAGUES = {"NFL": 889, "College": 880}
TRACKER = {"NFL": "https://www.thepredictiontracker.com/nflpredictions.csv",
           "College": "https://www.thepredictiontracker.com/ncaapredictions.csv"}
NFL_GAMES = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"


def _fetch(url: str, what: str) -> str:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
            return r.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError) as e:
        raise SourceError(f"{what} is unreachable ({type(e).__name__})") from None


@dataclass
class SharpLine:
    home: str
    away: str
    start: datetime
    home_spread: float | None = None
    home_spread_price: float | None = None
    away_spread_price: float | None = None
    total: float | None = None
    over_price: float | None = None
    under_price: float | None = None
    home_ml: float | None = None
    away_ml: float | None = None


def pinnacle(sport: str) -> list[SharpLine]:
    """Pinnacle's main full-game spread, total and moneyline for every listed game."""
    lid = PINNACLE_LEAGUES[sport]
    base = f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}"
    try:
        matchups = json.loads(_fetch(base + "/matchups", "Pinnacle"))
        markets = json.loads(_fetch(base + "/markets/straight", "Pinnacle"))
    except json.JSONDecodeError:
        raise SourceError("Pinnacle returned something that is not JSON") from None
    if not isinstance(matchups, list) or not isinstance(markets, list):
        raise SourceError("Pinnacle returned an unexpected shape")
    out: dict[int, SharpLine] = {}
    for m in matchups:
        if m.get("type") != "matchup" or m.get("parent") or m.get("isLive"):
            continue
        parts = {p.get("alignment"): p.get("name") for p in m.get("participants", [])}
        if "home" not in parts or "away" not in parts:
            continue
        out[m["id"]] = SharpLine(parts["home"], parts["away"],
                                 datetime.strptime(m["startTime"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc))
    for k in markets:
        s = out.get(k.get("matchupId"))
        if s is None or k.get("period") != 0 or k.get("isAlternate") or k.get("status") != "open":
            continue
        pr = {p.get("designation"): p for p in k.get("prices", [])}
        if k["type"] == "spread" and "home" in pr and "away" in pr:
            s.home_spread, s.home_spread_price, s.away_spread_price = pr["home"]["points"], pr["home"]["price"], pr["away"]["price"]
        elif k["type"] == "total" and "over" in pr and "under" in pr:
            s.total, s.over_price, s.under_price = pr["over"]["points"], pr["over"]["price"], pr["under"]["price"]
        elif k["type"] == "moneyline" and "home" in pr and "away" in pr:
            s.home_ml, s.away_ml = pr["home"]["price"], pr["away"]["price"]
    return list(out.values())


def tracker(sport: str, save_dir: Path | None = None) -> list[dict]:
    """The Prediction Tracker's weekly file: ~50 public systems' predicted home margin per game.

    The site overwrites it each week, so a dated copy is kept."""
    text = _fetch(TRACKER[sport], "The Prediction Tracker")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or "lineavg" not in rows[0]:
        raise SourceError("The Prediction Tracker file has no 'lineavg' column")
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / f"{sport}_{datetime.now(timezone.utc):%Y-%m-%d}.csv").write_text(text)
    out = []
    for r in rows:
        try:
            systems = [float(v) for k, v in r.items()
                       if k.startswith("line") and k not in ("line", "lineopen", "lineavg", "linestd", "linemedian", "linemidweek") and v not in ("", None)]
            out.append({"home": r["home"].strip(), "road": r["road"].strip(), "avg_home_margin": float(r["lineavg"]),
                        "median_home_margin": float(r["linemedian"]), "spread_of_opinion": float(r["linestd"]),
                        "systems": len(systems), "neutral": r.get("neutral", "0").strip() == "1"})
        except (ValueError, KeyError):
            continue
    if not out:
        raise SourceError("The Prediction Tracker file had no usable rows")
    return out


def nfl_games(cache: Path | None = None, max_age_hours: float = 12) -> list[dict]:
    """Every NFL game since 1999 with its closing spread and total (nflverse)."""
    if cache and cache.exists() and (datetime.now().timestamp() - cache.stat().st_mtime) < max_age_hours * 3600:
        text = cache.read_text()
    else:
        text = _fetch(NFL_GAMES, "nflverse games file")
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(text)
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or "spread_line" not in rows[0]:
        raise SourceError("nflverse games file has no 'spread_line' column")
    return rows
