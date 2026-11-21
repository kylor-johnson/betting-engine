"""Read-only client for the Wagerhouse customer site.

Only the operations in READ_ONLY can be called. Nothing here can place,
change or cancel a bet. The login comes from .env and is never printed.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from engine.bets.history import parse_wh_time
from engine.odds.espn import SourceError

BASE = "https://wagerhouse.ag/cloud/api/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
READ_ONLY = {
    "System/authenticateCustomer",
    "Customer/getAccountInfo",
    "Lines/Get_LeagueLines2",
    "Report/getDailyFiguresByCustomer",
    "Report/getWagersByFigureDate",
}
SPORTS = {"NFL": ("FOOTBALL", "NFL"), "College": ("FOOTBALL", "College"), "NBA": ("BASKETBALL", "NBA")}


@dataclass
class BookLine:
    """One game's lines, from the home team's side. Team 2 is the home team."""
    sport: str
    away: str
    home: str
    start: datetime | None        # UTC
    home_spread: float | None
    home_spread_price: float | None
    away_spread_price: float | None
    home_ml: float | None
    away_ml: float | None
    total: float | None
    over_price: float | None
    under_price: float | None


def normalize_line(sport: str, r: dict) -> BookLine:
    t1, t2 = (r.get("Team1ID") or "").strip(), (r.get("Team2ID") or "").strip()
    spread = r.get("Spread")
    home_spread = None
    if spread is not None:
        fav = (r.get("FavoredTeamID") or "").strip()
        mag = abs(float(spread))
        home_spread = -mag if fav == t2 else mag if fav == t1 else 0.0 if mag == 0 else None
        if home_spread is None:
            raise SourceError(f"Wagerhouse spread for {t1} at {t2} names no favorite")
    f = lambda k: float(r[k]) if r.get(k) is not None else None
    return BookLine(sport, t1, t2, parse_wh_time(r.get("GameDateTime")), home_spread,
                    f("SpreadAdj2"), f("SpreadAdj1"), f("MoneyLine2"), f("MoneyLine1"),
                    f("TotalPoints"), f("TtlPtsAdj1"), f("TtlPtsAdj2"))


class Wagerhouse:
    def __init__(self, user: str, password: str):
        if not user or not password:
            raise SourceError("Wagerhouse login is missing from .env")
        self._user, self._password = user.upper().strip(), password.upper().strip()
        self._token: str | None = None
        self.customer_id: str | None = None
        self.agent_id: str | None = None
        self.office: str | None = None

    def _post(self, op: str, body: dict) -> dict:
        if op not in READ_ONLY:
            raise PermissionError(f"{op} is not a read-only operation; refused")
        req = urllib.request.Request(
            BASE + op, data=json.dumps(body).encode(), method="POST",
            headers={"Content-Type": "application/json", "User-Agent": UA,
                     "X-Requested-With": "XMLHttpRequest",
                     "Authorization": "Bearer " + (self._token or "undefined")})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            raise SourceError(f"Wagerhouse {op} returned HTTP {e.code}") from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            raise SourceError(f"Wagerhouse {op} failed: {type(e).__name__}") from None

    def login(self) -> None:
        d = self._post("System/authenticateCustomer", {
            "customerID": self._user, "state": True, "password": self._password, "multiaccount": "1",
            "response_type": "code", "client_id": self._user, "domain": "wagerhouse.ag",
            "redirect_uri": "wagerhouse.ag", "operation": "authenticateCustomer", "RRO": 1})
        if not d.get("code") or not d.get("accountInfo"):
            raise SourceError("Wagerhouse sign-in was refused (check the login in .env)")
        self._token = d["code"]
        self.customer_id = d["accountInfo"]["customerID"].strip()
        self.office = (d["accountInfo"].get("Office") or "").strip()

    def lines(self, sport: str) -> list[BookLine]:
        if not self._token:
            self.login()
        stype, sub = SPORTS[sport]
        d = self._post("Lines/Get_LeagueLines2", {
            "customerID": self.customer_id, "operation": "Get_LeagueLines2", "sportType": stype,
            "sportSubType": sub, "period": "Game", "hourFilter": 0, "propDescription": "",
            "wagerType": "Straight", "keyword": "", "office": self.office, "correlationID": "",
            "periodNumber": 0, "periods": 0, "rotOrder": 0, "placeLateFlag": False, "RRO": 1})
        if "Lines" not in d:
            raise SourceError(f"Wagerhouse lines for {sport} came back without a 'Lines' field")
        return [normalize_line(sport, r) for r in d["Lines"] if (r.get("PeriodDescription") or "Game").strip() == "Game"]

    def graded_pull(self, weeks: int = 2, pause: float = 0.4) -> dict:
        """Graded wagers for the current week and `weeks - 1` before it."""
        if not self._token:
            self.login()
        out = {"pulled_at_utc": datetime.now(timezone.utc).isoformat(), "weeks": [], "rows": []}
        today = datetime.now(timezone.utc).date() + timedelta(days=1)
        for wk in range(weeks):
            f = self._post("Report/getDailyFiguresByCustomer", {
                "agentID": self.agent_id or "", "customerID": self.customer_id, "week": wk, "RRO": 1,
                "operation": "getDailyFiguresByCustomer"})
            info = f.get("INFO")
            if not info or "BOW" not in info:
                raise SourceError(f"Wagerhouse weekly figures for week {wk} came back empty")
            bow = date.fromisoformat(info["BOW"][:10])
            out["weeks"].append({"week": wk, "bow": str(bow), "days": [info.get(f"day{i}", 0) or 0 for i in range(1, 8)]})
            for i in range(7):
                d = bow + timedelta(days=i)
                if d > today:
                    break
                w = self._post("Report/getWagersByFigureDate", {
                    "customerID": self.customer_id, "figureDate": str(d), "graded": 1, "week": str(wk),
                    "operation": "getWagersByFigureDate", "RRO": 1})
                lst = w.get("LIST")
                if lst is None:
                    raise SourceError(f"Wagerhouse wagers for {d} came back without a 'LIST' field")
                rows = (lst.get("INFO") or []) if isinstance(lst, dict) else lst
                for r in rows:
                    r["_week"], r["_figure_date"] = wk, str(d)
                out["rows"].extend(rows)
                time.sleep(pause)
        return out
