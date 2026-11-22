"""NFL matchup numbers from play-by-play: the handicapping layer.

Per team, on offense and defense: efficiency (EPA per play, success rate, by
pass and rush), situational results (third down, red zone), drive results,
play volume, pass rate over expected, first-quarter and first-half scoring,
the strength of the opposing units faced, and how all of it has changed over
the last four games. Also an opponent-adjusted power number built only from
play-by-play, so the engine has a number of its own that is not the market's.
"""
from __future__ import annotations

from datetime import datetime

import duckdb

from engine.odds.espn import SourceError
from engine.picks.totals import pbp_file

RECENT = 4          # games in the "recent" window
PLAYS_PER_TEAM = 62.0


def game_rows(years: list[int], current_year: int) -> list[dict]:
    """One row per team per game (that team's offense against that opponent's defense)."""
    files = [str(pbp_file(y, y == current_year)) for y in years]
    con = duckdb.connect()
    q = f"""
    WITH p AS (
      SELECT * FROM read_parquet({files!r}, union_by_name=true) WHERE season_type = 'REG'
    ), o AS (
      SELECT game_id, season, week, posteam AS team, defteam AS opp, (posteam = home_team) AS is_home,
        count(*) FILTER (WHERE play_type IN ('pass','run')) AS plays,
        coalesce(sum(epa) FILTER (WHERE play_type IN ('pass','run')), 0) AS epa,
        coalesce(sum(success) FILTER (WHERE play_type IN ('pass','run')), 0) AS succ,
        count(*) FILTER (WHERE pass = 1 AND play_type IN ('pass','run')) AS dropbacks,
        coalesce(sum(epa) FILTER (WHERE pass = 1 AND play_type IN ('pass','run')), 0) AS db_epa,
        coalesce(sum(success) FILTER (WHERE pass = 1 AND play_type IN ('pass','run')), 0) AS db_succ,
        count(*) FILTER (WHERE rush = 1 AND play_type IN ('pass','run')) AS rushes,
        coalesce(sum(epa) FILTER (WHERE rush = 1 AND play_type IN ('pass','run')), 0) AS ru_epa,
        coalesce(sum(success) FILTER (WHERE rush = 1 AND play_type IN ('pass','run')), 0) AS ru_succ,
        count(*) FILTER (WHERE down IN (1,2) AND play_type IN ('pass','run')) AS early,
        coalesce(sum(success) FILTER (WHERE down IN (1,2) AND play_type IN ('pass','run')), 0) AS early_succ,
        count(*) FILTER (WHERE down = 3 AND play_type IN ('pass','run')) AS third,
        coalesce(sum(CASE WHEN first_down = 1 OR touchdown = 1 THEN 1 ELSE 0 END) FILTER (WHERE down = 3 AND play_type IN ('pass','run')), 0) AS third_conv,
        coalesce(sum(pass_oe) FILTER (WHERE pass_oe IS NOT NULL), 0) AS proe_sum,
        count(*) FILTER (WHERE pass_oe IS NOT NULL) AS proe_n,
        coalesce(sum(yards_gained) FILTER (WHERE play_type IN ('pass','run')), 0) AS yards,
        count(*) FILTER (WHERE touchdown = 1 AND td_team = posteam AND qtr <= 2) AS h1_tds
      FROM p WHERE posteam IS NOT NULL GROUP BY ALL
    ), d0 AS (
      SELECT game_id, posteam AS team, fixed_drive, max(fixed_drive_result) AS res,
             count(*) FILTER (WHERE play_type IN ('pass','run')) AS n, min(yardline_100) AS closest
      FROM p WHERE posteam IS NOT NULL AND fixed_drive IS NOT NULL GROUP BY ALL
    ), d AS (
      SELECT game_id, team,
        count(*) FILTER (WHERE NOT (res = 'End of half' AND n <= 3)) AS drives,
        count(*) FILTER (WHERE res = 'Touchdown') AS td_drives,
        count(*) FILTER (WHERE res IN ('Touchdown','Field goal')) AS score_drives,
        count(*) FILTER (WHERE res = 'Punt') AS punts,
        count(*) FILTER (WHERE res = 'Punt' AND n <= 3) AS three_outs,
        sum(CASE res WHEN 'Touchdown' THEN 7 WHEN 'Field goal' THEN 3 ELSE 0 END) AS drive_pts,
        count(*) FILTER (WHERE closest <= 20) AS rz, count(*) FILTER (WHERE closest <= 20 AND res = 'Touchdown') AS rz_td,
        min_by(res, fixed_drive) AS first_drive
      FROM d0 GROUP BY ALL
    ), q AS (
      SELECT game_id, home_team, away_team,
        coalesce(max(total_home_score) FILTER (WHERE qtr = 1), 0) AS h_q1, coalesce(max(total_away_score) FILTER (WHERE qtr = 1), 0) AS a_q1,
        coalesce(max(total_home_score) FILTER (WHERE qtr <= 2), 0) AS h_h1, coalesce(max(total_away_score) FILTER (WHERE qtr <= 2), 0) AS a_h1,
        max(total_home_score) AS h_fin, max(total_away_score) AS a_fin
      FROM p GROUP BY ALL
    )
    SELECT o.*, d.drives, d.td_drives, d.score_drives, d.punts, d.three_outs, d.drive_pts, d.rz, d.rz_td, d.first_drive,
      CASE WHEN o.is_home THEN q.h_q1 ELSE q.a_q1 END AS q1_for, CASE WHEN o.is_home THEN q.a_q1 ELSE q.h_q1 END AS q1_against,
      CASE WHEN o.is_home THEN q.h_h1 ELSE q.a_h1 END AS h1_for, CASE WHEN o.is_home THEN q.a_h1 ELSE q.h_h1 END AS h1_against,
      CASE WHEN o.is_home THEN q.h_fin ELSE q.a_fin END AS pts_for, CASE WHEN o.is_home THEN q.a_fin ELSE q.h_fin END AS pts_against
    FROM o JOIN d USING (game_id, team) JOIN q USING (game_id) ORDER BY o.season, o.week"""
    cur = con.execute(q)
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    con.close()
    if not rows:
        raise SourceError("no play-by-play rows came back for the matchup numbers")
    return rows


