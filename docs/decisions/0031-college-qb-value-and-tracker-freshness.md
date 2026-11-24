# 0031: College quarterback value measured; the tracker page stays current (2026-11-23, night)

Replaces: the college quarterback range in decision 0029 ("3 to 7, not measured").

- **College starter out = about 3.5 points** (research 21: 3.7 mean, 3.5 median over 1,078 team-games 2021-2026; Power 4 3.2, Group of 5 4.2).
  Only 0.9 points of it moves after the opener on average. Missing high-efficiency starters were discounted less (2.3), not more. The
  college guide and the shared `priced_in` instruction use this number; above 5 needs a written reason; no extra points for a star. Parity
  cell "player value measured" for college is live.
- **Tracker page** (Kylor: "make sure you are keeping this up to date", tracker.html): it was rebuilt in the middle of each hourly read,
  before that read's picks were issued, so a new pick showed an hour late, and nothing rebuilt it after 5pm. Now it is rebuilt after the
  read's picks and teaser tickets, and outside read hours the 30-minute job grades finished picks and rebuilds it at most once an hour (no
  book sign-in). The page reloads itself every 15 minutes.
