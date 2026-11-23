# Create run (daily, 06:27 ET)

Learn from what posted, then make today's Reel around one clear bet. Never post in this run.

## 0. Set up
`bash pipeline/setup.sh` (once per machine). `TZ=America/New_York date +%F` gives today. Read `PLAYBOOK.md`,
`learnings.md`, `backlog.md` and the last 3 files in `hypotheses/`. Read today's `research/<today>.md` only to quote
one line of it to Srini (if the Research run has not written it, say so and carry on); ideas never come from it.

## 1. Monday only: weekly review (do this first)
1. Read the weekly funnel: the GitHub Action `Funnel weekly fetch` writes last Monday–Sunday (ET) to
   `funnel/<ISO-year>-W<ISO-week>.json` at about 5:37am ET. If it is missing, trigger `funnel-weekly.yml` on `main`
   by hand (`workflow_dispatch`), wait and pull. If that fails too, say **"funnel data unavailable"** and why, and
   guess no numbers.
2. Score the week: Reel views → Instagram visits → Get started → sign-ups → bank linked, plus followers gained.
   Compare with last week's row in `targets.json` (ahead / on track within ±20% / behind). Never edit
   `targets.json` without Srini's explicit agreement.
3. Promote any pattern that won twice into `learnings.md` (and, if it changes the template, propose it to Srini).
   Retire any that lost twice. Prune `backlog.md`.
