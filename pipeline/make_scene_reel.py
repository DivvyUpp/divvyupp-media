"""Render a "scene" Reel: a short film told in scenes, each over a still (slow push-in) or a video clip, with
dialogue / voice-over from ElevenLabs (one voice per character), burned-in captions, and overlays drawn by us so
every number stays sharp (phone cards, a notification banner, a progress bar, a note card, title text).

Usage:  python3 pipeline/make_scene_reel.py hooks/<id>.json           -> reels/<id>.mp4
        python3 pipeline/make_scene_reel.py hooks/<id>.json --check   -> reels/<id>_check_<n>.jpg (one still per scene)

Spec:
{ "id": "...", "voices": {"him": "<elevenlabs voice id>", "her": "..."}, "model": "eleven_v3", "music": true,
  "hook": {"text": "...", "until": 4.5}, "label": "Dramatization",
  "scenes": [ {"media": "path.png|path.mp4", "min": 3.0, "pre": 0.3, "post": 0.4, "zoom": [1.0, 1.08],
               "lines": [{"who": "him", "text": "[warm] ...", "vo": true}],
               "overlays": [ {"type": "card", "label": "...", "value": "...", "color": "green", "at": 0.5, "y": 520},
                             {"type": "notif", "title": "...", "body": "...", "at": 0.3},
                             {"type": "progress", "label": "Paris fund", "from": 9400, "to": 10000, "goal": 10000,
                              "at": 0.5, "dur": 2.0, "y": 560, "done": "Paris: booked"},
                             {"type": "note", "text": "...", "at_line_end": 0, "delay": 0.3},
                             {"type": "title", "text": "...", "at": 0.0} ] } ],
  "end": {"lines": [["Save first.", "ink"], ["Then spend what's safe.", "orange"]], "url": "divvyupp.com", "dur": 3.0} }
Overlay timing: "at" (seconds into the scene), or "at_line": i (start of line i), or "at_line_end": i (+ "delay").
Audio tags like [warm] are sent to ElevenLabs and stripped from captions. Responses are cached in pipeline/.cache.
"""
import base64, hashlib, json, math, os, re, subprocess, sys, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
CACHE = os.path.join(HERE, ".cache")
W, H, FPS, SR = 1080, 1920, 30, 24000
CAP_Y, CARD_Y = 1500, 1130          # captions and cards sit low, clear of faces and inside the safe zone (bottom 260 px)
FD = os.path.join(CACHE, "fonts/package/files/plus-jakarta-sans-latin-%s-normal.woff")
INK = (21, 16, 15); GREY = (95, 102, 114); ORANGE = (224, 74, 26); WHITE = (255, 255, 255)
GREEN = (30, 140, 80); RED = (200, 40, 30); CREAM = (250, 245, 238)
COLS = {"ink": INK, "orange": ORANGE, "green": GREEN, "red": RED, "grey": GREY, "white": WHITE}
_fc = {}
def font(w, s):
    k = (w, int(s))
    if k not in _fc: _fc[k] = ImageFont.truetype(FD % {"m": 500, "b": 700, "xb": 800}[w], int(s))
    return _fc[k]
def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def strip_tags(s): return re.sub(r"\[[^\]]*\]\s*", "", s).strip()

# ---------------- voice ----------------
def _el_key():
    k = os.environ.get("ELEVENLABS_API_KEY")
    if not k:
        f = os.path.expanduser("~/.secrets/elevenlabs_key")
        if os.path.exists(f): k = open(f).read().strip()
    if not k: sys.exit("No ELEVENLABS_API_KEY (or ~/.secrets/elevenlabs_key)")
    return k

def speak(vid, model, text):
    """One line -> (mono float audio at SR, [(word, start, end)]). Cached by voice+model+text."""
    os.makedirs(os.path.join(CACHE, "eleven"), exist_ok=True)
    body = {"text": text, "model_id": model}
    h = hashlib.sha256((vid + json.dumps(body, sort_keys=True)).encode()).hexdigest()[:20]
    cf = os.path.join(CACHE, "eleven", "scene_" + h + ".json")
    if os.path.exists(cf): r = json.load(open(cf))
    else:
        req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128",
                                     data=json.dumps(body).encode(), headers={"xi-api-key": _el_key(), "Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=300)); json.dump(r, open(cf, "w"))
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         input=base64.b64decode(r["audio_base64"]), capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.float32).astype(np.float64)
    al = r["alignment"]; words, cur, ws, we, tag = [], "", None, None, False
    for c, a, b in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if c == "[": tag = True; continue
        if c == "]": tag = False; continue
        if tag: continue
        if c.isspace():
            if cur: words.append((cur, ws, we)); cur = ""
            continue
        if not cur: ws = a
        cur += c; we = b
    if cur: words.append((cur, ws, we))
    return audio, words

