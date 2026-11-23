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


def scheduled_slot(cfg: dict, now: datetime) -> datetime | None:
    """The scheduled research time that fell in the last 30 minutes, if any (as UTC)."""
    sched = (cfg.get("agent") or {}).get("schedule") or {}
    local = now.astimezone(config.display_tz(cfg))
    for hhmm in sched.get("sunday" if local.weekday() == 6 else "other", []):
        h, m = (int(x) for x in str(hhmm).split(":"))
        slot = local.replace(hour=h, minute=m, second=0, microsecond=0)
        if timedelta(0) <= local - slot < timedelta(minutes=30):
            return slot.astimezone(timezone.utc)
    return None


def _deliver(con, env: dict, alerts: list[rules.Alert], now: datetime, out: list[str]) -> None:
    for a in alerts:
        if con.execute("SELECT 1 FROM alerts_sent WHERE key=?", [a.key]).fetchone():
            continue
        delivered = True
        try:
            sent = telegram.send(env, a.text, kind="system" if a.kind in ("gap", "failure") else "info")
        except SourceError as e:
            delivered = False
            out.append(f"NOT SENT ({e}): {a.text}")
        else:
            out.append(a.text if sent else f"held back (not a bet; telegram.send_kinds): {a.text.splitlines()[0]}")
            delivered = sent
        con.execute("INSERT INTO alerts_sent VALUES (?,?,?,?,?)", [a.key, now.replace(tzinfo=None), a.kind, a.text, delivered])


def _paper_props(con, cfg: dict, sport: str, model, priced: list, now: datetime, out: list) -> None:
    """Stamp this read's props with the model version, freeze new paper suggestions, refresh the props card. Never blocks a read."""
    from engine import version
    from engine.models import props
    pc = (cfg.get("models") or {}).get("props") or {}
    pv = version.props_version(cfg)
    props.stamp_versions(con, pv)
    n = props.log_paper(con, sport, pc.get("edge", 0.05), pv, now)
    sc = props.scorecard(con, pc.get("edge", 0.05), sport=sport, version=pv)
    if sport == "NBA":
        from engine.models import nba_props
        kw = {"about": nba_props.ABOUT, "kinds": nba_props.KIND}
    else:
        kw = {}
    props.write_sheet(priced, sc, pc, model, now, sport=sport, paper=props.paper_text(props.paper_record(con, sport, pv)), **kw)
    out.append(f"{sport} props: {n} new paper suggestion(s) frozen.")


def missed_agent_slots(cfg: dict, now: datetime, run_times: list[datetime], grace_minutes: int = 60) -> list[datetime]:
    """Scheduled research times earlier today that have no agent_runs row within `grace_minutes` after them (UTC)."""
    sched = (cfg.get("agent") or {}).get("schedule") or {}
    local = now.astimezone(config.display_tz(cfg))
    out = []
    for hhmm in sched.get("sunday" if local.weekday() == 6 else "other", []):
        h, m = (int(x) for x in str(hhmm).split(":"))
        slot = local.replace(hour=h, minute=m, second=0, microsecond=0).astimezone(timezone.utc)
        if now - slot < timedelta(minutes=grace_minutes):
            continue
        if not any(slot <= t.replace(tzinfo=timezone.utc) < slot + timedelta(minutes=grace_minutes) for t in run_times):
            out.append(slot)
    return out


