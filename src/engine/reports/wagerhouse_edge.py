"""Where is Wagerhouse soft against Pinnacle, and how fast does it follow? (plan items 2 and 3)

Two questions, answered from our own line logger, no model involved:

1. PRICE. At each hourly read, for every market Wagerhouse and Pinnacle both post (full game, first half, first quarter, team totals), how far is
   Wagerhouse's number from Pinnacle's, what does Wagerhouse charge in juice compared with Pinnacle, and what would the better side be worth at
   Wagerhouse's price if Pinnacle's no-vig price is the truth? Then, for games that have kicked off: how did Wagerhouse's number compare with
   Pinnacle's last line before kickoff (closing-line value, in points)?
2. SPEED. Each time Pinnacle's line moved between two reads, how long until Wagerhouse showed the same number?

Limits, stated on every report:
 * Hourly reads only show speed to the hour. Inside the fast-read windows (every ten minutes, `engine burst`) section 4 times moves to the
   minute and judges the speed idea against the keep/kill rule approved 2026-11-23.
 * "Worth" turns points into probability with a normal curve whose spread scales with the part of the game (an approximation; real NFL key
   numbers and real half and quarter distributions are not modelled). The points and the juice are measured, not assumed; only the
   conversion between them is an approximation.
 * Reads of the same game are not independent. Counts of games are shown next to counts of reads.
 * Nothing here is a pick. It points the research at the markets where the book looks softest.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean, median

from engine.odds.math import american_to_decimal, implied_prob, no_vig

NORMAL_PEAK = 0.3989
PERIOD_FRACTION = {"Game": 1.0, "1st Half": 0.5, "1st Quarter": 0.25}
MIN_VALUE = 0.02          # the engine's own bar for a Bet (config picks.min_value)
CLOSE_WITHIN = timedelta(minutes=95)       # a "closing" Pinnacle read must be this near kickoff
READ_BEFORE = timedelta(minutes=30)        # only reads at least this long before kickoff count for closing-line value
MATCH = 0.25              # lines this close count as the same number


def slope(sd: dict, market: str, period: str) -> float:
    """Probability per point near the line (normal curve; spread scales with the square root of the share of the game)."""
    f = PERIOD_FRACTION[period]
    if market == "spread":
        base = sd["spread"]
    elif market == "total":
        base = sd["total"]
    else:                                      # one team's score: about the game total's spread divided by 1.4
        base = sd["total"] / 1.4
    return NORMAL_PEAK / (base * math.sqrt(f))


def hold(price_a: float, price_b: float) -> float:
    return implied_prob(price_a) + implied_prob(price_b) - 1


def sides(market: str, w_line: float, p_line: float):
    """(name, points in this side's favour at Wagerhouse's number, index of its price) for both sides."""
    d = w_line - p_line
    if market == "spread":                     # line is the home spread: a bigger number is better for home
        return [("home", d, 0), ("away", -d, 1)]
    return [("over", -d, 0), ("under", d, 1)]  # a smaller total is better for the over


def side_value(market: str, side_i: int, adv: float, w_prices: tuple, p_prices: tuple, sl: float) -> float:
    """Expected profit per $1 at Wagerhouse's price, if Pinnacle's no-vig price is the truth at Pinnacle's number."""
    p = no_vig(*p_prices)[side_i] + sl * adv
    p = min(max(p, 0.01), 0.99)
    return p * (american_to_decimal(w_prices[side_i]) - 1) - (1 - p)


def clv_points(market: str, side: str, w_line: float, p_close: float) -> float:
    """Points better (+) or worse (-) than Pinnacle's closing number, from the side's view."""
    if market == "spread":
        return (w_line - p_close) if side == "home" else (p_close - w_line)
    return (p_close - w_line) if side == "over" else (w_line - p_close)


