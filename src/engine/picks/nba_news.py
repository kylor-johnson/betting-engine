"""NBA injury watcher: catch a status change for a player who matters before Wagerhouse moves its line.

Runs three times a day (10:00, 15:00 and 17:00 Mountain; launchd, `engine nba-watch`; times in config `nba_watch.run_times`).
Each run compares today's injury report with the one stored at the previous run, so the 10:00 run catches overnight and morning changes.
Each run:
  1. reads ESPN's public NBA injury report (no account, no Wagerhouse);
  2. compares it with the last stored report;
  3. keeps changes that cross the "will he play" line (to or from Out / Doubtful, or off the report) for a
     player who matters (enough minutes this season) on a team that plays in the next 30 hours;
  4. only then reads Wagerhouse and Pinnacle once (capped per day), sends the news with both lines, and starts
     an NBA research run, which issues a pick only if the numbers support it.

It never prices the player itself: how much a player is worth to the line has not been tested here. The
number comes from Pinnacle (which moves first) against Wagerhouse; the watcher's job is speed.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from engine import config
from engine.odds import espn
from engine.odds import snapshots as _db
from engine.odds.espn import SourceError

REPORT_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
STATS_URL = "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/statistics/byathlete?limit=1000&isqualified=false"
SCHEMA = """
CREATE TABLE IF NOT EXISTS nba_injury_status (
  key VARCHAR PRIMARY KEY, team VARCHAR, name VARCHAR, status VARCHAR, comment VARCHAR, seen_utc TIMESTAMP);
CREATE TABLE IF NOT EXISTS nba_injury_changes (
  ts_utc TIMESTAMP, key VARCHAR, team VARCHAR, name VARCHAR, old_status VARCHAR, new_status VARCHAR,
  minutes DOUBLE, points DOUBLE, alerted BOOLEAN, comment VARCHAR);
