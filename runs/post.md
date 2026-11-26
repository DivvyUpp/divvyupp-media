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
3c. **TikTok (Srini, 2026-11-26: Instagram and TikTok post together, every approved main Reel).** Right after a
   main entry posts on Instagram (and its YouTube step), publish the same video **publicly** to @getdivvyupp on TikTok
   through **Postproxy** (REST API, `POSTPROXY_API_KEY` in the environment; TikTok profile `MZU39X`). Run:
   `python3 scripts/post_tiktok.py <entry.id>` from the repo root. It posts `entry.tiktok_caption` (else
   `entry.caption` with only the "Link in the comments." sentence removed: that comment is Instagram-only), video = the same GitHub Pages URL as step 3, public, comments / Duet /
   Stitch on, posted now (the Post slots already are the schedule), then waits for TikTok and writes `tiktok_id`,
   `tiktok_url` and `tiktok_postproxy_id` onto the entry in `queue.json`. Tested end to end 2026-11-26 (same-10k
   v12 → https://www.tiktok.com/@getdivvyupp/video/7712592763354762509).
   - Exit 0 = live: commit the `queue.json` change with the Instagram one. Exit 1 = refused or failed: the reason is
     on stderr; log status `partial` with it and tell Srini. Exit 2 = still processing after ~10 minutes: log
     `partial`, tell Srini, and leave it: the next run checks `GET https://api.postproxy.dev/api/posts/<tiktok_postproxy_id>`
     and copies the permalink onto the entry once it shows `published`.
   - Never post twice: the script refuses an entry that already has `tiktok_id` or `tiktok_postproxy_id`, and sends
     an idempotency key per entry. Never work around a refusal, never retry blindly, never post a private copy or a
     draft. Skip trial entries (the script refuses them too).
   - **If `POSTPROXY_API_KEY` is not set, TikTok is NOT skipped silently:** Instagram still posts, the run log status
     is `partial` with "TikTok: POSTPROXY_API_KEY missing in this environment", and Srini is told the same run.
   - The script needs `api.postproxy.dev` reachable. It does not need `divvyupp.github.io` (Postproxy fetches the video
     itself).
   - Backfill like YouTube: one approved, posted main entry from the last 3 days with no `tiktok_id` and no
     `tiktok_postproxy_id` per run.
4. Trial entries (`"kind": "trial"`): same action plus `trial_params: {"graduation_strategy": "MANUAL"}`. Instagram
   reportedly needs 200+ followers for trials. If the publish fails with a follower-requirement error, set the entry's
   status to `"trial_rejected"`, check with `get_data` that nothing reached the grid, don't retry, and tell Srini.
5. Never edit captions. Never post anything not approved. If a publish fails, do not retry blindly; check with
   `get_data` first and tell Srini what failed.
6. For each posted entry set `"status": "posted"` and `media_id`, add its row to `experiment-log.csv` (with `kind`,
   `bet`, `variable`, `control_id` and `prediction` copied from its `hypotheses/` card), commit and push to main.
7. Write your run log record (`runlog/<today>/post.json`, see "Run log" in `PLAYBOOK.md`) and push it with the rest; write it even if you stop early. Each slot appends its own attempt, including slots where nothing was approved
   (status `ok`, summary "Nothing approved to post").
8. Send Srini one short line: what posted (main and trials) and the links (Instagram, YouTube and TikTok). If any of
   the three is missing for a main Reel, say which and why in that same line.
