"""Command line entry point: `engine <command>`."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from engine import config
from engine.odds import snapshots as _db

ROOT, DATA = config.ROOT, config.DATA
MASTER = DATA / "raw" / "wagerhouse_graded_master.json"


def _history_file(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit)
    if MASTER.exists():
        return MASTER
    return max((DATA / "raw").glob("wagerhouse_graded_wagers_pull_*.json"), default=None)


def _audit(pull: Path, week: str | None = None):
    from engine.bets import audit
    from engine.bets.history import load_wagers, weekly_figures

    cfg = config.load_config()
    wagers = load_wagers(pull)
    figures = weekly_figures(pull)
    if week:
        wagers = [w for w in wagers if w.week == week]
        figures = {k: v for k, v in figures.items() if k == week}
    priced = audit.price_all(wagers, cfg["margin_sd"], DATA / "raw" / "espn")
    return cfg, wagers, priced, figures


def cmd_audit(args) -> int:
    from engine.bets import store
    from engine.reports import audit_report

    pull = _history_file(args.history)
    if pull is None or not pull.exists():
        print("No history found in data.nosync/raw/. Run `engine sync` first.", file=sys.stderr)
        return 2
    cfg, wagers, priced, figures = _audit(pull)
    store.save_audit(config.DB, wagers, priced)
    out = ROOT / "docs" / "research" / "01-bet-audit.md"
    out.write_text(audit_report.build(wagers, priced, figures, cfg, cfg["timezone_display"]))
    print(f"Audited {len(wagers)} wagers from {pull.name}. Report: {out.relative_to(ROOT)}")
    return 0


def cmd_sync(args) -> int:
    """Pull recent graded bets from the account and fold them into the history."""
    from engine.bets.history import merge_pull
    from engine.odds.wagerhouse import Wagerhouse

    env = config.load_env()
    master = json.loads(MASTER.read_text()) if MASTER.exists() else None
    if master is None:
        seed = _history_file(None)
        if seed:
            master = merge_pull(None, json.loads(seed.read_text()))
    wh = Wagerhouse(env.get("WAGERHOUSE_USER", ""), env.get("WAGERHOUSE_PASSWORD", ""))
    pull = wh.graded_pull(weeks=args.weeks)
    merged = merge_pull(master, pull)
    MASTER.parent.mkdir(parents=True, exist_ok=True)
    MASTER.write_text(json.dumps(merged))
    n = len({(r["TicketNumber"], r["WagerNumber"]) for r in merged["rows"]})
    print(f"Synced {args.weeks} week(s). History now holds {n} wagers across {len(merged['weeks'])} weeks.")
    return 0


def cmd_report(args) -> int:
    """Weekly report for one account week (default: the last completed one)."""
    from engine.alerts import telegram
    from engine.bets.history import weekly_figures
    from engine.reports import audit_report

    if not args.no_sync:
        rc = cmd_sync(argparse.Namespace(weeks=2))
        if rc:
            return rc
    pull = _history_file(None)
    weeks = sorted(weekly_figures(pull))
    if not weeks:
        print("No weeks in the history.", file=sys.stderr)
        return 2
    week = args.week or (weeks[-2] if len(weeks) > 1 else weeks[-1])
    cfg, wagers, priced, figures = _audit(pull, week)
    if not wagers:
        print(f"No graded wagers in the week of {week}.")
        return 0
    text = audit_report.build(wagers, priced, figures, cfg, cfg["timezone_display"], title=f"Weekly report: week of {week}")
    out = DATA / "reports" / f"weekly_{week}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"Report: {out}")
    summary = text.split("## Bottom line\n", 1)[1].split("\n## ", 1)[0].replace("**", "").strip()
    from engine.odds import snapshots as snap
    from engine.picks import grade
    gcon = snap.connect(config.DB)
    try:
        engine_lines = grade.summary(gcon, cfg)
    finally:
        gcon.close()
    msg = (f"Week of {week}\n{summary}\n\nThe engine's own picks (all time):\n" + "\n".join(engine_lines)
           + f"\n\nFull report: data.nosync/reports/weekly_{week}.md")
    if args.no_send:
        print(msg)
    else:
        telegram.send(config.load_env(), msg)
    return 0


def cmd_poll(args) -> int:
    from engine import poll

    code, lines = poll.run(force=args.force, send_alerts=not args.no_send)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    for line in lines:
        print(f"{stamp} {line}")
    return code


def cmd_book(args) -> int:
    from engine.odds import snapshots
    from engine.reports import book_report

    con = snapshots.connect(config.DB)
    try:
        print(book_report.build(con))
    finally:
        con.close()
    return 0


def cmd_telegram_setup(args) -> int:
    from engine.alerts import telegram

    env = config.load_env()
    chat = telegram.find_chat_id(env.get("TELEGRAM_BOT_TOKEN", ""))
    if not chat:
        print("The bot has no messages yet. Open Telegram, send your bot any message, and run this again.", file=sys.stderr)
        return 2
    config.set_env_value("TELEGRAM_CHAT_ID", chat)
    telegram.send(config.load_env(), "Betting engine connected. Alerts will arrive here.")
    print("Chat id saved and a test message sent.")
    return 0


def cmd_watch(args) -> int:
    from engine.bets.parser import parse
    from engine.odds import snapshots

    con = snapshots.connect(config.DB)
    try:
        if args.action == "add":
            t = parse(" ".join(args.text))
            target = t.line if t.market != "ml" else t.price
            if target is None:
                raise ValueError("a moneyline watch needs a price, e.g. `Bills ML -150`")
            worst = t.price if t.market != "ml" else None
            nid = con.execute("SELECT coalesce(max(id), 0) + 1 FROM watchlist").fetchone()[0]
            con.execute("INSERT INTO watchlist VALUES (?,?,?,?,?,?,?,?)",
                        [nid, datetime.now(timezone.utc).replace(tzinfo=None), t.team, t.market, target, worst, "", True])
            print(f"Watching #{nid}: {t.team} {t.market} {target:+g} or better" + (f", price {worst:+g} or better" if worst else ""))
        elif args.action == "remove":
            con.execute("UPDATE watchlist SET active = false WHERE id = ?", [int(args.text[0])])
            print(f"Removed #{args.text[0]}")
        else:
            rows = con.execute("SELECT id, team, market, target, worst_price FROM watchlist WHERE active ORDER BY id").fetchall()
            print("\n".join(f"#{r[0]} {r[1]} {r[2]} {r[3]:+g}" + (f" (price {r[4]:+g} or better)" if r[4] else "") for r in rows) or "Watchlist is empty.")
    finally:
        con.close()
    return 0


def cmd_bet_add(args) -> int:
    from engine.bets.parser import parse
    from engine.odds import snapshots

    raw = " ".join(args.text)
    t = parse(raw)
    cfg = config.load_config()
    con = snapshots.connect(config.DB)
    try:
        con.execute("INSERT INTO manual_bets VALUES (?,?,?,?,?,?,?,?)",
                    [datetime.now(timezone.utc).replace(tzinfo=None), raw, t.team, t.market, t.line, t.price, t.stake, args.note or ""])
    finally:
        con.close()
    cap = cfg["unit"] * cfg["max_units"]
    print(f"Logged: {t.team} {t.market} {'' if t.line is None else format(t.line, '+g')} {'' if t.price is None else format(t.price, '+g')} ${t.stake or 0:g}")
    if t.stake and t.stake > cap:
        print(f"Over the cap: ${t.stake:g} is more than {cfg['max_units']} units (${cap}).")
    return 0


def cmd_slate(args) -> int:
    """Build the slate sheet: every number for every game, from live prices."""
    from engine.picks import slate

    sheet = slate.build(args.sport, days_ahead=args.days)
    path = slate.save(sheet)
    flagged = [(g["game"], s["pick"], s["value"]) for g in sheet["games"] for m in g["markets"]
               for s in m.get("sides", []) if s["numbers_say_bet"]]
    print(f"Slate sheet: {path}")
    print(f"{args.sport}: {len(sheet['games'])} games priced. The numbers flag {len(flagged)} side(s) for a second look:")
    for game, pick, val in flagged:
        print(f"  {pick}  ({game})  {100 * val:+.1f}% per $1")
    for pr in sheet["problems"]:
        print(f"  NOTE: {pr}")
    return 0


def cmd_agent(args) -> int:
    from engine.picks import agent, slate

    sports = list(slate.SPORTS) if args.sport == "all" else [args.sport]
    worst = 0
    for sport in sports:
        code, lines = agent.run(args.reason, send=not args.no_send, skip_research=args.skip_research, sport=sport)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        for line in lines:
            print(f"{stamp} {line}")
        worst = max(worst, code)
    return worst


def cmd_totals_test(args) -> int:
    """Walk-forward test: does the pace-and-efficiency totals model add anything to the market's total?"""
    import csv
    import io

    from engine.picks import sources, totals

    rows = sources.nfl_games(DATA / "raw" / "nflverse_games.csv")
    closes = {r["game_id"]: (float(r["total_line"]), float(r["total"])) for r in rows
              if r["total_line"] not in ("", None) and r["total"] not in ("", None) and r["game_type"] == "REG"}
    year = max(int(r["season"]) for r in rows if r["total"] not in ("", None))
    res = totals.backtest(list(range(year - 4, year + 1)), year, closes)
    print(f"{res['games']} games, weeks 5 and later, {year - 4} to {year}.")
    print(f"Average miss: market {res['mae_close']:.2f} points, model {res['mae_model']:.2f}.")
    print(f"Best blend puts {100 * res['best_market_weight']:.0f}% on the market.")
    for gap, (w, n) in res["bets"].items():
        print(f"Betting the model's side when it disagreed by {gap}+ points: {w}-{n - w} ({100 * w / n:.1f}%; break-even is 52.4%).")
    return 0


