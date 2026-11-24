"""Research 24b: NFL props variant (zero-usage games skipped; RB carry role into catches), as pre-registered in
docs/research/24b-props-variant.md (commit d732378). Test-only: patches the live props model in memory, changes nothing on disk.

UV_PROJECT_ENVIRONMENT=.venv.nosync uv run python scripts/research24/props_variant.py

Variant:
 (a) a game with 0 targets, 0 carries and 0 pass attempts is not added to the player's history, so it is in none of the
     averages built from it (props._weighted, props_news.long_share / recent_share). Kickers are left alone: their usage
     is field-goal attempts, and the literal rule would delete every kicker game (fg_made is then identical in both models).
 (b) for RBs, props_news' carry role ratio R["c"] = clip((last-2 carry share + .02) / (long carry share + .02), 0.5, 2.0);
     when above 1, receptions, targets and receiving-yards projections are multiplied by R["c"] ** 0.25 (so capped at 2 ** 0.25).
Both are applied everywhere the live model uses them (fitting pool, distributions, pricing), fitted by the same procedure.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, timezone
from itertools import groupby
from pathlib import Path
from zoneinfo import ZoneInfo

from engine import config
from engine.models import props, props_news
from engine.odds.snapshots import connect

EAST = ZoneInfo("America/New_York")
SEASON = 2026
RB_STATS = ("receptions", "receiving_yards")
POWER = 0.25

# ---- local files only (no downloads, nothing written)
props.stats_file = lambda year, current: props.RAW / f"stats_player_week_{year}.parquet"
props.injuries_file = lambda year, current: (p if (p := props.RAW / f"injuries_{year}.parquet").exists() else None)

# ---- (b): the news dict carries "rbc" only in the variant; without it this is the live factor exactly
_orig_factor = props_news.factor


def factor(news, stat, params):
    f = _orig_factor(news, stat, params)
    if news and stat in RB_STATS and news.get("rbc", 1.0) > 1.0:
        f *= news["rbc"] ** POWER
    return f


props_news.factor = factor


def zero_usage(r: dict) -> bool:
    return r["position"] != "K" and not (r["targets"] or r["carries"] or r["attempts"])


def history_projections(rows, out_reports, variant: bool):
    """props.history_projections with the variant switches (identical to it when variant=False)."""
    hist: dict[str, list[tuple]] = defaultdict(list)
    teams = props_news.TeamState()
    out = []
    for _, grp in groupby(rows, key=lambda r: (r["game_id"], r["team"])):
        grp = list(grp)
        team, season = grp[0]["team"], grp[0]["season"]
        played = {r["player_id"] for r in grp}
        regs = teams.regulars(team)
        reported = (out_reports or {}).get((season, grp[0]["week"], team), set())
        boost, _ = props_news.vacated(regs, (regs - played) | (regs & reported), hist, season)
        for r in grp:
            h = hist[r["player_id"]]
            news = props_news.features(r["player_id"], hist, season, boost, bool(r.get("questionable")))
            if variant and r["position"] == "RB":
                news["rbc"] = news["R"]["c"]
            rec = {"row": r, "by_decay": {}, "news": news}
            for d in props.DECAYS + (1.0,):
                got = props._weighted(h, season, d)
                if got:
                    rec["by_decay"][d] = got
            if rec["by_decay"]:
                out.append(rec)
        for r in grp:
            if variant and zero_usage(r):
                continue
            hist[r["player_id"]].append(props._hist_entry(r))
        teams.record(team, played)
    return out


class CutModel(props.Model):
    """props.Model, fitted once on seasons before SEASON, with its history cut at a date (stats before that day only)."""

    def __init__(self, rows, out_reports, variant: bool):
        self.variant, self.season, self.rows = variant, SEASON, rows
        recs = history_projections([r for r in rows if r["season"] < SEASON], out_reports, variant)
        train = [r for r in recs if props.FIRST_SEASON < r["row"]["season"] < SEASON]
        self.params, self.dists, self.news_params = {}, {}, {}
        for stat in props.STATS:
            d, a = props.fit_stat(train, stat)
            pool = [r for r in train if d in r["by_decay"] and props.ROLE[stat](r["by_decay"][d][0])]
            self.params[stat] = (d, a)
            npar = props_news.fit([(props._proj_one(r, stat, d, a), r["news"], float(r["row"][stat])) for r in pool], stat) \
                if stat in props.NEWS_STATS else props_news.NO_NEWS
            self.news_params[stat] = npar
            self.dists[stat] = props.Distribution([(props._proj_one(r, stat, d, a) * props_news.factor(r["news"], stat, npar),
                                                    float(r["row"][stat])) for r in pool], props.KIND[stat])

    def cut(self, before: date):
        self.hist = defaultdict(list)
        self.teams = props_news.TeamState()
        self.players, self.names, self.last_week, self.pos = {}, {}, {}, {}
        rows = [r for r in self.rows if r["gameday"] < before]
        for _, grp in groupby(rows, key=lambda r: (r["game_id"], r["team"])):
            grp = list(grp)
            for r in grp:
                if not (self.variant and zero_usage(r)):
                    self.hist[r["player_id"]].append(props._hist_entry(r))
                self.names[r["player_id"]] = r["name"]
                self.pos[r["player_id"]] = r["position"]
                if r["season"] == SEASON:
                    self.last_week[r["player_id"]] = (r["week"], r["team"], r["name"])
            self.teams.record(grp[0]["team"], {r["player_id"] for r in grp})
        return self

    def price(self, pid, stat, line, implied, injuries=None):
        if self.variant and self.pos.get(pid) == "RB":
            orig = props_news.features

            def feat(*a, **k):
                n = orig(*a, **k)
                n["rbc"] = n["R"]["c"]
                return n
            props_news.features = feat
            try:
                return super().price(pid, stat, line, implied, injuries)
            finally:
                props_news.features = orig
        return super().price(pid, stat, line, implied, injuries)


class WeekInjuries:
    """nflverse's injury report for that week, in the live Injuries interface (live used ESPN + reporter news, not kept)."""

    def __init__(self, path, season, week, names):
        import duckdb
        self.status = {}
        for gid, team, st in duckdb.connect().execute(
                f"SELECT gsis_id, team, report_status FROM read_parquet('{path}') WHERE season={season} AND week={week} "
                "AND report_status IN ('Out','Doubtful','Questionable')").fetchall():
            if gid in names:
                self.status[(props.norm_name(names[gid]), team)] = st

    def of(self, name, team):
        return self.status.get((props.norm_name(name), team), "")


