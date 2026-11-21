"""Command line entry point: `engine <command>`."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from engine import config

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
    msg = f"Week of {week}\n{summary}\n\nFull report: data.nosync/reports/weekly_{week}.md"
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

    sheet = slate.build_nfl(days_ahead=args.days)
    path = slate.save(sheet)
    flagged = [(g["game"], s["pick"], s["value"]) for g in sheet["games"] for m in g["markets"]
               for s in m.get("sides", []) if s["numbers_say_bet"]]
    print(f"Slate sheet: {path}")
    print(f"{len(sheet['games'])} games. The numbers flag {len(flagged)} side(s) for a second look:")
    for game, pick, val in flagged:
        print(f"  {pick}  ({game})  {100 * val:+.1f}% per $1")
    for pr in sheet["problems"]:
        print(f"  PROBLEM: {pr}")
    return 0


def cmd_card(args) -> int:
    """Render the card from the latest slate sheet and the decisions file."""
    import json as _json

    from engine.picks import card

    cfg = config.load_config()
    sheet_path = DATA / "slates" / "NFL_latest.json"
    if not sheet_path.exists():
        print("No slate sheet yet. Run `engine slate` first.", file=sys.stderr)
        return 2
    sheet = _json.loads(sheet_path.read_text())
    day = args.date or datetime.fromisoformat(sheet["games"][0]["start_utc"]).astimezone(config.display_tz(cfg)).strftime("%Y-%m-%d")
    dpath = ROOT / "docs" / "cards" / "decisions" / f"{day}-nfl.yaml"
    if not dpath.exists():
        print(f"No decisions file at {dpath.relative_to(ROOT)}.", file=sys.stderr)
        return 2
    decisions, note = card.load_decisions(dpath)
    text, rows = card.build(sheet, decisions, note, cfg)
    out = ROOT / "docs" / "cards" / f"{day}.md"
    out.write_text(text)
    print(f"Card: {out.relative_to(ROOT)}  ({sum(r['status'] == 'Bet' for r in rows)} bets, "
          f"{sum(r['status'] == 'Conditional' for r in rows)} conditional, {sum(r['status'] == 'Pass' for r in rows)} passed)")
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
    a.add_argument("--days", type=int, default=3)
    a.set_defaults(func=cmd_slate)
    a = sub.add_parser("card", help="render the card from the slate sheet and the decisions file")
    a.add_argument("--date", help="card date, e.g. 2026-11-22 (default: first game on the sheet)")
    a.set_defaults(func=cmd_card)
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
