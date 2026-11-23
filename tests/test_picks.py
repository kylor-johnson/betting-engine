import pytest
import yaml

from engine.odds.espn import SourceError
from engine.picks import card, ratings
from engine.picks.pricing import Landing


def spread_rows():
    """Home favored by 3 in every game; margins land on 3 a lot, like real football."""
    rows = []
    for margin, n in ((3, 15), (7, 9), (-3, 6), (1, 5), (2, 5), (4, 5), (5, 4), (6, 6), (10, 6), (-1, 4), (-7, 5),
                      (14, 5), (-10, 4), (17, 4), (0, 1), (-4, 4), (8, 4), (-14, 4), (21, 4)):
        rows += [(-3.0, float(margin))] * (n * 6)
    return rows


def test_a_half_point_through_three_is_worth_much_more_than_one_through_five():
    land = Landing(spread_rows(), "spread", window=1.0, min_n=100)
    at = lambda line: land.probs(-3.0, line, "home")[0] + land.probs(-3.0, line, "home")[1] / 2
    through_three = at(-2.5) - at(-3.5)
    through_five = at(-4.5) - at(-5.5)
    assert through_three > 0.10 and through_five < 0.06 and through_three > 2 * through_five


def test_fair_line_is_a_coin_flip_and_sides_mirror():
    land = Landing(spread_rows(), "spread", window=1.0, min_n=100)
    win, push, lose = land.probs(-3.0, -3.0, "home")
    assert win + push / 2 == pytest.approx(0.5)
    assert land.probs(-3.0, -3.0, "away") == (lose, push, win)
    assert win + push + lose == pytest.approx(1.0)


def test_value_and_dont_bet_past():
    land = Landing(spread_rows(), "spread", window=1.0, min_n=100)
    assert land.value(-3.0, -3.0, "home", -110) < 0          # fair line at -110 loses the vig
    assert land.value(-3.0, -2.5, "home", -110) > 0.02       # the hook under 3 is a bet
    is_bet, limit = land.limit(-3.0, -1.5, "home", -110, 0.02)
    assert is_bet and limit == -2.5                          # still good at -2.5, not at -3
    is_bet, would = land.limit(-3.0, -3.5, "home", -110, 0.02)
    assert not is_bet and would == -2.5
    # lines are always the HOME spread: the dog at +3.5 is home spread -3.5
    is_bet, limit = land.limit(-3.0, -3.5, "away", -110, 0.02)
    assert is_bet and limit == -3.5                          # dog +3.5 is a bet; +3 is not


def test_totals_over_and_under():
    rows = [(44.0, float(t)) for t in range(30, 60)] * 10
    land = Landing(rows, "total", window=3.0, min_n=100)
    assert land.probs(44.0, 42.0, "over")[0] > 0.5 > land.probs(44.0, 42.0, "under")[0]
    assert land.value(44.0, 41.0, "over", -110) > land.value(44.0, 43.0, "over", -110)


def test_price_lean_moves_the_fair_line_the_right_way():
    land = Landing(spread_rows(), "spread", window=1.0, min_n=100)
    assert land.fair_from_price(-3.0, 0.55) < -3.0 < land.fair_from_price(-3.0, 0.45)


def test_market_ratings_recover_team_strength():
    truth = {"A": 6.0, "B": 2.0, "C": -2.0, "D": -6.0}
    games, week = [], 1
    teams = list(truth)
    for rnd in range(12):
        for i, h in enumerate(teams):
            a = teams[(i + 1 + rnd % 3) % 4]
            if a == h:
                continue
            games.append({"season": "2026", "gameday": f"2026-09-{week:02d}", "week": str(week), "game_type": "REG",
                          "home_team": h, "away_team": a, "location": "Home",
                          "spread_line": str(truth[h] - truth[a] + 1.7), "total_line": "44"})
        week += 1
    r, tend, avg, n = ratings.market_ratings(games, 2026, "2026-12-31", hfa=1.7)
    assert n == len(games) and avg == pytest.approx(44)
    for t in truth:
        assert r[t] == pytest.approx(truth[t], abs=0.6)
    assert r["A"] > r["B"] > r["C"] > r["D"]


SHEET = {"built_utc": "2026-11-21T23:30:00+00:00", "problems": [], "adjustments_used": [], "games": [{
    "event_id": "1", "game": "Jets at Chargers", "start_utc": "2026-11-22T21:05:00+00:00", "notes": [], "markets": [
        {"market": "spread", "rating_line": -4.0, "public_systems_line": -2.0, "adjustment_points": 0, "model_line": -3.0,
         "pinnacle_line": -3.0, "fair_line": -3.1, "book_line": -2.5, "sides": [
             {"side": "home", "pick": "Chargers -2.5", "price": -110, "value": 0.06, "edge_points": 0.6,
              "numbers_say_bet": True, "dont_bet_past": "Chargers -2.5", "win": 0.55, "push": 0.0},
             {"side": "away", "pick": "Jets +2.5", "price": -110, "value": -0.15, "edge_points": -0.6,
              "numbers_say_bet": False, "dont_bet_past": "Jets +3.5", "win": 0.45, "push": 0.0}]}]}]}
