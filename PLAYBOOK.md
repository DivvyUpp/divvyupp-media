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
- Brand: warm off-white background, orange #E04A1A, near-black #15100F, Plus Jakarta Sans.
- Voice (agreed with Srini 2026-11-16): ElevenLabs, model `eleven_v3`, **Jessica** (`cgSgspJ2msm6clMCkdW9`) for presenter C,
  spec value `"character_voice": "elevenlabs:cgSgspJ2msm6clMCkdW9:eleven_v3"`. Direct the delivery with v3 audio tags
  ([playful], [sighs], [reassuring], [happy]...). Kokoro `af_heart` sounded flat and is retired for Reels.
  The API key comes from env `ELEVENLABS_API_KEY` (or `~/.secrets/elevenlabs_key`); never commit it. If the key is
  missing, ask Srini (SendUserMessage + PushNotification) to paste the key in the session, save it to
  `~/.secrets/elevenlabs_key` (chmod 600, outside the repo) and carry on. If `api.elevenlabs.io` is blocked, stop and
  tell Srini to add it under Settings → Capabilities → Allowed websites. Never fall back to Kokoro.
- Guarantee wording (agreed 2026-11-16): "If you don't save more or spend less in 90 days, we refund your subscription,
  up to $30. Terms apply." Never "or both", never "save more and spend less".
- No competitor names, no maths equations on screen, no invented testimonials. The founder figure is
  "about $1,000 a month" saved; don't inflate it.

## The offer and message (what every Reel sells)
Fixed bills stay fixed. What's left is flexible money. DivvyUpp has you save first (you choose the amount),
then gives a daily and weekly guide for the rest that adjusts when you overspend, before you spend, not after.
No budgeting homework: it sorts transactions into fixed or flexible automatically. 90-day guarantee: save more,
spend less, or both, or the subscription is refunded up to $30 (terms apply). Audience: two-income households
with a mortgage and kids who earn well but have nothing left at month end.

## Story Reels and presenter characters (agreed with Srini 2026-11-15)
A story Reel tells the whole loop, not just a hook: pain → save first (approved body, part 1) → the daily/weekly
guide for the rest that adjusts when you overspend → payoff (bills paid, savings kept, guilt-free spending) →
guarantee + CTA (body, part 2). Render with `python3 pipeline/make_story_reel.py hooks/<id>.json` (spec format in
that file; `--check` writes one still per scene). Keep it under 90s (Srini prefers clarity over a 60s cap).
Current template (approved 2026-11-16), copy `hooks/2026-11-19-a.json`:
- hook → **four-numbers `plan` scene** (income and fixed bills checked against bank history, savings you pick,
  safe-to-spend; replaces the old "flips the order" body section, `skip_flip: true`) → guide with **two `spends`**
  → payoff → `"ending": "rendered"` (guarantee + CTA in the same voice, new guarantee wording; the CTA line is
  "Save first. Then spend with confidence. Try it at divvyupp dot com.", which Srini prefers to the bare URL).
- Optional data-backed `stat` card in the hook (guess vs actual, or a %), only from a real, checked source shown
  on screen (e.g. C+R Research 2022: subscriptions guessed $86 vs actual $219; PYMNTS/LendingClub Sept 2023: 44% of
  >$100K earners live paycheck to paycheck). Never invent a statistic.
