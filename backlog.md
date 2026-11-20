# Backlog: bets waiting to be tested

Ranked by score = impact (1–5, on the current bottleneck) × confidence (A=3, B=2, C=1) × ease (1–3). The Research run
adds and re-sorts; the Create run takes from the top. Current bottleneck: **3-second hold and reach** (see
`learnings.md`).

| # | Score | Bet | Variable | Metric and prediction | Source |
|---|---|---|---|---|---|
| 1 | 5×2×3=30 | **In test 2026-11-20 (hypotheses/2026-11-20.md).** Testing 3 hook variants of one script as Trial Reels gets more total non-follower views per day than one main post. | Distribution: 1 main + 2 trials vs 1 main | Total views per day ≥ 2× the main post's views | Windsor supports `trial_params`; Instagram shows trials to non-followers ([research/2026-11-20.md](research/2026-11-20.md)) |
| 2 | 5×1×3=15 | Opening on the payoff (the safe-to-spend number on screen in frame 1, e.g. "Balance $2,400. Safe to spend $310.") holds more viewers than opening on a pain question. | First 3 seconds only | Skip ≤ 75% vs control 2026-11-15-a (85.7%) | "Speed to value" topic from Chris Chung (title only, C); our skip data |
| 3 | 4×1×3=12 | A 35–45 s cut of the same story keeps more viewers to the end than the 60–90 s version, without losing clarity. | Length (same script, trimmed) | Avg watch ÷ length ≥ 1.5× control | Chris Chung "30–45 s is best" chapter title (C). Srini prefers clarity, so this needs his yes on the cut. |
| 4 | 4×1×2=8 | A story with a turn ("I had money in the bank. But rent hadn't cleared. So I overspent.") holds better than the step-by-step explainer. | Story shape | Avg watch +30% vs control | "Zigzag" storytelling topic, Chris Chung (C) |
| 5 | 3×1×2=6 | A format borrowed from another niche ("what I can spend in a day", after "what I eat in a day") earns more shares. | Format | Shares ≥ 3 on ≥ 300 views | "Borrow formats from other niches", Chris Chung (C) |
| 6 | 3×1×1=3 | A photoreal AI-video opening shot (e.g. a grocery checkout) holds better than the drawn presenter. | First shot visual | Skip ≤ 75% | Runway Gen-4.5 can make 9:16 clips ([research/2026-11-20.md](research/2026-11-20.md)). Needs Srini to sign up for Runway; label as AI on Instagram. |
| 7 | 4×2×3=24 | Text and presenter on screen from frame 1 (no blank fade-in) lowers skip rate. | First frame only | Skip ≤ main − 10 pts on 100+ views | Our template opens blank for ~0.7s (stills, 2026-11-20). In test as trial 2026-11-20-t1. |
| 8 | 4×1×3=12 | Proof-first opening: the surprising number is the first line ("You think it's eighty-six. It's two-nineteen.") instead of a claim or question. | Hook line + first stat line | Skip ≤ 75% | Cold review 2026-11-20 (C) |
| 9 | 3×1×2=6 | Moving the daily-number moment (a relatable spend, tomorrow adjusts) ahead of the four-numbers card keeps more viewers past 30s. | Scene order | Avg watch +30% vs control | Cold review 2026-11-20 called the four-numbers card "a wall of someone else's budget" (C) |
