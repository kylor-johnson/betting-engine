from datetime import datetime, timezone

import duckdb
import pytest

from engine.models import props


def test_names_and_descriptions():
    assert props.norm_name("Marvin Harrison Jr.") == props.norm_name("marvin harrison") == "marvin harrison"
    assert props.norm_name("Ja'Marr Chase") == "jamarr chase"
    assert props.split_description("Aaron Jones Total Receiving Yards") == ("Aaron Jones", "Receiving Yards")
    assert props.split_description("T.J. Hockenson Total Receptions") == ("T.J. Hockenson", "Receptions")
    assert props.split_description("Some Player Total Tackles") is None


def test_distribution_reads_neighbors_and_scales_yards():
    pairs = [(50.0, float(x)) for x in range(0, 101)]          # projection 50, outcomes 0..100
    d = props.Distribution(pairs, "yards", k=101)
    assert d.median(50.0) == pytest.approx(50.0)
    assert d.p_over(50.0, 49.5) == pytest.approx(51 / 101)
    assert d.median(100.0) == pytest.approx(100.0)              # yardage scales with the projection
    c = props.Distribution([(3.0, float(x % 7)) for x in range(70)], "count", k=70)
    assert c.median(6.0) == c.median(3.0)                       # counts are not scaled


def test_distribution_picks_closest_projections():
    pairs = [(1.0, 1.0)] * 50 + [(10.0, 10.0)] * 50
    d = props.Distribution(pairs, "count", k=50)
    assert d.median(1.2) == 1.0 and d.median(9.0) == 10.0


def test_weighted_needs_three_games_and_ignores_old_seasons():
    h = [(2024, {"receptions": 9.0}, 24.0)] * 5 + [(2026, {"receptions": 3.0}, 24.0)] * 2
    assert props._weighted(h, 2026, 0.9) is None                # 2024 games are too old; only two 2026 games
    h.append((2026, {"receptions": 3.0}, 24.0))
    avg, imp, _ = props._weighted(h, 2026, 0.9)
    assert avg["receptions"] == pytest.approx(3.0) and imp == pytest.approx(24.0)


def test_game_implied_puts_points_on_the_favorite():
    con = duckdb.connect()
    con.execute("""CREATE TABLE line_snapshots (ts_utc TIMESTAMP, source VARCHAR, sport VARCHAR, event_id VARCHAR, away VARCHAR,
                   home VARCHAR, start_utc TIMESTAMP, home_spread DOUBLE, home_spread_price DOUBLE, away_spread_price DOUBLE,
                   home_ml DOUBLE, away_ml DOUBLE, total DOUBLE, over_price DOUBLE, under_price DOUBLE)""")
    con.execute("INSERT INTO line_snapshots VALUES ('2026-11-22 10:00', 'pinnacle', 'NFL', '1', 'Las Vegas Raiders', 'Denver Broncos', "
                "NULL, -11.5, -110, -110, NULL, NULL, 41.0, -110, -110)")
    away, home = props.game_implied("Las Vegas Raiders", "Denver Broncos", datetime(2026, 11, 22, 12), con)
    assert home == pytest.approx(26.25) and away == pytest.approx(14.75)
    assert props.game_implied("Las Vegas Raiders", "Denver Broncos", datetime(2026, 11, 22, 9), con) is None   # no look-ahead


def _graded(rows):
    con = duckdb.connect()
    con.execute(props.SCHEMA)
    for i, (mp, qp, outcome) in enumerate(rows):
        con.execute("INSERT INTO prop_evals (ts_utc, start_utc, away, home, player, player_id, team, stat, line, over_price, under_price, market_p_over, model_p_over, model_median, projection, season, through_week, outcome, graded_utc, news, sport) VALUES (?, 'S', 'A', 'H', 'P', ?, 'T', 'receptions', 4.5, -110, -110, ?, ?, 4, 4, 2026, 11, ?, ?, NULL, 'NFL')",
                    [datetime(2026, 11, 22), f"p{i}", mp, qp, outcome, datetime(2026, 11, 23)])
    return con


def test_scorecard_and_gate():
    # model right more often than the market on these: it should earn weight and win its disagreements
    con = _graded([(0.5, 0.8, 6.0)] * 200 + [(0.5, 0.2, 3.0)] * 200)
    sc = props.scorecard(con)
    assert sc["graded"] == 400 and sc["best_weight_on_model"] > 0 and sc["model_edge_bets"]["won"] == 400
    assert props.passes_gate(sc, {"min_graded": 300})
    assert not props.passes_gate(sc, {"min_graded": 500})
    assert "testing only" in props.gate_line({"graded": 10}, {"min_graded": 300})


def test_scorecard_uses_last_read_and_skips_pushes():
    con = _graded([(0.5, 0.5, 4.5)])
    assert props.scorecard(con)["graded"] == 0


from engine.models import props_news


def _h(season, tshare, cshare=0.0):
    return (season, {"tshare": tshare, "cshare": cshare, "xshare": (tshare + cshare) / 2}, 22.0)


