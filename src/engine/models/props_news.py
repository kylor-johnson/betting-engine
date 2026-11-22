"""Injury and role news for the props model.

Three effects, each sized on earlier seasons only (`fit`), and each a multiplier on the base projection:

1. **Teammate out.** When regulars on his team are out, their share of targets (or carries, or touches)
   is vacated. The rest of the team absorbs it in proportion to their own shares, at a fitted rate `r`
   (1 = all of it, proportionally). Boost = 1 + r x vacated / (regulars' share still playing).
   History: a regular is a player who appeared in one of the team's last two games, still with that team.
   He counts as out when he had 10%+ of that usage and was listed Out or Doubtful on that week's injury report
   or has no stats row for the game (the inactive list shows this 90 minutes before kickoff). Live: ESPN's injury report (Out, Doubtful, Injured Reserve, Suspension).
2. **Role change.** His share over his last two games against his longer weighted share, clipped to 0.5-2x,
   raised to a fitted power `beta`. Catches a promotion or demotion faster than the slow average does.
3. **Questionable.** A fitted multiplier `q` for players listed Questionable who then play (nflverse injury
   reports in history; ESPN live). A player listed Out or Doubtful himself is not priced.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque

USAGE_OF = {"receptions": "t", "receiving_yards": "t", "rushing_yards": "c", "carries": "c", "tds": "x"}
SHARE_KEY = {"t": "tshare", "c": "cshare", "x": "xshare"}
REGULAR_MIN_SHARE = 0.05
OUT_MIN_SHARE = 0.10
OUT_STATUSES = ("Out", "Doubtful", "Injured Reserve", "Suspension")
R_GRID = (0.0, 0.1, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0)
BETA_GRID = (0.0, 0.25, 0.5, 0.75)
Q_GRID = (0.85, 0.9, 0.95, 1.0)
NO_NEWS = (0.0, 0.0, 1.0)


def shares(r: dict) -> dict[str, float]:
    tt, tc = r.get("team_targets") or 0, r.get("team_carries") or 0
    t, c = float(r.get("targets") or 0), float(r.get("carries") or 0)
    return {"tshare": t / tt if tt else 0.0, "cshare": c / tc if tc else 0.0,
            "xshare": (t + c) / (tt + tc) if tt + tc else 0.0}


def long_share(hist: list[tuple], season: int, decay: float = 0.92) -> dict[str, float] | None:
    use = [h for h in hist[-16:] if h[0] >= season - 1]
    if not use:
        return None
    acc, wsum, n = defaultdict(float), 0.0, len(use)
    for i, h in enumerate(use):
        w = decay ** (n - 1 - i) * (1.0 if h[0] == season else 0.6)
        wsum += w
        for k in SHARE_KEY.values():
            acc[k] += w * h[1].get(k, 0.0)
    return {k: v / wsum for k, v in acc.items()}


def recent_share(hist: list[tuple]) -> dict[str, float] | None:
    use = hist[-2:]
    if not use:
        return None
    return {k: sum(h[1].get(k, 0.0) for h in use) / len(use) for k in SHARE_KEY.values()}


class TeamState:
    """Who has been playing for each team, so 'who is missing today' can be worked out."""

    def __init__(self):
        self.recent: dict[str, deque] = defaultdict(lambda: deque(maxlen=2))
        self.last_team: dict[str, str] = {}

    def regulars(self, team: str) -> set[str]:
        out: set[str] = set()
        for s in self.recent[team]:
            out |= s
        return {p for p in out if self.last_team.get(p) == team}

    def record(self, team: str, played: set[str]) -> None:
        self.recent[team].append(set(played))
        for p in played:
            self.last_team[p] = team


def vacated(team_regulars: set[str], out: set[str], hist: dict[str, list[tuple]], season: int) -> tuple[dict, list[tuple]]:
    """Boost inputs per usage (vacated share / share still playing) and who is out with their shares.
    Only a real role counts as vacated: 10%+ of that usage."""
    total = defaultdict(float)
    gone = defaultdict(float)
    named = []
    for p in team_regulars:
        ls = long_share(hist.get(p, []), season)
        if ls is None:
            continue
        counted = False
        for u, k in SHARE_KEY.items():
            if ls[k] < REGULAR_MIN_SHARE or (p in out and ls[k] < OUT_MIN_SHARE):
                continue          # bit roles, and bit-role players who are out, do not move anything
            total[u] += ls[k]
            if p in out and ls[k] >= OUT_MIN_SHARE:
                gone[u] += ls[k]
                counted = True
        if counted:
            named.append((p, ls))
    boost = {}
    for u in SHARE_KEY:
        left = total[u] - gone[u]
        boost[u] = min(1.5, gone[u] / max(0.05, left)) if gone[u] > 0 else 0.0
    return boost, named


def features(pid: str, hist: dict[str, list[tuple]], season: int, boost: dict, questionable: bool) -> dict:
    h = hist.get(pid, [])
    ls, rs = long_share(h, season), recent_share(h)
    role = {}
    for u, k in SHARE_KEY.items():
        if ls is None or rs is None:
            role[u] = 1.0
        else:
            role[u] = min(2.0, max(0.5, (rs[k] + 0.02) / (ls[k] + 0.02)))
    return {"B": dict(boost), "R": role, "q": bool(questionable)}


def factor(news: dict | None, stat: str, params: tuple[float, float, float]) -> float:
    if not news:
        return 1.0
    r, beta, qm = params
    f = 1.0
    u = USAGE_OF.get(stat)
    if u:
        f *= (1 + r * news["B"][u]) * news["R"][u] ** beta
    if news["q"]:
        f *= qm
    return f


def fit(pool: list[tuple[float, dict, float]], stat: str) -> tuple[float, float, float]:
    """pool = (base projection, news, actual). Grid search on squared error."""
    if not pool:
        return NO_NEWS
    rs, bs = (R_GRID, BETA_GRID) if stat in USAGE_OF else ((0.0,), (0.0,))
    best = None
    for r in rs:
        for b in bs:
            for q in Q_GRID:
                se = 0.0
                for base, news, actual in pool:
                    se += (base * factor(news, stat, (r, b, q)) - actual) ** 2
                if best is None or se < best[0] - 1e-9:
                    best = (se, (r, b, q))
    return best[1]


def describe(news: dict, stat: str, params: tuple, named_out: list[str], role_recent: float | None, role_long: float | None) -> str:
    """Plain-English note for the props sheet."""
    bits = []
    u = USAGE_OF.get(stat)
    f = factor(news, stat, params)
    if u and named_out and news["B"][u] > 0 and params[0] > 0:
        bits.append(f"out: {', '.join(named_out)}")
    if u and abs(math.log(news["R"][u])) > 0.15 and params[1] > 0 and role_recent is not None:
        bits.append(f"role {'up' if news['R'][u] > 1 else 'down'} ({role_recent:.0%} share last two games vs {role_long:.0%})")
    if news["q"]:
        bits.append("listed Questionable")
    if not bits:
        return ""
    return "; ".join(bits) + f" ({(f - 1):+.0%} on the projection)"
