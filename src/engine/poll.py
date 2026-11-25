"""One scheduled read: collect lines, store them, decide and send alerts."""
from __future__ import annotations

import traceback
from datetime import datetime, timedelta, timezone

from engine import config
from engine.alerts import rules, telegram
from engine.odds import snapshots as snap
from engine.odds.espn import SourceError
from engine.odds.wagerhouse import Wagerhouse


def due(cfg: dict, now: datetime, last_ok: datetime | None, pregame: bool = False) -> bool:
    """True when this half-hourly wake-up should actually read lines: hourly, or every wake-up (both :02 and :32) when `pregame`, a game
    of a sport in `read_pregame_hours` starts within that many hours (decision 0037)."""
    local = now.astimezone(config.display_tz(cfg))
    hours = cfg["read_hours"]["sunday" if local.weekday() == 6 else "other"]
    if local.hour not in hours:
        return False
    return last_ok is None or (now - last_ok) > timedelta(minutes=20 if pregame else 45)


def pregame(con, cfg: dict, now: datetime) -> bool:
    """True when a game of a sport in config `read_pregame_hours` ({sport: hours}) starts after now and within that many hours."""
    for sport, h in ((cfg.get("read_pregame_hours") or {}).items()):
        try:
            n = con.execute("SELECT count(*) FROM line_snapshots WHERE sport = ? AND start_utc > ? AND start_utc <= ?",
                            [sport, now.replace(tzinfo=None), (now + timedelta(hours=float(h))).replace(tzinfo=None)]).fetchone()[0]
        except Exception:
            continue
        if n:
            return True
    return False


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


def extra_slots(cfg: dict, now: datetime) -> list[tuple[str, datetime]]:
    """Extra research runs for one sport inside a date window (decision 0034: college bowl season), as (sport, UTC slot) for the slot that
    fell in the last 30 minutes. Config: agent.extra_runs = [{sport, from, to, times}] with dates as YYYY-MM-DD, Mountain time."""
    local = now.astimezone(config.display_tz(cfg))
    out = []
    for e in (cfg.get("agent") or {}).get("extra_runs") or []:
        if not (str(e["from"]) <= local.date().isoformat() <= str(e["to"])):
            continue
        for hhmm in e.get("times") or []:
            h, m = (int(x) for x in str(hhmm).split(":"))
            slot = local.replace(hour=h, minute=m, second=0, microsecond=0)
            if timedelta(0) <= local - slot < timedelta(minutes=30):
                out.append((e["sport"], slot.astimezone(timezone.utc)))
    return out


def refresh_tracker(con, cfg: dict, now: datetime) -> list[str]:
    """Outside read hours (evenings, nights), grade finished picks and rebuild the tracker page at most once an hour, so tracker.html is
    current when games end at night. No Wagerhouse sign-in: grades come from final scores; your bets come from the last history sync."""
    stamp = config.DATA / "raw" / ".tracker_refresh"
    try:
        if stamp.exists() and now.timestamp() - stamp.stat().st_mtime < 3300:
            return []
        from engine.bets import tracker as _tr
        from engine.picks import playbook as _pb, teasers as _tz
        _tz.grade(con)
        _pb.grade(con, cfg)
        _tr.write(con, cfg)
        from engine.bets import public_page
        pub = public_page.publish(con, cfg)
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text(now.isoformat())
        return ["Tracker page refreshed (graded finished picks; no book read)."] + ([pub] if pub else [])
    except Exception as e:
        return [f"Tracker refresh failed: {type(e).__name__}: {e}"]


def _deliver(con, env: dict, alerts: list[rules.Alert], now: datetime, out: list[str]) -> None:
    for a in alerts:
        if con.execute("SELECT 1 FROM alerts_sent WHERE key=?", [a.key]).fetchone():
            continue
        delivered = True
        try:
            sent = telegram.send(env, a.text, kind="system" if a.kind in ("gap", "failure", "lane") else "info")
        except SourceError as e:
            delivered = False
            out.append(f"NOT SENT ({e}): {a.text}")
        else:
            out.append(a.text if sent else f"held back (not a bet; telegram.send_kinds): {a.text.splitlines()[0]}")
            delivered = sent
        con.execute("INSERT INTO alerts_sent VALUES (?,?,?,?,?)", [a.key, now.replace(tzinfo=None), a.kind, a.text, delivered])


