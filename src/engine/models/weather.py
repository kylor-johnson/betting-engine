"""Game-time weather for NFL stadiums from Open-Meteo (free, no key).

Three sources, one shape (wind in mph at 10 m, temperature in F, precipitation in mm/h):
- `archive`: reanalysis (what the weather actually was), 1940 to about a week ago. Used to fit and test.
- `previous_day`: the forecast issued the day before, kept by Open-Meteo's previous-runs service. Used to
  check that a forecast is close enough to the reanalysis for the tested effect to carry over.
- `forecast`: the live forecast for an upcoming kickoff. Used on the slate.

Fail loudly: a source that does not answer raises SourceError; nothing is filled in.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from engine import config
from engine.odds.espn import SourceError

CACHE = config.DATA / "raw" / "weather"
EASTERN = ZoneInfo("America/New_York")

# stadium id (nflverse) -> (lat, lon). Outdoor and retractable-roof venues used since 2010.
STADIUMS = {
    "ATL97": (33.755, -84.401), "BAL00": (39.278, -76.623), "BOS00": (42.091, -71.264), "BUF00": (42.774, -78.787),
    "CAR00": (35.226, -80.853), "CHI98": (41.862, -87.617), "CIN00": (39.095, -84.516), "CLE00": (41.506, -81.700),
    "DAL00": (32.748, -97.093), "DEN00": (39.744, -105.020), "FRA00": (50.069, 8.645), "GER00": (48.219, 11.625),
    "GNB00": (44.501, -88.062), "HOU00": (29.685, -95.411), "IND00": (39.760, -86.164), "JAX00": (30.324, -81.637),
    "KAN00": (39.049, -94.484), "LAX97": (33.864, -118.261), "LAX99": (34.014, -118.288), "LON00": (51.556, -0.280),
    "LON01": (51.456, -0.342), "LON02": (51.604, -0.066), "MEX00": (19.303, -99.150), "MIA00": (25.958, -80.239),
    "MIN98": (44.976, -93.225), "NAS00": (36.166, -86.771), "NYC01": (40.814, -74.074), "OAK00": (37.751, -122.201),
    "PHI00": (39.901, -75.168), "PHO00": (33.528, -112.263), "PIT00": (40.447, -80.016), "RIO00": (-22.912, -43.230),
    "SAO00": (-23.545, -46.474), "SDG00": (32.783, -117.120), "SEA00": (47.595, -122.332), "SFO00": (37.714, -122.386),
    "SFO01": (37.403, -121.970), "TAM00": (27.976, -82.503), "WAS00": (38.908, -76.864),
}

# current home stadium by ESPN team abbreviation; None = dome or fixed roof (weather does not apply)
HOME_STADIUM = {
    "BAL": "BAL00", "NE": "BOS00", "BUF": "BUF00", "CAR": "CAR00", "CHI": "CHI98", "CIN": "CIN00", "CLE": "CLE00",
    "DEN": "DEN00", "GB": "GNB00", "JAX": "JAX00", "KC": "KAN00", "MIA": "MIA00", "TEN": "NAS00", "NYG": "NYC01",
    "NYJ": "NYC01", "PHI": "PHI00", "PIT": "PIT00", "SEA": "SEA00", "SF": "SFO01", "TB": "TAM00", "WSH": "WAS00",
    # roofed: retractable roofs are usually closed in bad weather, so treat as no weather
    "ATL": None, "DAL": None, "DET": None, "HOU": None, "IND": None, "LV": None, "LAR": None, "LAC": None,
    "MIN": None, "NO": None, "ARI": None,
}

VARS = "wind_speed_10m,temperature_2m,precipitation"


def _get(url: str, params: dict, tries: int = 3) -> dict:
    q = url + "?" + urllib.parse.urlencode(params)
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(q, headers={"User-Agent": "betting-engine/0.1"}), timeout=90) as r:
                data = json.loads(r.read())
            if data.get("error"):
                raise SourceError(f"Open-Meteo refused the request: {data.get('reason')}")
            return data
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(2 + 3 * i)
    raise SourceError(f"Open-Meteo is unreachable ({type(last).__name__})")


def _hourly(data: dict, suffix: str = "") -> dict[str, tuple[float, float, float]]:
    h = data.get("hourly") or {}
    times = h.get("time") or []
    w, t, p = (h.get(v + suffix) or [None] * len(times) for v in VARS.split(","))
    return {ts: (w[i], t[i], p[i]) for i, ts in enumerate(times)}


def archive(stadium: str, start: date, end: date) -> dict[str, tuple]:
    """Hourly reanalysis at a stadium, keyed 'YYYY-MM-DDTHH:00' in Eastern time. Cached on disk."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"archive_{stadium}_{start}_{end}.json"
    if path.exists():
        return {k: tuple(v) for k, v in json.loads(path.read_text()).items()}
    lat, lon = STADIUMS[stadium]
    data = _get("https://archive-api.open-meteo.com/v1/archive", {
        "latitude": lat, "longitude": lon, "start_date": str(start), "end_date": str(end), "hourly": VARS,
        "wind_speed_unit": "mph", "temperature_unit": "fahrenheit", "timezone": "America/New_York"})
    out = _hourly(data)
    if not out:
        raise SourceError(f"Open-Meteo archive returned no hours for {stadium}")
    path.write_text(json.dumps(out))
    return out


