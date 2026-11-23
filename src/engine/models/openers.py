"""Early-number model: price the opening line from what was known when it was posted.

The idea. The closing line is the sharpest number there is; nothing built from public data beats it. The
opener is softer: it is one book's first guess, posted early in the week, and the market spends the week
correcting it. If our own number, built only from information available when the opener went up, says
where the line is going, betting the opener in that direction gets a better number than the close.

Our number at opener time: team ratings backed out of every earlier closing line (this season, plus last
season counted less), the same ratings the rest of the engine uses. The cutoff for "earlier" is the Sunday
before the week's first game (8 pm Eastern for NFL, so the late Sunday games are excluded; 6 am for
college, after Saturday's games). Nothing after that cutoff is used.

The test, walk-forward: for each season, fit how much of the gap between our number and the opener the
market closes by kickoff, using only earlier seasons. Then on the held-out season, when our number and
the opener disagree by a threshold or more, "bet" the opener in our direction and record:
  - closing line value: how many points better the opener was than the close (the real measure of skill);
  - the record against the final score at the opener's number, against the 52.4% break-even at -110.

Sources: NFL openers and closes are ESPN BET / DraftKings from ESPN's public odds feed (2023 on, cached in
data.nosync/raw/espn). College openers and closes are Bovada from CollegeFootballData (2021 on, cached).
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from engine import config
from engine.picks import ratings

EASTERN = ZoneInfo("America/New_York")
NFL_CSV = config.DATA / "raw" / "nflverse_games.csv"
ESPN_CACHE = config.DATA / "raw" / "espn"
CFBD_CACHE = config.DATA / "raw" / "cfbd"
NFL_BOOKS = ("ESPN BET",)   # DraftKings' "open" on ESPN is its May lookahead line (checked 2026-11-23), not a Sunday opener
CFB_BOOK = "Bovada"
BREAK_EVEN = 110 / 210
THRESHOLDS = {"spread": (1.0, 1.5, 2.0, 3.0), "total": (1.5, 2.0, 3.0, 4.0)}
SHRINK_GRID = [i / 20 for i in range(0, 21)]      # share of (our number - opener) the close takes back


@dataclass
class Game:
    league: str
    season: int
    week: int
    kickoff: datetime                 # UTC
    home: str
    away: str
    neutral: bool
    open_margin: float | None         # expected home margin at the opener (= minus the home spread)
    close_margin: float | None
    open_total: float | None
    close_total: float | None
    margin: float                     # actual home margin
    points: float                     # actual total
    model_margin: float | None = None
    model_total: float | None = None


# ---------- loading ----------

def _american(d: dict | None, key: str) -> float | None:
    try:
        return float(((d or {}).get(key) or {}).get("american"))
    except (TypeError, ValueError):
        return None


def nfl_lines(espn_id: str) -> tuple[float | None, float | None, float | None, float | None] | None:
    """(open home spread, close home spread, open total, close total) from the first book in NFL_BOOKS."""
    p = ESPN_CACHE / f"odds_NFL_{espn_id}.json"
    if not p.exists():
        return None
    items = json.loads(p.read_text()).get("items") or []
    for book in NFL_BOOKS:
        for it in items:
            if (it.get("provider") or {}).get("name") != book:
                continue
            h = it.get("homeTeamOdds") or {}
            os_, cs = _american(h.get("open"), "pointSpread"), _american(h.get("close"), "pointSpread")
            ot, ct = _american(it.get("open"), "total"), _american(it.get("close"), "total")
            if os_ is None and ot is None:
                continue
            return os_, cs, ot, ct
    return None


def nfl_games(first: int = 2023) -> list[Game]:
    out = []
    for r in csv.DictReader(open(NFL_CSV)):
        if int(r["season"]) < first - 1 or r["result"] in ("", None) or not r["gametime"]:
            continue
        ko = datetime.combine(date.fromisoformat(r["gameday"]), time.fromisoformat(r["gametime"]), EASTERN)
        lines = nfl_lines(r["espn"]) if int(r["season"]) >= first and r["espn"] else None
        os_, cs, ot, ct = lines or (None, None, None, None)
        close_m = float(r["spread_line"]) if r["spread_line"] else None          # nflverse: positive = home favored
        close_t = float(r["total_line"]) if r["total_line"] else None
        if lines and cs is not None:
            close_m = -cs
        if lines and ct is not None:
            close_t = ct
        out.append(Game("NFL", int(r["season"]), int(r["week"]) + (100 if r["game_type"] != "REG" else 0),
                        ko.astimezone(timezone.utc), r["home_team"], r["away_team"], r.get("location") == "Neutral",
                        -os_ if os_ is not None else None, close_m, ot, close_t,
                        float(r["result"]), float(r["total"])))
    return out


def cfb_games(first: int = 2021) -> list[Game]:
    out = []
    for season in range(first - 1, 2100):
        p = CFBD_CACHE / f"cfbd_lines_{season}.json"
        if not p.exists():
            if season > first:
                break
            continue
        for g in json.loads(p.read_text()):
            if g.get("homeScore") is None or g.get("awayScore") is None or g.get("seasonType") != "regular":
                continue
            line = next((l for l in g.get("lines") or [] if l.get("provider") == CFB_BOOK), None)
            if line is None or line.get("spread") is None:
                continue
            ko = datetime.fromisoformat(g["startDate"].replace("Z", "+00:00"))
            so, to = line.get("spreadOpen"), line.get("overUnderOpen")
            out.append(Game("College", season, int(g["week"]), ko, str(g["homeTeamId"]), str(g["awayTeamId"]),
                            bool(g.get("neutralSite")), -float(so) if so is not None else None, -float(line["spread"]),
                            float(to) if to is not None else None,
                            float(line["overUnder"]) if line.get("overUnder") is not None else None,
                            float(g["homeScore"] - g["awayScore"]), float(g["homeScore"] + g["awayScore"])))
    return out


# ---------- our number at opener time ----------

def cutoff(league: str, week_start: datetime) -> datetime:
    """The Sunday before the week's first game: 8 pm Eastern for NFL, 6 am for college."""
    local = week_start.astimezone(EASTERN).date()
    sunday = local - timedelta(days=(local.weekday() + 1) % 7 or 7)
    at = time(20, 0) if league == "NFL" else time(6, 0)
    return datetime.combine(sunday, at, EASTERN).astimezone(timezone.utc)


