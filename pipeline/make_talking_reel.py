"""Render a talking-head Reel from one real clip: jump-cut to the kept segments (fillers and pauses removed), the
person's own voice, word-timed captions from a speech-to-text transcript, and a "reveal" table under the video whose
values are hidden behind bars that slide away on the exact word each value is spoken.

Usage:  python3 pipeline/make_talking_reel.py hooks/<id>.json           -> reels/<id>.mp4
        python3 pipeline/make_talking_reel.py hooks/<id>.json --check   -> reels/<id>_check_<n>.jpg

Spec:
{ "id": "...", "source": "pipeline/assets/scenes/<x>/raw.mov", "transcript": ".../transcript.json" (ElevenLabs STT),
  "segments": [[start, end], ...]  (source seconds, kept in order; each segment alternates a slight punch-in),
  "panel": {"top": 0, "height": 1120, "focus_y": 0.42}   (video panel; focus_y = where the face sits in the source),
  "hook": {"text": "...", "until": 3.0}, "nametag": {"text": "...", "until": 3.0},
  "table": {"title": "...", "source": "...", "rows": [{"label": "30", "value": "$100K", "word_at": 14.86}, ...]},
  "music": "pipeline/assets/music/....mp3", "music_gain": 0.2, "duck": 0.35,
  "end": {...same as make_scene_reel...} }
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import make_scene_reel as M
from make_scene_reel import W, H, FPS, SR, font, ease, fit, layer, paste, draw_hook, draw_end, INK, GREY, ORANGE, WHITE, GREEN, CREAM

FILLERS = {"um", "uh", "um,", "uh,", "uh.", "um."}

def rel(p): return p if os.path.isabs(p) else os.path.join(ROOT, p)

def timeline(spec):
    """Output time <-> source time over the kept segments."""
    segs, t = [], 0.0
    for sg in spec["segments"]:
        a, b = sg[0], sg[1]; sp = sg[2] if len(sg) > 2 else 1.0
        segs.append((t, t + (b - a) / sp, a, b, sp)); t += (b - a) / sp
    return segs, t

def src_to_out(segs, s):
    for o0, o1, a, b, sp in segs:
        if a <= s <= b: return o0 + (s - a) / sp
    return None

def load_frames(spec):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", rel(spec["source"]), "-an", "-vf",
                          f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)

def captions(spec, segs):
    tr = json.load(open(rel(spec["transcript"]))); out = []
    for w in tr["words"]:
        if w["type"] != "word" or w["text"].lower().strip() in FILLERS: continue
        s = src_to_out(segs, w["start"]); e = src_to_out(segs, w["end"])
        if s is None: continue
        seg = next(i for i, g in enumerate(segs) if g[2] <= w["start"] <= g[3])
        out.append((spec.get("replace", {}).get(w["text"], w["text"]), s, e if e is not None else s + 0.3, seg))
    return out

def draw_caption(img, caps, t, y):
    cur = [i for i, c in enumerate(caps) if c[1] - 0.05 <= t <= c[2] + 0.3]
    if not cur: return
    i = cur[-1]; lid = caps[i][3]; first = min(j for j, c in enumerate(caps) if c[3] == lid)
    start = first + ((i - first) // 4) * 4; grp = [c for c in caps[start:start + 4] if c[3] == lid]
    d = ImageDraw.Draw(img); size = 64; words = [c[0] for c in grp]
    while size > 40 and font("xb", size).getlength(" ".join(words)) > 860: size -= 2
    x = W / 2 - font("xb", size).getlength(" ".join(words)) / 2
    for w, s, e, _ in grp:
        col = (255, 214, 64) if s - 0.05 <= t <= e + 0.05 else WHITE
        d.text((x, y), w, font=font("xb", size), fill=col, stroke_width=7, stroke_fill=INK)
        x += font("xb", size).getlength(w + " ")

def draw_logo_icon(d, x, y, size, a=255):
    """DivvyUpp mark: orange rounded square with the white branching arrow (same geometry as make_reel.logo)."""
    d.rounded_rectangle([x, y, x + size, y + size], size * 0.28, fill=ORANGE + (a,))
    c = x + size / 2; sw = max(3, int(size * 0.1)); top, bot = y + size * 0.27, y + size * 0.73; arm = size * 0.19
    col = WHITE + (a,)
    d.line([(c, top), (c, bot)], fill=col, width=sw); d.line([(c - arm, top + arm), (c, top), (c + arm, top + arm)], fill=col, width=sw, joint="curve")
    for px, py in [(c, bot), (c - arm, top + arm), (c + arm, top + arm), (c, top)]:
        d.ellipse([px - sw / 2, py - sw / 2, px + sw / 2, py + sw / 2], fill=col)

def draw_nametag(img, nt, t):
    """Pill, top right: [logo] DivvyUpp | Srini · Founder. Pops in with a small scale bounce."""
    k = ease((t - nt.get("from", 0)) / 0.3)
    if k <= 0: return
    pop = 1 + 0.12 * math.sin(min(1.0, (t - nt.get("from", 0)) / 0.35) * math.pi)       # quick overshoot
    lay = Image.new("RGBA", (900, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    fb, fw = font("xb", 34), font("b", 32); ic = 46; x = 22
    brand = "DivvyUpp"; who = nt.get("text", "Srini · Founder")
    wb, ww = fb.getlength(brand), fw.getlength(who); total = 22 + ic + 12 + wb + 22 + 2 + 22 + ww + 26
    d.rounded_rectangle([0, 20, total, 20 + 74], 37, fill=(255, 255, 255, 240))
    draw_logo_icon(d, x, 20 + 14, ic); x += ic + 12
    d.text((x, 57), brand, font=fb, fill=INK, anchor="lm"); x += wb + 22
    d.line([(x, 38), (x, 76)], fill=(215, 208, 200), width=2); x += 24
    d.text((x, 57), who, font=fw, fill=GREY, anchor="lm")
    lay = lay.crop((0, 0, int(total) + 2, 120))
    if pop != 1: lay = lay.resize((int(lay.width * pop), int(lay.height * pop)), Image.BICUBIC)
    a = np.array(lay); a[..., 3] = (a[..., 3] * k).astype(np.uint8); lay = Image.fromarray(a)
    x1 = W - 46; yy = nt.get("y", 270)
    img.alpha_composite(lay, (int(x1 - lay.width), int(yy - (lay.height - 120) / 2)))

def draw_table(img, tb, t, y0, hook=None):
    """Title slot shows the hook (bigger, in orange) while it's live, then the table title."""
    d = ImageDraw.Draw(img); x0, x1 = 90, W - 90
    if hook and t < hook.get("until", 3.0):
        lines = hook["text"].split("\n")
        for i, ln in enumerate(lines):
            d.text((W / 2, y0 - 6 + 52 * i), ln, font=font("xb", fit(ln, "xb", 50, 900)), fill=ORANGE, anchor="ma")
    else:
        d.text((W / 2, y0 + 20), tb["title"], font=font("xb", 46), fill=INK, anchor="ma")
    rows = tb["rows"]; rh = 76; y = y0 + 104
    for r in rows:
        d.rounded_rectangle([x0, y, x1, y + rh - 12], 20, fill=(255, 255, 255))
        d.text((x0 + 36, y + (rh - 12) / 2), r["label"], font=font("xb", 42), fill=INK, anchor="lm")
        vx0, vx1 = x0 + 300, x1 - 24
        d.text(((vx0 + vx1) / 2, y + (rh - 12) / 2), r["value"], font=font("xb", 46), fill=GREEN, anchor="mm")
        k = ease((t - r["_out"]) / 0.4) if r.get("_out") is not None else 0.0   # bar slides right and away
        if k < 1:
            bx0 = vx0 + (vx1 - vx0) * k                                  # cover shrinks to the right, inside the row
            if vx1 - bx0 > 6: d.rounded_rectangle([bx0, y + 8, vx1, y + rh - 20], 14, fill=ORANGE)
            if k == 0: d.text(((vx0 + vx1) / 2, y + (rh - 12) / 2), "?", font=font("xb", 40), fill=WHITE, anchor="mm")
        y += rh
    if tb.get("source"): d.text((W / 2, y + 8), tb["source"], font=font("m", 30), fill=GREY, anchor="ma")

