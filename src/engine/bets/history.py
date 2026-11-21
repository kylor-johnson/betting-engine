"""Turn the raw Wagerhouse graded-wager pull into wagers and legs."""
from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

WH_TZ = ZoneInfo("America/New_York")

CHANNELS = {"Internet": "pregame", "GSLIVE": "live", "GSBUILDER": "builder"}
LEG_KINDS = {"S": "spread", "L": "total", "M": "moneyline", "E": "team_total"}
IN_SCOPE_SPORTS = {"NFL", "College", "NBA"}


def parse_wh_time(s: str | None) -> datetime | None:
    """Wagerhouse times are Eastern wall-clock. Return UTC, or None for blanks."""
    if not s or s.startswith("1900"):
        return None
    naive = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    return naive.replace(tzinfo=WH_TZ).astimezone(timezone.utc)


def _clean(s) -> str:
    return html.unescape(s or "").replace("\r", " ").replace("\n", " ").strip()


@dataclass
class Leg:
    item: int
    kind: str            # spread, total, moneyline, team_total, prop, other
    sport: str           # NFL, College, NBA, MLB, NHL, NFLPLRPROPS, ""
    team1: str
    team2: str
    chosen: str
    line: float | None        # the number bet (before teaser points)
    orig_line: float | None   # before bought points
    buy_points: float
    teaser_points: float
    over_under: str      # "O", "U" or ""
    price: int | None
    game_time: datetime | None
    outcome: str
    period: str


@dataclass
class Wager:
    ticket: int
    wager_no: int
    type_code: str       # S L M P T C E G
    channel: str         # pregame, live, builder
    accepted: datetime | None
    risk: float
    to_win: float
    won: float
    lost: float
    status: str          # W L X
    free_play: bool
    teaser_name: str
    description: str
    week: str            # first day of the account week (Tuesday), e.g. 2026-11-10
    legs: list[Leg] = field(default_factory=list)

    @property
    def net(self) -> float:
        """Free-play losses cost nothing; free-play wins are real money."""
        return self.won - (0.0 if self.free_play else self.lost)

    @property
    def key(self) -> str:
        return f"{self.ticket}-{self.wager_no}"

    @property
    def sports(self) -> set[str]:
        return {l.sport for l in self.legs if l.sport}


def _leg(r: dict) -> Leg:
    sport = (r.get("SportSubType") or "").strip()
    code = (r.get("LegWagerType") or "").strip()
    kind = LEG_KINDS.get(code, "other")
    if "PROPS" in sport.upper() or r.get("WagerType") == "C":
        kind = "prop"
    if kind == "spread":
        line, orig = r.get("AdjSpread"), r.get("OrigSpread")
    elif kind in ("total", "team_total", "prop"):
        line, orig = r.get("AdjTotalPoints"), r.get("OrigTotalPoints")
    else:
        line = orig = None
    price = r.get("FinalMoney")
    return Leg(
        item=int(r.get("ItemNumber") or 0),
        kind=kind,
        sport=sport,
        team1=_clean(r.get("Team1ID")),
        team2=_clean(r.get("Team2ID")),
        chosen=_clean(r.get("ChosenTeamID")),
        line=float(line) if line is not None else None,
        orig_line=float(orig) if orig is not None else None,
        buy_points=float(r.get("BuyPoints") or 0),
        teaser_points=float(r.get("TeaserPoints") or 0),
        over_under=(r.get("TotalPointsOU") or "").strip(),
        price=int(price) if price not in (None, 0) else None,
        game_time=parse_wh_time(r.get("GameDateTime")),
        outcome=(r.get("Outcome") or "").strip(),
        period=(r.get("PeriodDescription") or "").strip(),
    )


