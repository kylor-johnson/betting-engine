"""Price past bets against DraftKings' opening and closing lines from ESPN."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from engine.bets.history import IN_SCOPE_SPORTS, Leg, Wager
from engine.odds import espn
from engine.odds.math import american_to_decimal, ev_per_dollar, no_vig, win_prob_shift

ET = ZoneInfo("America/New_York")
STRAIGHT = {"S", "L", "M"}


@dataclass
class Priced:
    wager: Wager
    leg: Leg
    reason: str | None = None          # why it could not be priced
    match: str = ""
    close_line: float | None = None    # for my side
    open_line: float | None = None
    close_price: float | None = None   # for my side
    pts_vs_close: float | None = None  # positive = I had the better number
    pts_vs_open: float | None = None
    fair_prob: float | None = None     # approx win probability of my bet
    ev: float | None = None            # approx expected profit per $1, straight bets only
    price_vs_close: str = ""           # moneylines: better / same / worse

    @property
    def ok(self) -> bool:
        return self.reason is None


def _events_for(leg: Leg, cache: Path | None, memo: dict) -> list[espn.Event]:
    day = leg.game_time.astimezone(ET).date()
    out = []
    for d in (day, day + timedelta(days=1), day - timedelta(days=1)):
        k = (leg.sport, d)
        if k not in memo:
            memo[k] = espn.scoreboard(leg.sport, d, cache)
        out.append(memo[k])
    return out


def price_leg(w: Wager, leg: Leg, margin_sd: dict, cache: Path | None, memo: dict) -> Priced:
    p = Priced(w, leg)
    if w.channel != "pregame":
        p.reason = "live or same-game ticket"
    elif leg.kind not in ("spread", "total", "moneyline"):
        p.reason = "prop or other market (no reference price)"
    elif leg.sport not in IN_SCOPE_SPORTS:
        p.reason = "sport out of scope"
    elif leg.period != "Game":
        p.reason = "first-half line (no reference price)"
    elif leg.game_time is None:
        p.reason = "no game time on the ticket"
    if p.reason:
        return p

    ev = None
    for events in _events_for(leg, cache, memo):
        ev, how = espn.find_event(events, leg.team1, leg.team2)
        if ev:
            p.match = how
            break
    if ev is None:
        p.reason = "game not found on ESPN"
        return p
    if w.accepted and w.accepted >= ev.start:
        p.reason = "placed after the game started"
        return p
    odds = memo.get(("odds", ev.event_id))
    if odds is None and ("odds", ev.event_id) not in memo:
        odds = memo[("odds", ev.event_id)] = espn.event_odds(ev, cache)
    if odds is None:
        p.reason = "ESPN has no line for this game"
        return p
    c, o = odds.close, odds.open
    straight = w.type_code in STRAIGHT and leg.price is not None
    sd = margin_sd[leg.sport]

    if leg.kind == "total":
        if c.total is None or leg.over_under not in ("O", "U"):
            p.reason = "ESPN has no closing total"
            return p
        sign = 1 if leg.over_under == "O" else -1
        p.close_line, p.open_line = c.total, o.total
        p.pts_vs_close = sign * (c.total - leg.line)
        p.pts_vs_open = sign * (o.total - leg.line) if o.total is not None else None
        mine, other = (c.over_price, c.under_price) if sign == 1 else (c.under_price, c.over_price)
        p.close_price = mine
        if mine and other:
            p.fair_prob = no_vig(mine, other)[0] + win_prob_shift(p.pts_vs_close, sd["total"])
    else:
        side = espn.side_of(ev, leg.chosen)
        if side is None:
            p.reason = "could not tell which team was bet"
            return p
        flip = 1 if side == "home" else -1
        if leg.kind == "spread":
            if c.home_spread is None:
                p.reason = "ESPN has no closing spread"
                return p
            p.close_line = flip * c.home_spread
            p.open_line = flip * o.home_spread if o.home_spread is not None else None
            p.pts_vs_close = leg.line - p.close_line
            p.pts_vs_open = leg.line - p.open_line if p.open_line is not None else None
            mine, other = (c.home_spread_price, c.away_spread_price) if side == "home" else (c.away_spread_price, c.home_spread_price)
            p.close_price = mine
            if mine and other:
                p.fair_prob = no_vig(mine, other)[0] + win_prob_shift(p.pts_vs_close, sd["spread"])
        else:  # moneyline
            mine, other = (c.home_ml, c.away_ml) if side == "home" else (c.away_ml, c.home_ml)
            if not mine or not other:
                p.reason = "ESPN has no closing moneyline"
                return p
            p.close_price = mine
            p.fair_prob = no_vig(mine, other)[0]
            if leg.price is not None:
                a, b = american_to_decimal(leg.price), american_to_decimal(mine)
                p.price_vs_close = "better" if a > b + 1e-9 else "worse" if a < b - 1e-9 else "same"
    if straight and p.fair_prob is not None:
        p.ev = ev_per_dollar(min(max(p.fair_prob, 0.01), 0.99), leg.price)
    return p


def price_all(wagers: list[Wager], margin_sd: dict, cache: Path | None) -> list[Priced]:
    memo: dict = {}
    return [price_leg(w, leg, margin_sd, cache, memo) for w in wagers for leg in w.legs]
