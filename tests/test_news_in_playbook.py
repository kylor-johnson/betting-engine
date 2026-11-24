"""Decision 0029: sourced news moves the playbook number by the part Pinnacle has not priced; in a shown-only lane it can make a news pick."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from test_review18 import _pb_con

UTC = timezone.utc
NOW = datetime(2026, 11, 26, 18, 0, tzinfo=UTC)


def _game(**kw):
    g = {"event_id": "e1", "home": "UCLA Bruins", "away": "USC Trojans", "kick": NOW + timedelta(days=2),
         "own_home": 24.0, "own_away": 31.0, "own_margin": -7.0, "own_total": 55.0, "mkt_home": 24.0, "mkt_away": 31.0,
         "mkt_margin": -7.0, "mkt_total": 55.0, "wh_spread": 7.0, "wh_home_price": -110, "wh_away_price": -110,
         "wh_total": None, "wh_over": None, "wh_under": None}
    g.update(kw)
    return g


def _with_file(tmp_path, monkeypatch, text):
    from engine.picks import slate
    f = tmp_path / "adjustments.yaml"
    f.write_text(text)
    monkeypatch.setattr(slate, "ADJ_FILE", f)


ADJ = """adjustments:
  - game: "USC Trojans at UCLA Bruins"
    team: "USC Trojans"
    market: spread
    points: -4.0
    reason: "USC starting quarterback ruled out (test)."
    source: "https://example.com/x"
    added: "2026-11-26 10:00 MT"
    news_at: "2026-11-26 09:00 MT"
