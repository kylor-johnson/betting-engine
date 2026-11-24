"""Research 18 follow-ups (decision 0025): props re-centring, NBA news-timed props paper test."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone

import duckdb

from engine.models import calibrate
from engine.picks import news_props

UTC = timezone.utc


def test_calibration_recentres_an_under_lean_and_shrinks_small_stats():
    # model says 40% over on every prop; half of them went over
    rows = [("pts", 0.40, i % 2) for i in range(400)] + [("fg3m", 0.40, 1)] * 4
    sh = calibrate.fit_rows(rows, prior_n=100)
    assert sh["_all"] > 0.3                                       # pushes chances up
    assert abs(calibrate.apply(0.40, sh, "pts") - 0.5) < 0.03     # pts has 400 props: close to what happened
    assert abs(sh["fg3m"] - sh["_all"]) < 0.25                    # 4 props barely move off the pooled shift
    assert calibrate.apply(0.4, None, "pts") == 0.4
    assert calibrate.fit_rows([]) == {"_all": 0.0}


def test_out_names_parses_the_models_news_text():
    assert news_props.out_names("out: Jaylin Williams, Alex Caruso; second night of a back-to-back") == ["Jaylin Williams", "Alex Caruso"]
    assert news_props.out_names("blowout risk (spread 12.5)") == []


class _Teams:
    def __init__(self, recent):
        self.recent = recent


class _Model:
    def __init__(self):
        self.teams = _Teams({"OKC": deque([{"p1", "p2"}, {"p1", "p3"}])})
        self.names = {"p1": "Shai Gilgeous-Alexander", "p2": "Old Injury", "p3": "Fresh Out"}


def _con():
    con = duckdb.connect()
    con.execute("CREATE TABLE nba_injury_changes (ts_utc TIMESTAMP, key VARCHAR, team VARCHAR, name VARCHAR, old_status VARCHAR, "
                "new_status VARCHAR, minutes DOUBLE, points DOUBLE, alerted BOOLEAN, comment VARCHAR)")
    con.execute("CREATE TABLE player_news (url VARCHAR, sport VARCHAR, player VARCHAR, team VARCHAR, position VARCHAR, posted_utc TIMESTAMP, "
                "source_utc TIMESTAMP, headline VARCHAR, source VARCHAR, source_url VARCHAR, signal VARCHAR, seen_utc TIMESTAMP)")
    con.execute("CREATE TABLE nba_official_status (name VARCHAR, status VARCHAR, report VARCHAR, seen_utc TIMESTAMP)")
    from engine.models import props
    con.execute(props.SCHEMA)
    return con


def test_news_props_logs_only_fresh_new_absences_and_grades_clv():
    con = _con()
    now = datetime(2030, 1, 1, 22, 0, tzinfo=UTC)
    news_t = now - timedelta(minutes=40)
    con.execute("INSERT INTO nba_injury_changes VALUES (?, 'k', 'OKC', 'Fresh Out', NULL, 'Out', 30, 15, false, '')", [news_t.replace(tzinfo=None)])
    con.execute("INSERT INTO nba_injury_changes VALUES (?, 'k2', 'OKC', 'Old Injury', NULL, 'Out', 30, 15, false, '')", [news_t.replace(tzinfo=None)])
    base = {"away": "A", "home": "OKC Home", "player": "Shai Gilgeous-Alexander", "player_id": "p1", "team": "OKC", "stat": "pts",
            "line": 30.5, "over_price": -110, "under_price": -110, "market_p_over": 0.50, "model_p_over": 0.60,
            "start_utc": (now + timedelta(hours=3)).isoformat().replace("+00:00", "Z")}
    # Pinnacle's price before the news, for the "already moved" column
    con.execute("INSERT INTO prop_evals (ts_utc, start_utc, away, home, player, player_id, team, stat, line, over_price, under_price, "
                "market_p_over, model_p_over, sport) VALUES (?, ?, 'A', 'OKC Home', 'SGA', 'p1', 'OKC', 'pts', 30.5, -110, -110, 0.48, 0.55, 'NBA')",
                [(news_t - timedelta(minutes=30)).replace(tzinfo=None), base["start_utc"]])
    cfg = {}
    # an absence of a player who did not play the last game (long-term) is not news
    assert news_props.log(con, cfg, _Model(), [{**base, "news": "out: Old Injury"}], now) == []
    out = news_props.log(con, cfg, _Model(), [{**base, "news": "out: Fresh Out"}], now)
    assert len(out) == 1 and "over 30.5" in out[0]
    assert news_props.log(con, cfg, _Model(), [{**base, "news": "out: Fresh Out"}], now) == []      # once per prop
    row = con.execute("SELECT side, pin_p_side, pin_p_side_before, minutes_after_news FROM news_prop_picks").fetchone()
    assert row[0] == "over" and row[1] == 0.5 and row[2] == 0.48 and abs(row[3] - 40) < 1e-6
    # too old: outside the window
    assert news_props.log(con, {"playbook": {"news_props": {"window_min": 30}}}, _Model(),
                          [{**base, "player_id": "p9", "news": "out: Fresh Out"}], now) == []
    # grade: close 0.56 over, result 33
    kick = now + timedelta(hours=3)
    con.execute("INSERT INTO prop_evals (ts_utc, start_utc, away, home, player, player_id, team, stat, line, over_price, under_price, "
                "market_p_over, model_p_over, outcome, sport) VALUES (?, ?, 'A', 'OKC Home', 'SGA', 'p1', 'OKC', 'pts', 30.5, -130, 110, 0.56, 0.6, 33, 'NBA')",
                [(kick - timedelta(minutes=5)).replace(tzinfo=None), base["start_utc"]])
    assert news_props.grade(con, kick + timedelta(hours=4)) == 1
    clv, res = con.execute("SELECT clv, result FROM news_prop_picks").fetchone()
    assert abs(clv - 0.06) < 1e-9 and res == "W"
    assert "news-timed" in news_props.record_markdown(con, cfg)


def _pb_con():
    from engine.picks import playbook as pb, teasers
    from engine.models import props
    con = duckdb.connect()
    con.execute(pb.SCHEMA)
    con.execute(teasers.SCHEMA)
    con.execute(props.SCHEMA)
    con.execute("CREATE TABLE line_snapshots (ts_utc TIMESTAMP, source VARCHAR, sport VARCHAR, event_id VARCHAR, away VARCHAR, home VARCHAR, "
                "start_utc TIMESTAMP, home_spread DOUBLE, home_spread_price DOUBLE, away_spread_price DOUBLE, home_ml DOUBLE, away_ml DOUBLE, "
                "total DOUBLE, over_price DOUBLE, under_price DOUBLE)")
    con.execute("CREATE TABLE derivative_snapshots (ts_utc TIMESTAMP, source VARCHAR, sport VARCHAR, away VARCHAR, home VARCHAR, start_utc VARCHAR, "
                "market VARCHAR, period VARCHAR, description VARCHAR, line DOUBLE, price_a DOUBLE, price_b DOUBLE)")
    return con


def test_paper_lane_and_cleared_checks_are_paper_and_one_unit_per_game():
    from engine.picks import playbook as pb
    con = _pb_con()
    c = {"grade": "B", "event_id": "g1"}
    paper = pb.settings({"playbook": {"sports": {"NFL": {"full_game": "paper", "props_stake": False}}}}, "NFL")
    assert pb._paper_or_staked(con, paper, c, 0.5, 25.0, "B pick", 50, True)[:2] == (0.0, 0.0)
    assert pb._paper_or_staked(con, paper, c, 0.5, 25.0, "B pick", 50, False)[3] == 0.5          # nominal size kept
    staked = pb.settings({}, "NFL")
    assert pb._paper_or_staked(con, staked, {**c, "cleared": True}, 0.5, 25.0, "B pick", 50, True)[:2] == (0.0, 0.0)
    assert pb._paper_or_staked(con, staked, c, 0.5, 25.0, "B pick", 50, True)[:2] == (0.5, 25.0)
    # a $50 teaser ticket with a leg in this game already uses the game's one unit
    con.execute("INSERT INTO teaser_legs (leg_key, event_id) VALUES ('g1|away', 'g1'), ('g2|home', 'g2')")
    con.execute("INSERT INTO teaser_tickets (ticket_key, leg_a, leg_b, units, dollars) VALUES ('t', 'g1|away', 'g2|home', 1.0, 50.0)")
    assert pb.game_exposure(con, "g1") == 50.0
    u, d, note, nom = pb._paper_or_staked(con, staked, c, 0.5, 25.0, "B pick", 50, True)
    assert (u, d, nom) == (0.0, 0.0, 0.5) and "one unit" in note


def test_never_into_a_move():
    from engine.picks import playbook as pb
    con = _pb_con()
    st = pb.settings({}, "NFL")
    t0 = datetime(2030, 1, 1)
    for i, sp in enumerate((-3.0, -2.0)):          # home went from -3 to -2: a point against the home side
        con.execute("INSERT INTO line_snapshots (ts_utc, source, sport, event_id, home_spread, total) VALUES (?, 'pinnacle', 'NFL', 'g1', ?, 45)",
                    [t0 + timedelta(hours=i), sp])
    from engine.odds import snapshots as snap
    con.execute("UPDATE line_snapshots SET source = ?", [snap.SHARP])
    assert pb.moved_against(con, {"market": "side", "side": "home", "event_id": "g1"}, "NFL", st)
    assert pb.moved_against(con, {"market": "side", "side": "away", "event_id": "g1"}, "NFL", st) is None
    for i, (line, p) in enumerate(((244.5, 0.50), (244.5, 0.38))):     # Allen, Nov 23: -114 to +148 on the over
        con.execute("INSERT INTO prop_evals (ts_utc, sport, player_id, stat, home, away, line, market_p_over) VALUES (?, 'NFL', 'qb', 'passing_yards', "
                    "'Buffalo Bills', 'Kansas City Chiefs', ?, ?)", [t0 + timedelta(hours=i), line, p])
    prop = {"market": "prop", "side": "over", "player_id": "qb", "stat": "passing_yards", "home": "Buffalo Bills", "away": "Kansas City Chiefs"}
    assert "12 points" in pb.moved_against(con, prop, "NFL", st)
    assert pb.moved_against(con, {**prop, "side": "under"}, "NFL", st) is None


def test_props_and_team_totals_get_a_closing_grade():
    from engine.picks import playbook as pb
    con = _pb_con()
    kick = datetime(2030, 1, 1, 20)
    con.execute("INSERT INTO prop_evals (ts_utc, sport, player_id, stat, home, away, line, market_p_over) VALUES (?, 'NBA', 'p', 'pts', 'H', 'A', 12.5, 0.55)",
                [kick - timedelta(minutes=10)])
    cl, pts, cc = pb.prop_close(con, "NBA", "p", "pts", "H", "A", "over", 12.5, 118, kick)
    assert cl == 12.5 and pts == 0 and abs(cc - (0.55 - 100 / 218)) < 1e-4
    assert pb.prop_close(con, "NBA", "p", "pts", "H", "A", "over", 11.5, 118, kick)[2] is None      # a different line: points only
    con.execute("INSERT INTO derivative_snapshots VALUES (?, 'Pinnacle', 'NFL', 'A', 'H', '', 'team_total', 'Game', 'home', 23.5, -110, -110)",
                [kick - timedelta(minutes=10)])
    cl, pts, cc = pb.team_total_close(con, {}, "NFL", "H", "A", "home", "under", 24.0, -105, kick)
    assert cl == 23.5 and pts == 0.5 and cc is not None and 0 < cc < 0.03     # half a point better than the close, after -105


def test_sent_and_paper_messages_are_saved():
    from engine.picks import playbook as pb
    con = _pb_con()
    pb._send_and_save(con, {}, "NFL · PLAYBOOK PAPER PICK (B), DO NOT BET\nx", "nfl_sides_totals", "k1", datetime(2030, 1, 1, tzinfo=UTC), False)
    assert con.execute("SELECT kind, delivered FROM alerts_sent WHERE key = 'playbook|k1'").fetchone() == ("paper", False)


def test_a_conditional_that_does_not_say_what_the_line_prices_is_a_pass(tmp_path):
    import yaml
    from engine.picks import card
    base = {"game": "USC Trojans at UCLA Bruins", "market": "spread", "side": "home", "status": "Conditional",
            "condition": "Ty Dieffenbach is confirmed as UCLA's starting quarterback.", "summary": "QB better than feared.",
            "reasons": {"price": "p", "matchup": "m", "situation": "s", "kills_it": "k"}}
    f = tmp_path / "d.yaml"
    f.write_text(yaml.safe_dump({"decisions": [base]}))
    d = card.load_decisions(f)[0][("USC Trojans at UCLA Bruins", "spread", "home")]
    assert d["status"] == "Pass" and "priced_in" in d["why_pass"]
    ok = {**base, "reasons": {**base["reasons"], "priced_in": "UCLA opened +6.5 after the injury; a healthy starter is about 3 points, so +7 "
                                                          "assumes roughly a coin flip that he plays."}}
    f.write_text(yaml.safe_dump({"decisions": [ok]}))
    assert card.load_decisions(f)[0][("USC Trojans at UCLA Bruins", "spread", "home")]["status"] == "Conditional"
