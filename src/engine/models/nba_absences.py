"""NBA: does the closing spread already carry who is missing? (plan, NBA step 2; docs/research/13-nba-absences.md)

For every stored game (ESPN box scores with the closing spread), find the team's regulars who did not play: players who averaged 15+ minutes
over the team's last ten games they played in and appeared in one of its last three (a long-term absence is already in the rating; a fresh one
is the news). Measure how far the result landed from the closing spread against the minutes those absences remove.

  y = home margin + closing home spread   (positive: home beat the close)
  x = (minutes lost by the away team - minutes lost by the home team) / 10

A coefficient near zero means the close prices absences (the expected answer). A positive one means the healthier side beat the close on
average. IMPORTANT: absences come from the final box score, so they include players scratched AFTER the close. A positive coefficient is
therefore a mix of late news (not tradeable) and under-pricing (tradeable); this test cannot separate them. What it can say is how big the
whole effect is and whether it is stable, walk-forward by season. It does not say how much Pinnacle moves when news breaks: that needs our own
minute-level logs, which began on Nov 21 (the injury watcher and the fast reads).
"""
from __future__ import annotations

import math
from collections import defaultdict, deque

REG_MIN = 15.0
STAR_MIN = 28.0


def game_features(games: list[dict]) -> list[dict]:
    """One row per game with a closing spread, oldest first. Uses only games before it to decide who counts as a regular."""
    hist: dict[str, deque] = defaultdict(lambda: deque(maxlen=10))      # team -> recent games: {player id: minutes}
    rows = []
    for g in games:
        by_team = {g["home"]: {}, g["away"]: {}}
        for p in g["players"]:
            if p["team"] in by_team:
                by_team[p["team"]][p["id"]] = p.get("min", 0.0) or 0.0
        if g.get("home_spread") is None or any(len(v) == 0 for v in by_team.values()):
            continue
        h = sum(p.get("pts", 0) for p in g["players"] if p["team"] == g["home"])
        a = sum(p.get("pts", 0) for p in g["players"] if p["team"] == g["away"])
        if h + a < 150:
            continue
        lost, stars = {}, {}
        for team, played in by_team.items():
            past = list(hist[team])
            lost[team] = stars[team] = 0.0
            if len(past) >= 5:
                avg = defaultdict(list)
                for gm in past:
                    for pid, m in gm.items():
                        if m > 0:
                            avg[pid].append(m)
                recent = {pid for gm in past[-3:] for pid, m in gm.items() if m > 0}
                for pid, ms in avg.items():
                    mean = sum(ms) / len(ms)
                    if mean >= REG_MIN and pid in recent and played.get(pid, 0.0) == 0.0:
                        lost[team] += mean
                        stars[team] += mean >= STAR_MIN
            hist[team].append(by_team[team])
        rows.append({"season": g["season"], "y": (h - a) + float(g["home_spread"]),
                     "x": (lost[g["away"]] - lost[g["home"]]) / 10, "stars": stars[g["away"]] - stars[g["home"]],
                     "lost_home": lost[g["home"]], "lost_away": lost[g["away"]]})
    return rows


def fit(rows: list[dict]) -> tuple[float, float, int]:
    """(slope, standard error, n) of y on x through the origin."""
    sxx = sum(r["x"] ** 2 for r in rows)
    if not rows or sxx == 0:
        return 0.0, 0.0, len(rows)
    b = sum(r["x"] * r["y"] for r in rows) / sxx
    resid = [r["y"] - b * r["x"] for r in rows]
    se = math.sqrt(sum(e * e for e in resid) / max(len(rows) - 1, 1) / sxx)
    return b, se, len(rows)


def walk_forward(rows: list[dict]) -> list[dict]:
    seasons = sorted({r["season"] for r in rows})
    out = []
    for s in seasons[1:]:
        train = [r for r in rows if r["season"] < s]
        test = [r for r in rows if r["season"] == s]
        if len(train) < 300 or not test:
            continue
        b, _, _ = fit(train)
        mse0 = sum(r["y"] ** 2 for r in test) / len(test)
        mse1 = sum((r["y"] - b * r["x"]) ** 2 for r in test) / len(test)
        big = [r for r in test if abs(r["x"]) >= 2.0]          # 20+ minutes of difference in who is out
        healthier_covers = sum(1 for r in big if r["x"] * r["y"] > 0)
        decided = sum(1 for r in big if r["y"] != 0)
        out.append({"season": s, "n": len(test), "b_train": b, "mse_close": mse0, "mse_adjusted": mse1,
                    "big": len(big), "healthier_covers": healthier_covers, "decided": decided})
    return out


def report(games: list[dict]) -> str:
    from datetime import datetime
    rows = game_features(games)
    b, se, n = fit(rows)
    wf = walk_forward(rows)
    stars = [r for r in rows if r["stars"] != 0]
    sb = sum(r["y"] * (1 if r["stars"] > 0 else -1) for r in stars) / len(stars) if stars else 0.0
    out = ["# 13. NBA: does the closing spread already carry who is missing?", "",
           f"Generated {datetime.now():%Y-%m-%d}. {n} games with a closing spread (seasons {sorted({r['season'] for r in rows})}). Method and its main limit are in "
           "`src/engine/models/nba_absences.py`: absences come from the final box score, so they include scratches made after the close.", "",
           "## Result", "",
           f"- Across all games, each extra 10 minutes of regulars missing from one side moved the result **{b:+.2f} points** against that side relative to the closing spread "
           f"(standard error {se:.2f}, t = {b / se if se else 0:+.1f}).",
           f"- When one side was missing a 28+ minute player and the other was not ({len(stars)} games), the healthier side beat the close by {sb:+.2f} points on average.", "",
           "| Test season | Games | Slope fitted on earlier seasons | Error vs the close | Error after adjusting | Games with 20+ minutes difference | Healthier side covered |",
           "|---|---|---|---|---|---|---|"]
    for w in wf:
        cov = f"{w['healthier_covers']} of {w['decided']}" if w["decided"] else "n/a"
        out.append(f"| {w['season']} | {w['n']} | {w['b_train']:+.2f} | {w['mse_close']:.1f} | {w['mse_adjusted']:.1f} | {w['big']} | {cov} |")
    out += ["", "## How to read it", "",
            "- A slope near zero, and no improvement in error after adjusting, means the closing spread already carries absences: nothing to find at the close.",
            "- A positive slope with a stable sign across seasons means the healthier side beats the close on average. That is partly late scratches (news after the close), which "
            "cannot be traded, and possibly under-pricing, which can. This test cannot split them.",
            "- It says nothing about how fast Pinnacle moves when news breaks, or whether Wagerhouse trails it. That is measured from our own logs (`engine wh-edge`, the injury watcher), "
            "which began Nov 21; too few events exist yet.", ""]
    return "\n".join(out)
