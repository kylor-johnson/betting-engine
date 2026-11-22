"""NFL totals model, built the way pace-and-efficiency handicappers describe it.

Expected points for a team = how many drives it will get x how many points it
scores per drive x how soft the opposing defense is. Points per drive is half
the real number and half what the team's play-by-play success rate says it
should be, which takes out some turnover and red-zone luck. Everything is
pulled toward league average when a team has played few games.

The model is only worth using if it adds something on top of the market's
total. `backtest` measures exactly that, walking forward week by week.
"""
from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb

from engine import config
from engine.odds.espn import SourceError

PBP_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{year}.parquet"
RAW = config.DATA / "raw" / "nflverse"
K_DRIVES, K_PLAYS, K_GAMES = 40.0, 250.0, 3.0      # how hard to pull small samples toward league average


def pbp_file(year: int, current: bool) -> Path:
    path = RAW / f"pbp_{year}.parquet"
    fresh = path.exists() and path.stat().st_size > 1_000_000 and (
        not current or (datetime.now().timestamp() - path.stat().st_mtime) < 12 * 3600)
    if fresh:
        return path
    RAW.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(urllib.request.Request(PBP_URL.format(year=year), headers={"User-Agent": "Mozilla/5.0"}), timeout=240) as r:
            data = r.read()
    except (urllib.error.URLError, TimeoutError) as e:
        if path.exists():
            return path          # keep working from the last good copy
        raise SourceError(f"nflverse play-by-play for {year} is unreachable ({type(e).__name__})") from None
    if len(data) < 1_000_000:
        raise SourceError(f"nflverse play-by-play for {year} came back too small to be real")
    path.write_bytes(data)
    return path


def team_games(years: list[int], current_year: int) -> list[dict]:
    """One row per team per game: drives, points from drives, plays, successful plays, luck inputs."""
    files = [str(pbp_file(y, y == current_year)) for y in years]
    con = duckdb.connect()
    q = f"""
    WITH plays AS (
      SELECT * FROM read_parquet({files!r}, union_by_name=true)
      WHERE season_type = 'REG' AND posteam IS NOT NULL AND fixed_drive IS NOT NULL
    ), drives AS (
      SELECT game_id, season, week, posteam AS team, defteam AS opp, fixed_drive,
             max(fixed_drive_result) AS res,
             count(*) FILTER (WHERE play_type IN ('pass','run')) AS plays,
             coalesce(sum(success) FILTER (WHERE play_type IN ('pass','run')), 0) AS succ,
             min(yardline_100) AS closest
      FROM plays GROUP BY ALL
    ), off AS (
      SELECT game_id, season, week, team, opp,
             count(*) FILTER (WHERE NOT (res = 'End of half' AND plays <= 3)) AS drives,
             sum(CASE res WHEN 'Touchdown' THEN 7 WHEN 'Field goal' THEN 3 ELSE 0 END) AS pts,
             sum(plays) AS plays, sum(succ) AS succ,
             count(*) FILTER (WHERE closest <= 20) AS rz, count(*) FILTER (WHERE closest <= 20 AND res = 'Touchdown') AS rz_td
      FROM drives GROUP BY ALL
    ), fum AS (
      SELECT game_id, posteam AS team, coalesce(sum(fumble), 0) AS fumbles, coalesce(sum(fumble_lost), 0) AS lost,
             coalesce(sum(interception), 0) AS ints
      FROM plays GROUP BY ALL
    ), score AS (
      SELECT game_id, max(total_home_score) + max(total_away_score) AS total FROM plays GROUP BY ALL
    )
    SELECT o.game_id, o.season, o.week, o.team, o.opp, o.drives, o.pts, o.plays, o.succ, o.rz, o.rz_td,
           f.fumbles, f.lost, f.ints, s.total
    FROM off o JOIN fum f USING (game_id, team) JOIN score s USING (game_id)
    ORDER BY o.season, o.week"""
    cols = ["game_id", "season", "week", "team", "opp", "drives", "pts", "plays", "succ", "rz", "rz_td", "fumbles", "lost", "ints", "total"]
    rows = [dict(zip(cols, r)) for r in con.execute(q).fetchall()]
    con.close()
    if not rows:
        raise SourceError("no play-by-play rows came back")
    return rows


