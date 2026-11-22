"""NFL player props model, its held-out test, and its forward test against Pinnacle.

Projection, for each player and stat, using only games before the one projected:
- a weighted average of his recent games (newer games count more; last season's games count less, older
  seasons not at all), needing at least three earlier games;
- scaled for game context: (his team's implied points this game / his team's average implied points in
  the games behind the average) ** alpha. Implied points come from the closing spread and total.
`decay` and `alpha` are fitted per stat on earlier seasons only.

Distribution: books price the median, and these stats are skewed (a floor of 0, a long right tail), so a
projection is turned into a full distribution by looking up the 500 player-games in earlier seasons with
the closest projection and reading what actually happened (yardage scaled to this projection; counts not).
The chance of going over any line is read off that distribution.

Two tests:
- Held-out seasons (`backtest`): is the projection more accurate than a plain recent average, and are its
  over/under probabilities honest (when it says 60%, does it happen about 60% of the time)?
- Forward against Pinnacle (`evaluate_logged`, `grade`): no free history of prop lines exists, so the only
  market test is from now on. Every read logs the model's chance next to Pinnacle's vig-free chance; once
  enough are graded, the model may drive a pick only if it beats Pinnacle (config `models.props`).
"""
from __future__ import annotations

import bisect
import math
import re
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from engine import config
from engine.odds.espn import SourceError
from engine.odds.math import implied_prob, no_vig

RAW = config.DATA / "raw" / "nflverse"
GAMES_CSV = config.DATA / "raw" / "nflverse_games.csv"
STATS_URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{y}.parquet"
FIRST_SEASON = 2018

# Pinnacle's wording -> (stat, kind). Yardage is scaled when reading neighbors; counts are not.
PINNACLE_STATS = {
    "Receptions": ("receptions", "count"), "Receiving Yards": ("receiving_yards", "yards"),
    "Rushing Yards": ("rushing_yards", "yards"), "Rush Attempts": ("carries", "count"),
    "Passing Yards": ("passing_yards", "yards"), "Pass Attempts": ("attempts", "count"),
    "Pass Completions": ("completions", "count"), "Touchdown Passes": ("passing_tds", "count"),
    "Interceptions": ("passing_interceptions", "count"), "Touchdowns": ("tds", "count"),
    "Field Goals": ("fg_made", "count"),
}
KIND = {s: k for s, k in PINNACLE_STATS.values()}
STATS = list(KIND)
USAGE = ("targets", "carries", "attempts", "fg_att")
# who counts as a prop-worthy player for a stat (books do not post props on bit players)
ROLE = {
    "receptions": lambda u: u["targets"] >= 3, "receiving_yards": lambda u: u["targets"] >= 3,
    "rushing_yards": lambda u: u["carries"] >= 6, "carries": lambda u: u["carries"] >= 6,
    "passing_yards": lambda u: u["attempts"] >= 20, "attempts": lambda u: u["attempts"] >= 20,
    "completions": lambda u: u["attempts"] >= 20, "passing_tds": lambda u: u["attempts"] >= 20,
    "passing_interceptions": lambda u: u["attempts"] >= 20, "tds": lambda u: u["targets"] + u["carries"] >= 6,
    "fg_made": lambda u: u["fg_att"] >= 1,
}
DECAYS = (0.75, 0.85, 0.92)
ALPHAS = (0.0, 0.5, 1.0, 1.5)
MAX_BACK = 16
K_NEIGHBORS = 500

TEAM_NAMES = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL", "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR", "Chicago Bears": "CHI", "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL", "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX", "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC", "Los Angeles Rams": "LA", "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN", "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT", "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB", "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}


def norm_name(s: str) -> str:
    s = re.sub(r"[^a-z ]", "", s.lower().replace("-", " "))
    return " ".join(w for w in s.split() if w not in ("jr", "sr", "ii", "iii", "iv", "v"))