def run(force: bool = False, send_alerts: bool = True) -> tuple[int, list[str]]:
    """Returns (exit code, lines to print)."""
    cfg, env = config.load_config(), config.load_env()
    now = datetime.now(timezone.utc)
    con = snap.connect(config.DB)
    out: list[str] = []
    try:
        last_ok = snap.last_ok_poll(con)
        if send_alerts and not force:
            slot = scheduled_slot(cfg, now)
            if slot is not None:
                from engine.picks import agent
                agent.SCHEMA and con.execute(agent.SCHEMA)
                last_run = con.execute("SELECT max(ts_utc) FROM agent_runs").fetchone()[0]
                if last_run is None or last_run.replace(tzinfo=timezone.utc) < slot:
                    agent.spawn(f"scheduled {slot.astimezone(config.display_tz(cfg)):%a %-I:%M %p} run", "all")
                    out.append("Started the scheduled research run for all sports.")
        if send_alerts and not force:
            try:
                from engine.picks import agent
                con.execute(agent.SCHEMA)
                since = (now - timedelta(hours=26)).replace(tzinfo=None)
                times = [r[0] for r in con.execute("SELECT ts_utc FROM agent_runs WHERE ts_utc >= ?", [since]).fetchall()]
                for slot in missed_agent_slots(cfg, now, times):
                    when = slot.astimezone(config.display_tz(cfg))
                    _deliver(con, env, [rules.Alert(f"missed-agent|{slot.isoformat()}", "gap",
                                                    f"The {when:%a %-I:%M %p} research run did not start (no record of it). Check ~/Library/Logs/betting-engine/agent.log.")], now, out)
            except Exception as e:
                out.append(f"Could not check for missed research runs: {type(e).__name__}: {e}")
        if send_alerts and not force:
            try:   # drift guard: Monday morning, and whenever what a lane looks at or which models are on changes
                from engine import lanes
                changed = lanes.check_changed(con, cfg, now)
                extra = []
                if changed:
                    extra.append(rules.Alert(f"status-changed|{lanes.structure_hash(cfg)}", "status", changed))
                local = now.astimezone(config.display_tz(cfg))
                if local.weekday() == 0 and local.hour >= 7:
                    extra.append(rules.Alert(f"status-monday|{local:%Y-%m-%d}", "status", "LANE STATUS, Monday (all five lanes)\n" + lanes.table_text(cfg, con)))
                if extra:
                    _deliver(con, env, extra, now, out)
            except Exception as e:
                out.append(f"Lane status check failed: {type(e).__name__}: {e}")
        if not force and not due(cfg, now, last_ok):
            return 0, out + ["Nothing read: outside the scheduled hours, or a read already ran in the last 45 minutes."]
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
        try:   # period lines, team totals, props: logged only, never drive a pick (plan item 2 in docs/research/04-evaluation.md)
            from engine.odds import derivatives
            drows, dprobs = derivatives.collect(wh, cfg["sports"], now)
            derivatives.save(con, drows)
            problems += dprobs
            out.append(f"Logged {len(drows)} period, team-total and prop rows.")
        except Exception as e:
            problems.append(f"Period/team-total/prop logging failed: {type(e).__name__}: {e}")
        rw_new, rw_first = [], False
        try:   # reporter news (Rotoworld posts each beat-writer and insider item minutes after the tweet)
            from engine.picks import player_news
            rw_new, rw_first = player_news.update(con, "NFL", now)
            out.append(f"Rotoworld NFL: {len(rw_new)} new post(s).")
        except SourceError as e:
            problems.append(str(e))
        try:   # props model: price this read's Pinnacle props and grade finished ones (forward test, decision 0006)
            if ((cfg.get("models") or {}).get("props") or {}).get("enabled"):
                from engine.models import props
                pm = props.Model(now.year if now.month >= 3 else now.year - 1)
                priced = props.evaluate_logged(con, pm, now)
                graded = props.grade(con, pm.season)
                out.append(f"Props model priced {len(priced)} Pinnacle props, graded {graded}.")
                _paper_props(con, cfg, "NFL", pm, priced, now, out)
        except Exception as e:
            problems.append(f"Props model failed: {type(e).__name__}: {e}")
        try:   # NBA props model: same forward test, its own scorecard (decision 0006)
            if ((cfg.get("models") or {}).get("props") or {}).get("nba_enabled"):
                from engine.models import nba_props
                nm = nba_props.NbaModel(now)
                priced = nba_props.evaluate_logged(con, nm, now)
                graded = nba_props.grade(con)
                out.append(f"NBA props model priced {len(priced)} Pinnacle props, graded {graded}.")
                _paper_props(con, cfg, "NBA", nm, priced, now, out)
        except Exception as e:
            problems.append(f"NBA props model failed: {type(e).__name__}: {e}")
        try:   # grade finished engine picks as games end; a failure is reported, never silent
            from engine.picks import grade
            from engine.picks import leans as _leans
            _leans.grade(cfg, con)      # paper Leans are graded quietly, shown on the board
            for gl in grade.run(cfg, con):
                if gl.startswith(("GRADED", "NOT GRADED")):
                    out.append(gl)
                if gl.startswith(("GRADED Bet", "GRADED Conditional")):
                    alerts.append(rules.Alert(f"graded|{gl}", "graded", "PICK GRADED: " + gl.removeprefix("GRADED ")))
        except Exception as e:
            problems.append(f"Pick grading failed: {type(e).__name__}: {e}")
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
            if not rw_first:
                from engine.picks import player_news
                for k, text, trig in player_news.nfl_qb_hits(con, rw_new, now):
                    alerts.insert(0, rules.Alert(k, "news", text))
                    triggers.append(trig)
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
                agent.spawn("; ".join(triggers)[:300], "NFL")
                out.append(f"Started a research run: {'; '.join(triggers)}")
        con.execute("INSERT INTO polls VALUES (?,?,?,?,?)",
                    [now.replace(tzinfo=None), True, len(wh_now), len(mk_now), "; ".join(problems)[:500] or None])
        out.append(f"Read {len(wh_now)} Wagerhouse games, {len(mk_now)} with a market line. {len(alerts)} alert candidates.")
        if not cfg["alerts"].get("price_messages", False):
            quiet = [a for a in alerts if a.kind in ("off-market", "moving")]
            alerts = [a for a in alerts if a.kind not in ("off-market", "moving")]
            if quiet:
                out.append(f"{len(quiet)} price gap(s) noted for the slate sheet; no message sent (price gaps alone are not picks).")
        if send_alerts:
            _deliver(con, env, alerts, now, out)
        else:
            out += [f"[{a.kind}] {a.text}" for a in alerts]
        return 0, out
    finally:
        con.close()
