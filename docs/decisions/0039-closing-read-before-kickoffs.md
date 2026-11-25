# 0039: A closing read before each NFL and college kickoff (2026-11-24)

Kylor, Nov 24 night, after answering research 25's question 5 ("NFL and CFB need less of a read but at least 2 times early week and then
3-4 for each game that is within 24 hours"), asked "what is most elite?". The answer: keep the hourly reads and add one full read about 15
minutes before each NFL and college kickoff time. He said "yes".

Replaces: none (adds to the read schedule of decisions 0036 and 0037; read hours and the half-hourly NBA reads are unchanged).

**Why:** the hourly job wakes only at :02 and :32, so the last full read before a kickoff could be 58 minutes old. Only the full read makes
picks, sends CANCELLED and stores the team-total and prop prices the closing grade uses. The closing number is the week-to-week scorecard
(PLAYBOOK section 4); a stale close blurs it, and late inactives or injuries could move the line with no CANCELLED.

**The rule:** config `closing_read: {sports: [NFL, College], minutes_before: [25, 8]}`. The 10-minute fast-read job checks every wake-up;
when a kickoff is 8 to 25 minutes away and no full read has run since 25 minutes before it, it starts the full read (`poll.run`). Kickoffs
within that window of a read share it. It runs at any hour, inside or outside `read_hours`. No launchd reload: the fast-read job already
wakes every 10 minutes, with the same environment as the hourly job.

**Cost, simulated on the week of Nov 24 from the line log:** 1 extra read on a single-game night (Tue, Wed, Mon), 4 on Thanksgiving and on
Sunday, 6 on Friday, and 18 on Saturday (18 college kickoff times from 10am to 9pm). The Saturday number is about three times what was
estimated when Kylor said yes; if that is too many, the fix is a wider window so one read covers neighbouring kickoffs.

Test: `tests/test_tuning_check.py::test_closing_read_before_each_nfl_and_college_kickoff`.