def split_description(desc: str) -> tuple[str, str] | None:
    """'Aaron Jones Total Receiving Yards' -> ('Aaron Jones', 'Receiving Yards')."""
    m = re.match(r"^(.*?) Total (.+)$", desc.strip())
    if not m or m.group(2) not in PINNACLE_STATS:
        return None
    return m.group(1), m.group(2)


# ---------------------------------------------------------------- data

def stats_file(year: int, current: bool) -> Path:
    path = RAW / f"stats_player_week_{year}.parquet"
    fresh = path.exists() and path.stat().st_size > 100_000 and (
        not current or (datetime.now().timestamp() - path.stat().st_mtime) < 12 * 3600)
    if fresh:
        return path
    RAW.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(urllib.request.Request(STATS_URL.format(y=year), headers={"User-Agent": "Mozilla/5.0"}), timeout=120) as r:
            data = r.read()
    except OSError as e:
        if path.exists():
            return path
        raise SourceError(f"nflverse player stats for {year} are unreachable ({type(e).__name__})") from None
    if len(data) < 100_000:
        raise SourceError(f"nflverse player stats for {year} came back too small to be real")
    path.write_bytes(data)
    return path


def load_rows(last_season: int) -> list[dict]:
    """One row per player per game (QB, RB, WR, TE, FB, K), in time order, with the team's implied points."""
    files = [str(stats_file(y, y == last_season)) for y in range(FIRST_SEASON, last_season + 1)]
    cols = ", ".join(f"coalesce({c}, 0) AS {c}" for c in
                     ("receptions", "receiving_yards", "rushing_yards", "carries", "passing_yards", "attempts", "completions",
                      "passing_tds", "passing_interceptions", "fg_made", "targets", "fg_att"))
    q = f"""
    SELECT s.player_id, s.player_display_name AS name, s.position, s.season, s.week, s.game_id, s.team, {cols},
           coalesce(s.rushing_tds, 0) + coalesce(s.receiving_tds, 0) AS tds,
           g.gameday, g.home_team, g.spread_line, g.total_line
    FROM read_parquet({files!r}, union_by_name=true) s
    JOIN read_csv_auto('{GAMES_CSV}') g ON g.game_id = s.game_id
    WHERE s.position IN ('QB', 'RB', 'WR', 'TE', 'FB', 'K') AND s.season_type IN ('REG', 'POST')
      AND g.spread_line IS NOT NULL AND g.total_line IS NOT NULL
    ORDER BY g.gameday, s.game_id
    """
    con = duckdb.connect()
    res = con.execute(q)
    names = [d[0] for d in res.description]
    out = []
    for r in res.fetchall():
        d = dict(zip(names, r))
        d["implied"] = implied_points(d["team"] == d["home_team"], d["spread_line"], d["total_line"])
        out.append(d)
    return out


def implied_points(is_home: bool, spread_line: float, total_line: float) -> float:
    """nflverse spread_line is the home team's expected margin."""
    return total_line / 2 + (spread_line / 2 if is_home else -spread_line / 2)


# ---------------------------------------------------------------- projection

def _weighted(hist: list[tuple], season: int, decay: float) -> tuple[dict, float, float] | None:
    """hist = [(season, stats dict, implied)], oldest first. Returns (weighted stats, weighted implied, weight sum)."""
    use = [h for h in hist[-MAX_BACK:] if h[0] >= season - 1]
    if len(use) < 3:
        return None
    acc = defaultdict(float)
    wsum = imp = 0.0
    n = len(use)
    for i, (s, st, im) in enumerate(use):
        w = decay ** (n - 1 - i) * (1.0 if s == season else 0.6)
        wsum += w
        imp += w * im
        for k, v in st.items():
            acc[k] += w * v
    return {k: v / wsum for k, v in acc.items()}, imp / wsum, wsum


def project(hist: list[tuple], season: int, implied: float, decay: float, alpha: dict[str, float]) -> dict | None:
    got = _weighted(hist, season, decay)
    if got is None:
        return None
    avg, avg_imp, _ = got
    ratio = implied / avg_imp if avg_imp > 0 else 1.0
    out = {s: avg[s] * ratio ** alpha.get(s, 0.0) for s in STATS}
    out.update({u: avg[u] for u in USAGE})
    return out