# ---------------- timeline ----------------
def build(spec):
    """Lay scenes out in time. Returns scenes with t0/t1, line timings, the voice track and caption words."""
    t, voice = 0.0, np.zeros(int(SR * 120)); caps = []
    for sc in spec["scenes"]:
        sc["t0"] = t; cur = t + sc.get("pre", 0.3); sc["_lines"] = []
        for ln in sc.get("lines", []):
            a, words = speak(spec["voices"][ln["who"]], spec.get("model", "eleven_v3"), ln["text"])
            i0 = int(cur * SR); voice[i0:i0 + len(a)] += a * ln.get("gain", 1.0)
            dur = len(a) / SR; sc["_lines"].append((cur, cur + dur))
            lid = len(caps) and caps[-1][3] + 1 or 0
            caps += [(w, cur + s, cur + e, lid) for w, s, e in words]
            cur += dur + ln.get("gap", 0.25)
        end = max(t + sc.get("min", 2.0), cur - 0.25 + sc.get("post", 0.4))
        sc["t1"] = end; t = end
    end = spec.get("end")
    total = t + (end.get("dur", 3.0) if end else 0)
    return total, voice[:int(total * SR) + SR], caps

def ov_start(sc, o):
    if "at_line" in o: return sc["_lines"][o["at_line"]][0] - sc["t0"] + o.get("delay", 0)
    if "at_line_end" in o: return sc["_lines"][o["at_line_end"]][1] - sc["t0"] + o.get("delay", 0)
    return o.get("at", 0.0)

# ---------------- drawing ----------------
_media = {}
def media_frame(path, local_t, dur, zoom):
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    if full.lower().endswith((".mp4", ".mov", ".webm")):
        if full not in _media:
            raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", full, "-an", "-vf",
                                  f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], check=True, capture_output=True).stdout
            _media[full] = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
        fs = _media[full]; return Image.fromarray(fs[min(int(local_t * FPS), len(fs) - 1)]).convert("RGBA")
    if full not in _media: _media[full] = Image.open(full).convert("RGB")
    im = _media[full]; iw, ih = im.size
    z = zoom[0] + (zoom[1] - zoom[0]) * min(1.0, local_t / max(dur, 0.01))
    base = min(iw / W, ih / H); cw, ch = W * base / z, H * base / z      # cover-crop, then zoom in about the centre
    x0, y0 = (iw - cw) / 2, (ih - ch) * 0.45
    return im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")

def shade(img):
    g = np.zeros((H, 1), np.float32); g[:700, 0] = np.linspace(0.55, 0, 700); g[H - 760:, 0] = np.linspace(0, 0.62, 760)
    a = np.zeros((H, W, 4), np.uint8); a[..., 3] = (np.repeat(g, W, 1) * 255).astype(np.uint8)
    img.alpha_composite(Image.fromarray(a))

def fit(text, w, size, maxw):
    while size > 20 and font(w, size).getlength(text) > maxw: size -= 2
    return size

def layer(): return Image.new("RGBA", (W, H), (0, 0, 0, 0))

def paste(img, lay, k, dy=0):
    if k <= 0: return
    a = np.array(lay); a[..., 3] = (a[..., 3] * min(1.0, k)).astype(np.uint8)
    l2 = Image.fromarray(a)
    if dy: l2 = l2.transform(l2.size, Image.AFFINE, (1, 0, 0, 0, 1, -dy))
    img.alpha_composite(l2)

def wrap(text, w, size, maxw):
    out, cur = [], ""
    for word in text.split():
        nxt = (cur + " " + word).strip()
        if font(w, size).getlength(nxt) <= maxw: cur = nxt
        else: out.append(cur); cur = word
    if cur: out.append(cur)
    return out

def draw_card(img, o, k):
    lay = layer(); d = ImageDraw.Draw(lay); y = o.get("y", CARD_Y); w0 = 780; x0 = (W - w0) // 2
    lab = o.get("label", ""); val = o.get("value", "")
    vs = fit(val, "xb", 84, w0 - 80); hgt = 70 + (60 if lab else 0) + vs
    d.rounded_rectangle([x0, y, x0 + w0, y + hgt], 44, fill=(255, 255, 255, 240))
    yy = y + 36
    if lab: d.text((W / 2, yy), lab, font=font("b", 40), fill=GREY, anchor="ma"); yy += 60
    d.text((W / 2, yy), val, font=font("xb", vs), fill=COLS.get(o.get("color", "ink"), INK), anchor="ma")
    paste(img, lay, k, dy=int((1 - k) * 30))