@dataclass
class TeamNumbers:
    off_ppd: float       # points per drive, luck-reduced and pulled toward average
    def_ppd: float
    drives: float        # drives per game involving this team (own offense and opponents averaged)
    games: int


@dataclass
class Model:
    teams: dict[str, TeamNumbers]
    league_ppd: float
    league_drives: float
    extra: float         # points per game that do not come from offensive drives (returns, defensive scores)
    luck: dict[str, dict]

    def total(self, home: str, away: str) -> float | None:
        h, a = self.teams.get(home), self.teams.get(away)
        if h is None or a is None:
            return None
        d = (h.drives + a.drives) / 2
        return d * h.off_ppd * a.def_ppd / self.league_ppd + d * a.off_ppd * h.def_ppd / self.league_ppd + self.extra


def _fit_line(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    var = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var if var else 0.0
    return my - b * mx, b


def fit(rows: list[dict]) -> Model:
    """Build the model from team-game rows (pass only the games that should count)."""
    if len(rows) < 60:
        raise ValueError("too few games for a totals model")
    agg: dict[str, dict] = {}
    for r in rows:
        o = agg.setdefault(r["team"], dict(g=0, d=0, p=0, pl=0, s=0, ad=0, ap=0, apl=0, asu=0, rz=0, rztd=0, f=0, fl=0, i=0, of=0, ofl=0, oi=0))
        o["g"] += 1; o["d"] += r["drives"]; o["p"] += r["pts"]; o["pl"] += r["plays"]; o["s"] += r["succ"]
        o["rz"] += r["rz"]; o["rztd"] += r["rz_td"]; o["f"] += r["fumbles"]; o["fl"] += r["lost"]; o["i"] += r["ints"]
        x = agg.setdefault(r["opp"], dict(g=0, d=0, p=0, pl=0, s=0, ad=0, ap=0, apl=0, asu=0, rz=0, rztd=0, f=0, fl=0, i=0, of=0, ofl=0, oi=0))
        x["ad"] += r["drives"]; x["ap"] += r["pts"]; x["apl"] += r["plays"]; x["asu"] += r["succ"]
        x["of"] += r["fumbles"]; x["ofl"] += r["lost"]; x["oi"] += r["ints"]
    tot_d = sum(o["d"] for o in agg.values()); tot_p = sum(o["p"] for o in agg.values())
    tot_pl = sum(o["pl"] for o in agg.values()); tot_s = sum(o["s"] for o in agg.values())
    L_ppd, L_sr = tot_p / tot_d, tot_s / tot_pl
    games = {r["game_id"]: r["total"] for r in rows}
    drive_pts_per_game = tot_p / len(games)
    extra = sum(games.values()) / len(games) - drive_pts_per_game
    L_drives = tot_d / sum(o["g"] for o in agg.values())
    usable = [o for o in agg.values() if o["d"] >= 20 and o["pl"] >= 100]
    a, b = _fit_line([o["s"] / o["pl"] for o in usable], [o["p"] / o["d"] for o in usable]) if len(usable) >= 8 else (L_ppd, 0.0)
    rz_rate = sum(o["rztd"] for o in agg.values()) / max(1, sum(o["rz"] for o in agg.values()))
    teams, luck = {}, {}
    for t, o in agg.items():
        if not o["g"]:
            continue
        ppd = (o["p"] + K_DRIVES * L_ppd) / (o["d"] + K_DRIVES)
        sr = (o["s"] + K_PLAYS * L_sr) / (o["pl"] + K_PLAYS)
        dppd = (o["ap"] + K_DRIVES * L_ppd) / (o["ad"] + K_DRIVES)
        dsr = (o["asu"] + K_PLAYS * L_sr) / (o["apl"] + K_PLAYS)
        dr = ((o["d"] + o["ad"]) / 2 + K_GAMES * L_drives) / (o["g"] + K_GAMES)
        teams[t] = TeamNumbers(0.5 * ppd + 0.5 * (a + b * sr), 0.5 * dppd + 0.5 * (a + b * dsr), dr, o["g"])
        all_f = o["f"] + o["of"]
        luck[t] = {
            "games": o["g"],
            "fumbles_recovered_share": round((o["f"] - o["fl"] + o["ofl"]) / all_f, 2) if all_f >= 8 else None,   # 0.50 is neutral
            "turnover_margin": int((o["ofl"] + o["oi"]) - (o["fl"] + o["i"])),
            "red_zone_td_rate": round(o["rztd"] / o["rz"], 2) if o["rz"] >= 12 else None,
            "league_red_zone_td_rate": round(rz_rate, 2),
            "points_per_drive": round(o["p"] / o["d"], 2), "points_per_drive_from_success_rate": round(a + b * (o["s"] / o["pl"]), 2),
        }
    return Model(teams, L_ppd, L_drives, extra, luck)


def current(now: datetime) -> Model:
    """The model as of now: this season's regular-season games so far."""
    year = now.year if now.month >= 8 else now.year - 1
    rows = [r for r in team_games([year], year) if r["season"] == year]
    return fit(rows)


def backtest(years: list[int], current_year: int, closes: dict[str, tuple[float, float]], first_week: int = 5) -> dict:
    """Walk forward: for each game, fit on that season's earlier weeks only, then compare.

    closes: game_id -> (closing total, actual total)."""
    rows = team_games(years, current_year)
    out = []
    for season in years:
        srows = [r for r in rows if r["season"] == season]
        for week in sorted({r["week"] for r in srows}):
            if week < first_week:
                continue
            prior = [r for r in srows if r["week"] < week]
            if len(prior) < 60:
                continue
            m = fit(prior)
            seen = set()
            for r in (x for x in srows if x["week"] == week):
                gid = r["game_id"]
                if gid in seen or gid not in closes:
                    continue
                seen.add(gid)
                away, home = gid.split("_")[2], gid.split("_")[3]
                pred = m.total(home, away)
                if pred is not None:
                    close, actual = closes[gid]
                    out.append({"season": season, "week": week, "game": gid, "model": pred, "close": close, "actual": actual})
    n = len(out)
    if n < 100:
        raise ValueError(f"only {n} games in the backtest")
    mae = lambda f: sum(abs(f(g) - g["actual"]) for g in out) / n
    best_w, best = 1.0, None
    grid = {}
    for i in range(0, 21):
        w = i / 20                                   # weight on the market
        e = sum((w * g["close"] + (1 - w) * g["model"] - g["actual"]) ** 2 for g in out) / n
        grid[w] = e
        if best is None or e < best:
            best_w, best = w, e
    bets = {}
    for gap in (1.5, 2.5, 3.5):
        picks = [g for g in out if abs(g["model"] - g["close"]) >= gap and g["actual"] != g["close"]]
        wins = sum((g["model"] > g["close"]) == (g["actual"] > g["close"]) for g in picks)
        bets[gap] = (wins, len(picks))
    by_season = {}
    for s in years:
        gs = [g for g in out if g["season"] == s]
        if gs:
            picks = [g for g in gs if abs(g["model"] - g["close"]) >= 2.5 and g["actual"] != g["close"]]
            by_season[s] = (len(gs), sum(abs(g["close"] - g["actual"]) for g in gs) / len(gs), sum(abs(g["model"] - g["actual"]) for g in gs) / len(gs),
                            sum((g["model"] > g["close"]) == (g["actual"] > g["close"]) for g in picks), len(picks))
    return {"games": n, "mae_close": mae(lambda g: g["close"]), "mae_model": mae(lambda g: g["model"]),
            "mae_blend": mae(lambda g: best_w * g["close"] + (1 - best_w) * g["model"]), "best_market_weight": best_w,
            "mse_market_only": grid[1.0], "mse_best": best, "bets": bets, "by_season": by_season,
            "avg_model_minus_close": sum(g["model"] - g["close"] for g in out) / n}
