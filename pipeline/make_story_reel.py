"""Render a DivvyUpp *story* Reel: an illustrated character tells the whole save-first story, with the
approved body spliced in where it explains the flip, then the guarantee and call to action.

Order: hook (character) -> body part 1 ("DivvyUpp flips the order", 0-12.4s) -> guide scene (daily/weekly
number that adjusts) -> payoff scene (bills paid, savings kept, still spending) -> body part 2 (guarantee + CTA).

Usage:  python3 pipeline/make_story_reel.py hooks/<id>.json          -> reels/<id>.mp4
        python3 pipeline/make_story_reel.py hooks/<id>.json --check  -> reels/<id>_check.jpg (one still per scene)

Spec (JSON):
{
  "id": "2026-11-15-a", "format": "story",
  "character": "c" (presenter id from characters.py), "character_voice": "af_heart" (Kokoro) or
  "elevenlabs:<voice_id>[:<model_id>]" (ElevenLabs, default model eleven_v3; needs ELEVENLABS_API_KEY; the whole Reel
  is voiced in one take and cut per scene so the voice stays consistent, "one_take": false to disable), "name_tag": "" (optional),
  "hook":   {"small": "...", "lines": [["...", "ink"|"orange"], ...], "narration": ["..."],
             "moods": ["neutral", "worried", ...] (optional, one per sentence; default worried until turn_cue)},
  "guide":  {"title": [["...", "ink"|"orange"], ...], "narration": ["..."],
             "week": 460, "today": 66, "spend_label": "Dinner out", "spend": 120, "tomorrow": 52,
             "spends": [{"label": "...", "amount": 112, "tomorrow": 55}, ...] (optional, replaces spend_label/spend/
             tomorrow: one sentence per spend after the first guide sentence, tomorrow re-adjusts after each)},
  "payoff": {"title": [["...", "ink"|"orange"], ...], "checks": ["...", "...", "..."], "narration": ["..."]},
  "plan":   {"title": [...], "narration": [one sentence per row], "rows": [{"label": "Income", "amount": 8600, "tag": "Checked against your bank"},
             {"label": "Fixed bills", ...}, {"label": "Savings", ...}, {"label": "Safe-to-spend", ...},
             optional 5th: {"label": "Flexible spending lately", "amount": 2650, "tag": "From your bank history", "bar": false}]}
             (optional: the four numbers, shown after the hook in place of the "flips the order" body section)
}
Run pipeline/setup.sh once per machine first.
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from make_reel import (W, H, FPS, S, CACHE, INK, GREY, ORANGE, WHITE, MUTED, COL, LEAD, TAIL,
                       font, make_bg, ease, appear, Frame, logo)
ROOT = os.path.dirname(HERE)
BODY_SPLIT = 12.4          # body_video/body_audio: end of the "flips the order" scene (silence 11.35-12.8s)
SKIN = (198, 136, 98); SKIN_D = (170, 110, 78); HAIR = (38, 28, 24); SHIRT = ORANGE; SHIRT_D = (190, 60, 20)
RED = (200, 40, 30); GREEN = (30, 140, 80); CARD_BG = (255, 255, 255)

# ---------- voice + mouth envelope ----------
LETTER_PHONEME = {**{c: "a" for c in "a"}, **{c: "e" for c in "eiy"}, **{c: "o" for c in "o"}, **{c: "u" for c in "uw"},
                  **{c: "m" for c in "mbp"}, **{c: "f" for c in "fv"}, **{c: "l" for c in "ltdn"}, **{c: "s" for c in "szcgkhjqxr"}}

def _el_key():
    k = os.environ.get("ELEVENLABS_API_KEY")
    if not k:
        f = os.path.expanduser("~/.secrets/elevenlabs_key")
        if os.path.exists(f): k = open(f).read().strip()
    if not k: sys.exit("ElevenLabs voice requested but no ELEVENLABS_API_KEY (or ~/.secrets/elevenlabs_key)")
    return k

def narrate_elevenlabs(sentences, voice, out_wav):
    """voice = "elevenlabs:<voice_id>[:<model_id>]". One request for the whole segment so the delivery flows;
    sentences may carry v3 audio tags like [excited]. Returns the same shape as narrate(): sentence cues come from the
    character timings, and letters stand in for phonemes for the lip-sync. Responses are cached by text+voice+model."""
    import base64, hashlib, urllib.request, soundfile as sf
    parts = voice.split(":"); vid = parts[1]; model = parts[2] if len(parts) > 2 else "eleven_v3"
    texts = [x[0] if isinstance(x, list) else x for x in sentences]
    text = " ".join(texts); starts, pos = [], 0
    for x in texts: starts.append(pos); pos += len(x) + 1
    os.makedirs(os.path.join(CACHE, "eleven"), exist_ok=True)
    h = hashlib.sha256(f"{vid}|{model}|{text}".encode()).hexdigest()[:20]; cf = os.path.join(CACHE, "eleven", h + ".json")
    if os.path.exists(cf): r = json.load(open(cf))
    else:
        req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128",
                                     data=json.dumps({"text": text, "model_id": model}).encode(),
                                     headers={"xi-api-key": _el_key(), "Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=300)); json.dump(r, open(cf, "w"))
    mp3 = os.path.join(os.path.dirname(out_wav), h + ".mp3"); open(mp3, "wb").write(base64.b64decode(r["audio_base64"]))
    sr = 24000
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", str(sr), out_wav], check=True)
    audio, _ = sf.read(out_wav)
    al = r["alignment"]; ch, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    in_tag, phon = False, []
    for c, a, b in zip(ch, st, en):
        if c == "[": in_tag = True
        if not in_tag: phon.append((LEAD + a, LEAD + b, LETTER_PHONEME.get(c.lower(), " ")))
        if c == "]": in_tag = False
    def first_spoken(i):                 # time of the first spoken letter at or after char index i (skips tags)
        tag = False
        for j in range(i, len(ch)):
            if ch[j] == "[": tag = True
            elif ch[j] == "]": tag = False
            elif not tag and ch[j].isalnum(): return st[j]
        return st[-1]
    cues = [LEAD + first_spoken(i) for i in starts]
    return len(audio) / sr, cues, sr, audio, phon

ONE_TAKE = {}   # tuple(sentence texts) -> (audio, cues, phon) for segments cut from a single whole-Reel take

def _el_request(vid, model, text, seed=None):
    import hashlib, urllib.request
    body = {"text": text, "model_id": model, "voice_settings": {"stability": 0.5}}
    if seed is not None: body["seed"] = seed
    os.makedirs(os.path.join(CACHE, "eleven"), exist_ok=True)
    h = hashlib.sha256(json.dumps(body, sort_keys=True).encode() + vid.encode()).hexdigest()[:20]; cf = os.path.join(CACHE, "eleven", h + ".json")
    if os.path.exists(cf): return h, json.load(open(cf))
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128",
                                 data=json.dumps(body).encode(), headers={"xi-api-key": _el_key(), "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=300)); json.dump(r, open(cf, "w")); return h, r

def one_take(spec, names, tmp):
    """Voice the whole Reel in ONE ElevenLabs request and cut it into segments, so the voice can't drift between
    scenes (separate v3 requests can come back sounding like different takes). Fills ONE_TAKE."""
    import base64, soundfile as sf
    parts = spec["character_voice"].split(":"); vid = parts[1]; model = parts[2] if len(parts) > 2 else "eleven_v3"
    segs = [[x[0] if isinstance(x, list) else x for x in spec[n]["narration"]] for n in names]
    text, sent_starts, pos = "", [], 0
    for sents in segs:
        ss = []
        for x in sents: ss.append(pos); text += x + " "; pos += len(x) + 1
        sent_starts.append(ss)
    text = text.strip()
    h, r = _el_request(vid, model, text)
    mp3 = os.path.join(tmp, "onetake_" + h + ".mp3"); open(mp3, "wb").write(base64.b64decode(r["audio_base64"]))
    wav = os.path.join(tmp, "onetake.wav"); sr = 24000
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", str(sr), wav], check=True)
    audio, _ = sf.read(wav)
    al = r["alignment"]; ch, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    def first_spoken(i):
        tag = False
        for j in range(i, len(ch)):
            if ch[j] == "[": tag = True
            elif ch[j] == "]": tag = False
            elif not tag and ch[j].isalnum(): return st[j]
        return st[-1]
    def last_spoken(lo, hi):
        tag, t = False, None
        for j in range(lo, hi):
            if ch[j] == "[": tag = True
            elif ch[j] == "]": tag = False
            elif not tag and ch[j].isalnum(): t = en[j]
        return t
    # The soundtrack is the take itself, never cut: LEAD of quiet before, TAIL after. Scene boundaries sit in the
    # middle of the take's own pauses, and each scene's video is exactly as long as its stretch of the take.
    full = np.concatenate([np.zeros(int(LEAD * sr)), audio, np.zeros(int(TAIL * sr))])
    bounds = [0.0]
    for k in range(1, len(segs)):
        lo, hi = sent_starts[k - 1][0], sent_starts[k][0]
        e = last_spoken(lo, hi); b0 = first_spoken(hi)
        bounds.append(LEAD + ((e + b0) / 2 if e is not None else b0 - 0.2))
    bounds.append(len(full) / sr)
    fb = [round(t * FPS) for t in bounds]
    plan = {"audio": full, "sr": sr, "names": names, "frames": {}}
    for k, (name, sents) in enumerate(zip(names, segs)):
        t0 = fb[k] / FPS
        cues = [LEAD + first_spoken(i) - t0 for i in sent_starts[k]]
        lo = sent_starts[k][0]; hi = sent_starts[k + 1][0] if k + 1 < len(segs) else len(ch)
        in_tag, phon = False, []
        for c, a_, b_ in zip(ch[lo:hi], st[lo:hi], en[lo:hi]):
            if c == "[": in_tag = True
            if not in_tag: phon.append((LEAD + a_ - t0, LEAD + b_ - t0, LETTER_PHONEME.get(c.lower(), " ")))
            if c == "]": in_tag = False
        plan["frames"][name] = (fb[k], fb[k + 1], cues, phon)
    ONE_TAKE["plan"] = plan

def narrate(sentences, voice, out_wav):
    if voice.startswith("elevenlabs:"): return narrate_elevenlabs(sentences, voice, out_wav)
    """Speak each sentence; return duration, sentence cues, sample rate, audio and phoneme timings
    [(start, end, phoneme)] in reel seconds (LEAD included). Uses kokoro-timed.onnx (built by setup.sh),
    the same model with its per-phoneme durations exposed, so the mouth follows the actual speech."""
    import soundfile as sf
    from kokoro_onnx import Kokoro
    timed = os.path.join(CACHE, "kokoro-timed.onnx")
    k = Kokoro(timed if os.path.exists(timed) else os.path.join(CACHE, "kokoro.onnx"), os.path.join(CACHE, "voices.bin"))
    parts, cues, phon, t, sr = [], [], [], 0.0, 24000
    for i, s in enumerate(sentences):
        s, spd = (s[0], s[1]) if isinstance(s, list) else (s, 1.0)      # ["text", speed] slows a line for delivery
        a, sr, tm = k.create_timed(s, voice=voice, speed=spd, lang="en-us"); p = 0.35 if i < len(sentences) - 1 else 0.0
        cues.append(LEAD + t); phon += [(LEAD + t + x.start, LEAD + t + x.end, x.phoneme) for x in tm]
        parts += [a, np.zeros(int(sr * p))]; t += len(a) / sr + p
    audio = np.concatenate(parts); sf.write(out_wav, audio, sr)
    return t, cues, sr, audio, phon

def viseme_track(phon, n):
    """One mouth shape per frame from phoneme timings; stress/length marks carry the neighbouring sound,
    single-frame flickers are smoothed away."""
    from characters import PHONEME_VISEME
    seq, last = [], "rest"
    for i, (a, b, p) in enumerate(phon):
        if p in "ˈˌ":                       # stress mark: take the next real phoneme's shape
            nxt = next((q for _, _, q in phon[i + 1:] if q not in "ˈˌː"), " ")
            v = PHONEME_VISEME.get(nxt, "rest")
        elif p == "ː": v = last
        else: v = PHONEME_VISEME.get(p, "rest")
        seq.append((a, b, v)); last = v
    out = []
    for f in range(n):
        tt = (f + 0.5) / FPS
        out.append(next((v for a, b, v in seq if a <= tt < b), "rest"))
    for f in range(1, n - 1):
        if out[f - 1] == out[f + 1] != out[f]: out[f] = out[f - 1]
    return out

def mouth_env(audio, sr, total):
    """Per-frame mouth openness 0..1 from the voice loudness (offset by LEAD)."""
    n = round(total * FPS); env = np.zeros(n); hop = sr / FPS
    for f in range(n):
        s = int((f / FPS - LEAD) * sr)
        if 0 <= s < len(audio): env[f] = np.sqrt(np.mean(audio[s:s + int(hop)] ** 2))
    if env.max() > 0: env = env / np.percentile(env[env > 0], 90)
    env = np.clip(env, 0, 1)
    return np.convolve(env, np.ones(2) / 2, "same")

# ---------- character (SVG presenter from characters.py; only the face moves) ----------
def character(base, cx, top, height, t, mouth, mood, k, who):
    """Paste presenter `who` centred on cx with its top at `top` (px), `height` px tall, alpha k (0..1)."""
    if k <= 0: return
    from characters import sprite as human_sprite
    import animals
    sprite = animals.sprite if who in animals.ANIMALS else human_sprite      # animal presenters share the same contract
    m = mouth if isinstance(mouth, str) else (0 if mouth < 0.12 else 1 if mouth < 0.4 else 2 if mouth < 0.75 else 3)
    blink = (t + 0.9) % 3.7 < 0.12
    sp = sprite(who, m, blink, mood, int(height * S))
    if k < 1: sp = sp.copy(); sp.putalpha(sp.split()[3].point(lambda v: int(v * k)))
    bob = math.sin(t * 1.6) * 3
    base.alpha_composite(sp, (int(cx * S - sp.width / 2), int((top + bob) * S)))

def check_icon(fr, x, y, r, k, col=GREEN):
    if k <= 0: return
    fr.ellipse([x - r, y - r, x + r, y + r], col + (fr.a(k),))
    fr.line([(x - r * 0.45, y + r * 0.02), (x - r * 0.1, y + r * 0.38), (x + r * 0.5, y - r * 0.35)], WHITE + (fr.a(k),), r * 0.22)

def title_lines(fr, lines, y, t, start, size=88):
    size = min(size, min(size * 940 / max(fr.tl(s, font("xb", size)), 1) for s, _ in lines))   # fit 940px
    for i, (s, c) in enumerate(lines):
        fr.text((W / 2, y + i * size * 1.14), s, font("xb", size), COL.get(c, INK), appear(t, start + i * 0.25), anchor="ma")

# ---------- scenes ----------
def hook_scene(fr, t, sp, cues, mouth, spec):
    logo(fr, W / 2, 150, 70, appear(t, 0.2))
    y = 330
    if sp.get("small"):
        fs = min(66, 66 * 900 / max(fr.tl(sp["small"], font("b", 66)), 1))     # keep the small line off the edges
        fr.text((W / 2, y), sp["small"], font("b", fs), INK, appear(t, cues[0]), anchor="ma"); y += 130
    title_lines(fr, sp["lines"], y, t, cues[0] + 0.5, 104)
    aside = sp.get("aside")               # {"text": "...", "cue": n}: a deadpan aside chip; the face turns unimpressed
    mood = "worried"
    if aside and aside["cue"] < len(cues):
        k2 = appear(t, cues[aside["cue"]], 0.35); mood = "unimpressed" if k2 > 0.3 else mood
        f = font("xb", 46); tw = fr.tl(aside["text"], f); ay = y + 2 * 118 + 40
        fr.rrect([W / 2 - tw / 2 - 36, ay, W / 2 + tw / 2 + 36, ay + 88], 44, INK, k2)
        fr.text((W / 2, ay + 44), aside["text"], f, WHITE, k2, anchor="mm", dy=0)
    st = sp.get("stat")                  # {"title", "rows": [[label, amount], [label, amount]], "source", "cue"}: guess vs actual
    if st:
        c0 = cues[st.get("cue", 1)] if st.get("cue", 1) < len(cues) else 2.0
        kc = appear(t, c0, 0.4); cx0, cx1, cy = 110, W - 110, y + len(sp["lines"]) * 118 + 30
        unit = st.get("unit", "$"); ch_ = 120 + len(st["rows"]) * 95
        fr.rrect([cx0, cy, cx1, cy + ch_], 36, WHITE, kc)
        fr.text((cx0 + 40, cy + 30), st["title"].upper(), font("b", 26), GREY, kc, dy=0)
        mx = st.get("max") or max(a for _, a in st["rows"])
        for j, (lab, amt) in enumerate(st["rows"]):
            kj = appear(t, c0 + 0.6 + j * 1.6, 0.6); ry = cy + 85 + j * 95
            fr.text((cx0 + 40, ry), lab, font("b", 30), INK, kc, dy=0)
            bw = (cx1 - cx0 - 250) * amt / mx * kj
            col = st.get("color") and RED or (GREY if j == 0 else RED)
            if kj > 0: fr.rrect([cx0 + 40, ry + 42, cx0 + 40 + max(bw, 24), ry + 72], 15, col, kc)
            fr.text((cx1 - 40, ry + 22), f"{amt}%" if unit == "%" else f"${amt}", font("xb", 52), col, kj, anchor="ra", dy=0)
        fr.text((W / 2, cy + ch_ + 15), st["source"], font("m", 24), GREY, kc, anchor="ma", dy=0)
    turn = sp.get("turn_cue")             # sentence index where she turns from the pain to the fix
    if turn is not None and turn < len(cues) and t >= cues[turn] - 0.1: mood = "neutral"
    moods = sp.get("moods")               # optional per-sentence moods, e.g. ["neutral", "worried", "neutral"]
    if moods: mood = moods[min(len(moods) - 1, max([i for i, c in enumerate(cues) if t >= c - 0.1] or [0]))]
    ctop, ch = (1010, 1000) if st else (820, 1150)          # make room for a stat card
    character(fr.layer, W / 2, ctop, ch, t, mouth, mood, appear(t, 0.15) * fr.g, spec["character"])
    if spec.get("name_tag"):
        f = font("b", 30); tw = fr.tl(spec["name_tag"], f); kk = appear(t, 0.8)
        fr.rrect([W / 2 - tw / 2 - 28, 1680, W / 2 + tw / 2 + 28, 1744], 32, WHITE, kk)
        fr.text((W / 2, 1712), spec["name_tag"], f, INK, kk, anchor="mm", dy=0)

def guide_scene(fr, t, sp, cues, mouth, spec):
    logo(fr, W / 2, 150, 70, appear(t, 0.2))
    title_lines(fr, sp["title"], 290, t, 0.3, 84)
    # card
    k = appear(t, 0.6); x0, x1, y0 = 110, W - 110, 540
    ch_n = len(sp.get("spends") or [0]); card_h = 600 + (ch_n - 1) * 96
    if k > 0:
        fr.rrect([x0 + 6, y0 + 10, x1 + 6, y0 + card_h + 10], 44, (230, 215, 208), k * 0.6)
        fr.rrect([x0, y0, x1, y0 + card_h], 44, CARD_BG, k)
    # one or more spends, each on its own sentence (cues[1], cues[2], ...); tomorrow re-adjusts after each
    spends = sp.get("spends") or [{"label": sp["spend_label"], "amount": sp["spend"], "tomorrow": sp["tomorrow"]}]
    sk = [appear(t, cues[1 + i] if 1 + i < len(cues) else 3.0 + 2 * i, 0.4) for i in range(len(spends))]
    def adj_at(i):                        # tomorrow updates near the end of that spend's sentence (when it's said)
        st = cues[1 + i] if 1 + i < len(cues) else 3.0 + 2 * i
        nx = cues[2 + i] if 2 + i < len(cues) else None
        return max(st + 1.4, nx - 1.8) if nx is not None and sp.get("spends") else st + 1.4
    ak = [appear(t, adj_at(i), 0.5) for i in range(len(spends))]
    ov_k = sk[0]; spent = sum(x["amount"] for x, k2 in zip(spends, sk) if k2 > 0.5)
    fr.text((x0 + 50, y0 + 50), "THIS WEEK", font("b", 28), GREY, k, dy=0)
    fr.text((x1 - 50, y0 + 38), f"${sp['week']:,}", font("xb", 52), INK, k, anchor="ra", dy=0)
    used = 0.35 + sum(0.26 / len(spends) * k2 for k2 in sk)
    fr.rrect([x0 + 50, y0 + 120, x1 - 50, y0 + 150], 15, (240, 232, 228), k)
    fr.rrect([x0 + 50, y0 + 120, x0 + 50 + (x1 - x0 - 100) * used, y0 + 150], 15, ORANGE if ov_k < 0.5 else RED, k)
    ty = y0 + 200
    fr.rrect([x0 + 50, ty, W / 2 - 15, ty + 220], 30, (255, 243, 237), k)
    fr.text((x0 + 80, ty + 30), "TODAY", font("b", 26), GREY, k, dy=0)
    today_col = INK if ov_k < 0.5 else RED
    fr.text((x0 + 80, ty + 80), f"${sp['today']}", font("xb", 84), today_col, k, dy=0)
    if ov_k > 0 and spent > sp["today"]: fr.text((x0 + 80, ty + 182), f"${spent - sp['today']} over", font("b", 26), RED, ov_k, dy=0)
    fr.rrect([W / 2 + 15, ty, x1 - 50, ty + 220], 30, (255, 243, 237), k)
    fr.text((W / 2 + 45, ty + 30), "TOMORROW", font("b", 26), GREY, k, dy=0)
    last = max([i for i, a in enumerate(ak) if a > 0] or [-1])
    if last >= 0:
        fr.text((W / 2 + 45, ty + 80), f"${spends[last]['tomorrow']}", font("xb", 84), ORANGE, ak[last])
        fr.text((W / 2 + 45, ty + 182), "adjusted", font("b", 26), ORANGE, ak[0], dy=0)
    else:
        fr.text((W / 2 + 45, ty + 80), f"${sp['today']}", font("xb", 84), INK, k * (1 - ov_k * 0.6))
    # spend chips, stacked
    n = len(spends); ch = 90 if n == 1 else 80; gap = 16
    for i, x in enumerate(spends):
        cy = y0 + 470 + i * (ch + gap)
        fr.rrect([x0 + 50, cy, x1 - 50, cy + ch], ch / 2, (253, 232, 228), sk[i])
        fr.text((x0 + 90, cy + ch / 2), x["label"], font("b", 34), INK, sk[i], anchor="lm", dy=0)
        fr.text((x1 - 90, cy + ch / 2), f"${x['amount']}", font("xb", 38), RED, sk[i], anchor="rm", dy=0)
    tag = 1 + len(spends)
    if len(cues) > tag:
        fr.text((W / 2, 1215 + (n - 1) * (ch + gap)), "Before you spend. Not after.", font("xb", 50), ORANGE, appear(t, cues[tag]), anchor="ma")
    character(fr.layer, W / 2, 1300, 900, t, mouth, "neutral", appear(t, 0.3) * fr.g, spec["character"])

def payoff_scene(fr, t, sp, cues, mouth, spec):
    logo(fr, W / 2, 150, 70, appear(t, 0.2))
    title_lines(fr, sp["title"], 290, t, 0.3, 88)
    y = 560
    for i, s in enumerate(sp["checks"]):
        st = cues[i] if i < len(cues) else 0.6 + i * 0.6; k = appear(t, st)
        fr.rrect([154, y + i * 150 + 8, W - 146, y + i * 150 + 128], 60, (236, 222, 215), k * 0.7)
        fr.rrect([150, y + i * 150, W - 150, y + i * 150 + 120], 60, WHITE, k)
        check_icon(fr, 225, y + i * 150 + 60, 36, k)
        fr.text((290, y + i * 150 + 60), s, font("xb", 52), INK, k, anchor="lm", dy=0)
    character(fr.layer, W / 2, 1080, 1000, t, mouth, "happy", appear(t, 0.3) * fr.g, spec["character"])

def plan_scene(fr, t, sp, cues, mouth, spec):
    """The four numbers: income and fixed bills (checked against bank history), savings (you pick),
    safe-to-spend (what's left). One stacked bar fills segment by segment; no arithmetic on screen."""
    logo(fr, W / 2, 150, 70, appear(t, 0.2))
    title_lines(fr, sp["title"], 290, t, 0.3, 84)
    rows = sp["rows"]; total = rows[0]["amount"]; x0, x1, by = 110, W - 110, 540
    cols = [INK, (150, 140, 136), ORANGE, GREEN, RED]      # a 5th row (e.g. "Flexible spending lately", "bar": false) is red
    k0 = appear(t, cues[0] if cues else 0.6)
    fr.rrect([x0, by, x1, by + 56], 28, (240, 232, 228), appear(t, 0.6))
    # segments are plain rectangles drawn on their own layer, then clipped to one rounded bar so they join cleanly
    seg = Image.new("RGBA", fr.layer.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(seg)
    k1 = appear(t, cues[1] if len(cues) > 1 else 9)
    if k0 > 0 and k1 < 1:                                        # income fills the bar, then hands over to the split
        sd.rectangle([x0 * S, by * S, (x0 + (x1 - x0) * k0) * S, (by + 56) * S], fill=cols[0] + (int(fr.a(k0) * (1 - k1)),))
    xs = x0
    for i, r in enumerate(rows[1:], 1):
        if r.get("bar") is False: continue
        ki = appear(t, cues[i] if i < len(cues) else 2.0 + i, 0.5)
        wseg = (x1 - x0) * r["amount"] / total
        if ki > 0: sd.rectangle([xs * S, by * S, (xs + wseg * ki) * S + 1, (by + 56) * S], fill=cols[i] + (fr.a(ki),))
        xs += wseg
    mask = Image.new("L", fr.layer.size, 0); ImageDraw.Draw(mask).rounded_rectangle([x0 * S, by * S, x1 * S, (by + 56) * S], 28 * S, fill=255)
    seg.putalpha(Image.fromarray(np.minimum(np.asarray(seg.split()[3]), np.asarray(mask))))
    fr.layer.alpha_composite(seg)
    y = by + 110
    for i, r in enumerate(rows):
        ki = appear(t, cues[i] if i < len(cues) else 2.0 + i)
        if ki <= 0: continue
        fr.rrect([x0, y, x1, y + 120], 36, WHITE, ki)
        fr.ellipse([(x0 + 40) , (y + 46), (x0 + 68), (y + 74)] , cols[i] + (fr.a(ki),))
        fr.text((x0 + 95, y + 30), r["label"], font("xb", 42), INK, ki, dy=0)
        fr.text((x0 + 95, y + 82), r.get("tag", ""), font("b", 26), GREEN if "bank" in r.get("tag", "") else GREY, ki, dy=0)
        fr.text((x1 - 40, y + 60), f"${r['amount']:,}", font("xb", 52), cols[i] if i else INK, ki, anchor="rm", dy=0)
        y += 140
    character(fr.layer, W / 2, 1300 + 120, 780, t, mouth, "neutral", appear(t, 0.3) * fr.g, spec["character"])

# ---------- rendered ending (replaces body part 2 when "ending": "rendered") ----------
ENDING = {
    "guarantee": {"narration": ["Try DivvyUpp for ninety days.",
                                "If you don't save more or spend less, we refund your subscription, up to thirty dollars.",
                                "Terms apply."]},
    "cta": {"narration": ["[warm] Save first. Then spend with confidence.", "Try it at divvyupp dot com."]},
}

def guarantee_scene(fr, t, sp, cues, mouth, spec):
    logo(fr, W / 2, 150, 70, appear(t, 0.2))
    k = appear(t, 0.3, 0.6); cx, cy, r = W / 2, 560, 250 * (0.85 + 0.15 * k)
    if k > 0:
        fr.ellipse([cx - r - 18, cy - r - 18, cx + r + 18, cy + r + 18], (250, 222, 210) + (fr.a(k),))
        fr.ellipse([cx - r, cy - r, cx + r, cy + r], ORANGE + (fr.a(k),))
        fr.d.ellipse([(cx - r + 22) * S, (cy - r + 22) * S, (cx + r - 22) * S, (cy + r - 22) * S], outline=(255, 255, 255, int(fr.a(k) * 0.55)), width=4 * S)
        fr.text((cx, cy - 40), "90", font("xb", 200), WHITE, k, anchor="mm", dy=0)
        fr.text((cx, cy + 92), "DAY", font("xb", 52), WHITE, k, anchor="mm", dy=0)
        fr.text((cx, cy + 140), "GUARANTEE", font("xb", 32), WHITE, k, anchor="mm", dy=0)
    c = lambda i, d=9.0: cues[i] if i < len(cues) else d
    fr.text((W / 2, 900), "Use DivvyUpp for 90 days.", font("b", 54), INK, appear(t, c(0)), anchor="ma")
    fr.text((W / 2, 1000), "If you don't save more", font("xb", 58), INK, appear(t, c(1)), anchor="ma")
    fr.text((W / 2, 1072), "or spend less,", font("xb", 58), ORANGE, appear(t, c(1) + 0.3), anchor="ma")
    fr.text((W / 2, 1172), "we refund your subscription,", font("b", 50), INK, appear(t, c(1) + 1.6), anchor="ma")
    fr.text((W / 2, 1236), "up to $30.", font("b", 50), INK, appear(t, c(1) + 1.9), anchor="ma")
    fr.text((W / 2, 1340), "Terms apply. See divvyupp.com for details.", font("m", 26), GREY, appear(t, c(2)), anchor="ma")

def cta_scene(fr, t, sp, cues, mouth, spec):
    c = lambda i, d=9.0: cues[i] if i < len(cues) else d
    fr.text((W / 2, 520), "Save first.", font("xb", 96), INK, appear(t, c(0)), anchor="ma")
    fr.text((W / 2, 630), "Then spend with", font("xb", 72), ORANGE, appear(t, c(0) + 0.7), anchor="ma")
    fr.text((W / 2, 714), "confidence.", font("xb", 72), ORANGE, appear(t, c(0) + 0.9), anchor="ma")
    k = appear(t, c(1) - 0.2)
    logo(fr, W / 2, 860, 110, k)
    fr.text((W / 2, 1020), "divvyupp.com", font("b", 46), INK, k, anchor="ma")
    k2 = appear(t, c(1) + 0.5)
    fr.rrect([200, 1130, W - 200, 1240], 55, ORANGE, k2)
    fr.text((W / 2, 1185), "Try the 90-day guarantee", font("xb", 40), WHITE, k2, anchor="mm", dy=0)
    k3 = appear(t, c(1) + 0.8)
    fr.rrect([200, 1270, W - 200, 1370], 50, (255, 238, 230), k3)
    fr.text((W / 2, 1320), "Try live demo, no signup", font("b", 36), ORANGE, k3, anchor="mm", dy=0)

SCENES = {"hook": hook_scene, "plan": plan_scene, "guide": guide_scene, "payoff": payoff_scene,
          "guarantee": guarantee_scene, "cta": cta_scene}

XFADE = 0.3   # seconds of dissolve between scenes (no dip to an empty background)

def render_segment(name, spec, tmp, bg, check_dir=None, last=False):
    sp = spec[name]; voice = spec.get("character_voice", "af_heart")
    plan = ONE_TAKE.get("plan")
    if plan and name in plan["frames"]:
        f0, f1, cues, phon = plan["frames"][name]; sr = plan["sr"]
        n = (f1 - f0) + (0 if last else round(XFADE * FPS))            # run on through the dissolve into the next scene
        total = n / FPS; audio = plan["audio"][int(f0 / FPS * sr):int((f0 / FPS + total) * sr)]
        env = mouth_env(np.concatenate([np.zeros(int(LEAD * sr)), audio]), sr, total)
    else:
        wav = os.path.join(tmp, f"{name}.wav")
        dur, cues, sr, audio, phon = narrate(sp["narration"], voice, wav)
        total = LEAD + dur + TAIL; n = round(total * FPS); env = mouth_env(audio, sr, total)
    vis = viseme_track(phon, n) if phon else None
    def draw(f):
        tt = f / FPS; fr = Frame(bg, tt, total)
        fr.g = min(min(1.0, tt / 0.35) if name == "hook" else 1.0, min(1.0, (total - tt) / 0.35) if last else 1.0)   # fade only at the very start/end
        SCENES[name](fr, tt, sp, cues, vis[min(f, n - 1)] if vis else env[min(f, n - 1)], spec); return fr.img()
    if check_dir:
        f = next((i for i, v in enumerate(vis or []) if v in ("A", "E")), int((total - 1.0) * FPS)); draw(f).save(os.path.join(check_dir, f"{spec['id']}_check_{name}.jpg"), quality=85)
        return None
    mp4 = os.path.join(tmp, f"{name}.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", mp4], stdin=subprocess.PIPE)
    for f in range(n): p.stdin.write(draw(f).tobytes())
    p.stdin.close(); assert p.wait() == 0
    seg = np.zeros(int(round(n / FPS * sr))); s = int(LEAD * sr); seg[s:s + len(audio)] = audio[:len(seg) - s]
    return mp4, seg, sr

def body_part(tmp, a, b, name):
    out = os.path.join(tmp, name + ".mp4"); src = os.path.join(HERE, "assets", "body_video.mp4")
    args = ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(a), "-i", src] + (["-t", str(b - a)] if b else []) + \
           ["-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out]
    subprocess.run(args, check=True)
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out]))
    return out, dur

