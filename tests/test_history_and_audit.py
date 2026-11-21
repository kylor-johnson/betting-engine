import json
from datetime import datetime, timezone

import pytest

from engine.bets import audit
from engine.bets.history import category, load_wagers, parse_wh_time
from engine.odds import espn


def row(**kw):
    base = dict(TicketNumber=1, WagerNumber=1, PlayNumber=1, ItemNumber=1, WagerType="S", LegWagerType="S",
                TicketWriter="Internet", AcceptedDateTime="2026-11-15 10:00:00.000",
                GameDateTime="2026-11-15 13:00:00.000", AmountWagered=2200, ToWinAmount=2000,
                AmountWon=2000, AmountLost=0, WagerStatus="W", FreePlayFlag="N", TeaserName="",
                Description="Football #268 Colts -5 -110", SportSubType="NFL                 ",
                Team1ID="Miami Dolphins", Team2ID="Indianapolis Colts", ChosenTeamID="Indianapolis Colts",
                AdjSpread=-5, OrigSpread=-5, AdjTotalPoints=0, OrigTotalPoints=-5, BuyPoints=0,
                TeaserPoints=0, TotalPointsOU="", FinalMoney=-110, Outcome="W",
                PeriodDescription="Game                ", _week=1)
    base.update(kw)
    return base


def write(tmp_path, rows):
    p = tmp_path / "pull.json"
    p.write_text(json.dumps({"rows": rows, "weeks": [{"week": 1, "days": [20, 0, 0, 0, 0, 0, 0]}]}))
    return p


def test_times_are_eastern():
    assert parse_wh_time("2026-11-15 13:00:00.000") == datetime(2026, 11, 15, 18, 0, tzinfo=timezone.utc)
    assert parse_wh_time("2026-07-04 13:00:00.000") == datetime(2026, 7, 4, 17, 0, tzinfo=timezone.utc)
    assert parse_wh_time("1900-01-01 00:00:00.000") is None


def test_duplicates_collapse_and_legs_survive(tmp_path):
    rows = [row(_figure_date=d) for d in ("a", "b", "c")]
    rows += [row(TicketNumber=2, WagerType="P", ItemNumber=i, LegWagerType="M", FinalMoney=-400,
                 AmountWon=0, AmountLost=5000, WagerStatus="L") for i in (1, 2, 1, 2)]
    ws = load_wagers(write(tmp_path, rows))
    assert len(ws) == 2
    assert len(ws[0].legs) == 1 and len(ws[1].legs) == 2
    assert ws[0].net == 20 and ws[1].net == -50
    assert category(ws[0]) == "Spread"
    assert category(ws[1]) == "Parlay, all moneyline favorites"


def test_free_play_loss_costs_nothing(tmp_path):
    ws = load_wagers(write(tmp_path, [row(FreePlayFlag="Y", AmountWon=0, AmountLost=10900, WagerStatus="L")]))
    assert ws[0].net == 0


def test_unknown_writer_fails_loudly(tmp_path):
    with pytest.raises(ValueError):
        load_wagers(write(tmp_path, [row(TicketWriter="MYSTERY")]))


def test_categories(tmp_path):
    ws = load_wagers(write(tmp_path, [
        row(TicketNumber=1, TicketWriter="GSLIVE"),
        row(TicketNumber=2, WagerType="T", TeaserPoints=13, TeaserName="WH 4tm 13pt"),
        row(TicketNumber=3, WagerType="M", LegWagerType="M", FinalMoney=-500),
        row(TicketNumber=4, BuyPoints=0.5),
        row(TicketNumber=5, WagerType="L", LegWagerType="L", SportSubType="NFLPLRPROPS"),
        row(TicketNumber=6, WagerType="M", LegWagerType="M", FinalMoney=108, SportSubType="MLB"),
    ]))
    assert [category(w) for w in ws] == [
        "Live in-game", "Teaser, 1-team 13-point", "Moneyline, -300 or shorter",
        "Spread, bought points", "Player prop", "Baseball and hockey straight bets"]


