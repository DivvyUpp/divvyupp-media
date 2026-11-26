# Routine prompts for the daily loop

The scheduled routines were made in the Claude app, so they are changed there. Each prompt is short on purpose: the
logic lives in this repo, so changing the loop means editing `PLAYBOOK.md` and `runs/*.md`, not the routines.

## 1. Research (new routine) — every day, 05:57 America/New_York
Connectors: none beyond GitHub. Web search and fetch on.

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

## 2b. Metrics pull — every day, 05:53 America/New_York
Needs the Windsor.ai for Social Media connector (Instagram) and `POSTPROXY_API_KEY` with `api.postproxy.dev` allowed
(TikTok and YouTube, 2026-11-26). Repos: DivvyUpp/divvyupp-media (push).

```
You run the daily Metrics pull for DivvyUpp's Instagram Reels loop (@getdivvyupp). Make sure the GitHub repo DivvyUpp/divvyupp-media is available (attach it with push access if it is not, then clone it). Read runs/metrics.md and follow it exactly. Use the Windsor.ai for Social Media connector (connector instagram, account 17841422626862357) for Instagram, and scripts/fetch_platform_stats.py (Postproxy, needs POSTPROXY_API_KEY) for TikTok and YouTube. Data only: never post, publish or change anything outside the files runs/metrics.md names. If something blocks you, tell Srini exactly what and stop.
```

## 3. Post (replaces the prompt of "DivvyUpp Reels: post today's approved Reel") — three slots a day, 11:57, 16:57 and 21:57 America/New_York
Needs the Windsor.ai for Social Media connector (Instagram) AND `POSTPROXY_API_KEY` in its environment, with
`api.postproxy.dev` allowed (2026-11-26: TikTok and YouTube go through Postproxy with each Instagram post). Without
the key the run still posts Instagram and reports TikTok and YouTube as missing.

```
You post DivvyUpp's approved Reels for today to @getdivvyupp on Instagram, YouTube Shorts and TikTok. Make sure the GitHub repo DivvyUpp/divvyupp-media is available (attach it with push access if it is not, then clone it). Read PLAYBOOK.md, then runs/post.md, and follow them exactly. Use the Windsor.ai for Social Media connector (connector instagram, account 17841422626862357) for Instagram, and scripts/post_postproxy.py (Postproxy, needs POSTPROXY_API_KEY) for TikTok and YouTube, for the Reel just posted to Instagram only (no backfill). Only entries Srini explicitly approved (status "approved") may ever be posted; never post anything else, never edit captions. If publishing fails, do not retry blindly; tell Srini what failed.
```

## 4. Blog (add to "DivvyUpp Blog: weekly SEO report & article management") — add this paragraph under HISTORY

```
HYPOTHESES: also read and update docs/seo/hypotheses.md on the outreach-log branch (create it if missing). For every article improvement you approve and every topic instruction or swap you make, add a card: date, url or topic, target query, bet ("if we change X, then impressions/position/clicks will move because Y"), prediction (a number), review date 4 weeks out. Each week, review the cards whose review date has passed: verdict supported / refuted / inconclusive (fewer than 50 impressions = inconclusive) and one line on why, and put the verdicts in the report.
```

## Leave as they are
- "DivvyUpp Reels: Sunday kickoff" and the Thursday mid-week check stay disabled.