CREATE TABLE IF NOT EXISTS nba_watch_reads (ts_utc TIMESTAMP, reason VARCHAR);
CREATE TABLE IF NOT EXISTS nba_official_status (name VARCHAR PRIMARY KEY, status VARCHAR, report VARCHAR, seen_utc TIMESTAMP);
CREATE TABLE IF NOT EXISTS nba_official_teams (team VARCHAR, report VARCHAR);
"""
OFFICIAL_INDEX = "https://official.nba.com/nba-injury-report-{y}-{y2:02d}-season/"
OFFICIAL_PDF = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_{d}_{hm}.pdf"
ROW = re.compile(r"([A-Z][A-Za-z\.'\- ]*?(?:\s+(?:II|III|IV|Jr\.|Sr\.))?)\s*,\s*([A-Za-z\.'\-]+(?:\s[A-Za-z\.'\-]+)?)\s{2,}"
                 r"(Out|Doubtful|Questionable|Probable|Available)\b")
OFF = "Available (off the report)"
LEVEL = {"Available": 0, "Out": 3, "Suspension": 3, "Injured Reserve": 3, "Doubtful": 2, "Questionable": 1, "Day-To-Day": 1,
         "Game Time Decision": 1, "Probable": 0, OFF: 0}


def _get(url: str, what: str) -> dict:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=45) as r:
            return json.load(r)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise SourceError(f"{what} failed: {type(e).__name__}") from None


NBA_TEAMS = ("Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets", "Chicago Bulls", "Cleveland Cavaliers",
             "Dallas Mavericks", "Denver Nuggets", "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
             "LA Clippers", "Los Angeles Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat", "Milwaukee Bucks",
             "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks", "Oklahoma City Thunder", "Orlando Magic",
             "Philadelphia 76ers", "Phoenix Suns", "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs",
             "Toronto Raptors", "Utah Jazz", "Washington Wizards")
TEAM_RE = re.compile("|".join(r"\s+".join(map(re.escape, t.split())) for t in NBA_TEAMS))


def official_pdf_text(data: bytes) -> str:
    import io

    from pypdf import PdfReader
    try:
        r = PdfReader(io.BytesIO(data))
        return "\n".join(pg.extract_text(extraction_mode="layout") or "" for pg in r.pages)
    except Exception as e:     # a broken PDF is a source failure, said out loud
        raise SourceError(f"official NBA injury report PDF could not be read ({type(e).__name__})") from None


def parse_official(text: str) -> dict[str, str]:
    """normalized 'First Last' -> status. The PDF lists 'Last, First'; a player listed for two games keeps the first."""
    from engine.models.props import norm_name
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = TEAM_RE.sub("   ", line)            # the team column sometimes lands on the same line as a player
        line = re.sub(r"\b\d{2}/\d{2}/\d{4}\b|\b\d{1,2}:\d{2}\s*\(ET\)|\b[A-Z]{2,3}@[A-Z]{2,3}\b", "   ", line)
        line = re.sub(r"\s{2,}(?=[,])", "", line)
        for last, first, status in ROW.findall(re.sub(r"(?<=\S) {2}(?=\S)", "  ", line)):
            last = " ".join(last.split())
            first = " ".join(first.split())
            key = norm_name(f"{first} {last}")
            out.setdefault(key, status)
    return out


def official_teams(text: str) -> set[str]:
    """Teams listed on an official report (ESPN-normalised names). The PDF only lists teams with games coming up."""
    from engine.odds import espn
    return {espn.norm(" ".join(m.split())) for m in TEAM_RE.findall(text)}


ESPN_ABBR = {"ATL": "Atlanta Hawks", "BKN": "Brooklyn Nets", "BOS": "Boston Celtics", "CHA": "Charlotte Hornets",
             "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers", "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets",
             "DET": "Detroit Pistons", "GS": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
             "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies", "MIA": "Miami Heat",
             "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves", "NO": "New Orleans Pelicans", "NY": "New York Knicks",
             "OKC": "Oklahoma City Thunder", "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
             "POR": "Portland Trail Blazers", "SA": "San Antonio Spurs", "SAC": "Sacramento Kings", "TOR": "Toronto Raptors",
             "UTAH": "Utah Jazz", "WSH": "Washington Wizards"}   # ESPN stats teamShortName -> the PDF's team name


def team_full(team: str) -> str:
    """An ESPN short name ('PHI') or a full name, ESPN-normalised the way official_teams() normalises the PDF."""
    from engine.odds import espn
    return espn.norm(ESPN_ABBR.get(team, team))


LAST_TEAMS: dict[str, set[str]] = {}      # report url -> teams on it, filled by latest_official


def latest_official(now: datetime) -> tuple[str, dict[str, str]]:
    """The newest official report: from the season index page, else stepping back 15 minutes at a time (Eastern)."""
    from zoneinfo import ZoneInfo
    et = now.astimezone(ZoneInfo("America/New_York"))
    y = et.year if et.month >= 8 else et.year - 1
    url = None
    try:
        with urllib.request.urlopen(urllib.request.Request(OFFICIAL_INDEX.format(y=y, y2=(y + 1) % 100),
                                                           headers={"User-Agent": "Mozilla/5.0"}), timeout=45) as r:
            links = re.findall(r"https://ak-static\.cms\.nba\.com/referee/injury/Injury-Report_[0-9_\-]+[AP]M\.pdf", r.read().decode("utf-8", "replace"))
        url = links[-1] if links else None
    except (urllib.error.URLError, TimeoutError):
        url = None
    tries = [url] if url else []
    t = et.replace(minute=et.minute - et.minute % 15, second=0, microsecond=0)
    for _ in range(12):
        tries.append(OFFICIAL_PDF.format(d=f"{t:%Y-%m-%d}", hm=t.strftime("%I_%M%p")))
        t -= timedelta(minutes=15)
    for u in tries:
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=45) as r:
                data = r.read()
        except (urllib.error.URLError, TimeoutError):
            continue
        if data[:4] == b"%PDF":
            text = official_pdf_text(data)
            got = parse_official(text)
            LAST_TEAMS[u] = official_teams(text)
            if not got:
                raise SourceError(f"official NBA injury report had no player rows ({u.rsplit('/', 1)[-1]})")
            return u, got
    raise SourceError("official NBA injury report not found (index page and the last three hours of report times)")


def check_official(con, now: datetime, url: str, statuses: dict[str, str], persist: bool = True,
                   teams: set[str] | None = None, team_of: dict[str, str] | None = None) -> tuple[list[tuple], bool]:
    """(name, old, new) changes since the last stored official report. Off the report = available.

    The report lists only teams with games coming up, so when it rolls to the next day every player on a team that
    played yesterday and plays tomorrow looked like news (Embiid "Out to Available", Nov 24; audit 24). With `teams`
    (the teams on this report) and `team_of` (player -> team), a player who joined or left the report counts only when
    his team is on both reports; a player whose team is unknown counts only for a status change on both reports."""
    con.execute(SCHEMA)
    prev = dict(con.execute("SELECT name, status FROM nba_official_status").fetchall())
    prev_teams = {r[0] for r in con.execute("SELECT team FROM nba_official_teams").fetchall()}
    first = not prev
    both = None if teams is None else (teams & prev_teams)
    def on_both(n: str) -> bool:
        if both is None:
            return True
        t = (team_of or {}).get(n)
        return t is not None and t in both
    changes = []
    if not first:
        for n, st in statuses.items():
            if n not in prev and not on_both(n):
                continue
            if prev.get(n, "Available") != st:
                changes.append((n, prev.get(n), st))
        for n, st in prev.items():
            if n not in statuses and st != "Available" and on_both(n):
                changes.append((n, st, OFF))
    if persist:
        con.execute("DELETE FROM nba_official_status")
        con.executemany("INSERT INTO nba_official_status VALUES (?,?,?,?)",
                        [(n, st, url.rsplit("/", 1)[-1], now.replace(tzinfo=None)) for n, st in statuses.items()])
        if teams is not None:
            con.execute("DELETE FROM nba_official_teams")
            con.executemany("INSERT INTO nba_official_teams VALUES (?,?)", [(t, url.rsplit("/", 1)[-1]) for t in sorted(teams)])
    return changes, first


@dataclass
class Listed:
    key: str          # ESPN athlete id when present, else team|name
    team: str         # full team name, e.g. "Los Angeles Lakers"
    name: str
    status: str
    comment: str


def athlete_id(athlete: dict) -> str | None:
    if athlete.get("id"):
        return str(athlete["id"])
    for link in athlete.get("links") or []:
        m = re.search(r"/id/(\d+)", link.get("href", ""))
        if m:
            return m.group(1)
    return None


def parse_report(data: dict) -> list[Listed]:
    if "injuries" not in data:
        raise SourceError("ESPN NBA injury report has no 'injuries' field")
    out = []
    for t in data["injuries"]:
        for i in t.get("injuries", []):
            a = i.get("athlete") or {}
            aid = athlete_id(a)
            name = a.get("displayName", "")
            out.append(Listed(aid or f"{t.get('displayName')}|{name}", t.get("displayName", ""), name,
                              i.get("status", ""), (i.get("shortComment") or "").strip()))
    if not out:
        raise SourceError("ESPN NBA injury report came back empty")
    return out


def parse_impact(data: dict) -> dict[str, dict]:
    """athlete id -> season minutes, points, rebounds, assists, games, team abbreviation."""
    cats = {c["name"]: c["names"] for c in data.get("categories", [])}
    if "general" not in cats or "offensive" not in cats:
        raise SourceError("ESPN NBA player stats came back without the expected categories")
    out = {}
    for a in data.get("athletes", []):
        ath = a.get("athlete") or {}
        vals = {c["name"]: dict(zip(cats[c["name"]], c.get("totals") or c.get("values") or [])) for c in a.get("categories", [])}
        g, o = vals.get("general", {}), vals.get("offensive", {})
        f = lambda d, k: float(d.get(k) or 0)
        out[str(ath.get("id"))] = {"name": ath.get("displayName", ""), "team": ath.get("teamShortName", ""),
                                   "games": f(g, "gamesPlayed"), "minutes": f(g, "avgMinutes"), "rebounds": f(g, "avgRebounds"),
                                   "points": f(o, "avgPoints"), "assists": f(o, "avgAssists")}
    if not out:
        raise SourceError("ESPN NBA player stats came back empty")
    return out


def impact_with_last_season(current_data: dict) -> dict[str, dict]:
    """This season's numbers; for a player with fewer than 3 games this season (back from a long injury, say),
    last season's regular-season numbers, marked as such. Last season is cached on disk; it does not change."""
    cur = parse_impact(current_data)
    year = int((current_data.get("currentSeason") or {}).get("year") or 0)
    if not year:
        return cur
    path = config.DATA / "raw" / f"espn_nba_player_stats_{year - 1}.json"
    if path.exists():
        last_data = json.loads(path.read_text())
    else:
        last_data = _get(f"{STATS_URL}&season={year - 1}&seasontype=2", "ESPN NBA player stats (last season)")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(last_data))
    last = parse_impact(last_data)
    out = dict(cur)
    for k, v in last.items():
        if k not in cur or cur[k]["games"] < 3:
            out[k] = {**v, "last_season": True}
    return out


