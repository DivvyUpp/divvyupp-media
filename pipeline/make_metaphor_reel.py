"""Render a wordless "money metaphor" Reel (15 s): no voice-over, a music bed, big on-screen words and one animated
picture that carries the whole idea. Built 2026-11-28 as an exploration-slot test of the mechanism Gump found in
@neuronvisuals' "INCOME / EXPENSES" (Instagram, 7.2M views): money comes in slowly and leaves fast, shown as motion,
no narration (research/2026-11-28-gump-eval.md). We copy the mechanism, not the video.

Story (illustrative numbers, labelled on screen):
  A (0-7.5 s)  One paycheck pours into a jar; spending leaks out faster and faster; empty by day 11 of 14.
  B (7.5-15 s) Same paycheck, saving first: a chunk moves to a savings jar on payday, the rest drains one even
               step a day and lasts to day 14.
Usage:  python3 pipeline/make_metaphor_reel.py [--at 1 4 9] -> reels/2026-11-28-paycheck-jar.mp4 (or stills)
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import make_diagram_reel as D                                                   # canvas, fonts, colours, easing
from make_diagram_reel import F, Canvas, clamp, ease, back, INK, ORANGE, GREY, WHITE, MUTED, TINT, RED
from music_upbeat import upbeat_bed

ID = "2026-11-28-paycheck-jar"; W, H, FPS, S = D.W, D.H, 30, D.S; DUR = 15.0
GREEN = (46, 139, 87)
PAY, SAVE, DAYS = 1400, 300, 14                                                  # after-bills paycheck, savings, days
JX, JY0, JY1, JW = 540, 620, 1180, 500                                           # main jar: centre x, top, bottom, width
SPENDS = [("coffee", 6), ("takeout", 38), ("online order", 27), ("groceries", 142), ("gas", 55),
          ("concert", 120), ("dinner out", 96), ("kids' gear", 85), ("streaming", 15), ("gift", 60)]


def jar(cv, x, y0, y1, w, level, col, label, k=1.0, label_col=INK):
    """A rounded container whose fill rises/falls with level (0..1), label above it."""
    cv.shadow([x - w / 2, y0, x + w / 2, y1], 40, k)
    cv.rect([x - w / 2, y0, x + w / 2, y1], 40, fill=WHITE, k=k)
    fy = y1 - (y1 - y0 - 16) * clamp(level)
    if level > 0.003 and fy < y1 - 10:
        cv.rect([x - w / 2 + 8, fy, x + w / 2 - 8, y1 - 8], min(32, (y1 - 8 - fy) / 2), fill=col, k=k)
        cv.rect([x - w / 2 + 8, fy, x + w / 2 - 8, min(y1 - 8, fy + 34)], 0, fill=col, k=k)
    cv.rect([x - w / 2, y0, x + w / 2, y1], 40, outline=INK, w=6, k=k)
    cv.text(x, y0 - 50, label, F("xb", 46), label_col, k)


def amount(cv, x, y, v):
    """The jar's balance on a dark pill, readable whatever the fill level behind it."""
    txt = f"${v:,.0f}"; f = F("xb", 84); w = cv.tl(txt, f) + 70
    cv.rect([x - w / 2, y - 62, x + w / 2, y + 62], 62, fill=INK, k=0.92); cv.text(x, y, txt, f, WHITE, 1)


