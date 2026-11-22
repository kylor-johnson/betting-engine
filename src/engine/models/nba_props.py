"""NBA player props model: projected minutes x production per minute.

Minutes (the part that moves most, and the part injury news changes):
- weighted recent minutes (fitted recency);
- teammates out: regulars who appeared in one of the team's last three games and averaged 15+ minutes but are
  not playing; their minutes go to the players still in the rotation in proportion to their minutes, at a
  fitted rate (history: no box-score line for the game, which the inactive list shows before tip; live: the
  official injury report, reporter news through Rotoworld, then ESPN, listing him Out or Doubtful);
- blowout risk: starters (28+ minutes) lose minutes as the spread grows past 8 points, fitted;
- second night of a back-to-back, fitted.

Per minute: weighted rates (slower recency), boosted when vacated shot volume (shots + 0.44 free throws +
turnovers) has to go somewhere, at a fitted rate, and scaled by the team's expected points from the closing
line against its average in the games behind the rates (fitted power).

Distribution: the 500 earlier player-games with the closest projection, as in the NFL model.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from engine.models import nba_data
from engine.models.props import Distribution, norm_name

PINNACLE_STATS = {"Points": ("pts", "yards"), "Rebounds": ("reb", "yards"), "Assists": ("ast", "count"),
                  "Threes Made": ("fg3m", "count"), "Pts & Rebs & Asts": ("pra", "yards")}
KIND = {s: k for s, k in PINNACLE_STATS.values()}
STATS = list(KIND)
NAME_TO_ABBR = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN", "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE", "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GS", "Houston Rockets": "HOU", "Indiana Pacers": "IND", "Los Angeles Clippers": "LAC",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM", "Miami Heat": "MIA", "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NO", "New York Knicks": "NY", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC", "San Antonio Spurs": "SA", "Toronto Raptors": "TOR", "Utah Jazz": "UTAH", "Washington Wizards": "WSH",
}
DECAYS = (0.8, 0.9, 0.95)
ALPHAS = (0.0, 0.5, 1.0)
MAX_BACK = 25
MIN_ROLE = 15.0          # projected minutes for a prop-worthy player
REG_MIN = 15.0           # a regular whose absence frees minutes
STARTER_MIN = 28.0
GRID = {"r_min": (0.0, 0.25, 0.5, 0.75, 1.0), "r_use": (0.0, 0.25, 0.5, 0.75), "blowout": (0.0, -0.01, -0.02, -0.03),
        "b2b": (1.0, 0.97, 0.94)}
NO_NEWS = {"r_min": 0.0, "r_use": 0.0, "blowout": 0.0, "b2b": 1.0}


def usage(p: dict) -> float:
    return p.get("fga", 0) + 0.44 * p.get("fta", 0) + p.get("tov", 0)


def _entry(season: int, p: dict, implied: float) -> tuple:
    m = p["min"]
    per = {s: (p[s] if s != "pra" else p["pts"] + p["reb"] + p["ast"]) / m for s in ("pts", "reb", "ast", "fg3m")} if m > 0 else {}
    if per:
        per["pra"] = per["pts"] + per["reb"] + per["ast"]
    return (season, m, per, usage(p), implied)


def _weighted(hist: list[tuple], season: int, decay: float) -> dict | None:
    """Weighted minutes, per-minute rates, usage and implied points over his recent games (games he played)."""
    use = [h for h in hist[-MAX_BACK:] if h[0] >= season - 1 and h[1] > 0]
    if len(use) < 3:
        return None
    n = len(use)
    wsum = mins = imp = use_g = 0.0
    rate_w = 0.0
    rates = defaultdict(float)
    for i, (s, m, per, u, im) in enumerate(use):
        w = decay ** (n - 1 - i) * (1.0 if s == season else 0.5)
        wsum += w
        mins += w * m
        use_g += w * u
        imp += w * im
        rw = w * m                       # rates weighted by minutes too: a 4-minute game says little
        rate_w += rw
        for k, v in per.items():
            rates[k] += rw * v
    return {"min": mins / wsum, "use": use_g / wsum, "imp": imp / wsum, "rate": {k: v / rate_w for k, v in rates.items()}}


class TeamState:
    def __init__(self):
        self.recent: dict[str, deque] = defaultdict(lambda: deque(maxlen=3))
        self.last_team: dict[str, str] = {}
        self.last_date: dict[str, str] = {}

    def regulars(self, team: str) -> set[str]:
        out: set[str] = set()
        for s in self.recent[team]:
            out |= s
        return {p for p in out if self.last_team.get(p) == team}

    def record(self, team: str, played: set[str], day: str) -> None:
        self.recent[team].append(set(played))
        for p in played:
            self.last_team[p] = team
        self.last_date[team] = day


def vacated(regs: set[str], out: set[str], hist: dict, season: int) -> tuple[float, float, list[str]]:
    """(minutes boost input, usage boost input, names out). Boost input = vacated / still playing."""
    tot_m = gone_m = tot_u = gone_u = 0.0
    named = []
    for p in regs:
        w = _weighted(hist.get(p, []), season, 0.9)
        if w is None or w["min"] < REG_MIN:
            continue
        tot_m += w["min"]
        tot_u += w["use"]
        if p in out:
            gone_m += w["min"]
            gone_u += w["use"]
            named.append(p)
    bm = min(1.0, gone_m / max(30.0, tot_m - gone_m)) if gone_m else 0.0
    bu = min(1.0, gone_u / max(10.0, tot_u - gone_u)) if gone_u else 0.0
    return bm, bu, named


def _is_b2b(prev_day: str | None, day: str) -> bool:
    if not prev_day:
        return False
    return (datetime.fromisoformat(day) - datetime.fromisoformat(prev_day)).days == 1


def history(games: list[dict]) -> tuple[list[dict], dict, TeamState, dict]:
    """Every player-game with what was known before it (plus who was missing from the game)."""
    hist: dict[str, list[tuple]] = defaultdict(list)
    names: dict[str, str] = {}
    teams = TeamState()
    recs = []
    for g in games:
        if g["home_spread"] is None or g["total"] is None:
            # no closing line: still learn from the game, but do not test on it
            pass
        for side in ("home", "away"):
            team = g[side]
            rows = [p for p in g["players"] if p["team"] == team]
            played = {p["id"] for p in rows if p["min"] > 0}
            regs = teams.regulars(team)
            bm, bu, _ = vacated(regs, regs - played, hist, g["season"])
            has_line = g["home_spread"] is not None and g["total"] is not None
            spread_for = (-g["home_spread"] if side == "home" else g["home_spread"]) if has_line else 0.0   # + = favored
            implied = (g["total"] / 2 + spread_for / 2) if has_line else 112.0
            b2b = _is_b2b(teams.last_date.get(team), g["date"])
            for p in rows:
                if p["min"] <= 0:
                    continue
                pid = p["id"]
                names[pid] = p["name"]
                h = hist[pid]
                rec = {"pid": pid, "season": g["season"], "date": g["date"], "team": team, "has_line": has_line,
                       "implied": implied, "spread": spread_for, "b2b": b2b, "bm": bm, "bu": bu,
                       "actual": {s: (p[s] if s != "pra" else p["pts"] + p["reb"] + p["ast"]) for s in STATS},
                       "w": {d: _weighted(h, g["season"], d) for d in DECAYS}}
                if any(rec["w"].values()):
                    recs.append(rec)
            for p in rows:
                if p["min"] > 0:
                    hist[p["id"]].append(_entry(g["season"], p, implied))
            teams.record(team, played, g["date"])
    return recs, hist, teams, names


def project(rec: dict, stat: str, base: tuple, news: dict) -> float | None:
    dm, dr, alpha = base
    wm, wr = rec["w"].get(dm), rec["w"].get(dr)
    if wm is None or wr is None or stat not in wr["rate"]:
        return None
    mins = wm["min"] * (1 + news["r_min"] * rec["bm"])
    if wm["min"] >= STARTER_MIN:
        mins *= 1 + news["blowout"] * max(0.0, abs(rec["spread"]) - 8)
    if rec["b2b"]:
        mins *= news["b2b"]
    rate = wr["rate"][stat] * (1 + news["r_use"] * rec["bu"]) * (rec["implied"] / wr["imp"] if wr["imp"] > 0 else 1.0) ** alpha
    return max(0.0, mins * rate)


def eligible(rec: dict) -> bool:
    w = rec["w"].get(0.9)
    return bool(w and w["min"] >= MIN_ROLE and rec["has_line"])


def _sse(pool, stat, base, news) -> float:
    se = 0.0
    for r in pool:
        p = project(r, stat, base, news)
        if p is not None:
            se += (p - r["actual"][stat]) ** 2
    return se


def fit(recs: list[dict], stat: str, with_news: bool = True) -> tuple[tuple, dict]:
    pool = [r for r in recs if eligible(r)]
    best = None
    for dm in DECAYS:
        for dr in DECAYS:
            for a in ALPHAS:
                se = _sse(pool, stat, (dm, dr, a), NO_NEWS)
                if best is None or se < best[0]:
                    best = (se, (dm, dr, a))
    base = best[1]
    news = dict(NO_NEWS)
    if with_news:
        for _ in range(2):                       # coordinate descent over the news terms
            for k, vals in GRID.items():
                scores = [(_sse(pool, stat, base, {**news, k: v}), v) for v in vals]
                news[k] = min(scores)[1]
    return base, news


def _plain(rec: dict, stat: str) -> float | None:
    w = rec["w"].get(0.95)
    return None if w is None or stat not in w["rate"] else w["min"] * w["rate"][stat]


def backtest(first_test: int = 2025) -> dict:
    games = nba_data.load()
    recs, _, _, _ = history(games)
    seasons = sorted({r["season"] for r in recs})
    report = {}
    for stat in STATS:
        kind = KIND[stat]
        sc = {k: {"n": 0, "mae": 0.0, "brier": 0.0, "nb": 0} for k in ("plain", "base", "news", "base_when_news", "news_when_news")}
        params, rel = {}, defaultdict(lambda: [0.0, 0, 0])
        for season in [s for s in seasons if s >= first_test]:
            train = [r for r in recs if r["season"] < season]
            test = [r for r in recs if r["season"] == season and eligible(r)]
            if not train or not test:
                continue
            base, news = fit(train, stat)
            params[season] = {"recency_minutes": base[0], "recency_rates": base[1], "points_power": base[2], **news}
            pool = [r for r in train if eligible(r)]
            dists = {"base": Distribution([(project(r, stat, base, NO_NEWS), r["actual"][stat]) for r in pool if project(r, stat, base, NO_NEWS) is not None], kind),
                     "news": Distribution([(project(r, stat, base, news), r["actual"][stat]) for r in pool if project(r, stat, base, news) is not None], kind),
                     "plain": Distribution([(_plain(r, stat), r["actual"][stat]) for r in pool if _plain(r, stat) is not None], kind)}
            for r in test:
                pb, pn, pp = project(r, stat, base, NO_NEWS), project(r, stat, base, news), _plain(r, stat)
                if pb is None or pn is None or pp is None:
                    continue
                actual = r["actual"][stat]
                med = dists["base"].median(pb)
                step = 0.5 if kind == "count" else max(1.0, round(med * 0.15))
                lines = [math.floor(x) + 0.5 for x in (med - step, med, med + step)]
                touched = pb > 0 and abs(pn / pb - 1) > 0.05
                for name, proj in (("plain", pp), ("base", pb), ("news", pn)):
                    keys = [name] + ([f"{name}_when_news"] if touched and name != "plain" else [])
                    m = dists[name].median(proj)
                    for k in keys:
                        sc[k]["n"] += 1
                        sc[k]["mae"] += abs(actual - m)
                    for line in lines:
                        p = dists[name].p_over(proj, line)
                        hit = 1 if actual > line else 0
                        for k in keys:
                            sc[k]["brier"] += (p - hit) ** 2
                            sc[k]["nb"] += 1
                        if name == "news":
                            b = min(9, int(p * 10))
                            rel[b][0] += p
                            rel[b][1] += 1
                            rel[b][2] += hit
        report[stat] = {k: {"player_games": v["n"], "mae": round(v["mae"] / v["n"], 3) if v["n"] else None,
                            "brier": round(v["brier"] / v["nb"], 4) if v["nb"] else None} for k, v in sc.items()}
        report[stat]["params"] = params
        report[stat]["calibration"] = [{"said": round(v[0] / v[1], 3), "happened": round(v[2] / v[1], 3), "n": v[1]}
                                       for b, v in sorted(rel.items()) if v[1] >= 30]
    return report


# ---------------------------------------------------------------- live pricing and forward test

def current_season(now: datetime) -> int:
    return now.year + 1 if now.month >= 8 else now.year


class NbaInjuries:
    """Who is out tonight: the official report (Out/Doubtful), then a Rotoworld post from the last 36 hours, then ESPN."""

    def __init__(self, official: dict[str, str], reporter: dict[str, str], espn_status: dict[str, str]):
        self.official, self.reporter, self.espn = official, reporter, espn_status

    @classmethod
    def fetch(cls, con, now: datetime) -> "NbaInjuries":
        from engine.odds.espn import SourceError
        from engine.picks import nba_news, player_news
        official: dict[str, str] = {}
        try:
            _, official = nba_news.latest_official(now)
        except SourceError:
            official = {}
        rep = {n: s for n, (s, _, _) in player_news.latest_signals(con, "NBA", now).items()}
        esp = {norm_name(p.name): p.status for p in nba_news.parse_report(nba_news._get(nba_news.REPORT_URL, "ESPN NBA injury report"))}
        if not official and not esp:
            raise SourceError("no NBA injury source answered")
        return cls(official, rep, esp)

    def status(self, name: str) -> tuple[str, str]:
        """(status, where it came from)."""
        n = norm_name(name)
        sig = self.reporter.get(n)
        if sig == "not playing":
            return "Out", "reporter"
        if sig == "playing":
            return "Available", "reporter"
        if n in self.official:
            return self.official[n], "official report"
        if n in self.espn:
            return self.espn[n], "ESPN"
        return "Available", ""

    def out(self, name: str) -> bool:
        return self.status(name)[0] in ("Out", "Doubtful", "Suspension", "Injured Reserve")


PARAMS_DIR = nba_data.config.DATA / "models"


def load_params(season: int) -> dict | None:
    """Fitted recency and news terms for this season (fitted once on earlier seasons; they do not change mid-season)."""
    import json
    p = PARAMS_DIR / f"nba_props_{season}.json"
    return json.loads(p.read_text()) if p.exists() else None


def save_params(season: int, params: dict) -> None:
    import json
    PARAMS_DIR.mkdir(parents=True, exist_ok=True)
    (PARAMS_DIR / f"nba_props_{season}.json").write_text(json.dumps({s: {"base": list(b), "news": n} for s, (b, n) in params.items()}, indent=1))


class NbaModel:
    def __init__(self, now: datetime | None = None):
        now = now or datetime.now(timezone.utc)
        self.season = current_season(now)
        games = nba_data.load()
        if not games:
            from engine.odds.espn import SourceError
            raise SourceError("no NBA box scores on disk; run `engine nba-history` first")
        recs, self.hist, self.teams, self.names = history(games)
        train = [r for r in recs if r["season"] < self.season]
        self.params, self.dists = {}, {}
        cached = load_params(self.season)
        for stat in STATS:
            pool = [r for r in train if eligible(r)]
            if cached and stat in cached:
                base, news = tuple(cached[stat]["base"]), cached[stat]["news"]
            else:
                base, news = fit(train, stat)
            self.params[stat] = (base, news)
            self.dists[stat] = Distribution([(p, r["actual"][stat]) for r in pool if (p := project(r, stat, base, news)) is not None], KIND[stat])
        if not cached:
            save_params(self.season, self.params)
        self.players: dict[tuple[str, str], str] = {}
        for g in games:
            if g["season"] == self.season:
                for p in g["players"]:
                    if p["min"] > 0:
                        self.players[(norm_name(p["name"]), p["team"])] = p["id"]
        self.through = max((g["date"] for g in games), default="")

    def find(self, name: str, teams: tuple[str, str]) -> str | None:
        n = norm_name(name)
        hits = [pid for t in teams if (pid := self.players.get((n, t)))]
        return hits[0] if len(hits) == 1 else None

    def price(self, pid: str, stat: str, line: float, implied: float, spread_for: float, game_day: str,
              injuries: NbaInjuries | None) -> dict | None:
        team = self.teams.last_team.get(pid, "")
        name = self.names.get(pid, "")
        if injuries and injuries.out(name):
            st, src = injuries.status(name)
            return {"skip": f"{name} is {st} ({src})"}
        regs = self.teams.regulars(team)
        out = {p for p in regs if injuries and injuries.out(self.names.get(p, ""))}
        bm, bu, named = vacated(regs, out, self.hist, self.season)
        rec = {"w": {d: _weighted(self.hist[pid], self.season, d) for d in DECAYS}, "implied": implied, "spread": spread_for,
               "b2b": _is_b2b(self.teams.last_date.get(team), game_day), "bm": bm, "bu": bu, "has_line": True}
        if not eligible(rec):
            return None
        base, news = self.params[stat]
        p0 = project(rec, stat, base, NO_NEWS)
        p = project(rec, stat, base, news)
        if p is None:
            return None
        bits = []
        if named and (news["r_min"] or news["r_use"]):
            bits.append("out: " + ", ".join(self.names.get(x, x) for x in named))
        if rec["b2b"] and news["b2b"] != 1.0:
            bits.append("second night of a back-to-back")
        if rec["w"][0.9]["min"] >= STARTER_MIN and abs(spread_for) > 8 and news["blowout"]:
            bits.append(f"blowout risk (spread {abs(spread_for):g})")
        if injuries:
            st, src = injuries.status(name)
            if st in ("Questionable", "Day-To-Day", "Probable") and src:
                bits.append(f"listed {st} ({src}); not adjusted")
        note = "; ".join(bits) + (f" ({p / p0 - 1:+.0%} on the projection)" if p0 and abs(p / p0 - 1) > 0.005 else "") if bits else ""
        d = self.dists[stat]
        return {"projection": round(p, 2), "median": d.median(p), "p_over": round(d.p_over(p, line), 4), "news": note,
                "minutes": round(rec["w"][base[0]]["min"], 1)}


def split_description(desc: str) -> tuple[str, str] | None:
    import re
    m = re.match(r"^(.*?) Total (.+)$", desc.strip())
    if not m or m.group(2) not in PINNACLE_STATS:
        return None
    return m.group(1), m.group(2)


def evaluate_logged(con, model: NbaModel, now: datetime, injuries: NbaInjuries | None = None) -> list[dict]:
    """Price every Pinnacle NBA prop in the latest read for games not started; store in prop_evals (sport NBA)."""
    from zoneinfo import ZoneInfo

    from engine.models import props
    from engine.odds.math import no_vig
    con.execute(props.SCHEMA)
    ts = con.execute("SELECT max(ts_utc) FROM derivative_snapshots WHERE source='Pinnacle' AND sport='NBA' AND market='prop'").fetchone()[0]
    if ts is None:
        return []
    rows = con.execute("""SELECT start_utc, away, home, description, line, price_a, price_b FROM derivative_snapshots
                          WHERE source='Pinnacle' AND sport='NBA' AND market='prop' AND ts_utc = ?""", [ts]).fetchall()
    injuries = injuries or NbaInjuries.fetch(con, now)
    east = ZoneInfo("America/New_York")
    out, imp_cache = [], {}
    live: list = []
    try:
        from engine.picks import sources
        live = sources.pinnacle("NBA")
    except Exception:
        live = []
    for start, away, home, desc, line, po, pu in rows:
        st = datetime.fromisoformat(start.replace("Z", "+00:00")) if start else None
        if st is None or st <= now or po is None or pu is None:
            continue
        sp = split_description(desc)
        if sp is None:
            continue
        player, label = sp
        stat = PINNACLE_STATS[label][0]
        teams = (NAME_TO_ABBR.get(away), NAME_TO_ABBR.get(home))
        if None in teams:
            continue
        pid = model.find(player, teams)
        if pid is None:
            continue
        if (away, home) not in imp_cache:
            imp_cache[(away, home)] = props.game_implied(away, home, ts, con, sport="NBA") or live_implied(away, home, live)
        imp = imp_cache[(away, home)]
        if imp is None:
            continue
        is_home = model.teams.last_team.get(pid) == teams[1]
        implied = imp[1] if is_home else imp[0]
        spread_for = (imp[1] - imp[0]) if is_home else (imp[0] - imp[1])
        got = model.price(pid, stat, line, implied, spread_for, st.astimezone(east).date().isoformat(), injuries)
        if got is None or "skip" in got:
            continue
        mp = no_vig(po, pu)[0]
        team = model.teams.last_team.get(pid, "")
        rec = {"ts_utc": ts, "start_utc": start, "away": away, "home": home, "player": player, "player_id": pid, "team": team,
               "stat": stat, "label": label, "line": line, "over_price": po, "under_price": pu, "market_p_over": round(mp, 4),
               "model_p_over": got["p_over"], "model_median": got["median"], "projection": got["projection"], "news": got["news"]}
        out.append(rec)
        con.execute("DELETE FROM prop_evals WHERE ts_utc = ? AND player_id = ? AND stat = ? AND line = ? AND sport = 'NBA'", [ts, pid, stat, line])
        con.execute("""INSERT INTO prop_evals (ts_utc, start_utc, away, home, player, player_id, team, stat, line, over_price,
                       under_price, market_p_over, model_p_over, model_median, projection, season, through_week, news, sport)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'NBA')""",
                    [ts, start, away, home, player, pid, team, stat, line, po, pu, rec["market_p_over"], rec["model_p_over"],
                     rec["model_median"], rec["projection"], model.season, None, rec["news"]])
    return out


def live_implied(away: str, home: str, lines: list) -> tuple[float, float] | None:
    """(away, home) expected points from Pinnacle's current NBA game line."""
    from engine.picks.slate import _find  # noqa: F401
    for l in lines:
        if l.home_spread is None or l.total is None:
            continue
        if NAME_TO_ABBR.get(l.home) == NAME_TO_ABBR.get(home) and NAME_TO_ABBR.get(l.away) == NAME_TO_ABBR.get(away):
            return l.total / 2 + l.home_spread / 2, l.total / 2 - l.home_spread / 2
    return None