def attach_model(games: list[Game], hfa: float, decay: float = 0.9, season_gap: int = 8, source: str = "close", lag_days: int = 0) -> None:
    """Fill model_margin / model_total for every game, using games that kicked off before its cutoff.

    source "close": ratings from earlier closing lines (what the market thought).
    source "result": ratings from earlier final scores, margins capped at 21 (what actually happened). A game's
    result only counts if it had finished by the cutoff (kickoff at least four hours before it)."""
    by_week: dict[tuple[int, int], list[Game]] = {}
    for g in games:
        by_week.setdefault((g.season, g.week), []).append(g)
    min_games = 40 if games and games[0].league == "NFL" else 200
    for (season, week), wk in sorted(by_week.items()):
        cut = cutoff(wk[0].league, min(g.kickoff for g in wk)) - timedelta(days=lag_days)
        seasons_max = {}
        for g in games:
            if g.kickoff < cut and g.season in (season - 1, season):
                seasons_max[g.season] = max(seasons_max.get(g.season, 0), g.week)
        past = []
        for g in games:
            if g.kickoff >= cut or g.season not in (season - 1, season) or g.close_margin is None:
                continue
            if source == "result" and g.kickoff > cut - timedelta(hours=4):
                continue
            if g.season == season:
                ago = seasons_max[season] - g.week
            else:
                ago = seasons_max.get(season, 0) + season_gap + (seasons_max[g.season] - g.week)
            past.append({"home": g.home, "away": g.away, "home_margin": g.close_margin if source == "close" else max(-21.0, min(21.0, g.margin)),
                         "total": g.close_total if source == "close" else g.points,
                         "weeks_ago": min(ago, 60), "neutral": g.neutral})
        if len(past) < min_games:
            continue
        sr, tend, avg, _ = ratings.fit(past, hfa, decay=decay, min_games=min_games)
        for g in wk:
            if g.home in sr and g.away in sr:
                g.model_margin = sr[g.home] - sr[g.away] + (0.0 if g.neutral else hfa)
                if avg is not None:
                    g.model_total = avg + tend.get(g.home, 0.0) + tend.get(g.away, 0.0)


