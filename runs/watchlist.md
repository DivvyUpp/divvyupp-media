# Watchlist run (weekly, Sunday 05:00 ET)

Keep `research/watchlist.csv` honest: every account on it meets the entry bar in `research/watchlist.md`, and good
new accounts get in. Needs env `YOUTUBE_API_KEY` and `www.googleapis.com` allowed; if either is missing, tell Srini
and stop. Never contact anyone, sign up for or buy anything.

1. **Re-check everyone.** Run `python3 scripts/vet_channels.py --names <each account's handle>` (lookups by handle
   cost almost nothing). For each account update `subscribers`, `shorts_last_90d`, `median_short_views`,
   `last_checked`.
2. **Remove** any niche or fintech-brand account that now fails the bar: fewer than 10 Shorts in the last 90 days,
   under 50,000 subscribers, or recent Shorts mostly off-topic (read its last 10 titles). Move it to the "Checked and
   left out" table in `research/watchlist.md` with the date and reason. Format teachers stay unless they stopped
   posting entirely for 90 days.
3. **Re-check the near misses** in "Checked and left out"; add any that now pass.
4. **Discover.** Up to 40 searches (each costs 100 of the 10,000 daily units): `vet_channels.py --queries` with
   topics such as budgeting, couples money, family finance, paycheck to paycheck, frugal living, cash stuffing,
   debt payoff, money news, plus names surfaced by the Research runs or the outliers' collaborators. Add every
   account that passes; log the ones checked and left out with the reason.
5. Regenerate `research/watchlist.md` from the CSV (same layout), commit and push to main with a one-line summary of
   added and removed accounts. Send Srini nothing unless the list dropped below 20 niche accounts or you were
   blocked.
6. Write your run log record (`runlog/<today>/watchlist.json`, see "Run log" in `PLAYBOOK.md`) and push it with the rest; write it even if you stop early.