def test_vacated_counts_only_real_roles_that_are_out():
    hist = {"star": [_h(2026, 0.30)] * 4, "wr2": [_h(2026, 0.20)] * 4, "scrub": [_h(2026, 0.06)] * 4, "te": [_h(2026, 0.15)] * 4}
    regs = set(hist)
    boost, named = props_news.vacated(regs, {"star", "scrub"}, hist, 2026)
    # the scrub (6%) does not count as vacated; the star's 30% goes to the 35% still playing
    assert boost["t"] == pytest.approx(0.30 / (0.20 + 0.15))
    assert [p for p, _ in named] == ["star"]
    assert props_news.vacated(regs, set(), hist, 2026)[0]["t"] == 0.0


def test_role_ratio_and_factor():
    hist = {"rb": [_h(2026, 0.0, 0.30)] * 6 + [_h(2026, 0.0, 0.60)] * 2}
    f = props_news.features("rb", hist, 2026, {"t": 0.0, "c": 0.5, "x": 0.0}, questionable=True)
    assert f["R"]["c"] > 1.3 and f["q"]
    base = props_news.factor(f, "carries", (0.0, 0.0, 1.0))
    full = props_news.factor(f, "carries", (0.2, 0.5, 0.9))
    assert base == 1.0 and full == pytest.approx((1 + 0.2 * 0.5) * f["R"]["c"] ** 0.5 * 0.9)
    assert props_news.factor(f, "passing_yards", (0.2, 0.5, 1.0)) == 1.0     # no usage share for passing; only Questionable


def test_team_state_drops_players_who_changed_teams():
    ts = props_news.TeamState()
    ts.record("MIN", {"a", "b"})
    ts.record("DAL", {"b"})            # b traded
    assert ts.regulars("MIN") == {"a"}


def test_injuries_lookup_by_name_and_team():
    class P:
        def __init__(self, name, team, status):
            self.name, self.team, self.status = name, team, status
    inj = props.Injuries([P("Jordan Addison", "Minnesota Vikings", "Out"), P("Brock Bowers", "Las Vegas Raiders", "Questionable")])
    assert inj.of("Jordan Addison", "MIN") == "Out" and inj.of("brock bowers", "LV") == "Questionable"
    assert inj.of("Jordan Addison", "LV") == ""


def test_paper_picks_are_frozen_at_first_sight_graded_at_that_price_and_split_by_version():
    from datetime import timedelta
    con = duckdb.connect()
    con.execute(props.SCHEMA)
    now = datetime(2026, 11, 22, 12, 0)
    future = (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cols = ("ts_utc, start_utc, away, home, player, player_id, team, stat, line, over_price, under_price, market_p_over, model_p_over, "
            "model_median, projection, season, through_week, sport")

    def read(ts, line, q):
        con.execute(f"INSERT INTO prop_evals ({cols}) VALUES (?,?,'A','H','P','p1','T','receptions',?,-110,-110,0.5,?,4,4,2026,11,'NFL')", [ts, future, line, q])
    read(now, 4.5, 0.62)                                     # model says 62% over against 52% break-even: a paper Over
    assert props.log_paper(con, "NFL", 0.05, "pA", now) == 1
    read(now + timedelta(hours=1), 5.5, 0.30)                # later reads never change a frozen pick
    props.log_paper(con, "NFL", 0.05, "pB", now + timedelta(hours=1))
    picks = con.execute("SELECT side, line, model_version FROM prop_paper_picks ORDER BY first_seen_utc").fetchall()
    assert picks[0] == ("Over", 4.5, "pA") and ("Under", 5.5, "pB") in picks
    con.execute("UPDATE prop_evals SET outcome = 7")          # he caught 7: the Over at 4.5 won, the Under at 5.5 lost
    rec = props.paper_record(con, "NFL")
    assert (rec["graded"], rec["won"], rec["lost"]) == (2, 1, 1) and rec["versions"] == 2
    assert props.paper_record(con, "NFL", "pA")["won"] == 1 and props.paper_record(con, "NFL", "pB")["lost"] == 1
    assert "Paper suggestions" in props.paper_text(rec)


def test_scorecard_can_count_only_the_current_version():
    con = duckdb.connect()
    con.execute(props.SCHEMA)
    for i, v in enumerate(("old", "new", "new")):
        con.execute("INSERT INTO prop_evals (ts_utc, start_utc, away, home, player, player_id, team, stat, line, over_price, under_price, market_p_over, model_p_over, "
                    "model_median, projection, season, through_week, outcome, sport, model_version) VALUES "
                    "(?, 'S','A','H','P',?,'T','receptions',4.5,-110,-110,0.5,0.6,4,4,2026,11,6,'NFL',?)", [datetime(2026, 11, 22), f"p{i}", v])
    assert props.scorecard(con)["graded"] == 3 and props.scorecard(con, version="new")["graded"] == 2
