from datetime import datetime, timezone

from engine.picks import nba_news, player_news as pn

PAGE = """
<div class="PlayerNewsPost" data-date="2026-11-22T21:20:28.753Z">
 <span class="PlayerNewsPost-firstName">Myron</span> <span class="PlayerNewsPost-lastName">Gardner</span>
 <span class="PlayerNewsPost-team-abbr">MIA</span><span class="PlayerNewsPost-position">Forward</span>
 <button data-share-url="https://www.nbcsports.com/fantasy/basketball/player-news/2026-11-22/myron-gardner"></button>
 <h3 class="PlayerNewsPost-headline">Myron Gardner (hamstring) is available to play against the Thunder on Sunday.</h3>
 <div class="PlayerNewsPost-source">Source:&nbsp;<a href="https://x.com/Anthony_Chiang/status/2124613349967265864?s=20">Anthony Chiang</a></div>
</div>
<div class="PlayerNewsPost" data-date="2026-11-22T21:03:29.000Z">
 <span class="PlayerNewsPost-firstName">Mitchell</span> <span class="PlayerNewsPost-lastName">Robinson</span>
 <span class="PlayerNewsPost-team-abbr">BOS</span>
 <button data-share-url="https://www.nbcsports.com/x/robinson"></button>
 <h3 class="PlayerNewsPost-headline">Mitchell Robinson (illness) has been ruled out against the Warriors on Sunday.</h3>
</div>"""


def test_parse_posts_and_tweet_time():
    posts = pn.parse(PAGE, "NBA")
    assert [p.player for p in posts] == ["Myron Gardner", "Mitchell Robinson"]
    p = posts[0]
    assert p.signal == "playing" and p.team == "MIA" and p.source == "Anthony Chiang"
    assert p.source_time is not None and p.source_time < p.posted          # tweet came before the relay
    assert p.kind == "beat" and "Miami Heat beat writer" in p.source_label
    assert posts[1].signal == "not playing" and posts[1].source_time is None


def test_signal_wording():
    cases = {"X will not be active Sunday": "not playing", "X is doubtful to play": "not playing",
             "X is probable for Monday": "playing", "X is questionable": "uncertain",
             "Coach said X was a full participant in practice": None, "X caught 9 passes for 54 yards": None,
             "X is not on the injury report for Monday": "playing", "X has been ruled out": "not playing"}
    for h, want in cases.items():
        assert pn.signal(h) == want, h


def test_source_kinds_from_reporter_list():
    assert pn.source_kind("Adam Schefter", "https://x.com/AdamSchefter/status/1")[0] == "insider"
    assert pn.source_kind("Tom Pelissero", "https://x.com/TomPelissero/status/1")[0] == "insider"
    assert pn.source_kind("Shams Charania", "https://x.com/ShamsCharania/status/1")[0] == "insider"
    assert pn.source_kind("NBA Injury Report", "https://ak-static.cms.nba.com/referee/injury/a.pdf")[0] == "official"
    assert pn.source_kind("Somebody", "https://x.com/somebody/status/1")[0] == "other"


def test_official_report_rows():
    text = ("   11/22/2026  01:30 (ET)  DET@ATL   Atlanta  Hawks     Castro, Rafael        Out        G  League  -Two-Way\n"
            "                                   McCollum,   CJ                 Out        Injury/Illness\n"
            "                                   Holland  II,Ronald             Available\n"
            "                                   Washington,  P.J.              Doubtful   Illness\n")
    got = nba_news.parse_official(text)
    assert got == {"rafael castro": "Out", "cj mccollum": "Out", "ronald holland": "Available", "pj washington": "Doubtful"}


def test_official_changes_include_players_dropped_from_the_report():
    import duckdb
    con = duckdb.connect()
    now = datetime(2026, 11, 22, 22, tzinfo=timezone.utc)
    assert nba_news.check_official(con, now, "a.pdf", {"star": "Questionable", "bench": "Out"})[1] is True
    ch, first = nba_news.check_official(con, now, "b.pdf", {"star": "Out"})
    assert not first and set(ch) == {("star", "Questionable", "Out"), ("bench", "Out", nba_news.OFF)}
