# DivvyUpp Reels loop: playbook for scheduled runs

This repo is the memory of the daily content loop. Scheduled Claude runs read this file first, then their own run file
in `runs/` (`runs/research.md`, `runs/create.md`, `runs/post.md`). If a routine's prompt and these files disagree,
these files win: the loop is changed by editing the repo, not the routine.
Videos are served publicly by GitHub Pages at `https://divvyupp.github.io/divvyupp-media/<path>`.

## Ground rules (never break these)
- **Nothing is posted to Instagram unless its queue entry has `"status": "approved"`**, set only after Srini
  watched the actual video and said yes in chat. Videos awaiting review are sent to him as files and are
  **not pushed to this public repo** until approved.
- Post only through the Windsor.ai for Social Media connector: connector `instagram`, account `17841422626862357`
  (@getdivvyupp), action `create_video_post`, `share_to_feed: true`.
- @getdivvyupp is the single main account for all DivvyUpp content (the personal @srinithinks account is retired).
- Cadence (Srini, 2026-11-20, rapid-test phase): **up to 3 Reels a day** (changed 2026-11-21 from 4), one per slot at about noon, 5pm and
  10pm ET, one Reel per proven format per day so every format gets a daily read. The Post run posts one approved Reel
  per slot, oldest first. Trial Reels stay off until 200 followers. If the scorecard shows extra posts hurting
  reach per Reel, propose cutting back. If anything fails, stop and tell Srini; do not retry a publish blindly (check with
  Windsor `get_data` for a media created today before any retry, so nothing posts twice). Trial Reels follow the same
  approval rule as any post: only entries Srini approved.
- Brand: warm off-white background, orange #E04A1A, near-black #15100F, Plus Jakarta Sans.
- Voice (agreed with Srini 2026-11-16): ElevenLabs, model `eleven_v3`, **Jessica** (`cgSgspJ2msm6clMCkdW9`) for presenter C,
  spec value `"character_voice": "elevenlabs:cgSgspJ2msm6clMCkdW9:eleven_v3"`. Direct the delivery with v3 audio tags
  ([playful], [sighs], [reassuring], [happy]...). Kokoro `af_heart` sounded flat and is retired for Reels.
  The API key comes from env `ELEVENLABS_API_KEY` (or `~/.secrets/elevenlabs_key`); never commit it. If the key is
  missing, ask Srini (SendUserMessage + PushNotification) to paste the key in the session, save it to
  `~/.secrets/elevenlabs_key` (chmod 600, outside the repo) and carry on. If `api.elevenlabs.io` is blocked, stop and
  tell Srini to add it under Settings → Capabilities → Allowed websites. Never fall back to Kokoro.
- **Free beta, no guarantee (Srini, 2026-11-23).** DivvyUpp is in free beta, so no caption, voiceover or on-screen text
  mentions the 90-day guarantee, refunds or a subscription. Caption line: "DivvyUpp is free while we're in beta. Get
  started at divvyupp.com". The old guarantee Reels (Nov 15-19) stay up as they are; their captions were changed in
  `queue.json` (old text kept as `caption_before_beta`) and Srini edits them by hand in Instagram.
- No competitor names, no maths equations on screen, no invented testimonials. The founder figure is
  "about $1,000 a month" saved; don't inflate it.