def ll(p, y):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def blend(R, k):
    n = len(R)
    base = sum(ll(r["mkt"], r["y"]) for r in R) / n
    own = sum(ll(r[k], r["y"]) for r in R) / n
    best = min((sum(ll(r["mkt"] + w / 20 * (r[k] - r["mkt"]), r["y"]) for r in R) / n, w / 20) for w in range(21))
    return base, own, best


def week_of(gday: date, rows) -> int:
    import duckdb
    return duckdb.connect().execute(f"SELECT max(week) FROM read_csv_auto('{props.GAMES_CSV}') WHERE season={SEASON} AND gameday=?",
                                    [gday]).fetchone()[0]


def part1(rows, out_reports, con):
    q = """with g as (select *, row_number() over (partition by player_id,stat,home,away,line order by ts_utc) rf
      from prop_evals where coalesce(sport,'NFL')='NFL' and outcome is not null and outcome<>line and market_p_over is not null
      and model_p_over is not null and over_price is not null and under_price is not null)
    select ts_utc, start_utc, away, home, player, player_id, team, stat, line, market_p_over, model_p_over, outcome, through_week, season
    from g where rf=1 order by ts_utc"""
    seen, props_ = set(), []
    for r in con.execute(q).fetchall():
        k = (r[5], r[7], r[3])
        if k not in seen:
            seen.add(k)
            props_.append(r)
    cur, var = CutModel(rows, out_reports, False), CutModel(rows, out_reports, True)
    inj_path = props.RAW / f"injuries_{SEASON}.parquet"
    res, miss = [], 0
    for ts, start, away, home, player, pid, team, stat, line, mkt, stored, outcome, tw, season in props_:
        cutoff = ts.replace(tzinfo=timezone.utc).astimezone(EAST).date()
        gday = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(EAST).date()
        imp = props.game_implied(away, home, ts, con)
        if imp is None:
            miss += 1
            continue
        teams = (props.TEAM_NAMES.get(away), props.TEAM_NAMES.get(home))
        implied = imp[1] if team == teams[1] else imp[0]
        got = {}
        for name, m in (("cur", cur), ("var", var)):
            if getattr(m, "_cut", None) != cutoff:
                m.cut(cutoff)
                m._cut = cutoff
            inj = WeekInjuries(inj_path, SEASON, week_of(gday, rows), m.names)
            p = m.price(pid, stat, line, implied, inj)
            got[name] = None if (p is None or "skip" in p) else p["p_over"]
        if None in got.values():
            miss += 1
            continue
        res.append({"stat": stat, "player": player, "y": int(outcome > line), "mkt": mkt, "stored": stored,
                    "cur": got["cur"], "var": got["var"], "tw": tw, "cutoff": cutoff})
    return res, miss, len(props_), cur, var


