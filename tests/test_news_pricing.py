from datetime import datetime, timedelta, timezone

from engine.picks.slate import unpriced_part

T0 = datetime(2026, 11, 23, 16, 0, tzinfo=timezone.utc)      # 9:00 MT
ADD = {"market": "spread", "team": "Home", "points": -4.0, "added": "2026-11-23 09:00 MT", "news_at": "2026-11-23 09:00 MT"}
# home team loses 4 points of strength: the home spread should rise by 4 if fully priced


def hist(*rows):
    return [(T0 + timedelta(minutes=m), sp, tot) for m, sp, tot in rows]


def test_no_move_since_news_is_unpriced_and_fully_applied():
    pts, why = unpriced_part(ADD, hist((-30, -7.0, 44), (30, -7.0, 44)), -7.0, 44, 1)
    assert pts == -4.0 and why.startswith("unpriced")


def test_full_move_is_priced_and_nothing_added():
    pts, why = unpriced_part(ADD, hist((-30, -7.0, 44), (30, -3.0, 44)), -3.0, 44, 1)
    assert pts == 0.0 and why.startswith("priced")


def test_half_move_leaves_half():
    pts, why = unpriced_part(ADD, hist((-30, -7.0, 44), (30, -5.0, 44)), -5.0, 44, 1)
    assert pts == -2.0 and why.startswith("partly priced")


def test_no_line_from_before_the_news_means_not_applied():
    pts, why = unpriced_part(ADD, hist((10, -3.0, 44)), -3.0, 44, 1)
    assert pts == 0.0 and "before the news" in why


def test_move_the_wrong_way_does_not_count_as_priced():
    pts, _ = unpriced_part(ADD, hist((-30, -7.0, 44), (30, -9.0, 44)), -9.0, 44, 1)
    assert pts == -4.0


def test_away_team_entry_and_totals():
    away = {**ADD, "team": "Away", "points": -4.0}       # away weaker: home spread should FALL by 4
    assert unpriced_part(away, hist((-30, -3.0, 44), (30, -7.0, 44)), -7.0, 44, -1)[0] == 0.0
    tot = {"market": "total", "points": -3.0, "news_at": "2026-11-23 09:00 MT"}
    assert unpriced_part(tot, hist((-30, -3.0, 44.0), (30, -3.0, 41.0)), -3.0, 41.0, 1)[0] == 0.0
    assert unpriced_part(tot, hist((-30, -3.0, 44.0), (30, -3.0, 44.0)), -3.0, 44.0, 1)[0] == -3.0


def test_entry_without_news_time_is_not_applied():
    old = {k: v for k, v in ADD.items() if k != "news_at"}
    pts, why = unpriced_part(old, hist((-30, -7.0, 44)), -7.0, 44, 1)
    assert pts == 0.0 and "news_at" in why


def test_no_pinnacle_read_since_the_news_is_not_applied():
    """Research 22, finding 4: Pinnacle pulled the game (or no read ran) after the news, so its unchanged pre-news line proves nothing."""
    pts, why = unpriced_part(ADD, hist((-30, -7.0, 44)), -7.0, 44, 1)
    assert pts == 0.0 and "no Pinnacle read since the news" in why