def history_projections(rows: list[dict]) -> list[dict]:
    """For every player-game, the raw weighted averages under each decay (no fitting, no look-ahead)."""
    hist: dict[str, list[tuple]] = defaultdict(list)
    out = []
    for r in rows:
        h = hist[r["player_id"]]
        rec = {"row": r, "by_decay": {}}
        for d in DECAYS + (1.0,):          # 1.0 = plain average, the comparison baseline only
            got = _weighted(h, r["season"], d)
            if got:
                rec["by_decay"][d] = got
        if rec["by_decay"]:
            out.append(rec)
        h.append((r["season"], {k: float(r[k]) for k in STATS + list(USAGE)}, r["implied"]))
    return out


def _proj_one(rec: dict, stat: str, decay: float, alpha: float) -> float | None:
    got = rec["by_decay"].get(decay)
    if got is None:
        return None
    avg, avg_imp, _ = got
    ratio = rec["row"]["implied"] / avg_imp if avg_imp > 0 else 1.0
    return avg[stat] * ratio ** alpha


def fit_stat(recs: list[dict], stat: str) -> tuple[float, float]:
    """decay and alpha with the lowest squared error on these (earlier-season) player-games."""
    best = None
    for d in DECAYS:
        pool = [r for r in recs if d in r["by_decay"] and ROLE[stat](r["by_decay"][d][0])]
        for a in ALPHAS:
            se = sum((_proj_one(r, stat, d, a) - r["row"][stat]) ** 2 for r in pool)
            if pool and (best is None or se / len(pool) < best[0]):
                best = (se / len(pool), d, a)
    return best[1], best[2]


