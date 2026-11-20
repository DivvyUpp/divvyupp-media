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

HALF = H // 2; BAND = 150
COLS = {"green": GREEN, "red": RED, "orange": ORANGE, "white": WHITE, "ink": INK}

def bg_for(spec):
    bg = Image.new("RGBA", (W * S, H * S), (255, 250, 247, 255))
    for i, h in enumerate(spec["halves"]):
        tint = tuple(h.get("tint", (245, 240, 236)))
        bg.paste(Image.new("RGBA", (W * S, HALF * S), tint + (255,)), (0, i * HALF * S))
    return bg

_P = {}
def person(path, height):
    k = (path, height)
    if k not in _P:
        im = Image.open(path if os.path.isabs(path) else os.path.join(ROOT, path)).convert("RGBA")
        bb = im.getbbox(); im = im.crop(bb) if bb else im
        _P[k] = im.resize((int(im.width * height / im.height), height), Image.LANCZOS)
    return _P[k]

def block(fr, x, y, w, h, b, k):
    if k <= 0: return
    st = b.get("style", "plain")
    fill = {"good": GREEN, "bad": RED}.get(st, WHITE)
    txt = WHITE if st in ("good", "bad") else INK
    fr.rrect([x, y, x + w, y + h], 24, fill, k)
    lab_f = font("b", 26 if not b.get("big") else 28); val_size = 46 if not b.get("big") else 58
    fr.text((x + 24, y + 16), b["label"].upper(), lab_f, (WHITE if st in ("good", "bad") else GREY), k, dy=8)
    vcol = txt if st != "minus" else RED
    fr.text((x + 24, y + h - 14), b["value"], font("xb", fit(fr, b["value"], "xb", val_size, w - 48)), vcol, k, anchor="ld", dy=8)

def main():
    import soundfile as sf
    spec = json.load(open(sys.argv[1])); rid = spec["id"]; check = "--check" in sys.argv
    tmp = os.path.join(CACHE, "tmp_" + rid); os.makedirs(tmp, exist_ok=True)
    spec["beats"] = [{"sentences": [{"text": s} for s in spec["sentences"]]}]
    sents, starts, (ch, st, en), audio, sr = one_take(spec, tmp)
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
    def cue(i, d=0.0): return cues[min(i, len(cues) - 1)] - 0.12 + d
    def draw(f):
        t = f / FPS; fr = Frame(bg, t, total); fr.g = min(1.0, (total - t) / 0.35)
        if t >= cta_t:
            fr.bg = Image.new("RGBA", (W * S, H * S), (255, 250, 247, 255)); v_cta(fr, t - cta_t, {}, [])
            return fr.img()
        for i, h in enumerate(spec["halves"]):
            y0 = i * HALF
            # person on the right, bottom-aligned in the half, slow push-in
            top_y = y0 + (0 if i == 0 else BAND // 2); bot_y = y0 + HALF - (BAND // 2 if i == 0 else 0)
            p = person(h["person"], int((bot_y - top_y) * 0.96 * S * (1 + 0.03 * t / total)))
            fr.layer.alpha_composite(p, (max(W * S - p.width + int(40 * S), int(W * 0.40 * S)), bot_y * S - p.height))
            # tag
            tf = font("xb", 30); tw = fr.tl(h["tag"], tf); ty = y0 + (28 if i == 0 else BAND // 2 + 24)
            col = COLS.get(h.get("tag_color", "ink"), INK)
            fr.rrect([40, ty, 40 + tw + 44, ty + 58], 29, col, 1); fr.text((62, ty + 29), h["tag"], tf, WHITE, 1, anchor="lm", dy=0)
            # blocks
            bx, bw = 40, 510; top = ty + 78; bottom = y0 + HALF - (BAND // 2 if i == 0 else 0) - (16 if i == 0 else 70)
            nb = len(h["blocks"]); gap = 10; nbig = sum(1 for b in h["blocks"] if b.get("big"))
            bh = min(118, (bottom - top - gap * (nb - 1)) / (nb + 0.18 * nbig))
            yy = top
            for b in h["blocks"]:
                hh = bh * (1.18 if b.get("big") else 1.0)
                block(fr, bx, yy, bw, hh, b, appear(t, cue(b["at"], b.get("delay", 0.0)), 0.35))
                yy += hh + gap
            bd = h.get("badge")
            if bd:
                k = appear(t, cue(bd["at"], bd.get("delay", 0.0)), 0.4); bf = font("xb", 44); bwid = fr.tl(bd["text"], bf)
                by = y0 + HALF - (BAND // 2 if i == 0 else 0) - 110
                fr.rrect([W - bwid - 100, by, W - 40, by + 84], 42, COLS.get(bd["color"], INK), k)
                fr.text((W - 70 - bwid / 2 - 0, by + 42), bd["text"], bf, WHITE, k, anchor="mm", dy=0)
        # centre band
        fr.rrect([0, HALF - BAND // 2, W, HALF + BAND // 2], 0, INK, 1)
        band = spec["band"]; lines = band["lines"] if t < cue(band.get("until", 99)) else band.get("after", band["lines"])
        size = min(fit(fr, s_, "xb", 58, 1000) for s_, _ in lines)
        yy = HALF - (len(lines) * size * 1.12) / 2 + size * 0.05
        for s_, c in lines:
            fr.text((W / 2, yy), s_, font("xb", size), COLS.get(c, WHITE), 1, anchor="ma", dy=0); yy += size * 1.12
        nt = spec.get("note")
        if nt:
            from make_beat_reel import wrap
            for j, l in enumerate(wrap(fr, nt["text"], "m", 22, 500)[:2]):
                fr.text((42, H - 58 + j * 28), l, font("m", 22), GREY, appear(t, cue(nt["at"])), dy=0)
        return fr.img()
    if check:
        for j, tt in enumerate([0.1] + [c + 1.0 for c in cues]):
            if tt < total: draw(int(tt * FPS)).save(os.path.join(ROOT, "reels", f"{rid}_check_{j}.jpg"), quality=85)
        print("check frames written"); return
    full = np.concatenate([np.zeros(int(LEAD * sr)), audio, np.zeros(int(TAIL * sr))]) * 0.95
    if spec.get("music", True):
        from music import mix_under
        full = mix_under(full, sr)
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