@dataclass
class Change:
    player: Listed
    old_status: str | None     # None = not on the report before
    impact: dict | None

    @property
    def new_status(self) -> str:
        return self.player.status

    def crosses(self) -> bool:
        """Did 'will he play' change? Out or Doubtful on one side, not on the other."""
        old = LEVEL.get(self.old_status or OFF, 1)
        new = LEVEL.get(self.new_status, 1)
        return (old >= 2) != (new >= 2)

    def matters(self, min_minutes: float) -> bool:
        return bool(self.impact and self.impact["games"] >= 3 and self.impact["minutes"] >= min_minutes)

    def text(self) -> str:
        i = self.impact or {}
        who = f"{self.player.team}: {self.player.name}"
        if i:
            who += (f" ({i['minutes']:.0f} min, {i['points']:.0f} pts, {i['rebounds']:.0f} reb, {i['assists']:.0f} ast a game"
                    f"{', last season' if i.get('last_season') else ''})")
        return f"{who}\n{self.old_status or 'not on the report'} → {self.new_status}" + (f"\n{self.player.comment}" if self.player.comment else "")


def diff(previous: dict[str, tuple[str, str, str]], now: list[Listed], impact: dict[str, dict]) -> list[Change]:
    """previous: key -> (team, name, status). Includes players who dropped off the report (now available)."""
    seen = {p.key for p in now}
    out = [Change(p, previous[p.key][2] if p.key in previous else None, impact.get(p.key))
           for p in now if (previous.get(p.key) or (None, None, None))[2] != p.status]
    for key, (team, name, status) in previous.items():
        if key not in seen:
            out.append(Change(Listed(key, team, name, OFF, ""), status, impact.get(key)))
    return out