# (name, numerator, denominator, higher is better for the offense)
RATES = [
    ("epa_per_play", "epa", "plays", True), ("success_rate", "succ", "plays", True),
    ("epa_per_dropback", "db_epa", "dropbacks", True), ("pass_success_rate", "db_succ", "dropbacks", True),
    ("epa_per_rush", "ru_epa", "rushes", True), ("rush_success_rate", "ru_succ", "rushes", True),
    ("early_down_success_rate", "early_succ", "early", True), ("third_down_rate", "third_conv", "third", True),
    ("points_per_drive", "drive_pts", "drives", True), ("td_per_drive", "td_drives", "drives", True),
    ("scoring_drive_rate", "score_drives", "drives", True), ("punt_rate", "punts", "drives", False),
    ("three_and_out_rate", "three_outs", "drives", False), ("yards_per_drive", "yards", "drives", True),
    ("red_zone_td_rate", "rz_td", "rz", True), ("pass_rate_over_expected", "proe_sum", "proe_n", None),
]


def _unit(rows: list[dict]) -> dict:
    out = {"games": len(rows)}
    for name, num, den, _ in RATES:
        d = sum(r[den] for r in rows)
        out[name] = (sum(r[num] for r in rows) / d) if d else None
    g = len(rows) or 1
    out["plays_per_game"] = sum(r["plays"] for r in rows) / g
    out["points_per_game"] = sum(r["pts_for"] for r in rows) / g
    out["first_quarter_points_per_game"] = sum(r["q1_for"] for r in rows) / g
    out["first_half_points_per_game"] = sum(r["h1_for"] for r in rows) / g
    out["games_with_2plus_first_half_tds"] = sum(r["h1_tds"] >= 2 for r in rows)
    out["first_drive_punts"] = sum(r["first_drive"] == "Punt" for r in rows)
    return out


def _rank(values: dict[str, float | None], best_high: bool) -> dict[str, int]:
    have = sorted((t for t, v in values.items() if v is not None), key=lambda t: values[t], reverse=best_high)
    return {t: i + 1 for i, t in enumerate(have)}


