"""Research 22 yes-list (Kylor 2026-11-24, decision 0033): a failed Telegram send is resent, picks past a cap are paper, sent picks the
market has moved past get a CANCELLED message."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from test_review18 import _pb_con

UTC = timezone.utc
NOW = datetime(2026, 11, 26, 18, 0, tzinfo=UTC)
CFG = {"timezone_display": "America/Denver", "units_by_sport": {"NFL": 50},
       "playbook": {"sports": {"NFL": {"max_per_period": 1, "props": False}}}}


def _game(eid, kick=None):
    # market: home loses by 7 (home spread +7); Wagerhouse hangs home +9.5, so home +9.5 has a price edge and no CHECK
    return {"event_id": eid, "home": f"Home {eid}", "away": f"Away {eid}", "kick": kick or NOW + timedelta(days=2),
            "own_home": 17.0, "own_away": 24.0, "own_margin": -7.0, "own_total": 41.0, "mkt_home": 17.0, "mkt_away": 24.0,
            "mkt_margin": -7.0, "mkt_total": 41.0, "wh_spread": 9.5, "wh_home_price": -110, "wh_away_price": -110,
            "wh_total": None, "wh_over": None, "wh_under": None}


@pytest.fixture
def live(monkeypatch):
    """playbook.run on hand-made games: no database reads for lines, no card, no git."""
    from engine import version
    from engine.picks import playbook as pb
    games = [_game("g1"), _game("g2")]
    monkeypatch.setattr(pb, "live_games", lambda con, now, sport: (games, []))
    monkeypatch.setattr(pb, "apply_news", lambda con, g, sport, now: [])
    monkeypatch.setattr(pb, "load_checks", lambda now, cfg, sport: {})
    monkeypatch.setattr(pb, "moved_against", lambda con, c, sport, st: None)
    monkeypatch.setattr(pb, "card", lambda *a, **k: "")
    monkeypatch.setattr(version, "stamp", lambda cfg, con=None: "test")
    return games


def _sender(log, fail=False):
    def send(env, text, lane=None, kind="info"):
        if fail:
            from engine.odds.espn import SourceError
            raise SourceError("Telegram sendMessage failed: URLError")
        log.append((text, lane, kind))
        return True
    return send


def test_a_pick_past_the_cap_is_issued_as_paper_not_dropped(live, monkeypatch):
    from engine.alerts import telegram
    from engine.picks import playbook as pb
    sent = []
    monkeypatch.setattr(telegram, "send", _sender(sent))
    con = _pb_con()
    out, _ = pb.run(CFG, {}, con, NOW, send=True, sport="NFL")
    rows = con.execute("SELECT event_id, dollars FROM playbook_picks ORDER BY dollars DESC").fetchall()
    assert [r[1] for r in rows] == [25.0, 0.0], out             # first staked (B, half of $50), second paper
    assert len(sent) == 1 and "PLAYBOOK BET" in sent[0][0]
    paper = con.execute("SELECT text FROM alerts_sent WHERE kind = 'paper'").fetchone()[0]
    assert "past the cap of 1 full-game picks per week" in paper
    from engine.bets import tracker
    assert "past the cap" in tracker.not_sent_line(con, NOW)    # named in the 9am recap


def test_a_failed_send_is_saved_undelivered_then_resent_on_the_next_read(live, monkeypatch):
    from engine import checks
    from engine.alerts import telegram
    from engine.picks import playbook as pb
    monkeypatch.setattr(telegram, "send", _sender([], fail=True))
    con = _pb_con()
    out, _ = pb.run(CFG, {}, con, NOW, send=True, sport="NFL")
    assert any(l.startswith("NOT SENT") for l in out)
    assert con.execute("SELECT kind, delivered FROM alerts_sent WHERE key LIKE 'playbook|%' AND kind = 'bet'").fetchone() == ("bet", False)
    assert [k for k, _ in checks.delivery_problems(con)] and checks.delivery_problems(con)[0][0].startswith("undelivered|")
    # next read: Telegram is back
    sent = []
    msgs = pb.resend_undelivered(con, {}, CFG, NOW + timedelta(hours=1), sender=_sender(sent))
    assert len(sent) == 1 and "SENT LATE" in sent[0][0].splitlines()[0] and sent[0][1] == "nfl_sides_totals" and sent[0][2] == "bet"
    assert msgs and msgs[0].startswith("Sent late")
    assert con.execute("SELECT delivered FROM alerts_sent WHERE kind = 'bet'").fetchone()[0] is True
    assert checks.delivery_problems(con) == []
    assert pb.resend_undelivered(con, {}, CFG, NOW + timedelta(hours=2), sender=_sender(sent)) == []     # once
    # a later failure of the same kind for a game that has started is not resent
    con.execute("UPDATE alerts_sent SET delivered = false")
    assert pb.resend_undelivered(con, {}, CFG, NOW + timedelta(days=3), sender=_sender(sent)) == []


def test_teaser_ticket_send_failure_is_caught_and_resent():
    from engine.picks import playbook as pb, teasers
    con = _pb_con()
    kick = (NOW + timedelta(days=2)).replace(tzinfo=None)
    con.execute("INSERT INTO teaser_legs (leg_key, event_id, kickoff_utc) VALUES ('a', 'g1', ?), ('b', 'g2', ?)", [kick, kick])
    con.execute("INSERT INTO teaser_tickets VALUES ('a+b', ?, 'a', 'b', 1, 50, -110, 'NFL · TEASER BET (A)\nx')", [NOW.replace(tzinfo=None)])
    con.execute(pb.ALERTS_SCHEMA)
    con.execute("INSERT INTO alerts_sent VALUES ('teaser|a+b', ?, 'bet', 'NFL · TEASER BET (A)\nx', false)", [NOW.replace(tzinfo=None)])
    sent = []
    pb.resend_undelivered(con, {}, CFG, NOW, sender=_sender(sent))
    assert sent and sent[0][1] == "nfl_teasers"
    assert con.execute("SELECT delivered FROM alerts_sent WHERE key = 'teaser|a+b'").fetchone()[0] is True


def _sent_pick(con, line=9.5, market_line=7.0, our_line=7.0, side="home", market="side"):
    from engine.picks import playbook as pb
    con.execute(f"INSERT INTO playbook_picks ({pb.PICK_COLS}) VALUES ({','.join('?' * 24)})",
                ["g1|side|home", NOW.replace(tzinfo=None), "NFL", "g1", "Away g1 at Home g1", market, side, "Home g1 +9.5", line, -110, "B",
                 0.05, our_line, market_line, our_line, 0.5, 25.0, "Home g1 +8.5", (NOW + timedelta(days=2)).replace(tzinfo=None), "w", "why",
                 "test", 0.5, 0.04])
    con.execute(pb.ALERTS_SCHEMA)
    con.execute("INSERT INTO alerts_sent VALUES ('playbook|g1|side|home', ?, 'bet', 'x', true)", [NOW.replace(tzinfo=None)])


def _pin(con, spread, when):
    con.execute("INSERT INTO line_snapshots (ts_utc, source, sport, event_id, home_spread, total) VALUES (?, 'pinnacle', 'NFL', 'g1', ?, 41)",
                [when.replace(tzinfo=None), spread])


def test_cancelled_once_when_pinnacle_moves_past_the_limit_and_not_for_a_small_move():
    from engine.picks import playbook as pb
    con = _pb_con()
    _sent_pick(con)
    _pin(con, 7.5, NOW + timedelta(hours=1))                     # half a point toward the bet: still fine
    assert pb.cancel_moved(con, {}, CFG, NOW + timedelta(hours=1), sender=_sender([])) == []
    _pin(con, 10.5, NOW + timedelta(hours=2))                    # Pinnacle now has the home team +10.5: home +9.5 is no longer a bet
    sent = []
    out = pb.cancel_moved(con, {}, CFG, NOW + timedelta(hours=2), sender=_sender(sent))
    assert len(sent) == 1 and sent[0][0].startswith("NFL · CANCELLED, DO NOT BET") and sent[0][2] == "bet"
    assert "7 to 10.5" in sent[0][0] and "keep it" in sent[0][0] and out
    assert pb.cancel_moved(con, {}, CFG, NOW + timedelta(hours=3), sender=_sender(sent)) == [] and len(sent) == 1    # once
    assert con.execute("SELECT dollars FROM playbook_picks").fetchone()[0] == 25.0                                      # still frozen


def test_no_cancel_after_the_game_starts_or_for_an_unsent_pick():
    from engine.picks import playbook as pb
    con = _pb_con()
    _sent_pick(con)
    _pin(con, 10.5, NOW + timedelta(hours=1))
    assert pb.cancel_moved(con, {}, CFG, NOW + timedelta(days=3), sender=_sender([])) == []
    con.execute("UPDATE alerts_sent SET delivered = false")
    assert pb.cancel_moved(con, {}, CFG, NOW + timedelta(hours=1), sender=_sender([])) == []


def test_research_agent_can_run_only_read_only_engine_commands():
    """Research 22, finding 9: the agent could run `engine playbook` (issues and sends picks), `status --send`, `bet add`, `lock take`."""
    from engine.picks import agent
    bash = [t for t in agent.AGENT_TOOLS if t.startswith("Bash(")]
    assert "Bash(uv run engine:*)" not in bash
    for bad in ("playbook:", "playbook --sport", "bet", "lock", "poll", "status --send", "status:", "tracker-publish", "telegram"):
        assert not any(f"engine {bad}" in t for t in bash), bad
    assert "Bash(uv run engine playbook --dry-run:*)" in bash and "Bash(uv run engine status)" in bash


def test_research_launchd_job_matches_the_config_schedule():
    """Research 22, finding 10: 8:15 every day plus 6:45 pm Sunday, as config.yaml agent.schedule says."""
    import plistlib
    from engine import config
    plist = plistlib.loads((config.ROOT / "ops" / "launchd" / "com.kylor.betting-engine.agent.plist").read_bytes())
    got = sorted((d.get("Weekday", -1), d["Hour"], d["Minute"]) for d in plist["StartCalendarInterval"])
    sched = config.load_config()["agent"]["schedule"]
    hm = lambda x: tuple(int(v) for v in x.split(":"))
    want = sorted([(-1, *hm(x)) for x in sched["other"]] + [(0, *hm(x)) for x in sched["sunday"] if x not in sched["other"]])
    assert got == want


def test_picks_from_before_messages_were_saved_are_never_resent():
    """Nov 23 picks issued before alerts_sent existed have no row, but most reached Telegram: resending could mean a second bet."""
    from engine.checks import SAVED_SINCE
    from engine.picks import playbook as pb
    con = _pb_con()
    _sent_pick(con)
    con.execute("DELETE FROM alerts_sent")
    con.execute("UPDATE playbook_picks SET first_seen_utc = ?", [SAVED_SINCE - timedelta(hours=1)])
    assert pb.resend_undelivered(con, {}, CFG, NOW, sender=_sender([])) == []
    con.execute("UPDATE playbook_picks SET first_seen_utc = ?", [SAVED_SINCE + timedelta(hours=1)])
    assert len(pb.resend_undelivered(con, {}, CFG, NOW, sender=_sender([]))) == 1      # no row after saving began: a real miss