def cmd_matchup(args) -> int:
    """Side-by-side play-by-play numbers for two NFL teams (use nflverse abbreviations, e.g. TEN DAL)."""
    from engine.picks import matchup

    mu, pw = matchup.current(datetime.now(timezone.utc))
    a, b = args.away.upper(), args.home.upper()
    for t in (a, b):
        if t not in mu:
            print(f"Unknown team {t}. Known: {' '.join(sorted(mu))}", file=sys.stderr)
            return 2
    print(matchup.sheet(mu, a, b))
    pm = matchup.power_margin(pw, b, a, config.load_config()["picks"]["home_field"]["NFL"])
    print(f"\nEngine's own play-by-play number: {b} by {pm:+.1f} at home (context only; it did not beat the closing spread in testing).")
    return 0


def cmd_spread_test(args) -> int:
    """Walk-forward test of the engine's own power number against closing spreads."""
    from engine.picks import matchup, sources

    rows = sources.nfl_games(DATA / "raw" / "nflverse_games.csv")
    closes = {r["game_id"]: (float(r["spread_line"]), float(r["result"])) for r in rows
              if r["spread_line"] not in ("", None) and r["result"] not in ("", None) and r["game_type"] == "REG"}
    year = max(int(r["season"]) for r in rows if r["result"] not in ("", None))
    res = matchup.spread_backtest(list(range(year - 4, year + 1)), year, closes, config.load_config()["picks"]["home_field"]["NFL"])
    print(f"{res['games']} games. Average miss: market {res['mae_close']:.2f}, own number {res['mae_model']:.2f}.")
    print(f"Best blend puts {100 * res['best_market_weight_all']:.0f}% on the market.")
    for gap, (w, n) in res["ats"].items():
        print(f"Betting the own number's side at a {gap}+ point gap: {w}-{n - w} ({100 * w / n:.1f}%; break-even 52.4%).")
    return 0