class Distribution:
    """Outcomes of earlier player-games, looked up by how close their projection was."""

    def __init__(self, pairs: list[tuple[float, float]], kind: str, k: int = K_NEIGHBORS):
        self.pairs = sorted(pairs)
        self.keys = [p for p, _ in self.pairs]
        self.kind, self.k = kind, k

    def outcomes(self, proj: float) -> list[float]:
        n = len(self.pairs)
        if n == 0:
            raise ValueError("empty distribution")
        i = bisect.bisect_left(self.keys, proj)
        lo, hi = i, i
        while hi - lo < min(self.k, n):     # widen toward whichever side is closer in log terms
            left = self.keys[lo - 1] if lo > 0 else None
            right = self.keys[hi] if hi < n else None
            if right is None or (left is not None and abs(math.log((proj + 1) / (left + 1))) <= abs(math.log((right + 1) / (proj + 1)))):
                lo -= 1
            else:
                hi += 1
        sel = self.pairs[lo:hi]
        if self.kind == "yards":
            return [a * proj / p if p > 0 else a for p, a in sel]
        return [a for _, a in sel]

    def p_over(self, proj: float, line: float) -> float:
        o = self.outcomes(proj)
        over = sum(1 for x in o if x > line)
        push = sum(1 for x in o if x == line)
        return over / max(1, len(o) - push)

    def median(self, proj: float) -> float:
        o = sorted(self.outcomes(proj))
        return o[len(o) // 2]


# ---------------------------------------------------------------- held-out test

def backtest(first_test: int = 2023, last: int | None = None) -> dict:
    last = last or datetime.now().year
    rows = load_rows(last)
    recs = history_projections(rows)
    report = {}
    for stat in STATS:
        kind = KIND[stat]
        n = 0
        mae_model = mae_base = 0.0
        rel = defaultdict(lambda: [0.0, 0, 0])     # bucket -> [sum p, count, overs]
        brier = brier_base = 0.0
        nb = 0
        params = {}
        for season in range(first_test, last + 1):
            train = [r for r in recs if FIRST_SEASON < r["row"]["season"] < season]
            test = [r for r in recs if r["row"]["season"] == season]
            if not train or not test:
                continue
            d, a = fit_stat(train, stat)
            params[season] = {"decay": d, "alpha": a}
            pool = [r for r in train if d in r["by_decay"] and ROLE[stat](r["by_decay"][d][0])]
            dist = Distribution([(_proj_one(r, stat, d, a), float(r["row"][stat])) for r in pool], kind)
            # baseline: plain average of the last 8 games, no context, distribution read the same way
            base_pairs = [(_plain(r, stat), float(r["row"][stat])) for r in pool if _plain(r, stat) is not None]
            base_dist = Distribution(base_pairs, kind)
            for r in test:
                if d not in r["by_decay"] or not ROLE[stat](r["by_decay"][d][0]):
                    continue
                proj = _proj_one(r, stat, d, a)
                actual = float(r["row"][stat])
                med = dist.median(proj)
                n += 1
                mae_model += abs(actual - med)
                bp = _plain(r, stat)
                mae_base += abs(actual - base_dist.median(bp)) if bp is not None else abs(actual - med)
                # honesty check at three lines a book might post: the model's own median and a step either side
                step = 0.5 if kind == "count" else max(5.0, round(med * 0.15))
                for line in (med - step, med, med + step):
                    line = math.floor(line) + 0.5
                    p = dist.p_over(proj, line)
                    hit = 1 if actual > line else 0
                    b = min(9, int(p * 10))
                    rel[b][0] += p
                    rel[b][1] += 1
                    rel[b][2] += hit
                    brier += (p - hit) ** 2
                    pb = base_dist.p_over(bp, line) if bp is not None else p
                    brier_base += (pb - hit) ** 2
                    nb += 1
        if n == 0:
            continue
        report[stat] = {
            "player_games": n, "mae_model": round(mae_model / n, 2), "mae_plain_average": round(mae_base / n, 2),
            "brier_model": round(brier / nb, 4), "brier_plain_average": round(brier_base / nb, 4), "params": params,
            "calibration": [{"said": round(v[0] / v[1], 3), "happened": round(v[2] / v[1], 3), "n": v[1]}
                            for b, v in sorted(rel.items()) if v[1] >= 30],
        }
    return report


def _plain(rec: dict, stat: str) -> float | None:
    """Plain average of his recent games (last season's games at 0.6 weight), no game context."""
    got = rec["by_decay"].get(1.0)
    return None if got is None else got[0][stat]


# ---------------------------------------------------------------- live model and forward test

class Model:
    """Fitted on every finished season before `season`; projects upcoming games from all games so far."""

    def __init__(self, season: int):
        rows = load_rows(season)
        recs = history_projections(rows)
        train = [r for r in recs if FIRST_SEASON < r["row"]["season"] < season]
        self.season = season
        self.params, self.dists = {}, {}
        for stat in STATS:
            d, a = fit_stat(train, stat)
            pool = [r for r in train if d in r["by_decay"] and ROLE[stat](r["by_decay"][d][0])]
            self.params[stat] = (d, a)
            self.dists[stat] = Distribution([(_proj_one(r, stat, d, a), float(r["row"][stat])) for r in pool], KIND[stat])
        self.hist: dict[str, list[tuple]] = defaultdict(list)
        self.players: dict[tuple[str, str], str] = {}     # (normalized name, team) -> player_id
        self.last_week: dict[str, tuple] = {}
        for r in rows:
            self.hist[r["player_id"]].append((r["season"], {k: float(r[k]) for k in STATS + list(USAGE)}, r["implied"]))
            if r["season"] == season:
                self.players[(norm_name(r["name"]), r["team"])] = r["player_id"]
                self.last_week[r["player_id"]] = (r["week"], r["team"], r["name"])
        self.through_week = max((r["week"] for r in rows if r["season"] == season), default=0)

    def find(self, name: str, teams: tuple[str, str]) -> str | None:
        n = norm_name(name)
        hits = [pid for t in teams if (pid := self.players.get((n, t)))]
        return hits[0] if len(hits) == 1 else None

    def price(self, pid: str, stat: str, line: float, implied: float) -> dict | None:
        d, a = self.params[stat]
        got = _weighted(self.hist[pid], self.season, d)
        if got is None:
            return None
        avg, avg_imp, _ = got
        if not ROLE[stat](avg):
            return None
        proj = avg[stat] * (implied / avg_imp if avg_imp > 0 else 1.0) ** a
        dist = self.dists[stat]
        return {"projection": round(proj, 2), "median": dist.median(proj), "p_over": round(dist.p_over(proj, line), 4)}


SCHEMA = """
CREATE TABLE IF NOT EXISTS prop_evals (
  ts_utc TIMESTAMP, start_utc VARCHAR, away VARCHAR, home VARCHAR, player VARCHAR, player_id VARCHAR, team VARCHAR,
  stat VARCHAR, line DOUBLE, over_price DOUBLE, under_price DOUBLE, market_p_over DOUBLE, model_p_over DOUBLE,
  model_median DOUBLE, projection DOUBLE, season INTEGER, through_week INTEGER,
  outcome DOUBLE, graded_utc TIMESTAMP);
"""


def game_implied(away: str, home: str, at, con) -> tuple[float, float] | None:
    """(away, home) implied points from Pinnacle's game line logged at or before `at` (home_spread < 0 = home favored)."""
    if not _has(con, "line_snapshots"):
        return None
    row = con.execute("""
        SELECT home_spread, total FROM line_snapshots
        WHERE lower(source) = 'pinnacle' AND sport = 'NFL' AND home_spread IS NOT NULL AND total IS NOT NULL
          AND lower(home) = lower(?) AND lower(away) = lower(?) AND ts_utc <= ?
        ORDER BY ts_utc DESC LIMIT 1""", [home, away, at]).fetchone()
    if row is None:
        return None
    hs, tot = row
    return tot / 2 + hs / 2, tot / 2 - hs / 2


def _has(con, table: str) -> bool:
    return bool(con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [table]).fetchone()[0])


