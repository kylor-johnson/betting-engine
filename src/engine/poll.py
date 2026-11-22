"""One scheduled read: collect lines, store them, decide and send alerts."""
from __future__ import annotations

import traceback
from datetime import datetime, timedelta, timezone

from engine import config
from engine.alerts import rules, telegram
from engine.odds import snapshots as snap
from engine.odds.espn import SourceError
from engine.odds.wagerhouse import Wagerhouse


def due(cfg: dict, now: datetime, last_ok: datetime | None) -> bool:
    """True when this half-hourly wake-up should actually read lines."""
    local = now.astimezone(config.display_tz(cfg))
    hours = cfg["read_hours"]["sunday" if local.weekday() == 6 else "other"]
    if local.hour not in hours:
        return False
    return last_ok is None or (now - last_ok) > timedelta(minutes=45)


def _deliver(con, env: dict, alerts: list[rules.Alert], now: datetime, out: list[str]) -> None:
    for a in alerts:
        if con.execute("SELECT 1 FROM alerts_sent WHERE key=?", [a.key]).fetchone():
            continue
        delivered = True
        try:
            telegram.send(env, a.text)
        except SourceError as e:
            delivered = False
            out.append(f"NOT SENT ({e}): {a.text}")
        else:
            out.append(a.text)
        con.execute("INSERT INTO alerts_sent VALUES (?,?,?,?,?)", [a.key, now.replace(tzinfo=None), a.kind, a.text, delivered])


