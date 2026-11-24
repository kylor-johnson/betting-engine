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
