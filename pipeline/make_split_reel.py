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

HALF = H // 2; BAND = 130
# Instagram Reels covered areas, measured on Srini's iPhone screenshot (2026-11-20, 1320x2868): the 9:16 video is
# scaled to fill the height, so ~55 px is cropped off each side; status bar/Reels header cover the top ~180 px;
# username + caption + "posts tagged" cover y>=1660 (full width); the like/comment/repost/send rail covers x>=905 from
# y~1150 down. All text and blocks stay inside; only background and the people run into covered areas.
SAFE_TOP, SAFE_BOT, SAFE_L, TEXT_R = 190, 1650, 80, 890
ZONES = [[0, 0, W, 180], [0, 1660, W, H], [905, 1150, W, 1660], [0, 0, 55, H], [W - 55, 0, W, H]]
MID = (SAFE_TOP + SAFE_BOT) // 2
COLS = {"green": GREEN, "red": RED, "orange": ORANGE, "white": WHITE, "ink": INK}

def bg_for(spec):
    bg = Image.new("RGBA", (W * S, H * S), (255, 250, 247, 255))
    for i, h in enumerate(spec["halves"]):
        tint = tuple(h.get("tint", (245, 240, 236)))
        y0, y1 = (0, MID) if i == 0 else (MID, H)
        bg.paste(Image.new("RGBA", (W * S, (y1 - y0) * S), tint + (255,)), (0, y0 * S))
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
    lab_f = font("b", min(26, h * 0.25)); val_size = min(58, h * (0.40 if not b.get("big") else 0.46))
    fr.text((x + 22, y + h * 0.10), b["label"].upper(), lab_f, (WHITE if st in ("good", "bad") else GREY), k, dy=8)
    vcol = txt if st != "minus" else RED
    fr.text((x + 22, y + h - h * 0.12), b["value"], font("xb", fit(fr, b["value"], "xb", val_size, w - 48)), vcol, k, anchor="ld", dy=8)
    if b.get("mark"): mark(fr, x + w - 40, y + h / 2, 22, b["mark"], k)
    if b.get("sub"):                     # short right-aligned note on the value row, e.g. "$100/day · $700/week"
        sc = COLS.get(b.get("sub_color", "green"), GREEN)
        fr.text((x + w - 22, y + h - 18), b["sub"], font("xb", fit(fr, b["sub"], "xb", min(30, h * 0.3), w * 0.55)), sc, k, anchor="rd", dy=8)

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
            r0, r1 = (SAFE_TOP, MID - BAND // 2 - 14) if i == 0 else (MID + BAND // 2 + 14, SAFE_BOT - (62 if spec.get("note") else 0))
            # person on the right; may run into the covered areas (no text there)
            if i == 0: pb, ph = MID - BAND // 2, MID - BAND // 2 - 40
            else: pb, ph = H, min(880, H - (MID + BAND // 2) - 20)
            p = person(h["person"], int(ph * S * (1 + 0.03 * t / total)))
            fr.layer.alpha_composite(p, (max(W * S - p.width + int(40 * S), int(W * 0.46 * S)), pb * S - p.height))
            # tag + result badge on one row at the top of the safe region
            tf = font("xb", 30); tw = fr.tl(h["tag"], tf); col = COLS.get(h.get("tag_color", "ink"), INK)
            fr.rrect([SAFE_L, r0, SAFE_L + tw + 44, r0 + 58], 29, col, 1); fr.text((SAFE_L + 22, r0 + 29), h["tag"], tf, WHITE, 1, anchor="lm", dy=0)
            bd = h.get("badge")
            if bd:
                k = appear(t, cue(bd["at"], bd.get("delay", 0.0)), 0.4); bx0 = SAFE_L + tw + 64
                bf = font("xb", fit(fr, bd["text"], "xb", 36, TEXT_R - bx0 - 40)); bwid = fr.tl(bd["text"], bf)
                fr.rrect([bx0, r0, bx0 + bwid + 40, r0 + 58], 29, WHITE, k)
                fr.text((bx0 + 20, r0 + 29), bd["text"], bf, COLS.get(bd["color"], INK), k, anchor="lm", dy=0)
            # blocks
            bx, bw = SAFE_L, 500; top = r0 + 72; bottom = r1
            nb = len(h["blocks"]); gap = 8; nbig = sum(1 for b in h["blocks"] if b.get("big"))
            bh = min(110, (bottom - top - gap * (nb - 1)) / (nb + 0.2 * nbig))
            yy = top
            for b in h["blocks"]:
                hh = bh * (1.2 if b.get("big") else 1.0)
                block(fr, bx, yy, bw, hh, b, appear(t, cue(b["at"], b.get("delay", 0.0)), 0.35))
                yy += hh + gap
        # centre band (full width as a stripe; text inside the safe width)
        fr.rrect([0, MID - BAND // 2, W, MID + BAND // 2], 0, INK, 1)
        band = spec["band"]; lines = band["lines"] if t < cue(band.get("until", 99)) else band.get("after", band["lines"])
        size = min(fit(fr, s_, "xb", 52, TEXT_R - SAFE_L) for s_, _ in lines)
        yy = MID - (len(lines) * size * 1.12) / 2 + size * 0.05
        for s_, c in lines:
            fr.text((W / 2, yy), s_, font("xb", size), COLS.get(c, WHITE), 1, anchor="ma", dy=0); yy += size * 1.12
        nt = spec.get("note")
        if nt:
            from make_beat_reel import wrap
            from make_beat_reel import wrap
            for j, l in enumerate(wrap(fr, nt["text"], "b", 22, 500)[:2]):
                fr.text((SAFE_L, SAFE_BOT - 54 + j * 28), l, font("b", 22), INK, appear(t, cue(nt["at"])), dy=0)
        return fr.img()
    if check:
        for j, tt in enumerate([0.1] + [c + 1.0 for c in cues]):
            if tt < total and "--zones" in sys.argv:
                from PIL import ImageDraw
                im = draw(int(tt * FPS)).convert("RGBA"); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                for r in ZONES: d.rectangle(r, fill=(255, 0, 0, 80))
                Image.alpha_composite(im, ov).convert("RGB").save(os.path.join(ROOT, "reels", f"{rid}_zones_{j}.jpg"), quality=85)
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