def part2(rows, out_reports):
    """Walk-forward 2023-2026 squared error, as backtest(): each season fitted on earlier seasons only."""
    stats = ("receptions", "targets", "receiving_yards")
    recs = {v: history_projections(rows, out_reports, v) for v in (False, True)}
    out = {s: {"cur": 0.0, "var": 0.0, "n": 0} for s in stats}
    for season in range(2023, SEASON + 1):
        preds = {}
        for v in (False, True):
            R = recs[v]
            train = [r for r in R if props.FIRST_SEASON < r["row"]["season"] < season]
            test = [r for r in R if r["row"]["season"] == season]
            p = {}
            for stat in ("receptions", "receiving_yards"):
                d, a = props.fit_stat(train, stat)
                pool = [r for r in train if d in r["by_decay"] and props.ROLE[stat](r["by_decay"][d][0])]
                npar = props_news.fit([(props._proj_one(r, stat, d, a), r["news"], float(r["row"][stat])) for r in pool], stat) \
                    if stat in props.NEWS_STATS else props_news.NO_NEWS
                for r in test:
                    if d in r["by_decay"] and props.ROLE[stat](r["by_decay"][d][0]):
                        key = (r["row"]["player_id"], r["row"]["game_id"])
                        p[(stat, key)] = (props._proj_one(r, stat, d, a) * props_news.factor(r["news"], stat, npar), float(r["row"][stat]))
                        if stat == "receptions":      # targets: weighted average at the receptions decay, receptions role
                            t = r["by_decay"][d][0]["targets"]
                            if r["news"].get("rbc", 1.0) > 1.0:
                                t *= r["news"]["rbc"] ** POWER
                            p[("targets", key)] = (t, float(r["row"]["targets"]))
            preds[v] = p
        for k in preds[False].keys() & preds[True].keys():     # same player-games for both
            o = out[k[0]]
            o["n"] += 1
            o["cur"] += (preds[False][k][0] - preds[False][k][1]) ** 2
            o["var"] += (preds[True][k][0] - preds[True][k][1]) ** 2
    return out


