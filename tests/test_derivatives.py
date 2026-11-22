import json

from engine.odds import derivatives


def test_pinnacle_rows_parse_period_team_total_and_prop(monkeypatch):
    matchups = [
        {"id": 1, "type": "matchup", "parent": None, "isLive": False, "startTime": "2026-11-22T18:00:00Z",
         "participants": [{"alignment": "home", "name": "H"}, {"alignment": "away", "name": "A"}]},
        {"id": 2, "type": "special", "parentId": 1, "isLive": False, "special": {"description": "X Total Receiving Yards"},
         "participants": [{"id": 20, "name": "Over"}, {"id": 21, "name": "Under"}]},
    ]
    markets = [
        {"matchupId": 1, "period": 1, "type": "spread", "status": "open",
         "prices": [{"designation": "home", "points": -3.5, "price": -110}, {"designation": "away", "points": 3.5, "price": -110}]},
        {"matchupId": 1, "period": 0, "type": "team_total", "status": "open", "side": "home",
         "prices": [{"designation": "over", "points": 23.5, "price": -116}, {"designation": "under", "points": 23.5, "price": -101}]},
        {"matchupId": 2, "period": 0, "type": "total", "status": "open",
         "prices": [{"participantId": 20, "points": 21.5, "price": 134}, {"participantId": 21, "points": 21.5, "price": -163}]},
        {"matchupId": 1, "period": 3, "type": "total", "status": "closed",
         "prices": [{"designation": "over", "points": 9.5, "price": -110}, {"designation": "under", "points": 9.5, "price": -110}]},
    ]
    monkeypatch.setattr(derivatives, "_fetch", lambda url, what: json.dumps(matchups if url.endswith("matchups") else markets))
    rows = derivatives.pinnacle_rows("NFL")
    kinds = {(r[4], r[5]) for r in rows}
    assert kinds == {("spread", "1st Half"), ("team_total", "Game"), ("prop", "Game")}   # closed market skipped
    prop = next(r for r in rows if r[4] == "prop")
    assert prop[7:] == (21.5, 134, -163) and prop[6] == "X Total Receiving Yards"
