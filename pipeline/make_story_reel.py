"""Render a DivvyUpp *story* Reel: an illustrated character tells the whole save-first story, with the
approved body spliced in where it explains the flip, then the guarantee and call to action.

Order: hook (character) -> body part 1 ("DivvyUpp flips the order", 0-12.4s) -> guide scene (daily/weekly
number that adjusts) -> payoff scene (bills paid, savings kept, still spending) -> body part 2 (guarantee + CTA).

Usage:  python3 pipeline/make_story_reel.py hooks/<id>.json          -> reels/<id>.mp4
        python3 pipeline/make_story_reel.py hooks/<id>.json --check  -> reels/<id>_check.jpg (one still per scene)

Spec (JSON):
{
  "id": "2026-11-15-a", "format": "story",
  "character": "c" (presenter id from characters.py), "character_voice": "af_heart", "name_tag": "" (optional),
  "hook":   {"small": "...", "lines": [["...", "ink"|"orange"], ...], "narration": ["..."]},
  "guide":  {"title": [["...", "ink"|"orange"], ...], "narration": ["..."],
             "week": 460, "today": 66, "spend_label": "Dinner out", "spend": 120, "tomorrow": 52},
  "payoff": {"title": [["...", "ink"|"orange"], ...], "checks": ["...", "...", "..."], "narration": ["..."]}
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
def narrate(sentences, voice, out_wav):
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
    from characters import sprite
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
        fr.text((W / 2, y), sp["small"], font("b", 66), INK, appear(t, cues[0]), anchor="ma"); y += 130
    title_lines(fr, sp["lines"], y, t, cues[0] + 0.5, 104)
    aside = sp.get("aside")               # {"text": "...", "cue": n}: a deadpan aside chip; the face turns unimpressed
    mood = "worried"
    if aside and aside["cue"] < len(cues):
        k2 = appear(t, cues[aside["cue"]], 0.35); mood = "unimpressed" if k2 > 0.3 else mood
        f = font("xb", 46); tw = fr.tl(aside["text"], f); ay = y + 2 * 118 + 40
        fr.rrect([W / 2 - tw / 2 - 36, ay, W / 2 + tw / 2 + 36, ay + 88], 44, INK, k2)
        fr.text((W / 2, ay + 44), aside["text"], f, WHITE, k2, anchor="mm", dy=0)
    character(fr.layer, W / 2, 820, 1150, t, mouth, mood, appear(t, 0.15) * fr.g, spec["character"])
    if spec.get("name_tag"):
        f = font("b", 30); tw = fr.tl(spec["name_tag"], f); kk = appear(t, 0.8)
        fr.rrect([W / 2 - tw / 2 - 28, 1680, W / 2 + tw / 2 + 28, 1744], 32, WHITE, kk)
        fr.text((W / 2, 1712), spec["name_tag"], f, INK, kk, anchor="mm", dy=0)

def guide_scene(fr, t, sp, cues, mouth, spec):
    logo(fr, W / 2, 150, 70, appear(t, 0.2))
    title_lines(fr, sp["title"], 290, t, 0.3, 84)
    # card
    k = appear(t, 0.6); x0, x1, y0 = 110, W - 110, 540
    if k > 0:
        fr.rrect([x0 + 6, y0 + 10, x1 + 6, y0 + 610], 44, (230, 215, 208), k * 0.6)
        fr.rrect([x0, y0, x1, y0 + 600], 44, CARD_BG, k)
    ov = cues[1] if len(cues) > 1 else 3.0          # overspend moment = 2nd sentence
    ov_k = appear(t, ov, 0.4); adj_k = appear(t, ov + 1.4, 0.5)
    fr.text((x0 + 50, y0 + 50), "THIS WEEK", font("b", 28), GREY, k, dy=0)
    fr.text((x1 - 50, y0 + 38), f"${sp['week']:,}", font("xb", 52), INK, k, anchor="ra", dy=0)
    used = 0.35 + 0.26 * ov_k
    fr.rrect([x0 + 50, y0 + 120, x1 - 50, y0 + 150], 15, (240, 232, 228), k)
    fr.rrect([x0 + 50, y0 + 120, x0 + 50 + (x1 - x0 - 100) * used, y0 + 150], 15, ORANGE if ov_k < 0.5 else RED, k)
    # today / tomorrow tiles
    ty = y0 + 200
    fr.rrect([x0 + 50, ty, W / 2 - 15, ty + 220], 30, (255, 243, 237), k)
    fr.text((x0 + 80, ty + 30), "TODAY", font("b", 26), GREY, k, dy=0)
    today_col = INK if ov_k < 0.5 else RED
    fr.text((x0 + 80, ty + 80), f"${sp['today']}", font("xb", 84), today_col, k, dy=0)
    if ov_k > 0: fr.text((x0 + 80, ty + 182), f"${sp['spend'] - sp['today']} over", font("b", 26), RED, ov_k, dy=0)
    fr.rrect([W / 2 + 15, ty, x1 - 50, ty + 220], 30, (255, 243, 237), k)
    fr.text((W / 2 + 45, ty + 30), "TOMORROW", font("b", 26), GREY, k, dy=0)
    if adj_k > 0:
        fr.text((W / 2 + 45, ty + 80), f"${sp['tomorrow']}", font("xb", 84), ORANGE, adj_k)
        fr.text((W / 2 + 45, ty + 182), "adjusted", font("b", 26), ORANGE, adj_k, dy=0)
    else:
        fr.text((W / 2 + 45, ty + 80), f"${sp['today']}", font("xb", 84), INK, k * (1 - ov_k * 0.6))
    # overspend chip
    cy = y0 + 470
    fr.rrect([x0 + 50, cy, x1 - 50, cy + 90], 45, (253, 232, 228), ov_k)
    fr.text((x0 + 90, cy + 45), sp["spend_label"], font("b", 36), INK, ov_k, anchor="lm", dy=0)
    fr.text((x1 - 90, cy + 45), f"${sp['spend']}", font("xb", 40), RED, ov_k, anchor="rm", dy=0)
    if len(cues) > 2:
        fr.text((W / 2, 1215), "Before you spend. Not after.", font("xb", 50), ORANGE, appear(t, cues[2]), anchor="ma")
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

SCENES = {"hook": hook_scene, "guide": guide_scene, "payoff": payoff_scene}

def render_segment(name, spec, tmp, bg, check_dir=None):
    sp = spec[name]; voice = spec.get("character_voice", "af_heart")
    wav = os.path.join(tmp, f"{name}.wav")
    dur, cues, sr, audio, phon = narrate(sp["narration"], voice, wav)
    total = LEAD + dur + TAIL; n = round(total * FPS); env = mouth_env(audio, sr, total)
    vis = viseme_track(phon, n) if phon else None
    def draw(f):
        tt = f / FPS; fr = Frame(bg, tt, total); SCENES[name](fr, tt, sp, cues, vis[min(f, n - 1)] if vis else env[min(f, n - 1)], spec); return fr.img()
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
    if check:
        for name in ("hook", "guide", "payoff"): render_segment(name, spec, tmp, bg, os.path.join(ROOT, "reels"))
        print("check frames written"); return
    body, sr = sf.read(os.path.join(HERE, "assets", "body_audio.flac"))
    hook_v, hook_a, _ = render_segment("hook", spec, tmp, bg)
    skip_flip = spec.get("skip_flip", False)   # true: go straight from the hook to the guide
    b1_v, b1_d = (None, 0) if skip_flip else body_part(tmp, 0, BODY_SPLIT, "body1")
    guide_v, guide_a, _ = render_segment("guide", spec, tmp, bg)
    pay_v, pay_a, _ = render_segment("payoff", spec, tmp, bg)
    b2_v, b2_d = body_part(tmp, BODY_SPLIT, None, "body2")
    cut = int(round(BODY_SPLIT * sr)); b1_a = body[:cut]; b2_a = body[cut:]
    def fit(a, d): n = int(round(d * sr)); return np.pad(a, (0, max(0, n - len(a))))[:n]
    audio = np.concatenate([hook_a * 0.95] + ([] if skip_flip else [fit(b1_a, b1_d)]) + [guide_a * 0.95, pay_a * 0.95, fit(b2_a, b2_d)])
    if spec.get("music", True):
        from music import mix_under
        audio = mix_under(audio, sr)
    sf.write(os.path.join(tmp, "full.wav"), audio, sr)
    open(os.path.join(tmp, "list.txt"), "w").write("".join(f"file '{v}'\n" for v in (hook_v, b1_v, guide_v, pay_v, b2_v) if v))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"), "-c", "copy", os.path.join(tmp, "v.mp4")], check=True)
    out = os.path.join(ROOT, "reels", rid + ".mp4"); part = out + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(tmp, "v.mp4"), "-i", os.path.join(tmp, "full.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", part], check=True)
    os.replace(part, out); print("wrote", out)

if __name__ == "__main__": main()