def build(rows: list[dict]) -> dict:
    """Per team: offense and defense over the season, the last RECENT games and the games before those,
    each number with its league rank, plus the strength of the units faced."""
    teams = sorted({r["team"] for r in rows})
    off = {t: sorted((r for r in rows if r["team"] == t), key=lambda r: r["week"]) for t in teams}
    dfn = {t: sorted((r for r in rows if r["opp"] == t), key=lambda r: r["week"]) for t in teams}
    windows = {"season": lambda g: g, "recent": lambda g: g[-RECENT:], "earlier": lambda g: g[:-RECENT]}
    raw = {w: {"off": {t: _unit(f(off[t])) for t in teams}, "def": {t: _unit(f(dfn[t])) for t in teams}} for w, f in windows.items()}
    ranked: dict = {t: {"off": {}, "def": {}} for t in teams}
    extras = [("plays_per_game", None), ("points_per_game", True), ("first_quarter_points_per_game", True), ("first_half_points_per_game", True)]
    for w in windows:
        for side in ("off", "def"):
            for name, _, _, hib in RATES + [(n, None, None, h) for n, h in extras]:
                vals = {t: raw[w][side][t].get(name) for t in teams}
                best_high = True if hib is None else (hib if side == "off" else not hib)
                rk = _rank(vals, best_high)
                for t in teams:
                    v = vals[t]
                    ranked[t][side].setdefault(w, {"games": raw[w][side][t]["games"]})[name] = None if v is None else {"value": round(v, 3), "rank": rk.get(t)}
            for t in teams:
                for k in ("games_with_2plus_first_half_tds", "first_drive_punts"):
                    ranked[t][side][w][k] = raw[w][side][t][k]
    # strength of the units faced: season-long EPA per play of the opposing unit, averaged over opponents
    def_epa = {t: raw["season"]["def"][t]["epa_per_play"] for t in teams}
    off_epa = {t: raw["season"]["off"][t]["epa_per_play"] for t in teams}
    for w, f in windows.items():
        faced_d = {t: (sum(def_epa[r["opp"]] for r in f(off[t])) / len(f(off[t]))) if f(off[t]) else None for t in teams}
        faced_o = {t: (sum(off_epa[r["team"]] for r in f(dfn[t])) / len(f(dfn[t]))) if f(dfn[t]) else None for t in teams}
        rd, ro = _rank(faced_d, False), _rank(faced_o, True)      # rank 1 = toughest schedule faced
        for t in teams:
            ranked[t]["off"][w]["defenses_faced_toughness_rank"] = rd.get(t)
            ranked[t]["def"][w]["offenses_faced_toughness_rank"] = ro.get(t)
    for t in teams:
        ranked[t]["results"] = [{"week": r["week"], "opp": r["opp"], "home": bool(r["is_home"]), "score": f"{r['pts_for']}-{r['pts_against']}",
                                 "first_quarter": f"{r['q1_for']}-{r['q1_against']}", "first_half": f"{r['h1_for']}-{r['h1_against']}",
                                 "first_drive": r["first_drive"]} for r in off[t]]
    return ranked


def power(rows: list[dict], decay: float = 0.93, shrink_games: float = 3.0, iters: int = 12) -> dict[str, tuple[float, float]]:
    """Opponent-adjusted EPA per play, recent games weighted more. Returns team -> (offense, defense),
    both relative to league average; a positive defense number means it allows more than average."""
    teams = sorted({r["team"] for r in rows})
    lg = sum(r["epa"] for r in rows) / sum(r["plays"] for r in rows)
    by_off = {t: sorted((r for r in rows if r["team"] == t), key=lambda r: r["week"]) for t in teams}
    by_def = {t: sorted((r for r in rows if r["opp"] == t), key=lambda r: r["week"]) for t in teams}
    o = {t: 0.0 for t in teams}
    d = {t: 0.0 for t in teams}
    for _ in range(iters):
        no, nd = {}, {}
        for t in teams:
            g = by_off[t]
            w = [decay ** (len(g) - 1 - i) for i in range(len(g))]
            no[t] = sum(wi * (r["epa"] / max(r["plays"], 1) - lg - d[r["opp"]]) for wi, r in zip(w, g)) / (sum(w) + shrink_games) if g else 0.0
            g = by_def[t]
            w = [decay ** (len(g) - 1 - i) for i in range(len(g))]
            nd[t] = sum(wi * (r["epa"] / max(r["plays"], 1) - lg - o[r["team"]]) for wi, r in zip(w, g)) / (sum(w) + shrink_games) if g else 0.0
        o, d = no, nd
    return {t: (o[t], d[t]) for t in teams}


def power_margin(pw: dict, home: str, away: str, hfa: float) -> float | None:
    if home not in pw or away not in pw:
        return None
    (oh, dh), (oa, da) = pw[home], pw[away]
    return PLAYS_PER_TEAM * ((oh + da) - (oa + dh)) + hfa


