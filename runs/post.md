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
3b. **TikTok + YouTube Shorts, through Postproxy (Srini, 2026-11-26).** Right after a main entry posts on Instagram,
   the SAME entry goes to @getdivvyupp on TikTok and on YouTube (Shorts) in one Postproxy request (one Postproxy post,
   whatever the number of platforms). From the repo root run:
   `python3 scripts/post_postproxy.py <entry.id>`
   (Postproxy REST API, `POSTPROXY_API_KEY` in the environment; profiles TikTok `MZU39X`, YouTube `rOUpVX`.) It posts
   `entry.tiktok_caption`, else `entry.caption` with only the "Link in the comments." sentence removed (that comment is
   Instagram-only), as the TikTok caption and the YouTube description; YouTube title = `entry.hook` without a trailing
   "(...)" note, cut to 100 characters; both public, TikTok comments / Duet / Stitch on; posted now (the Post slots
   already are the schedule). It waits for both, then writes `tiktok_id` / `tiktok_url` / `tiktok_postproxy_id` and
   `youtube_id` / `youtube_url` / `youtube_postproxy_id` onto the entry in `queue.json`. Tested end to end 2026-11-26
   (TikTok: same-10k v12; YouTube: S8 minimum → https://www.youtube.com/watch?v=U82Qn1ZS-GU).
   - **Only the Reel this slot just posted to Instagram. No backfill or catch-up on TikTok or YouTube (Srini,
     2026-11-26).** If nothing posted to Instagram this slot, nothing goes to TikTok or YouTube. Older Reels go there
     only when Srini asks for that specific Reel. Skip trial entries (the script refuses them).
   - Exit 0 = live on both: commit `queue.json` with the Instagram change. Exit 1 = refused or a platform failed (the
     reason is on stderr; a platform that did publish is still recorded): log status `partial`, tell Srini. Exit 2 =
     a platform still processing after ~10 minutes: log `partial`, tell Srini the Postproxy post id, and leave it.
   - Never post twice: the script leaves out any platform the entry already has `<platform>_id` or
     `<platform>_postproxy_id` for, and sends an idempotency key. Never work around a refusal, never retry blindly,
     never post a private copy or a draft.
   - If `POSTPROXY_API_KEY` is not set, Instagram still posts; the run log status is `partial` with "Postproxy:
     POSTPROXY_API_KEY missing in this environment", and Srini is told the same run.
   - YouTube no longer goes through Windsor (its uploads kept coming back "rate-limited"). Windsor stays for Instagram.
   - The script needs `api.postproxy.dev` reachable, not `divvyupp.github.io` (Postproxy fetches the video itself).
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
