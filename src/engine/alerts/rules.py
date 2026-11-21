"""Decide what is worth an alert. Pure functions: no network, no database."""
from __future__ import annotations

from dataclasses import dataclass

from engine.odds.math import ev_per_dollar, no_vig, win_prob_shift


def fmt_line(x: float) -> str:
    return "PK" if x == 0 else f"{x:+g}"


def fmt_price(x: float | None) -> str:
    return "" if x is None else f"{int(x):+d}"


def key_between(a: float, b: float, keys) -> int | None:
    """A key number that separates two spreads on the same side of zero.

    -2.5 vs -3.5 -> 3. -3 vs -3.5 -> 3 (one of them sits on it). -4 vs -4.5 -> None.
    """
    if a == b or a * b < 0:
        return None
    lo, hi = sorted((abs(a), abs(b)))
    for k in keys:
        if lo <= k <= hi:
            return k
    return None


@dataclass
class Alert:
    key: str
    kind: str      # off-market, moving, watchlist, opener
    text: str


def value_per_dollar(points_better: float, my_price, mkt_my_price, mkt_other_price, sd: float) -> float | None:
    """Approximate value of a bet at my book against the market's vig-free price."""
    if my_price is None or not mkt_my_price or not mkt_other_price:
        return None
    p = no_vig(mkt_my_price, mkt_other_price)[0] + win_prob_shift(points_better, sd)
    return ev_per_dollar(min(max(p, 0.01), 0.99), my_price)


def off_market(wh, mkt, cfg: dict, mkt_earlier=None, wh_earlier=None) -> list[Alert]:
    """Wagerhouse against the market for one game. `wh` and `mkt` are snapshots."""
    out: list[Alert] = []
    sport = wh.sport
    th = cfg["alerts"]
    keys = cfg.get("key_numbers", {}).get(sport, [])
    sd = cfg["margin_sd"][sport]
    game = f"{wh.away} at {wh.home}"

    if wh.home_spread is not None and mkt.home_spread is not None:
        diff = wh.home_spread - mkt.home_spread     # positive: home is cheaper at Wagerhouse
        k = key_between(wh.home_spread, mkt.home_spread, keys)
        if abs(diff) >= th["spread_points"] or (k and abs(diff) >= 0.5):
            if diff > 0:
                team, mine, theirs = wh.home, wh.home_spread, mkt.home_spread
                price, mp, op = wh.home_spread_price, mkt.home_spread_price, mkt.away_spread_price
            else:
                team, mine, theirs = wh.away, -wh.home_spread, -mkt.home_spread
                price, mp, op = wh.away_spread_price, mkt.away_spread_price, mkt.home_spread_price
            val = value_per_dollar(abs(diff), price, mp, op, sd["spread"])
            if val is None or val >= th["min_value"]:
                pts = f"{abs(diff):g} point{'' if abs(diff) == 1 else 's'}"
                why = f"{pts}, across {k}" if k else pts
                stale = ""
                if mkt_earlier is not None and wh_earlier is not None and mkt_earlier.home_spread is not None:
                    moved = mkt.home_spread - mkt_earlier.home_spread
                    if abs(moved) >= 0.5 and wh.home_spread == wh_earlier.home_spread:
                        stale = (f"\nMarket moved {fmt_line(mkt_earlier.home_spread)} → {fmt_line(mkt.home_spread)} "
                                 f"(home side); Wagerhouse has not moved.")
                v = f" Approx value {100 * val:+.1f}% per $1." if val is not None else ""
                out.append(Alert(
                    f"spread|{wh.event_id}|{wh.home_spread}|{mkt.home_spread}",
                    "moving" if stale else "off-market",
                    f"{sport}: {game}\n{team} {fmt_line(mine)} ({fmt_price(price)}) at Wagerhouse. "
                    f"Market: {fmt_line(theirs)} ({fmt_price(mp)}). Better by {why}.{v}{stale}"))

    if wh.total is not None and mkt.total is not None:
        diff = wh.total - mkt.total                 # positive: under is cheaper at Wagerhouse
        if abs(diff) >= th["total_points"][sport]:
            side, price, mp, op = (("Under", wh.under_price, mkt.under_price, mkt.over_price) if diff > 0
                                   else ("Over", wh.over_price, mkt.over_price, mkt.under_price))
            val = value_per_dollar(abs(diff), price, mp, op, sd["total"])
            if val is None or val >= th["min_value"]:
                v = f" Approx value {100 * val:+.1f}% per $1." if val is not None else ""
                out.append(Alert(
                    f"total|{wh.event_id}|{wh.total}|{mkt.total}", "off-market",
                    f"{sport}: {game}\n{side} {wh.total:g} ({fmt_price(price)}) at Wagerhouse. "
                    f"Market total: {mkt.total:g}. Better by {abs(diff):g} point{'' if abs(diff) == 1 else 's'}.{v}"))
    return out