def cmd_model_test(args) -> int:
    """Walk-forward tests of the candidate models on seasons they never saw (docs/research/05-model-first-picks.md)."""
    import json

    if args.model == "wind":
        from engine.models import wind_totals
        r = wind_totals.run(forecast_check=True)
        b, k = r["fit_all_before_2019"]
        print(f"{r['games_with_weather']} outdoor games with weather. Fitted on 2010-2018: {b:+.3f} points per mph above {k:g} mph.")
        h = r["held_out"]
        print(f"Held out 2019 on ({h['games']} games): average squared miss, close {h['mse_close']}, close plus wind {h['mse_model']}.")
        for x in h["records"]:
            print(f"  Unders where the model is {x['threshold']:g}+ below the close: {x['won']}-{x['lost']} ({100 * (x['win_rate'] or 0):.1f}%; break-even 52.4%), {x['units_at_110']:+} units")
        for s in h["per_season"]:
            x = s["under_1"]
            print(f"  {s['season']}: {x['won']}-{x['lost']}")
        if "forecast_vs_reanalysis" in r:
            f = r["forecast_vs_reanalysis"]
            print(f"Day-before forecast vs actual wind, {f['games']} games since 2024: off by {f['mean_abs_gap_mph']} mph on average, correlation {f['correlation']}.")
            for x in r["held_out_with_forecast"]["records"]:
                print(f"  Using the forecast, {x['threshold']:g}+: {x['won']}-{x['lost']}, {x['units_at_110']:+} units")
    elif args.model == "first-half":
        from engine.models import first_half
        print(json.dumps(first_half.run(), indent=1))
    elif args.model == "openers":
        from engine.models import openers
        for league in ("NFL", "College"):
            for source in ("close", "result"):
                for lag in (0, 7):
                    print(f"\n{league}: our number from earlier {'closing lines' if source == 'close' else 'final scores'}"
                          f"{', opener assumed a week earlier' if lag else ''}")
                    for kind, res in openers.run(league, source, lag).items():
                        for t, bets in res["bets"].items():
                            x = openers.summarize(bets)
                            if x["n"]:
                                print(f"  {kind} gap {t:g}+: {x['won']}-{x['lost']} at the opener ({100 * x['pct']:.1f}%), "
                                      f"{x['units']:+.1f} units, line moved our way {x['moved_our_way']} / against {x['moved_against']}, "
                                      f"average {x['avg_clv']:+.2f} points")
    return 0


