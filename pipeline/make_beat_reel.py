"""Render a short "beat" Reel (30-50 s): big on-screen visuals that build sentence by sentence, a small presenter
(or Dollar Bill) at the bottom lip-synced to one uncut ElevenLabs take, light music, and the agreed CTA.

Usage:  python3 pipeline/make_beat_reel.py hooks/<id>.json          -> reels/<id>.mp4
        python3 pipeline/make_beat_reel.py hooks/<id>.json --check  -> reels/<id>_check_<n>.jpg (one still per beat)

Spec:
{ "id": "...", "character": "c" | "e" | "raccoon_soft3d", "character_voice": "elevenlabs:<voice>:eleven_v3",
  "voice_prefix": "..." (optional, raccoon), "music": true,
  "beats": [ {"sentences": [{"text": "..."}, ...], "visual": {...}}, ... ] }
Visuals (items appear on the sentence index given by "at", default: item i on sentence i):
  {"type": "title", "small": "...", "lines": [["text", "ink|orange|green|red"], ...], "chips": [{"label", "value", "color", "at"}]}
  {"type": "split", "left": "header", "right": "header", "rows": [{"label", "left", "right", "lmark": "x|check|", "rmark", "at"}],
   "foot": {"left", "right", "at"}}
  {"type": "pairs", "title": "...", "pairs": [{"left", "right", "good": "left|right", "at"}]}
  {"type": "table", "title": "...", "rows": [{"label", "value", "at", "check": false}], "source": "..."}
  {"type": "card", "lines": [["text", "colour"], ...], "source": "..."}
  {"type": "cta", "lines": [["Save first.", "ink"], ...]}  (default lines: "Save first. Then spend with confidence.")
Spec "logo": false drops the small top logo, which sits inside the Instagram top safe zone (y < 255).
Hook beat is always fully on screen from frame 1.
"""
import json, math, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from make_reel import W, H, FPS, S, CACHE, INK, GREY, ORANGE, WHITE, font, make_bg, appear, Frame, logo
from make_story_reel import character, viseme_track, LETTER_PHONEME, LEAD, TAIL
from make_explainer import one_take

RED = (200, 40, 30); GREEN = (30, 140, 80); CARD = (255, 255, 255); SOFT_G = (226, 244, 233); SOFT_R = (250, 228, 224)
COLS = {"ink": INK, "orange": ORANGE, "green": GREEN, "red": RED, "grey": GREY}
PRES_TOP, PRES_H = 1260, 720          # presenter: head and shoulders at the bottom

def fit(fr, s, w, size, maxw):
    return min(size, size * maxw / max(fr.tl(s, font(w, size)), 1))

def mark(fr, x, y, r, kind, k):
    if k <= 0 or not kind: return
    col = GREEN if kind == "check" else RED
    fr.ellipse([x - r, y - r, x + r, y + r], col + (fr.a(k),))
    c = WHITE + (fr.a(k),)
    if kind == "check": fr.line([(x - r * .45, y + r * .02), (x - r * .1, y + r * .38), (x + r * .5, y - r * .35)], c, r * .22)
    else:
        fr.line([(x - r * .38, y - r * .38), (x + r * .38, y + r * .38)], c, r * .22)
        fr.line([(x + r * .38, y - r * .38), (x - r * .38, y + r * .38)], c, r * .22)

def wrap(fr, s, w, size, maxw):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if fr.tl(t, font(w, size)) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = wd
    return lines + [cur]

def k_at(t, cues, i, d=0.4):
    i = min(max(i, 0), len(cues) - 1); return appear(t, cues[i] - 0.15, d)

def v_title(fr, t, v, cues, inst):
    y = 330
    if v.get("small"):
        fs = fit(fr, v["small"], "b", 60, 920); fr.text((W / 2, y), v["small"], font("b", fs), INK, 1 if inst else k_at(t, cues, 0), anchor="ma"); y += 110
    size = min(fit(fr, s, "xb", 104, 940) for s, _ in v["lines"])
    for i, (s, c) in enumerate(v["lines"]):
        fr.text((W / 2, y), s, font("xb", size), COLS.get(c, INK), 1 if inst else k_at(t, cues, 0), anchor="ma"); y += size * 1.15
    chips = v.get("chips", [])
    if chips:
        y += 40; cw = (940 - 30 * (len(chips) - 1)) / len(chips)
        for j, c in enumerate(chips):
            k = k_at(t, cues, c.get("at", j)) if c.get("at") is not None else 1
            x0 = 70 + j * (cw + 30); col = COLS.get(c.get("color", "ink"), INK)
            fr.rrect([x0, y, x0 + cw, y + 250], 36, CARD, k)
            fr.text((x0 + cw / 2, y + 40), c["label"], font("b", fit(fr, c["label"], "b", 34, cw - 40)), GREY, k, anchor="ma", dy=0)
            fr.text((x0 + cw / 2, y + 110), c["value"], font("xb", fit(fr, c["value"], "xb", 92, cw - 40)), col, k, anchor="ma", dy=10)
        y += 250
    if v.get("source"): fr.text((W / 2, y + 30), v["source"], font("m", 28), GREY, 1, anchor="ma", dy=0)

