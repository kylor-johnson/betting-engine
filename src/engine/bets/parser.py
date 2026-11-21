"""Parse typed bets and watchlist entries like "Kansas State +10 -110 25"."""
from __future__ import annotations

import re
from dataclasses import dataclass

_NUM = r"[+-]?\d+(?:\.\d+|½)?"


@dataclass
class Typed:
    team: str
    market: str            # spread, over, under, ml
    line: float | None     # spread or total; None for moneyline
    price: float | None
    stake: float | None


def _f(tok: str) -> float:
    return float(tok.replace("½", ".5"))


def parse(text: str) -> Typed:
    """Team words, then the number, then optionally price and stake.

    "Kansas State +10 -110 25"   spread +10 at -110 for $25
    "Chiefs -3"                  spread -3
    "Bills ML -150 50"           moneyline at -150 for $50
    "Bills/Jets o47.5 -110"      over 47.5
    "Bills u 47 -105 25"         under 47
    """
    toks = text.replace("$", "").split()
    if not toks:
        raise ValueError("empty bet")
    i = 0
    team: list[str] = []
    while i < len(toks) and not re.fullmatch(_NUM, toks[i]) and not re.fullmatch(r"(?i)(ml|[ou])(\d.*)?", toks[i]):
        team.append(toks[i])
        i += 1
    if not team:
        raise ValueError(f"no team in {text!r}")
    if i >= len(toks):
        raise ValueError(f"no line in {text!r}: add a spread, o/u total, or ML")
    tok = toks[i]
    i += 1
    line: float | None
    m = re.fullmatch(r"(?i)([ou])(\d+(?:\.\d+|½)?)?", tok)
    if tok.lower() == "ml":
        market, line = "ml", None
    elif m:
        market = "over" if m.group(1).lower() == "o" else "under"
        if m.group(2):
            line = _f(m.group(2))
        elif i < len(toks) and re.fullmatch(r"\d+(?:\.\d+|½)?", toks[i]):
            line = _f(toks[i])
            i += 1
        else:
            raise ValueError(f"no total after {tok!r} in {text!r}")
    elif tok[0] in "+-" or tok in ("0", "pk", "PK"):
        market, line = "spread", _f(tok)
    else:
        raise ValueError(f"spread needs a sign in {text!r}: write +10 or -3")
    rest = [_f(t) for t in toks[i:] if re.fullmatch(_NUM, t)]
    if len(rest) != len(toks[i:]):
        raise ValueError(f"could not read the end of {text!r}")
    price = stake = None
    if rest:
        if abs(rest[0]) >= 100:
            price = rest[0]
            stake = rest[1] if len(rest) > 1 else None
        elif market == "ml":
            raise ValueError(f"moneyline price must be 100 or more in {text!r}")
        else:
            stake = rest[0]
    if price is not None and abs(price) < 100:
        raise ValueError(f"price {price:g} is not American odds")
    if stake is not None and stake <= 0:
        raise ValueError("stake must be positive")
    return Typed(" ".join(team), market, line, price, stake)
