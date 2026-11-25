# 0037: Full reads every 30 minutes before NBA tips (2026-11-24)

Kylor, Nov 24: "i want to make sure there is a run to account for those games [8pm MT tips] if something changes"; asked whether to read
every 30 minutes in the 3 hours before any NBA tip, "yes".

Replaces: the hourly full read (one every 45+ minutes, `poll.due`) during those 3 hours. Read hours (decision 0036) are unchanged.

**Why:** only the full read makes picks and sends CANCELLED. On Nov 24 the 8pm Mountain games had one full read in their last hour (7:33pm),
no fast reads after 5:15pm (those follow the day's first tip) and no news check after 6:30pm. A single slow or failed read meant nothing ran
before tip. Our number starts from Pinnacle, which moves within minutes of injury news, so a read is what carries late news into a pick.

**The rule:** when any NBA game in the line log starts within the next 3 hours (config `read_pregame_hours: {NBA: 3}`), every poll wake-up
(:02 and :32) reads, if the last good read is more than 20 minutes old. Outside that, reads stay hourly. No launchd reload is needed: the poll
job already wakes twice an hour. On a night with 5pm and 8pm tips this adds about 5 reads.

Test: `tests/test_decision_0036.py::test_pregame_reads_every_half_hour_before_an_nba_tip`.
