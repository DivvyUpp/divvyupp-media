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
3a. **First comment (added 2026-11-23, Srini).** If the posted entry has `first_comment`, post it right after the
   Reel is live: Windsor `execute_action`, connector `instagram`, action `create_comment`, `media_id` = the new
   media id, `message` = `entry.first_comment` exactly. Save the returned id on the entry as `first_comment_id`.
   Never post it twice (skip if `first_comment_id` is set). Windsor can't pin comments: tell Srini to pin it in the
   app. If the comment fails, the Reel still stands: don't retry blindly, log status `partial` and tell Srini.
3b. **YouTube Shorts (added 2026-11-23, Srini).** Right after a main entry posts on Instagram, upload the same video
   to the DivvyUpp YouTube channel (@getdivvyupp): Windsor `execute_action`, connector `youtube`, account `115938`,
   action `upload_video` with `video_url` = the same URL as step 3, `title` = `entry.hook` with any trailing
   "(...)" note removed and cut to 100 characters, `description` = `entry.caption`, `privacy_status` = `"public"`,
   `made_for_kids` = false, `category_id` = `"22"`. A vertical video of 3 minutes or less is a Short automatically.
   Skip the upload if the entry already has `youtube_id` (never upload twice) and skip trial entries. Save the
   returned id and URL on the entry as `youtube_id` and `youtube_url`. If the upload fails, the Instagram post still
   stands: don't retry, put the error in the run log as status `partial` with the blocker, and tell Srini.
   **Backfill:** every run, also upload any main entry with `"status": "posted"`, a `post_date` in the last 3 days and
   no `youtube_id` (one upload per run, oldest first), even when nothing new is approved for Instagram. If YouTube
   answers "rate-limited", stop and leave it for the next run.
3c. **TikTok (added 2026-11-26, Srini: "whatever is the most automated").** Right after a main entry posts on
   Instagram (and its YouTube step), publish the same video **publicly** to @getdivvyupp on TikTok with the TikTok
   posting connector Srini connected (planned: PostProxy's MCP; use whatever TikTok publish tool the session lists).
   Video = the same `video_url` as step 3; caption = `entry.tiktok_caption` (fall back to `entry.caption` with the
   "Link in the comments" sentence removed); privacy public; comments, duet and stitch on. Post now, not scheduled:
   the Post slots already are the schedule. Save the returned id/URL as `tiktok_id` / `tiktok_url`.
   - Never post twice: skip if the entry has `tiktok_id`; after a failure or timeout, check the account's latest
     posts (or the publish status) before anything else, and never retry blindly. Skip trial entries.
   - **If no TikTok posting tool is in the session, skip this step** and write "TikTok not connected" in the run log
     summary (status stays `ok`; tell Srini once per day at most).
   - If TikTok only allows a private post or a draft (TikTok's unaudited-app limit), don't post private copies:
     stop the TikTok step, log status `partial` with that blocker, and tell Srini.
   - Backfill like YouTube: one approved, posted main entry from the last 3 days with no `tiktok_id` per run.
4. Trial entries (`"kind": "trial"`): same action plus `trial_params: {"graduation_strategy": "MANUAL"}`. Instagram
   reportedly needs 200+ followers for trials. If the publish fails with a follower-requirement error, set the entry's
   status to `"trial_rejected"`, check with `get_data` that nothing reached the grid, don't retry, and tell Srini.
5. Never edit captions. Never post anything not approved. If a publish fails, do not retry blindly; check with
   `get_data` first and tell Srini what failed.
6. For each posted entry set `"status": "posted"` and `media_id`, add its row to `experiment-log.csv` (with `kind`,
   `bet`, `variable`, `control_id` and `prediction` copied from its `hypotheses/` card), commit and push to main.
7. Write your run log record (`runlog/<today>/post.json`, see "Run log" in `PLAYBOOK.md`) and push it with the rest; write it even if you stop early. Each slot appends its own attempt, including slots where nothing was approved
   (status `ok`, summary "Nothing approved to post").
8. Send Srini one short line: what posted (main and trials) and the links (Instagram, YouTube and TikTok).
