"""College football wind totals: does wind at kickoff predict the total better than the closing line? (research 20)

Same model and walk-forward test as the NFL (`wind_totals.py`): expected total = closing total + b x max(0, wind - knot), fitted only on
earlier seasons. Wind is Open-Meteo's at the venue over the first three hours of the game.

The look-ahead trap research 18 found in the NFL script (it used the wind that actually blew, which nobody knows when betting) is handled
the same way as the NFL wind test: the model is FITTED on reanalysis (what blew), but the seasons that decide whether it is used (2024 on)
are TESTED on the forecast issued the day before (Open-Meteo previous-runs, kept from early 2024). Only that test counts.

Data: CollegeFootballData games (venue, kickoff, neutral site) and venues (coordinates, dome), the cached closing lines
(`data.nosync/raw/cfbd/cfbd_lines_<year>.json`). FBS games with a closing total, a known kickoff time and an open-air venue.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

from engine import config
from engine.models import weather
from engine.models.wind_totals import Game, fit, walk_forward

CFBD = "https://api.collegefootballdata.com"
CACHE = config.DATA / "raw" / "cfbd"
OUT = config.DATA / "models" / "college_wind_test.json"
FIRST = 2022
FORECAST_FROM = date(2024, 2, 1)
BOOKS = ("DraftKings", "consensus", "ESPN Bet", "Bovada", "William Hill (New Jersey)")
PAUSE = 0.8                 # seconds between uncached Open-Meteo calls: stays under its 5,000 an hour


def _cfbd(path: str, cache: Path, key: str) -> list:
    if cache.exists():
        return json.loads(cache.read_text())
    req = urllib.request.Request(CFBD + path, headers={"Authorization": "Bearer " + key, "Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data))
    return data


def venues(key: str) -> dict[int, dict]:
    return {v["id"]: v for v in _cfbd("/venues", CACHE / "cfbd_venues.json", key)}


def season_games(year: int, key: str) -> list[dict]:
    out = []
    for st in ("regular", "postseason"):
        current = year >= datetime.now().year
        cache = CACHE / f"cfbd_games_{year}_{st}.json"
        if current and cache.exists() and time.time() - cache.stat().st_mtime > 12 * 3600:
            cache.unlink()
        out += _cfbd(f"/games?year={year}&seasonType={st}&classification=fbs", cache, key)
    return out


def _total(line_game: dict) -> float | None:
    lines = [l for l in line_game.get("lines") or [] if l.get("overUnder") is not None]
    for b in BOOKS:
        for l in lines:
            if l.get("provider") == b:
                return float(l["overUnder"])
    return float(lines[0]["overUnder"]) if lines else None


def games(key: str, first: int = FIRST) -> list[tuple[Game, tuple[float, float]]]:
    """(Game, (lat, lon)) for every completed FBS game since `first` with a closing total, a kickoff time and an open-air venue."""
    vs = venues(key)
    out = []
    for year in range(first, datetime.now().year + 1):
        lp = CACHE / f"cfbd_lines_{year}.json"
        if not lp.exists():
            continue
        totals = {g["id"]: _total(g) for g in json.loads(lp.read_text())}
        for g in season_games(year, key):
            if not g.get("completed") or g.get("startTimeTBD") or g.get("homePoints") is None or g.get("awayPoints") is None:
                continue
            tot = totals.get(g["id"])
            v = vs.get(g.get("venueId"))
            if tot is None or not v or v.get("dome") or v.get("latitude") is None:
                continue
            kick = datetime.fromisoformat(g["startDate"].replace("Z", "+00:00")).astimezone(weather.EASTERN)
            out.append((Game(str(g["id"]), year, f"cfb{v['id']}", kick, tot, float(g["homePoints"] + g["awayPoints"])),
                        (float(v["latitude"]), float(v["longitude"]))))
    return out


def attach(rows: list[tuple[Game, tuple[float, float]]], log=print) -> dict:
    """Reanalysis wind for every game; the day-before forecast from 2024 on. One call per venue and day, cached, throttled."""
    calls = fails = 0
    for i, (g, (lat, lon)) in enumerate(rows):
        d = g.kickoff.date()
        for kind, fn in (("archive", weather.archive_at), ("prevday", weather.previous_day_at)):
            if kind == "prevday" and d < FORECAST_FROM:
                continue
            cached = (weather.CACHE / f"{kind}_{g.stadium}_{d}_{d}.json").exists()
            try:
                hours = fn(g.stadium, lat, lon, d, d)
            except Exception as e:      # a refused or empty day is counted and reported, never filled in
                fails += 1
                log(f"weather {kind} {g.stadium} {d}: {type(e).__name__}: {e}")
                continue
            if not cached:
                calls += 1
                time.sleep(PAUSE)
            w = weather.game_window(hours, g.kickoff)
            if w and kind == "archive":
                g.wind, g.temp, g.precip = w["wind_mph"], w["temp_f"], w["precip_mm"]
            elif w:
                g.fwind = w["wind_mph"]
        if i % 250 == 0:
            log(f"{i}/{len(rows)} games, {calls} new weather calls, {fails} failures")
    return {"new_calls": calls, "failures": fails}


def run(key: str, log=print) -> dict:
    rows = games(key)
    fetched = attach(rows, log)
    gs = [g for g, _ in rows]
    have = [g for g in gs if g.wind is not None]
    fc = [g for g in have if g.fwind is not None]
    out = {"games": len(gs), "with_reanalysis": len(have), "with_forecast": len(fc), **fetched,
           "fit_on_2022_2023": fit([g for g in have if g.season < 2024]) if have else None,
           "held_out_reanalysis_2024_on": walk_forward(gs, 2024),
           "held_out_forecast_2024_on": walk_forward(gs, 2024, use_forecast=True),
           "by_wind_band_forecast": bands(fc)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=str))
    return out


def bands(gs: list[Game]) -> list[dict]:
    """Plain check with no fitting: Unders by day-before forecast wind band (the market already sees the forecast)."""
    out = []
    for lo, hi in ((0, 8), (8, 12), (12, 16), (16, 20), (20, 99)):
        sel = [g for g in gs if lo <= g.fwind < hi]
        u = sum(g.actual < g.close for g in sel)
        o = sum(g.actual > g.close for g in sel)
        out.append({"band_mph": f"{lo}-{hi}", "games": len(sel), "unders": u, "overs": o,
                    "under_rate": round(u / (u + o), 3) if u + o else None,
                    "avg_actual_minus_close": round(sum(g.actual - g.close for g in sel) / len(sel), 2) if sel else None})
    return out


if __name__ == "__main__":
    import sys
    res = run(config.load_env().get("CFBD_API_KEY", ""), log=lambda m: print(m, flush=True))
    print(json.dumps({k: v for k, v in res.items()}, indent=1, default=str))
    sys.exit(0)
