"""Render a "Real Numbers" Reel: the diagram format (make_diagram_reel.py: cream background, section titles, karaoke
captions, Style C characters) plus elements for the founder's REAL app screenshots, and an upbeat music bed.
First used for Real Numbers ep 01 (hooks/2026-11-28-real-numbers-01.json, Srini 2026-11-28).

Extra elements (boxes are in the screenshot's 921-wide layout units, whatever the file's resolution):
  phone   x y w h shots:[{src, y0, blur:[[x0,y0,x1,y1]], at, spot:[{box, at}]}] [tag]
          a phone frame; each shot after the first SWIPES in from the right on its "at"; the status bar is cropped
          (region starts at y0, default 100); blur boxes hide sensitive amounts; a spot dims the screen except its
          box, with an orange ring. An orange "REAL SCREENSHOT" tag sits on the frame.
  stat    x y w h label value at [col] [s] [sub] [accent]   big-number tile (the number is the visual)
  mchip   x y w h label value at [col] [sub]                 small month tile (label left, value right)
  plan    x y w rows:[{label, value, from, col, at}]         plan card; "from" is struck through, then an arrow

Screenshots: "src" is an absolute path or a path relative to the repo root. Keep raw screenshots in private/
(git-ignored): they show income and balances. Only the rendered video, with blur boxes applied, is ever committed.
Music: spec "music": false turns the upbeat bed off (default on).

Usage:  python3 pipeline/make_realnumbers_reel.py hooks/<id>.json [--check | --at t1 t2 ... | --cover]
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import make_diagram_reel as D
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

S, F, INK, ORANGE, GREY, WHITE, RED = D.S, D.F, D.INK, D.ORANGE, D.GREY, D.WHITE, D.RED
GREEN = (30, 140, 80)
COLS = dict(D.COLS, green=GREEN, red=RED)
APP_BG = (244, 243, 241)
_C = {}

def shot_img(src, y0, blur, w, h):
    key = (src, y0, tuple(map(tuple, blur)), w, h)
    if key not in _C:
        im = Image.open(src if os.path.isabs(src) else os.path.join(ROOT, src)).convert("RGB"); K = im.width / 921
        for b in blur:
            box = tuple(int(v * K) for v in b); reg = im.crop(box).filter(ImageFilter.GaussianBlur(int(16 * K)))
            im.paste(Image.blend(reg, Image.new("RGB", reg.size, (228, 228, 231)), 0.35), box)
        region_h = h * 921 / w
        im = im.crop((0, int(y0 * K), im.width, int(min(im.height, (y0 + region_h) * K))))
        _C[key] = im.resize((int(w * S), int(h * S)), Image.LANCZOS).convert("RGBA")
    return _C[key]

def e_phone(cv, e, t, T):
    k = T.k(e, t)
    if k <= 0: return
    x, y, w, h = e["x"], e["y"], e["w"], e["h"]; bz = 11
    cv.shadow([x - bz, y - bz, x + w + bz, y + h + bz], 44, k, blur=30, dy=18, alpha=0.18)
    cv.rect([x - bz, y - bz, x + w + bz, y + h + bz], 44, fill=INK, k=k)
    shots = e["shots"]; st = [T.anchor(s_.get("at", 0)) if i else -1.0 for i, s_ in enumerate(shots)]
    i = max(j for j in range(len(shots)) if t >= st[j])
    can = Image.new("RGBA", (int(w * S), int(h * S)), APP_BG + (255,))
    p = D.ease((t - st[i]) / 0.42) if i > 0 else 1.0
    def put(sh, dx): can.alpha_composite(shot_img(sh["src"], sh.get("y0", 100), sh.get("blur", []), w, h), (int(dx * S), 0))
    if p < 1: put(shots[i - 1], -p * w)
    put(shots[i], (1 - p) * w)
    sh = shots[i]; sc = w / 921; y0 = sh.get("y0", 100)
    spots = [b for b in sh.get("spot", []) if t >= T.anchor(b.get("at", 0))]
    if spots and p >= 1:
        ks = max(D.ease((t - T.anchor(b.get("at", 0))) / 0.3) for b in spots)
        ov = Image.new("RGBA", can.size, (21, 16, 15, int(115 * ks))); d = ImageDraw.Draw(ov)
        boxes = [[b["box"][0] * sc, (b["box"][1] - y0) * sc, b["box"][2] * sc, (b["box"][3] - y0) * sc] for b in spots]
        for b in boxes: d.rounded_rectangle([v * S for v in b], int(10 * S), fill=(0, 0, 0, 0))
        can.alpha_composite(ov); d2 = ImageDraw.Draw(can)
        for b in boxes: d2.rounded_rectangle([(b[0] - 2) * S, (b[1] - 2) * S, (b[2] + 2) * S, (b[3] + 2) * S], int(12 * S), outline=ORANGE + (int(255 * ks),), width=int(4 * S))
    m = Image.new("L", can.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, can.width - 1, can.height - 1], int(34 * S), fill=int(255 * k * cv.g))
    can.putalpha(m); D.paste_rgba(cv, can, x, y)
    tag = e.get("tag", "REAL SCREENSHOT"); f = F("xb", 22); tw = cv.tl(tag, f); ty = y - bz - 22
    cv.rect([x + w / 2 - tw / 2 - 18, ty, x + w / 2 + tw / 2 + 18, ty + 40], 20, fill=ORANGE, k=k)
    cv.text(x + w / 2, ty + 20, tag, f, WHITE, k)

def e_mchip(cv, e, t, T):
    u = T.u(e, t, 0.4); k = T.fade(e, t) * D.clamp(u * 3)
    if k <= 0: return
    x, y, w, h = e["x"], e["y"] + (1 - D.back(u)) * 24, e["w"], e.get("h", 104)
    D.soft(cv, [x, y, x + w, y + h], 22, k); cv.rect([x, y, x + w, y + h], 22, fill=WHITE, k=k)
    if e.get("accent"): cv.rect([x, y, x + w, y + h], 22, outline=COLS.get(e.get("col", "ink"), INK), w=4, k=k)
    cv.text(x + 26, y + h / 2, e["label"], F("xb", 26), GREY, k, anchor="lm")
    cv.text(x + w - 24, y + h / 2 - (12 if e.get("sub") else 0), e["value"], F("xb", 44), COLS.get(e.get("col", "ink"), INK), k, anchor="rm")
    if e.get("sub"): cv.text(x + w - 24, y + h / 2 + 26, e["sub"], F("b", 22), COLS.get(e.get("col", "ink"), INK), k, anchor="rm")

def e_stat(cv, e, t, T):
    """A big-number tile: small label on top, a large value centred (the number is the visual, not the screenshot)."""
    u = T.u(e, t, 0.4); k = T.fade(e, t) * D.clamp(u * 3)
    if k <= 0: return
    x, y, w, h = e["x"], e["y"] + (1 - D.back(u)) * 24, e["w"], e["h"]; col = COLS.get(e.get("col", "ink"), INK)
    D.soft(cv, [x, y, x + w, y + h], 26, k); cv.rect([x, y, x + w, y + h], 26, fill=WHITE, k=k)
    if e.get("accent"): cv.rect([x, y, x + w, y + h], 26, outline=col, w=5, k=k)
    ls = e.get("ls", 26); vs = e.get("s", 64); sub = e.get("sub")
    total = ls + 14 + vs + (14 + 24 if sub else 0); top = y + (h - total) / 2
    cv.text(x + w / 2, top + ls / 2, e["label"], F("xb", ls), GREY, k)
    cv.text(x + w / 2, top + ls + 14 + vs / 2, e["value"], F("xb", vs), col, k)
    if sub: cv.text(x + w / 2, top + ls + 14 + vs + 14 + 12, sub, F("b", 24), col, k)

def e_plan(cv, e, t, T):
    x, y, w = e["x"], e["y"], e["w"]
    for r in e["rows"]:
        u = D.clamp((t - T.anchor(r.get("at", 0))) / 0.4) if t >= T.anchor(r.get("at", 0)) else 0.0
        k = D.clamp(u * 3) * T.fade(e, t); h = r.get("h", 170)
        if k > 0:
            yy = y + (1 - D.back(u)) * 26
            D.soft(cv, [x, yy, x + w, yy + h], 26, k); cv.rect([x, yy, x + w, yy + h], 26, fill=WHITE, k=k)
            cv.text(x + 40, yy + 46, r["label"], F("b", 34), GREY, k, anchor="lm")
            col = COLS.get(r.get("col", "ink"), INK); fv = F("xb", 60)
            if r.get("from"):
                ff = F("xb", 50); fw = cv.tl(r["from"], ff)
                cv.text(x + 40, yy + 112, r["from"], ff, GREY, k, anchor="lm")
                cv.line([(x + 34, yy + 114), (x + 46 + fw, yy + 114)], RED, 6, k)
                ax = x + 72 + fw; cv.line([(ax, yy + 112), (ax + 46, yy + 112)], GREY, 6, k)
                cv.line([(ax + 30, yy + 98), (ax + 46, yy + 112), (ax + 30, yy + 126)], GREY, 6, k)
                cv.text(x + 140 + fw, yy + 110, r["value"], fv, col, k, anchor="lm")
            else:
                cv.text(x + 40, yy + 110, r["value"], fv, col, k, anchor="lm")
        y += h + 22

D.DRAW.update(phone=e_phone, mchip=e_mchip, plan=e_plan, stat=e_stat)

# upbeat bed under the voice: make_diagram_reel writes the final voice mix to .../mix.wav; add the bed there
import soundfile as _sf
from music_upbeat import upbeat_bed
_write = _sf.write
def _write_with_bed(path, data, sr, *a, **k):
    if str(path).endswith("mix.wav"):
        v = np.asarray(data, float); bed = upbeat_bed(len(v) / sr, sr); bed = np.pad(bed, (0, max(0, len(v) - len(bed))))[:len(v)]
        wl = int(0.25 * sr); loud = np.convolve(np.abs(v), np.ones(wl) / wl, "same"); act = np.clip(loud / 0.03, 0, 1)
        sm = int(0.4 * sr); act = np.convolve(act, np.ones(sm) / sm, "same")
        data = v + bed * 1.6 * (1 - 0.5 * act); data = data / max(1.0, np.abs(data).max() / 0.98)
    return _write(path, data, sr, *a, **k)

if __name__ == "__main__":
    if json.load(open(sys.argv[1])).get("music", True): _sf.write = _write_with_bed
    D.main()
