# 0032: College wind totals failed; college weather stays off (2026-11-23, night)

Replaces: none (closes the "college wind test running" line of decision 0030's parity table).

- **Result (research 20):** on day-before forecasts, 2024-2026, 2,556 games, fit only on 2022-2023: 57-53 at a 1-point edge (-1.2 units),
  25-22 at 1.5, 10-9 at 2. The model's total was no closer to the score than the closing total. Coin flip; the close already prices it.
- **Switched:** nothing on. College lane model `college_wind_totals` and the parity cell weather/College are now "failed". No live code was added;
  the wiring prepared in case it passed was removed.
- **What college has now:** news picks (decision 0029) with the measured quarterback value (3.5 points, research 21). Its own script is still
  shown only (research 16). Weather is the one NFL component college does not get, and the parity table says why.
