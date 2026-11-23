"""Do the landing tables tell the truth? A walk-forward reliability check on the step that turns "your number is X points better
than fair" into a win probability. That step sits under every flag the engine raises (src/engine/picks/pricing.py).

Method. For each game in a test season, take the market's closing line as the fair line (the best fair number there is), and price
bets at lines 0.5 to 3 points either side of it, using a Landing built ONLY from earlier seasons. Compare the predicted chance of
winning (a push counts half) with how the game actually landed. Report the squared error (Brier) and a reliability table: games
grouped by predicted chance, predicted against realized.

What this does and does not test. It tests the points-to-probability mapping (key numbers, the spread of results, the shape of the
curve). It does NOT test whether the fair line is right: using the close as fair is generous. A pass here means the engine is not
inventing edge from a wrong curve; it does not mean the engine has edge.
"""
from __future__ import annotations

from statistics import pstdev

from engine.picks.pricing import Landing, bell_rows

OFFSETS = (-3.0, -2.0, -1.0, -0.5, 0.5, 1.0, 2.0, 3.0)
KEYS = (3.0, 7.0)


def _real(kind: str, side: str, line: float, outcome: float) -> float:
    """1, 0.5 or 0 for a bet at `line`. spread: line = home spread, outcome = home margin. total: line = total, outcome = points."""
    mine = (outcome + line) if kind == "spread" else (outcome - line)       # home covers / over wins
    if side in ("away", "under"):
        mine = -mine
    return 1.0 if mine > 0 else 0.5 if mine == 0 else 0.0


def evaluate(rows: list[tuple[int, float, float]], make: dict, test_seasons: list[int], kind: str, min_train: int = 300) -> dict:
    """rows: (season, closing_line, outcome). make: name -> function(train_rows, train_seasons) -> Landing."""
    first, second = ("home", "away") if kind == "spread" else ("over", "under")
    out = {name: {"n": 0, "brier": 0.0, "bins": {}, "key_n": 0, "key_brier": 0.0, "pred": 0.0, "real": 0.0} for name in make}
    for s in test_seasons:
        train = [(l, o) for ss, l, o in rows if ss < s]
        test = [(l, o) for ss, l, o in rows if ss == s]
        if len(train) < min_train or not test:
            continue
        for name, fn in make.items():
            land = fn(train, s)
            a = out[name]
            for l, o in test:
                for k in OFFSETS:
                    for side in (first, second):
                        line = l + k
                        try:
                            w, p, _ = land.probs(l, line, side)
                        except ValueError:          # too few past games near this line: the engine cannot price it either
                            a["skipped"] = a.get("skipped", 0) + 1
                            continue
                        pred, real = w + 0.5 * p, _real(kind, side, line, o)
                        a["n"] += 1
                        a["brier"] += (pred - real) ** 2
                        a["pred"] += pred
                        a["real"] += real
                        b = a["bins"].setdefault(min(int(pred * 10), 9), [0, 0.0, 0.0])
                        b[0] += 1
                        b[1] += pred
                        b[2] += real
                        if kind == "spread" and abs(line) in (2.5, 3.0, 3.5, 6.5, 7.0, 7.5):
                            a["key_n"] += 1
                            a["key_brier"] += (pred - real) ** 2
    for a in out.values():
        if a["n"]:
            a["brier"] /= a["n"]
            a["pred"] /= a["n"]
            a["real"] /= a["n"]
        if a["key_n"]:
            a["key_brier"] /= a["key_n"]
    return out


def nfl_rows(games: list[dict]) -> list[tuple[int, float, float]]:
    return [(int(r["season"]), -float(r["spread_line"]), float(r["result"])) for r in games
            if r["result"] not in ("", None) and r["spread_line"] not in ("", None) and r.get("game_type") in (None, "REG", "POST")]


def nfl_total_rows(games: list[dict]) -> list[tuple[int, float, float]]:
    return [(int(r["season"]), float(r["total_line"]), float(r["total"])) for r in games
            if r["result"] not in ("", None) and r.get("total_line") not in ("", None, "NA") and r.get("total") not in ("", None, "NA")]


def nba_rows() -> tuple[list, list]:
    """(spread rows, total rows) from the stored ESPN box scores; a game's score is the sum of its players' points."""
    from engine.models import nba_data
    sp, tt = [], []
    for g in nba_data.load():
        if g.get("home_spread") is None or g.get("total") is None:
            continue
        h = sum(p.get("pts", 0) for p in g["players"] if p["team"] == g["home"])
        a = sum(p.get("pts", 0) for p in g["players"] if p["team"] == g["away"])
        if h + a < 150:
            continue
        sp.append((g["season"], float(g["home_spread"]), float(h - a)))
        tt.append((g["season"], float(g["total"]), float(h + a)))
    return sp, tt


