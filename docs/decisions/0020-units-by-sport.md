# 0020: Units by sport (2026-11-23)

Kylor: "NFL bets my unit is now $50 and for nba it is $25."

- `units_by_sport` in config.yaml: NFL $50, NBA $25. College stays at the default `unit` ($25) until he says otherwise.
- Stakes everywhere are units times that sport's dollars (`config.unit_for`): playbook picks, teaser tickets, cards, the board.
- Grades in dollars, NFL, until Dec 15 (half size): A $25, B $12.50. After Dec 15: A $50, B $25. NBA: A $12.50 / B $6.25, then $25 / $12.50.
- The two NFL picks already sent at the old $25 unit were re-priced in the database: Commanders team total under 24 is $12.50 (was $6.25),
  the Packers/Steelers teaser is $25 (was $12.50).