def evaluate_logged(con, model: Model, now: datetime, only_latest: bool = True) -> list[dict]:
    """Price every Pinnacle prop logged in the latest read for a game not yet started; store the rows."""
    con.execute(SCHEMA)
    if not _has(con, "derivative_snapshots"):
        return []
    ts = con.execute("SELECT max(ts_utc) FROM derivative_snapshots WHERE source='Pinnacle' AND sport='NFL' AND market='prop'").fetchone()[0]
    if ts is None:
        return []
    rows = con.execute("""
        SELECT ts_utc, start_utc, away, home, description, line, price_a, price_b FROM derivative_snapshots
        WHERE source='Pinnacle' AND sport='NFL' AND market='prop' AND ts_utc = ?""", [ts]).fetchall()
    return _evaluate(con, model, rows, now)


def _evaluate(con, model: Model, rows, now: datetime) -> list[dict]:
    out, implied_cache = [], {}
    for ts, start, away, home, desc, line, po, pu in rows:
        if start and datetime.fromisoformat(start.replace("Z", "+00:00")) <= now:
            continue
        sp = split_description(desc)
        if sp is None or po is None or pu is None:
            continue
        player, label = sp
        stat = PINNACLE_STATS[label][0]
        teams = (TEAM_NAMES.get(away), TEAM_NAMES.get(home))
        if None in teams:
            continue
        pid = model.find(player, teams)
        if pid is None:
            continue
        team = model.last_week[pid][1]
        key = (away, home)
        if key not in implied_cache:
            implied_cache[key] = game_implied(away, home, ts, con)
        imp = implied_cache[key]
        if imp is None:
            continue
        implied = imp[1] if team == teams[1] else imp[0]     # imp = (away, home)
        got = model.price(pid, stat, line, implied)
        if got is None:
            continue
        mp = no_vig(po, pu)[0]
        rec = {"ts_utc": ts, "start_utc": start, "away": away, "home": home, "player": player, "player_id": pid, "team": team,
               "stat": stat, "label": label, "line": line, "over_price": po, "under_price": pu, "market_p_over": round(mp, 4),
               "model_p_over": got["p_over"], "model_median": got["median"], "projection": got["projection"]}
        out.append(rec)
        con.execute("DELETE FROM prop_evals WHERE ts_utc = ? AND player_id = ? AND stat = ? AND line = ?", [ts, pid, stat, line])
        con.execute("INSERT INTO prop_evals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)",
                    [ts, start, away, home, player, pid, team, stat, line, po, pu, rec["market_p_over"], rec["model_p_over"],
                     rec["model_median"], rec["projection"], model.season, model.through_week])
    return out