def v_split(fr, t, v, cues, inst=False):
    x0, x1, mid, y = 50, W - 50, W / 2, 260
    hf = font("xb", 36)
    for side, (a, b) in (("left", (x0, mid - 12)), ("right", (mid + 12, x1))):
        col = RED if side == "left" else GREEN
        fr.rrect([a, y, b, y + 120], 30, SOFT_R if side == "left" else SOFT_G, 1)
        ls = wrap(fr, v[side], "xb", 36, b - a - 40)
        for i, l in enumerate(ls): fr.text(((a + b) / 2, y + 60 - (len(ls) - 1) * 22 + i * 44), l, hf, col, 1, anchor="mm", dy=0)
    y += 145
    rows = v["rows"]; rh = min(230, (PRES_TOP - 60 - y - (110 if v.get("foot") else 0)) / max(len(rows), 1))
    for j, r in enumerate(rows):
        k = k_at(t, cues, r.get("at", j)); ry = y + j * rh
        if r.get("label"): fr.text((mid, ry + 2), r["label"], font("b", 26), GREY, k, anchor="ma", dy=0)
        for side, (a, b), mk in (("left", (x0, mid - 12), r.get("lmark")), ("right", (mid + 12, x1), r.get("rmark"))):
            fr.rrect([a, ry + 36, b, ry + rh - 10], 24, CARD, k)
            txt = r.get(side, ""); lines = wrap(fr, txt, "b", 38, b - a - (90 if mk else 40))
            for i, l in enumerate(lines[:3]):
                fr.text((a + 24, ry + 36 + (rh - 46) / 2 - (len(lines[:3]) - 1) * 24 + i * 48), l, font("b", 38), INK, k, anchor="lm", dy=0)
            mark(fr, b - 40, ry + 36 + (rh - 46) / 2, 22, mk, k)
    f = v.get("foot")
    if f:
        k = k_at(t, cues, f.get("at", len(rows))); fy = y + len(rows) * rh + 10
        for side, (a, b), col in (("left", (x0, mid - 12), RED), ("right", (mid + 12, x1), GREEN)):
            fr.text(((a + b) / 2, fy), f[side], font("xb", fit(fr, f[side], "xb", 76, b - a - 20)), col, k, anchor="ma", dy=14)
        if f.get("label"): fr.text((mid, fy + 95), f["label"], font("b", 28), GREY, k, anchor="ma", dy=0)

def v_pairs(fr, t, v, cues, inst=False):
    y = 280
    if v.get("title"):
        size = fit(fr, v["title"], "xb", 70, 940); fr.text((W / 2, y), v["title"], font("xb", size), INK, 1, anchor="ma"); y += size + 50
    ph = min(270, (PRES_TOP - 40 - y) / max(len(v["pairs"]), 1))
    for j, p in enumerate(v["pairs"]):
        k = k_at(t, cues, p.get("at", j)); ry = y + j * ph
        good = p.get("good", "right")
        for side, (a, b) in (("left", (50, W / 2 - 12)), ("right", (W / 2 + 12, W - 50))):
            ok = side == good
            fr.rrect([a, ry, b, ry + ph - 24], 28, SOFT_G if ok else SOFT_R, k)
            lines = wrap(fr, p[side], "b", 40, b - a - 110)
            for i, l in enumerate(lines[:3]):
                fr.text((a + 26, ry + (ph - 24) / 2 - (len(lines[:3]) - 1) * 25 + i * 50), l, font("b", 40), INK if ok else GREY, k, anchor="lm", dy=0)
            mark(fr, b - 48, ry + (ph - 24) / 2, 26, "check" if ok else "x", k_at(t, cues, p.get("at", j), 0.3) if ok else k)