def load_wagers(path: str | Path) -> list[Wager]:
    """Read a pull file. The site repeats each wager once per day of its week,
    so rows are de-duplicated on ticket, wager and leg."""
    data = json.loads(Path(path).read_text())
    rows = data["rows"]
    if not rows:
        raise ValueError(f"{path} has no rows")
    bows = {w["week"]: w.get("bow", str(w["week"])) for w in data.get("weeks", [])}
    wagers: dict[tuple, Wager] = {}
    seen_legs: set[tuple] = set()
    for r in rows:
        k = (r["TicketNumber"], r["WagerNumber"])
        w = wagers.get(k)
        if w is None:
            writer = (r.get("TicketWriter") or "").strip()
            if writer not in CHANNELS:
                raise ValueError(f"unknown ticket writer {writer!r} on ticket {k}")
            w = wagers[k] = Wager(
                ticket=r["TicketNumber"],
                wager_no=r["WagerNumber"],
                type_code=r["WagerType"],
                channel=CHANNELS[writer],
                accepted=parse_wh_time(r.get("AcceptedDateTime")),
                risk=r["AmountWagered"] / 100,
                to_win=r["ToWinAmount"] / 100,
                won=r["AmountWon"] / 100,
                lost=r["AmountLost"] / 100,
                status=r["WagerStatus"],
                free_play=r.get("FreePlayFlag") == "Y",
                teaser_name=(r.get("TeaserName") or "").strip() if r["WagerType"] == "T" else "",
                description=_clean(r.get("Description")),
                week=r.get("_bow") or bows.get(r.get("_week"), str(r.get("_week", ""))),
            )
        lk = (*k, r.get("ItemNumber"), r.get("PlayNumber"))
        if lk in seen_legs:
            continue
        seen_legs.add(lk)
        w.legs.append(_leg(r))
    for w in wagers.values():
        w.legs.sort(key=lambda l: l.item)
    return list(wagers.values())


def weekly_figures(path: str | Path) -> dict[str, float]:
    """The account's own net per week, keyed by the week's first day."""
    data = json.loads(Path(path).read_text())
    return {w.get("bow", str(w["week"])): round(sum(w["days"]), 2) for w in data["weeks"]}


def merge_pull(master: dict | None, pull: dict) -> dict:
    """Fold a fresh pull into the running history. Newer rows and figures win."""
    bows = {w["week"]: w.get("bow", str(w["week"])) for w in pull.get("weeks", [])}
    out = master or {"weeks": [], "rows": []}
    weeks = {w["bow"]: w for w in out["weeks"]}
    for w in pull.get("weeks", []):
        bow = w.get("bow", str(w["week"]))
        weeks[bow] = {"week": bow, "bow": bow, "days": w["days"]}
    fresh = set()
    for r in pull["rows"]:
        r["_bow"] = r.get("_bow") or bows.get(r.get("_week"), str(r.get("_week", "")))
        fresh.add((r["TicketNumber"], r["WagerNumber"]))
    rows = [r for r in out["rows"] if (r["TicketNumber"], r["WagerNumber"]) not in fresh] + pull["rows"]
    return {"pulled_at_utc": pull.get("pulled_at_utc"), "weeks": sorted(weeks.values(), key=lambda w: w["bow"]), "rows": rows}


def category(w: Wager) -> str:
    """Plain-language bucket for a wager."""
    if w.channel == "live":
        return "Live in-game"
    if w.channel == "builder":
        return "Same-game builder"
    out_of_scope = w.sports and not (w.sports & IN_SCOPE_SPORTS) and "NFLPLRPROPS" not in w.sports
    if w.type_code == "T":
        pts = max((l.teaser_points for l in w.legs), default=0)
        return f"Teaser, {len(w.legs)}-team {pts:g}-point"
    if w.type_code == "P":
        if all(l.kind == "moneyline" and (l.price or 0) < 0 for l in w.legs):
            return "Parlay, all moneyline favorites"
        return "Parlay, mixed"
    if w.type_code == "C" or any(l.kind == "prop" for l in w.legs):
        return "Player prop"
    if out_of_scope:
        return "Baseball and hockey straight bets"
    if w.type_code == "M":
        price = w.legs[0].price or 0
        if price <= -300:
            return "Moneyline, -300 or shorter"
        if price < 0:
            return "Moneyline, favorite under -300"
        return "Moneyline, underdog"
    if w.type_code == "S":
        return "Spread, bought points" if w.legs[0].buy_points else "Spread"
    if w.type_code == "L":
        return "Total, bought points" if w.legs[0].buy_points else "Total"
    if w.type_code == "E":
        return "Team total"
    return f"Other ({w.type_code})"