def previous_day(stadium: str, start: date, end: date) -> dict[str, tuple]:
    """The forecast issued about 24 hours earlier for each hour. Open-Meteo keeps these from early 2024."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"prevday_{stadium}_{start}_{end}.json"
    if path.exists():
        return {k: tuple(v) for k, v in json.loads(path.read_text()).items()}
    lat, lon = STADIUMS[stadium]
    hourly = ",".join(f"{v}_previous_day1" for v in VARS.split(","))
    data = _get("https://previous-runs-api.open-meteo.com/v1/forecast", {
        "latitude": lat, "longitude": lon, "start_date": str(start), "end_date": str(end), "hourly": hourly,
        "wind_speed_unit": "mph", "temperature_unit": "fahrenheit", "timezone": "America/New_York"})
    out = _hourly(data, "_previous_day1")
    path.write_text(json.dumps(out))
    return out


def forecast_at(stadium: str, kickoff_utc: datetime) -> dict:
    """Live forecast averaged over the first three hours of the game. Not cached."""
    lat, lon = STADIUMS[stadium]
    data = _get("https://api.open-meteo.com/v1/forecast", {
        "latitude": lat, "longitude": lon, "hourly": VARS, "forecast_days": 16,
        "wind_speed_unit": "mph", "temperature_unit": "fahrenheit", "timezone": "America/New_York"})
    hours = _hourly(data)
    got = game_window(hours, kickoff_utc.astimezone(EASTERN))
    if got is None:
        raise SourceError(f"Open-Meteo forecast has no hours for {stadium} at {kickoff_utc:%Y-%m-%d %H:%M} UTC")
    return got


def game_window(hours: dict[str, tuple], kickoff_eastern: datetime, span: int = 3) -> dict | None:
    """Average wind, temperature and total precipitation over the game's first `span` hours."""
    base = kickoff_eastern.replace(minute=0, second=0, microsecond=0)
    rows = []
    for i in range(span):
        key = datetime.fromtimestamp(base.timestamp() + 3600 * i, EASTERN).strftime("%Y-%m-%dT%H:00")
        v = hours.get(key)
        if v and v[0] is not None:
            rows.append(v)
    if not rows:
        return None
    return {"wind_mph": round(sum(r[0] for r in rows) / len(rows), 1),
            "temp_f": None if any(r[1] is None for r in rows) else round(sum(r[1] for r in rows) / len(rows), 1),
            "precip_mm": None if any(r[2] is None for r in rows) else round(sum(r[2] for r in rows), 1)}