def v_table(fr, t, v, cues, inst=False):
    y = 270
    if v.get("title"):
        for l in wrap(fr, v["title"], "xb", 62, 940):
            fr.text((W / 2, y), l, font("xb", 62), INK, 1, anchor="ma"); y += 74
        y += 30
    rows = v["rows"]; rh = min(170, (PRES_TOP - 110 - y) / max(len(rows), 1))
    fr.rrect([60, y - 10, W - 60, y + len(rows) * rh + 10], 36, CARD, 1)
    for j, r in enumerate(rows):
        k = k_at(t, cues, r.get("at", j)); ry = y + j * rh + rh / 2
        fr.text((110, ry), r["label"], font("xb", 64), INK, k, anchor="lm", dy=0)
        fr.text((W - 110 - (70 if r.get("check") else 0), ry), r["value"], font("xb", 64), ORANGE, k, anchor="rm", dy=0)
        if r.get("check"): mark(fr, W - 130, ry, 26, "check", k)
    if v.get("source"): fr.text((W / 2, y + len(rows) * rh + 30), v["source"], font("m", 28), GREY, 1, anchor="ma", dy=0)

def v_card(fr, t, v, cues, inst=False):
    y = 420
    for i, (s, c) in enumerate(v["lines"]):
        k = k_at(t, cues, i if v.get("stagger") else 0)
        for l in wrap(fr, s, "xb", 96, 960):
            fr.text((W / 2, y), l, font("xb", 96), COLS.get(c, INK), k, anchor="ma"); y += 112
        y += 20
    if v.get("source"): fr.text((W / 2, y + 20), v["source"], font("m", 28), GREY, 1, anchor="ma", dy=0)

def v_cta(fr, t, v, cues, inst=False):
    logo(fr, W / 2, 420, 120, appear(t, 0))
    lines = [(s_, COLS.get(c_, INK)) for s_, c_ in v["lines"]] if v.get("lines") else [("Save first.", INK), ("Then spend with", INK), ("confidence.", ORANGE)]
    for i, (s, c) in enumerate(lines):
        fr.text((W / 2, 640 + i * 110), s, font("xb", 96), c, appear(t, 0.2 + i * 0.25), anchor="ma")
    f = font("xb", 54); tw = fr.tl("divvyupp.com", f); k = appear(t, 1.0)
    fr.rrect([W / 2 - tw / 2 - 50, 1040, W / 2 + tw / 2 + 50, 1150], 55, ORANGE, k)
    fr.text((W / 2, 1095), "divvyupp.com", f, WHITE, k, anchor="mm", dy=0)

_CLIPS = {}
def clip_frames(src):
    """Decode a background clip to 1080x1920 RGB frames (cover-cropped), cached per path."""
    if src not in _CLIPS:
        path = src if os.path.isabs(src) else os.path.join(ROOT, src)
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-an", "-vf",
                              f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], check=True, capture_output=True).stdout
        _CLIPS[src] = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    return _CLIPS[src]

def v_clip(fr, t, v, cues, inst=False, t0=0.0):
    """Full-screen background clip (frozen on its last frame if the voice runs longer) with a dark gradient at the
    top for the hook text, and optional chips near the bottom."""
    from PIL import Image as _I
    fs = clip_frames(v["src"]); i = min(int((t - t0) * FPS), len(fs) - 1)
    frame = _I.fromarray(fs[max(i, 0)]).resize((W * S, H * S)).convert("RGBA")
    grad = np.zeros((H, 1), np.float32); grad[:820, 0] = np.linspace(0.78, 0, 820); grad[H - 700:, 0] = np.linspace(0, 0.7, 700)
    shade = np.zeros((H, W, 4), np.uint8); shade[..., 3] = (np.repeat(grad, W, 1) * 255).astype(np.uint8)
    frame.alpha_composite(_I.fromarray(shade).resize((W * S, H * S)))
    fr.bg_override = frame
    y = 260
    size = min(fit(fr, s_, "xb", 96, 960) for s_, _ in v["lines"])
    for s_, c in v["lines"]:
        col = WHITE if c == "ink" else COLS.get(c, WHITE)
        fr.text((W / 2, y), s_, font("xb", size), col, 1 if inst else k_at(t, cues, 0), anchor="ma"); y += size * 1.15
    chips = v.get("chips", [])
    if chips:
        cy = H - 480; cw = (940 - 30 * (len(chips) - 1)) / len(chips)
        for j, c in enumerate(chips):
            k = k_at(t, cues, c.get("at", j)); x0 = 70 + j * (cw + 30); col = COLS.get(c.get("color", "ink"), INK)
            fr.rrect([x0, cy, x0 + cw, cy + 230], 36, CARD, k)
            fr.text((x0 + cw / 2, cy + 34), c["label"], font("b", fit(fr, c["label"], "b", 32, cw - 40)), GREY, k, anchor="ma", dy=0)
            fr.text((x0 + cw / 2, cy + 95), c["value"], font("xb", fit(fr, c["value"], "xb", 88, cw - 40)), col, k, anchor="ma", dy=10)

