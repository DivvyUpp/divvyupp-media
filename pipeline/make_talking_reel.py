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
import json, os, subprocess, sys
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
    for a, b in spec["segments"]:
        segs.append((t, t + (b - a), a, b)); t += b - a
    return segs, t

def src_to_out(segs, s):
    for o0, o1, a, b in segs:
        if a <= s <= b: return o0 + (s - a)
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
    o0, o1, a, b = segs[si]; s = a + (t - o0)
    src = Image.fromarray(frames[min(int(s * FPS), len(frames) - 1)])
    pn = spec["panel"]; ph = pn["height"]; z = 1.0 if si % 2 == 0 else pn.get("punch", 1.07)
    cw, ch = W / z, ph / z; cy = H * pn.get("focus_y", 0.42)
    y0 = min(max(0, cy - ch / 2), H - ch); x0 = (W - cw) / 2
    panel = src.resize((W, ph), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    img = Image.new("RGBA", (W, H), CREAM + (255,)); img.paste(panel, (0, pn.get("top", 0)))
    g = np.zeros((ph, 1), np.float32); g[ph - 260:, 0] = np.linspace(0, 0.55, 260); g[:420, 0] = np.linspace(0.45, 0, 420)
    a_ = np.zeros((ph, W, 4), np.uint8); a_[..., 3] = (np.repeat(g, W, 1) * 255).astype(np.uint8)
    img.alpha_composite(Image.fromarray(a_), (0, pn.get("top", 0)))
    hk = spec.get("hook")
    draw_table(img, spec["table"], t, pn.get("top", 0) + ph + 30, hk if spec.get("hook_in_table", True) else None)
    if hk and not spec.get("hook_in_table", True) and t < hk.get("until", 3.0): draw_hook(img, hk["text"])
    nt = spec.get("nametag")
    if nt and nt.get("from", 0) <= t < nt.get("until", 3.0):
        d = ImageDraw.Draw(img); f = font("b", 36); tw = f.getlength(nt["text"]); yy = pn.get("top", 0) + ph - 250
        d.rounded_rectangle([60, yy, 60 + tw + 48, yy + 64], 32, fill=(255, 255, 255, 235)); d.text((84, yy + 32), nt["text"], font=f, fill=INK, anchor="lm")
    draw_caption(img, caps, t, pn.get("top", 0) + ph - 150)
    return img

def audio(spec, segs, total):
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", rel(spec["source"]), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    src = np.frombuffer(pcm, np.float32).astype(np.float64); out = []; f = int(0.015 * SR)
    for _, _, a, b in segs:
        piece = src[int(a * SR):int(b * SR)].copy(); ramp = np.linspace(0, 1, f)
        piece[:f] *= ramp; piece[-f:] *= ramp[::-1]; out.append(piece)
    v = np.concatenate(out); v /= max(1e-6, np.abs(v).max()) / 0.9
    v = np.pad(v, (0, int(total * SR) - len(v)))[:int(total * SR)]
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
