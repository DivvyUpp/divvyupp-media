"""Render a wordless "money metaphor" Reel (15 s): no voice-over, a music bed, big on-screen words and one animated
picture that carries the whole idea. Built 2026-11-28 as an exploration-slot test of the mechanism Gump found in
@neuronvisuals' "INCOME / EXPENSES" (Instagram, 7.2M views): money comes in slowly and leaves fast, shown as motion,
no narration (research/2026-11-28-gump-eval.md). We copy the mechanism, not the video.

Story (illustrative numbers, labelled on screen; a household earning well, paid every 2 weeks):
  A (0-7.5 s)  What's left of one paycheck after bills pours into checking; spending leaks out like water, faster and
               faster; empty on day 11 of the 14 days to the next payday.
  B (7.5-15 s) Same paycheck, saving first: a chunk visibly leaves checking for savings on payday, the rest drains
               one even step a day and lasts to payday.
Usage:  python3 pipeline/make_metaphor_reel.py [--at 1 4 9] -> reels/2026-11-28-paycheck-jar.mp4 (or stills)
v2 2026-11-28 (Srini's notes): highlighted headline words, bigger spend labels, a water stream, "days to payday"
spelled out, the savings transfer shown as money leaving checking, household-sized amounts.
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import make_diagram_reel as D                                                   # canvas, fonts, colours, easing
from make_diagram_reel import F, Canvas, clamp, ease, back, INK, ORANGE, GREY, WHITE, RED
from music_upbeat import upbeat_bed

ID = "2026-11-28-paycheck-jar"; W, H, FPS = D.W, D.H, 30; DUR = 15.0
GREEN = (46, 139, 87); WATER = (232, 96, 48)
PAY, SAVE, DAYS = 2400, 500, 14                     # one paycheck after fixed bills, savings, days to the next payday
PER_DAY = (PAY - SAVE) / DAYS                        # ~ $136
JX, JY0, JY1, JW = 540, 660, 1150, 500               # main jar: centre x, top, bottom, width
SPOUT_Y = JY1 + 6
SPENDS = [("takeout", 64), ("groceries", 210), ("online order", 89), ("kids' soccer", 120), ("gas", 70),
          ("dinner out", 140), ("home stuff", 95), ("birthday gift", 60), ("streaming", 23)]


def headline(cv, t, line1, hl1, line2, hl2, col1, col2):
    """Two lines; the key words (hl1, hl2) sit on a colour pill that pops in, so the eye lands on them.
    A line whose colour is None is plain text (no pill)."""
    for i, (pre, hl, col, ts, y) in enumerate(((line1, hl1, col1, 0.0, 330), (line2, hl2, col2, 1.0, 430))):
        k = clamp((t - ts) / 0.2) if i else 1.0
        if k <= 0: continue
        f = F("xb", 74); gap = 34
        if col is None:
            cv.text(540, y, f"{pre} {hl}", f, INK, k); continue
        wp, wh = cv.tl(pre, f), cv.tl(hl, f); x0 = 540 - (wp + gap + wh) / 2; hx = x0 + wp + gap + wh / 2
        cv.text(x0, y, pre, f, INK, k, anchor="lm")
        u = clamp((t - ts - 0.15) / 0.35); sc = back(u) if u > 0 else 0
        if sc > 0: cv.rect([hx - (wh / 2 + 16) * sc, y - 50, hx + (wh / 2 + 16) * sc, y + 50], 26, fill=col, k=k)
        cv.text(hx, y, hl, f, WHITE if u > 0.3 else INK, k)


def day_pill(cv, x, day, k=1.0):
    left = DAYS - day
    txt = f"Day {day} of {DAYS}  ·  payday in {left} day{'s' if left != 1 else ''}" if left else "Day 14  ·  payday tomorrow"
    f = F("b", 36); w = cv.tl(txt, f) + 60
    cv.rect([x - w / 2, 525 - 32, x + w / 2, 525 + 32], 32, fill=WHITE, outline=(226, 219, 211), w=3, k=k)
    cv.text(x, 525, txt, f, GREY, k)


def jar(cv, x, y0, y1, w, level, col, label, k=1.0, label_col=INK, spout=False):
    cv.shadow([x - w / 2, y0, x + w / 2, y1], 40, k)
    cv.rect([x - w / 2, y0, x + w / 2, y1], 40, fill=WHITE, k=k)
    fy = y1 - (y1 - y0 - 16) * clamp(level)
    if level > 0.003 and fy < y1 - 10:
        cv.rect([x - w / 2 + 8, fy, x + w / 2 - 8, y1 - 8], min(32, (y1 - 8 - fy) / 2), fill=col, k=k)
        cv.rect([x - w / 2 + 8, fy, x + w / 2 - 8, min(y1 - 8, fy + 34)], 0, fill=col, k=k)
    cv.rect([x - w / 2, y0, x + w / 2, y1], 40, outline=INK, w=6, k=k)
    if spout: cv.rect([x - 22, y1 - 4, x + 22, y1 + 14], 6, fill=INK, k=k)
    cv.text(x, y0 - 40, label, F("xb", 44), label_col, k)


def amount(cv, x, y, v, k=1.0):
    txt = f"${v:,.0f}"; f = F("xb", 84); w = cv.tl(txt, f) + 70
    cv.rect([x - w / 2, y - 62, x + w / 2, y + 62], 62, fill=INK, k=0.92 * k); cv.text(x, y, txt, f, WHITE, k)


def stream(cv, x, t, rate):
    """Water drops falling from the spout; rate 0..1 sets how many and how fast."""
    if rate <= 0: return
    n = int(6 + 26 * rate)
    for j in range(n):
        ph = (t * (1.2 + 2.2 * rate) + j / n) % 1.0
        dx = math.sin(j * 12.9898) * 14 * ph; y = SPOUT_Y + 12 + 230 * ph ** 1.6
        r = (7 + 6 * rate) * (1 - 0.35 * ph); cv.circle(x + dx, y, r, fill=WATER, k=0.9 * (1 - ph ** 3))
    sp = 30 + 120 * rate                                                        # puddle at the bottom
    cv.rect([x - sp, SPOUT_Y + 236, x + sp, SPOUT_Y + 252], 8, fill=WATER, k=0.35 + 0.4 * rate)


def chip(cv, x, y, txt, k, col=ORANGE):
    if k <= 0: return
    f = F("xb", 46); w = cv.tl(txt, f) + 64
    cv.rect([x - w / 2, y - 46, x + w / 2, y + 46], 46, fill=col, k=k); cv.text(x, y, txt, f, WHITE, k)


def part_a(cv, t):
    headline(cv, t, "Money in:", "once.", "Money out:", "all month.", GREEN, ORANGE)
    pour = ease(clamp((t - 0.35) / 0.6))
    u = clamp((t - 1.5) / 4.9); spent = u ** 1.6                                # leak 1.5 -> 6.4 s, accelerating
    level = 0.9 * pour * (1 - spent)
    day = 1 + int(10 * u) if t >= 1.5 else 1
    day_pill(cv, JX, min(day, 11))
    jar(cv, JX, JY0, JY1, JW, level, ORANGE, "Checking", spout=True)
    if t < 1.1:                                                                 # the paycheck block drops in
        yb = JY0 + 90 + (JY1 - 160 - JY0 - 90) * ease(clamp((t - 0.15) / 0.7)); kb = 1 - clamp((t - 0.9) / 0.2)
        cv.rect([JX - 225, yb - 66, JX + 225, yb + 66], 30, fill=GREEN, k=kb)
        cv.text(JX, yb - 18, f"Paycheck +${PAY:,}", F("xb", 44), WHITE, kb)
        cv.text(JX, yb + 26, "(left after bills)", F("b", 28), WHITE, kb)
    if t >= 0.9: amount(cv, JX, (JY0 + JY1) / 2, PAY * (1 - spent))
    if 1.5 <= t < 6.5: stream(cv, JX, t, 0.25 + 0.75 * u)
    if t >= 1.5:                                                                # one big, readable spend at a time
        n = len(SPENDS); times = [1.5 + 4.9 * ((i + 0.5) / n) ** (1 / 1.6) for i in range(n)]
        for i, (name, amt) in enumerate(SPENDS):
            life = 0.75 if i < 4 else 0.55; a = (t - times[i]) / life
            if 0 <= a < 1:
                sd = -1 if i % 2 else 1
                chip(cv, JX + sd * 255, JY1 + 70 + 70 * a, f"{name}  -${amt}", clamp(a / 0.15) * (1 - clamp((a - 0.75) / 0.25)))
    if t >= 6.4:
        e = ease(clamp((t - 6.4) / 0.35)); cv.text(JX, JY1 + 330, "Empty, 3 days before payday.", F("xb", 54), RED, e)


def part_b(cv, t):
    tb = t - 7.5
    headline(cv, tb, "Same", "paycheck.", "Save", "first.", None, GREEN)
    mx = JX + 130 * ease(clamp((tb - 0.6) / 0.4)); SX, SW, SY0 = 185, 220, JY0 + 190
    pour = ease(clamp((tb - 0.1) / 0.5))
    lift = ease(clamp((tb - 1.0) / 0.3))                                        # $500 leaves checking 1.0-1.3 s
    fly = clamp((tb - 1.2) / 0.8)                                               # ...flies to savings 1.2-2.0 s
    land = ease(clamp((tb - 1.95) / 0.35))
    u = clamp((tb - 2.6) / 4.2); steps = math.floor(u * DAYS + 1e-6) / DAYS     # even drain 2.6 -> 6.8 s
    checking = PAY * pour - SAVE * lift
    if tb >= 2.6: checking = (PAY - SAVE) * (1 - steps)
    level = 0.9 * checking / PAY
    day = 1 + int(steps * DAYS) if tb >= 2.6 else 1
    day_pill(cv, mx, min(day, DAYS))
    jar(cv, mx, JY0, JY1, JW - 80, level, ORANGE, "Checking", spout=True)
    sk = clamp((tb - 0.6) / 0.3)
    jar(cv, SX, SY0, JY1, SW, 0.9 * land, GREEN, "Savings", k=sk, label_col=GREEN)
    if land > 0: cv.text(SX, (SY0 + JY1) / 2 + 30, f"${SAVE * land:,.0f}", F("xb", 54), WHITE, sk * land)
    if 1.0 <= tb < 2.1:                                                          # the $500 block leaves checking
        p0 = (mx, JY0 + 60); p1 = (SX, SY0 + 60); fe = ease(fly)
        bx = p0[0] + (p1[0] - p0[0]) * fe; by = p0[1] + (p1[1] - p0[1]) * fe - 190 * math.sin(math.pi * fe)
        kb = clamp((tb - 1.0) / 0.15) * (1 - clamp((tb - 1.95) / 0.15))
        cv.rect([bx - 190, by - 52, bx + 190, by + 52], 30, fill=GREEN, k=kb)
        cv.text(bx, by, f"-${SAVE} to savings", F("xb", 38), WHITE, kb)
    amount(cv, mx, (JY0 + JY1) / 2 + 40, checking)
    if tb >= 2.3:
        dk = ease(clamp((tb - 2.3) / 0.35)); txt = f"${PER_DAY:,.0f} a day is safe"; f = F("xb", 42); w = cv.tl(txt, f) + 60
        cv.rect([mx - w / 2, JY0 + 30, mx + w / 2, JY0 + 118], 44, fill=INK, k=dk); cv.text(mx, JY0 + 74, txt, f, WHITE, dk)
    if 2.6 <= tb < 6.8:                                                         # a calm, even trickle: one step a day
        stream(cv, mx, t, 0.18)
        a = (u * DAYS) % 1.0
        chip(cv, mx - 255, JY1 + 80 + 40 * a, f"-${PER_DAY:,.0f}", clamp(a / 0.12) * (1 - clamp((a - 0.65) / 0.2)))
    if tb >= 6.8:
        e = ease(clamp((tb - 6.8) / 0.35)); cv.text(540, JY1 + 330, "Lasts to payday. Savings kept.", F("xb", 54), GREEN, e)


def frame(t):
    cv = Canvas()
    if t < 7.5: part_a(cv, t)
    else: part_b(cv, t)
    cv.text(540, 1600, "Illustrative numbers · paid every 2 weeks", F("m", 28), GREY, 1)
    return cv.im.resize((W, H), Image.LANCZOS)


def main():
    D.BG["im"] = D.warm_bg()
    out = os.path.join(ROOT, "reels", f"{ID}.mp4")
    if "--at" in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index("--at") + 1:]]
        ims = [frame(t).resize((W // 2, H // 2)) for t in ts]
        sheet = Image.new("RGB", (W // 2 * len(ims), H // 2), WHITE)
        for i, im in enumerate(ims): sheet.paste(im, (i * W // 2, 0))
        p = os.path.join(ROOT, "reels", f"{ID}_at.jpg"); sheet.save(p, quality=88); print(p); return
    import soundfile as sf
    sr = 24000; wav = os.path.join(ROOT, "reels", f"{ID}.wav"); sf.write(wav, upbeat_bed(DUR, sr), sr)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", out], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)): ff.stdin.write(np.asarray(frame(i / FPS)).tobytes())
    ff.stdin.close(); ff.wait(); os.remove(wav); print(out)


if __name__ == "__main__":
    main()