def main():
    rows = props.load_rows(SEASON)
    out_reports = props.load_out_reports(SEASON)
    con = connect(config.DATA / "engine.duckdb", read_only=True)
    res, miss, total, cur, var = part1(rows, out_reports, con)
    n = len(res)
    print(f"PART 1: {total} first-seen graded NFL props; priced by both {n}; dropped {miss}")
    print(f"  fitted beta (role power): carries {cur.news_params['carries'][1]}, rushing_yards {cur.news_params['rushing_yards'][1]}, "
          f"receptions {cur.news_params['receptions'][1]}")
    diffs = [abs(r["cur"] - r["stored"]) for r in res]
    print(f"  recompute vs stored model_p_over: within .005 {sum(d <= .005 for d in diffs)}/{n}, within .02 {sum(d <= .02 for d in diffs)}/{n}, "
          f"mean abs diff {sum(diffs) / n:.4f}, through_week values {sorted({r['tw'] for r in res})}, cutoffs {sorted({str(r['cutoff']) for r in res})}")
    bad = sorted(res, key=lambda r: -abs(r["cur"] - r["stored"]))[:8]
    for r in bad:
        print(f"    mismatch {r['player']} {r['stat']} stored {r['stored']:.3f} recomputed {r['cur']:.3f}")
    for label, R in (("all", res), ("excluding fg_made", [r for r in res if r["stat"] != "fg_made"]),
                     ("receptions+receiving_yards", [r for r in res if r["stat"] in RB_STATS])):
        if not R:
            continue
        b, oc, bc = blend(R, "cur")
        _, ov, bv = blend(R, "var")
        _, os_, bs = blend(R, "stored")
        print(f"  [{label}] n={len(R)} logloss pinnacle={b:.4f} current={oc:.4f} (best w {bc[1]:.2f}, {bc[0]:.4f}) "
              f"variant={ov:.4f} (best w {bv[1]:.2f}, {bv[0]:.4f}) stored={os_:.4f} (best w {bs[1]:.2f})")
    changed = [r for r in res if abs(r["var"] - r["cur"]) > 1e-9]
    print(f"  props where the variant moved P(over): {len(changed)}")
    b, oc, bc = blend(res, "cur")
    _, ov, bv = blend(res, "var")
    p1 = ov < oc and bv[1] > 0.15
    print(f"  PART 1 {'PASS' if p1 else 'FAIL'} (variant {ov:.4f} < current {oc:.4f}: {ov < oc}; variant best weight {bv[1]:.2f} > 0.15: {bv[1] > 0.15})")

    # Coleman, receptions over 3.5, DEN Nov 27
    row = con.execute("""select ts_utc, start_utc, away, home, player_id, team, line, model_p_over, market_p_over from prop_evals
        where player='Jonah Coleman' and stat='receptions' and line=3.5 and start_utc like '2026-11-27%' order by ts_utc desc limit 1""").fetchone()
    if row:
        ts, start, away, home, pid, team, line, stored, mkt = row
        gday = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(EAST).date()
        imp = props.game_implied(away, home, ts, con)
        teams = (props.TEAM_NAMES.get(away), props.TEAM_NAMES.get(home))
        implied = imp[1] if team == teams[1] else imp[0]
        out = {}
        for name, m in (("current", cur), ("variant", var)):
            m.cut(gday)
            inj = WeekInjuries(props.RAW / f"injuries_{SEASON}.parquet", SEASON, week_of(gday, rows), m.names)
            out[name] = m.price(pid, "receptions", line, implied, inj)
        print(f"COLEMAN receptions o3.5 (latest read {ts}): stored model {stored}, Pinnacle no-vig {mkt}; "
              f"current {out['current']}; variant {out['variant']}")

    res2 = part2(rows, out_reports)
    p2 = True
    print("PART 2 (2023-2026 held-out, same player-games for both):")
    for s, o in res2.items():
        c, v = o["cur"] / o["n"], o["var"] / o["n"]
        worse = (v - c) / c
        p2 &= worse <= 0.005
        print(f"  {s}: n={o['n']} mse current={c:.4f} variant={v:.4f} change {worse:+.2%}")
    print(f"  PART 2 {'PASS' if p2 else 'FAIL'}")
    print(f"VERDICT: {'PASS' if p1 and p2 else 'FAIL'}")


if __name__ == "__main__":
    main()