def frame_at(spec, frames, segs, caps, total, t):
    end = spec.get("end"); body = segs[-1][1]
    if t >= body and end:
        last = Image.fromarray(frames[min(int(segs[-1][3] * FPS), len(frames) - 1)]).convert("RGBA")
        from PIL import ImageFilter
        img = last.filter(ImageFilter.GaussianBlur(12)); draw_end(img, end, ease((t - body) / 0.4)); return img
    si = next(i for i, g in enumerate(segs) if g[0] <= t < g[1] or i == len(segs) - 1)
    o0, o1, a, b, sp = segs[si]; s = a + (t - o0) * sp
    src = Image.fromarray(frames[min(int(s * FPS), len(frames) - 1)])
    pn = spec["panel"]; ph = pn["height"]; z = 1.0 if si % 2 == 0 else pn.get("punch", 1.07)
    zo = pn.get("zoom_out", 1.0)                       # >1 shows more of the frame; sides filled with a blurred copy
    ch = min(H, ph * zo) / z; cw = W / z; cy = H * pn.get("focus_y", 0.42)
    y0 = min(max(0, cy - ch / 2), H - ch); x0 = (W - cw) / 2
    pw = int(round(cw * ph / ch)) if zo > 1 else W
    fg = src.resize((pw, ph), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    if pw < W:
        from PIL import ImageFilter
        bg = src.resize((W, ph), Image.BILINEAR, box=(0, max(0, cy - ph / 2), W, max(0, cy - ph / 2) + ph)).filter(ImageFilter.GaussianBlur(28))
        bg = Image.blend(bg, Image.new("RGB", bg.size, (20, 16, 15)), 0.25); bg.paste(fg, ((W - pw) // 2, 0)); panel = bg
    else: panel = fg
    img = Image.new("RGBA", (W, H), CREAM + (255,)); img.paste(panel, (0, pn.get("top", 0)))
    g = np.zeros((ph, 1), np.float32); g[ph - 260:, 0] = np.linspace(0, 0.55, 260); g[:420, 0] = np.linspace(0.45, 0, 420)
    a_ = np.zeros((ph, W, 4), np.uint8); a_[..., 3] = (np.repeat(g, W, 1) * 255).astype(np.uint8)
    img.alpha_composite(Image.fromarray(a_), (0, pn.get("top", 0)))
    hk = spec.get("hook")
    draw_table(img, spec["table"], t, pn.get("top", 0) + ph + 30, hk if spec.get("hook_in_table", True) else None)
    if hk and not spec.get("hook_in_table", True) and t < hk.get("until", 3.0): draw_hook(img, hk["text"])
    nt = spec.get("nametag")
    if nt and nt.get("from", 0) <= t < nt.get("until", 3.0): draw_nametag(img, nt, t)
    draw_caption(img, caps, t, pn.get("top", 0) + ph - pn.get("caption_up", 110))
    return img

def whoosh(fx):
    """Airy sweep: noise through a moving low-pass, rising then falling, peaking at fx['peak'] of its length."""
    dur = fx.get("dur", 1.0); n = int(dur * SR); rng = np.random.default_rng(11); x = rng.normal(0, 1, n)
    tt = np.arange(n) / n; pk = fx.get("peak", 0.7)
    cut = 300 + 5200 * np.where(tt < pk, tt / pk, 1 - (tt - pk) / (1 - pk)) ** 1.5
    y = np.empty(n); acc = 0.0
    for i in range(n):
        a = math.exp(-2 * math.pi * cut[i] / SR); acc = (1 - a) * x[i] + a * acc; y[i] = acc
    env = np.where(tt < pk, (tt / pk) ** 2, ((1 - tt) / (1 - pk)) ** 1.6)
    return 0.55 * y / max(1e-6, np.abs(y).max()) * env

def pluck_fx(fx):
    from music import pluck
    rng = np.random.default_rng(5); out = np.zeros(int(0.7 * SR))
    for j, f in enumerate(fx.get("notes", [1318.5, 1975.5])):
        p = pluck(f, 0.6, SR, rng) * (0.5 if j else 0.6); s = int(j * 0.07 * SR); out[s:s + len(p)] += p[:len(out) - s]
    return 0.5 * out / max(1e-6, np.abs(out).max())

SFX = {"whoosh": whoosh, "pluck": pluck_fx}

def audio(spec, segs, total):
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", rel(spec["source"]), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    src = np.frombuffer(pcm, np.float32).astype(np.float64); out = []; f = int(0.015 * SR)
    for _, _, a, b, sp in segs:
        piece = src[int(a * SR):int(b * SR)].copy(); ramp = np.linspace(0, 1, f)
        if sp != 1.0: piece = np.interp(np.arange(0, len(piece), sp), np.arange(len(piece)), piece)
        piece[:f] *= ramp; piece[-f:] *= ramp[::-1]; out.append(piece)
    v = np.concatenate(out); v /= max(1e-6, np.abs(v).max()) / 0.9
    v = np.pad(v, (0, int(total * SR) - len(v)))[:int(total * SR)]
    for fx in spec.get("sfx", []):
        snd = SFX[fx["type"]](fx); i = int(fx["at"] * SR); n = min(len(snd), len(v) - i)
        if n > 0: v[i:i + n] += snd[:n] * fx.get("gain", 1.0)
    spec2 = dict(spec); spec2["scenes"] = []
    return M.mix(spec2, v, total)

def main():
    path = sys.argv[1]; check = "--check" in sys.argv
    spec = json.load(open(rel(path))); segs, body = timeline(spec)
    total = body + (spec["end"].get("dur", 2.5) if spec.get("end") else 0)
    for r in spec["table"]["rows"]: r["_out"] = src_to_out(segs, r["word_at"]) if r.get("word_at") is not None else None
    caps = captions(spec, segs); frames = load_frames(spec)
    out_dir = os.path.join(ROOT, "reels")
    if check:
        for i, t in enumerate([0.5] + [r["_out"] + 0.8 for r in spec["table"]["rows"] if r["_out"] is not None] + [total - 1]):
            frame_at(spec, frames, segs, caps, total, t).convert("RGB").save(os.path.join(out_dir, f"{spec['id']}_check_{i + 1}.jpg"), quality=85)
        print(f"checks written, total {total:.1f}s"); return
    import soundfile as sf
    wav = os.path.join(M.CACHE, spec["id"] + ".wav"); sf.write(wav, audio(spec, segs, total), SR)
    out = os.path.join(out_dir, spec["id"] + ".mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        p.stdin.write(frame_at(spec, frames, segs, caps, total, fi / FPS).convert("RGB").tobytes())
    p.stdin.close(); p.wait(); print(f"{out}  {total:.1f}s")

if __name__ == "__main__":
    main()
