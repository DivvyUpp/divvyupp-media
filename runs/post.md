# Post run (3 slots a day: about noon, 5pm and 10pm ET)

Post today's approved Reels to @getdivvyupp. Only entries Srini explicitly approved may ever be posted.

1. `TZ=America/New_York date +%F` gives today. Read `queue.json`. Take the entries with `"status": "approved"` and
   `post_date` on or before today, oldest `post_date` first, then queue order. Skip entries with a `not_before` time
   (ET, "HH:MM") later than now. **Post only the first main entry** (one Reel per slot), plus any approved trial
   entries with the same `post_date` (trials don't use a slot). If there are none, finish quietly.
   Skip any approved entry that already has `instagram_postproxy_id` (an earlier Instagram attempt failed or is
   still processing: Srini checks it, it is never re-posted) and name it in the reply.
2. **Everything posts through Postproxy (Srini, 2026-11-27): Instagram, TikTok and YouTube.** Windsor is no longer
   used for posting (it stays for the Instagram numbers in the Metrics pull). This run needs only
   `POSTPROXY_API_KEY` and `api.postproxy.dev`, so it runs as a Claude Code cloud session, not Cowork.
3. Post the entry from step 1 (main or trial) with ONE command from the repo root:
   `python3 scripts/post_reel.py <entry.id>`
   (`--dry-run` prints both payloads and sends nothing.) What it does, in order:
   - **Instagram first**, as its own Postproxy post (profile `6lUEBB` = account `17841422626862357`): Reel,
     `share_to_feed` on, cover = `entry.cover` or the rendered `reels/<video>_cover.jpg` (2026-11-27: no more setting
     covers by hand), caption = `entry.caption` exactly, video =
     `https://divvyupp.github.io/divvyupp-media/<entry.file>`. Main entries with `first_comment` (and no
     `first_comment_id`) get it as Postproxy's `first_comment`, posted right after the Reel is live; the script
     records Instagram's comment id as `first_comment_id` when Postproxy lists it. Instagram's API can't pin comments:
     tell Srini to pin it in the app. Trial entries (`"kind": "trial"`) post with `trial_strategy: "MANUAL"` (no
     first comment) and go nowhere else.
   - On success it sets `"status": "posted"`, `posted_at` (ET), `instagram_url`, `instagram_id` (shortcode) and
     `instagram_postproxy_id`. The numeric Graph `media_id` is filled in by the next Metrics pull from Windsor.
   - **Then TikTok + YouTube Shorts** for main entries only, in one Postproxy request (`scripts/post_postproxy.py`,
     called by `post_reel.py`): caption = `entry.tiktok_caption`, else `entry.caption` with only the "Link in the
     comments." sentence removed; YouTube title = `entry.hook` without a trailing "(...)" note, cut to 100
     characters; both public, TikTok comments / Duet / Stitch on. Writes `tiktok_*` / `youtube_*` ids and urls.
   - **If Instagram does not publish, nothing goes to TikTok or YouTube.** No backfill or catch-up on any platform
     (Srini, 2026-11-26): only the Reel this slot posts. Older Reels go to TikTok/YouTube only when Srini asks for
     that specific Reel (`python3 scripts/post_postproxy.py <id>`).
   - Never posts twice: each platform is left out once its id or Postproxy post id is on the entry (the Postproxy
     id is saved BEFORE waiting), Instagram also refuses if a recent Postproxy post already sent the same file, and
     every request carries an idempotency key.
   - Exit 0 = live everywhere it should be: go on to step 6. Exit 1 = refused or a platform failed (reason on
     stderr; whatever published is recorded): if Instagram failed, the entry stays `approved`; log `failed` (or
     `partial` if Instagram is live) and tell Srini. Exit 2 = a platform still processing after ~10 minutes: log
     `partial`, tell Srini the Postproxy post id, and leave it. Never retry blindly, never work around a refusal,
     never post a private copy or a draft. To check a Postproxy post: `GET https://api.postproxy.dev/api/posts/<id>`.
   - If `POSTPROXY_API_KEY` is not set, nothing posts: log `failed` with "POSTPROXY_API_KEY missing in this
     environment" and tell Srini.
4. Trials need 200+ followers on Instagram. If a trial fails with a follower-requirement error, set the entry's
   status to `"trial_rejected"`, check on Instagram (Postproxy post status / the app) that nothing reached the grid,
   don't retry, and tell Srini.
5. Never edit captions. Never post anything not approved.
6. For each posted entry (the script already set `"status": "posted"`), add its row to `experiment-log.csv` (with `kind`,
   `bet`, `variable`, `control_id` and `prediction` copied from its `hypotheses/` card; leave `media_id` empty, the Metrics pull fills it), commit and push to main.
7. Write your run log record (`runlog/<today>/post.json`, see "Run log" in `PLAYBOOK.md`) and push it with the rest; write it even if you stop early. Each slot appends its own attempt, including slots where nothing was approved
   (status `ok`, summary "Nothing approved to post").
8. Send Srini one short line: what posted (main and trials) and the links (Instagram, YouTube and TikTok). If any of
   the three is missing for a main Reel, say which and why in that same line.
