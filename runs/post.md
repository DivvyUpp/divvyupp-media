# Post run (3 slots a day: about noon, 5pm and 10pm ET)

Post today's approved Reels to @getdivvyupp. Only entries Srini explicitly approved may ever be posted.

1. `TZ=America/New_York date +%F` gives today. Read `queue.json`. Take the entries with `"status": "approved"` and
   `post_date` on or before today, oldest `post_date` first, then queue order. Skip entries with a `not_before` time
   (ET, "HH:MM") later than now. **Post only the first main entry** (one Reel per slot), plus any approved trial
   entries with the same `post_date` (trials don't use a slot). If there are none, finish quietly.
2. Before posting, use Windsor `get_data` (connector `instagram`, account `17841422626862357`) to list media created
   today, so nothing posts twice. Skip any entry whose video is already live.
3. Post it (`kind` is `"main"` or missing): Windsor `execute_action`
   `create_video_post`, `video_url` = `https://divvyupp.github.io/divvyupp-media/<entry.file>`, `caption` =
   `entry.caption`, `share_to_feed` = true.
3b. **YouTube Shorts (added 2026-11-23, Srini).** Right after a main entry posts on Instagram, upload the same video
   to the DivvyUpp YouTube channel (@getdivvyupp): Windsor `execute_action`, connector `youtube`, account `115938`,
   action `upload_video` with `video_url` = the same URL as step 3, `title` = `entry.hook` with any trailing
   "(...)" note removed and cut to 100 characters, `description` = `entry.caption`, `privacy_status` = `"public"`,
   `made_for_kids` = false, `category_id` = `"22"`. A vertical video of 3 minutes or less is a Short automatically.
   Skip the upload if the entry already has `youtube_id` (never upload twice) and skip trial entries. Save the
   returned id and URL on the entry as `youtube_id` and `youtube_url`. If the upload fails, the Instagram post still
   stands: don't retry, put the error in the run log as status `partial` with the blocker, and tell Srini.
4. Trial entries (`"kind": "trial"`): same action plus `trial_params: {"graduation_strategy": "MANUAL"}`. Instagram
   reportedly needs 200+ followers for trials. If the publish fails with a follower-requirement error, set the entry's
   status to `"trial_rejected"`, check with `get_data` that nothing reached the grid, don't retry, and tell Srini.
5. Never edit captions. Never post anything not approved. If a publish fails, do not retry blindly; check with
   `get_data` first and tell Srini what failed.
6. For each posted entry set `"status": "posted"` and `media_id`, add its row to `experiment-log.csv` (with `kind`,
   `bet`, `variable`, `control_id` and `prediction` copied from its `hypotheses/` card), commit and push to main.
7. Write your run log record (`runlog/<today>/post.json`, see "Run log" in `PLAYBOOK.md`) and push it with the rest; write it even if you stop early. Each slot appends its own attempt, including slots where nothing was approved
   (status `ok`, summary "Nothing approved to post").
8. Send Srini one short line: what posted (main and trials) and the links (Instagram and YouTube).
