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
        con.execute("INSERT INTO prop_evals VALUES (?, 'S', 'A', 'H', 'P', ?, 'T', 'receptions', 4.5, -110, -110, ?, ?, 4, 4, 2026, 11, ?, ?)",
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
