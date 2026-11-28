# Research run (daily, 05:57 ET)

Your job is to look outward. Find better and better ways to make short-form content that works, and turn them into
bets the Create run can test. You feed the loop; you do not make or post videos.

Do not anchor on any one creator, framework or tool. A method earns its place in `learnings.md` only by winning in
our own data. Until then it is a candidate bet in `backlog.md`.

## Steps
1. Read `PLAYBOOK.md` (goal, loop, noise rules), `learnings.md`, `backlog.md`, the last 7 files in `research/`
   (so you don't repeat yourself), and the last 3 files in `hypotheses/` (what just won or lost).
2. **Pick today's question** from the current bottleneck. Work down the funnel: if 3-second hold is the problem,
   research openings; if people watch but don't visit, research calls to action and profile/bio; if they visit but
   don't sign up, flag it for Srini (landing page, not content). Write the question in one sentence.
3. **Search widely.** Rotate source types across the week so no single voice dominates:
   - platform guidance (Instagram @creators, Meta / Instagram help and blog posts on Reels ranking, Trial Reels);
   - creators who teach short-form (hooks, scripting, editing, formats) — any of them, not a fixed list;
   - formats working in other niches that could carry a personal-finance message;
   - finance creators' formats (study the format, never copy their content);
   - tools that open new formats (AI video such as Runway, AI voice, editing) — what they can do, cost, limits, terms;
   - data: studies or platform numbers on watch time, skip rate, shares;
   - **studies for Study Reels (Srini, 2026-11-24), every run:** pitch up to 5 new ideas into
     `research/study-bank.md` with status **pitched**. Each needs a primary source (journal paper, NBER/working
     paper, J-PAL/regulator report): who was studied and how many, what they did, the measured result worded no
     stronger than the source, the caveat (lab vs field, one company, observational), and one concrete move a viewer
     can copy today. Prefer surprising results with a fun or concrete move; skip advice everyone already knows.
     Ask Srini in the run's note to mark each "send" or "no"; when he answers in this chat, set the status to
     **approved** or **declined** and record his reason. Never mark anything approved yourself.
   - **Gump (Srini signed up 2026-11-28; MCP connector "Gump", if the routine has it):** its library of 50K+ view
     TikTok/Instagram videos. Free tools only unless Srini OKs spending: `search_library` / `top_hooks` /
     `analyze_niche` on the day's question, then `get_video_analysis` on up to 3 relevant outliers to fill the
     creative-teardown fields (hook said/on screen/visual, beats with timestamps, why it worked). Mark Gump's per-beat
     "intrigue" as a Gump estimate, never as retention data; it gives no creator baseline, so check the 3x-own-median
     bar separately. Analyses may come back in French: translate. If the Gump tools are missing, say so in the brief
     and carry on. Never use `adapt_script`, `analyze_account` or anything that spends credits or Super Searches.
     See `research/2026-11-28-gump-eval.md`.
   - **the audience's own words (Srini, 2026-11-23):** how people who earn well but have nothing to show for it
     describe that pain, in comments under finance Reels/Shorts and in public forums (e.g. Reddit personal-finance
     threads). Add phrases to `research/pain-language.md` (phrase, where, link, date, how many times seen).
     Never copy usernames or anything identifying; phrases only. A **pain moment** (a specific scene, e.g. checking
     the balance before payday) is tested against the same proof bar as a format before Create may build on it.
4. **Grade the evidence** for each finding: A = platform data or a controlled test with numbers; B = a creator's
   claim with their own numbers; C = opinion. Paraphrase in your own words; at most one short quote per source.
   **Proof bar for a format or tactic (set by Srini 2026-11-20): an idea is not a bet until it has data.** A format
   counts as proven when we can show **at least 3 unrelated accounts** posting it **in the last 90 days**, each post
   beating that account's own typical views by **3x or more** (compare against 5–10 of its recent posts; write the
   numbers down: post views, account median, ratio, date, link). Our own numbers count too: a Reel, TikTok or YouTube Short of
   Srini's with 100+ views on any one platform (read them from `combined` / `tiktok` / `youtube` in the latest
   `metrics/<date>.json`; name the platform with the number). An idea without this is listed under "Ideas needing proof", not ranked as a bet.
   `research/watchlist.csv` (readable version: `research/watchlist.md`, with the **entry bar** every account must meet)
   holds three lists (Srini, 2026-11-20): niche, fintech_brand and format_teacher. Add accounts only if they meet the
   bar, and log any you check and leave out. Vet with `python3 scripts/vet_channels.py --names ...` (search costs
   100 of the 10,000 daily API units; lookups by handle are nearly free). **niche**: personal-finance, household-money and
   fintech accounts, used for the passes below. **format_teacher**: people who test and teach what works on
   Instagram and short-form generally (Chris Chung, Instagram @creators and others). They keep us out of a
   finance-only silo: a format they teach or show working is a candidate idea, which then goes through the Kill pass
   (3+ accounts at 3x+, in any niche) before it's ranked. Their own claims are graded B or C, never A.
   Two passes every run, over the niche accounts in `research/watchlist.csv` (add relevant personal-finance, household
   money and fintech accounts as you find them; record each one's typical views and where the number came from):
   **Mine**: read the accounts' outlier posts, group them into formats, and keep formats with 3+ accounts at 3x+.
   **Kill**: test each unproven idea in `backlog.md` against the same data; fewer than 3 accounts means it stays
   "needs proof", and say whether that's because the format failed or because the data wasn't there.
   Proven = 3 accounts at 3x+ within 90 days on short-form; supported = 3 accounts at 3x+ within 12 months on any
   format (proposed tiers, 2026-11-20, pending Srini). Data sources: **YouTube Data API** (Srini chose it 2026-11-20) for each watchlist
   channel's Shorts (views, publish date), key from env `YOUTUBE_API_KEY`, never committed; run
   `python3 scripts/fetch_shorts.py` (writes `research/shorts-<date>.csv`: each Short's views, likes, channel median,
   multiple and outlier flag; fix any handle it reports as not found in `research/watchlist.csv`); host `www.googleapis.com`
   must be allowed. If the key or host is missing, say so in the brief and fall back to OutlierKit pages. Shorts are
   a proxy for Reels (audiences may differ), so Shorts-only evidence is graded B until one of our Reels confirms it.
   Prefer formats where the payoff is held until the end and differs by viewer (e.g. a number per age or income
   bracket), since they hold watch time and get sent to the friend it fits.
   **Exploration lane (Srini, 2026-11-28):** the proof bar decides what ranks as a *bet*; it does not stop one
   exploration Reel a day (PLAYBOOK "Exploration slot"). Each run may list up to 2 exploration ideas, marked
   "explore", each with the one thing it tests and why it might work. Never rank them above proven bets.
   **Creative teardown (2026-11-28), for 3 outliers and 2 ordinary posts from the same accounts where viewable:** the
   first frame (what is on screen), the first spoken line, seconds until the first reveal, what changes on screen,
   the narrative device (comparison, ranking, experiment, prediction, dialogue), likely recipient, and length. Write
   "not viewable" rather than guessing from the title. Copy the mechanism, never the creator's script or look.
5. **Write `research/<YYYY-MM-DD>.md`**: the question, 3–6 findings (each with link, grade, one line on how it
   applies to DivvyUpp), and what you could not access.
6. **Add 1–3 bets to `backlog.md`** in hypothesis-card shape (see `PLAYBOOK.md`), each citing today's brief. Score
   each: impact (1–5, on the current bottleneck) × confidence (A=3, B=2, C=1) × ease (1–3). Re-sort the backlog by
   score. Remove bets that `learnings.md` already settles. Keep the backlog at 25 items or fewer.
7. If a finding argues for changing the script checklist or the loop itself, add it under "Proposed changes" in
   the brief. Do not edit `PLAYBOOK.md` or `learnings.md` yourself.
8. Commit and push `research/` and `backlog.md` to main.
9. Write your run log record (`runlog/<today>/research.json`, see "Run log" in `PLAYBOOK.md`) and push it with the rest; write it even if you stop early.

## Never
- Never sign up for, buy, install or connect any tool. Propose it in the brief with cost and terms.
- Never post, message anyone, or contact a creator.
- Never present a C-grade claim as fact.
- Send Srini nothing unless you are blocked; the Create run carries a one-line summary of your brief.
