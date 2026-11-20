"""Render a vertical split-screen comparison Reel: two people stacked (top half / bottom half), each standing on the
right of their half, with money blocks appearing to their left in sequence as the voice tells the story. One uncut
ElevenLabs take, light music, a centre band for the hook, and the agreed CTA at the end. No drawn presenter.

Usage:  python3 pipeline/make_split_reel.py hooks/<id>.json [--check]
Spec:
{ "id": "...", "character_voice": "elevenlabs:<voice>:eleven_v3", "music": true,
  "sentences": ["...", ...],                                   # the whole script, one take
  "band": {"lines": [["Same $10K a month.", "white"], ["Which one are you?", "orange"]], "until": 1},
  "halves": [ {"person": "path.png", "tint": [r,g,b], "tag": "Saves first", "tag_color": "green",
               "blocks": [{"label": "Income", "value": "$10,000", "at": 1, "style": "plain|good|bad|minus",
                           "delay": 0.0, "big": false}, ...],
               "badge": {"text": "$90,000 in 5 years", "color": "green", "at": 9}}, {...} ],
  "note": {"text": "3.8% = US average saving rate (BEA, Sept 2026)", "at": 7},
  "cta_at": 10 }
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from make_reel import W, H, FPS, S, CACHE, INK, GREY, ORANGE, WHITE, font, appear, Frame, logo, ease
from make_story_reel import LEAD, TAIL
from make_explainer import one_take
from make_beat_reel import v_cta, fit, mark, GREEN, RED

HALF = H // 2; BAND = 130
# Instagram Reels covered areas, measured on Srini's iPhone screenshot (2026-11-20, 1320x2868): the 9:16 video is
# scaled to fill the height, so ~55 px is cropped off each side; status bar/Reels header cover the top ~180 px;
# username + caption + "posts tagged" cover y>=1660 (full width); the like/comment/repost/send rail covers x>=905 from
# y~1150 down. All text and blocks stay inside; only background and the people run into covered areas.
SAFE_TOP, SAFE_BOT, SAFE_L, TEXT_R = 255, 1650, 80, 890     # top raised to 255 after the live post: the Reels/Friends header reached y~230
ZONES = [[0, 0, W, 240], [0, 1660, W, H], [905, 1150, W, 1660], [0, 0, 55, H], [W - 55, 0, W, H]]
MID = (SAFE_TOP + SAFE_BOT) // 2
COLS = {"green": GREEN, "red": RED, "orange": ORANGE, "white": WHITE, "ink": INK}

def bg_for(spec):
    bg = Image.new("RGBA", (W * S, H * S), (255, 250, 247, 255))
    for i, h in enumerate(spec["halves"]):
        tint = tuple(h.get("tint", (245, 240, 236)))
        y0, y1 = (0, MID) if i == 0 else (MID, H)
        bg.paste(Image.new("RGBA", (W * S, (y1 - y0) * S), tint + (255,)), (0, y0 * S))
    return bg

_P = {}
def person(path, height):
    k = (path, height)
    if k not in _P:
        im = Image.open(path if os.path.isabs(path) else os.path.join(ROOT, path)).convert("RGBA")
        bb = im.getbbox(); im = im.crop(bb) if bb else im
        _P[k] = im.resize((int(im.width * height / im.height), height), Image.LANCZOS)
    return _P[k]

import re as _re, math as _math
def _back(x):                          # ease-out-back: quick overshoot, then settle
    x = max(0.0, min(1.0, x)); c = 1.9; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

def _count(value, x):
    """Count a plain money value ("$1,500", "−$5,500") up from 0 while x goes 0..1; other text is returned as is."""
    m = _re.fullmatch(r"(−?\$)([\d,]+)", value)
    if not m or x >= 1: return value
    n = int(m.group(2).replace(",", "")); return f"{m.group(1)}{round(n * (1 - (1 - max(x, 0)) ** 3)):,}"

def pop_scale(age, big=False):
    """One smooth motion: grow from 88% to a small overshoot (6% on results, 3% otherwise) and settle by 0.45 s.
    No second pulse (two motions back to back read as a jitter)."""
    x = max(0.0, min(1.0, age / 0.45)); over = 0.06 if big else 0.03
    e = 1 - (1 - x) ** 3                               # ease-out position 0..1
    return 0.88 + 0.12 * e + over * _math.sin(_math.pi * e) * (1 - x)

_SPR = {}
def sprite(key, w, h, paint):
    """Draw something once at full size into its own transparent image (cached), so scaling it later is a smooth
    image resize instead of re-laying-out text at a new, rounded font size every frame (which jittered)."""
    if key not in _SPR:
        from PIL import ImageDraw
        sub = Frame.__new__(Frame); sub.layer = Image.new("RGBA", (int(w * S), int(h * S)), (0, 0, 0, 0))
        sub.d = ImageDraw.Draw(sub.layer); sub.g = 1.0; paint(sub); _SPR[key] = sub.layer
        if len(_SPR) > 400: _SPR.pop(next(iter(_SPR)))
    return _SPR[key]

def place(fr, img, cx, cy, sc, k):
    """Paste a sprite centred on (cx, cy) at scale sc and opacity k, with sub-pixel smooth resampling."""
    if k <= 0: return
    w, h = max(1, round(img.width * sc)), max(1, round(img.height * sc))
    im = img if (w, h) == img.size else img.resize((w, h), Image.BICUBIC)
    if k < 1: im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * k)))
    fr.layer.alpha_composite(im, (int(round(cx * S - w / 2)), int(round(cy * S - h / 2))))

def block(fr, x, y, w, h, b, k, age=9.0, pop=True):
    """k = opacity 0..1; age = seconds since the tile appeared (drives the pop and the count-up)."""
    if k <= 0: return
    val = _count(b["value"], (age - 0.05) / 0.6)
    st = b.get("style", "plain")
    def paint(f):
        fill = {"good": GREEN, "bad": RED}.get(st, WHITE)
        txt = WHITE if st in ("good", "bad") else INK
        f.rrect([0, 0, w, h], 24, fill, 1)
        lab_f = font("b", min(26, h * 0.25)); val_size = min(58, h * (0.40 if not b.get("big") else 0.46))
        f.text((22, h * 0.10), b["label"].upper(), lab_f, (WHITE if st in ("good", "bad") else GREY), 1, dy=0)
        vcol = txt if st != "minus" else RED
        f.text((22, h - h * 0.12), val, font("xb", fit(f, b["value"], "xb", val_size, w - 48)), vcol, 1, anchor="ld", dy=0)
        if b.get("mark"): mark(f, w - 40, h / 2, 22, b["mark"], 1)
        if b.get("sub"):
            scol = COLS.get(b.get("sub_color", "green"), GREEN)
            f.text((w - 22, h - 18), b["sub"], font("xb", fit(f, b["sub"], "xb", min(30, h * 0.3), w * 0.55)), scol, 1, anchor="rd", dy=0)
    img = sprite(("blk", round(w), round(h), b["label"], val, st, b.get("sub"), b.get("big")), w, h, paint)
    place(fr, img, x + w / 2, y + h / 2, pop_scale(age, b.get("big")) if pop else 1.0, k)

def tighten(audio, sr, ch, st, en, starts, max_gap=0.32, speed=1.0, keep_gap=None):
    """Shorten pauses between sentences to max_gap and speed the take up (pitch kept, ffmpeg atempo); the character
    timings are remapped so the visuals stay in sync. Returns audio, st, en."""
    cuts = []
    def spoken(j): return ch[j].isalnum()
    for k in range(1, len(starts)):
        a = max((en[j] for j in range(starts[k - 1], starts[k]) if spoken(j)), default=None)
        b = next((st[j] for j in range(starts[k], len(ch)) if spoken(j)), None)
        g = (keep_gap or {}).get(str(k), max_gap)          # a longer pause kept before sentence k, e.g. before the answer
        if a is not None and b is not None and b - a > g: cuts.append((a + g / 2, b - g / 2))
    def remap(t): return t - sum(min(max(t - c0, 0), c1 - c0) for c0, c1 in cuts)
    keep, prev = [], 0
    for c0, c1 in cuts: keep.append(audio[int(prev * sr):int(c0 * sr)]); prev = c1
    keep.append(audio[int(prev * sr):]); audio = np.concatenate(keep)
    st = [remap(t) for t in st]; en = [remap(t) for t in en]
    if speed != 1.0:
        import soundfile as sf, tempfile
        d = tempfile.mkdtemp(); a_, b_ = os.path.join(d, "a.wav"), os.path.join(d, "b.wav"); sf.write(a_, audio, sr)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a_, "-filter:a", f"atempo={speed}", b_], check=True)
        audio, _ = sf.read(b_); st = [t / speed for t in st]; en = [t / speed for t in en]
    return audio, st, en

def click(sr, gain=0.06):
    """A very soft, short 'tick' for a tile landing: a damped 1.6 kHz tone plus a tiny noise transient."""
    n = int(0.05 * sr); t = np.arange(n) / sr
    tone = np.sin(2 * np.pi * 1600 * t) * np.exp(-t / 0.012)
    noise = np.random.default_rng(3).normal(0, 1, n) * np.exp(-t / 0.003) * 0.3
    return (tone + noise) * gain

def main():
    import soundfile as sf
    spec = json.load(open(sys.argv[1])); rid = spec["id"]; check = "--check" in sys.argv
    tmp = os.path.join(CACHE, "tmp_" + rid); os.makedirs(tmp, exist_ok=True)
    spec["beats"] = [{"sentences": [{"text": s} for s in spec["sentences"]]}]
    sents, starts, (ch, st, en), audio, sr = one_take(spec, tmp)
    if spec.get("speed", 1.0) != 1.0 or spec.get("max_gap"):
        audio, st, en = tighten(audio, sr, ch, st, en, starts, spec.get("max_gap", 0.32), spec.get("speed", 1.0), spec.get("keep_gap"))
    def first_spoken(i):
        tag = False
        for j in range(i, len(ch)):
            if ch[j] == "[": tag = True
            elif ch[j] == "]": tag = False
            elif not tag and ch[j].isalnum(): return st[j]
        return st[-1]
    cues = [LEAD + first_spoken(i) for i in starts]
    total = LEAD + len(audio) / sr + TAIL; n = round(total * FPS)
    bg = bg_for(spec); cta_t = cues[spec["cta_at"]] - 0.2 if spec.get("cta_at") is not None else total + 1
    def cue(i, d=0.0, word=None):
        if word:                                   # time the given word is spoken inside sentence i
            text = "".join(ch); lo = starts[i]; hi = starts[i + 1] if i + 1 < len(starts) else len(ch)
            j = text.find(word, lo, hi)
            if j >= 0: return LEAD + st[j] - 0.12 + d
        return cues[min(i, len(cues) - 1)] - 0.12 + d
    def draw(f):
        t = f / FPS; fr = Frame(bg, t, total); fr.g = min(1.0, (total - t) / 0.35)
        if t >= cta_t:
            fr.bg = Image.new("RGBA", (W * S, H * S), (255, 250, 247, 255)); v_cta(fr, t - cta_t, {"lines": spec.get("cta_lines")}, [])
            return fr.img()
        def region(i): return (SAFE_TOP, MID - BAND // 2 - 14) if i == 0 else (MID + BAND // 2 + 30, SAFE_BOT - (62 if spec.get("note") else 0))
        def fit_h(i, h):
            r0, r1 = region(i); nb = len(h["blocks"]); nbig = sum(1 for b in h["blocks"] if b.get("big"))
            return (r1 - r0 - 72 - 8 * (nb - 1)) / (nb + 0.2 * nbig)
        bh_all = min([spec.get("block_h", 86)] + [fit_h(i, h) for i, h in enumerate(spec["halves"])])   # same tile size in both halves
        for i, h in enumerate(spec["halves"]):
            r0, r1 = (SAFE_TOP, MID - BAND // 2 - 14) if i == 0 else (MID + BAND // 2 + 30, SAFE_BOT - (62 if spec.get("note") else 0))
            # person on the right; may run into the covered areas (no text there)
            if i == 0: pb, ph = MID - BAND // 2, MID - BAND // 2 - SAFE_TOP - 80    # head starts below the tag/badge row
            else: pb, ph = H, min(790, H - (MID + BAND // 2) - 20)
            p = person(h["person"], int(ph * S * (1 + 0.03 * t / total)))
            fr.layer.alpha_composite(p, (max(W * S - p.width + int(40 * S), int(W * 0.46 * S)), pb * S - p.height))
            # tag + result badge on one row at the top of the safe region
            tf = font("xb", 30); tw = fr.tl(h["tag"], tf); col = COLS.get(h.get("tag_color", "ink"), INK)
            fr.rrect([SAFE_L, r0, SAFE_L + tw + 44, r0 + 58], 29, col, 1); fr.text((SAFE_L + 22, r0 + 29), h["tag"], tf, WHITE, 1, anchor="lm", dy=0)
            bd = h.get("badge")
            if bd:
                t_in = cue(bd["at"], bd.get("delay", 0.0), bd.get("word")); k = appear(t, t_in, 0.15); bx0 = SAFE_L + tw + 64
                bf = font("xb", fit(fr, bd["text"], "xb", 36, TEXT_R - bx0 - 40)); bwid = fr.tl(bd["text"], bf) + 40
                def paint_badge(f, bd=bd, bf=bf, bwid=bwid):
                    f.rrect([0, 0, bwid, 58], 29, WHITE, 1); f.text((bwid / 2, 29), bd["text"], bf, COLS.get(bd["color"], INK), 1, anchor="mm", dy=0)
                place(fr, sprite(("badge", bd["text"], round(bwid)), bwid, 58, paint_badge), bx0 + bwid / 2, r0 + 29, pop_scale(t - t_in, True), k)
            # blocks
            bx, bw = SAFE_L, spec.get("block_w", 470); top = r0 + 72; bottom = r1
            nb = len(h["blocks"]); gap = 8; nbig = sum(1 for b in h["blocks"] if b.get("big"))
            bh = bh_all
            yy = top
            for b in h["blocks"]:
                hh = bh * (1.2 if b.get("big") else 1.0)
                t_in = cue(b["at"], b.get("delay", 0.0))
                block(fr, bx, yy, bw, hh, b, appear(t, t_in, 0.15), t - t_in)
                yy += hh + gap
        # centre band (full width as a stripe; text inside the safe width)
        fr.rrect([0, MID - BAND // 2, W, MID + BAND // 2], 0, INK, 1)
        band = spec["band"]; lines = band["lines"] if t < cue(band.get("until", 99)) else band.get("after", band["lines"])
        size = min(fit(fr, s_, "xb", 52, TEXT_R - SAFE_L) for s_, _ in lines)
        yy = MID - (len(lines) * size * 1.12) / 2 + size * 0.05
        for s_, c in lines:
            fr.text((W / 2, yy), s_, font("xb", size), COLS.get(c, WHITE), 1, anchor="ma", dy=0); yy += size * 1.12
        nt = spec.get("note")
        if nt:
            from make_beat_reel import wrap
            for j, l in enumerate(wrap(fr, nt["text"], "b", 22, 500)[:2]):
                fr.text((SAFE_L, SAFE_BOT - 54 + j * 28), l, font("b", 22), INK, appear(t, cue(nt["at"])), dy=0)
        return fr.img()
    if check:
        for j, tt in enumerate([0.1] + [c + 1.0 for c in cues]):
            if tt < total and "--zones" in sys.argv:
                from PIL import ImageDraw
                im = draw(int(tt * FPS)).convert("RGBA"); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                for r in ZONES: d.rectangle(r, fill=(255, 0, 0, 80))
                Image.alpha_composite(im, ov).convert("RGB").save(os.path.join(ROOT, "reels", f"{rid}_zones_{j}.jpg"), quality=85)
            if tt < total: draw(int(tt * FPS)).save(os.path.join(ROOT, "reels", f"{rid}_check_{j}.jpg"), quality=85)
        print("check frames written"); return
    full = np.concatenate([np.zeros(int(LEAD * sr)), audio, np.zeros(int(TAIL * sr))]) * 0.95
    if spec.get("music", True):
        from music import mix_under
        full = mix_under(full, sr)
    if spec.get("clicks", True):
        tk = click(sr, spec.get("click_gain", 0.06))
        times = [cue(b["at"], b.get("delay", 0.0)) for h in spec["halves"] for b in h["blocks"]] + \
                [cue(h["badge"]["at"], h["badge"].get("delay", 0.0), h["badge"].get("word")) for h in spec["halves"] if h.get("badge")]
        for tt in times:
            i0 = int(max(tt, 0) * sr)
            if i0 < len(full): full[i0:i0 + len(tk)] += tk[:len(full) - i0]
    wav = os.path.join(tmp, "full.wav"); sf.write(wav, full, sr); vtmp = os.path.join(tmp, "v.mp4")
    pr = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", vtmp], stdin=subprocess.PIPE)
    for f in range(n): pr.stdin.write(draw(f).tobytes())
    pr.stdin.close(); assert pr.wait() == 0
    out = os.path.join(ROOT, "reels", rid + ".mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vtmp, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    print("wrote", out, f"{total:.1f}s")

if __name__ == "__main__": main()
