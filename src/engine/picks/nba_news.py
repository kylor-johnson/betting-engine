"""NBA injury watcher: catch a status change for a player who matters before Wagerhouse moves its line.

Runs every 10 minutes on game days (launchd, `engine nba-watch`), inside the hours in config `nba_watch`.
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
"""
OFF = "Available (off the report)"
LEVEL = {"Out": 3, "Suspension": 3, "Injured Reserve": 3, "Doubtful": 2, "Questionable": 1, "Day-To-Day": 1,
         "Game Time Decision": 1, "Probable": 0, OFF: 0}


def _get(url: str, what: str) -> dict:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=45) as r:
            return json.load(r)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise SourceError(f"{what} failed: {type(e).__name__}") from None


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
    w = cfg.get("nba_watch") or {}
    local = now.astimezone(config.display_tz(cfg))
    return bool(w.get("enabled")) and w.get("start_hour", 9) <= local.hour < w.get("end_hour", 21)


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


def run(force: bool = False, send: bool = True) -> tuple[int, list[str]]:
    import duckdb

    from engine.alerts import rules
    from engine.picks import agent
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
    con = duckdb.connect(str(config.DB))
    try:
        changes, first = check(con, now, report, impact, persist=send)
        if first:
            return 0, ["NBA injury report stored as the baseline; changes are reported from the next run."]
        hits = [c for c in changes if c.crosses() and c.matters(w.get("min_minutes", 22)) and espn.norm(c.player.team) in playing]
        ts = now.replace(tzinfo=None)
        for c in (changes if send else []):
            con.execute("INSERT INTO nba_injury_changes VALUES (?,?,?,?,?,?,?,?,?,?)",
                        [ts, c.player.key, c.player.team, c.player.name, c.old_status, c.new_status,
                         (c.impact or {}).get("minutes"), (c.impact or {}).get("points"), c in hits, c.player.comment])
        lines = [f"NBA injury report: {len(changes)} change(s), {len(hits)} that matter for tonight's or tomorrow's games."]
        if not hits:
            return 0, lines
        alerts = []
        can_read = book_reads_today(con, cfg, now) < w.get("max_book_reads_per_day", 12)
        if can_read and send:
            con.execute("INSERT INTO nba_watch_reads VALUES (?,?)", [ts, "; ".join(c.player.name for c in hits)[:300]])
        for c in hits:
            extra = ""
            if can_read:
                try:
                    extra = lines_text(con, c.player.team, events, env)
                except SourceError as e:
                    extra = f"\nLines could not be read: {e}"
            else:
                extra = "\nDaily cap on extra Wagerhouse reads reached; the next hourly read will check the line."
            alerts.append(rules.Alert(f"nbanews|{c.player.key}|{c.old_status}|{c.new_status}|{now:%Y-%m-%d}", "news",
                                      "NBA NEWS, checking now (not a bet yet): " + c.text() + extra))
        if send:
            _deliver(con, env, alerts, now, lines)
            reason = "NBA news: " + "; ".join(f"{c.player.name} {c.old_status or 'not listed'} to {c.new_status}" for c in hits)
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