def cmd_props(args) -> int:
    """Price the latest Pinnacle NFL props with the props model, grade finished ones, write the testing sheet."""
    import duckdb

    from engine.models import props

    now = datetime.now(timezone.utc)
    cfg = config.load_config()
    pc = (cfg.get("models") or {}).get("props") or {}
    if args.sport == "NBA":
        from engine.models import nba_props
        con = _db.connect(config.DB)
        m = nba_props.NbaModel(now)
        rows = nba_props.evaluate_logged(con, m, now)
        graded = nba_props.grade(con)
        sc = props.scorecard(con, pc.get("edge", 0.05), sport="NBA")
        path = props.write_sheet(rows, sc, pc, m, now, sport="NBA", about=nba_props.ABOUT, kinds=nba_props.KIND)
        con.close()
        print(f"Props sheet: {path}")
        print(f"Priced {len(rows)} NBA props from the latest Pinnacle read (box scores through {m.through}); graded {graded} new.")
        print(props.gate_line(sc, pc))
        return 0
    m = props.Model(now.year if now.month >= 3 else now.year - 1)
    con = _db.connect(config.DB)
    rows = props.evaluate_logged(con, m, now)
    graded = props.grade(con, m.season)
    sc = props.scorecard(con, pc.get("edge", 0.05))
    path = props.write_sheet(rows, sc, pc, m, now)
    con.close()
    print(f"Props sheet: {path}")
    print(f"Priced {len(rows)} props from the latest Pinnacle read (stats through week {m.through_week}); graded {graded} new.")
    print(props.gate_line(sc, pc))
    return 0


def cmd_nba_history(args) -> int:
    """Download (or top up) NBA box scores and closing lines from ESPN, for the NBA props model."""
    from engine.models import nba_data

    n = nba_data.download()
    print(f"Fetched {n} new NBA games; {len(nba_data.load())} on disk.")
    return 0


def cmd_nba_props_test(args) -> int:
    """Held-out test of the NBA props model, with and without the minutes/injury terms."""
    from engine.models import nba_props

    for stat, v in nba_props.backtest().items():
        print(f"{stat}: {v['base']['player_games']} player-games. Probability score: plain average {v['plain']['brier']}, "
              f"base {v['base']['brier']}, with news {v['news']['brier']}; on games news changed ({v['news_when_news']['player_games']}): "
              f"{v['base_when_news']['brier']} -> {v['news_when_news']['brier']}. Latest fit: {list(v['params'].values())[-1] if v['params'] else ''}")
    return 0


def cmd_props_test(args) -> int:
    """Held-out test of the props model (2023 on): accuracy against a plain average and honesty of its probabilities."""
    from engine.models import props

    r = props.backtest(2023)
    for stat, v in r.items():
        cal = max(abs(c["said"] - c["happened"]) for c in v["calibration"]) if v["calibration"] else None
        print(f"{stat}: {v['player_games']} player-games. Typical miss {v['mae_model']} vs {v['mae_plain_average']} for a plain average; "
              f"probability score {v['brier_model']} vs {v['brier_plain_average']} (lower is better); worst calibration gap {cal:.3f}.")
    return 0


def cmd_nba_watch(args) -> int:
    """NBA injury watcher: news for players who matter, lines at your book and Pinnacle, research run."""
    from engine.picks import nba_news

    code, lines = nba_news.run(force=args.force, send=not args.dry_run)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    for line in lines:
        print(f"{stamp} {line}")
    return code