def check(con, now: datetime, report: list[Listed], impact: dict[str, dict], persist: bool = True) -> tuple[list[Change], bool]:
    con.execute(SCHEMA)
    prev = {k: (t, n, s) for k, t, n, s in con.execute("SELECT key, team, name, status FROM nba_injury_status").fetchall()}
    first = not prev
    changes = [] if first else diff(prev, report, impact)
    if not persist:
        return changes, first
    ts = now.replace(tzinfo=None)
    con.execute("DELETE FROM nba_injury_status")
    con.executemany("INSERT INTO nba_injury_status VALUES (?,?,?,?,?,?)",
                    [(p.key, p.team, p.name, p.status, p.comment, ts) for p in {q.key: q for q in report}.values()])
    return changes, first


def in_window(cfg: dict, now: datetime) -> bool:
    """True within 30 minutes after one of the scheduled check times (config nba_watch.run_times, Mountain)."""
    w = cfg.get("nba_watch") or {}
    if not w.get("enabled"):
        return False
    local = now.astimezone(config.display_tz(cfg))
    for hhmm in w.get("run_times", ["10:00", "15:00", "17:00"]):
        h, m = (int(x) for x in str(hhmm).split(":"))
        slot = local.replace(hour=h, minute=m, second=0, microsecond=0)
        if timedelta(0) <= local - slot < timedelta(minutes=30):
            return True
    return False


