# Metrics pull (daily, 05:53 ET)

Pull yesterday's Instagram numbers with Windsor and commit them, so the Create run (06:27, which runs without
connectors) can read them from the repo. Data only: no postmortem, no verdicts, no edits to anything else. Never post.

1. `TZ=America/New_York date +%F` gives today.
2. Windsor `get_data` (connector `instagram`, account `17841422626862357`; call `get_fields` first and use only
   fields it lists): `media_id, media_shortcode, media_permalink, media_views, media_reach, media_reel_skip_rate, media_reel_avg_watch_time,
   media_shares, media_saved, media_like_count, media_reel_total_interactions` for every Reel posted in the last
   8 days. Also `followers_count` (today's total) and account `views_non_followers` for yesterday.
3. Write `metrics/<today>.json`:
   `{"date": "<today>", "pulled_at": "<ISO time ET>", "followers_count": N, "views_non_followers_yesterday": N,
   "reels": [{"media_id": "...", "permalink": "...", "posted": "<date>", "views": N, "reach": N, "skip_rate": N,
   "avg_watch_s": N, "shares": N, "saves": N, "likes": N, "interactions": N, "sends_per_1k": N, "age_h": N}]}`.
   `age_h` (2026-11-28) = hours from the post's publish time to `pulled_at`, so Reels are compared at the same age
   (`null` if the publish time is unknown).
   (`tiktok`, `youtube` and `combined` are added by step 3b.)
   `sends_per_1k` = shares ÷ reach × 1000, rounded to 1 decimal (`null` when reach is 0 or missing). It is the
   primary metric (PLAYBOOK "Primary metric").
   Write exactly what Windsor returns; use `null` for anything it does not return. Never estimate a number.
3a. **Fill in Instagram `media_id` for Reels posted through Postproxy (2026-11-27).** Postproxy records only the
   permalink (`instagram_url`, shortcode in `instagram_id`). For each `queue.json` entry with `instagram_id` and no
   `media_id`, find the Windsor row from step 2 whose `media_shortcode` equals it (or whose permalink contains it) and set the entry's
   `media_id` to it, and the `media_id` cell of that entry's `experiment-log.csv` row (matched by `id`). Never guess:
   no matching row means leave it empty and say so in the reply. Commit `queue.json` with the rest in step 5.
3b. **TikTok + YouTube, through Postproxy (Srini, 2026-11-26).** NOT part of the 05:53 Cowork pull (Cowork has no
   `POSTPROXY_API_KEY`): since 2026-11-27 it runs on its own at 06:05 ET in a Claude Code cloud session (task
   "DivvyUpp Reels: TikTok + YouTube stats"), which pulls main, runs this step only, commits `metrics/` and pushes.
   It runs from the repo root: `python3 scripts/fetch_platform_stats.py`
   (needs `POSTPROXY_API_KEY`, which the environment has). It adds `"tiktok"` (follower count + per-video views,
   reach, avg/total watch, full-watch rate, likes, comments, shares, sends per 1,000), `"youtube"` (subscribers,
   channel 7-day watch figures + per-Short views, likes, comments) and `"combined"` (one row per Reel: Instagram,
   TikTok and YouTube views side by side, `total_views` over the platforms it's on) to the same file, leaving the
   Instagram fields untouched. Everything is written exactly as Postproxy returns it, `null` where it returns
   nothing. If it exits 1, the Instagram numbers still stand: log status `partial` with its stderr line and say
   "TikTok/YouTube numbers unavailable" in the reply. Windsor is NOT used for TikTok or YouTube.
4. Write into `experiment-log.csv`: `read_d1` (first-morning read, about 8–18 h after posting) for yesterday's Reels and `read_72h` for Reels posted 3 days ago,
   as `sends_per_1k/views/skip%/avg_watch_s/shares/saves/likes`, and refresh the stats columns with the latest read. Avg watch
   is in seconds. Append `<today>,<followers_count>` to `followers.csv` (skip if today's row already exists).
5. Commit `metrics/`, `experiment-log.csv` and `followers.csv` ("metrics: <today>") and push to main. If the push
   is rejected, pull --rebase and push again once.
6. Write your run log record (`runlog/<today>/metrics.json`, see "Run log" in `PLAYBOOK.md`) and push it with the rest; write it even if you stop early.
7. Reply with one line: how many Reels were read and today's follower count, plus TikTok followers and YouTube
   subscribers. If Windsor fails or returns nothing,
   commit only the run log record (status `failed`), and tell Srini exactly what failed: the Create run will say the numbers are missing.