def cmd_reporters(args) -> int:
    """Which listed reporters (ops/reporters.yaml) actually reached the engine through Rotoworld lately."""
    import duckdb

    from engine.picks import player_news

    con = _db.connect(config.DB)
    now = datetime.now(timezone.utc)
    for sport in ("NFL", "NBA"):
        try:
            player_news.update(con, sport, now)
        except Exception as e:
            print(f"{sport}: Rotoworld read failed: {e}")
        c = player_news.coverage(con, sport, now, args.days)
        print(f"{sport}: {c['posts']} relayed posts in {args.days} days; by source: {c['by_kind']}. "
              f"{c['listed_seen']} of {c['listed']} listed reporters seen.")
        if c["top"]:
            print("  most relayed: " + ", ".join(f"{n} ({k})" for n, k in c["top"]))
        print(f"  not seen yet ({len(c['never_seen'])}): " + ", ".join(c["never_seen"][:40]) + (" ..." if len(c["never_seen"]) > 40 else ""))
    con.close()
    return 0


def cmd_board(args) -> int:
    """Rebuild the picks page and open it in the browser."""
    import subprocess

    from engine.picks import board

    path = board.build()
    print(f"Board: {path}")
    if not args.no_open:
        subprocess.run(["open", str(path)], check=False)
    return 0


def cmd_injuries(args) -> int:
    from engine.picks import news

    players = news.fetch(args.sport)
    for p in sorted(players, key=lambda p: (p.team, p.pos != "QB", p.name)):
        if not args.all and args.sport == "NFL" and p.pos != "QB":
            continue
        if args.sport != "NFL" and p.status == "Active":
            continue
        if args.team and args.team.lower() not in p.team.lower():
            continue
        if args.all and p.status == "Active":
            continue
        print(f"{p.team} | {p.pos} {p.name} | {p.status} | {p.updated} | {p.comment[:220]}")
    return 0


def cmd_card(args) -> int:
    """Render the card from the latest slate sheet and the decisions file."""
    import json as _json

    from engine.picks import agent, card

    cfg = config.load_config()
    sheet_path = DATA / "slates" / f"{args.sport}_latest.json"
    if not sheet_path.exists():
        print(f"No {args.sport} slate sheet yet. Run `engine slate --sport {args.sport}` first.", file=sys.stderr)
        return 2
    sheet = _json.loads(sheet_path.read_text())
    day = args.date or datetime.now(config.display_tz(cfg)).strftime("%Y-%m-%d")
    dpath = agent.decisions_path(day, args.sport)
    if not dpath.exists():
        print(f"No decisions file at {dpath.relative_to(ROOT)}.", file=sys.stderr)
        return 2
    decisions, note = card.load_decisions(dpath)
    text, rows = card.build(sheet, decisions, note, cfg)
    out = agent.card_path(day, args.sport)
    out.write_text(text)
    print(f"Card: {out.relative_to(ROOT)}  ({sum(r['status'] == 'Bet' for r in rows)} bets, "
          f"{sum(r['status'] == 'Conditional' for r in rows)} conditional, {sum(r['status'] == 'Pass' for r in rows)} passed)")
    return 0


