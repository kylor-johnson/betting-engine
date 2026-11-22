from datetime import datetime

import pytest

from engine.models import first_half, weather, wind_totals
from engine.models.wind_totals import Game
from engine.odds.espn import SourceError
from engine.picks import card


def test_wind_adjustment_is_zero_below_the_knot_and_grows_above():
    assert wind_totals.adjustment(5.0, -0.2, 6.0) == 0.0
    assert wind_totals.adjustment(16.0, -0.2, 6.0) == pytest.approx(-2.0)


def _g(season, wind, close, actual):
    return Game("x", season, "BUF00", datetime(2020, 1, 1, tzinfo=weather.EASTERN), close, actual, wind=wind)


def test_fit_recovers_a_planted_wind_effect():
    gs = [_g(2015, w, 45.0, 45.0 + 1.0 - 0.3 * max(0, w - 10)) for w in range(0, 30)] * 3
    b, k = wind_totals.fit(gs)
    assert k == 10.0 and b == pytest.approx(-0.3, abs=1e-6)


def test_walk_forward_only_uses_earlier_seasons():
    # 2015-2018 have a strong wind effect; 2019 has none. The 2019 test must use the 2015-2018 fit,
    # so it bets Unders in 2019 and loses them; a look-ahead fit would place no bets.
    train = [_g(s, w, 45.0, 45.0 - 0.5 * max(0, w - 6)) for s in range(2015, 2019) for w in range(0, 25)]
    test = [_g(2019, w, 45.0, 46.0) for w in range(15, 25)]
    r = wind_totals.walk_forward(train + test, 2019)
    assert r["records"][0]["won"] == 0 and r["records"][0]["lost"] == 10


def test_game_window_averages_the_first_three_hours():
    hours = {"2026-11-22T13:00": (10.0, 40.0, 0.0), "2026-11-22T14:00": (14.0, 42.0, 1.0), "2026-11-22T15:00": (18.0, 44.0, 0.5)}
    w = weather.game_window(hours, datetime(2026, 11, 22, 13, 0, tzinfo=weather.EASTERN))
    assert w == {"wind_mph": 14.0, "temp_f": 42.0, "precip_mm": 1.5}
    assert weather.game_window({}, datetime(2026, 11, 22, 13, 0, tzinfo=weather.EASTERN)) is None


def test_every_open_air_home_team_has_coordinates():
    for team, st in weather.HOME_STADIUM.items():
        assert st is None or st in weather.STADIUMS, team


def test_first_half_habit_uses_only_prior_games():
    gs = [{"game_id": str(i), "season": 2015 + i // 40, "week": 1, "home": "A" if i % 2 else "B", "away": "B" if i % 2 else "A",
           "spread": float(i % 7 - 3), "total": 40.0 + i % 9, "h1_home": 10 + (i % 3), "h1_away": 10, "f_home": 24, "f_away": 20, "day": i} for i in range(200)]
    first_half.build_features(gs)
    assert gs[0]["x_margin"] == 0.0 and gs[0]["x_total"] == 0.0     # nothing before the first game


def _sheet_with_wind_side():
    side = {"side": "under", "pick": "Under 44.5", "price": -110, "value": 0.03, "edge_points": 1.4, "win": 0.55, "push": 0.0,
            "numbers_say_bet": True, "dont_bet_past": "Under 43.5", "limit_line": 43.5, "model_agrees": True,
            "model": "wind", "max_status": "Conditional"}
    return {"sport": "NFL", "built_utc": "2026-11-22T20:00:00+00:00", "games": [{
        "event_id": "1", "game": "A at B", "start_utc": "2026-11-23T01:20:00+00:00", "notes": [], "adjustments": [],
        "markets": [{"market": "spread", "rating_line": None, "public_systems_line": None, "adjustment_points": 0, "model_line": None,
                     "fair_line": -3.0, "sides": []},
                    {"market": "total", "fair_line": 43.1, "book_line": 44.5, "sides": [side],
                     "wind_model": {"wind_mph": 17.0, "temp_f": 35.0, "precip_mm": 0.0, "points": -1.9, "used": True}}]}],
        "problems": [], "adjustments_used": []}


CFG = {"timezone_display": "America/Denver", "unit": 25, "picks": {"max_units": 1, "conditional_units": 0.5, "market_weight": 0.55}}
REASONS = {"price": "p", "matchup": "m", "situation": "s", "kills_it": "k"}


def test_card_refuses_a_bet_the_wind_model_only_allows_as_conditional():
    d = {("A at B", "total", "under"): {"game": "A at B", "market": "total", "side": "under", "status": "Bet",
                                        "reasons": REASONS, "summary": "Wind model pick."}}
    with pytest.raises(SourceError):
        card.build(_sheet_with_wind_side(), d, "", CFG)
    text, rows = card.build(_sheet_with_wind_side(), d, "", CFG, strict=False)
    assert rows[0]["status"] == "Conditional" and rows[0]["units"] == 0.5
    assert "Wind model" in text


def test_card_accepts_the_wind_conditional():
    d = {("A at B", "total", "under"): {"game": "A at B", "market": "total", "side": "under", "status": "Conditional",
                                        "condition": "Forecast still 15 mph or more two hours before kickoff.",
                                        "reasons": REASONS, "summary": "Wind model pick."}}
    _, rows = card.build(_sheet_with_wind_side(), d, "", CFG)
    assert rows[0]["status"] == "Conditional" and rows[0]["dont_bet_past"] == "Under 43.5"