def draw_notif(img, o, k):
    lay = layer(); d = ImageDraw.Draw(lay); y = 290; x0, x1 = 60, W - 60
    body = wrap(o["body"], "b", 40, x1 - x0 - 190); hgt = 120 + 52 * len(body)
    d.rounded_rectangle([x0, y, x1, y + hgt], 40, fill=(245, 245, 247, 245))
    d.rounded_rectangle([x0 + 34, y + 34, x0 + 124, y + 124], 22, fill=ORANGE)
    d.text((x0 + 79, y + 79), o.get("app", "D")[0], font=font("xb", 56), fill=WHITE, anchor="mm")
    d.text((x0 + 150, y + 36), o.get("title", "DivvyUpp"), font=font("xb", 38), fill=INK)
    d.text((x1 - 36, y + 38), "now", font=font("m", 32), fill=GREY, anchor="ra")
    for i, ln in enumerate(body): d.text((x0 + 150, y + 86 + 52 * i), ln, font=font("b", 40), fill=INK)
    paste(img, lay, k, dy=int(-(1 - k) * 120))

def draw_progress(img, o, t_local):
    k = ease((t_local - o["_at"]) / 0.4)
    p = ease((t_local - o["_at"] - 0.3) / o.get("dur", 0.01)) if o.get("dur") else 1.0
    v = o["from"] + (o["to"] - o["from"]) * p; goal = o["goal"]; done = v >= goal - 0.5
    lay = layer(); d = ImageDraw.Draw(lay); y = o.get("y", CARD_Y); w0 = 820; x0 = (W - w0) // 2
    d.rounded_rectangle([x0, y, x0 + w0, y + 250], 44, fill=(255, 255, 255, 240))
    d.text((x0 + 50, y + 38), o.get("label", "Paris fund"), font=font("b", 40), fill=GREY)
    right = o.get("done", "") if done and o.get("done") else f"${v:,.0f} of ${goal:,.0f}"
    d.text((x0 + w0 - 50, y + 38), right, font=font("xb", 40), fill=GREEN if done else INK, anchor="ra")
    bx0, by, bx1 = x0 + 50, y + 130, x0 + w0 - 50
    d.rounded_rectangle([bx0, by, bx1, by + 64], 32, fill=(236, 232, 226))
    d.rounded_rectangle([bx0, by, bx0 + max(64, (bx1 - bx0) * min(1, v / goal)), by + 64], 32, fill=GREEN if done else ORANGE)
    if o.get("sub"): d.text((W / 2, y + 260), o["sub"], font=font("xb", 46), fill=WHITE, anchor="ma", stroke_width=4, stroke_fill=INK)
    paste(img, lay, k, dy=int((1 - k) * 30))