def book_reads_today(con, cfg: dict, now: datetime) -> int:
    con.execute(SCHEMA)
    day_start = now.astimezone(config.display_tz(cfg)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    return con.execute("SELECT count(*) FROM nba_watch_reads WHERE ts_utc >= ?", [day_start.replace(tzinfo=None)]).fetchone()[0]


def lines_text(con, team: str, events: list, env: dict) -> str:
    """One Wagerhouse read and one Pinnacle read for this team's game, with Pinnacle's last stored line."""
    from engine.odds.wagerhouse import Wagerhouse
    from engine.picks import sources
    from engine.picks.slate import _find
    ev = next((e for e in events if espn.norm(team) in (espn.team_names(e.home) | espn.team_names(e.away))), None)
    if ev is None:
        return ""
    home, away = ev.home["displayName"], ev.away["displayName"]
    out = f"\n{away} at {home}, {ev.start.astimezone(config.display_tz(config.load_config())):%a %-I:%M %p} MT."
    wh = Wagerhouse(env.get("WAGERHOUSE_USER", ""), env.get("WAGERHOUSE_PASSWORD", ""))
    book = next((l for l in wh.lines("NBA") if _find([ev], l.home, l.away, l.start)), None)
    sharp = next((s for s in sources.pinnacle("NBA") if _find([ev], s.home, s.away, s.start)), None)
    fmt = lambda x: "pk" if x == 0 else f"{x:+g}"
    if book and book.home_spread is not None:
        out += f" Your book: {home} {fmt(book.home_spread)}."
    else:
        out += " Your book: no line posted (often taken down on news)."
    if sharp and sharp.home_spread is not None:
        out += f" Pinnacle: {home} {fmt(sharp.home_spread)}"
        was = con.execute("""SELECT home_spread FROM line_snapshots WHERE lower(source)='pinnacle' AND sport='NBA'
                             AND lower(home)=lower(?) AND home_spread IS NOT NULL ORDER BY ts_utc DESC LIMIT 1""", [home]).fetchone() \
            if con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='line_snapshots'").fetchone()[0] else None
        out += f" (was {fmt(was[0])} at the last hourly read)." if was else "."
    return out


@dataclass
class Hit:
    player: str
    team: str            # anything espn.team_names understands (full name or abbreviation)
    direction: str       # "out" or "in"
    text: str
    reason: str

    def key(self, now: datetime) -> str:
        # one message per player per direction per day, whichever source is first
        from engine.models.props import norm_name
        return f"nbaplay|{norm_name(self.player)}|{self.direction}|{now.astimezone(config.display_tz(config.load_config())):%Y-%m-%d}"


def reporter_hits(posts: list, report: list[Listed], impact: dict[str, dict], playing: set[str], min_minutes: float,
                  now: datetime, max_age_minutes: int = 90, star_minutes: float = 28, official: dict | None = None) -> list[Hit]:
    """'Playing' matters when ESPN has him Out/Doubtful, or Questionable/Day-To-Day for a 28+ minute player;
    'not playing' matters whenever ESPN does not already have him Out/Doubtful."""
    """Rotoworld posts where a reporter says playing / not playing and ESPN's table does not show it yet."""
    from engine.models.props import norm_name
    from engine.picks import player_news
    by_name = {norm_name(v["name"]): v for v in impact.values()}
    espn_status = {norm_name(p.name): p.status for p in report}
    listed_by = "ESPN"
    if official:
        espn_status = {n: ("Available (official report)" if st == "Available" else st) for n, st in official.items()}
        listed_by = "the official report"
    out = []
    for p in posts:
        sig = p.signal
        if sig not in ("playing", "not playing") or (now - p.posted) > timedelta(minutes=max_age_minutes):
            continue
        n = norm_name(p.player)
        imp = by_name.get(n)
        if not imp or imp["games"] < 3 or imp["minutes"] < min_minutes or espn.norm(imp["team"]) not in playing:
            continue
        espn_now = espn_status.get(n, OFF)
        level = 0 if espn_now.startswith("Available") else LEVEL.get(espn_now, 1)
        star = imp["minutes"] >= star_minutes
        if (sig == "playing" and (level >= 2 or (level == 1 and star))) or (sig == "not playing" and level <= 1):
            who = (f"{p.team} {p.player} ({imp['minutes']:.0f} min, {imp['points']:.0f} pts, {imp['rebounds']:.0f} reb, "
                   f"{imp['assists']:.0f} ast a game{', last season' if imp.get('last_season') else ''})")
            espn_txt = f"not on {listed_by}" if espn_now == OFF else f"{listed_by} still lists {espn_now}"
            if p.kind == "other" and not p.source_time:
                continue      # unattributed items do not alert on their own
            text = f"{who}\nReporter says {sig.upper()}; {espn_txt}.\n\"{p.headline}\"\n{player_news.credit(p, now)}"
            out.append(Hit(p.player, imp["team"], "out" if sig == "not playing" else "in", text,
                           f"{p.player} reported {sig} ({p.source_label}), {listed_by}: {espn_now}"))
    return out


def run(force: bool = False, send: bool = True) -> tuple[int, list[str]]:
    import duckdb

    from engine.alerts import rules
    from engine.picks import agent, player_news
    from engine.poll import _deliver

    cfg, env = config.load_config(), config.load_env()
    w = cfg.get("nba_watch") or {}
    now = datetime.now(timezone.utc)
    if not force and not in_window(cfg, now):
        return 0, ["Outside the NBA watch hours; nothing read."]
    events = [e for e in espn.upcoming("NBA", now.date() - timedelta(days=1), now.date() + timedelta(days=1))
              if now < e.start < now + timedelta(hours=30)]     # pregame only
    if not events and not force:
        return 0, ["No NBA games in the next 30 hours."]
    playing = set()
    for e in events:
        playing |= espn.team_names(e.home) | espn.team_names(e.away)
    report = parse_report(_get(REPORT_URL, "ESPN NBA injury report"))
    impact = impact_with_last_season(_get(STATS_URL, "ESPN NBA player stats"))
    min_minutes = w.get("min_minutes", 22)
    con = _db.connect(config.DB)
    lines: list[str] = []
    try:
        changes, first = check(con, now, report, impact, persist=send)
        # reporters first: Rotoworld posts every beat-writer and insider item minutes after the tweet
        try:
            if send:
                try:
                    posts, first_news = player_news.update(con, "NBA", now)
                except player_news.Truncated as e:     # keep what was read; report the gap (audit 24)
                    posts, first_news = e.new, e.first
                    lines.append(f"PROBLEM: {e}")
            else:
                seen = player_news.last_seen(con, "NBA")
                posts, first_news = [p for p in player_news.fetch("NBA", seen) if seen is None or p.posted > seen], seen is None
        except SourceError as e:
            posts, first_news = [], False
            lines.append(f"PROBLEM: {e}")
        if first:
            lines.append("NBA injury report stored as the baseline; changes are reported from the next run.")
        if first_news:
            lines.append("Rotoworld NBA news stored as the baseline; new posts are reported from the next run.")
            posts = []
        official, off_url, off_changes, off_first = {}, "", [], True
        try:
            off_url, official = latest_official(now)
            from engine.models.props import norm_name as _nn
            team_of = {_nn(v["name"]): team_full(v["team"]) for v in impact.values()}
            off_changes, off_first = check_official(con, now, off_url, official, persist=send,
                                                    teams=LAST_TEAMS.get(off_url), team_of=team_of)
        except SourceError as e:
            lines.append(f"PROBLEM: {e}")
        espn_hits = [c for c in changes if c.crosses() and c.matters(min_minutes) and espn.norm(c.player.team) in playing]
        ts = now.replace(tzinfo=None)
        for c in (changes if send else []):
            con.execute("INSERT INTO nba_injury_changes VALUES (?,?,?,?,?,?,?,?,?,?)",
                        [ts, c.player.key, c.player.team, c.player.name, c.old_status, c.new_status,
                         (c.impact or {}).get("minutes"), (c.impact or {}).get("points"), c in espn_hits, c.player.comment])
        hits = reporter_hits(posts, report, impact, playing, min_minutes, now, star_minutes=w.get("star_minutes", 28), official=official)
        from engine.models.props import norm_name
        by_name = {norm_name(v["name"]): v for v in impact.values()}
        for name, old, new in ([] if off_first else off_changes):
            imp = by_name.get(name)
            o, nw = LEVEL.get(old or "Available", 1), LEVEL.get(new, 1)
            if not imp or imp["games"] < 3 or imp["minutes"] < min_minutes or espn.norm(imp["team"]) not in playing or (o >= 2) == (nw >= 2):
                continue
            stamp = off_url.rsplit("_", 2)[-2:] if off_url else ""
            when = f"{stamp[0].replace('_', ':')} {stamp[1][:2]} ET" if len(stamp) == 2 else ""
            who = (f"{imp['team']} {imp['name']} ({imp['minutes']:.0f} min, {imp['points']:.0f} pts, {imp['rebounds']:.0f} reb, "
                   f"{imp['assists']:.0f} ast a game{', last season' if imp.get('last_season') else ''})")
            hits.append(Hit(imp["name"], imp["team"], "out" if nw >= 2 else "in",
                            f"{who}\n{old or 'not on the report'} → {new}\n(official NBA injury report{', ' + when if when else ''})",
                            f"{imp['name']} {old or 'not listed'} to {new} (official report)"))
        hits += [Hit(c.player.name, c.player.team, "out" if LEVEL.get(c.new_status, 1) >= 2 else "in",
                     c.text() + "\n(ESPN injury report)", f"{c.player.name} {c.old_status or 'not listed'} to {c.new_status}")
                 for c in espn_hits]
        fresh, keys = [], set()
        for h in hits:
            k = h.key(now)
            if k in keys or con.execute("SELECT 1 FROM alerts_sent WHERE key = ?", [k]).fetchone():
                continue
            keys.add(k)
            fresh.append(h)
        lines.append(f"NBA: {len(off_changes)} official-report change(s), {len(changes)} ESPN change(s), {len(posts)} new reporter post(s); "
                     f"{len(fresh)} new item(s) that matter for tonight's or tomorrow's games.")
        if not fresh:
            return 0, lines
        can_read = book_reads_today(con, cfg, now) < w.get("max_book_reads_per_day", 12)
        if can_read and send:
            con.execute("INSERT INTO nba_watch_reads VALUES (?,?)", [ts, "; ".join(h.player for h in fresh)[:300]])
        alerts = []
        for h in fresh:
            if can_read:
                try:
                    extra = lines_text(con, h.team, events, env)
                except SourceError as e:
                    extra = f"\nLines could not be read: {e}"
            else:
                extra = "\nDaily cap on extra Wagerhouse reads reached; the next hourly read will check the line."
            alerts.append(rules.Alert(h.key(now), "news", "NBA NEWS, checking now (not a bet yet): " + h.text + extra))
        if send:
            _deliver(con, env, alerts, now, lines)
            reason = "NBA news: " + "; ".join(h.reason for h in fresh)
            if agent.cooled_down(con, now, w.get("cooldown_minutes", 20), sport="NBA"):
                agent.spawn(reason[:300], "NBA")
                lines.append(f"Started an NBA research run: {reason}")
            else:
                lines.append("An NBA research run ran in the last few minutes; not starting another.")
        else:
            lines += [a.text for a in alerts]
        return 0, lines
    finally:
        con.close()