"""


def _pin(con, rows):
    for ts, sp in rows:
        con.execute("INSERT INTO line_snapshots (ts_utc, source, sport, event_id, home_spread, total) VALUES (?, 'pinnacle', 'College', 'e1', ?, 55)",
                    [ts.replace(tzinfo=None), sp])


def test_unpriced_news_moves_the_margin_and_priced_news_does_not(tmp_path, monkeypatch):
    from engine.picks import playbook as pb
    _with_file(tmp_path, monkeypatch, ADJ)
    con = _pb_con()
    _pin(con, [(NOW - timedelta(days=1), 7.0), (NOW, 7.0)])            # Pinnacle has not moved since the news
    games = [_game()]
    assert pb.apply_news(con, games, "College", NOW) == []
    assert games[0]["adj_margin"] == 4.0                                # USC 4 worse = home margin +4
    assert "unpriced" in games[0]["news"][0]
    con2 = _pb_con()
    _pin(con2, [(NOW - timedelta(days=1), 7.0), (NOW, 3.0)])           # Pinnacle already moved the full 4 toward UCLA
    g2 = [_game()]
    pb.apply_news(con2, g2, "College", NOW)
    assert g2[0].get("adj_margin", 0.0) == 0.0 and "priced" in g2[0]["news"][0]


def test_no_pinnacle_line_before_the_news_means_nothing_is_applied(tmp_path, monkeypatch):
    from engine.picks import playbook as pb
    _with_file(tmp_path, monkeypatch, ADJ)
    con = _pb_con()
    _pin(con, [(NOW, 7.0)])
    g = [_game()]
    pb.apply_news(con, g, "College", NOW)
    assert g[0].get("adj_margin", 0.0) == 0.0 and "not applied" in g[0]["news"][0]


def test_news_pick_only_when_news_is_what_clears_the_bar():
    from engine.picks import playbook as pb
    st = pb.settings({"playbook": {"sports": {"College": {"news_picks": True}}}}, "College")
    assert pb.is_news_pick({"market": "side", "edge": 0.05, "news_edge": 0.04}, st)
    assert not pb.is_news_pick({"market": "side", "edge": 0.08, "news_edge": 0.02}, st)     # script alone clears: not a news pick
    assert not pb.is_news_pick({"market": "side", "edge": 0.02, "news_edge": 0.02}, st)     # does not clear at all


def test_news_pick_is_staked_in_a_shown_lane_and_a_script_pick_is_not():
    from engine.picks import playbook as pb
    con = _pb_con()
    st = pb.settings({"playbook": {"sports": {"College": {"news_picks": True}}}}, "College")
    assert st["full_game"] == "show"
    news = pb._paper_or_staked(con, st, {"grade": "B", "event_id": "e1", "news_pick": True}, 0.5, 12.5, "B pick", 25, True)
    plain = pb._paper_or_staked(con, st, {"grade": "B", "event_id": "e2"}, 0.5, 12.5, "B pick", 25, True)
    assert news[:2] == (0.5, 12.5) and plain[:2] == (0.0, 0.0)


def test_candidates_carry_news_into_our_number():
    from engine import stale
    from engine.picks import playbook as pb
    st = pb.settings({}, "College")
    lands = stale.landings("College", {})
    g = _game(adj_margin=4.0, news=["News, USC Trojans -4 (unpriced: ...): test"])
    cands = [c for c in pb.candidates([g], st, lands) if c["market"] == "side" and c["side"] == "home"]
    assert cands and cands[0]["news_edge"] > 0 and cands[0]["news"]


def test_team_name_that_matches_neither_team_is_reported_not_dropped(tmp_path, monkeypatch):
    """Research 22: an entry whose team is misspelled used to vanish with no trace; it must say why it did not count."""
    from engine.picks import playbook as pb
    _with_file(tmp_path, monkeypatch, ADJ.replace('team: "USC Trojans"', 'team: "Southern Cal"'))
    con = _pb_con()
    _pin(con, [(NOW - timedelta(days=1), 7.0), (NOW, 7.0)])
    g = [_game()]
    pb.apply_news(con, g, "College", NOW)
    assert g[0].get("adj_margin", 0.0) == 0.0
    assert g[0]["news"] and "matches neither" in g[0]["news"][0]
    assert "NO" in "\n".join(pb.news_section(g))


def test_entry_for_a_game_wagerhouse_names_differently_is_listed(tmp_path, monkeypatch):
    from engine.picks import playbook as pb
    _with_file(tmp_path, monkeypatch, ADJ.replace("USC Trojans at UCLA Bruins", "Southern Cal at UCLA"))
    assert pb.unmatched_news([_game()]) == ["Southern Cal at UCLA"]
    _with_file(tmp_path, monkeypatch, ADJ)
    assert pb.unmatched_news([_game()]) == []


def test_news_pick_wins_its_game_over_a_bigger_pick_that_cannot_be_staked():
    """Research 22, finding 3 (Kylor 2026-11-24): in a shown-only lane, one pick per game is chosen AFTER the news-pick test, so a bigger
    script-only total cannot hide the news side on the same game."""
    from engine.picks import playbook as pb
    st = pb.settings({"playbook": {"sports": {"College": {"news_picks": True}}}}, "College")
    base = {"event_id": "e1", "check": False, "kick": NOW}
    total = {**base, "market": "total", "side": "over", "edge": 0.06, "news_edge": 0.0}
    side = {**base, "market": "side", "side": "away", "edge": 0.04, "news_edge": 0.02}
    graded = pb.grade_all([total, side], st)
    assert len(graded) == 1 and graded[0]["market"] == "side"
    assert graded[0]["grade"] == "B" and graded[0].get("news_pick") and "News pick" in graded[0]["note"]
    # without the news side, the script-only total is shown only (C)
    only = pb.grade_all([{**total}], st)
    assert only[0]["grade"] == "C" and "Shown only" in only[0]["note"]


def test_nfl_script_quarterback_flag_is_off_while_the_news_is_added_as_unpriced_points():
    """Research 22, finding 6: the script's backup-quarterback flag and the unpriced news must not both count the same absence."""
    from engine.picks import playbook as pb
    t0 = datetime(2026, 11, 26, 16, 0, tzinfo=UTC)                 # news_at 9:00 MT
    e = {"game": "USC Trojans at UCLA Bruins", "team": "USC Trojans", "market": "spread", "points": -4.0, "news_at": "2026-11-26 09:00 MT"}
    unpriced = [(t0 - timedelta(hours=1), 7.0, 55), (t0 + timedelta(hours=1), 7.0, 55)]
    priced = [(t0 - timedelta(hours=1), 7.0, 55), (t0 + timedelta(hours=1), 3.0, 55)]      # USC weaker: UCLA +7 to +3
    assert not pb.qb_out([e], unpriced, "UCLA Bruins", "USC Trojans", "USC Trojans")     # news adds the 4 points; flag off
    assert pb.qb_out([e], priced, "UCLA Bruins", "USC Trojans", "USC Trojans")           # Pinnacle has it; the script knows he is out
    assert pb.qb_out([{**e, "news_at": None}], unpriced, "UCLA Bruins", "USC Trojans", "USC Trojans")   # not countable as news
    assert not pb.qb_out([e], priced, "UCLA Bruins", "USC Trojans", "UCLA Bruins")       # the other team
