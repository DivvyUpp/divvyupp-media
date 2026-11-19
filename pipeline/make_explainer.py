"""Render the landscape "How DivvyUpp works" explainer: an animal presenter on the left, rebuilt app screens (current
brand) in a phone on the right, burned-in captions. The whole script is voiced in ONE ElevenLabs take, used uncut.

Usage:  python3 pipeline/make_explainer.py hooks/<spec>.json [--check]   -> reels/<id>.mp4 (or stills with --check)

Spec: {"id", "character", "character_voice": "elevenlabs:<voice>[:model]", "music": true,
       "beats": [{"screen": "<state>", "sentences": [{"text": "...", "screen": "<state>"?, "mood": "happy"?}, ...]}, ...]}
Screen states are drawn by screens.py (dashboard_today/week/month, report, plan_0..4, ask_*, cta).
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); ROOT = os.path.dirname(HERE)
CACHE = os.path.join(HERE, ".cache")
W, H, FPS = 1920, 1080, 30
LEAD, TAIL = 0.5, 1.6
INK = (21, 16, 15); ORANGE = (224, 74, 26); GREY = (95, 102, 114); CREAM = (255, 250, 247)
FD = os.path.join(CACHE, "fonts/package/files/plus-jakarta-sans-latin-%s-normal.woff")
_fc = {}
def font(w, s):
    k = (w, s)
    if k not in _fc: _fc[k] = ImageFont.truetype(FD % w, s)
    return _fc[k]

def background():
    bg = np.zeros((H, W, 3), dtype=np.float32); bg[:] = CREAM
    glow = Image.new("L", (W, H), 0); g = ImageDraw.Draw(glow)
    g.ellipse([1100, -500, 2300, 500], fill=255); g.ellipse([-400, 700, 700, 1500], fill=170)
    glow = np.asarray(glow.filter(ImageFilter.GaussianBlur(220)), dtype=np.float32)[..., None] / 255 * 0.55
    bg = bg * (1 - glow) + np.array((255, 226, 212), dtype=np.float32) * glow
    im = Image.fromarray(bg.astype("uint8")).convert("RGBA")
    # logo, top-left
    d = ImageDraw.Draw(im); s = 64; x, y = 60, 44
    d.rounded_rectangle([x, y, x + s, y + s], int(s * 0.28), fill=ORANGE)
    c = x + s / 2; sw = int(s * 0.1); top, bot = y + s * 0.27, y + s * 0.73; arm = s * 0.19
    for a, b in (((c, top), (c, bot)), ((c - arm, top + arm), (c, top)), ((c, top), (c + arm, top + arm))): d.line([a, b], fill="white", width=sw)
    for px, py in ((c, bot), (c - arm, top + arm), (c + arm, top + arm), (c, top)): d.ellipse([px - sw / 2, py - sw / 2, px + sw / 2, py + sw / 2], fill="white")
    d.text((x + s + 18, y + s / 2), "DivvyUpp", font=font(800, 40), fill=INK, anchor="lm")
    return im

# ---------- phone ----------
PX, PY, PW, PH = 1215, 40, 480, 1000          # phone body
def phone_frame():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).rounded_rectangle([PX + 10, PY + 24, PX + PW + 10, PY + PH + 24], 70, fill=90)
    im.paste((60, 40, 30, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(28)))
    d.rounded_rectangle([PX, PY, PX + PW, PY + PH], 70, fill=(26, 22, 22))
    return im
SX, SY, SW_, SH_ = PX + 14, PY + 14, PW - 28, PH - 28
def screen_mask():
    m = Image.new("L", (SW_, SH_), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, SW_ - 1, SH_ - 1], 58, fill=255); return m

# ---------- voice ----------
def voice_print(path):
    import librosa, warnings; warnings.filterwarnings("ignore")
    y, sr = librosa.load(path, sr=16000, duration=40)
    f0, _, _ = librosa.pyin(y, fmin=80, fmax=500, sr=sr); f0 = f0[~np.isnan(f0)]
    return librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20).mean(1), float(np.median(f0))

def voice_distance(mp3_bytes, ref, tmp):
    """How far a take sounds from the approved reference: pitch (the main giveaway) plus overall timbre."""
    f = os.path.join(tmp, "score.mp3"); open(f, "wb").write(mp3_bytes)
    m, f0 = voice_print(f)
    return abs(12 * np.log2(f0 / ref[1])) * 4 + float(np.linalg.norm(m - ref[0])) / 10

def one_take(spec, tmp):
    import base64, soundfile as sf
    from make_story_reel import _el_request
    parts = spec["character_voice"].split(":"); vid = parts[1]; model = parts[2] if len(parts) > 2 else "eleven_v3"
    sents = [s for b in spec["beats"] for s in b["sentences"]]
    text, starts, pos = "", [], 0
    for s in sents: starts.append(pos); text += s["text"] + " "; pos += len(s["text"]) + 1
    # v3 delivery varies from take to take (pitch, age, energy). Voice N seeded takes and keep the one that sounds
    # most like the approved reference recording of this character (spec "voice_reference").
    ref = voice_print(os.path.join(ROOT, spec["voice_reference"])) if spec.get("voice_reference") else None
    best = None
    for seed in range(1, int(spec.get("takes", 1)) + 1):
        h_, r_ = _el_request(vid, model, text.strip(), seed=seed if spec.get("takes", 1) > 1 else None)
        score = voice_distance(base64.b64decode(r_["audio_base64"]), ref, tmp) if ref else 0
        print(f"take {seed}: distance from reference {score:.1f}")
        if best is None or score < best[0]: best = (score, h_, r_)
    _, h, r = best
    mp3 = os.path.join(tmp, h + ".mp3"); open(mp3, "wb").write(base64.b64decode(r["audio_base64"]))
    wav = os.path.join(tmp, "take.wav"); sr = 24000
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", str(sr), wav], check=True)
    audio, _ = sf.read(wav)
    al = r["alignment"]; ch, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    return sents, starts, (ch, st, en), audio, sr

def words_of(sent_text, start, ch, st):
    """Spoken words (tags removed) of one sentence with start times, for captions."""
    out, word, wt, tag = [], "", None, False
    for j in range(start, start + len(sent_text)):
        c = ch[j] if j < len(ch) else " "
        if c == "[": tag = True; continue
        if c == "]": tag = False; continue
        if tag: continue
        if c == " ":
            if word: out.append((word, wt)); word = ""
        else:
            if not word: wt = st[j] if j < len(st) else st[-1]
            word += c
    if word: out.append((word, wt))
    return out

def caption_chunks(words, maxc=34):
    chunks, cur = [], []
    for w, t in words:
        if cur and len(" ".join(x for x, _ in cur + [(w, t)])) > maxc * 2: chunks.append(cur); cur = []
        cur.append((w, t))
        if w.endswith((".", "?", "!")) and len(" ".join(x for x, _ in cur)) > maxc: chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    return [(" ".join(x for x, _ in c), c[0][1]) for c in chunks]

def wrap(text, f, maxw, d):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) > maxw and cur: lines.append(cur); cur = w
        else: cur = t
    if cur: lines.append(cur)
    return lines

# ---------- main ----------
def main():
    import soundfile as sf, screens, animals
    from make_story_reel import viseme_track
    spec_path = sys.argv[1]; check = "--check" in sys.argv
    spec = json.load(open(spec_path)); rid = spec["id"]
    tmp = os.path.join(CACHE, "tmp_" + rid); os.makedirs(tmp, exist_ok=True); os.makedirs(os.path.join(ROOT, "reels"), exist_ok=True)
    sents, starts, (ch, st, en), audio, sr = one_take(spec, tmp)
    full = np.concatenate([np.zeros(int(LEAD * sr)), audio, np.zeros(int(TAIL * sr))]); total = len(full) / sr; n = int(total * FPS)
    # timeline: screen state, mood and captions keyed to the spoken words
    def first_t(i):
        tag = False
        for j in range(i, len(ch)):
            if ch[j] == "[": tag = True
            elif ch[j] == "]": tag = False
            elif not tag and ch[j].isalnum(): return LEAD + st[j]
        return LEAD + st[-1]
    events, caps, k = [], [], 0
    for b in spec["beats"]:
        for j, s in enumerate(b["sentences"]):
            t = first_t(starts[k]) - 0.15
            scr = s.get("screen") or (b["screen"] if j == 0 else None)
            events.append((t, scr, s.get("mood")))
            for text, wt in caption_chunks(words_of(s["text"], starts[k], ch, st)):
                for a_, b_ in spec.get("caption_replace", {}).items(): text = text.replace(a_, b_)   # e.g. said "Dollar Bill", shown "$Bill"
                caps.append((LEAD + wt - 0.05, text))
            k += 1
    phon = []; tag = False
    for c, a, b_ in zip(ch, st, en):
        if c == "[": tag = True
        if not tag:
            from make_story_reel import LETTER_PHONEME
            phon.append((LEAD + a, LEAD + b_, LETTER_PHONEME.get(c.lower(), " ")))
        if c == "]": tag = False
    vis = viseme_track(phon, n)
    def state_at(t):
        scr, mood = events[0][1], "happy"
        for et, s, m in events:
            if et <= t:
                if s: scr = s
                if m: mood = m
        return scr, mood
    def prev_screen_change(t):
        last, prev = None, None
        for et, s, _ in events:
            if et <= t and s:
                if s != last: prev, last, tchg = last, s, et
        return prev, (tchg if last else 0)
    bg = background(); ph = phone_frame(); mask = screen_mask(); scache = {}
    def screen_img(name):
        if name not in scache: scache[name] = screens.render(name, SW_, SH_)
        return scache[name]
    capcache = {}
    def caption_img(text):
        if text not in capcache:
            f = font(700, 40); dd = ImageDraw.Draw(Image.new("RGB", (10, 10)))
            lines = wrap(text, f, 860, dd); lh = 54; w = int(max(dd.textlength(l, font=f) for l in lines)) + 60; hgt = lh * len(lines) + 34
            im = Image.new("RGBA", (w, hgt), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.rounded_rectangle([0, 0, w - 1, hgt - 1], 26, fill=(21, 16, 15, 215))
            for i, l in enumerate(lines): d.text((w / 2, 17 + i * lh + lh / 2), l, font=f, fill="white", anchor="mm")
            capcache[text] = im
        return capcache[text]
    def frame(f):
        t = f / FPS; im = bg.copy()
        scr, mood = state_at(t)
        # presenter
        blink = (t + 0.9) % 3.7 < 0.12; bob = math.sin(t * 1.6) * 4
        sp = animals.sprite(spec["character"], vis[min(f, n - 1)], blink, mood, 980)
        im.alpha_composite(sp, (int(560 - sp.width / 2), int(150 + bob)))
        # phone + screen (crossfade on change)
        im.alpha_composite(ph)
        cur = screen_img(scr); prev, tc = prev_screen_change(t); k_ = min(1.0, (t - tc) / 0.3) if prev else 1.0
        scr_im = cur if k_ >= 1 or not prev else Image.blend(screen_img(prev), cur, k_)
        im.paste(scr_im, (SX, SY), mask)
        # caption
        cap = None
        for ct, text in caps:
            if ct <= t: cap = text
        if cap and t < LEAD + len(audio) / sr + 0.4:
            ci = caption_img(cap); im.alpha_composite(ci, (int(560 - ci.width / 2), H - ci.height - 46))
        g = min(1.0, t / 0.4, (total - t) / 0.6)
        out = im.convert("RGB")
        if g < 1: out = Image.blend(Image.new("RGB", (W, H), CREAM), out, max(0.0, g))
        return out
    if check:
        for et, s, _ in events:
            if s: frame(int((et + 0.5) * FPS)).save(os.path.join(ROOT, "reels", f"{rid}_check_{s}.jpg"), quality=85)
        print("check frames written"); return
    sf.write(os.path.join(tmp, "voice.wav"), full * 0.95, sr)
    a = full * 0.95
    if spec.get("music", True):
        from music import mix_under
        a = mix_under(a, sr)
    sf.write(os.path.join(tmp, "full.wav"), a, sr)
    out = os.path.join(ROOT, "reels", rid + ".mp4"); part = out + ".part.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", os.path.join(tmp, "full.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", part], stdin=subprocess.PIPE)
    for f in range(n): p.stdin.write(frame(f).tobytes())
    p.stdin.close(); assert p.wait() == 0
    os.replace(part, out); print("wrote", out, round(total, 1), "s")

if __name__ == "__main__": main()
