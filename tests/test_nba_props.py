import pytest

from engine.models import nba_props as m


def _p(pid, team, mins, pts, reb=5, ast=3, fg3m=1, fga=None):
    return {"id": pid, "name": f"P{pid}", "team": team, "min": mins, "pts": pts, "reb": reb, "ast": ast, "fg3m": fg3m,
            "fga": fga if fga is not None else pts / 2, "fta": 2, "tov": 1}


def _game(i, day, players, spread=-4.0, total=224.0, season=2025):
    return {"event_id": str(i), "season": season, "date": day, "start_utc": f"{day}T23:00:00+00:00", "home": "AAA", "away": "BBB",
            "home_spread": spread, "total": total, "players": players}


def test_weighted_minutes_and_rates():
    hist = [(2025, 30.0, {"pts": 0.5, "reb": 0.2, "ast": 0.1, "fg3m": 0.05, "pra": 0.8}, 15.0, 110.0)] * 5
    w = m._weighted(hist, 2025, 0.9)
    assert w["min"] == pytest.approx(30.0) and w["rate"]["pts"] == pytest.approx(0.5) and w["imp"] == pytest.approx(110.0)
    assert m._weighted(hist[:2], 2025, 0.9) is None


def test_star_out_frees_minutes_and_usage_for_the_rest():
    games = []
    for i in range(6):
        day = f"2024-11-{i * 2 + 1:02d}"
        games.append(_game(i, day, [_p("star", "AAA", 36, 30, fga=22), _p("wing", "AAA", 30, 12), _p("big", "AAA", 28, 10),
                                    _p("opp", "BBB", 34, 20)]))
    games.append(_game(9, "2024-11-15", [_p("wing", "AAA", 38, 20), _p("big", "AAA", 32, 12), _p("opp", "BBB", 34, 20)]))
    recs, hist, teams, names = m.history(games)
    last = [r for r in recs if r["date"] == "2024-11-15" and r["pid"] == "wing"][0]
    assert last["bm"] > 0.3 and last["bu"] > 0.3            # the star's minutes and shots were vacated
    earlier = [r for r in recs if r["date"] == "2024-11-11" and r["pid"] == "wing"][0]
    assert earlier["bm"] == 0.0
    news = {**m.NO_NEWS, "r_min": 0.5, "r_use": 0.5}
    assert m.project(last, "pts", (0.9, 0.9, 0.0), news) > m.project(last, "pts", (0.9, 0.9, 0.0), m.NO_NEWS)


def test_back_to_back_and_blowout_terms():
    rec = {"w": {d: {"min": 34.0, "use": 20.0, "imp": 112.0, "rate": {"pts": 0.7}} for d in m.DECAYS},
           "implied": 112.0, "spread": 14.0, "b2b": True, "bm": 0.0, "bu": 0.0, "has_line": True}
    base = m.project(rec, "pts", (0.9, 0.9, 0.0), m.NO_NEWS)
    adj = m.project(rec, "pts", (0.9, 0.9, 0.0), {**m.NO_NEWS, "blowout": -0.02, "b2b": 0.95})
    assert adj == pytest.approx(base * (1 - 0.02 * 6) * 0.95)


def test_b2b_detection():
    assert m._is_b2b("2024-11-01", "2024-11-02") and not m._is_b2b("2024-11-01", "2024-11-03") and not m._is_b2b(None, "2024-11-02")


def test_injuries_priority_reporter_then_official_then_espn():
    inj = m.NbaInjuries({"a b": "Questionable", "c d": "Out"}, {"a b": "playing", "e f": "not playing"}, {"g h": "Doubtful"})
    assert inj.status("A B") == ("Available", "reporter")
    assert inj.out("C D") and inj.out("E F") and inj.out("G H")
    assert not inj.out("Nobody Listed")


def test_split_description():
    assert m.split_description("Andrew Nembhard Total Pts & Rebs & Asts") == ("Andrew Nembhard", "Pts & Rebs & Asts")
    assert m.split_description("Ajay Mitchell Total Points") == ("Ajay Mitchell", "Points")
    assert m.split_description("Someone Total Steals") is None
