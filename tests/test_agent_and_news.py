from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from engine.picks import agent, card, news
from test_picks import CFG, REASONS, SHEET, decide


def player(pid="1", status="Questionable", pos="QB"):
    return news.Player(pid, "Minnesota Vikings", "Kyler Murray", pos, status, "2026-11-20T19:49", "hamstring")


def test_only_real_quarterback_changes_matter():
    prev = {"1": "Questionable", "2": "Active", "3": "Out", "4": "Active"}
    players = [player("1", "Out"), player("2", "Active"), player("3", "Active"), player("4", "Out", pos="WR"), player("5", "Doubtful")]
    ch = news.diff(prev, players)
    assert [c.player.player_id for c in ch] == ["1", "3", "4", "5"]          # unchanged player 2 is not a change
    assert [c.matters for c in ch] == [True, True, False, True]             # the receiver is logged, not alerted
    assert "Questionable → Out" in ch[0].text() and "not listed → Doubtful" in ch[3].text()


def test_active_to_active_note_update_is_not_news():
    assert news.diff({"1": "Active"}, [player("1", "Active")]) == []
    c = news.Change(player("9", "Active"), None)                             # newly listed but healthy
    assert not c.matters


MT = ZoneInfo("America/Denver")


def row(status, **kw):
    base = {"event_id": "1", "market": "spread", "side": "home", "game": "Jets at Chargers", "pick": "Chargers -2.5",
            "price": -110, "status": status, "units": 1, "dollars": 25, "value": 0.06, "edge_points": 0.6,
            "dont_bet_past": "Chargers -2.5", "downgraded": None, "kick": datetime(2026, 11, 22, 21, 5, tzinfo=timezone.utc),
            "decision": {"reasons": REASONS, "summary": "Herbert is back and the book has not moved.",
                         "condition": "Herbert is active.", "why_pass": "nothing found"}}
    base.update(kw)
    return base


def test_first_line_of_every_message_is_the_instruction():
    key = "1|spread|home"
    assert agent.changes({}, [row("Pass")], MT, "NFL") == []
    bet = agent.changes({}, [row("Bet")], MT, "NFL")[0]
    assert bet.splitlines()[0] == "NFL · BET NOW"
    assert "Chargers -2.5 (-110)" in bet and "Stake: $25" in bet and "worse than -2.5" in bet and "Why: Herbert is back" in bet
    assert agent.changes({key: {"status": "Bet", "pick": "Chargers -2.5"}}, [row("Bet")], MT, "NFL") == []
    wait = agent.changes({}, [row("Conditional", units=0.5, dollars=12.5)], MT, "NBA", " after the 3:15 PM check")[0]
    assert wait.splitlines()[0] == "NBA · WAIT, DO NOT BET YET"
    assert "Bet $12.5 ONLY IF: Herbert is active." in wait and "after the 3:15 PM check with BET NOW or CANCELLED" in wait
    up = agent.changes({key: {"status": "Conditional", "pick": "Chargers -2.5"}}, [row("Bet")], MT, "NFL")[0]
    assert up.splitlines()[0] == "NFL · BET NOW (the condition was met)"
    gone = agent.changes({key: {"status": "Bet", "pick": "Chargers -2.5"}}, [row("Pass", downgraded="Value gone: now -3.5")], MT, "NFL")[0]
    assert gone.splitlines()[0] == "NFL · CANCELLED, DO NOT BET" and "Value gone" in gone


def test_limit_number_is_pulled_from_the_pick():
    assert agent._limit(row("Bet", dont_bet_past="Oklahoma City Thunder +2.5")) == "+2.5"
    assert agent._limit(row("Bet", dont_bet_past="Over 44.5")) == "44.5"
    assert agent._limit(row("Bet", dont_bet_past=None)) == "-2.5"


def test_repricing_downgrades_a_bet_whose_value_is_gone(tmp_path):
    d, note = decide(tmp_path, [{"game": "Jets at Chargers", "market": "spread", "side": "home", "status": "Bet", "reasons": REASONS, "summary": "s"}])
    import copy
    moved = copy.deepcopy(SHEET)
    side = moved["games"][0]["markets"][0]["sides"][0]
    side.update(numbers_say_bet=False, pick="Chargers -3.5", value=-0.05, dont_bet_past="Chargers -2.5")
    text, rows = card.build(moved, d, note, CFG, strict=False)
    assert rows[0]["status"] == "Pass" and "Value gone" in rows[0]["downgraded"] and "**No bets.**" in text