def draw_note(img, o, k):
    lay = Image.new("RGBA", (860, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([20, 20, 840, 400], 18, fill=(255, 251, 230, 250), outline=(225, 215, 180), width=3)
    lines = wrap(o["text"], "b", 60, 720)
    for i, ln in enumerate(lines): d.text((430, 210 - 40 * (len(lines) - 1) + 80 * i), ln, font=font("b", 60), fill=INK, anchor="mm")
    lay = lay.rotate(-4, resample=Image.BICUBIC, expand=True)
    full = layer(); full.alpha_composite(lay, ((W - lay.width) // 2, o.get("y", 520)))
    paste(img, full, k, dy=int((1 - k) * 40))

def draw_title(img, o, k):
    lay = layer(); d = ImageDraw.Draw(lay); size = fit(o["text"], "xb", o.get("size", 84), 940)
    d.text((W / 2, o.get("y", 330)), o["text"], font=font("xb", size), fill=WHITE, anchor="ma", stroke_width=6, stroke_fill=INK)
    paste(img, lay, k)

def draw_hook(img, text):
    d = ImageDraw.Draw(img); lines = text.split("\n") if "\n" in text else wrap(text, "xb", 92, 940); y = 300
    for ln in lines:
        size = fit(ln, "xb", 92, 960)
        tw = font("xb", size).getlength(ln)
        d.rounded_rectangle([W / 2 - tw / 2 - 30, y - 18, W / 2 + tw / 2 + 30, y + size + 22], 26, fill=(255, 255, 255, 245))
        d.text((W / 2, y), ln, font=font("xb", size), fill=INK, anchor="ma"); y += size + 52

def draw_caption(img, caps, t):
    """Show the current phrase (up to ~5 words around the spoken word) in big type, the spoken word highlighted."""
    cur = [i for i, c in enumerate(caps) if c[1] - 0.05 <= t <= c[2] + 0.35]
    if not cur: return
    i = cur[-1]; lid = caps[i][3]; first = min(j for j, c in enumerate(caps) if c[3] == lid)
    start = first + ((i - first) // 4) * 4; grp = [c for c in caps[start:start + 4] if c[3] == lid]
    d = ImageDraw.Draw(img); size = 66; words = [c[0] for c in grp]
    while size > 40 and font("xb", size).getlength(" ".join(words)) > 820: size -= 2
    x = W / 2 - font("xb", size).getlength(" ".join(words)) / 2; y = CAP_Y
    for j, (w, s, e, _) in enumerate(grp):
        col = (255, 214, 64) if s - 0.05 <= t <= e + 0.05 else WHITE
        d.text((x, y), w, font=font("xb", size), fill=col, stroke_width=7, stroke_fill=INK)
        x += font("xb", size).getlength(w + " ")

def draw_end(img, end, k):
    lay = Image.new("RGBA", (W, H), CREAM + (255,)); d = ImageDraw.Draw(lay); y = 640
    for txt, c in end["lines"]:
        size = fit(txt, "xb", 104, 940); d.text((W / 2, y), txt, font=font("xb", size), fill=COLS.get(c, INK), anchor="ma"); y += size + 40
    f = font("xb", 58); tw = f.getlength(end.get("url", "divvyupp.com"))
    d.rounded_rectangle([W / 2 - tw / 2 - 54, y + 60, W / 2 + tw / 2 + 54, y + 180], 60, fill=ORANGE)
    d.text((W / 2, y + 120), end.get("url", "divvyupp.com"), font=f, fill=WHITE, anchor="mm")
    if end.get("small"): d.text((W / 2, 1600), end["small"], font=font("m", 34), fill=GREY, anchor="ma")
    paste(img, lay, k)

DRAW = {"card": draw_card, "notif": draw_notif, "note": draw_note, "title": draw_title}

def frame_at(spec, t, caps, total):
    scenes = spec["scenes"]; end = spec.get("end")
    last = scenes[-1]
    if t >= last["t1"] and end:
        img = media_frame(last["media"], last["t1"] - last["t0"], last["t1"] - last["t0"], last.get("zoom", [1.0, 1.08]))
        img = img.filter(ImageFilter.GaussianBlur(12)); draw_end(img, end, ease((t - last["t1"]) / 0.4)); return img
    sc = next(s for s in scenes if s["t0"] <= t < s["t1"]); lt = t - sc["t0"]; dur = sc["t1"] - sc["t0"]
    img = media_frame(sc["media"], lt, dur, sc.get("zoom", [1.0, 1.08])); shade(img)
    for o in sc.get("overlays", []):
        o["_at"] = ov_start(sc, o)
        if lt < o["_at"]: continue
        if o.get("until") is not None and lt > o["until"]: continue
        if o["type"] == "progress": draw_progress(img, o, lt)
        else: DRAW[o["type"]](img, o, ease((lt - o["_at"]) / 0.35))
    hk = spec.get("hook")
    if hk and t < hk.get("until", 4.5): draw_hook(img, hk["text"])
    if spec.get("label") and t < spec.get("label_until", 4.5):
        ImageDraw.Draw(img).text((70, 1600), spec["label"], font=font("m", 32), fill=(255, 255, 255, 220))
    draw_caption(img, caps, t)
    return img

# ---------------- audio ----------------
def ding(sr=SR):
    t = np.arange(int(0.6 * sr)) / sr
    return 0.18 * (np.sin(2 * np.pi * 1318.5 * t) + 0.6 * np.sin(2 * np.pi * 1975.5 * t)) * np.exp(-t * 7)

def mix(spec, voice, total):
    n = int(total * SR); v = np.pad(voice, (0, max(0, n - len(voice))))[:n]
    for sc in spec["scenes"]:
        for o in sc.get("overlays", []):
            if o.get("sfx") == "ding":
                i = int((sc["t0"] + ov_start(sc, o)) * SR); dd = ding(); v[i:i + len(dd)] += dd[:max(0, n - i)]
    if spec.get("music", True):
        from music import mix_under
        return mix_under(v, SR)
    return v / max(1.0, np.abs(v).max() / 0.98)

def main():
    path = sys.argv[1]; check = "--check" in sys.argv
    spec = json.load(open(path if os.path.isabs(path) else os.path.join(ROOT, path)))
    total, voice, caps = build(spec)
    out_dir = os.path.join(ROOT, "reels"); os.makedirs(out_dir, exist_ok=True)
    if check:
        for i, sc in enumerate(spec["scenes"]):
            t = (sc["t0"] + sc["t1"]) / 2
            frame_at(spec, t, caps, total).convert("RGB").save(os.path.join(out_dir, f"{spec['id']}_check_{i + 1}.jpg"), quality=85)
        print(f"{len(spec['scenes'])} check stills, total {total:.1f}s"); return
    import soundfile as sf
    wav = os.path.join(CACHE, spec["id"] + ".wav"); sf.write(wav, mix(spec, voice, total), SR)
    out = os.path.join(out_dir, spec["id"] + ".mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    for f in range(int(total * FPS)):
        p.stdin.write(frame_at(spec, f / FPS, caps, total).convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    print(f"{out}  {total:.1f}s")

if __name__ == "__main__":
    main()