def main():
    import soundfile as sf
    spec_path = sys.argv[1]; check = "--check" in sys.argv
    spec = json.load(open(spec_path)); rid = spec["id"]
    os.makedirs(os.path.join(ROOT, "reels"), exist_ok=True); tmp = os.path.join(CACHE, "tmp_" + rid); os.makedirs(tmp, exist_ok=True)
    bg = make_bg()
    if spec.get("ending") == "rendered":
        for name in ("guarantee", "cta"): spec.setdefault(name, ENDING[name])
    if spec.get("character_voice", "").startswith("elevenlabs:") and spec.get("one_take", True):
        one_take(spec, [n for n in ("hook", "plan", "guide", "payoff", "guarantee", "cta") if n in spec], tmp)
    if check:
        if spec.get("ending") == "rendered":
            for name in ("guarantee", "cta"): spec.setdefault(name, ENDING[name])
        for name in [n for n in ("hook", "plan", "guide", "payoff", "guarantee", "cta") if n in spec]: render_segment(name, spec, tmp, bg, os.path.join(ROOT, "reels"))
        print("check frames written"); return
    body, sr = sf.read(os.path.join(HERE, "assets", "body_audio.flac"))
    rendered_end = spec.get("ending") == "rendered"   # same-voice guarantee + CTA instead of the old body part 2
    skip_flip = spec.get("skip_flip", False) or "plan" in spec   # true: go straight from the hook to the guide
    cut = int(round(BODY_SPLIT * sr)); b1_a = body[:cut]; b2_a = body[cut:]
    def fit(a, d): n = int(round(d * sr)); return np.pad(a, (0, max(0, n - len(a))))[:n]
    order = ["hook"] + (["plan"] if "plan" in spec else []) + ([] if skip_flip else ["body1"]) + ["guide", "payoff"] + \
            (["guarantee", "cta"] if rendered_end else ["body2"])
    clips = []                                           # (video path, audio aligned to the clip's frames)
    for i, name in enumerate(order):
        if name == "body1": v, d = body_part(tmp, 0, BODY_SPLIT, "body1"); clips.append((v, fit(b1_a, d)))
        elif name == "body2": v, d = body_part(tmp, BODY_SPLIT, None, "body2"); clips.append((v, fit(b2_a, d)))
        else: v, a, _ = render_segment(name, spec, tmp, bg, last=(i == len(order) - 1)); clips.append((v, a * 0.95))
    plan = ONE_TAKE.get("plan")
    if plan and [n for n in order if n in plan["frames"]] == order:
        audio = plan["audio"] * 0.95                                    # the uncut take: no audio edits at all
        starts = [plan["frames"][n][0] / FPS for n in order]
        if spec.get("music", True):
            from music import mix_under
            audio = mix_under(audio, sr)
        sf.write(os.path.join(tmp, "full.wav"), audio, sr)
        inputs, fc, prev = [], [], "0:v"
        for v, _ in clips: inputs += ["-i", v]
        for i in range(1, len(clips)):
            fc.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XFADE}:offset={starts[i]:.4f}[x{i}]"); prev = f"x{i}"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", ";".join(fc), "-map", f"[{prev}]", "-r", str(FPS),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", os.path.join(tmp, "v.mp4")], check=True)
        out = os.path.join(ROOT, "reels", rid + ".mp4"); part = out + ".part.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(tmp, "v.mp4"), "-i", os.path.join(tmp, "full.wav"), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", part], check=True)
        os.replace(part, out); print("wrote", out); return
    # audio: overlap-add each join by XFADE (the overlap is the silent tail/lead of the scenes, so speech never collides)
    X = int(XFADE * sr); audio = clips[0][1].copy()
    for _, a in clips[1:]:
        ramp = np.linspace(0, 1, X); head = a[:X] * ramp; audio[-X:] = audio[-X:] * (1 - ramp) + head
        audio = np.concatenate([audio, a[X:]])
    if spec.get("music", True):
        from music import mix_under
        audio = mix_under(audio, sr)
    sf.write(os.path.join(tmp, "full.wav"), audio, sr)
    # video: dissolve between scenes with xfade; offsets follow the same overlap as the audio
    durs = [len(a) / sr for _, a in clips]; inputs = []; fc = []; prev = "0:v"; t = durs[0]
    for v, _ in clips: inputs += ["-i", v]
    for i in range(1, len(clips)):
        off = t - XFADE; lab = f"x{i}"
        fc.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XFADE}:offset={off:.4f}[{lab}]"); prev = lab; t = off + durs[i]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", ";".join(f"[{i}:v]fps={FPS},settb=AVTB,setpts=PTS-STARTPTS[s{i}]" for i in range(len(clips))).replace("", "") if False else ";".join(fc),
                    "-map", f"[{prev}]", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", os.path.join(tmp, "v.mp4")], check=True)
    out = os.path.join(ROOT, "reels", rid + ".mp4"); part = out + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(tmp, "v.mp4"), "-i", os.path.join(tmp, "full.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", part], check=True)
    os.replace(part, out); print("wrote", out)

if __name__ == "__main__": main()
