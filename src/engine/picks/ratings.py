"""Team ratings backed out of the market's own closing lines.

Each closing spread says "home team is X points better than the road team here".
Solve for the team ratings that best reproduce those lines, counting recent
weeks more (each week back counts 10% less, Walters' slow-update idea). The
result is what the market thought of each team BEFORE this week's news.
"""
from __future__ import annotations

from collections import defaultdict


def solve(games: list[tuple[str, str, float, float]], iters: int = 400) -> dict[str, float]:
    """games: (home, away, home_margin_expected_net_of_home_field, weight). Returns ratings averaging 0."""
    teams = sorted({t for g in games for t in g[:2]})
    r = {t: 0.0 for t in teams}
    by = defaultdict(list)
    for h, a, m, w in games:
        by[h].append((a, m, w))
        by[a].append((h, -m, w))
    for _ in range(iters):
        for t in teams:
            tw = sum(w for _, _, w in by[t])
            if tw:
                r[t] = sum(w * (m + r[o]) for o, m, w in by[t]) / (tw + 0.25)   # light pull toward average
        mean = sum(r.values()) / len(r)
        r = {t: v - mean for t, v in r.items()}
    return r


def market_ratings(rows: list[dict], season: int, before_date: str, hfa: float, decay: float = 0.9):
    """Spread ratings and total tendencies from this season's closing lines before a date."""
    past = [g for g in rows if g["season"] == str(season) and g["gameday"] < before_date
            and g["spread_line"] not in ("", None) and g["total_line"] not in ("", None) and g["game_type"] == "REG"]
    if len(past) < 40:
        raise ValueError(f"only {len(past)} games with closing lines this season; too few for ratings")
    last_week = max(int(g["week"]) for g in past)
    spread_games, total_games = [], []
    for g in past:
        w = decay ** (last_week - int(g["week"]))
        home_field = 0.0 if g.get("location") == "Neutral" else hfa
        spread_games.append((g["home_team"], g["away_team"], float(g["spread_line"]) - home_field, w))
        total_games.append((g["home_team"], g["away_team"], float(g["total_line"]), w))
    spread = solve(spread_games)
    avg_total = sum(t[2] * t[3] for t in total_games) / sum(t[3] for t in total_games)
    # total tendency: each game says tend[home] + tend[away] = total - average
    tend = {t: 0.0 for t in spread}
    by = defaultdict(list)
    for h, a, tot, w in total_games:
        by[h].append((a, tot - avg_total, w))
        by[a].append((h, tot - avg_total, w))
    for _ in range(400):
        for t in tend:
            tw = sum(w for _, _, w in by[t])
            if tw:
                tend[t] = sum(w * (d - tend[o]) for o, d, w in by[t]) / (tw + 0.25)
    return spread, tend, avg_total, len(past)
