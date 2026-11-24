"""Research 23 test-only module: the betting and pairing arithmetic."""
from engine.models import college_review as cr


def test_bets_at_close_skips_small_gaps_and_pushes():
    # (season, week, tier, close, own, blend, actual, open)
    rows = [
        (2024, 5, "g5", 50.0, 55.0, 50.0, 60.0, 49.0),   # over, wins
        (2024, 5, "g5", 50.0, 45.0, 50.0, 52.0, 51.0),   # under, loses
        (2024, 5, "g5", 50.0, 51.0, 50.0, 70.0, 50.0),   # gap 1 < 4: no bet
        (2024, 5, "g5", 50.0, 54.0, 50.0, 50.0, 50.0),   # push
    ]
    assert cr.bets(rows, 4.0)[:2] == (1, 1)


def test_bets_at_opener_reports_move_toward_us():
    rows = [(2024, 5, "g5", 52.0, 56.0, 52.0, 60.0, 50.0)]  # opened 50, closed 52, we said 56: moved 2 our way
    w, l, move = cr.bets(rows, 4.0, at=7)
    assert (w, l) == (1, 0) and move == 2.0


def test_pairs_builds_margin_and_total_from_home_and_away():
    base = {"season": 2024, "week": 3, "tier": "power", "total": 50.0, "spread": 3.0, "open_margin": 2.0, "open_total": 49.0}
    home = {**base, "event_id": "1", "_is_home": 1, "points": 30.0}
    away = {**base, "event_id": "1", "_is_home": 0, "points": 20.0}
    (g,) = cr._pairs([home, away], [28.0, 24.0])
    assert g["own_total"] == 52.0 and g["own_margin"] == 4.0 and g["actual_margin"] == 10.0 and g["actual_total"] == 50.0