def lane_change_key(structure_hash: str, now: datetime) -> str:
    """alerts_sent key for a lane change. The time is part of it: a lane that changes back to an earlier state (staked, paper,
    staked) repeats an old hash, and with the hash alone the return was never sent (audit 24)."""
    return f"status-changed|{structure_hash}|{now:%Y-%m-%dT%H:%M}"


SYSTEM_KINDS = ("gap", "failure", "lane")


def resend_system(con, env: dict, now: datetime, out: list[str], hours: int = 48) -> None:
    """Send again any system line (engine broken, missed read, lane change, stop, review, NOT DELIVERED) whose send failed in the
    last `hours`. `_deliver` saves a failed line as not delivered and never looks at its key again, so a stop that tripped while
    Telegram was down was never told (audit 24). A line held back by telegram.send_kinds stays held back."""
    rows = con.execute("SELECT key, text FROM alerts_sent WHERE kind IN ('gap', 'failure', 'lane') AND NOT delivered AND ts_utc >= ?",
                       [(now - timedelta(hours=hours)).astimezone(timezone.utc).replace(tzinfo=None)]).fetchall()
    for key, text in rows:
        try:
            sent = telegram.send(env, text, kind="system")
        except SourceError as e:
            out.append(f"NOT SENT again ({e}): {text.splitlines()[0]}")
            continue
        if sent:
            con.execute("UPDATE alerts_sent SET delivered = true WHERE key = ?", [key])
            out.append(f"sent late: {text.splitlines()[0]}")


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
            for x_sport, x_slot in extra_slots(cfg, now):       # decision 0034: bowl-season college runs
                from engine.picks import agent
                con.execute(agent.SCHEMA)
                last_x = con.execute("SELECT max(ts_utc) FROM agent_runs WHERE reason LIKE ?", [f"{x_sport}:%"]).fetchone()[0]
                if last_x is None or last_x.replace(tzinfo=timezone.utc) < x_slot:
                    agent.spawn(f"extra {x_slot.astimezone(config.display_tz(cfg)):%a %-I:%M %p} {x_sport} run", x_sport)
                    out.append(f"Started the extra {x_sport} research run.")
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
            try:   # drift guard (decision 0027): one Telegram line when a lane changes, a stop trips, or a lane falls below its review line
                from engine import lanes
                from engine.picks import playbook as _pbk
                changed = lanes.check_changed(con, cfg, now)
                extra = []
                if changed:
                    # the time is in the key: a lane that changes back to an earlier state is a new event, not a repeat (audit 24)
                    extra.append(rules.Alert(lane_change_key(lanes.structure_hash(cfg), now), "lane", changed))
                for key, text in _pbk.lane_events(con, cfg):
                    extra.append(rules.Alert(key, "lane", text))
                if extra:
                    _deliver(con, env, extra, now, out)
            except Exception as e:
                out.append(f"Lane status check failed: {type(e).__name__}: {e}")
        if not force and not due(cfg, now, last_ok, pregame(con, cfg, now)):
            out += refresh_tracker(con, cfg, now)
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
        nfl_props_ctx = nba_props_ctx = None
        try:   # reporter news (Rotoworld posts each beat-writer and insider item minutes after the tweet)
            from engine.picks import player_news
            rw_new, rw_first = player_news.update(con, "NFL", now)
            out.append(f"Rotoworld NFL: {len(rw_new)} new post(s).")
        except player_news.Truncated as e:     # posts read are kept; the gap is a problem line (audit 24)
            rw_new, rw_first = e.new, e.first
            problems.append(str(e))
        except SourceError as e:
            problems.append(str(e))
        try:   # props model: price this read's Pinnacle props and grade finished ones (forward test, decision 0006)
            if ((cfg.get("models") or {}).get("props") or {}).get("enabled"):
                from engine.models import props
                pm = props.Model(now.year if now.month >= 3 else now.year - 1)
                priced = props.evaluate_logged(con, pm, now)
                nfl_props_ctx = (pm, priced)
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
                nba_props_ctx = (nm, priced)
                graded = nba_props.grade(con)
                out.append(f"NBA props model priced {len(priced)} Pinnacle props, graded {graded}.")
                _paper_props(con, cfg, "NBA", nm, priced, now, out)
                try:   # NBA news-timed props, paper test (research 18; decision 0025)
                    from engine.models import calibrate as _cal
                    from engine.picks import news_props as _np
                    out += _np.log(con, cfg, nm, priced, now, shifts=_cal.fit(con, "NBA"))
                except Exception as e:
                    problems.append(f"NBA news props failed: {type(e).__name__}: {e}")
        except Exception as e:
            problems.append(f"NBA props model failed: {type(e).__name__}: {e}")
        # grade finished engine picks as games end; each step has its own try, so one failure cannot stop the others, the
        # daily check or the 9am recap (audit 24: one bad ESPN score used to skip all of them). A failure is a problem line.
        def _step(name, fn):
            try:
                return fn()
            except Exception as e:
                problems.append(f"{name} failed: {type(e).__name__}: {e}")
        from engine.picks import grade
        from engine.picks import leans as _leans
        from engine import stale as _stale
        from engine.picks import teasers as _teasers
        from engine.picks import playbook as _playbook
        from engine.picks import news_props as _np
        from engine.bets import tracker as _tracker
        _step("Lean grading", lambda: _leans.grade(cfg, con))      # paper Leans are graded quietly, shown on the board
        _step("Stale-number grading", lambda: _stale.grade(con, cfg=cfg))
        _step("Teaser grading", lambda: _teasers.grade(con))
        for gl in (_step("Playbook grading", lambda: _playbook.grade(con, cfg)) or []):
            if gl.startswith("NOT GRADED"):
                out.append(gl)
        _step("Candidate grading", lambda: _playbook.grade_candidates(con))
        _step("Playbook record", lambda: (config.ROOT / "docs" / "lanes" / "PLAYBOOK-RECORD.md").write_text(_playbook.record_markdown(con, cfg)))
        _step("News-props grading", lambda: _np.grade(con))
        _step("News-props record", lambda: (config.ROOT / "docs" / "lanes" / "NEWS-PROPS.md").write_text(_np.record_markdown(con, cfg)))
        _step("Tracker", lambda: _tracker.write(con, cfg))
        try:
            local = now.astimezone(config.display_tz(cfg))
            rstamp = config.DATA / "raw" / ".tracker_recap"
            cstamp = config.DATA / "raw" / ".checks_run"
            if local.hour >= 7 and (not cstamp.exists() or cstamp.read_text().strip() != local.date().isoformat()):
                try:     # the charter's working checks, once a day (decision 0030); one system line only when something fails
                    from engine import checks as _checks
                    _, cres = _checks.write(con, cfg, now)
                    ctext = _checks.telegram_text(cres)
                    if ctext and send_alerts:
                        _deliver(con, env, [rules.Alert(f"checks|{local.date().isoformat()}", "failure", ctext)], now, out)
                    cstamp.write_text(local.date().isoformat())
                except Exception as e:
                    out.append(f"Checks failed to run: {type(e).__name__}: {e}")
            if send_alerts and local.hour >= 9 and (not rstamp.exists() or rstamp.read_text().strip() != local.date().isoformat()):
                try:
                    from engine.alerts import telegram as _tg
                    _tg.send(env, _tracker.recap(con, cfg), kind="recap")
                    rstamp.write_text(local.date().isoformat())
                except Exception as e:
                    problems.append(f"9am recap failed: {type(e).__name__}: {e}")
        except Exception as e:
            problems.append(f"Checks or recap failed: {type(e).__name__}: {e}")
        try:
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
        from engine import stale
        stale_msgs = stale.scan(cfg, env, con, snaps, now, send=send_alerts)
        out += stale_msgs
        day = now.astimezone(config.display_tz(cfg)).strftime("%Y-%m-%d")
        try:   # NFL Wong teasers (decisions 0014, 0019): freeze new legs, send tickets, refresh this week's card
            from engine.picks import teasers
            out += teasers.scan(cfg, con, snaps, now, send=send_alerts)
            (config.ROOT / "docs" / "cards" / f"{day}-nfl-teasers.md").write_text(teasers.card(con, cfg, now))
        except Exception as e:
            out.append(f"Teaser lane failed: {type(e).__name__}: {e}")
        try:   # tracker (Kylor, Nov 23): the graded history twice a day (first read from 8am, first from 5pm); a 9am recap.
            # The site's report does not return open bets (graded: 0 returns graded ones), so a bet shows once it is graded.
            from engine.bets import tracker
            local = now.astimezone(config.display_tz(cfg))
            stamp = config.DATA / "raw" / ".tracker_full_sync"
            slot = f"{local.date().isoformat()}-{'pm' if local.hour >= 17 else 'am'}"
            if local.hour >= 8 and (not stamp.exists() or stamp.read_text().strip() != slot):
                out.append(tracker.sync(env, weeks=1, wh=wh))
                stamp.write_text(slot)
        except Exception as e:
            out.append(f"Tracker sync failed: {type(e).__name__}: {e}")
        from engine.picks import playbook
        if send_alerts:      # every read: resend what Telegram missed, check delivery, cancel sent picks the market has moved past (research 22)
            try:
                resend_system(con, env, now, out)
            except Exception as e:
                out.append(f"System-line resend failed: {type(e).__name__}: {e}")
            try:
                out += playbook.resend_undelivered(con, env, cfg, now)
                from engine import checks as _ck
                dp = _ck.delivery_problems(con)
                if dp:
                    _deliver(con, env, [rules.Alert(k, "failure", t) for k, t in dp], now, out)
            except Exception as e:
                out.append(f"Resend and delivery check failed: {type(e).__name__}: {e}")
            try:
                out += playbook.cancel_moved(con, env, cfg, now)
            except Exception as e:
                out.append(f"Cancel check failed: {type(e).__name__}: {e}")
        from engine.picks import paper_lanes      # three paper lanes, $0, never sent (decision 0036); before the playbook so the cards show them
        out += paper_lanes.run(con, cfg, now)
        for pb_sport, ctx in (("NFL", nfl_props_ctx), ("NBA", nba_props_ctx), ("College", None)):   # playbook picks (decisions 0018-0022)
            if pb_sport not in cfg.get("sports", []):
                continue
            try:
                pb_lines, pb_card = playbook.run(cfg, env, con, now, send=send_alerts, props_ctx=ctx, sport=pb_sport)
                out += [l for l in pb_lines if " · PLAYBOOK" not in l] + [f"playbook pick issued: {l.splitlines()[1]}" for l in pb_lines if " · PLAYBOOK" in l]
                if pb_card:
                    (config.ROOT / "docs" / "cards" / f"{day}-{pb_sport.lower()}-playbook.md").write_text(
                        pb_card + paper_lanes.card_block(con, cfg, pb_sport, now))
            except Exception as e:
                out.append(f"Playbook {pb_sport} failed: {type(e).__name__}: {e}")
        if "College" in cfg.get("sports", []):           # college openers on paper (research 23 T4, decision 0034); never sent
            from engine.picks import college_openers
            out += college_openers.run(con, cfg, now)
        try:   # rebuild the tracker after this read's picks and teaser tickets are issued, so the page shows them now, not next hour
            from engine.bets import tracker as _tr_after
            _tr_after.write(con, cfg)
        except Exception as e:
            out.append(f"Tracker page rebuild failed: {type(e).__name__}: {e}")
        if send_alerts:      # the live model-picks page (Kylor, Nov 23): pushed to Vercel only when the picks changed; never blocks a read
            from engine.bets import public_page
            out += [l for l in [public_page.publish(con, cfg)] if l]
        # run on change (decision 0016): a new stale number means Pinnacle moved and Wagerhouse has not; the agent looks for the reason
        stale_sports = stale.new_sports(con, now)
        if "NFL" in stale_sports:
            triggers.append("stale number at Wagerhouse (NFL)")
        if send_alerts:
            out += stale.start_research(cfg, con, now, [sp for sp in stale_sports if sp != "NFL"])
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