def part_a(cv, t):
    """0-7.5 s: paycheck pours in, spending leaks out faster and faster."""
    # headline: two short lines that are the whole idea
    cv.text(540, 330, "Money in: once.", F("xb", 76), INK, 1)
    cv.text(540, 425, "Money out: all month.", F("xb", 76), ORANGE, clamp((t - 1.3) / 0.3))
    pour = ease(clamp((t - 0.35) / 0.6))                                         # paycheck lands 0.3-1.2 s
    # leak: accelerating, from 1.4 s, empty at 6.4 s (day 11)
    u = clamp((t - 1.4) / 5.0); spent = u ** 1.6
    level = 0.9 * pour * (1 - spent)
    day = 1 + int(round(10 * u)) if t >= 1.4 else 1
    jar(cv, JX, JY0, JY1, JW, level, ORANGE, f"Checking · day {min(day, 11)} of {DAYS}")
    if t < 1.3:                                                                 # the paycheck block drops in
        yb = JY0 + 90 + (JY1 - 160 - JY0 - 90) * ease(clamp((t - 0.15) / 0.7))
        kb = 1 - clamp((t - 0.9) / 0.2)
        cv.rect([JX - 215, yb - 62, JX + 215, yb + 62], 30, fill=GREEN, k=kb)
        cv.text(JX, yb, f"Paycheck +${PAY:,}", F("xb", 46), WHITE, kb)
    left = PAY * (1 - spent) if t >= 1.2 else PAY * pour
    if t >= 0.9: amount(cv, JX, (JY0 + JY1) / 2, left)
    # spending chips fly out of the jar's right side, faster and faster
    if t >= 1.4:
        n_out = len(SPENDS); times = [1.4 + 5.0 * ((i + 1) / (n_out + 1)) ** (1 / 1.6) for i in range(n_out)]
        for i, (name, amt) in enumerate(SPENDS):
            a = clamp((t - times[i]) / 0.9)
            if 0 < a < 1:                                                       # out through the bottom, left/right
                sd = -1 if i % 2 else 1; x = JX + sd * 330 * ease(a); y = JY1 + 20 + 190 * a
                kk = 1 - a ** 4
                cv.rect([x - 160, y - 42, x + 160, y + 42], 42, fill=ORANGE, k=kk)
                cv.text(x, y, f"{name} -${amt}", F("xb", 38), WHITE, kk)
    # day counter + the empty moment
    if t >= 6.4:
        e = ease(clamp((t - 6.4) / 0.4))
        cv.text(JX, JY1 + 300, "Empty. 3 days to payday.", F("xb", 54), RED, e)


def part_b(cv, t):
    """7.5-15 s: same paycheck, save first, then an even daily amount that lasts."""
    tb = t - 7.5
    cv.text(540, 330, "Same paycheck.", F("xb", 76), INK, clamp(tb / 0.25))
    cv.text(540, 425, "Save first.", F("xb", 76), GREEN, clamp((tb - 0.9) / 0.3))
    mx = JX + 130 * ease(clamp((tb - 0.9) / 0.5))                               # main jar slides right
    pour = ease(clamp((tb - 0.15) / 0.6))
    moved = ease(clamp((tb - 1.2) / 0.7))                                       # savings chunk moves 1.2-1.9 s
    sv_frac = SAVE / PAY
    u = clamp((tb - 2.2) / 4.4)                                                 # even drain, day 1 -> 14
    steps = math.floor(u * DAYS + 1e-6) / DAYS
    spend_left = (PAY - SAVE) * (1 - steps)
    level = 0.9 * pour * (1 - sv_frac * moved) * (1 - steps)
    day = 1 + int(steps * DAYS) if tb >= 2.2 else 1
    jar(cv, mx, JY0, JY1, JW - 80, level, ORANGE, f"Checking · day {min(day, DAYS)} of {DAYS}")
    sk = clamp((tb - 0.9) / 0.4)
    jar(cv, 190, JY0 + 220, JY1, 220, 0.9 * moved, GREEN, "Savings", k=sk, label_col=GREEN)
    if moved > 0: cv.text(190, (JY0 + 220 + JY1) / 2 + 20, f"${SAVE * moved:,.0f}", F("xb", 54), WHITE if moved > 0.6 else INK, sk)
    shown = PAY * pour if tb < 1.2 else PAY - SAVE * moved if tb < 2.2 else spend_left
    amount(cv, mx, (JY0 + JY1) / 2 + 40, shown)
    if tb >= 2.0:                                                               # the daily number
        dk = ease(clamp((tb - 2.0) / 0.4)); per = (PAY - SAVE) / DAYS
        cv.rect([mx - 230, JY0 + 30, mx + 230, JY0 + 120], 45, fill=INK, k=dk)
        cv.text(mx, JY0 + 75, f"${per:,.0f} a day is safe", F("xb", 42), WHITE, dk)
    if 2.2 <= tb < 6.6:                                                       # one even step out per day
        a = (u * DAYS) % 1.0
        if a < 0.8:
            y = JY1 + 20 + 150 * (a / 0.8); kk = 1 - (a / 0.8) ** 4
            cv.rect([mx - 120, y - 40, mx + 120, y + 40], 40, fill=ORANGE, k=kk)
            cv.text(mx, y, f"-${(PAY - SAVE) / DAYS:,.0f}", F("xb", 40), WHITE, kk)
    if tb >= 6.7:
        e = ease(clamp((tb - 6.7) / 0.4))
        cv.text(540, JY1 + 300, "Lasts to payday. Savings kept.", F("xb", 54), GREEN, e)


def frame(t):
    cv = Canvas()
    if t < 7.5: part_a(cv, t)
    else: part_b(cv, t)
    cv.text(540, 1590, "Illustrative numbers", F("m", 28), GREY, 1)
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