def run(force: bool = False, send_alerts: bool = True) -> tuple[int, list[str]]:
    """Returns (exit code, lines to print)."""
    cfg, env = config.load_config(), config.load_env()
    now = datetime.now(timezone.utc)
    con = snap.connect(config.DB)
    out: list[str] = []
    try:
        last_ok = snap.last_ok_poll(con)
        if not force and not due(cfg, now, last_ok):
            return 0, ["Nothing read: outside the scheduled hours, or a read already ran in the last 45 minutes."]
        gap = rules.missed_reads(last_ok, now, cfg["missed_read_alert_hours"] + 12)
        if gap and send_alerts:
            _deliver(con, env, [rules.Alert(f"gap|{last_ok.isoformat()}", "gap", gap)], now, out)
        try:
            wh = Wagerhouse(env.get("WAGERHOUSE_USER", ""), env.get("WAGERHOUSE_PASSWORD", ""))
            snaps, problems = snap.collect(wh, cfg["sports"], now)
        except Exception as e:  # fail loudly: record it, alert, exit non-zero
            msg = str(e) if isinstance(e, (SourceError, PermissionError)) else f"{type(e).__name__}: {e}"
            con.execute("INSERT INTO polls VALUES (?,?,?,?,?)", [now.replace(tzinfo=None), False, 0, 0, msg])
            if not isinstance(e, SourceError):
                out.append(traceback.format_exc())
            if send_alerts:
                _deliver(con, env, [rules.Alert(f"fail|{now.isoformat()}", "failure", f"Line read FAILED: {msg}")], now, out)
            else:
                out.append(f"Line read FAILED: {msg}")
            return 1, out

        wh_now = {s.event_id: s for s in snaps if s.source == snap.WH}
        mk_now = {s.event_id: s for s in snaps if s.source == snap.MKT}
        alerts: list[rules.Alert] = []
        new_by_sport: dict[str, list] = {}
        day_ago = now - timedelta(hours=24)
        for eid, w in wh_now.items():
            prior_wh = snap.history(con, eid, snap.WH)
            if not prior_wh:
                new_by_sport.setdefault(w.sport, []).append(w)
            m = mk_now.get(eid)
            if m is not None:
                prior_mk = [s for s in snap.history(con, eid, snap.MKT) if s.ts >= day_ago]
                prior_w = [s for s in prior_wh if s.ts >= day_ago]
                alerts += rules.off_market(w, m, cfg, prior_mk[0] if prior_mk else None, prior_w[0] if prior_w else None)
        entries = [dict(zip(("id", "team", "market", "target", "worst_price"), r)) for r in con.execute(
            "SELECT id, team, market, target, worst_price FROM watchlist WHERE active").fetchall()]
        for eid, w in wh_now.items():
            alerts += rules.watchlist_hits(w, mk_now.get(eid), entries)
        first_ever = con.execute("SELECT count(*) FROM line_snapshots").fetchone()[0] == 0
        for sport, new in new_by_sport.items():
            if sport not in cfg.get("opener_messages", ["NFL"]):
                continue          # still stored; just no message for sports the picks engine does not cover
            d = rules.opener_digest(new[:40], mk_now)
            if d and not first_ever:
                alerts.insert(0, d)
        if problems:
            alerts.append(rules.Alert(f"problems|{now:%Y-%m-%d}|{len(problems)}", "problem",
                                      "Problems on this read:\n" + "\n".join(problems[:15])))
        # --- news: quarterback status changes since the last read
        triggers: list[str] = []
        try:
            from engine.picks import news
            changed, first = news.check(con, now)
            for c in [c for c in changed if c.matters]:
                game = next((w for w in wh_now.values() if w.sport == "NFL" and c.player.team in (w.home, w.away)), None)
                lines_txt = ""
                if game is not None:
                    prior = snap.history(con, game.event_id, snap.WH)
                    sharp_now = next((s for s in snaps if s.source == snap.SHARP and s.event_id == game.event_id), None)
                    sharp_prior = snap.history(con, game.event_id, snap.SHARP)
                    book_txt = f"{game.home} {rules.fmt_line(game.home_spread)}" if game.home_spread is not None else "no spread"
                    since = f" (was {rules.fmt_line(prior[-1].home_spread)} last read)" if prior and prior[-1].home_spread is not None else ""
                    lines_txt = f"\n{game.away} at {game.home}. Your book: {book_txt}{since}."
                    if sharp_now is not None and sharp_now.home_spread is not None:
                        was = f", was {rules.fmt_line(sharp_prior[-1].home_spread)}" if sharp_prior and sharp_prior[-1].home_spread is not None else ""
                        lines_txt += f" Pinnacle: {rules.fmt_line(sharp_now.home_spread)}{was}."
                alerts.insert(0, rules.Alert(f"news|{c.player.player_id}|{c.old_status}|{c.player.status}", "news",
                                             "QB NEWS: " + c.text() + lines_txt))
                triggers.append(f"quarterback news: {c.player.team} {c.player.name} {c.old_status or 'not listed'} to {c.player.status}")
            if first:
                out.append("Injury feed: first read stored as the baseline.")
        except SourceError as e:
            problems.append(str(e))
        if not first_ever and new_by_sport.get("NFL"):
            triggers.append(f"Wagerhouse posted {len(new_by_sport['NFL'])} new NFL game(s)")
        if problems:
            alerts = [a for a in alerts if a.kind != "problem"]
            alerts.append(rules.Alert(f"problems|{now:%Y-%m-%d}|{len(problems)}", "problem",
                                      "Problems on this read:\n" + "\n".join(problems[:15])))
        snap.save(con, snaps)
        if triggers and send_alerts:
            from engine.picks import agent
            acfg = cfg.get("agent") or {}
            if acfg.get("run_on_news", True) and agent.cooled_down(con, now, acfg.get("cooldown_minutes", 90)):
                agent.spawn("; ".join(triggers)[:300])
                out.append(f"Started a research run: {'; '.join(triggers)}")
        con.execute("INSERT INTO polls VALUES (?,?,?,?,?)",
                    [now.replace(tzinfo=None), True, len(wh_now), len(mk_now), "; ".join(problems)[:500] or None])
        out.append(f"Read {len(wh_now)} Wagerhouse games, {len(mk_now)} with a market line. {len(alerts)} alert candidates.")
        if send_alerts:
            _deliver(con, env, alerts, now, out)
        else:
            out += [f"[{a.kind}] {a.text}" for a in alerts]
        return 0, out
    finally:
        con.close()