- **This repo is public** (GitHub Pages serves the videos Instagram posts from). Never commit personal data (names,
  emails, anyone's money details), keys or tokens. Business numbers, briefs and unposted Reels are visible to anyone
  who looks; Srini accepted that on 2026-11-21. Revisit going private when sign-up numbers become confidential or user
  data could land here; the videos would then need another public host.

## The offer and message (what every Reel sells)
Fixed bills stay fixed. What's left is flexible money. DivvyUpp has you save first (you choose the amount),
then gives a daily and weekly guide for the rest that adjusts when you overspend, before you spend, not after.
No budgeting homework: it sorts transactions into fixed or flexible automatically. Free while in beta (no guarantee
or refund talk until paid plans launch). Audience (Srini,
2026-11-23): defined by the **pain, not the demographic**: people who earn decently and have nothing to show for it,
who want to save more and know what they can safely spend. Single, coupled or raising kids, one income or two.
Srini is a dad and husband on one income; don't assume two incomes or marriage in scripts.

**Messaging rule (Srini, 2026-11-23).** Every Reel talks to **one person in one painful moment, in their own words**,
then follows the four-layer opening (script checklist item 11). *Which* moments, words and formats we use is decided
by research, not by a fixed list: a pain moment is used only when Research has shown it resonates (the proof bar in
`runs/research.md`, or our own data), and the viewer's words come from `research/pain-language.md`. Candidate
moments waiting for proof sit in `backlog.md` under "Pain moments needing proof".

**Instagram bio (Srini, 2026-11-23, set by Srini in the app):** "You make good money. So where does it all go? Save
first, then spend what's safe today, guilt-free. Built by one of you 👇" with divvyupp.com below it. The last line
of a Reel may echo its promise.

**End line = the landing page's promise (Srini, 2026-11-24).** Someone who taps through from a Reel should land on
the same promise they just heard. The site headline is "Know what you can safely spend — before you spend it." (with
"Save first. Then see exactly what's safe to spend, every day." under it), so a Reel's closing line or end card is
**"Know what's safe to spend — before you spend it."** "Save first" is the mechanism: say it inside the Reel, never
as the closing promise, and never in a way that implies DivvyUpp moves or holds money (it's read-only). Study Reels
have no product line at all; this applies to formats that end on DivvyUpp. If the site headline changes, change
this line to match.

## Story Reels and presenter characters (agreed with Srini 2026-11-15)
A story Reel tells the whole loop, not just a hook: pain → save first (approved body, part 1) → the daily/weekly
guide for the rest that adjusts when you overspend → payoff (bills paid, savings kept, guilt-free spending) →
guarantee + CTA (body, part 2). Render with `python3 pipeline/make_story_reel.py hooks/<id>.json` (spec format in
that file; `--check` writes one still per scene). Keep it under 90s (Srini prefers clarity over a 60s cap).
Current template (approved 2026-11-16), copy `hooks/2026-11-19-a.json`:
- hook → **four-numbers `plan` scene** (income and fixed bills checked against bank history, savings you pick,
  safe-to-spend; replaces the old "flips the order" body section, `skip_flip: true`) → guide with **two `spends`**
  → payoff → `"ending": "rendered"` (guarantee + CTA in the same voice, new guarantee wording; the CTA line is
  "Know what's safe to spend, before you spend it. Try it at Divvyup dot com." (changed 2026-11-24 to match the site headline) (in voice scripts always write the name "Divvyup": the voice spells out "divvyupp" as U-P-P; Srini chose this spelling 2026-11-20. On screen the brand is "DivvyUpp" and the web address is all lowercase, "divvyupp.com" (Srini, 2026-11-20).), which Srini prefers to the bare URL).
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
  spending habits, never at the viewer; he still lets you enjoy things. Lock his voice with `"voice_prefix"`: the take opens with the reference demo's first lines ("Whoa, whoa, whoa. I've seen your bank history! ... On a TUESDAY? ... I know exactly where money disappears to."), which are then cut off, so v3 settles into the approved character (Srini confirmed 2026-11-19 this matches; picking takes by pitch alone did not). Reference audio: `pipeline/assets/voices/raccoon_reference.wav`. Approved take for new Reels: the `hooks/2026-11-21-rules-v6.json` take (Srini, 2026-11-20). Reuse approved takes whenever the lines are unchanged; for new lines, render 3-4 takes and let Srini pick by ear. The automatic closest-to-reference score once picked a take he called 'British and slow', so never rely on it alone. Never clone a library voice. Keep his scripts ~20% shorter than the human
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

## The goal: paying subscribers (agreed with Srini 2026-11-20)
Views and followers are a means to an end. They show the content resonates and fill the top of the funnel. The real
goal is people who go to divvyupp.com and sign up: **free beta users now, paying subscribers later**.

| Layer | What we count | Where it comes from |
|---|---|---|
| Goal (now) | Free beta sign-ups, then bank linked (active household) | funnel export: `signed_up`, `bank_linked` |
| Goal (later) | Paying subscribers | funnel export, once billing is live |
| Bridge | Instagram visits to divvyupp.com, Get started clicks | funnel export: `instagram.days[]` |
| Top of funnel | Views per Reel, 3-second hold, watch time, shares, saves, followers | Windsor |

Engagement milestones (agreed 2026-11-20): **200 followers (current) → first Reel past 1,000 views → 1,000 views every
Reel and one past 10,000 → 100,000 followers.** Every hypothesis card names which layer it moves. A bet that wins views
but sends no one to the site is only half a win: say so in the postmortem.

### Current milestone: 200 followers (set by Srini 2026-11-20)
Why 200: it is the reported Trial Reels minimum for a professional account (research/2026-11-20.md), and followers
mean strangers liked enough to come back. We get there through the three signals Instagram names for Reels (Adam
Mosseri, Jan 2025): **watch time, likes per reach, sends per reach** (sends count most with non-followers).
Every bet names which of the three it is built to move.

**Primary metric: sends per 1,000 reached (Srini, 2026-11-24).** Adam Mosseri (Silicon Valley Girl podcast, Nov
2026): "Sends per impression, definitely. That's a huge one for unconnected reach": of every 1,000 people who saw
the Reel, how many sent it to a friend. Watch time and like rate matter more for followers; views are "a relatively
shallow measure". Almost everyone who sees our Reels is a non-follower, so every postmortem, scorecard and dashboard
leads with sends per 1,000 reached. Views are context only. Scorecard per Reel at 72h, from Windsor, in this order:

| Signal | Windsor field(s) | Read as |
|---|---|---|
| **Sends (primary)** | `media_shares` ÷ `media_reach` × 1000 | **sends per 1,000 reached** (Windsor's `shares`; Instagram counts DM sends here) |
| Watch time | `media_reel_avg_watch_time` (ms), skip rate | avg watch ÷ video length, and skip % |
| Likes | `media_like_count` ÷ `media_reach` | likes per 100 reached |
| Saves | `media_saved` ÷ `media_reach` × 1000 | saves per 1,000 reached |
| Follows | `followers_count`, read daily into `followers.csv` | change per day; per-Reel follows aren't reported |

Compare each Reel with our own median, never outside benchmarks; under 100 reached the read is inconclusive.
"Some posts are built to hold your followers, some are built to be forwarded. They look different" (Marina
Mogilko): until ~1,000 followers, every Reel is built to be forwarded (see "Send Reel format").

### Srini judges send-worthiness (Srini, 2026-11-24)
**No idea becomes a Send Reel unless Srini has said he would send it.** Research pitches ideas; Srini marks each
"send" or "no"; Create builds only "send" ideas, from `research/study-bank.md` (status **approved**). His first
verdicts: surprising, data-backed, with a fun or concrete move = send; generic advice everyone knows, or a fact with
no clear "so what do I do", = no. Hot takes without a study behind them didn't pass.

### Study Reel format (the default Send Reel; Srini, 2026-11-24)
A real study, its real number, and a move you can copy, the way evidence-based fitness channels cite papers.
20–40 s:
1. **The hook is the move plus the result** ("Naming your savings goal raised savings 16%. 'Remember to save'
   did nothing."). Never a bare instruction without the payoff.
2. **The study:** who was studied, how many, what they did. Researcher names and journal on screen.
3. **The result:** the exact number from the bank, worded no stronger than the source, with its caveat said plainly
   ("in a lab study", "at one company").
4. **The move:** the one concrete thing to do today, from the bank.
5. **Send prompt** naming who to send it to, on screen at the payoff and as the last line. No product pitch.

### Send Reel format (default until ~1,000 followers; Srini, 2026-11-24)
The only job of a Send Reel is to make a viewer think of one specific person and send it to them. Why people pass
things on (Jonah Berger's research, *Contagious*): it makes the sharer look smart or caring (social currency), it's
useful (practical value), and it sparks a high-arousal feeling such as surprise or amused outrage, not sadness.
Shape, 20–35 s:
1. **Call-out (0–2 s):** a specific behaviour, in the viewer's own words, that they recognise in themselves or in
   someone they'd send it to ("'I'll save whatever's left.' Nothing is ever left.").
2. **Contrarian truth (2–8 s):** the non-obvious claim that flips what they believe. It must be true, come from
   `research/study-bank.md` with status **approved** (Srini said he'd send it); never invent a fact or a number.
3. **Proof (8–20 s):** one concrete thing they can check: a cited study, an official statistic, or simple math shown
   on screen.
4. **The fix (20–28 s):** one practical line they can do today.
5. **Send prompt:** on screen at the moment of recognition AND as the last line, naming the recipient ("Send this
   to the friend who always says 'I deserve it'"). No "follow for more".
6. **No product pitch inside the video.** People don't send ads. DivvyUpp lives in the logo, the caption and the bio.
Send gate (all must be yes, or rewrite): Who exactly would you send this to, and why? Does sending it make the
sender look smart or caring rather than mean? Is there one surprising, verified claim? One fix? Under 35 s?
Call-outs punch at the habit, never at a group of people or their income, and never shame the viewer.

## The daily loop (replaces the weekly batch, agreed 2026-11-20)
Scheduled runs (times changed 2026-11-21 so Create's Reels are ready when Srini wakes up): Each reads this file, then its own run file.

| Time (ET) | Run | File | Job |
|---|---|---|---|
| Sun 05:00 | Watchlist | `runs/watchlist.md` | Re-check every watchlist account against the entry bar; find and add new ones. Done before Sunday's Research. |
| Mon 05:37 | Weekly funnel (GitHub Action) | `.github/workflows/funnel-weekly.yml` | Last Mon–Sun funnel to `funnel/<year>-W<week>.json`, for Monday's weekly review and the blog report. |
| 05:53 | Metrics pull | `runs/metrics.md` | Pull Instagram numbers with Windsor into `metrics/<date>.json`, `experiment-log.csv` and `followers.csv`. Data only. |
| 05:57 | Research | `runs/research.md` | Look outward. Find better ways to make content that works, from any creator, tool or format. Feed `backlog.md`. Not tied to any one framework. |
| 06:27 | Create | `runs/create.md` | Postmortem on recent Reels → update `learnings.md` → pick bets → workshop the scripts → render → send to Srini. On Mondays it starts with the weekly review. |
| 11:57, 16:57, 21:57 | Post | `runs/post.md` | Post one approved Reel per slot, oldest first. |

Srini approves each day's videos in chat, ideally by 11:30am ET (he reviews from about 9am). No approval, no post.

### Files that hold the loop's memory
- `learnings.md`: the rulebook. Each rule cites the Reels that support it. Rules can be overturned by new data.
- `backlog.md`: ranked bets waiting to be tested. Research adds to it; Create takes from the top.
- `research/<date>.md`: each day's research brief, with sources.
- `hypotheses/<date>.md`: each day's hypothesis card, script workshop and later its postmortem.
- `experiment-log.csv`: one row per posted Reel (main or trial), with the bet, prediction and verdict.
- `metrics/<date>.json`: each morning's Windsor pull (written by the Metrics pull run, read by Create).
- `funnel/`: weekly exports (Monday) plus one-day exports `funnel/custom-<d>_<d>.json` the Create run requests.

### Hypothesis card (one per main Reel; trial variants share the card)
```
Goal layer:    top of funnel | bridge | sign-ups   (and which milestone)
Bet:           If we <change>, then <metric> will <move>, because <reason>.
Evidence:      our data (Reel ids) or an outside source (link) for the reason
Variable:      the ONE thing changed
Control:       the Reel id it is compared with (the current best on that metric)
Prediction:    a number, e.g. "3-second hold >= 30% (skip <= 70%) at 72h"
If it wins:    what we do next
If it loses:   what we do next
```

### Noise rules
- Fewer than 100 views at the 72h read: **inconclusive**. Log it, change no rule.
- One variable per main Reel. If two things changed, the verdict is inconclusive.
- A rule enters `learnings.md` after two supporting Reels, and leaves it after two contradicting ones.
- Attribution to the site is by day, not by Reel (older Reels also drive visits). Say so when reading sign-ups.
- Windsor limits: per-Reel follows and profile visits are not reported for Reels; daily new-follower counts need 100+
  followers. Record `followers_count` every day instead and read the change.

### Script checklist (owned by the loop, not fixed)
Start from this list. Research may propose changes; Create applies a change only when `learnings.md` supports it.
1. The first frame and first line deliver the point or the tension. No warm-up.
2. A stranger knows who it is for within 2 seconds.
3. On-screen text matches the spoken hook in second one.
4. The story turns at least once ("but", "so"); it is not a flat list.
5. Length fits the bet. Srini's standing preference is clarity over a hard 60s cap, with 90s as the ceiling;
   a shorter cut is a bet to test, not a rule, until `learnings.md` says otherwise.
6. Read aloud, it has rhythm. Stress words are marked for the voice.
7. It does not repeat the previous 5 Reels' example, numbers or payoff.
8. Every figure is real and checked. Guarantee wording as agreed. No competitor names.
10. **Instagram safe zone (Srini, 2026-11-20).** Measured on Srini's iPhone (2026-11-20): no text, number or block in
   the top 255 px (raised after the first live post: the Reels/Friends header reaches ~230 px), the bottom 260 px (from y=1660), the right rail (x>=905 from y=1150 down), or 55 px at each side (cropped
   on tall phones). Backgrounds and people may run
   there. Check with `make_split_reel.py --check --zones` (red = covered) before sending a Reel for review.
11. **Four-layer opening gate (Srini, 2026-11-23; from @hilzuckerman, see `research/2026-11-23-hook-layers.md`).**
   Within the first ~6 seconds the script must pass all four, or it doesn't render:
   1. **One person, their problem in their words** ("Went in for milk, came out with $140?").
   2. **The stakes:** what it's costing them ("That's how the month runs out by the 20th").
   3. **Something new:** a reframe that makes them question what they believe ("It's not willpower: your balance is lying").
   4. **A clear promise:** exactly what they'll get by staying ("Three rules fix it").
   Mark each layer's line in the script. Until backlog #28 has a verdict, one Reel a day may use our usual one-line
   hook as the control; all others must pass the gate.
9. **Hook and payoff (Srini, 2026-11-20).** Write down four things before the script: the hook (0–2 s, one specific
   question, same words on screen and in the voice), what the viewer stays for (that question in one line), a
   rehook at about 40% using a retention device (result first; not A or B but C; common belief then contradict
   it; "but here's the better way"; "but this won't work unless"),
   and the payoff in the last 5–8 s that answers exactly the hook's question. No bait. Srini's calls on hooks
   (2026-11-20; taste and two-reviewer tests, not yet our data): a contrast beats a plain moment (same income, very
   different savings); give income per month; never give the answer away in the hook; skip topics few people care
   about or that need explaining. The reviewers stopped for a moment they're in (a balance on a date) or something
   they can check tonight, and scrolled past big totals, "the average couple" and teasers that hide what "this" is. The cold review must say what
   question it was waiting on and whether the payoff answered it.

### Trial Reels
Windsor `create_video_post` takes `trial_params: {"graduation_strategy": "MANUAL"}` (or `"SS_PERFORMANCE"`, which
shares it with followers automatically if it performs well). Trial Reels go to non-followers only. Use them to test
2–3 hook variants of the day's script at once. Default to `MANUAL`; Srini decides whether a winner goes to followers.
Queue entries for trials have `"kind": "trial"`; the main Reel has `"kind": "main"` (missing `kind` means main).
Not yet verified end to end: the first trial post must be checked in the Instagram app (it should not appear on the
grid) and reported to Srini.

### Blog loop
The blog stays weekly because search moves in weeks. Each article or improvement the blog run approves gets a short
card in `docs/seo/hypotheses.md` on the outreach-log branch of DivvyUpp/divvyupp: target query, bet, prediction,
review date 4 weeks out. The weekly blog run reviews the cards that are due.

## Run log (the dashboard reads it; added 2026-11-21)
Every run writes one record so Srini can see the whole day on one page:
https://divvyupp.github.io/divvyupp-media/dashboard/ (pick a date). The page only reads `runlog/`.

- File: `runlog/<YYYY-MM-DD>/<run>.json`, with today's ET date and `<run>` one of `metrics`, `research`, `create`,
  `post`, `watchlist`, `funnel`. One file per run per day; a second run the same day (a re-run, or the next Post
  slot) **appends** to `attempts`, never rewrites earlier attempts.
- Shape:
  ```json
  {"run": "research", "date": "2026-11-21", "attempts": [{
    "started_at": "2026-11-21T05:57:10-05:00", "finished_at": "2026-11-21T06:03:40-05:00",
    "status": "ok", "trigger": "scheduled",
    "summary": "One or two plain sentences: what this run did and what it found.",
    "blocker": "Only when status is blocked or failed: what stopped it and what would fix it.",
    "outputs": [{"label": "Research brief", "path": "research/2026-11-21.md"}],
    "reels": [{"id": "2026-11-21-a", "hook": "First line of the hook", "status": "pending_review",
               "file": "reels/2026-11-21-a.mp4", "permalink": "https://www.instagram.com/reel/..."}]
  }]}
  ```
  `status`: `ok`, `partial` (finished with a gap, e.g. a fallback data source), `blocked` (stopped and waiting on
  Srini), `failed` (an error). `trigger`: `scheduled` or `manual`. Times are ET with offset. `outputs` are repo
  paths. `reels` only for Create (every Reel sent for review, updated to `approved`/`rejected` when Srini answers)
  and Post (what posted, with `permalink`). `file` only once the video is in the repo. Leave out fields that don't
  apply. Never put personal data, keys or tokens in a record.
- Pushing: push to main. If the session only lets you push to your own `claude/...` branch, push there: the
  "Merge run branches into main" GitHub Action merges any branch with a `runlog/` record into main within a minute
  (it stops on a conflict, which then needs merging by hand). Don't open a pull request for run work.
- Write the record as the last step, commit it with the run's other files and push. **Write it even when blocked
  or failed**, then push it on its own. If the push itself fails, say so to Srini: the dashboard will show the run as
  "no record".

## How-it-works explainer (landing page)
`python3 pipeline/make_explainer.py hooks/how-it-works-raccoon.json` renders the 1080p landscape explainer: Dollar Bill
on the left, app screens redrawn in the current brand (`pipeline/screens.py`, never the old blue screens) in a phone on
the right, captions, one uncut voice take. Approved 2026-11-19: `reels/how-it-works-dollar-bill.mp4`. No founder name;
CTA is the free beta ("go to divvyupp dot com and tap Get Started, free during the beta, no card required").
