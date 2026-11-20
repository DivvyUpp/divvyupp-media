# Create run (daily, 09:00 ET)

Learn from what posted, then make today's Reel around one clear bet. Never post in this run.

## 0. Set up
`bash pipeline/setup.sh` (once per machine). `TZ=America/New_York date +%F` gives today. Read `PLAYBOOK.md`,
`learnings.md`, `backlog.md`, today's `research/<today>.md` (if the Research run has not written it, say so and
carry on), and the last 3 files in `hypotheses/`.

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

## 2. Pull the data
1. Windsor `get_data` (connector `instagram`, account `17841422626862357`; fields from `get_fields`):
   `media_id, media_views, media_reach, media_reel_skip_rate, media_reel_avg_watch_time, media_shares,
   media_saved, media_reel_total_interactions` for every Reel posted in the last 8 days. Also `followers_count`
   (today's total) and account `views_non_followers` for yesterday.
2. Write into `experiment-log.csv`: `read_14h` for yesterday's Reels and `read_72h` for Reels posted 3 days ago,
   as `views/skip%/avg_watch_s/shares/saves`. The stats columns hold the latest read. Avg watch is in seconds.
3. Request yesterday's funnel: trigger `funnel-weekly.yml` with `from` = `to` = yesterday, wait, pull, and read
   `funnel/custom-<yesterday>_<yesterday>.json` (`instagram.days[]`: `ig_visits`, `get_started_clicked`, `signed_up`,
   `bank_linked`). Write them on the rows posted that day. If it fails, say "funnel unavailable" and carry on.

## 3. Postmortem
For each Reel with a fresh `read_72h` (and, as an early signal only, yesterday's `read_14h`):
1. Compare with its card's prediction. Verdict: **supported**, **refuted** or **inconclusive** (noise rules apply).
2. Ask why, in one or two lines. Was it the bet, the script, or the execution (voice, visuals, length)?
   Use watch time against video length to say where viewers left.
3. Write the postmortem at the bottom of that Reel's `hypotheses/<date>.md`, and fill `verdict` and `learning` in
   `experiment-log.csv`.
4. Update `learnings.md` only as the noise rules allow. Note which goal layer moved, not just views.

## 4. Pick today's bet
Take the top bet in `backlog.md` unless today's postmortem points to a better one; if so, say why. One variable
against the control (the current best Reel on the target metric). Write `hypotheses/<today>.md` with the card.

## 5. Script workshop
1. Write **10 hook candidates** for the bet. Score each against the script checklist in `PLAYBOOK.md`. Drop any
   that repeat the last 5 Reels.
2. Write the **best 2 as full scripts**.
3. Run a **cold review**: start a subagent that sees only the script and the `--check` stills (not the card or
   this playbook). Ask it, as a scrolling viewer in the target audience: what did you understand at 2 seconds,
   where would you scroll away, would you share it, and why. Revise. Pick one. Record the 10 hooks, the scores, the
   review and the changes in `hypotheses/<today>.md`.
4. Pick **2 trial variants** of the chosen script that change only the first 3 seconds (hook line, first frame or
   on-screen text), unless the card says trials are not useful today.

## 6. Render
Use `pipeline/make_story_reel.py` with a spec in `hooks/<today>-a.json` (trial variants `-t1`, `-t2`), or another
format if the bet calls for it and the tool exists. `--check` first and look at every still; then render. Keep
unapproved videos in a scratch folder, not in the repo (the repo is public).

## 7. Queue and send
1. Add queue entries with `"status": "pending_review"`, `"post_date": today`, `"kind": "main"` or `"trial"`, a
   caption each, and `"hypothesis": "hypotheses/<today>.md"`.
2. Send Srini the videos (SendUserFile) and one short note:
   - research: one line from today's brief;
   - postmortem: one line per Reel judged today (verdict and why);
   - today's card (bet, variable, prediction);
   - captions; ask him to approve, edit or reject each **by 5pm ET**.
   On Mondays, put the weekly scorecard and dashboard link first.
3. When he replies: apply edits (re-render and resend anything that changed), set approved entries to
   `"approved"`, drop rejected ones, then commit and push `hooks/`, approved `reels/`, `queue.json`,
   `experiment-log.csv`, `learnings.md`, `backlog.md` and `hypotheses/` to main. Confirm one Pages link loads.

If something blocks you (connector, render, push), tell Srini exactly what and stop.