def cmd_grade(args) -> int:
    from engine.odds import snapshots as snap
    from engine.picks import grade

    cfg = config.load_config()
    con = snap.connect(config.DB)
    try:
        for line in grade.run(cfg, con):
            print(line)
        print("--")
        for line in grade.summary(con, cfg):
            print(line)
    finally:
        con.close()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="price every graded bet against closing lines and write the report")
    a.add_argument("--history", help="path to a history file (default: the synced history)")
    a.set_defaults(func=cmd_audit)
    a = sub.add_parser("sync", help="pull recent graded bets from the account (read-only)")
    a.add_argument("--weeks", type=int, default=2)
    a.set_defaults(func=cmd_sync)
    a = sub.add_parser("report", help="weekly report, sent to Telegram")
    a.add_argument("--week", help="first day of the account week, e.g. 2026-11-10")
    a.add_argument("--no-sync", action="store_true")
    a.add_argument("--no-send", action="store_true")
    a.set_defaults(func=cmd_report)
    a = sub.add_parser("poll", help="read lines and send alerts (the scheduled job runs this)")
    a.add_argument("--force", action="store_true", help="read now even outside the scheduled hours")
    a.add_argument("--no-send", action="store_true", help="print alerts instead of sending them")
    a.set_defaults(func=cmd_poll)
    a = sub.add_parser("book", help="how Wagerhouse compares with the market so far")
    a.set_defaults(func=cmd_book)
    a = sub.add_parser("slate", help="build the slate sheet: fair lines and edges for every NFL game")
    a.add_argument("--days", type=int, default=None)
    a.add_argument("--sport", choices=["NFL", "College", "NBA"], default="NFL")
    a.set_defaults(func=cmd_slate)
    a = sub.add_parser("agent", help="research run: numbers, Claude research and decisions, card, pick alerts")
    a.add_argument("--reason", default="manual run")
    a.add_argument("--sport", choices=["NFL", "College", "NBA", "all"], default="all")
    a.add_argument("--no-send", action="store_true", help="print alerts instead of sending them")
    a.add_argument("--skip-research", action="store_true", help="re-price the existing decisions without a new research run")
    a.set_defaults(func=cmd_agent)
    a = sub.add_parser("totals-test", help="test the NFL totals model against the market's closing totals")
    a.set_defaults(func=cmd_totals_test)
    a = sub.add_parser("matchup", help="play-by-play matchup numbers for two NFL teams: matchup TEN DAL (away home)")
    a.add_argument("away")
    a.add_argument("home")
    a.set_defaults(func=cmd_matchup)
    a = sub.add_parser("spread-test", help="test the engine's own NFL power number against closing spreads")
    a.set_defaults(func=cmd_spread_test)
    a = sub.add_parser("model-test", help="walk-forward test of a candidate model: wind, first-half or openers")
    a.add_argument("model", choices=["wind", "first-half", "openers"])
    a.set_defaults(func=cmd_model_test)
    a = sub.add_parser("props", help="props model vs Pinnacle's props: price, grade, write the testing sheet")
    a.add_argument("--sport", choices=["NFL", "NBA"], default="NFL")
    a.set_defaults(func=cmd_props)
    a = sub.add_parser("nba-history", help="download or top up NBA box scores and closing lines (ESPN)")
    a.set_defaults(func=cmd_nba_history)
    a = sub.add_parser("nba-props-test", help="held-out test of the NBA props model")
    a.set_defaults(func=cmd_nba_props_test)
    a = sub.add_parser("props-test", help="held-out test of the props model")
    a.set_defaults(func=cmd_props_test)
    a = sub.add_parser("nba-watch", help="NBA injury watcher (launchd runs it every 10 minutes)")
    a.add_argument("--force", action="store_true", help="run outside the watch hours")
    a.add_argument("--dry-run", action="store_true", help="print, do not message or start a research run")
    a.set_defaults(func=cmd_nba_watch)
    a = sub.add_parser("reporters", help="which listed reporters reached the engine through Rotoworld lately")
    a.add_argument("--days", type=int, default=7)
    a.set_defaults(func=cmd_reporters)
    a = sub.add_parser("board", help="rebuild the picks page (board.html) and open it")
    a.add_argument("--no-open", action="store_true")
    a.set_defaults(func=cmd_board)
    a = sub.add_parser("injuries", help="current NFL injury statuses (quarterbacks by default)")
    a.add_argument("--all", action="store_true", help="every position, not only quarterbacks")
    a.add_argument("--team", help="filter by team name")
    a.add_argument("--sport", choices=["NFL", "NBA"], default="NFL")
    a.set_defaults(func=cmd_injuries)
    a = sub.add_parser("card", help="render the card from the slate sheet and the decisions file")
    a.add_argument("--date", help="card date, e.g. 2026-11-22 (default: today, Mountain)")
    a.add_argument("--sport", choices=["NFL", "College", "NBA"], default="NFL")
    a.set_defaults(func=cmd_card)
    a = sub.add_parser("grade", help="grade the engine's own picks on result and against Pinnacle's close")
    a.set_defaults(func=cmd_grade)
    a = sub.add_parser("telegram-setup", help="find the chat id and send a test message")
    a.set_defaults(func=cmd_telegram_setup)
    a = sub.add_parser("watch", help='watchlist: add "Kansas State +10", list, remove 3')
    a.add_argument("action", choices=["add", "list", "remove"])
    a.add_argument("text", nargs="*")
    a.set_defaults(func=cmd_watch)
    a = sub.add_parser("bet", help='log a bet by hand: bet add "Kansas State +10 -110 25"')
    a.add_argument("action", choices=["add"])
    a.add_argument("text", nargs="+")
    a.add_argument("--note")
    a.set_defaults(func=cmd_bet_add)
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:
        from engine.odds.espn import SourceError
        if isinstance(e, (SourceError, ValueError, PermissionError)):
            print(f"FAILED: {e}", file=sys.stderr)
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(main())
