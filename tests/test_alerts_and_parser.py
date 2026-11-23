from datetime import datetime, timedelta, timezone

import pytest

from engine import poll
from engine.alerts import rules
from engine.bets.history import merge_pull
from engine.bets.parser import parse
from engine.odds.snapshots import Snap
from engine.odds.wagerhouse import READ_ONLY, Wagerhouse, normalize_line

NOW = datetime(2026, 11, 22, 17, 0, tzinfo=timezone.utc)
CFG = {
    "alerts": {"spread_points": 1.0, "total_points": {"NFL": 1.5, "NBA": 2.0}, "min_value": -0.01},
    "key_numbers": {"NFL": [3, 7, 6, 10, 14]},
    "margin_sd": {"NFL": {"spread": 13.3, "total": 13.5}, "NBA": {"spread": 12.0, "total": 18.0}},
    "read_hours": {"sunday": [9, 10], "other": [7]}, "timezone_display": "America/Denver",
}


def snap(source, hs, total=44.0, sport="NFL", hp=-110, ap=-110, ts=NOW):
    return Snap(ts, source, sport, "E1", "Jets", "Chargers", NOW + timedelta(hours=3), hs, hp, ap, -170, 150, total, -110, -110)


def test_key_between():
    assert rules.key_between(-2.5, -3.5, [3, 7]) == 3
    assert rules.key_between(-3, -3.5, [3, 7]) == 3
    assert rules.key_between(-4, -4.5, [3, 7]) is None
    assert rules.key_between(-1, 1, [3, 7]) is None
    assert rules.key_between(6.5, 7.5, [3, 7]) == 7
    assert rules.key_between(3, 3, [3, 7]) is None


def test_no_alert_when_books_agree_or_gap_is_small_off_key():
    assert rules.off_market(snap("wagerhouse", -4.5), snap("draftkings", -4.5), CFG) == []
    assert rules.off_market(snap("wagerhouse", -4.5), snap("draftkings", -5), CFG) == []


def test_half_point_across_three_alerts_for_the_right_side():
    a = rules.off_market(snap("wagerhouse", -2.5), snap("draftkings", -3.5), CFG)
    assert len(a) == 1 and "Chargers -2.5" in a[0].text and "across 3" in a[0].text
    a = rules.off_market(snap("wagerhouse", -3.5), snap("draftkings", -2.5), CFG)
    assert "Jets +3.5" in a[0].text


def test_full_point_gap_alerts_and_bad_price_suppresses():
    a = rules.off_market(snap("wagerhouse", -8), snap("draftkings", -9), CFG)
    assert len(a) == 1 and "Better by 1 point." in a[0].text
    # same gap but Wagerhouse charges -160 for it: no value, no alert
    assert rules.off_market(snap("wagerhouse", -8, hp=-160), snap("draftkings", -9), CFG) == []


def test_stale_line_is_called_out():
    earlier = NOW - timedelta(hours=3)
    a = rules.off_market(snap("wagerhouse", -2.5), snap("draftkings", -3.5), CFG,
                         mkt_earlier=snap("draftkings", -2.5, ts=earlier), wh_earlier=snap("wagerhouse", -2.5, ts=earlier))
    assert a[0].kind == "moving" and "has not moved" in a[0].text


def test_total_gap():
    a = rules.off_market(snap("wagerhouse", -4.5, total=46), snap("draftkings", -4.5, total=44), CFG)
    assert len(a) == 1 and "Under 46" in a[0].text
    assert rules.off_market(snap("wagerhouse", -4.5, total=45), snap("draftkings", -4.5, total=44), CFG) == []


def test_alert_key_changes_only_when_lines_change():
    a = rules.off_market(snap("wagerhouse", -2.5), snap("draftkings", -3.5), CFG)[0]
    b = rules.off_market(snap("wagerhouse", -2.5), snap("draftkings", -3.5), CFG)[0]
    c = rules.off_market(snap("wagerhouse", -2.5), snap("draftkings", -4), CFG)[0]
    assert a.key == b.key != c.key


def test_watchlist():
    e = [{"id": 1, "team": "Jets", "market": "spread", "target": 3.5, "worst_price": -115}]
    assert rules.watchlist_hits(snap("wagerhouse", -3), snap("draftkings", -3), e) == []
    hit = rules.watchlist_hits(snap("wagerhouse", -3.5), snap("draftkings", -3), e)
    assert len(hit) == 1 and "Jets +3.5" in hit[0].text and "may not last" in hit[0].text
    assert rules.watchlist_hits(snap("wagerhouse", -3.5, ap=-125), snap("draftkings", -3.5), e) == []
    over = [{"id": 2, "team": "Chargers", "market": "over", "target": 44, "worst_price": None}]
    assert len(rules.watchlist_hits(snap("wagerhouse", -3, total=43.5), None, over)) == 1
    assert rules.watchlist_hits(snap("wagerhouse", -3, total=44.5), None, over) == []


def test_opener_digest_and_missed_reads():
    d = rules.opener_digest([snap("wagerhouse", -3)], {"E1": snap("draftkings", -3.5)})
    assert "posted 1 new game" in d.text and "Your book: Chargers -3" in d.text and "DraftKings has Chargers -3.5" in d.text
    assert "not a pick" in d.text
    assert rules.opener_digest([], {}) is None
    assert rules.missed_reads(NOW - timedelta(hours=30), NOW, 20) is not None
    assert rules.missed_reads(NOW - timedelta(hours=3), NOW, 20) is None
    assert rules.missed_reads(None, NOW, 20) is None