def backfill(con, model: Model) -> int:
    """Price every logged read (each prop at each read before its game), not just the latest one."""
    con.execute(SCHEMA)
    rows = con.execute("""
        SELECT ts_utc, start_utc, away, home, description, line, price_a, price_b FROM derivative_snapshots
        WHERE source='Pinnacle' AND sport='NFL' AND market='prop' ORDER BY ts_utc""").fetchall()
    n = 0
    for ts in sorted({r[0] for r in rows}):
        n += len(_evaluate(con, model, [r for r in rows if r[0] == ts], ts.replace(tzinfo=timezone.utc)))
    return n


def grade(con, season: int) -> int:
    """Fill in outcomes from nflverse player stats once the game's stats are posted. A player with no stats row
    for that game did not play: the prop is void and stays ungraded."""
    con.execute(SCHEMA)
    open_rows = con.execute("SELECT DISTINCT player_id, stat, start_utc FROM prop_evals WHERE outcome IS NULL").fetchall()
    if not open_rows:
        return 0
    f = stats_file(season, True)
    stats = duckdb.connect().execute(f"""
        SELECT s.player_id, g.gameday, s.receptions, s.receiving_yards, s.rushing_yards, s.carries, s.passing_yards,
               s.attempts, s.completions, s.passing_tds, s.passing_interceptions, s.fg_made,
               coalesce(s.rushing_tds,0) + coalesce(s.receiving_tds,0) AS tds
        FROM read_parquet('{f}') s JOIN read_csv_auto('{GAMES_CSV}') g ON g.game_id = s.game_id""").fetchall()
    cols = ("receptions", "receiving_yards", "rushing_yards", "carries", "passing_yards", "attempts", "completions",
            "passing_tds", "passing_interceptions", "fg_made", "tds")
    by = {(r[0], str(r[1])): dict(zip(cols, r[2:])) for r in stats}
    from zoneinfo import ZoneInfo
    east = ZoneInfo("America/New_York")
    n = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for pid, stat, start in open_rows:
        day = str(datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(east).date())
        got = by.get((pid, day))
        if got is None:
            continue
        con.execute("UPDATE prop_evals SET outcome = ?, graded_utc = ? WHERE player_id = ? AND stat = ? AND start_utc = ? AND outcome IS NULL",
                    [float(got[stat] or 0), now, pid, stat, start])
        n += 1
    return n


def scorecard(con, edge: float = 0.05) -> dict:
    """Model against Pinnacle on graded props, using each prop's last read before kickoff."""
    con.execute(SCHEMA)
    rows = con.execute("""
        SELECT line, over_price, under_price, market_p_over, model_p_over, outcome FROM (
          SELECT *, row_number() OVER (PARTITION BY player_id, stat, start_utc ORDER BY ts_utc DESC) AS rn
          FROM prop_evals WHERE outcome IS NOT NULL) WHERE rn = 1 AND outcome <> line""").fetchall()
    n = len(rows)
    if n == 0:
        return {"graded": 0}
    ll = lambda p, y: -math.log(max(1e-6, p if y else 1 - p))
    res = {"graded": n}
    res["logloss_pinnacle"] = round(sum(ll(m, o > l) for l, _, _, m, _, o in rows) / n, 4)
    res["logloss_model"] = round(sum(ll(q, o > l) for l, _, _, _, q, o in rows) / n, 4)
    best = min((sum(ll(w * q + (1 - w) * m, o > l) for l, _, _, m, q, o in rows) / n, w) for w in [i / 10 for i in range(11)])
    res["best_weight_on_model"] = best[1]
    w = lo = 0
    units = 0.0
    for l, po, pu, m, q, o in rows:
        for side, p, price in (("over", q, po), ("under", 1 - q, pu)):
            if p - implied_prob(price) >= edge:
                won = (o > l) if side == "over" else (o < l)
                w, lo = w + won, lo + (not won)
                units += (100 / -price if price < 0 else price / 100) if won else -1
    res["model_edge_bets"] = {"edge": edge, "won": w, "lost": lo, "units": round(units, 1)}
    return res


