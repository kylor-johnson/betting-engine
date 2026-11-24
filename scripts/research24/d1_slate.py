"""Research 24, Job 4 / test D1: what a paper lane of our NFL script's first halves and team totals against Pinnacle's derivative lines
would show on this week's slate (games Nov 25 to Dec 1, 2026). Read-only. Rule frozen in commit fccd765:
  first-half total = 1.89 + 0.47 x our total; first-half margin = 0.48 + 0.62 x our margin (research 04, test E);
  team totals = our blended team points; "ours" = the playbook blend (side 0.25, total 0.35, team total 0.4 on our own number).
Win chance from a bell curve whose width is the spread of first-half results around that rule applied to the closing line, 2022-2025
(nflverse play-by-play; games before the test), and 9.0 for game team totals (playbook team_total_sd). Pick = 4% of win chance over the
chance Pinnacle's own price needs.

uv run python scripts/research24/d1_slate.py
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from statistics import NormalDist, pstdev

from engine.models import first_half
from engine.odds.math import american_to_decimal
from engine.odds.snapshots import connect

DB = Path(__file__).resolve().parents[2] / "data.nosync" / "engine.duckdb"
W = {"side": 0.25, "total": 0.35, "team_total": 0.4}


def widths() -> tuple[float, float]:
    gs = [g for g in first_half.games(2022, 2025)]
    m = [(g["h1_home"] - g["h1_away"]) - (0.48 + 0.62 * g["spread"]) for g in gs]
    t = [(g["h1_home"] + g["h1_away"]) - (1.89 + 0.47 * g["total"]) for g in gs]
    return pstdev(m), pstdev(t)


def need(price: float) -> float:
    return 1 / american_to_decimal(price)


def chance_over(mean: float, line: float, sd: float) -> float:
    """P(result > line), with a whole-number line's push shared out (no push on a half point)."""
    if line == int(line):
        lo, hi = NormalDist(mean, sd).cdf(line - 0.5), NormalDist(mean, sd).cdf(line + 0.5)
        win, lose = 1 - hi, lo
        return win / (win + lose)
    return 1 - NormalDist(mean, sd).cdf(line)


def main() -> None:
    sd_m, sd_t = widths()
    print(f"First-half widths from 2022-2025 closing lines: margin {sd_m:.2f}, total {sd_t:.2f} (games: {len(first_half.games(2022, 2025))})")
    con = connect(DB, read_only=True)
    lo, hi = datetime(2026, 11, 25, 12), datetime(2026, 12, 2, 12)
    cands = con.execute("""SELECT game, market, side, own_value, market_value, kickoff_utc FROM (
                             SELECT *, row_number() OVER (PARTITION BY game, market, side ORDER BY first_seen_utc DESC) rn
                             FROM playbook_candidates WHERE sport='NFL' AND kickoff_utc BETWEEN ? AND ?) WHERE rn = 1""", [lo, hi]).fetchall()
    ours: dict[str, dict] = {}
    for game, market, side, own, mkt, kick in cands:
        if own is None or mkt is None:
            continue
        g = ours.setdefault(game, {"kick": kick})
        val = W[market] * own + (1 - W[market]) * mkt if market in W else None
        if market in ("side", "total"):
            g[market] = val
        elif market == "team_total":
            g["tt_" + side.split("_")[0]] = val
    derivs = con.execute("""SELECT away, home, market, period, description, line, price_a, price_b FROM (
                              SELECT *, row_number() OVER (PARTITION BY away, home, market, period, description ORDER BY ts_utc DESC) rn
                              FROM derivative_snapshots WHERE sport='NFL' AND source='Pinnacle' AND start_utc BETWEEN ? AND ?)
                            WHERE rn = 1 AND ((market IN ('spread', 'total') AND period = '1st Half') OR (market = 'team_total' AND period = 'Game'))""",
                         [lo.isoformat(), hi.isoformat()]).fetchall()
    picks, rows = [], []
    for away, home, market, period, desc, line, pa, pb in derivs:
        g = ours.get(f"{away} at {home}")
        if not g:
            continue
        if market == "spread" and "side" in g:
            mean = 0.48 + 0.62 * g["side"]                       # home first-half margin
            p_home = chance_over(mean, -line, sd_m)              # home covers when margin > -line
            opts = [(f"{home} 1H {line:+g}", p_home, pa), (f"{away} 1H {-line:+g}", 1 - p_home, pb)]
            ref = f"our 1H margin {mean:+.1f} (home)"
        elif market == "total" and "total" in g:
            mean = 1.89 + 0.47 * g["total"]
            p = chance_over(mean, line, sd_t)
            opts = [(f"1H Over {line:g}", p, pa), (f"1H Under {line:g}", 1 - p, pb)]
            ref = f"our 1H total {mean:.1f}"
        elif market == "team_total" and f"tt_{desc}" in g:
            mean = g[f"tt_{desc}"]
            team = home if desc == "home" else away
            p = chance_over(mean, line, 9.0)
            opts = [(f"{team} team total Over {line:g}", p, pa), (f"{team} team total Under {line:g}", 1 - p, pb)]
            ref = f"our {team} points {mean:.1f}"
        else:
            continue
        for name, p, price in opts:
            e = p - need(price)
            rows.append((e, f"{away} at {home}", name, price, ref))
            if e >= 0.04:
                picks.append((e, f"{away} at {home}", name, price, ref))
    print(f"\n{len(rows)} priced options on {len(ours)} games; paper picks at 4%+: {len(picks)}")
    for e, game, name, price, ref in sorted(picks, reverse=True):
        print(f"  {name} ({int(price):+d}), {game}: edge {100 * e:+.1f}% ({ref})")
    print("\nTop five under the bar:")
    for e, game, name, price, ref in sorted([r for r in rows if r[0] < 0.04], reverse=True)[:5]:
        print(f"  {name} ({int(price):+d}), {game}: edge {100 * e:+.1f}% ({ref})")


if __name__ == "__main__":
    main()
