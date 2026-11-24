# 0028: Units only, no dollar cap; lane-change messages say what changed, not how the table is worded (2026-11-23, night)

Replaces: the $500 weekly cap and the bankroll line in decision 0027.

Kylor: "dont worry about bankroll for now, let's build it and we can adjust as later, just stick to units. no cap on $ either for now."

- `playbook.weekly_cap_dollars: 0` (off). The code stays, so a cap is one number when he wants one. The charter's Money section says units
  only; the tracker and recap show the week's total with "(no weekly cap)".
- `bankroll` in config is marked unused.
- **Lane-change messages.** The first one (Nov 23, ~7pm) listed nine changes, most of them rewordings of "what can produce a pick", because
  the change check hashed the table's prose. It also spanned decisions 0026 and 0027 at once, since the last stored snapshot was from the
  0025 (paper) evening. The check now compares only what decides behaviour: each lane's money state (staked, paper, shown, off), its inputs,
  and each model's switch and test result. Messages are one short line per real change, named by lane ("NFL player props: now STAKED (was
  paper)."). The first read after this change stores a new baseline quietly.
