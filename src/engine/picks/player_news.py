"""Reporter news, fast: Rotoworld's player-news feed (NBC Sports), NBA and NFL.

Why this and not X: X's API costs money (the no-paid-data rule) and its pages need a login and JavaScript.
Rotoworld posts every beat-reporter and national-insider item (Schefter, Shams, team beat writers, the
official NBA injury report) with a link to the original X post, usually 3 to 15 minutes after the tweet
(measured from the tweet ids, 2026-11-22). ESPN's injury table, by contrast, often still says Questionable
after a reporter has said the player will play.

Each post is read into: player, team, position, when posted, when the source tweeted (from the X post id),
headline, source name and link, and a plain signal from the headline: "playing", "not playing", "uncertain"
or none (a news item that is not about availability).
"""
from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta, timezone

from engine.odds.espn import SourceError

URLS = {"NBA": "https://www.nbcsports.com/fantasy/basketball/player-news",
        "NFL": "https://www.nbcsports.com/fantasy/football/player-news"}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS player_news (
  url VARCHAR PRIMARY KEY, sport VARCHAR, player VARCHAR, team VARCHAR, position VARCHAR, posted_utc TIMESTAMP,
  source_utc TIMESTAMP, headline VARCHAR, source VARCHAR, source_url VARCHAR, signal VARCHAR, seen_utc TIMESTAMP);