# ---------- the test ----------

def _kind(g: Game, kind: str):
    if kind == "spread":
        return g.open_margin, g.close_margin, g.model_margin, g.margin
    return g.open_total, g.close_total, g.model_total, g.points


def usable(games: list[Game], kind: str) -> list[Game]:
    return [g for g in games if all(v is not None for v in _kind(g, kind)[:3])]


def fit_share(games: list[Game], kind: str) -> float:
    """Least-squares share k in (close - open) = k x (model - open), searched on a grid from 0 to 1."""
    best, best_err = 0.0, math.inf
    for k in SHRINK_GRID:
        err = 0.0
        for g in games:
            o, c, m, _ = _kind(g, kind)
            err += (c - o - k * (m - o)) ** 2
        if err < best_err:
            best, best_err = k, err
    return best


def grade_open(g: Game, kind: str, side: int) -> float | None:
    """+1 win, 0 push, -1 loss for a bet at the opener. side +1 = home / over, -1 = away / under."""
    o, _, _, actual = _kind(g, kind)
    diff = (actual - o) * side
    return 1.0 if diff > 0 else -1.0 if diff < 0 else 0.0


def walk_forward(games: list[Game], kind: str, first_test: int) -> dict:
    """Held-out seasons from first_test on. For each, k is fitted on earlier seasons only."""
    use = usable(games, kind)
    seasons = sorted({g.season for g in use})
    out = {"kind": kind, "seasons": {}, "bets": {t: [] for t in THRESHOLDS[kind]}}
    for s in seasons:
        if s < first_test:
            continue
        train = [g for g in use if g.season < s]
        test = [g for g in use if g.season == s]
        if len(train) < 100:
            continue
        k = fit_share(train, kind)
        move_sq_open = sum((_kind(g, kind)[1] - _kind(g, kind)[0]) ** 2 for g in test)
        move_sq_model = sum((_kind(g, kind)[1] - _kind(g, kind)[0] - k * (_kind(g, kind)[2] - _kind(g, kind)[0])) ** 2
                            for g in test)
        out["seasons"][s] = {"k": k, "games": len(test),
                             "close_error_open": math.sqrt(move_sq_open / len(test)),
                             "close_error_model": math.sqrt(move_sq_model / len(test))}
        for g in test:
            o, c, m, _ = _kind(g, kind)
            gap = m - o
            for t in THRESHOLDS[kind]:
                if abs(gap) >= t:
                    side = 1 if gap > 0 else -1
                    out["bets"][t].append({"season": s, "clv": (c - o) * side, "result": grade_open(g, kind, side),
                                           "game": g})
    return out


def summarize(bets: list[dict]) -> dict:
    if not bets:
        return {"n": 0}
    w = sum(1 for b in bets if b["result"] > 0)
    l = sum(1 for b in bets if b["result"] < 0)
    clv = sum(b["clv"] for b in bets) / len(bets)
    moved_our_way = sum(1 for b in bets if b["clv"] > 0)
    moved_against = sum(1 for b in bets if b["clv"] < 0)
    return {"n": len(bets), "won": w, "lost": l, "pct": w / (w + l) if w + l else None,
            "units": w * (100 / 110) - l, "avg_clv": clv, "moved_our_way": moved_our_way, "moved_against": moved_against}


def run(league: str, source: str = "close", lag_days: int = 0) -> dict:
    hfa = config.load_config()["picks"]["home_field"][league]
    games = nfl_games() if league == "NFL" else cfb_games()
    attach_model(games, hfa, source=source, lag_days=lag_days)
    first_test = 2024 if league == "NFL" else 2023
    return {kind: walk_forward(games, kind, first_test) for kind in ("spread", "total")}