def gate_line(sc: dict, pc: dict) -> str:
    """One plain sentence on whether props may drive picks yet."""
    need = pc.get("min_graded", 300)
    n = sc.get("graded", 0)
    if n < need:
        return f"Props are testing only: {n} of {need} graded against Pinnacle so far. No prop picks until then."
    e = sc["model_edge_bets"]
    ok = sc["best_weight_on_model"] > 0 and e["units"] > 0
    verdict = "PASSED: props may be Conditionals" if ok else "NOT PASSED: props stay testing only"
    return (f"{verdict}. {n} graded; error with Pinnacle alone {sc['logloss_pinnacle']}, model {sc['logloss_model']}, "
            f"best weight on the model {sc['best_weight_on_model']:.0%}; the model's {e['edge']:.0%}+ disagreements went {e['won']}-{e['lost']} ({e['units']:+} units).")


def passes_gate(sc: dict, pc: dict) -> bool:
    return (sc.get("graded", 0) >= pc.get("min_graded", 300) and sc["best_weight_on_model"] > 0
            and sc["model_edge_bets"]["units"] > 0)


def write_sheet(rows: list[dict], sc: dict, pc: dict, model: Model, now: datetime) -> Path:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Denver")
    local = now.astimezone(tz)
    edge = pc.get("edge", 0.05)
    out = [f"# NFL props: model against Pinnacle ({local:%a %b %-d, %-I:%M %p} MT)", "",
           f"**{gate_line(sc, pc)}**", "",
           "These are not bets. The model projects each player from his recent games and his team's expected points "
           f"(stats through week {model.through_week}). It does not know about injuries, role changes or who is "
           "inactive, so a big disagreement is more often news the model missed than a mistake by Pinnacle. "
           "Every prop is graded after the game to find out whether the model knows anything Pinnacle does not.", ""]
    lean = []
    for r in rows:
        for side, p, price in (("Over", r["model_p_over"], r["over_price"]), ("Under", 1 - r["model_p_over"], r["under_price"])):
            gap = p - implied_prob(price)
            if gap >= edge:
                lean.append((gap, side, p, price, r))
    lean.sort(key=lambda x: -x[0])
    out += ["## Where the model disagrees with Pinnacle's price by 5% or more", ""]
    if lean:
        out += ["| Kick (MT) | Player | Prop | Pinnacle price | Model chance | Pinnacle chance (no vig) | Model median |", "|---|---|---|---|---|---|---|"]
        for gap, side, p, price, r in lean[:40]:
            kick = datetime.fromisoformat(r["start_utc"].replace("Z", "+00:00")).astimezone(tz)
            mp = r["market_p_over"] if side == "Over" else 1 - r["market_p_over"]
            med = r["model_median"]
            out.append(f"| {kick:%a %-I:%M %p} | {r['player']} | {side} {r['line']:g} {r['label'].lower()} | {int(price):+d} | "
                       f"{p:.0%} | {mp:.0%} | {med:.0f} |" if KIND[r["stat"]] == "yards" else
                       f"| {kick:%a %-I:%M %p} | {r['player']} | {side} {r['line']:g} {r['label'].lower()} | {int(price):+d} | "
                       f"{p:.0%} | {mp:.0%} | {med:g} |")
    else:
        out.append("None.")
    out += ["", f"{len(rows)} props priced; {len(lean)} disagreements at 5% or more.", ""]
    d = config.ROOT / "docs" / "cards"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{local:%Y-%m-%d}-nfl-props.md"
    path.write_text("\n".join(out))
    return path
