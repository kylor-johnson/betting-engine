from datetime import datetime, timezone

import duckdb

from engine import burst

CFG = {"timezone_display": "America/Denver", "burst": {"enabled": True, "max_reads_per_day": 2,
       "windows": {"sun": ["09:00-11:15"], "wed": ["12:00-15:30"]}}}


def utc(y, m, d, h, mi):
    return datetime(y, m, d, h, mi, tzinfo=timezone.utc)


def test_window_is_checked_in_mountain_time():
    # Sunday Nov 22 2026, 10:00 MT = 17:00 UTC (MST)
    assert burst.in_window(CFG, utc(2026, 11, 22, 17, 0)) == "09:00-11:15"
    assert burst.in_window(CFG, utc(2026, 11, 22, 18, 30)) is None         # 11:30 MT, after the window
    assert burst.in_window(CFG, utc(2026, 11, 25, 20, 0)) == "12:00-15:30"  # Wednesday 13:00 MT
    assert burst.in_window(CFG, utc(2026, 11, 24, 20, 0)) is None           # Tuesday has none


def test_disabled_means_no_window():
    assert burst.in_window({**CFG, "burst": {**CFG["burst"], "enabled": False}}, utc(2026, 11, 22, 17, 0)) is None


def test_daily_cap_counts_reads_not_rows():
    con = duckdb.connect()
    con.execute(burst.SCHEMA)
    t = datetime(2026, 11, 22, 17, 0)
    for sport in ("NFL", "NFL"):          # two rows, one read time
        con.execute("INSERT INTO burst_reads VALUES (?,?,?,?,?,?)", [t, sport, True, 5, 5, ""])
    assert burst.reads_today(con, CFG, utc(2026, 11, 22, 19, 0)) == 1