def lags(series: list[tuple[datetime, float, float]], min_move: float = 0.5) -> list[dict]:
    """series: (time, wagerhouse line, pinnacle line) per read, oldest first.
    For each Pinnacle move of at least `min_move` between consecutive reads, when did Wagerhouse make the same move?
    "Same move" is measured against Wagerhouse's own previous number, so a book that always sits half a point off is not counted as slow."""
    out = []
    for i in range(1, len(series)):
        t, w, p = series[i]
        dp = p - series[i - 1][2]
        if abs(dp) < min_move:
            continue
        sign = 1 if dp > 0 else -1
        need = abs(dp) - MATCH

        def moved(j: int, base: float) -> bool:
            d = series[j][1] - base
            return d * sign > 0 and abs(d) >= need

        if i >= 2 and moved(i - 1, series[i - 2][1]):
            out.append({"kind": "already there", "hours": 0.0, "move": dp})       # Wagerhouse made this move a read earlier
            continue
        base = series[i - 1][1]
        hit = next(((series[j][0] - t).total_seconds() / 3600 for j in range(i, len(series)) if moved(j, base)), None)
        if hit == 0.0:
            out.append({"kind": "same read", "hours": 0.0, "move": dp})
        else:
            out.append({"kind": "followed" if hit is not None else "not yet", "hours": hit, "move": dp})
    return out


MIN_MOVE = {"NFL": 0.5, "College": 0.5, "NBA": 1.0}     # a Pinnacle move this big counts (review 14, item 3)
STALE_MINUTES = 20        # Wagerhouse still on the old number this long after we saw Pinnacle move = actionable by hand
KEEP_SHARE, KILL_SHARE, NEED_MOVES = 0.30, 0.80, 60     # keep if 30%+ of moves stay stale 20+ minutes; kill if 80%+ caught within one fast read


def lag_minutes(series: list[tuple[datetime, float, float]], kick: datetime, now: datetime, min_move: float = 0.5) -> list[dict]:
    """Minute-level speed for full-game lines (fast reads every ten minutes plus the hourly reads).
    For each Pinnacle move: `stale_min` = minutes from the read where we first saw Pinnacle's new number until the first read where Wagerhouse
    showed the same move (0 = it already had). `gap_min` = minutes since the read before, i.e. how precisely the move is timed.
    `status`: caught (Wagerhouse moved), never (kickoff came first), open (game not started, Wagerhouse still behind)."""
    out = []
    for m, (t, w, p) in zip(lags(series, min_move), [x for i, x in enumerate(series) if i and abs(x[2] - series[i - 1][2]) >= min_move]):
        prev = max(x[0] for x in series if x[0] < t)
        gap = (t - prev).total_seconds() / 60
        if m["kind"] in ("already there", "same read"):
            out.append({"status": "caught", "stale_min": 0.0, "gap_min": gap})
        elif m["kind"] == "followed":
            out.append({"status": "caught", "stale_min": m["hours"] * 60, "gap_min": gap})
        else:
            out.append({"status": "never" if kick <= now else "open", "stale_min": ((min(kick, now) - t).total_seconds() / 60), "gap_min": gap})
    return out


def lag_verdict(rows: list[dict]) -> tuple[str, str]:
    """(word, sentence) against the rule approved 2026-11-23: keep the speed idea if, over 60+ moves, at least 30% left Wagerhouse on the old
    number for 20+ minutes; kill it if Wagerhouse matched within one fast read (10 minutes) on 80%+ of moves. Only moves timed to within
    15 minutes count (fast-read windows), since an hourly read cannot tell 5 minutes from 55."""
    timed = [r for r in rows if r["gap_min"] <= 15 and r["status"] != "open"]
    n = len(timed)
    if not n:
        return "no data", "No Pinnacle moves seen inside the fast-read windows yet."
    stale = sum(r["stale_min"] >= STALE_MINUTES for r in timed) / n
    quick = sum(r["status"] == "caught" and r["stale_min"] <= 10 for r in timed) / n
    tail = f"{n} timed moves: {100 * stale:.0f}% left Wagerhouse behind {STALE_MINUTES}+ minutes, {100 * quick:.0f}% matched within 10 minutes."
    if n < NEED_MOVES:
        return "too early", f"{tail} Need {NEED_MOVES} before deciding."
    if quick >= KILL_SHARE:
        return "kill", f"{tail} Wagerhouse keeps up: the speed idea fails its test."
    if stale >= KEEP_SHARE:
        return "keep", f"{tail} Wagerhouse lags often enough to act by hand."
    return "unclear", f"{tail} Between the keep and kill lines."


def _read(con, sql, params=()):
    return con.execute(sql, list(params)).fetchall()