4. Update the Growth Tracker dashboard (https://claude.ai/artifact/8vyZDG1RR62SbamqpwaXzA): attach DivvyUpp/divvyupp
   with push access, `git fetch origin outreach-log`, check out outreach-log, and follow `docs/dashboard/README.md`
   exactly (weekly.csv last week's row, reels.csv a row per posted Reel, actions.csv any loop change). Commit and push
   to outreach-log only (never main), then upload the changed CSVs with upload_asset (slug
   40393e71-2526-4648-9859-26f12f001b13) and update each dataset's source url and updated.at with db_get + db_write
   as the README says. Never invent numbers. If the artifact tools aren't available, say so.

## 2. Read the data
The Create run has no Windsor connector. The Metrics pull run (`runs/metrics.md`, 05:53 ET) pulls the Instagram
numbers with Windsor and commits them before this run starts.
1. `git pull` and read `metrics/<today>.json`. It holds every Reel posted in the last 8 days (views, reach, skip
   rate, avg watch, shares, saves, likes), today's `followers_count` and yesterday's `views_non_followers`. The
   pull has already written `read_d1` / `read_72h` into `experiment-log.csv` and today's row in `followers.csv`.
   If `metrics/<today>.json` is missing, say **"Instagram numbers unavailable: the metrics pull didn't land"** at
   the top of the note to Srini, mark every postmortem due today **inconclusive (no data)**, never guess a number,
   and carry on with steps 4–7.
2. Work out the 200-follower scorecard in `PLAYBOOK.md` (avg watch ÷ length, likes per 100 reached, shares per 100
   reached) for each Reel read today.
3. Request yesterday's funnel: trigger `funnel-weekly.yml` with `from` = `to` = yesterday, wait, pull, and read
   `funnel/custom-<yesterday>_<yesterday>.json` (`instagram.days[]`: `ig_visits`, `get_started_clicked`, `signed_up`,
   `bank_linked`). Write them on the rows posted that day. If it fails, say "funnel unavailable" and carry on.

## 3. Postmortem
For each Reel with a fresh `read_72h` (and, as an early signal only, yesterday's `read_d1`):
1. Compare with its card's prediction. Verdict: **supported**, **refuted** or **inconclusive** (noise rules apply).
2. Ask why, in one or two lines. Was it the bet, the script, or the execution (voice, visuals, length)?
   Use watch time against video length to say where viewers left.
3. Write the postmortem at the bottom of that Reel's `hypotheses/<date>.md`, and fill `verdict` and `learning` in
   `experiment-log.csv`.
4. Update `learnings.md` only as the noise rules allow. Note which goal layer moved, not just views.

## 4. Pick today's bets (rapid-test phase: up to 3 Reels a day)
Today's Reels come from `backlog.md` and nowhere else. Take bets from the top: **proven** first, then
**supported**; never one marked needs proof or blocked. One Reel per bet, up to 3. Where a bet's row cites a
research brief, read that part of the brief for its numbers and sources. An idea that is in a brief but not yet in
the backlog isn't ready: leave it. If fewer than 3 bets qualify, make fewer and say why. Each Reel has its own card in
`hypotheses/<today>.md`; the variable is the format, the control is the median of our last 5 Reels. Lengths 30–50 s
unless the card says otherwise.

## 5. Script workshop
1. For each Reel, write **6–8 hook candidates** that follow the format's pattern, then a **hook review**: two
   subagents, each in a different viewer persona from the target audience, see only the lines and mark each STOP or
   SCROLL with the question it raises. Keep a hook only if both stop. What stops viewers so far: a moment they're in,
   or something they can check against themselves tonight (`research/hook-review-2026-11-20.md`). Score each against the script checklist in `PLAYBOOK.md`. Drop any
   that repeat the last 5 Reels.
   Then build the opening on the **four-layer gate** (PLAYBOOK checklist item 11). Layer 1 is one person in one
   painful moment that Research has backed (PLAYBOOK "Messaging rule"), worded from `research/pain-language.md` where
   it has a fitting phrase: problem in their words, the stakes,
   something new, a clear promise. Each persona reviewer also answers, for the full opening: who is this for, what's
   it costing them, what did I learn that I didn't believe before, and what am I staying for? Any "don't know" is a
   fail: rewrite that layer.
2. Write the **best 2 as full scripts**.
3. Run a **cold review**: start a subagent that sees only the script and the `--check` stills (not the card or
   this playbook). Ask it, as a scrolling viewer in the target audience: what did you understand at 2 seconds,
   where would you scroll away, would you share it, and why, and whether each of the four opening layers landed. Revise. Pick one. Record the 10 hooks, the scores, the
   review and the changes in `hypotheses/<today>.md`.
4. No trial variants until 200 followers (Trial Reels need it).

## 6. Render
No Runway in this run (Srini, 2026-11-21): use only images that are in the repo, such as Dollar Bill in
`pipeline/assets/characters/` and the drawn presenters. Never point a spec at a `/tmp` path: older `hooks/` specs
reference Runway images from past chat sessions that no longer exist. Srini polishes the visuals himself after review.
Use `pipeline/make_story_reel.py` with a spec in `hooks/<today>-a.json` (trial variants `-t1`, `-t2`), or another
format if the bet calls for it and the tool exists. `--check` first and look at every still; then render. Save each
video as `reels/<id>.mp4`: the dashboard shows it there for Srini to review (the repo is public; Srini accepted on
2026-11-21 that Reels waiting for review are visible).

## 7. Queue and send
1. Add queue entries with `"status": "pending_review"`, `"post_date": today`, `"kind": "main"`, `"file"`, `"hook"`,
   a caption each, and `"hypothesis": "hypotheses/<today>.md"`. Commit and push `reels/`, `hooks/`, `queue.json` and
   today's run log record to main straight away, so the Reels show on the dashboard
   (https://divvyupp.github.io/divvyupp-media/dashboard/) before you message Srini.
2. Send Srini a push notification (PushNotification): "<n> Reels ready for review" with the review page link
   https://divvyupp.github.io/divvyupp-media/dashboard/review.html. Do this every time, even if the run's own
   notification also fires. If the tool isn't available, say so at the top of your message.
3. Send Srini the videos (SendUserFile) and one short note:
   - research: one line from today's brief;
   - postmortem: one line per Reel judged today (verdict and why);
   - today's card (bet, variable, prediction);
   - captions; ask him to approve, edit or reject each **by 11:30am ET** (he reviews from about 9am; the Post slots are noon, 5pm and 10pm, and anything approved later goes out in the next free slot).
   Put the dashboard link at the top. On Mondays, put the weekly scorecard first.
4. When he replies: apply edits (re-render and resend anything that changed), set approved entries to
   `"approved"`, set rejected ones to `"rejected"` and delete their video from `reels/`, then commit and push `hooks/`,
   `reels/`, `queue.json`,
   `experiment-log.csv`, `learnings.md`, `backlog.md` and `hypotheses/` to main. Confirm one Pages link loads.

## 8. Run log
Write your run log record (`runlog/<today>/create.json`, see "Run log" in `PLAYBOOK.md`) and push it with the rest; write it even if you stop early. Write it when you send the videos (each Reel with
`status: pending_review` and its hook), and update that same attempt when Srini answers (approved / rejected).
Include `file` for each Reel, since the videos are in the repo from the start.

If something blocks you (render, voice, push), tell Srini exactly what and stop.