def test_schedule():
    sunday_10am_mt = datetime(2026, 11, 22, 17, 5, tzinfo=timezone.utc)
    assert poll.due(CFG, sunday_10am_mt, None)
    assert not poll.due(CFG, sunday_10am_mt, sunday_10am_mt - timedelta(minutes=30))
    assert poll.due(CFG, sunday_10am_mt, sunday_10am_mt - timedelta(minutes=60))
    assert not poll.due(CFG, sunday_10am_mt + timedelta(hours=5), None)          # 3pm Sunday not listed here
    assert poll.due(CFG, datetime(2026, 11, 23, 14, 0, tzinfo=timezone.utc), None)  # Monday 7am MT


@pytest.mark.parametrize("text,expected", [
    ("Kansas State +10 -110 25", ("Kansas State", "spread", 10, -110, 25)),
    ("Kansas State +10 -110 $20", ("Kansas State", "spread", 10, -110, 20)),
    ("Chiefs -3", ("Chiefs", "spread", -3, None, None)),
    ("Chiefs -3½ -120", ("Chiefs", "spread", -3.5, -120, None)),
    ("Bills ML -150 50", ("Bills", "ml", None, -150, 50)),
    ("Bills/Jets o47.5 -110", ("Bills/Jets", "over", 47.5, -110, None)),
    ("Bills u 47 -105 25", ("Bills", "under", 47, -105, 25)),
    ("Texas A&M +7 25", ("Texas A&M", "spread", 7, None, 25)),
])
def test_parse(text, expected):
    t = parse(text)
    assert (t.team, t.market, t.line, t.price, t.stake) == expected


@pytest.mark.parametrize("bad", ["", "+10 -110", "Chiefs", "Chiefs 3", "Bills ML 50", "Chiefs -3 abc", "Bills o"])
def test_parse_rejects(bad):
    with pytest.raises(ValueError):
        parse(bad)


def test_wagerhouse_line_is_turned_to_the_home_side():
    r = {"Team1ID": "Baltimore Ravens", "Team2ID": "Carolina Panthers", "FavoredTeamID": "Carolina Panthers",
         "Spread": -3, "SpreadAdj1": -120, "SpreadAdj2": 100, "MoneyLine1": 130, "MoneyLine2": -150,
         "TotalPoints": 43.5, "TtlPtsAdj1": -110, "TtlPtsAdj2": -110, "GameDateTime": "2026-11-22 13:00:01.000"}
    l = normalize_line("NFL", r)
    assert (l.home, l.home_spread, l.home_spread_price, l.away_spread_price) == ("Carolina Panthers", -3, 100, -120)
    assert (l.home_ml, l.away_ml, l.total) == (-150, 130, 43.5)
    r2 = dict(r, FavoredTeamID="Baltimore Ravens")
    assert normalize_line("NFL", r2).home_spread == 3


def test_client_refuses_anything_not_read_only():
    wh = Wagerhouse("u", "p")
    for op in ("Wager/placeBet", "Lines/saveWager", "Customer/changePassword", "Report/PendingDelete"):
        with pytest.raises(PermissionError):
            wh._post(op, {})
    assert not any(w in op.lower() for op in READ_ONLY for w in ("place", "save", "delete", "change", "update", "buyout"))


def test_merge_pull_replaces_refreshed_wagers_and_keeps_old_ones():
    old = {"weeks": [{"week": 0, "bow": "2026-11-10", "days": [1, 0, 0, 0, 0, 0, 0]}],
           "rows": [{"TicketNumber": 1, "WagerNumber": 1, "_week": 0, "v": "old"},
                    {"TicketNumber": 2, "WagerNumber": 1, "_week": 0, "v": "keep"}]}
    master = merge_pull(None, old)
    new = {"weeks": [{"week": 1, "bow": "2026-11-10", "days": [5, 0, 0, 0, 0, 0, 0]},
                     {"week": 0, "bow": "2026-11-17", "days": [2, 0, 0, 0, 0, 0, 0]}],
           "rows": [{"TicketNumber": 1, "WagerNumber": 1, "_week": 1, "v": "new"},
                    {"TicketNumber": 3, "WagerNumber": 1, "_week": 0, "v": "new"}]}
    m = merge_pull(master, new)
    assert sorted((r["TicketNumber"], r["v"], r["_bow"]) for r in m["rows"]) == [
        (1, "new", "2026-11-10"), (2, "keep", "2026-11-10"), (3, "new", "2026-11-17")]
    assert [(w["bow"], w["days"][0]) for w in m["weeks"]] == [("2026-11-10", 5), ("2026-11-17", 2)]


def test_missed_agent_slot_is_found():
    from datetime import datetime, timezone
    from engine.poll import missed_agent_slots
    cfg = {"timezone_display": "America/Denver", "agent": {"schedule": {"other": ["08:15", "15:15"], "sunday": ["08:15"]}}}
    now = datetime(2026, 11, 23, 23, 30, tzinfo=timezone.utc)     # Mon 4:30pm MT
    ran = [datetime(2026, 11, 23, 15, 16)]                        # 8:16am MT only
    miss = missed_agent_slots(cfg, now, ran)
    assert [m.hour for m in miss] == [22]                         # the 3:15pm MT slot (22:15 UTC)
    assert missed_agent_slots(cfg, now, ran + [datetime(2026, 11, 23, 22, 20)]) == []
