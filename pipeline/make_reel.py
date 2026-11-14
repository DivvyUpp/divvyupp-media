"""Render a DivvyUpp Reel: a new opening hook + the approved body (save first, guarantee, call to action).

Usage:  python3 pipeline/make_reel.py hooks/<id>.json        -> reels/<id>.mp4
        python3 pipeline/make_reel.py hooks/<id>.json --check -> reels/<id>_check.jpg (one still, no render)

Hook spec (JSON):
{
  "id": "2026-11-17-a",
  "small": "You make good money.",                      # optional small line above the big lines
  "lines": [["So why is there", "ink"], ["nothing left", "ink"],
            ["at the end of", "orange"], ["the month?", "orange"]],   # 1-5 big lines, colour ink|orange
  "narration": ["You make good money.", "So why is there nothing left at the end of the month?"],
  "chart": true                                           # optional draining-balance chart under the text
}
Run pipeline/setup.sh once per machine first.
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); CACHE = os.path.join(HERE, ".cache")
W, H, FPS, S = 1080, 1920, 30, 2
FD = os.path.join(CACHE, "fonts/package/files/plus-jakarta-sans-latin-%s-normal.woff")
INK = (21, 16, 15); GREY = (95, 102, 114); ORANGE = (224, 74, 26); WHITE = (255, 255, 255); MUTED = (214, 206, 202)
COL = {"ink": INK, "orange": ORANGE}
LEAD, TAIL, VOICE = 0.45, 0.9, "af_heart"

_fc = {}
def font(w, s):
    k = (w, int(s))
    if k not in _fc: _fc[k] = ImageFont.truetype(FD % {"m": 500, "b": 700, "xb": 800}[w], int(s * S))
    return _fc[k]

def make_bg():
    bg = np.zeros((H, W, 3), dtype=np.float32); bg[:] = (255, 250, 247)
    glow = Image.new("L", (W, H), 0); g = ImageDraw.Draw(glow)
    g.ellipse([500, -400, 1500, 600], fill=255); g.ellipse([-500, 1450, 400, 2300], fill=170)
    glow = np.asarray(glow.filter(ImageFilter.GaussianBlur(200)), dtype=np.float32)[..., None] / 255 * 0.55
    bg = bg * (1 - glow) + np.array((255, 226, 212), dtype=np.float32) * glow
    return Image.fromarray(bg.astype("uint8")).resize((W * S, H * S), Image.BILINEAR).convert("RGBA")

def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def ease_io(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def appear(t, st, d=0.5): return ease((t - st) / d)

class Frame:
    def __init__(self, bg, t, total):
        self.bg = bg; self.layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0)); self.d = ImageDraw.Draw(self.layer)
        self.g = max(0.0, min(1.0, t / 0.35, (total - t) / 0.35))
    def a(self, k): return int(255 * max(0, min(1, k)) * self.g)
    def text(self, xy, s, f, col, k=1.0, anchor="la", dy=24):
        if k > 0: self.d.text((xy[0] * S, (xy[1] + (1 - k) * dy) * S), s, font=f, fill=col + (self.a(k),), anchor=anchor)
    def tl(self, s, f): return self.d.textlength(s, font=f) / S
    def rrect(self, b, r, col, k=1.0):
        if k > 0: self.d.rounded_rectangle([v * S for v in b], r * S, fill=col + (self.a(k),))
    def line(self, pts, col, w): self.d.line([(x * S, y * S) for x, y in pts], fill=col, width=int(w * S), joint="curve")
    def ellipse(self, b, col): self.d.ellipse([v * S for v in b], fill=col)
    def poly(self, pts, col): self.d.polygon([(x * S, y * S) for x, y in pts], fill=col)
    def img(self): return Image.alpha_composite(self.bg, self.layer).convert("RGB").reduce(S)

def logo(fr, cx, y, size, k):
    if k <= 0: return
    f = font("xb", size * 0.62); tw = fr.tl("DivvyUpp", f); gap = size * 0.28; x = cx - (size + gap + tw) / 2
    fr.rrect([x, y, x + size, y + size], size * 0.28, ORANGE, k)
    c = x + size / 2; sw = max(3, size * 0.1); top, bot = y + size * 0.27, y + size * 0.73; arm = size * 0.19; col = WHITE + (fr.a(k),)
    fr.line([(c, top), (c, bot)], col, sw); fr.line([(c - arm, top + arm), (c, top), (c + arm, top + arm)], col, sw)
    for px, py in [(c, bot), (c - arm, top + arm), (c + arm, top + arm), (c, top)]: fr.ellipse([px - sw / 2, py - sw / 2, px + sw / 2, py + sw / 2], col)
    fr.text((x + size + gap, y + size / 2), "DivvyUpp", f, INK, k, anchor="lm", dy=0)

rng = np.random.default_rng(7); _days = np.arange(31)
_bal = 6840 - (6840 - 37) * (_days / 30) ** 0.8 + np.r_[0, np.convolve(rng.normal(0, 160, 33), np.ones(5) / 5, "valid"), 0]
_bal[0], _bal[-1] = 6840, 37

def hook_scene(fr, t, spec, cues):
    logo(fr, W / 2, 150, 70, appear(t, 0.2))
    chart = spec.get("chart", True); lines = spec["lines"]
    y = 430 if chart else 820 - len(lines) * 60 - (80 if spec.get("small") else 0)
    if spec.get("small"):
        fr.text((W / 2, y), spec["small"], font("b", 66), INK, appear(t, cues[0]), anchor="ma"); y += 160
    big_start = (cues[1] if len(cues) > 1 else cues[0] + 0.4) if spec.get("small") else cues[0]
    size = min(104, min(960 / max(fr.tl(s, font("xb", 100)) / 100, 1) for s, _ in lines))
    for i, (s, c) in enumerate(lines):
        fr.text((W / 2, y + i * size * 1.13), s, font("xb", size), COL.get(c, INK), appear(t, big_start + i * 0.3), anchor="ma")
    if not chart: return
    k = appear(t, 0.5); p = ease_io((t - 0.6) / 3.6); gx0, gx1, gy0, gy1 = 120, W - 120, 1170, 1480
    if k <= 0: return
    fr.text((gx0, gy0 - 70), "CHECKING BALANCE", font("b", 26), GREY, k, dy=0)
    fr.line([(gx0, gy1), (gx1, gy1)], MUTED + (fr.a(k),), 2)
    fr.text((gx0, gy1 + 22), "Payday", font("b", 26), GREY, k, dy=0); fr.text((gx1, gy1 + 22), "Day 30", font("b", 26), GREY, k, anchor="ra", dy=0)
    n = p * 30; xs = np.linspace(0, n, max(2, int(n * 8) + 2)); ys = np.interp(xs, _days, _bal)
    pts = [(gx0 + (gx1 - gx0) * x / 30, gy1 - (gy1 - gy0) * v / 6840) for x, v in zip(xs, ys)]
    if p > 0:
        fr.poly(pts + [(pts[-1][0], gy1), (gx0, gy1)], ORANGE + (int(fr.a(k) * 0.10),)); fr.line(pts, ORANGE + (fr.a(k),), 6)
        ex, ey = pts[-1]; fr.ellipse([ex - 13, ey - 13, ex + 13, ey + 13], WHITE + (fr.a(k),)); fr.ellipse([ex - 9, ey - 9, ex + 9, ey + 9], ORANGE + (fr.a(k),))
        fr.text((gx1, gy0 - 88), f"${float(ys[-1]):,.0f}", font("xb", 60), ORANGE if p > 0.85 else INK, k, anchor="ra", dy=0)

def narrate(sentences, out_wav):
    import soundfile as sf
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(CACHE, "kokoro.onnx"), os.path.join(CACHE, "voices.bin"))
    parts, cues, t, sr = [], [], 0.0, 24000
    for i, s in enumerate(sentences):
        a, sr = k.create(s, voice=VOICE, speed=1.0, lang="en-us"); p = 0.35 if i < len(sentences) - 1 else 0.0
        cues.append(LEAD + t); parts += [a, np.zeros(int(sr * p))]; t += len(a) / sr + p
    sf.write(out_wav, np.concatenate(parts), sr); return t, cues, sr

def main():
    spec_path = sys.argv[1]; check = "--check" in sys.argv
    spec = json.load(open(spec_path)); rid = spec["id"]
    os.makedirs(os.path.join(ROOT, "reels"), exist_ok=True); tmp = os.path.join(CACHE, "tmp_" + rid); os.makedirs(tmp, exist_ok=True)
    dur, cues, sr = narrate(spec["narration"], os.path.join(tmp, "hook.wav"))
    total = LEAD + dur + TAIL; n = round(total * FPS); bg = make_bg()
    def draw(tt): fr = Frame(bg, tt, total); hook_scene(fr, tt, spec, cues); return fr.img()
    if check:
        draw(total - 1.0).save(os.path.join(ROOT, "reels", rid + "_check.jpg"), quality=85); print("check frame written"); return
    hv = os.path.join(tmp, "hook.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", hv], stdin=subprocess.PIPE)
    for f in range(n): p.stdin.write(draw(f / FPS).tobytes())
    p.stdin.close(); assert p.wait() == 0
    import soundfile as sf
    a, _ = sf.read(os.path.join(tmp, "hook.wav")); seg = np.zeros(int(round(n / FPS * sr))); s = int(LEAD * sr); seg[s:s + len(a)] = a[:len(seg) - s]
    body, bsr = sf.read(os.path.join(HERE, "assets", "body_audio.flac")); assert bsr == sr
    sf.write(os.path.join(tmp, "full.wav"), np.concatenate([seg * 0.95, body]), sr)
    open(os.path.join(tmp, "list.txt"), "w").write(f"file '{hv}'\nfile '{os.path.join(HERE, 'assets', 'body_video.mp4')}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"), "-c", "copy", os.path.join(tmp, "v.mp4")], check=True)
    out = os.path.join(ROOT, "reels", rid + ".mp4"); part = out + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(tmp, "v.mp4"), "-i", os.path.join(tmp, "full.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", part], check=True)
    os.replace(part, out); print("wrote", out)

if __name__ == "__main__": main()