def fake_espn(monkeypatch, close_home=-5.5, open_home=-6.5, total_close=37.5, total_open=47.5):
    ev = espn.Event("1", "NFL", datetime(2026, 11, 15, 18, 0, tzinfo=timezone.utc),
                    {"displayName": "Indianapolis Colts", "location": "Indianapolis"},
                    {"displayName": "Miami Dolphins", "location": "Miami"}, True)
    mk = lambda hs, tot: espn.Lines(hs, -105, -115, -238, 195, tot, -110, -110)
    monkeypatch.setattr(espn, "scoreboard", lambda league, day, cache=None: [ev])
    monkeypatch.setattr(espn, "event_odds", lambda e, cache=None: espn.EventOdds("DraftKings", mk(open_home, total_open), mk(close_home, total_close)))


SD = {"NFL": {"spread": 13.3, "total": 13.5}}


def test_spread_clv_home_and_away(tmp_path, monkeypatch):
    fake_espn(monkeypatch)
    ws = load_wagers(write(tmp_path, [
        row(TicketNumber=1),                                                  # Colts -5, close -5.5: half point better
        row(TicketNumber=2, ChosenTeamID="Miami Dolphins", AdjSpread=6.5),    # Dolphins +6.5, close +5.5: one better
        row(TicketNumber=3, ChosenTeamID="Miami Dolphins", AdjSpread=5),      # worse than close
    ]))
    ps = audit.price_all(ws, SD, None)
    assert [p.pts_vs_close for p in ps] == [0.5, 1.0, -0.5]
    assert ps[0].pts_vs_open == 1.5 and ps[1].pts_vs_open == 0
    assert ps[1].ev > ps[2].ev
    assert all(p.ok for p in ps)


def test_total_clv_over_and_under(tmp_path, monkeypatch):
    fake_espn(monkeypatch)
    ws = load_wagers(write(tmp_path, [
        row(TicketNumber=1, WagerType="L", LegWagerType="L", AdjTotalPoints=40, TotalPointsOU="U", ChosenTeamID="x/y"),
        row(TicketNumber=2, WagerType="L", LegWagerType="L", AdjTotalPoints=40, TotalPointsOU="O", ChosenTeamID="x/y"),
    ]))
    ps = audit.price_all(ws, SD, None)
    assert ps[0].pts_vs_close == 2.5      # under 40 when it closed 37.5
    assert ps[1].pts_vs_close == -2.5


def test_moneyline_fair_value(tmp_path, monkeypatch):
    fake_espn(monkeypatch)
    ws = load_wagers(write(tmp_path, [row(WagerType="M", LegWagerType="M", FinalMoney=-200, AmountWagered=4000)]))
    p = audit.price_all(ws, SD, None)[0]
    assert p.price_vs_close == "better"       # -200 beats a -238 close
    assert p.fair_prob == pytest.approx(0.675, abs=0.005)
    assert p.ev > 0


def test_unpriced_reasons(tmp_path, monkeypatch):
    fake_espn(monkeypatch)
    ws = load_wagers(write(tmp_path, [
        row(TicketNumber=1, TicketWriter="GSLIVE"),
        row(TicketNumber=2, SportSubType="MLB"),
        row(TicketNumber=3, PeriodDescription="1st Half"),
        row(TicketNumber=4, AcceptedDateTime="2026-11-15 14:00:00.000"),
        row(TicketNumber=5, Team1ID="Nobody", Team2ID="Nowhere", ChosenTeamID="Nobody"),
    ]))
    reasons = [p.reason for p in audit.price_all(ws, SD, None)]
    assert reasons == ["live or same-game ticket", "sport out of scope", "first-half line (no reference price)",
                       "placed after the game started", "game not found on ESPN"]


def test_team_name_matching():
    assert espn.norm("Ohio St") == "ohio state"
    assert espn.norm("Mississippi") == "ole miss"
    assert espn.norm("Texas A&amp;M") == "texas a&m"
    assert espn.norm("Miami Florida") == "miami"
