# Post run (daily, 19:00 ET)

Post today's approved Reels to @getdivvyupp. Only entries Srini explicitly approved may ever be posted.

1. `TZ=America/New_York date +%F` gives today. Read `queue.json`. Take every entry with `"status": "approved"` and
   `post_date` equal to today. If there are none, finish quietly.
2. Before posting, use Windsor `get_data` (connector `instagram`, account `17841422626862357`) to list media created
   today, so nothing posts twice. Skip any entry whose video is already live.
3. Post the **main** entry first (`kind` is `"main"` or missing; at most one per day): Windsor `execute_action`
   `create_video_post`, `video_url` = `https://divvyupp.github.io/divvyupp-media/<entry.file>`, `caption` =
   `entry.caption`, `share_to_feed` = true.
4. Post each **trial** entry (`"kind": "trial"`, at most 3): same action, plus
   `trial_params: {"graduation_strategy": "MANUAL"}` unless the entry sets another strategy.
5. Never edit captions. Never post anything not approved. If a publish fails, do not retry blindly; check with
   `get_data` first and tell Srini what failed.
6. For each posted entry set `"status": "posted"` and `media_id`, add its row to `experiment-log.csv` (with `kind`,
   `bet`, `variable`, `control_id` and `prediction` copied from its `hypotheses/` card), commit and push to main.
7. Send Srini one short line: what posted (main and trials) and the links.