def load(con) -> tuple[dict, dict]:
    """(paired, pin_lines).
    paired[(sport, game_key, market, period, description)] = {"kick": datetime, "reads": [(ts, w_line, w_prices, p_line, p_prices)]}
    pin_lines[same key] = [(ts, p_line)] every Pinnacle read, oldest first (for the close)."""
    paired: dict = {}
    pin: dict = defaultdict(list)
    # full game: pair each Wagerhouse snapshot with the Pinnacle snapshot of the same event within ten minutes
    rows = _read(con, """
        SELECT w.sport, w.event_id, w.home, w.away, w.start_utc, w.ts_utc,
               w.home_spread, w.home_spread_price, w.away_spread_price, w.total, w.over_price, w.under_price,
               p.ts_utc, p.home_spread, p.home_spread_price, p.away_spread_price, p.total, p.over_price, p.under_price
        FROM line_snapshots w JOIN line_snapshots p
          ON p.source='pinnacle' AND p.event_id=w.event_id AND abs(epoch(p.ts_utc) - epoch(w.ts_utc)) < 600
        WHERE w.source='wagerhouse' ORDER BY w.ts_utc""")
    seen = set()
    for r in rows:
        sport, eid, home, away, kick, ts = r[:6]
        if (eid, ts) in seen:
            continue
        seen.add((eid, ts))
        gk = f"{away} at {home}"
        for market, wl, wp, pl, pp in (("spread", r[6], (r[7], r[8]), r[13], (r[14], r[15])),
                                        ("total", r[9], (r[10], r[11]), r[16], (r[17], r[18]))):
            if None in (wl, pl) or None in wp or None in pp:
                continue
            k = (sport, gk, market, "Game", "")
            paired.setdefault(k, {"kick": kick, "reads": []})["reads"].append((ts, wl, wp, pl, pp))
    for sport, eid, ts, home, away, spread, total in _read(con, "SELECT sport, event_id, ts_utc, home, away, home_spread, total FROM line_snapshots WHERE source='pinnacle' ORDER BY ts_utc"):
        gk = f"{away} at {home}"
        if spread is not None:
            pin[(sport, gk, "spread", "Game", "")].append((ts, spread))
        if total is not None:
            pin[(sport, gk, "total", "Game", "")].append((ts, total))
    # periods and team totals: the same poll writes both books with the same timestamp
    rows = _read(con, """
        SELECT w.sport, w.home, w.away, w.start_utc, w.ts_utc, w.market, w.period, w.description,
               w.line, w.price_a, w.price_b, p.line, p.price_a, p.price_b
        FROM derivative_snapshots w JOIN derivative_snapshots p
          ON p.source='Pinnacle' AND p.ts_utc=w.ts_utc AND p.home=w.home AND p.away=w.away AND p.market=w.market
         AND p.period=w.period AND p.description=w.description
        WHERE w.source='Wagerhouse' AND w.market IN ('spread','total','team_total') ORDER BY w.ts_utc""")
    for sport, home, away, kick, ts, market, period, desc, wl, wa, wb, pl, pa, pb in rows:
        if None in (wl, pl, wa, wb, pa, pb):
            continue
        try:
            kk = datetime.fromisoformat(str(kick).replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            continue
        k = (sport, f"{away} at {home}", market, period, desc)
        paired.setdefault(k, {"kick": kk, "reads": []})["reads"].append((ts, wl, (wa, wb), pl, (pa, pb)))
    for sport, home, away, ts, market, period, desc, line in _read(con, "SELECT sport, home, away, ts_utc, market, period, description, line FROM derivative_snapshots WHERE source='Pinnacle' AND market IN ('spread','total','team_total') ORDER BY ts_utc"):
        if line is not None:
            pin[(sport, f"{away} at {home}", market, period, desc)].append((ts, line))
    return paired, pin


def close_line(pin_series: list, kick: datetime) -> float | None:
    before = [(t, l) for t, l in pin_series if t <= kick]
    if not before or kick - before[-1][0] > CLOSE_WITHIN:
        return None
    return before[-1][1]


def group_name(market: str, period: str) -> str:
    base = {"spread": "side", "total": "total", "team_total": "team total"}[market]
    return base if period == "Game" else f"{period.lower()} {base}"


def analyse(paired: dict, pin: dict, margin_sd: dict, now: datetime | None = None) -> dict:
    now = (now or datetime.now(timezone.utc)).replace(tzinfo=None)
    groups: dict = defaultdict(lambda: {"reads": 0, "games": set(), "gap": [], "hold_w": [], "hold_p": [], "ev": [], "flag_games": set(),
                                        "flag_reads": 0, "clv_all": [], "clv_flag": [], "clv_games": set(), "lag": [], "minutes": []})
    for (sport, gk, market, period, desc), d in paired.items():
        sl = slope(margin_sd[sport], market, period)
        g = groups[(sport, group_name(market, period))]
        close = close_line(pin.get((sport, gk, market, period, desc), []), d["kick"]) if d["kick"] <= now else None
        series = []
        for ts, wl, wp, pl, pp in d["reads"]:
            g["reads"] += 1
            g["games"].add(gk)
            g["gap"].append(abs(wl - pl))
            g["hold_w"].append(hold(*wp))
            g["hold_p"].append(hold(*pp))
            series.append((ts, wl, pl))
            best = max(((side_value(market, i, adv, wp, pp, sl), name) for name, adv, i in sides(market, wl, pl)))
            g["ev"].append(best[0])
            flagged = best[0] >= MIN_VALUE
            if flagged:
                g["flag_reads"] += 1
                g["flag_games"].add((gk, desc))
            if close is not None and ts <= d["kick"] - READ_BEFORE:
                c = clv_points(market, best[1], wl, close)
                g["clv_all"].append(c)
                g["clv_games"].add((gk, desc))
                if flagged:
                    g["clv_flag"].append(c)
        g["lag"].extend(lags(series, min_move=MIN_MOVE.get(sport, 0.5)))
        if period == "Game" and market in ("spread", "total"):
            g["minutes"].extend(lag_minutes(series, d["kick"], now, min_move=MIN_MOVE.get(sport, 0.5)))
    return groups


def pct(x, n):
    return "n/a" if not n else f"{100 * x / n:.0f}%"


def report(con, cfg: dict, now: datetime | None = None) -> str:
    paired, pin = load(con)
    groups = analyse(paired, pin, cfg["margin_sd"], now)
    reads = sum(g["reads"] for g in groups.values())
    first = con.execute("SELECT min(ts_utc), max(ts_utc) FROM derivative_snapshots").fetchone()
    out = ["# 12. Where is Wagerhouse soft against Pinnacle, and how fast does it follow?", "",
           f"Generated {datetime.now():%Y-%m-%d %H:%M}. Data: our own hourly reads from {first[0]:%b %-d} to {first[1]:%b %-d %H:%M} UTC, {reads} paired reads "
           f"across {len({k[1] for k in paired})} games. **This is a small sample; read the counts, not the averages.** Re-run with `engine wh-edge` as it grows.", "",
           "How to read it: **gap** is how far Wagerhouse's number is from Pinnacle's (points). **Juice** is the book's built-in margin on a two-way market "
           "(Pinnacle is usually 2 to 4%). **Best side worth** is the better side's expected profit per $1 at Wagerhouse's price if Pinnacle's no-vig price is the "
           "truth (the points-to-probability step is an approximation: normal curve, spread scaled to the part of the game; NFL key numbers are not modelled). "
           f"**Reads worth {MIN_VALUE:.0%}+** is how often that clears the engine's own bar. **Closing-line value** is Wagerhouse's number against Pinnacle's last "
           "line before kickoff, in points, for the best side at each read at least 30 minutes before the game (games that have started only). "
           "Reads of one game are correlated, so the number of distinct games is shown.", ""]
    out += ["## 1. Price", "",
            "| Sport | Market | Reads | Games | Mean gap (pts) | Wagerhouse juice | Pinnacle juice | Best side worth, average | Reads worth 2%+ | Games with one |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for (sport, name), g in sorted(groups.items()):
        out.append(f"| {sport} | {name} | {g['reads']} | {len(g['games'])} | {mean(g['gap']):.2f} | {100 * mean(g['hold_w']):.1f}% | {100 * mean(g['hold_p']):.1f}% | "
                   f"{100 * mean(g['ev']):+.1f}% | {pct(g['flag_reads'], g['reads'])} | {len(g['flag_games'])} |")
    out += ["", "## 2. Closing-line value of the best side at each read (games already started)", "",
            "| Sport | Market | Games | Reads | Average, all reads (pts) | Reads worth 2%+ | Average on those (pts) |", "|---|---|---|---|---|---|---|"]
    for (sport, name), g in sorted(groups.items()):
        if not g["clv_all"]:
            continue
        flag = f"{mean(g['clv_flag']):+.2f}" if g["clv_flag"] else "n/a"
        out.append(f"| {sport} | {name} | {len(g['clv_games'])} | {len(g['clv_all'])} | {mean(g['clv_all']):+.2f} | {len(g['clv_flag'])} | {flag} |")
    out += ["", "A positive average means that betting the better side at Wagerhouse's number, at the times we read, would have beaten Pinnacle's close by that many points "
            "before paying the extra juice. Zero or negative means the gap at the time of the read was not predictive of where Pinnacle ended up.", ""]
    out += ["## 3. Speed: after Pinnacle moves, how long until Wagerhouse shows the same number?", "",
            "Only moves of half a point or more between two reads. Resolution is one hour, so 'within the next read' means about an hour or less.", "",
            "| Sport | Market | Pinnacle moves seen | Wagerhouse already there | Same read | Followed within 1h | Followed in 1-3h | Followed later | Not by the last read | Median hours (followed) |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for (sport, name), g in sorted(groups.items()):
        L = g["lag"]
        if not L:
            continue
        fol = [x["hours"] for x in L if x["kind"] == "followed"]
        out.append(f"| {sport} | {name} | {len(L)} | {sum(x['kind'] == 'already there' for x in L)} | {sum(x['kind'] == 'same read' for x in L)} | "
                   f"{sum(1 for x in fol if x <= 1.2)} | {sum(1 for x in fol if 1.2 < x <= 3.2)} | {sum(1 for x in fol if x > 3.2)} | "
                   f"{sum(x['kind'] == 'not yet' for x in L)} | {median(fol):.1f} |" if fol else
                   f"| {sport} | {name} | {len(L)} | {sum(x['kind'] == 'already there' for x in L)} | {sum(x['kind'] == 'same read' for x in L)} | 0 | 0 | 0 | {sum(x['kind'] == 'not yet' for x in L)} | n/a |")
    out += ["", "## 4. Speed in minutes (full-game lines; fast reads every ten minutes)", "",
            f"A Pinnacle move counts at {MIN_MOVE['NFL']:g} point in football and {MIN_MOVE['NBA']:g} in the NBA. **Timed** moves are those seen within 15 minutes "
            "of the read before (inside a fast-read window); only they can say whether Wagerhouse was behind for minutes or for an hour. "
            f"Rule approved 2026-11-23: over {NEED_MOVES}+ timed moves, keep the speed idea if {KEEP_SHARE:.0%} or more left Wagerhouse on the old number "
            f"{STALE_MINUTES}+ minutes; kill it if {KILL_SHARE:.0%} or more were matched within 10 minutes.", "",
            "| Sport | Market | Moves | Timed | Matched within 10 min | 10-30 min | 30-60 min | Over 60 min | Never before kickoff | Still behind now | Median minutes behind (caught) | Verdict |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (sport, name), g in sorted(groups.items()):
        M = g["minutes"]
        if not M:
            continue
        T = [r for r in M if r["gap_min"] <= 15]
        c = [r["stale_min"] for r in T if r["status"] == "caught"]
        word, _ = lag_verdict(M)
        out.append(f"| {sport} | {name} | {len(M)} | {len(T)} | {sum(x <= 10 for x in c)} | {sum(10 < x <= 30 for x in c)} | {sum(30 < x <= 60 for x in c)} | "
                   f"{sum(x > 60 for x in c)} | {sum(r['status'] == 'never' for r in T)} | {sum(r['status'] == 'open' for r in T)} | "
                   f"{median(c):.0f} | {word} |" if c else
                   f"| {sport} | {name} | {len(M)} | {len(T)} | 0 | 0 | 0 | 0 | {sum(r['status'] == 'never' for r in T)} | {sum(r['status'] == 'open' for r in T)} | n/a | {word} |")
    allm = [r for g in groups.values() for r in g["minutes"]]
    out += ["", f"**All sports together:** {lag_verdict(allm)[1]}", ""]
    return "\n".join(out)
