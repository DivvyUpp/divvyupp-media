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
- Cadence (Srini, 2026-11-20, rapid-test phase): **up to 4 Reels a day**, one per slot at about 8am, noon, 5pm and
  7pm ET, one Reel per proven format per day so every format gets a daily read. The Post run posts one approved Reel
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
Every bet names which of the three it is built to move. Scorecard per Reel at 72h, from Windsor:

| Signal | Windsor field(s) | Read as |
|---|---|---|
| Watch time | `media_reel_avg_watch_time` (ms), skip rate | avg watch ÷ video length, and skip % |
| Likes | `media_like_count` ÷ `media_reach` | likes per 100 reached |
| Sends | `media_shares` ÷ `media_reach` | shares per 100 reached (Instagram counts DM sends here) |
| Follows | `followers_count`, read daily into `followers.csv` | change per day; per-Reel follows aren't reported |

Compare each Reel with our own median, never outside benchmarks; under 100 views the read is inconclusive.

## The daily loop (replaces the weekly batch, agreed 2026-11-20)
Three scheduled runs a day. Each reads this file, then its own run file.

| Time (ET) | Run | File | Job |
|---|---|---|---|
| 07:00 | Research | `runs/research.md` | Look outward. Find better ways to make content that works, from any creator, tool or format. Feed `backlog.md`. Not tied to any one framework. |
| 09:00 | Create | `runs/create.md` | Postmortem on recent Reels → update `learnings.md` → pick one bet → workshop the script → render → send to Srini. On Mondays it starts with the weekly review. |
| 08:00, 12:00, 17:00, 19:00 | Post | `runs/post.md` | Post one approved Reel per slot, oldest first. |
| Sun 05:30 | Watchlist | `runs/watchlist.md` | Re-check every watchlist account against the entry bar; find and add new ones. |

Srini approves each day's videos in chat, ideally by 5pm ET. No approval, no post.

### Files that hold the loop's memory
- `learnings.md`: the rulebook. Each rule cites the Reels that support it. Rules can be overturned by new data.
- `backlog.md`: ranked bets waiting to be tested. Research adds to it; Create takes from the top.
- `research/<date>.md`: each day's research brief, with sources.
- `hypotheses/<date>.md`: each day's hypothesis card, script workshop and later its postmortem.
- `experiment-log.csv`: one row per posted Reel (main or trial), with the bet, prediction and verdict.
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
9. **Hook and payoff (Srini, 2026-11-20).** Write down four things before the script: the hook (0–2 s, one specific
   question, same words on screen and in the voice), what the viewer stays for (that question in one line), a
   rehook at about 40% using one of the retention devices in `research/reel-ideas-2026-11-20.md` (result first;
   not A or B but C; common belief then contradict it; "but here's the better way"; "but this won't work unless"),
   and the payoff in the last 5–8 s that answers exactly the hook's question. No bait. The cold review must say what
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

## How-it-works explainer (landing page)
`python3 pipeline/make_explainer.py hooks/how-it-works-raccoon.json` renders the 1080p landscape explainer: Dollar Bill
on the left, app screens redrawn in the current brand (`pipeline/screens.py`, never the old blue screens) in a phone on
the right, captions, one uncut voice take. Approved 2026-11-19: `reels/how-it-works-dollar-bill.mp4`. No founder name;
CTA is the free beta ("go to divvyupp dot com and tap Get Started, free during the beta, no card required").
