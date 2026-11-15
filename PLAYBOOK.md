# DivvyUpp Reels loop: playbook for scheduled runs

This repo is the memory of the weekly content loop. Scheduled Claude runs read this file first.
Videos are served publicly by GitHub Pages at `https://divvyupp.github.io/divvyupp-media/<path>`.

## Ground rules (never break these)
- **Nothing is posted to Instagram unless its queue entry has `"status": "approved"`**, set only after Srini
  watched the actual video and said yes in chat. Videos awaiting review are sent to him as files and are
  **not pushed to this public repo** until approved.
- Post only through the Windsor.ai for Social Media connector: connector `instagram`, account `17841422626862357`
  (@getdivvyupp), action `create_video_post`, `share_to_feed: true`.
- @getdivvyupp is the single main account for all DivvyUpp content (the personal @srinithinks account is retired).
- Cadence: 5 Reels a week, Tuesday to Saturday, one per day. At most one post per day. If anything fails, stop and tell Srini; do not retry a publish blindly (check with
  Windsor `get_data` for a media created today before any retry, so nothing posts twice).
- Brand: warm off-white background, orange #E04A1A, near-black #15100F, Plus Jakarta Sans. Voice: Kokoro `af_heart`.
- No competitor names, no maths equations on screen, no invented testimonials. The founder figure is
  "about $1,000 a month" saved; don't inflate it.

## The offer and message (what every Reel sells)
Fixed bills stay fixed. What's left is flexible money. DivvyUpp has you save first (you choose the amount),
then gives a daily and weekly guide for the rest that adjusts when you overspend, before you spend, not after.
No budgeting homework: it sorts transactions into fixed or flexible automatically. 90-day guarantee: save more,
spend less, or both, or the subscription is refunded up to $30 (terms apply). Audience: two-income households
with a mortgage and kids who earn well but have nothing left at month end.

## Monday run: plan and produce
1. `bash pipeline/setup.sh` (once per machine).
2. Pull stats for every `posted` queue entry through Windsor `get_data` (connector `instagram`, fields from
   `get_fields`: `media_id, media_views, media_reach, media_reel_skip_rate, media_reel_avg_watch_time,
   media_shares, media_saved, media_reel_total_interactions`, a date range wide enough to include the post).
   Fill the matching rows in `experiment-log.csv` (avg watch in seconds).
3. Read the funnel. The GitHub Action `Funnel weekly fetch` writes last Monday–Sunday (ET) to
   `funnel/<ISO-year>-W<ISO-week>.json` at 6am ET. Open the newest file whose `from`/`to` cover last
   week. If it is missing or older than last week, say **"funnel data unavailable"** in the report and do
   not guess any numbers. Otherwise, from `instagram.days[]` (one row per day, `stages` gives the order of
   `reach`), take per day: landing (`ig_visits`), `get_started_clicked` (`get_started`), `signed_up`
   (`signups`) and `bank_linked` (`bank_links`). Write them into `experiment-log.csv` on the row of the
   Reel posted that day (`posted_date`), and show the week as Reel views → Instagram visits → Get started
   → sign-ups → bank connected. Remember older Reels also drive traffic: attribution is by day, not per
   Reel. Use `all_sources` only for context (e.g. total sign-ups this week).
3b. Compare against targets. Find last week's row in `targets.json` (match `week` to the funnel file's
   ISO week). For each metric show actual vs target and mark it **ahead**, **on track** (within ±20%) or
   **behind**; also show running totals vs the month-1 and month-3 milestones in `_about`. Weeks before the
   first row: say "no target yet". If a metric is behind two weeks running, propose one concrete change for
   it (a hook idea, caption/CTA, landing page, or another channel) in the note to Srini. Never edit
   `targets.json` without Srini's explicit agreement.
4. Decide: the main signal is **skip rate (lower is better)** then **average watch time**; sign-ups and
   Get started from step 3 are the business result and win ties. With little data,
   say so plainly rather than over-reading one post. Write a short `decision` for last week's rows
   (keep / kill / iterate) and why.
5. Write **5 new hook specs** in `hooks/<YYYY-MM-DD>-<a..e>.json` (format in `pipeline/make_reel.py`).
   Each tests one idea against the current best (pain question, founder result, guarantee-first,
   "before you spend", no-budget). Keep text short enough for 1-4 big lines.
6. Check each with `python3 pipeline/make_reel.py hooks/<id>.json --check` and look at the still; then render
   all 5 (`python3 pipeline/make_reel.py hooks/<id>.json`).
7. Add queue entries with `"status": "pending_review"`, a caption per video (same structure as the first
   post), and proposed `post_date`s, one per day Tuesday to Saturday of this week, posted at 7pm ET.
8. Send Srini the 5 videos (SendUserFile) plus a short note: last week's numbers in one line each (Reel stats plus the funnel from step 3), then a short actual-vs-target scorecard from step 3b, what each
   new hook tests, and the proposed captions and dates. Ask him to approve, reject or edit each.
9. When he replies: apply edits (re-render if the hook changed and send it again), set approved entries to
   `"approved"`, drop rejected ones, then commit and push `hooks/`, approved `reels/`, `queue.json` and
   `experiment-log.csv`. Confirm one Pages link loads before finishing.

## Daily run: post one approved Reel
1. Read `queue.json`. Find the first entry with `"status": "approved"` and `post_date` equal to today (ET).
   If none, finish silently.
2. Publish it with Windsor `create_video_post` (video_url = Pages URL of `file`, caption from the entry).
3. Set `"status": "posted"` and `media_id`, add a row to `experiment-log.csv`, commit and push.
4. Send Srini one line: what posted and its link (`media_permalink` via `get_data` if available).