def spread_backtest(years: list[int], current_year: int, closes: dict[str, tuple[float, float]], hfa: float, first_week: int = 5) -> dict:
    """Walk forward. closes: game_id -> (closing expected home margin, actual home margin)."""
    rows = game_rows(years, current_year)
    out = []
    for season in years:
        srows = [r for r in rows if r["season"] == season]
        for week in sorted({r["week"] for r in srows}):
            if week < first_week:
                continue
            prior = [r for r in srows if r["week"] < week]
            if len(prior) < 60:
                continue
            pw = power(prior)
            for gid in {r["game_id"] for r in srows if r["week"] == week}:
                if gid not in closes:
                    continue
                away, home = gid.split("_")[2], gid.split("_")[3]
                m = power_margin(pw, home, away, hfa)
                if m is not None:
                    out.append({"season": season, "model": m, "close": closes[gid][0], "actual": closes[gid][1]})
    n = len(out)
    if n < 100:
        raise ValueError(f"only {n} games in the backtest")
    mse = lambda S, w: sum((w * g["close"] + (1 - w) * g["model"] - g["actual"]) ** 2 for g in S) / len(S)
    train, test = [g for g in out if g["season"] <= years[-3]], [g for g in out if g["season"] > years[-3]]
    w_all = min((i / 20 for i in range(21)), key=lambda w: mse(out, w))
    w_train = min((i / 20 for i in range(21)), key=lambda w: mse(train, w))
    def ats(S, gap):
        picks = [g for g in S if abs(g["model"] - g["close"]) >= gap and g["actual"] != g["close"]]
        return sum((g["model"] > g["close"]) == (g["actual"] > g["close"]) for g in picks), len(picks)
    return {"games": n, "mae_close": sum(abs(g["close"] - g["actual"]) for g in out) / n,
            "mae_model": sum(abs(g["model"] - g["actual"]) for g in out) / n, "best_market_weight_all": w_all,
            "best_market_weight_train": w_train, "heldout_games": len(test), "heldout_mse_market": mse(test, 1.0),
            "heldout_mse_blend": mse(test, w_train), "ats": {gap: ats(out, gap) for gap in (1.5, 2.5, 4.0)},
            "ats_heldout": {gap: ats(test, gap) for gap in (1.5, 2.5, 4.0)}}


def current(now: datetime) -> tuple[dict, dict]:
    """(matchup numbers per team, power number per team) for this season so far."""
    year = now.year if now.month >= 8 else now.year - 1
    rows = [r for r in game_rows([year], year) if r["season"] == year]
    return build(rows), power(rows)


BRIEF = ("epa_per_play", "success_rate", "epa_per_dropback", "epa_per_rush", "early_down_success_rate", "third_down_rate",
         "points_per_drive", "td_per_drive", "punt_rate", "three_and_out_rate", "red_zone_td_rate", "pass_rate_over_expected",
         "plays_per_game", "first_quarter_points_per_game", "first_half_points_per_game")


def brief(team: dict | None) -> dict | None:
    """The slate-sheet version: season and recent numbers as 'value (rank)' strings, plus schedule and results."""
    if team is None:
        return None
    out = {}
    for side, faced in (("off", "defenses_faced_toughness_rank"), ("def", "offenses_faced_toughness_rank")):
        for w in ("season", "recent", "earlier"):
            u = team[side][w]
            d = {"games": u["games"], faced: u.get(faced)}
            for k in BRIEF:
                v = u.get(k)
                if v:
                    d[k] = f"{v['value']} (#{v['rank']})"
            if w == "season":
                d["games_with_2plus_first_half_tds"] = u["games_with_2plus_first_half_tds"]
                d["first_drive_punts"] = u["first_drive_punts"]
            out[f"{'offense' if side == 'off' else 'defense'}_{w}"] = d
    out["results"] = team["results"]
    return out


def sheet(mu: dict, a: str, b: str) -> str:
    """A readable side-by-side for two teams (a's offense vs b's defense, and the reverse)."""
    lines = []
    for off, dfn in ((a, b), (b, a)):
        lines.append(f"\n{off} offense  vs  {dfn} defense   (value, league rank; season / last {RECENT})")
        o, d = mu[off]["off"], mu[dfn]["def"]
        for k in BRIEF:
            f = lambda u: "   n/a   " if not u.get(k) else f"{u[k]['value']:>7} #{u[k]['rank']:<2}"
            lines.append(f"  {k:<30} {f(o['season'])} / {f(o['recent'])}      allowed {f(d['season'])} / {f(d['recent'])}")
        lines.append(f"  {'schedule faced (1 = toughest)':<30} defenses #{o['season']['defenses_faced_toughness_rank']} / #{o['recent']['defenses_faced_toughness_rank']}"
                     f"              offenses #{d['season']['offenses_faced_toughness_rank']} / #{d['recent']['offenses_faced_toughness_rank']}")
    for t in (a, b):
        lines.append(f"\n{t} results: " + "; ".join(f"wk{r['week']} {'vs' if r['home'] else 'at'} {r['opp']} {r['score']} (1Q {r['first_quarter']}, 1H {r['first_half']}, first drive {r['first_drive']})" for r in mu[t]["results"]))
    return "\n".join(lines)