def watchlist_hits(wh, mkt, entries: list[dict]) -> list[Alert]:
    """Entries: {id, team, market ('spread'|'over'|'under'|'ml'), target, worst_price}."""
    from engine.odds.espn import norm
    out = []
    for e in entries:
        t = norm(e["team"])
        is_home, is_away = t == norm(wh.home), t == norm(wh.away)
        if not (is_home or is_away):
            continue
        m = e["market"]
        if m == "spread" and wh.home_spread is not None:
            line = wh.home_spread if is_home else -wh.home_spread
            price = wh.home_spread_price if is_home else wh.away_spread_price
            mline = None if mkt is None or mkt.home_spread is None else (mkt.home_spread if is_home else -mkt.home_spread)
            hit, shown = line >= e["target"], f"{e['team']} {fmt_line(line)}"
            leaving = mline is not None and mline < e["target"]
        elif m in ("over", "under") and wh.total is not None:
            line, price = wh.total, (wh.over_price if m == "over" else wh.under_price)
            mline = mkt.total if mkt is not None else None
            hit = line <= e["target"] if m == "over" else line >= e["target"]
            shown = f"{m.title()} {line:g} ({wh.away} at {wh.home})"
            leaving = mline is not None and (mline > e["target"] if m == "over" else mline < e["target"])
        elif m == "ml":
            price = wh.home_ml if is_home else wh.away_ml
            mprice = None if mkt is None else (mkt.home_ml if is_home else mkt.away_ml)
            if price is None:
                continue
            hit, shown, line = price >= e["target"], f"{e['team']} moneyline", price
            leaving = mprice is not None and mprice < e["target"]
            price = None
        else:
            continue
        if not hit:
            continue
        if price is not None and e.get("worst_price") is not None and price < e["worst_price"]:
            continue
        tail = " The market has already moved past your number: this may not last." if leaving else ""
        out.append(Alert(
            f"watch|{e['id']}|{wh.event_id}|{line}|{int(leaving)}", "watchlist",
            f"Watchlist: {shown} {fmt_price(price)} is available at Wagerhouse "
            f"(your number: {fmt_line(e['target']) if m in ('spread', 'ml') else format(e['target'], 'g')} or better).{tail}"))
    return out


def opener_digest(new: list, markets: dict) -> Alert | None:
    """One message listing games Wagerhouse just posted for the first time."""
    if not new:
        return None
    lines = []
    for s in sorted(new, key=lambda s: s.start):
        m = markets.get(s.event_id)
        wh_txt = f"{s.home} {fmt_line(s.home_spread)}" if s.home_spread is not None else "no spread"
        tot = f", total {s.total:g}" if s.total is not None else ""
        mk = ""
        if m is not None and m.home_spread is not None:
            mk = f" | market {fmt_line(m.home_spread)}" + (f", {m.total:g}" if m.total is not None else "")
        lines.append(f"{s.away} at {wh_txt}{tot}{mk}")
    sport = new[0].sport
    ids = ",".join(sorted(s.event_id for s in new))
    return Alert(f"opener|{sport}|{ids}", "opener",
                 f"{sport}: Wagerhouse posted {len(new)} new game{'s' if len(new) != 1 else ''}\n" + "\n".join(lines))


def missed_reads(last_ok, now, expected_gap_hours: float) -> str | None:
    """A message when the scheduled reads stopped for longer than expected."""
    if last_ok is None:
        return None
    hours = (now - last_ok).total_seconds() / 3600
    if hours > expected_gap_hours:
        return f"No line reads for {hours:.1f} hours (last good read {last_ok:%b %-d %H:%M} UTC). The Mac was probably asleep or offline."
    return None
