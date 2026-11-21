# "Same account" — production script (draft for Srini's approval, 2026-11-21)

Couple Reel, male point of view, comedic and affectionate. About 33 s, 9:16. Realistic people (Runway), the same
couple in every shot: `pipeline/assets/characters/couple/him.png`, `her.png`. All numbers, phone screens and text
cards are drawn by our renderer on top of the footage (AI-made screens have garbled text).
Label: small "Dramatization" note on screen for the first 3 s. Female version: same shots with the roles swapped,
made only if this one gets approved.

**Bet:** a funny, self-aware "same account, different number" couple story told by him, with real-looking people and a
Paris payoff, gets shares (send it to your partner) where the drawn 70 s couple Reel would not.
**Prediction at 72 h:** views >= 100, shares >= 2, skip <= 60%, average watch >= 40% of length.

## Scene by scene

| # | Time | Shot (what we see) | Camera | Voice (him, warm and wry) | On-screen text and graphics | Sound |
|---|---|---|---|---|---|---|
| 1 | 0.0–5.0 | HOOK. Split screen. Left: him at the kitchen island glancing at his phone, small proud smile (clip A). Right: her in the kitchen, coffee in hand, beaming (still, slow push-in). | Left: slow push-in on him. Right: slow push-in on her. | "Same bank account. You see eighty-four dollars safe to spend today. She sees four thousand. Sound familiar?" | Frame 1, top: **You see $84. She sees $4,212.** Phone cards over each side: left green **Safe to spend today $84**, right **Balance $4,212**. Small: Dramatization. | Upbeat light music starts on frame 1. Soft "ding" when the cards land. |
| 2 | 5.0–9.5 | Late evening, couch. He secretly browses his phone, glances sideways to check she isn't looking, grins (clip B). | Over-the-shoulder, then cut to his face. | "I'm planning a surprise. Paris. Two tickets, eighteen hundred bucks." | Phone overlay: **Paris · 2 tickets · $1,840**. Bar appears: **Paris fund $0 / $3,000**. | Light whoosh on the bar. |
| 3 | 9.5–13.5 | Boutique. She holds a sundress against herself in a mirror, does a little spin, delighted (clip C). Quick cut: at a checkout she taps her card and gives the cashier a happy little wave (clip D). | Handheld, playful. Cut on the spin. | "Meanwhile, she is living her best life. A dress. Candles. Brunch." | Chips stack on each word: **−$89 dress**, **−$42 candles**, **−$64 brunch**. | Three "cha-ching" ticks on the chips. |
| 4 | 13.5–18.5 | Calendar flips 1 → 28 over the kitchen; the Paris fund bar climbs to $600, then drains to $0 on the 28th. Cut to him looking into the camera: loving, defeated, a tiny head tilt and smile (clip E). | Graphic, then static close-up. | "We still save. But the extra that should've been Paris? Gone by the twenty-eighth." | **Paris fund $600 → $0** (red on the 28th). Calendar date in big type. | Music dips on "Gone". Comic record-scratch-lite. |
| 5 | 18.5–26.0 | Couch, daytime. He shows her his phone; she leans in, reads, nods, laughs and bumps his shoulder (clip F). | Medium two-shot, slow push-in. | "So I stopped showing her the balance. Savings leaves on payday. Bills are already counted. And she gets one number: what's safe to spend today." | Cards appear one per sentence: **1 Savings leaves on payday** → **2 Bills already counted** → **3 Safe to spend today: $84**. | Music lifts back up. |
| 6 | 26.0–30.5 | Paris café terrace, morning, Eiffel Tower soft in the background. They laugh over coffee; she raises her cup. Then she sneaks a glance at her phone and smirks (clip G). | Wide, then push-in on her smirk. | "Two months later? Paris. She still checks the number." (beat) "…Mostly." | Bar fills: **Paris fund $3,000 ✓**. | Accordion-ish flourish on "Paris". Beat of silence before "Mostly". |
| 7 | 30.5–33.5 | End card over a blurred café frame. | Static. | (none) | **Send this to the one who only checks the balance.** / **Save first. Then spend what's safe.** / **divvyupp.com** | Music button ending. |

Voice total: about 95 words, roughly 33 s at a lively pace.

## How it gets made (and what it costs)

1. **Storyboard stills first** (about 20 credits each, 7 stills, about 140 credits): one still per clip, made from the two
   portraits so the faces match. Srini approves or changes each still before any video is made.
2. **Animate the approved stills** into 5 s clips (about 80 credits each at 720p, 7 clips, about 550 credits). Scene 1's
   right side and scene 4's calendar are drawn, not generated.
3. **Voice** with ElevenLabs (already set up; no Runway credits), or Srini records it.
4. **Render** with `pipeline/make_beat_reel.py` (clip beats for footage, our overlays for every number).

Total about 700 credits of 2,095. Each step stops for Srini's yes before spending more.

## Caption (draft)
Same account. Two very different numbers. 😅
He's watching what's safe to spend. She's watching the balance. Paris is watching both of them.
Save first. Then spend what's safe.
Example couple, dramatized.
Try DivvyUpp for 90 days. If you don't save more or spend less, we refund your subscription, up to $30. Terms apply.
Link in bio → divvyupp.com
#couplesmoney #personalfinance #savingmoney #moneytips #budgeting