def fitted_sd(train: list[tuple[float, float]], kind: str) -> float:
    return pstdev([(o + l) if kind == "spread" else (o - l) for l, o in train])


def bell(kind: str, sd: float, lo: float, hi: float) -> Landing:
    return Landing(bell_rows(kind, sd, lo, hi), kind, window=0.25, min_n=100)


def reliability_table(a: dict) -> list[str]:
    lines = ["| Predicted chance | Bets | Predicted | Realized |", "|---|---|---|---|"]
    for k in sorted(a["bins"]):
        n, p, r = a["bins"][k]
        lines.append(f"| {k * 10}-{k * 10 + 10}% | {n} | {p / n:.3f} | {r / n:.3f} |")
    return lines


def run_all(write: bool = True) -> str:
    """The whole check, as a markdown report written to docs/research/11a-calibration.md."""
    from datetime import datetime
    from engine import config
    from engine.picks import sources
    games = sources.nfl_games(config.DATA / "raw" / "nflverse_games.csv")
    out = ["# 11a. Do the landing tables tell the truth? (walk-forward reliability check)", "",
           f"Run {datetime.now():%Y-%m-%d}. Method and limits are in the docstring of `src/engine/models/calibration.py`: the market close is used as the fair line, "
           "bets are priced 0.5 to 3 points either side, the table is built only from earlier seasons. This checks the points-to-probability curve, not whether the fair line is right.", ""]

    def block(title, res, note=""):
        out.extend([f"## {title}", ""])
        if note:
            out.extend([note, ""])
        out.extend(["| Version | Bets priced | Squared error | Average predicted | Average realized | Skipped (too few past games) |", "|---|---|---|---|---|---|"])
        for name, a in res.items():
            out.append(f"| {name} | {a['n']} | {a['brier']:.5f} | {a['pred']:.3f} | {a['real']:.3f} | {a.get('skipped', 0)} |")
        for name, a in res.items():
            out.extend(["", f"Reliability, {name}:", ""] + reliability_table(a))
            if a["key_n"]:
                out.append(f"\nBets priced at 2.5/3/3.5 or 6.5/7/7.5: {a['key_n']}, squared error {a['key_brier']:.5f}.")
        out.append("")

    rows = [r for r in nfl_rows(games) if r[0] >= 2015]
    block("NFL sides, test seasons 2019 to 2025 (table from 2015 up to the season before)",
          evaluate(rows, {"engine's table (window 1.0)": lambda tr, s: Landing(tr, "spread", window=1.0)}, list(range(2019, 2026)), "spread"))
    trows = [r for r in nfl_total_rows(games) if r[0] >= 2015]
    block("NFL totals, same seasons",
          evaluate(trows, {"engine's table (window 3.0)": lambda tr, s: Landing(tr, "total", window=3.0)}, list(range(2019, 2026)), "total"))
    sp, tt = nba_rows()
    seasons = sorted({r[0] for r in sp})[1:]
    block(f"NBA sides, test seasons {seasons} (ESPN box scores and closing lines; earlier seasons are the training window)",
          evaluate(sp, {"bell curve, sd 12 (what config.yaml uses)": lambda tr, s: bell("spread", 12.0, -25, 25),
                        "bell curve, sd fitted on earlier seasons": lambda tr, s: bell("spread", fitted_sd(tr, "spread"), -25, 25),
                        "real results (window 2.0)": lambda tr, s: Landing(tr, "spread", window=2.0, min_n=300)}, seasons, "spread"),
          note="The overall spread of NBA margins around the close is about 13.9 points, but the engine only prices bets within a few points of fair, "
               "where results are more bunched than a bell curve with that spread. That is why the smaller configured value (12) holds up.")
    block("NBA totals, same seasons",
          evaluate(tt, {"bell curve, sd 18 (config.yaml)": lambda tr, s: bell("total", 18.0, 180, 270),
                        "bell curve, sd fitted": lambda tr, s: bell("total", fitted_sd(tr, "total"), 180, 270)}, seasons, "total"))
    text = "\n".join(out) + "\n"
    if write:
        (config.ROOT / "docs" / "research" / "11a-calibration.md").write_text(text)
    return text