"""

# headline wording -> signal. Order matters: the first match wins, most specific first.
NOT_PLAYING = (r"\bruled out\b", r"\bwon'?t play\b", r"\bwill not play\b", r"\bwill not suit up\b", r"\bwon'?t suit up\b",
               r"\bwill miss\b", r"\bis out\b", r"\bare out\b", r"\bout for\b", r"\binactive\b", r"\bwill sit\b", r"\bnot playing\b",
               r"\bwill be held out\b", r"\bdid not travel\b", r"\bplaced on (?:ir|injured reserve)\b", r"\bout (?:sunday|monday|tuesday|wednesday|thursday|friday|saturday)\b",
               r"\bwill not return\b", r"\bdoubtful\b", r"\bnot expected to play\b", r"\bunlikely to play\b")
PLAYING = (r"\bwill play\b", r"\bis available\b", r"\bavailable to play\b", r"\bexpected to play\b", r"\bplans to play\b",
           r"\bwill start\b", r"\bis starting\b", r"\bwill suit up\b", r"\bset to play\b", r"\bon track to play\b", r"\bprobable\b",
           r"\bnot on the injury report\b", r"\bcleared to play\b", r"\bwill return\b", r"\bwill make (?:his|her) return\b",
           r"\bactive\b", r"\bupgraded to available\b", r"\bgood to go\b", r"\blikely to play\b")
UNCERTAIN = (r"\bquestionable\b", r"\bgame-time decision\b", r"\bgametime decision\b", r"\bday-to-day\b", r"\buncertain\b")
NOT_PREFIX = re.compile(r"\b(?:not|isn'?t|won'?t be|unlikely to be)\s+(?:be\s+)?(?:active|available|probable)\b")


REPORTERS_FILE = Path(__file__).resolve().parents[3] / "ops" / "reporters.yaml"
_REPORTERS: dict | None = None


def reporters() -> dict[str, dict]:
    """X handle (lowercase) -> {name, team, kind, sport} from ops/reporters.yaml."""
    global _REPORTERS
    if _REPORTERS is None:
        import yaml
        data = yaml.safe_load(REPORTERS_FILE.read_text()) if REPORTERS_FILE.exists() else {}
        _REPORTERS = {r["handle"].lower(): {**r, "sport": sport} for sport, rows in (data or {}).items() for r in rows or []}
    return _REPORTERS


def source_kind(source_name: str, source_url: str) -> tuple[str, str]:
    """(kind, label): 'official' injury report, a listed 'insider' or 'beat' writer, a 'team' account, or 'other'."""
    u = (source_url or "").lower()
    if "cms.nba.com/referee/injury" in u or "official.nba.com" in u or source_name.lower() in ("nba injury report", "nfl injury report"):
        return "official", "official injury report"
    m = re.search(r"(?:x|twitter)\.com/([a-z0-9_]+)/status", u)
    if m:
        r = reporters().get(m.group(1))
        if r:
            return r["kind"], f"{r['name']} ({'national insider' if r['kind'] == 'insider' else r['team'] + ' beat writer'})"
        if source_name.strip().lower() in team_names():
            return "team", f"{source_name} (team account)"
    return "other", source_name or "Rotoworld"


def team_names() -> set[str]:
    """Full NFL and NBA team names, lowercase (team X accounts post as their full name)."""
    from engine.models.props import TEAM_NAMES
    from engine.picks.nba_news import NBA_TEAMS
    return {t.lower() for t in TEAM_NAMES} | {t.lower() for t in NBA_TEAMS}


def signal(headline: str) -> str | None:
    h = headline.lower().replace("’", "'")
    if re.search(r"\bpractice[sd]?\b|\bparticipant\b|\bpracticing\b", h) and not re.search(r"\bwill play\b|\bruled out\b|\bwill miss\b", h):
        return None      # practice reports are a hint, not a decision
    if NOT_PREFIX.search(h):
        return "not playing"
    for pats, sig in ((NOT_PLAYING, "not playing"), (UNCERTAIN, "uncertain"), (PLAYING, "playing")):
        if any(re.search(p, h) for p in pats):
            return sig
    return None


def tweet_time(url: str) -> datetime | None:
    m = re.search(r"(?:x|twitter)\.com/[^/]+/status/(\d+)", url or "")
    if not m:
        return None
    return datetime.fromtimestamp(((int(m.group(1)) >> 22) + 1288834974657) / 1000, timezone.utc)


@dataclass
class Post:
    url: str
    sport: str
    player: str
    team: str
    position: str
    posted: datetime
    headline: str
    source: str
    source_url: str

    @property
    def signal(self) -> str | None:
        return signal(self.headline)

    @property
    def source_time(self) -> datetime | None:
        return tweet_time(self.source_url)

    @property
    def kind(self) -> str:
        return source_kind(self.source, self.source_url)[0]

    @property
    def source_label(self) -> str:
        return source_kind(self.source, self.source_url)[1]


def _g(pat: str, s: str) -> str:
    m = re.search(pat, s, re.S)
    return html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ""


def parse(page: str, sport: str) -> list[Post]:
    out = []
    for p in page.split('class="PlayerNewsPost"')[1:]:
        posted = _g(r'data-date="([^"]+)"', p)
        url = _g(r'data-share-url="([^"]+)"', p)
        headline = _g(r'PlayerNewsPost-headline">(.*?)</h3>', p)
        if not posted or not url or not headline:
            continue
        name = (_g(r'PlayerNewsPost-firstName">(.*?)</', p) + " " + _g(r'PlayerNewsPost-lastName">(.*?)</', p)).strip()
        if not name:
            name = _g(r'data-object-name="([^"]+)"', p)
        src = re.search(r'PlayerNewsPost-source">.*?<a href="([^"]+)"[^>]*>([^<]+)</a>', p, re.S)
        out.append(Post(url, sport, re.sub(r"<[^>]+>", "", name), _g(r'PlayerNewsPost-team-abbr">([^<]+)', p),
                        _g(r'PlayerNewsPost-position">([^<]+)', p),
                        datetime.fromisoformat(posted.replace("Z", "+00:00")), re.sub(r"<[^>]+>", "", headline),
                        html.unescape(src.group(2)).strip() if src else "", html.unescape(src.group(1)) if src else ""))
    return out


def fetch(sport: str, since: datetime | None = None, max_pages: int = 4) -> list[Post]:
    """Newest first. Reads further pages until it reaches `since` (or `max_pages`)."""
    posts: list[Post] = []
    for page in range(1, max_pages + 1):
        url = URLS[sport] + (f"?p={page}" if page > 1 else "")
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                got = parse(r.read().decode("utf-8", "replace"), sport)
        except (urllib.error.URLError, TimeoutError) as e:
            raise SourceError(f"Rotoworld {sport} news is unreachable ({type(e).__name__})") from None
        if not got:
            if page == 1:
                raise SourceError(f"Rotoworld {sport} news page had no posts (layout changed?)")
            break
        posts += got
        if since is None or min(p.posted for p in got) <= since:
            break
    return posts


def store_new(con, posts: list[Post], now: datetime) -> list[Post]:
    """Save posts not seen before; return only those (oldest first)."""
    con.execute(SCHEMA)
    seen = {r[0] for r in con.execute("SELECT url FROM player_news WHERE url IN (SELECT unnest(?))", [[p.url for p in posts]]).fetchall()} if posts else set()
    new = [p for p in posts if p.url not in seen]
    uniq = {p.url: p for p in new}
    if not uniq:
        return []
    con.executemany("INSERT INTO player_news VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [(p.url, p.sport, p.player, p.team, p.position, p.posted.replace(tzinfo=None),
                      p.source_time.replace(tzinfo=None) if p.source_time else None, p.headline, p.source, p.source_url,
                      p.signal, now.replace(tzinfo=None)) for p in uniq.values()])
    return sorted(uniq.values(), key=lambda p: p.posted)


def last_seen(con, sport: str) -> datetime | None:
    con.execute(SCHEMA)
    t = con.execute("SELECT max(posted_utc) FROM player_news WHERE sport = ?", [sport]).fetchone()[0]
    return t.replace(tzinfo=timezone.utc) if t else None


def update(con, sport: str, now: datetime) -> tuple[list[Post], bool]:
    """Read new posts and store them. Returns (new posts, first run)."""
    since = last_seen(con, sport)
    posts = fetch(sport, since)
    return store_new(con, posts, now), since is None


def latest_signals(con, sport: str, now: datetime, hours: int = 36) -> dict[str, tuple[str, datetime, str]]:
    """normalized player name -> (signal, posted, headline), latest availability post in the window."""
    con.execute(SCHEMA)
    rows = con.execute("""SELECT player, signal, posted_utc, headline FROM player_news
                          WHERE sport = ? AND signal IN ('playing', 'not playing', 'uncertain') AND posted_utc >= ?
                          ORDER BY posted_utc""", [sport, (now - timedelta(hours=hours)).replace(tzinfo=None)]).fetchall()
    from engine.models.props import norm_name
    return {norm_name(p): (s, t.replace(tzinfo=timezone.utc), h) for p, s, t, h in rows}


def credit(p: Post, now: datetime) -> str:
    """'via Shams Charania on X, 4 min ago' style credit line."""
    t = p.source_time or p.posted
    mins = max(0, int((now - t).total_seconds() // 60))
    where = " on X" if p.source_time else ""
    return f"via {p.source_label}{where}, {mins} min ago (relayed by Rotoworld)"


def nfl_starting_qbs(season: int) -> set[str]:
    """Normalized names of each team's quarterback in its latest game, plus any QB averaging 15+ attempts this season."""
    import duckdb

    from engine.models.props import norm_name, stats_file
    f = stats_file(season, True)
    rows = duckdb.connect().execute(f"""
        WITH q AS (SELECT player_display_name AS n, team, week, attempts FROM read_parquet('{f}') WHERE position = 'QB'),
        last AS (SELECT team, max(week) AS wk FROM q GROUP BY team)
        SELECT n FROM (SELECT q.n, row_number() OVER (PARTITION BY q.team ORDER BY q.attempts DESC) AS r
                       FROM q JOIN last ON q.team = last.team AND q.week = last.wk) WHERE r = 1
        UNION SELECT n FROM q GROUP BY n HAVING avg(attempts) >= 15""").fetchall()
    return {norm_name(r[0]) for r in rows}


