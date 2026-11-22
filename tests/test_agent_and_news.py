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


def row(status, **kw):
    base = {"event_id": "1", "market": "spread", "side": "home", "game": "Jets at Chargers", "pick": "Chargers -2.5",
            "price": -110, "status": status, "units": 1, "dollars": 25, "value": 0.06, "edge_points": 0.6,
            "dont_bet_past": "Chargers -2.5", "downgraded": None,
            "decision": {"reasons": REASONS, "condition": "Herbert active", "why_pass": "nothing found"}}
    base.update(kw)
    return base


def test_alerts_only_for_changes():
    key = "1|spread|home"
    assert agent.changes({}, [row("Pass")]) == []
    new = agent.changes({}, [row("Bet")])
    assert len(new) == 1 and new[0].startswith("NEW BET: Chargers -2.5 (-110)") and "Don't bet past: Chargers -2.5" in new[0]
    assert agent.changes({key: {"status": "Bet", "pick": "Chargers -2.5"}}, [row("Bet")]) == []
    up = agent.changes({key: {"status": "Conditional", "pick": "Chargers -2.5"}}, [row("Bet")])
    assert up[0].startswith("CONDITIONAL IS NOW A BET")
    cond = agent.changes({}, [row("Conditional", units=0.5, dollars=12.5)])
    assert "NEW CONDITIONAL" in cond[0] and "Only if: Herbert active" in cond[0] and "0.5u ($12.5)" in cond[0]
    gone = agent.changes({key: {"status": "Bet", "pick": "Chargers -2.5"}}, [row("Pass", downgraded="Value gone: now -3.5")])
    assert gone[0].startswith("WITHDRAWN: Chargers -2.5") and "Value gone" in gone[0]


def test_repricing_downgrades_a_bet_whose_value_is_gone(tmp_path):
    d, note = decide(tmp_path, [{"game": "Jets at Chargers", "market": "spread", "side": "home", "status": "Bet", "reasons": REASONS}])
    import copy
    moved = copy.deepcopy(SHEET)
    side = moved["games"][0]["markets"][0]["sides"][0]
    side.update(numbers_say_bet=False, pick="Chargers -3.5", value=-0.05, dont_bet_past="Chargers -2.5")
    text, rows = card.build(moved, d, note, CFG, strict=False)
    assert rows[0]["status"] == "Pass" and "Value gone" in rows[0]["downgraded"] and "**No bets.**" in text
