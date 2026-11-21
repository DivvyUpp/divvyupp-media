"""Render a "rules" Reel: a speaker (Dollar Bill or a presenter) at the bottom, lip-synced to one uncut ElevenLabs take,
with wrong-way / right-way rule pairs popping in above, inside the Instagram safe area. Same pop, count-up, click and
narration-tightening machinery as make_split_reel.py.

Usage:  python3 pipeline/make_rules_reel.py hooks/<id>.json [--check [--zones]]
Spec:
{ "id": "...", "character": "raccoon_soft3d", "character_voice": "elevenlabs:<voice>:eleven_v3", "voice_prefix": "...",
  "music": true, "speed": 1.1, "max_gap": 0.32, "keep_gap": {"7": 0.6},
  "sentences": ["...", ...],
  "title": [{"from": 0, "lines": [["Fourth takeout", "ink"], ["this week?", "orange"]]}, ...],   # big text, top area
  "header": [{"from": 2, "text": "Dollar Bill's rules"}, ...],                                   # small heading once rules start
  "pairs": [{"left": "...", "right": "...", "good": "left|right", "at": 2, "label": "Rule 1"}, ...],
  "moods": [{"from": 0, "mood": "unimpressed"}, ...],
  "note": {"text": "...", "at": 0}, "cta_lines": [...], "cta_at": 7 }
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from make_reel import W, H, FPS, S, CACHE, INK, GREY, ORANGE, WHITE, font, appear, Frame, logo, make_bg
from make_story_reel import LEAD, TAIL, character, viseme_track, LETTER_PHONEME
from make_explainer import one_take
from make_beat_reel import v_cta, fit, mark, wrap, GREEN, RED
from make_split_reel import SAFE_TOP, SAFE_BOT, SAFE_L, ZONES, tighten, click, sprite, place, pop_scale, COLS

SOFT_G = (226, 244, 233); SOFT_R = (250, 228, 224)
PAIRS_TOP, PAIRS_BOT, PAIRS_R = 470, 1130, W - 80      # rule rows end above the button rail (y>=1150)
SPK_TOP, SPK_H = 1170, 700                             # speaker at the bottom; may run into covered areas

def card(w, h, text, ok):
    def paint(f):
        f.rrect([0, 0, w, h], 26, SOFT_G if ok else SOFT_R, 1)
        size = min(44, h * 0.29); lines = wrap(f, text, "b", size, w - 110)[:3]
        lh = size * 1.22; y0 = h / 2 - lh * len(lines) / 2 + lh / 2
        for i, l in enumerate(lines):
            f.text((24, y0 + i * lh), l, font("b", size), INK if ok else GREY, 1, anchor="lm", dy=0)
        mark(f, w - 46, h / 2, 26, "check" if ok else "x", 1)
    return sprite(("card", round(w), round(h), text, ok), w, h, paint)

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
    phon, tag = [], False
    for c, a, b in zip(ch, st, en):
        if c == "[": tag = True
        if not tag and b > 0: phon.append((LEAD + a, LEAD + b, LETTER_PHONEME.get(c.lower(), " ")))
        if c == "]": tag = False
    total = LEAD + len(audio) / sr + TAIL; n = round(total * FPS)
    vis = viseme_track(phon, n)
    def cue(i, d=0.0): return cues[min(i, len(cues) - 1)] - 0.12 + d
    def phase(lst, t, key):
        cur = None
        for p in lst or []:
            if p["from"] == 0 or t >= cue(p["from"]): cur = p[key]     # the opening text is on screen from frame 1
        return cur
    bg = make_bg(); cta_t = cue(spec["cta_at"], -0.08) if spec.get("cta_at") is not None else total + 1
    def draw(f):
        t = f / FPS; fr = Frame(bg, t, total); fr.g = min(1.0, (total - t) / 0.35)
        if t >= cta_t:
            v_cta(fr, t - cta_t, {"lines": spec.get("cta_lines")}, []); return fr.img()
        logo(fr, W / 2, 140, 56, 1)                                   # decorative; sits under the header area
        title = phase(spec.get("title"), t, "lines"); header = phase(spec.get("header"), t, "text")
        if title:
            size = min(fit(fr, s_, "xb", 92, W - 2 * SAFE_L - 20) for s_, _ in title); y = SAFE_TOP + 40
            for s_, c in title:
                fr.text((W / 2, y), s_, font("xb", size), COLS.get(c, INK), 1, anchor="ma", dy=0); y += size * 1.15
        elif header:
            size = fit(fr, header, "xb", 64, W - 2 * SAFE_L)
            fr.text((W / 2, SAFE_TOP + 40), header, font("xb", size), INK, 1, anchor="ma", dy=0)
        # rule pairs
        prs = spec.get("pairs", []); shown = [p for p in prs if t >= cue(p["at"], p.get("delay", 0.0))]
        if shown and not title:
            rh = min(170, (PAIRS_BOT - PAIRS_TOP - 14 * (len(prs) - 1)) / len(prs)); cw = (PAIRS_R - SAFE_L - 20) / 2
            for j, p in enumerate(prs):
                t_in = cue(p["at"], p.get("delay", 0.0))
                if t < t_in: continue
                y = PAIRS_TOP + j * (rh + 14); age = t - t_in
                for side in ("left", "right"):
                    ok = side == p.get("good", "right"); x = SAFE_L if side == "left" else SAFE_L + cw + 20
                    a2 = age - (0.18 if ok else 0.0)                    # the ✓ side lands a beat after the ✗
                    if a2 < 0: continue
                    place(fr, card(cw, rh, p[side], ok), x + cw / 2, y + rh / 2, pop_scale(a2, ok), appear(t, t_in + (0.18 if ok else 0), 0.12))
        mood = phase(spec.get("moods"), t, "mood") or "happy"
        character(fr.layer, W / 2, SPK_TOP, SPK_H, t, vis[min(f, n - 1)], mood, fr.g, spec["character"])
        nt = spec.get("note")
        if nt and t >= cue(nt["at"]):
            for j, l in enumerate(wrap(fr, nt["text"], "b", 22, 420)[:2]):
                fr.text((SAFE_L, SAFE_BOT - 54 + j * 28), l, font("b", 22), INK, 1, dy=0)
        return fr.img()
    if check:
        for j, tt in enumerate([0.1] + [c + 1.2 for c in cues]):
            if tt >= total: continue
            im = draw(int(tt * FPS))
            if "--zones" in sys.argv:
                from PIL import ImageDraw
                im = im.convert("RGBA"); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                for r in ZONES: d.rectangle(r, fill=(255, 0, 0, 80))
                im = Image.alpha_composite(im, ov).convert("RGB")
            im.save(os.path.join(ROOT, "reels", f"{rid}_check_{j}.jpg"), quality=85)
        print("check frames written"); return
    full = np.concatenate([np.zeros(int(LEAD * sr)), audio, np.zeros(int(TAIL * sr))]) * 0.95
    if spec.get("music", True):
        from music import mix_under
        full = mix_under(full, sr)
    if spec.get("clicks", True):
        tk = click(sr, spec.get("click_gain", 0.06))
        for p in spec.get("pairs", []):
            for d_ in (0.0, 0.18):
                i0 = int(max(cue(p["at"], p.get("delay", 0.0) + d_), 0) * sr)
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
