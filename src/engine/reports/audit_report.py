"""Write the bet audit as a plain-language markdown report."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from statistics import mean
from zoneinfo import ZoneInfo

from engine.bets.audit import Priced
from engine.bets.history import Wager, category
from engine.odds.math import breakeven_leg_rate, crosses_3_and_7, luck_range, touches_key


def money(x: float) -> str:
    return f"{'−' if x < 0 else '+'}${abs(x):,.0f}"


def pct(x: float) -> str:
    return f"{'−' if x < 0 else '+'}{abs(100 * x):.1f}%"


def _row(label: str, ws: list[Wager]) -> str:
    n = len(ws)
    won = sum(w.status == "W" for w in ws)
    lost = sum(w.status == "L" for w in ws)
    risk = sum(w.risk for w in ws if not w.free_play)
    net = sum(w.net for w in ws)
    swing = luck_range([(w.risk, w.to_win) for w in ws])
    roi = pct(net / risk) if risk else "n/a"
    return f"| {label} | {n} | {won}-{lost} | ${risk:,.0f} | {money(net)} | {roi} | ±${swing:,.0f} |"


HEAD = "| | Bets | Won-lost | Risked | Net | Return | Luck range |\n|---|---|---|---|---|---|---|"


def build(wagers: list[Wager], priced: list[Priced], figures: dict[str, float], cfg: dict, tz: str,
          title: str = "Bet audit: every graded bet, priced against the closing line") -> str:
    now = datetime.now(ZoneInfo(tz))
    out: list[str] = []
    add = out.append
    total_net = sum(w.net for w in wagers)
    fig_total = sum(figures.values())
    first = min(w.accepted for w in wagers if w.accepted).astimezone(ZoneInfo(tz))
    last = max(w.accepted for w in wagers if w.accepted).astimezone(ZoneInfo(tz))

    add(f"# {title}\n")
    add(f"Run {now:%Y-%m-%d %H:%M} Mountain. Covers bets placed {first:%b %-d} to {last:%b %-d, %Y}.\n")
    add("How to read this: \"Luck range\" is how far results swing by chance alone for someone with no edge "
        "making the same bets. A net inside the luck range says nothing about skill. The reference price is "
        "DraftKings' closing line as published by ESPN. DraftKings follows the market and is not a sharp book, "
        "so the value figures are approximate.\n")

    # bottom line
    ok_ = [p for p in priced if p.ok and p.ev is not None]
    live = [w for w in wagers if w.channel == "live"]
    cap_ = cfg["unit"] * cfg["max_units"]
    over_ = [w for w in wagers if w.risk > cap_ and not w.free_play]
    swing_all = luck_range([(w.risk, w.to_win) for w in wagers])
    add("## Bottom line\n")
    verdict = ("so the result is indistinguishable from break-even." if abs(total_net) <= swing_all
               else "and this result is outside that range.")
    add(f"- **Overall: {money(total_net)} on {len(wagers)} wagers.** Chance alone moves this set of bets by ±${swing_all:,.0f}, {verdict}")
    if ok_:
        risk_ = sum(p.wager.risk for p in ok_)
        val = sum(p.ev * p.wager.risk for p in ok_) / risk_
        beat = sum(1 for p in ok_ if (p.price_vs_close == "better") or (p.pts_vs_close or 0) > 0)
        actual_, expected_ = sum(p.wager.net for p in ok_), val * risk_
        head = "Prices: no sign of an edge yet." if val < 0 else "Prices: better than fair on average."
        luck = ("which is luck running ahead of the prices." if actual_ > expected_
                else "which is behind what the prices implied.")
        add(f"- **{head}** On {len(ok_)} straight bets that could be checked, you beat the closing number on {beat}. "
            f"Each dollar risked was worth about {pct(val)} at closing prices; a bettor with no edge sits near −4.5%. "
            f"Those bets returned {money(actual_)} against {money(expected_)} expected, {luck}")
    if live:
        add(f"- **Live in-game betting: {money(sum(w.net for w in live))}** on {len(live)} tickets.")
    add(f"- **Bets over the ${cap_} cap: {len(over_)}, net {money(sum(w.net for w in over_))}.**")
    add("")

    # reconciliation
    by_week = defaultdict(float)
    for w in wagers:
        by_week[w.week] += w.net
    bad = [k for k in figures if abs(figures[k] - round(by_week.get(k, 0), 2)) > 0.01]
    add("## Does it add up\n")
    add(f"- {len(wagers)} wagers, net {money(total_net)}. The account's own weekly figures total {money(fig_total)}.")
    add("- Every week matches the account to the cent." if not bad else f"- **Weeks that do not match the account: {sorted(bad)}**")
    fp = [w for w in wagers if w.free_play]
    if fp:
        add(f"- {len(fp)} free plays won {money(sum(w.net for w in fp))}; without them the net is {money(total_net - sum(w.net for w in fp))}.")
    add("")

    # channel
    add("## By how the bet was placed\n")
    add(HEAD)
    names = {"pregame": "Before the game, regular site", "live": "Live in-game", "builder": "Same-game builder"}
    for ch in ("pregame", "live", "builder"):
        add(_row(names[ch], [w for w in wagers if w.channel == ch]))
    add(_row("**All**", wagers))
    add("")

    # category
    add("## By bet type\n")
    add(HEAD)
    cats = defaultdict(list)
    for w in wagers:
        cats[category(w)].append(w)
    for c, ws in sorted(cats.items(), key=lambda kv: sum(w.net for w in kv[1])):
        add(_row(c, ws))
    add("")

    # price quality, straight pregame
    ok = [p for p in priced if p.ok]
    straight = [p for p in ok if p.ev is not None]
    add("## Price quality on straight bets (spread, total, moneyline; NFL, college football, NBA)\n")
    add("This is the part that answers \"do I have an edge.\" For each bet: was your number better or worse than "
        "where the market closed, and what was the bet worth at the closing price with the vig removed.\n")
    add("| | Bets | Beat the close | Same | Worse | Avg points vs close | Approx value per $1 | Expected at those prices | Actual |")
    add("|---|---|---|---|---|---|---|---|---|")

    def q_row(label, ps):
        if not ps:
            return
        def cmp(p):
            if p.leg.kind == "moneyline":
                return {"better": 1, "same": 0, "worse": -1}[p.price_vs_close]
            return (p.pts_vs_close > 0) - (p.pts_vs_close < 0)
        b = sum(cmp(p) > 0 for p in ps); s = sum(cmp(p) == 0 for p in ps); wz = sum(cmp(p) < 0 for p in ps)
        pts = [p.pts_vs_close for p in ps if p.pts_vs_close is not None]
        risk = sum(p.wager.risk for p in ps)
        exp = sum(p.ev * p.wager.risk for p in ps)
        act = sum(p.wager.net for p in ps)
        avg_pts = f"{mean(pts):+.2f}" if pts else "n/a"
        add(f"| {label} | {len(ps)} | {b} | {s} | {wz} | {avg_pts} | {pct(exp / risk)} | {money(exp)} | {money(act)} |")

    q_row("**All straight bets**", straight)
    for sport in ("NFL", "College", "NBA"):
        q_row({"College": "College football"}.get(sport, sport), [p for p in straight if p.leg.sport == sport])
    for kind, label in (("spread", "Spreads"), ("total", "Totals"), ("moneyline", "Moneylines")):
        q_row(label, [p for p in straight if p.leg.kind == kind])
    q_row("With bought points", [p for p in straight if p.leg.buy_points])
    q_row("Without bought points", [p for p in straight if not p.leg.buy_points and p.leg.kind != "moneyline"])
    add("")
    add("\"Approx value per $1\" is what each dollar risked was worth at the closing price after removing the vig. "
        "A typical bet with no edge sits near −4.5%. Zero or better means you were getting fair or better prices.\n")

    # timing
    moved = [p for p in ok if p.leg.kind in ("spread", "total") and p.pts_vs_open is not None
             and abs(p.pts_vs_close - p.pts_vs_open) >= 1]
    add("## Timing: games where the line moved a point or more from open to close\n")
    add("Caution: the \"open\" here is the first line DraftKings ever posted for the game, which for NFL games can be a "
        "lookahead number from weeks or months earlier. It overstates what was available the week of the game. "
        "The line logger in Phase 1B replaces this with what your own book posted and when.\n")
    if moved:
        mine = [p for p in moved if p.pts_vs_close - p.pts_vs_open > 0]
        against = [p for p in moved if p.pts_vs_close - p.pts_vs_open < 0]
        add(f"- {len(moved)} of your {sum(1 for p in ok if p.leg.kind in ('spread','total'))} spread and total picks (straight bets plus parlay and teaser legs) were on games that moved a point or more.")
        add(f"- The market moved **toward your side** on {len(mine)} and **away from it** on {len(against)}.")
        if mine:
            late = sum(p.pts_vs_close <= 0 for p in mine)
            early = sum(p.pts_vs_open >= 0 for p in mine)
            add(f"- When it moved toward your side ({len(mine)} picks): you had the opening number or better on {early}, "
                f"and the closing number or worse on {late}. Average: {mean(p.pts_vs_close for p in mine):+.2f} points against the close, "
                f"{mean(p.pts_vs_open for p in mine):+.2f} against the open.")
        if against:
            add(f"- When it moved away from your side ({len(against)} picks): average {mean(p.pts_vs_close for p in against):+.2f} points against the close "
                "(negative means a better number was available later).")
    else:
        add("No priced picks on games that moved a point or more.")
    add("")

    # teasers
    add("## Teasers\n")
    add("| Teaser | Tickets | Won-lost | Net | Legs | Legs won | Leg win rate | Needed per leg | True Wong legs |")
    add("|---|---|---|---|---|---|---|---|---|")
    pay = {(2, 6.5): -120, (3, 6.5): 140, (2, 7): -140, (3, 7): 120, (3, 10): -130, (4, 13): -140, (2, 6): None}
    tz_ = defaultdict(list)
    for w in wagers:
        if w.type_code == "T" and w.channel == "pregame":
            tz_[(len(w.legs), max(l.teaser_points for l in w.legs))].append(w)
    for (n, pts), ws in sorted(tz_.items(), key=lambda kv: -len(kv[1])):
        legs = [l for w in ws for l in w.legs]
        lw = sum(l.outcome == "W" for l in legs)
        graded = sum(l.outcome in ("W", "L") for l in legs)
        price = pay.get((n, pts))
        need = f"{100 * breakeven_leg_rate(price, n):.1f}%" if price else "price not on file"
        wong = sum(1 for l in legs if l.kind == "spread" and l.sport == "NFL" and l.line is not None and crosses_3_and_7(l.line, pts))
        add(f"| {n}-team {pts:g}-point | {len(ws)} | {sum(w.status=='W' for w in ws)}-{sum(w.status=='L' for w in ws)} | {money(sum(w.net for w in ws))} "
            f"| {len(legs)} | {lw} | {100*lw/graded:.0f}% | {need} | {wong} of {len(legs)} |")
    add("")
    add("A \"true Wong leg\" is an NFL side teased through both 3 and 7 without crossing zero. Totals, college games and anything else are not.\n")
    t_legs = [p for p in ok if p.wager.type_code == "T"]
    if t_legs:
        add(f"Teaser legs against the close (before teaser points): {sum(p.pts_vs_close > 0 for p in t_legs)} better, "
            f"{sum(p.pts_vs_close == 0 for p in t_legs)} same, {sum(p.pts_vs_close < 0 for p in t_legs)} worse, "
            f"average {mean(p.pts_vs_close for p in t_legs):+.2f} points.\n")

    # bought points
    bought = [(w, w.legs[0]) for w in wagers if w.channel == "pregame" and w.type_code in ("S", "L") and w.legs[0].buy_points]
    add("## Bought points (straight bets)\n")
    if bought:
        add("| Sport | Market | Bought | From → to | Price paid | On or off 3 or 7 | Result |")
        add("|---|---|---|---|---|---|---|")
        for w, l in bought:
            keys = touches_key(l.orig_line, l.line) if l.kind == "spread" and l.sport in ("NFL", "College") else []
            add(f"| {l.sport} | {l.kind} | {l.buy_points:g} | {l.orig_line:g} → {l.line:g} | {l.price} | {', '.join(map(str, keys)) or 'no'} | {money(w.net)} |")
        add("")
        on_key = sum(1 for w, l in bought if l.kind == "spread" and l.sport == "NFL" and touches_key(l.orig_line, l.line))
        add(f"{len(bought)} bets with bought points, net {money(sum(w.net for w, _ in bought))}. "
            f"{on_key} were NFL spreads moving on or off 3 or 7, the only case where buying can be worth the price. "
            "Buying points on totals is never on a key number.\n")
    else:
        add("None.\n")

    # stakes
    cap = cfg["unit"] * cfg["max_units"]
    over = [w for w in wagers if w.risk > cap and not w.free_play]
    add("## Stakes\n")
    add(f"- Unit is ${cfg['unit']}, cap ${cap} a bet. {len(over)} of {len(wagers)} wagers risked more than the cap; they net {money(sum(w.net for w in over))}.")
    add(f"- Average risked ${mean(w.risk for w in wagers):,.0f}, largest ${max(w.risk for w in wagers):,.0f}.\n")

    # unpriced
    add("## What could not be priced, and why\n")
    reasons = Counter(p.reason for p in priced if not p.ok)
    add(f"{sum(p.ok for p in priced)} of {len(priced)} individual picks were priced against a closing line.\n")
    for r, n in reasons.most_common():
        add(f"- {n}: {r}")
    add("")
    return "\n".join(out)