- Delivery tags must fit the moment: no [sighs] on things people are happy to buy (kids' gear, a party).
- Guide lines are full, clear sentences, e.g. "Then your car needs a repair. That's a hundred and sixty dollars, so
  you're ninety over for today. DivvyUpp spreads that across the rest of your week, and tomorrow adjusts to
  forty-seven." Never clipped ("Tomorrow: forty-seven"). Moderate examples: tomorrow drops by about half, not to
  near zero. Use everyday spends (grocery run, online order, kid's birthday party, car repair); no brand names.
- Each Reel needs its own example, numbers and payoff line; don't repeat the previous days' storyline.
- Founder story (stated by Srini, true, he can show the activity): he makes good money but had nothing to show for it
  at month end, built DivvyUpp to fix his own problem, and now saves about $1,000 a month with it.
- Mascot (agreed with Srini 2026-11-16): the **raccoon**, named **Dollar Bill** (written out as "Dollar Bill", never "$Bill"; agreed 2026-11-19), soft-3D plush style (`"character": "raccoon_soft3d"` from
  `pipeline/animals.py`), voiced by **Valf** (`"character_voice": "elevenlabs:loY1uopAz31XyhAEhNSa:eleven_v3"`): upbeat,
  snarky, animated, never deadpan. Our own character: never imitate a film character or actor. The snark is aimed at
  spending habits, never at the viewer; he still lets you enjoy things. Lock his voice with `"voice_prefix"`: the take opens with the reference demo's first lines ("Whoa, whoa, whoa. I've seen your bank history! ... On a TUESDAY? ... I know exactly where money disappears to."), which are then cut off, so v3 settles into the approved character (Srini confirmed 2026-11-19 this matches; picking takes by pitch alone did not). Reference audio: `pipeline/assets/voices/raccoon_reference.wav`. Never clone a library voice. Keep his scripts ~20% shorter than the human
  presenters' (energetic delivery runs long). Reference spec: `hooks/raccoon-demo.json`. How many raccoon Reels per
  week is still to be agreed with Srini; propose a split and compare skip rate and watch time against the humans.
- ElevenLabs Reels are voiced in one take that becomes the uncut soundtrack; scenes change in its natural pauses.
- Presenters and voices: C (female) = Jessica `cgSgspJ2msm6clMCkdW9`; E (male) = Eric `cjVigY5qzO86Huf0OWal`
  (`"character_voice": "elevenlabs:cjVigY5qzO86Huf0OWal:eleven_v3"`). Week of 2026-11-16: C on Mon-Thu, E on Fri-Sat.
Rules for every presenter character, current or new:
- Drawn in `pipeline/characters.py` as SVG in the same flat editorial style as presenters A–E: head and
  shoulders, real proportions (short neck, broad shoulders), soft shading, believable outfit for the audience
  (mid-30s to early-40s working parent). Presenter **C** is the current pick; reuse it before inventing a new one.
- **Only the face moves.** No hands or arm gestures (tried, looked bad). Small idle bob and natural blinks only.
- **Lip-sync from phoneme timings**, never from loudness. Mouth shapes are the soft visemes in
  `characters.py` (lip-coloured edge, at most a sliver of teeth). Never a wide toothy grin: it read as angry.
- Mood: worried in the pain hook (corners slightly down, brows up in the middle), neutral in the guide,
  happy in the payoff.
- Voice: Kokoro `af_heart` for both presenter and narrator.
- A presenter is not the founder and not a customer: she speaks to the viewer ("you"). The founder result is
  stated as the founder's ("our founder saves about $1,000 a month"). No name tags.
- Light background music (`pipeline/music.py`, synthesised, no licensing) sits under the voice and ducks
  while anyone speaks.
- When adding a character, show Srini a lineup still (resting and talking) before rendering any video.

## Monday run: plan and produce
1. `bash pipeline/setup.sh` (once per machine).
2. Pull stats for every `posted` queue entry through Windsor `get_data` (connector `instagram`, fields from
   `get_fields`: `media_id, media_views, media_reach, media_reel_skip_rate, media_reel_avg_watch_time,
   media_shares, media_saved, media_reel_total_interactions`, a date range wide enough to include the post).
   Fill the matching rows in `experiment-log.csv` (avg watch in seconds).
3. Read the funnel. The GitHub Action `Funnel weekly fetch` writes last Monday–Sunday (ET) to
   `funnel/<ISO-year>-W<ISO-week>.json` at about 5:37am ET. Open the newest file whose `from`/`to` cover last
   week. If it is missing (GitHub sometimes skips scheduled runs; it did on 2026-11-16), trigger the workflow by
   hand (GitHub `actions_run_trigger`, `run_workflow`, `funnel-weekly.yml` on `main`), wait for it and pull. Only if
   that also fails say **"funnel data unavailable"** in the report, say why, and do not guess any numbers. Otherwise, from `instagram.days[]` (one row per day, `stages` gives the order of
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
5. Write **5 new story Reel specs** in `hooks/<YYYY-MM-DD>-a.json` (one per day Tue-Sat) using the story template
   above and `pipeline/make_story_reel.py`, NOT the old text-only `make_reel.py`. Each tests one idea (pain question,
   founder result, guarantee-first, before-you-spend, no-budget, audience call-out, flexible-spending reality check).
6. Check each with `python3 pipeline/make_story_reel.py hooks/<id>.json --check` and look at every still; then render.
   Srini reviews one day at a time if he asks to; keep unapproved videos out of the repo (scratch folder).
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

## How-it-works explainer (landing page)
`python3 pipeline/make_explainer.py hooks/how-it-works-raccoon.json` renders the 1080p landscape explainer: Dollar Bill
on the left, app screens redrawn in the current brand (`pipeline/screens.py`, never the old blue screens) in a phone on
the right, captions, one uncut voice take. Approved 2026-11-19: `reels/how-it-works-dollar-bill.mp4`. No founder name;
CTA is the free beta ("go to divvyupp dot com and tap Get Started, free during the beta, no card required").
