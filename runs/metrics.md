# Metrics pull (daily, 05:53 ET)

Pull yesterday's Instagram numbers with Windsor and commit them, so the Create run (06:27, which runs without
connectors) can read them from the repo. Data only: no postmortem, no verdicts, no edits to anything else. Never post.

1. `TZ=America/New_York date +%F` gives today.
2. Windsor `get_data` (connector `instagram`, account `17841422626862357`; call `get_fields` first and use only
   fields it lists): `media_id, media_views, media_reach, media_reel_skip_rate, media_reel_avg_watch_time,
   media_shares, media_saved, media_like_count, media_reel_total_interactions` for every Reel posted in the last
   8 days. Also `followers_count` (today's total) and account `views_non_followers` for yesterday.
3. Write `metrics/<today>.json`:
   `{"date": "<today>", "pulled_at": "<ISO time ET>", "followers_count": N, "views_non_followers_yesterday": N,
   "reels": [{"media_id": "...", "permalink": "...", "posted": "<date>", "views": N, "reach": N, "skip_rate": N,
   "avg_watch_s": N, "shares": N, "saves": N, "likes": N, "interactions": N}]}`.
   Write exactly what Windsor returns; use `null` for anything it does not return. Never estimate a number.
4. Write into `experiment-log.csv`: `read_d1` (first-morning read, about 8–18 h after posting) for yesterday's Reels and `read_72h` for Reels posted 3 days ago,
   as `views/skip%/avg_watch_s/shares/saves/likes`, and refresh the stats columns with the latest read. Avg watch
   is in seconds. Append `<today>,<followers_count>` to `followers.csv` (skip if today's row already exists).
5. Commit `metrics/`, `experiment-log.csv` and `followers.csv` ("metrics: <today>") and push to main. If the push
   is rejected, pull --rebase and push again once.
6. Reply with one line: how many Reels were read and today's follower count. If Windsor fails or returns nothing,
   commit nothing, and tell Srini exactly what failed: the Create run will say the numbers are missing.