VIS = {"clip": v_clip, "title": v_title, "split": v_split, "pairs": v_pairs, "table": v_table, "card": v_card, "cta": v_cta}

def main():
    import soundfile as sf
    spec_path = sys.argv[1]; check = "--check" in sys.argv
    spec = json.load(open(spec_path)); rid = spec["id"]
    tmp = os.path.join(CACHE, "tmp_" + rid); os.makedirs(tmp, exist_ok=True); os.makedirs(os.path.join(ROOT, "reels"), exist_ok=True)
    bg = make_bg()
    sents, starts, (ch, st, en), audio, sr = one_take(spec, tmp)
    def first_spoken(i):
        tag = False
        for j in range(i, len(ch)):
            if ch[j] == "[": tag = True
            elif ch[j] == "]": tag = False
            elif not tag and ch[j].isalnum(): return st[j]
        return st[-1]
    scue = [LEAD + first_spoken(i) for i in starts]                  # sentence start times, reel seconds
    phon, tag = [], False
    for c, a, b in zip(ch, st, en):
        if c == "[": tag = True
        if not tag and b > 0: phon.append((LEAD + a, LEAD + b, LETTER_PHONEME.get(c.lower(), " ")))
        if c == "]": tag = False
    total = LEAD + len(audio) / sr + TAIL; n = round(total * FPS)
    # beats -> time ranges and per-beat sentence cues
    beats, k = [], 0
    for bi, b in enumerate(spec["beats"]):
        m = len(b["sentences"]); cs = scue[k:k + m]; k += m
        beats.append({"v": b["visual"], "t0": 0.0 if bi == 0 else cs[0] - 0.25, "cues": cs, "mood": b.get("mood", "neutral")})
    for i, b in enumerate(beats): b["t1"] = beats[i + 1]["t0"] if i + 1 < len(beats) else total
    vis = viseme_track(phon, n)
    def draw(f):
        t = f / FPS; fr = Frame(bg, t, total); fr.g = min(1.0, (total - t) / 0.35)
        b = next(x for x in beats if x["t0"] <= t < x["t1"] or x is beats[-1]); bi = beats.index(b)
        kin = 1.0 if bi == 0 else appear(t, b["t0"], 0.3)
        sub = Frame(bg, t, total); sub.g = kin * fr.g; sub.layer = fr.layer; sub.d = fr.d
        typ = b["v"]["type"]
        if typ not in ("cta", "clip") and spec.get("logo", True): logo(sub, W / 2, 140, 60, 1)  # "logo": false keeps the top 255 px clear (safe zone)
        if typ == "clip": v_clip(sub, t, b["v"], b["cues"], bi == 0, b["t0"]); fr.bg = sub.bg_override
        else: VIS[typ](sub, t, b["v"], b["cues"], bi == 0)
        if typ not in ("cta", "clip"):
            character(fr.layer, W / 2, PRES_TOP, PRES_H, t, vis[min(f, n - 1)], b["mood"], fr.g, spec["character"])
        return fr.img()
    if check:
        for bi, b in enumerate(beats):
            tt = min(b["t1"] - 0.2, (b["cues"][-1] if b["cues"] else b["t0"]) + 1.2)
            draw(int(tt * FPS)).save(os.path.join(ROOT, "reels", f"{rid}_check_{bi}.jpg"), quality=85)
        print("check frames written", len(beats)); return
    full = np.concatenate([np.zeros(int(LEAD * sr)), audio, np.zeros(int(TAIL * sr))]) * 0.95
    if spec.get("music", True):
        from music import mix_under
        full = mix_under(full, sr)
    wav = os.path.join(tmp, "full.wav"); sf.write(wav, full, sr)
    vtmp = os.path.join(tmp, "v.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", vtmp], stdin=subprocess.PIPE)
    for f in range(n): p.stdin.write(draw(f).tobytes())
    p.stdin.close(); assert p.wait() == 0
    out = os.path.join(ROOT, "reels", rid + ".mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vtmp, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    print("wrote", out, f"{total:.1f}s")

if __name__ == "__main__": main()