def grade(con) -> int:
    """Fill outcomes from the stored ESPN box scores (fetch yesterday's and today's finished games first).
    A player with no minutes in that game did not play: void, left ungraded."""
    from zoneinfo import ZoneInfo

    from engine.models import props
    con.execute(props.SCHEMA)
    open_rows = con.execute("SELECT DISTINCT player_id, stat, start_utc FROM prop_evals WHERE outcome IS NULL AND sport = 'NBA'").fetchall()
    if not open_rows:
        return 0
    nba_data.download([current_season(datetime.now(timezone.utc))], log=lambda *_: None)
    east = ZoneInfo("America/New_York")
    by = {}
    for g in nba_data.load():
        for p in g["players"]:
            if p["min"] > 0:
                by[(p["id"], g["date"])] = {s: (p[s] if s != "pra" else p["pts"] + p["reb"] + p["ast"]) for s in STATS}
    n = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for pid, stat, start in open_rows:
        day = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(east).date().isoformat()
        got = by.get((pid, day))
        if got is None:
            continue
        con.execute("UPDATE prop_evals SET outcome = ?, graded_utc = ? WHERE player_id = ? AND stat = ? AND start_utc = ? AND outcome IS NULL AND sport = 'NBA'",
                    [float(got[stat]), now, pid, stat, start])
        n += 1
    return n


ABOUT = ("These are not bets. The model projects minutes (recent minutes, plus minutes freed by teammates who are out, "
         "minus blowout risk for starters and the second night of a back-to-back) times production per minute (boosted "
         "when a teammate's shots need a new home, scaled by the team's expected points). Who is out comes from reporter "
         "news, then the official NBA injury report, then ESPN; players listed Out or Doubtful are not priced, and "
         "Questionable players are shown but not adjusted (no history to size it). Every prop is graded after the game.")
