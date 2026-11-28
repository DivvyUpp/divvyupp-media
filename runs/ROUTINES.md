# Routine prompts for the daily loop

The scheduled routines were made in the Claude app, so they are changed there. Each prompt is short on purpose: the
logic lives in this repo, so changing the loop means editing `PLAYBOOK.md` and `runs/*.md`, not the routines.

## 1. Research (new routine) — every day, 05:57 America/New_York
Connectors: Gump (added by Srini 2026-11-28, `https://mcp.gump.io/mcp`; used per `runs/research.md` step 3).
Web search and fetch on.

```
You run the daily Research run for DivvyUpp's content loop (Instagram @getdivvyupp; DivvyUpp is a safe-to-spend personal finance app, divvyupp.com). Make sure the GitHub repo DivvyUpp/divvyupp-media is available (attach it with push access if it is not, then clone it). Read PLAYBOOK.md, then runs/research.md, and follow them exactly. Those files are the source of truth; if they differ from this prompt, they win. Never sign up for, buy, post or send anything. If something blocks you, tell Srini exactly what and stop.
```

## 2. Create (replaces "DivvyUpp Reels: Monday plan and produce") — every day, 06:27 America/New_York
Runs in the Default cloud environment (it has `ELEVENLABS_API_KEY` and allows `api.elevenlabs.io`). Connectors: none,
because tasks in that environment get none; the Instagram numbers come from the Metrics pull below. Repos:
DivvyUpp/divvyupp-media (push), DivvyUpp/divvyupp (push, Mondays, for the dashboard on outreach-log).

```
You run the daily Create run for DivvyUpp's Instagram Reels loop (@getdivvyupp). Make sure the GitHub repo DivvyUpp/divvyupp-media is available (attach it with push access if it is not, then clone it). Read PLAYBOOK.md, then runs/create.md, and follow them exactly. Those files are the source of truth; if they differ from this prompt, they win. On Mondays runs/create.md starts with the weekly review and the Growth Tracker dashboard update, which also needs DivvyUpp/divvyupp with push access (outreach-log branch only, never main). NEVER publish anything in this run and never mark anything approved without Srini's explicit yes in this session. If something blocks you, tell Srini exactly what and stop.
```

## 2b. Metrics pull — every day, 05:53 America/New_York (Cowork)
Needs the Windsor.ai for Social Media connector (Instagram). Repos: DivvyUpp/divvyupp-media (push). Instagram only
since 2026-11-27: TikTok/YouTube stats moved to 2c because Cowork has no `POSTPROXY_API_KEY`.

```
You run the daily Metrics pull for DivvyUpp's Instagram Reels loop (@getdivvyupp). Make sure the GitHub repo DivvyUpp/divvyupp-media is available (attach it with push access if it is not, then clone it). Read runs/metrics.md and follow it exactly, EXCEPT step 3b (TikTok/YouTube via Postproxy), which a separate 06:05 run does: skip it and do not log its absence as a failure. Use the Windsor.ai for Social Media connector (connector instagram, account 17841422626862357). Data only: never post, publish or change anything outside the files runs/metrics.md names. If something blocks you, tell Srini exactly what and stop.
```

## 2c. TikTok + YouTube stats — every day, 06:05 America/New_York (Claude Code cloud, after the 05:53 pull)
Needs `POSTPROXY_API_KEY` and `api.postproxy.dev`; no connector. Repos: DivvyUpp/divvyupp-media (push).

```
You add TikTok and YouTube numbers to DivvyUpp's daily metrics. Make sure the GitHub repo DivvyUpp/divvyupp-media is available (attach it with push access if it is not, then clone it). Read runs/metrics.md, then run only step 3b: `python3 scripts/fetch_platform_stats.py` from the repo root (needs POSTPROXY_API_KEY, which this environment has). Data only: never post or change anything except the metrics/<today>.json file it writes and this run's runlog/<today>/metrics.json attempt. Commit and push to main (pull --rebase and push once more if rejected). If it fails, append a partial attempt with the error to runlog/<today>/metrics.json, push, and tell Srini.
```

## 3. Post (Claude Code cloud scheduled task "DivvyUpp Reels: post next approved Reel (Postproxy, all 3 platforms)") — three slots a day, 11:57, 16:57 and 21:57 America/New_York
Runs as a Claude Code cloud session (since 2026-11-27), NOT Cowork: it needs `POSTPROXY_API_KEY` and
`api.postproxy.dev`, and no connector (Instagram, TikTok and YouTube all post through Postproxy). The old Cowork
task "DivvyUpp Reels: post next approved Reel (3 slots a day)" is disabled.

```
You post DivvyUpp's next approved Reel to @getdivvyupp on Instagram, TikTok and YouTube Shorts (one Reel per slot; three slots a day). Make sure the GitHub repo DivvyUpp/divvyupp-media is available (attach it with push access if it is not, then clone it). Read PLAYBOOK.md, then runs/post.md, and follow them exactly; those files are the source of truth. All three platforms post through Postproxy with ONE command from the repo root: `python3 scripts/post_reel.py <entry id>` (needs POSTPROXY_API_KEY, which this environment has). Instagram posts first; TikTok and YouTube get that same Reel only once it is live on Instagram. No backfill or catch-up of older Reels on any platform. Only entries Srini explicitly approved (status "approved") may ever be published; never post anything else, never edit captions. Srini explicitly authorized these posts (2026-11-26, moved to Postproxy 2026-11-27). If publishing fails, do not retry and do not work around a refusal: log the run, push, and tell Srini exactly what failed. If nothing is approved, log it and finish quietly.
```

## 4. Blog (add to "DivvyUpp Blog: weekly SEO report & article management") — add this paragraph under HISTORY

```
HYPOTHESES: also read and update docs/seo/hypotheses.md on the outreach-log branch (create it if missing). For every article improvement you approve and every topic instruction or swap you make, add a card: date, url or topic, target query, bet ("if we change X, then impressions/position/clicks will move because Y"), prediction (a number), review date 4 weeks out. Each week, review the cards whose review date has passed: verdict supported / refuted / inconclusive (fewer than 50 impressions = inconclusive) and one line on why, and put the verdicts in the report.
```

## Leave as they are
- "DivvyUpp Reels: Sunday kickoff" and the Thursday mid-week check stay disabled.