def nfl_qb_hits(con, posts: list[Post], now: datetime, max_age_minutes: int = 120) -> list[tuple[str, str, str]]:
    """(alert key, message, research trigger) for reporter news on a starting quarterback that ESPN's table does
    not show yet. ESPN statuses come from the stored injury_status table (refreshed each hourly read)."""
    from engine.models.props import norm_name
    qb_posts = [p for p in posts if p.position == "Quarterback" and p.signal in ("playing", "not playing")
                and (now - p.posted) <= timedelta(minutes=max_age_minutes)]
    if not qb_posts:
        return []
    starters = nfl_starting_qbs(now.year if now.month >= 3 else now.year - 1)
    espn_status = {}
    if con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'injury_status'").fetchone()[0]:
        espn_status = {norm_name(n): s for n, s in con.execute("SELECT name, status FROM injury_status").fetchall()}
    out = []
    for p in qb_posts:
        n = norm_name(p.player)
        if n not in starters or (p.kind == "other" and not p.source_time):
            continue
        st = espn_status.get(n, "")
        serious = st in ("Out", "Injured Reserve", "Doubtful", "Suspension")
        if (p.signal == "not playing" and not serious) or (p.signal == "playing" and st in ("Out", "Injured Reserve", "Doubtful", "Questionable")):
            direction = "out" if p.signal == "not playing" else "in"
            key = f"nflqb|{n}|{direction}|{now:%Y-%m-%d}"
            espn_txt = f"ESPN still lists {st}" if st else "not on ESPN's report"
            text = (f"QB NEWS (reporter, ahead of ESPN): {p.team} {p.player}: {p.signal.upper()}; {espn_txt}.\n"
                    f"\"{p.headline}\"\n{credit(p, now)}")
            out.append((key, text, f"quarterback news: {p.team} {p.player} reported {p.signal} ({p.source or 'Rotoworld'})"))
    return out


def coverage(con, sport: str, now: datetime, days: int = 7) -> dict:
    """How many relayed posts came from each listed reporter in the last `days`, and which listed reporters never appeared."""
    con.execute(SCHEMA)
    rows = con.execute("SELECT source, source_url FROM player_news WHERE sport = ? AND posted_utc >= ?",
                       [sport, (now - timedelta(days=days)).replace(tzinfo=None)]).fetchall()
    seen: dict[str, int] = {}
    kinds: dict[str, int] = {}
    for name, url in rows:
        k, _ = source_kind(name or "", url or "")
        kinds[k] = kinds.get(k, 0) + 1
        m = re.search(r"(?:x|twitter)\.com/([a-z0-9_]+)/status", (url or "").lower())
        if m and m.group(1) in reporters():
            seen[m.group(1)] = seen.get(m.group(1), 0) + 1
    listed = {h: r for h, r in reporters().items() if r["sport"] == sport}
    return {"posts": len(rows), "by_kind": kinds, "listed": len(listed), "listed_seen": len(seen),
            "top": sorted(((listed[h]["name"], n) for h, n in seen.items()), key=lambda x: -x[1])[:15],
            "never_seen": sorted(r["name"] for h, r in listed.items() if h not in seen)}