CFG = {"timezone_display": "America/Denver", "unit": 25,
       "picks": {"max_units": 1, "conditional_units": 0.5, "market_weight": 0.55}}
REASONS = {"price": "p", "matchup": "m", "situation": "s", "kills_it": "k"}


def decide(tmp_path, items):
    p = tmp_path / "d.yaml"
    p.write_text(yaml.safe_dump({"decisions": items}))
    return card.load_decisions(p)


def test_card_uses_sheet_numbers_and_sizes_from_config(tmp_path):
    d, note = decide(tmp_path, [{"game": "Jets at Chargers", "market": "spread", "side": "home", "status": "Bet", "reasons": REASONS, "summary": "s"}])
    text, rows = card.build(SHEET, d, note, CFG)
    assert "Chargers -2.5 (-110)" in text and "1u / $25" in text and "Sunday Nov 22" in text
    assert rows[0]["dollars"] == 25


def test_a_bet_the_numbers_do_not_support_is_refused(tmp_path):
    d, note = decide(tmp_path, [
        {"game": "Jets at Chargers", "market": "spread", "side": "home", "status": "Pass", "why_pass": "x"},
        {"game": "Jets at Chargers", "market": "spread", "side": "away", "status": "Bet", "reasons": REASONS, "summary": "s"}])
    with pytest.raises(SourceError, match="refused"):
        card.build(SHEET, d, note, CFG)


def test_flagged_side_without_a_decision_fails_loudly(tmp_path):
    d, note = decide(tmp_path, [])
    with pytest.raises(SourceError, match="no decision"):
        card.build(SHEET, d, note, CFG)


@pytest.mark.parametrize("bad", [
    {"game": "g", "market": "spread", "side": "home", "status": "Bet", "reasons": REASONS, "stake": 75},
    {"game": "g", "market": "spread", "side": "home", "status": "Bet", "reasons": REASONS, "line": -2.5},
    {"game": "g", "market": "spread", "side": "home", "status": "Bet", "reasons": {"price": "only this"}},
    {"game": "g", "market": "spread", "side": "home", "status": "Conditional", "reasons": REASONS, "summary": "s"},
    {"game": "g", "market": "spread", "side": "home", "status": "Bet", "reasons": REASONS},
    {"game": "g", "market": "spread", "side": "home", "status": "Conditional", "reasons": REASONS, "summary": "s", "condition": "word " * 40},
    {"game": "g", "market": "spread", "side": "home", "status": "Pass"},
    {"game": "g", "market": "spread", "side": "home", "status": "Lock"},
])
def test_decisions_cannot_carry_numbers_or_skip_reasons(tmp_path, bad):
    with pytest.raises(SourceError):
        decide(tmp_path, [bad])


def _card_text(use_model):
    sheet = {**SHEET, "settings": {"use_model_leg": use_model, "market_weight": 0.55}}
    return card.build(sheet, {}, "", CFG, strict=False)[0]


def test_card_sentence_about_fair_line_follows_the_setting():
    off, on = _card_text(False), _card_text(True)
    assert "55%" not in off and "100%" in off and "switched off" in off
    assert "55% Pinnacle" in on and "45% model" in on


def test_card_sentence_matches_the_real_config():
    from engine import config
    pc = config.load_config()["picks"]
    sentence = card.fair_sentence({"settings": {"use_model_leg": bool(pc.get("use_model_leg", False)),
                                                "market_weight": pc["market_weight"]}}, pc)
    assert ("100%" in sentence) == (not pc.get("use_model_leg", False))


def test_one_position_per_game_keeps_the_stronger_and_passes_the_other(tmp_path):
    import copy
    sheet = copy.deepcopy(SHEET)
    sheet["games"][0]["markets"].append({"market": "total", "fair_line": 44.0, "book_line": 45.0, "sides": [
        {"side": "under", "pick": "Under 45", "price": -110, "value": 0.03, "edge_points": 1.0, "numbers_say_bet": True,
         "dont_bet_past": "Under 44.5", "win": 0.53, "push": 0.0}]})
    d, note = decide(tmp_path, [
        {"game": "Jets at Chargers", "market": "spread", "side": "home", "status": "Bet", "reasons": REASONS, "summary": "s"},
        {"game": "Jets at Chargers", "market": "total", "side": "under", "status": "Bet", "reasons": REASONS, "summary": "s"}])
    text, rows = card.build(sheet, d, note, CFG)
    live = [r for r in rows if r["status"] != "Pass"]
    assert [r["pick"] for r in live] == ["Chargers -2.5"]           # value 0.06 beats 0.03
    cut = [r for r in rows if r["pick"] == "Under 45"][0]
    assert cut["status"] == "Pass" and cut["dollars"] == 0 and "One position per game" in cut["downgraded"]
