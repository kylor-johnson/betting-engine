from engine.models import nba_absences as na


def game(i, home_play, away_play, spread=-3.0, hp=60, ap=55):
    pl = [{"id": f"h{k}", "team": "H", "min": m, "pts": hp / 5} for k, m in home_play.items()]
    pl += [{"id": f"a{k}", "team": "A", "min": m, "pts": ap / 5} for k, m in away_play.items()]
    return {"season": 2026, "home": "H", "away": "A", "home_spread": spread, "players": pl, "start_utc": f"2026-11-{i:02d}"}


def test_fresh_absence_of_a_regular_counts_and_a_long_absence_does_not():
    full = {k: 30.0 for k in range(5)}
    games = [game(i, full, full, hp=60, ap=55) for i in range(1, 8)]
    # game 8: home's player 0 (30 min regular) is out; away is whole
    games.append(game(8, {k: (0.0 if k == 0 else 30.0) for k in range(5)}, full, hp=120, ap=110))
    rows = na.game_features(games)
    last = rows[-1]
    assert last["lost_home"] == 30.0 and last["lost_away"] == 0.0 and last["x"] == -3.0 and last["stars"] == -1
    # y = margin + spread: (120-110)... points are per player so total pts = 120 vs 110 -> margin 10, +(-3) = 7
    assert last["y"] == 7.0


def test_fit_recovers_a_planted_slope():
    rows = [{"x": x / 2, "y": 2.0 * (x / 2)} for x in range(-10, 11)]
    b, se, n = na.fit(rows)
    assert abs(b - 2.0) < 1e-9 and n == 21
