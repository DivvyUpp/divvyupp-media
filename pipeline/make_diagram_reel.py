"""Render a "diagram" Study Reel: a faceless explainer. One voice-over take, a cream background, a short section title
at the top, word-timed captions at the bottom, and animated diagrams that land on the words they illustrate.
No background music: a soft tick when something lands is the only sound besides the voice.

Usage:  python3 pipeline/make_diagram_reel.py hooks/<id>.json             -> reels/<id>.mp4
        python3 pipeline/make_diagram_reel.py hooks/<id>.json --check     -> reels/<id>_check.jpg (one still per scene,
                                                                             safe zones shaded red)
        python3 pipeline/make_diagram_reel.py hooks/<id>.json --at 1.2 4  -> reels/<id>_at.jpg (full-size stills)

Spec:
{ "id": "...", "voice": "elevenlabs:<voice id>:eleven_v3", "voice_settings": {...} (optional),
  "speed": 1.08, "max_gap": 0.3,                       # optional: faster take, pauses capped (seconds)
  "scenes": [
    { "title": "the *trap*",                            # top label; *word* is drawn orange
      "text": "Here's the trap. ...",                   # spoken; v3 audio tags are stripped from captions
      "speed": 1.2,                                     # optional: this scene's lines faster/slower than "speed"
      "keep_prev": true,                                # optional: the previous scene's diagram stays on screen
      "elements": [ {"type": "...", "at": "phrase" | seconds, ...}, ... ] } ] }

Element timing: "at" is a phrase from this scene's text (the element lands as that word starts) or seconds from the
scene start; default 0. Optional "until" (same forms) fades it out early. "instant": true skips the entrance.
Element types (coordinates are 1080x1920 frame pixels):
  text    x y text s w(m|b|xb|serif|serif_b) col(ink|orange|grey|muted|white) align(l|m|r) [strike: at] [pop]
  chip    x y text [style: quote|orange|ink|soft] [s]          a pill that springs in
  chart   x0 x1 base y [labels] [label] [dur] [flat_label]     a savings line that draws flat, area fill, live head
  card    x y w h [kicker] title [subtitle] [lines] [highlight: at]
  panel   x y w h [accent]                                     white tile with a soft shadow
  bars    base bars:[{x w h col label at}] [bracket:{a b label at}] [gain:{from to text at}] [note]
  lock    x y w h [time] notifs:[{text sub at}]                a lock-screen phone, notifications slide in
  target  x y r [hit: at]                                      bullseye, an arrow lands on the hit
  qring   x y r                                                dashed ring with a faded "?"
  accounts x y w h [title] rows:[{label from to swap}]         banking app; a rename strikes then types out
  avatar  x y r label
  curve   p0 p1 c [col] [dur]                                  dashed bezier that draws itself
  ticket  x y w h title [sub]
  clock   x y r [dur] [label]
  tag     x y lines:[{text style: ink|orange}] [s] [dx] [stagger]   series tag: stacked solid blocks slide in
  line    pts [col] [width] [dash] [dur]
  dot     x y [r] [col] [pulse]
  statement x y w h [issuer] [acct] [rows] [hl: at] [hl_row] [warnings]   card statement Payment Information box
  research x y                                                 study paper + magnifier sweep + $ coin pop (tip-tag intro)
  crowd   x y [cols rows h sp] [count suffix label] [dur] [moods]   rows of small figures popping in, number counts up
  couple  x y h [gap] [label label_col] [move:{at x dur}] [show: both|him|her] moods:[{at, him, her}] [labels:[l, r]] [q]   Style C couple (Srini picked
          2026-11-26), sprites from pipeline/couple_sprites.js; moods happy|neutral|worried|sad|confused|frustrated; a mood
          change gives a little bounce; q draws an orange "?" over confused faces
Spec options (2026-11-26, Srini): "cap_style": "karaoke" draws the spoken words in a dark box, the current word on an
orange pill and upcoming words dimmed, so captions read as speech, not as part of the diagram. A scene's
"cap_split": "sentence" keeps whole sentences together (up to "cap_max" words, default 12; a sentence of 5 words or fewer joins the one before) so a still frame such as
the cover carries the full thought. "--cover" writes reels/<id>_cover.jpg at the spec's "cover_at" ([scene, phrase]).
Every element must sit outside the Instagram safe zones (PLAYBOOK checklist 10); --check shades them red.
"""
import json, math, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from make_scene_reel import speak, SR, font as _font  # noqa: E402  (ElevenLabs with-timestamps, cached)

W, H, FPS, S = 1080, 1920, 30, 2
INK = (21, 16, 15); GREY = (112, 106, 101); MUTED = (208, 200, 191); ORANGE = (224, 74, 26); WHITE = (255, 255, 255)
CREAM = (249, 245, 239); TINT = (252, 226, 212); TINT2 = (247, 196, 170); HILITE = (255, 210, 180); LINE = (226, 219, 211)
RED = (205, 45, 35)
COLS = {"ink": INK, "orange": ORANGE, "grey": GREY, "muted": MUTED, "white": WHITE}
LEAD, TAIL = 0.08, 0.9
TITLE_Y, CAP_Y, CAP_CX, CAP_W = 300, 1545, 480, 800
SERIF = {"serif": "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
         "serif_b": "/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf"}
_sf, _shadow = {}, {}

def F(w, s):
    """Font at supersampled size. w: m|b|xb (Plus Jakarta Sans) or serif|serif_b (Georgia italic)."""
    if w in SERIF:
        k = (w, int(s))
        if k not in _sf:
            path = SERIF[w]
            if not os.path.exists(path):  # Linux (cloud runs): Liberation Serif has the same metrics family
                path = "/usr/share/fonts/truetype/liberation/LiberationSerif-%s.ttf" % ("BoldItalic" if w == "serif_b" else "Italic")
            _sf[k] = ImageFont.truetype(path, int(s * S))
        return _sf[k]
    return _font(w, s * S)

def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3
def back(x, s=1.9): x = clamp(x) - 1; return x * x * ((s + 1) * x + s) + 1
def mix(a, b, u): return tuple(int(p + (q - p) * clamp(u)) for p, q in zip(a, b))
def norm(w): return re.sub(r"[^a-z0-9%]", "", w.lower().replace("’", "'"))
def strip_tags(s): return re.sub(r"\[[^\]]*\]\s*", "", s).strip()

class Canvas:
    def __init__(self):
        self.im = Image.new("RGB", (W * S, H * S), CREAM); self.d = ImageDraw.Draw(self.im, "RGBA"); self.g = 1.0
    def c(self, col, k=1.0): return tuple(col[:3]) + (int(255 * clamp(k) * self.g),)
    def text(self, x, y, s, f, col, k=1.0, anchor="mm", rise=0):
        if k > 0 and s: self.d.text((x * S, (y + (1 - ease(k)) * rise) * S), s, font=f, fill=self.c(col, k), anchor=anchor)
    def tl(self, s, f): return self.d.textlength(s, font=f) / S
    def line(self, pts, col, w, k=1.0, caps=True):
        if k <= 0 or len(pts) < 2: return
        self.d.line([(x * S, y * S) for x, y in pts], fill=self.c(col, k), width=max(1, int(w * S)), joint="curve")
        if caps:
            for x, y in (pts[0], pts[-1]): self.circle(x, y, w / 2, fill=col, k=k)
    def circle(self, x, y, r, fill=None, outline=None, w=2, k=1.0):
        if k > 0 and r > 0: self.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S],
                                           fill=self.c(fill, k) if fill else None, outline=self.c(outline, k) if outline else None, width=int(w * S))
    def rect(self, b, r, fill=None, outline=None, w=2, k=1.0):
        if k > 0: self.d.rounded_rectangle([v * S for v in b], int(r * S), fill=self.c(fill, k) if fill else None,
                                           outline=self.c(outline, k) if outline else None, width=int(w * S))
    def poly(self, pts, col, k=1.0):
        if k > 0 and len(pts) > 2: self.d.polygon([(x * S, y * S) for x, y in pts], fill=self.c(col, k))
    def pie(self, x, y, r, a0, a1, col, k=1.0):
        if k > 0: self.d.pieslice([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], a0, a1, fill=self.c(col, k))
    def shadow(self, b, r, k=1.0, blur=22, dy=12, alpha=0.13):
        """A soft drop shadow under box b (cached blurred mask)."""
        if k <= 0: return
        w, h = int(b[2] - b[0]), int(b[3] - b[1]); key = (w, h, int(r), blur)
        if key not in _shadow:
            m = Image.new("L", ((w + 4 * blur) * S, (h + 4 * blur) * S), 0)
            ImageDraw.Draw(m).rounded_rectangle([2 * blur * S, 2 * blur * S, (2 * blur + w) * S, (2 * blur + h) * S], int(r * S), fill=255)
            _shadow[key] = m.filter(ImageFilter.GaussianBlur(blur * S / 2))
        a = alpha * clamp(k) * self.g; m = _shadow[key].point(lambda v: int(v * a))
        self.im.paste((40, 25, 15), (int((b[0] - 2 * blur) * S), int((b[1] - 2 * blur + dy) * S)), m)
    def out(self): return self.im.reduce(S)

def partial(pts, frac):
    """The first `frac` of a polyline, by length."""
    if frac >= 1: return pts
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]; L = sum(seg) * max(frac, 0); out = [pts[0]]
    for i, s in enumerate(seg):
        if L <= s:
            a, b = pts[i], pts[i + 1]; u = L / s if s else 0
            out.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)); return out
        L -= s; out.append(pts[i + 1])
    return out

def dashed(cv, pts, col, w, k, on=16, off=12):
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if L == 0: continue
        u = 0.0
        while u < L:
            ph = (acc + u) % (on + off)
            if ph < on:
                v = min(L, u + on - ph)
                cv.line([(a[0] + (b[0] - a[0]) * u / L, a[1] + (b[1] - a[1]) * u / L), (a[0] + (b[0] - a[0]) * v / L, a[1] + (b[1] - a[1]) * v / L)], col, w, k, caps=False)
                u = v
            else: u = min(L, u + on + off - ph)
        acc += L

def bezier(p0, c, p1, n=40):
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u * u * p1[0], (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u * u * p1[1])
            for u in np.linspace(0, 1, n)]

def rich(cv, x, y, s, size, k, base=INK):
    """Centered text where *words* are orange (section titles)."""
    parts = re.split(r"(\*[^*]+\*)", s); f = F("xb", size); total = sum(cv.tl(p.strip("*"), f) for p in parts); cx = x - total / 2
    for p in parts:
        col = ORANGE if p.startswith("*") else base; p = p.strip("*")
        cv.text(cx, y, p, f, col, k, anchor="lm"); cx += cv.tl(p, f)

def wrap(cv, s, f, maxw):
    lines, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if cv.tl(t, f) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    return lines + ([cur] if cur else [])

# ---------------- elements ----------------
def e_text(cv, e, t, T):
    k = T.k(e, t); f = F(e.get("w", "b"), e.get("s", 44)); col = COLS.get(e.get("col", "ink"), INK)
    st = T.at(e, "strike")
    if st is not None and t >= st: col = mix(col, GREY, ease((t - st) / 0.3))
    anchor = {"l": "lm", "m": "mm", "r": "rm"}[e.get("align", "m")]
    if e.get("pop"):
        sz = e.get("s", 44) * (0.6 + 0.4 * back(T.u(e, t, 0.45))); f = F(e.get("w", "b"), sz)
        cv.text(e["x"], e["y"], e["text"], f, col, min(1, k * 2), anchor=anchor)
    else: cv.text(e["x"], e["y"], e["text"], f, col, k, anchor=anchor, rise=e.get("rise", 16))
    if st is not None and t >= st:
        w = cv.tl(e["text"], f); x0 = {"l": e["x"], "m": e["x"] - w / 2, "r": e["x"] - w}[e.get("align", "m")]
        cv.line([(x0 - 8, e["y"]), (x0 - 8 + (w + 16) * ease((t - st) / 0.35), e["y"])], RED, max(4, e.get("s", 44) / 10), k)

def e_chip(cv, e, t, T):
    u = T.u(e, t, 0.45); k = T.fade(e, t) * clamp(u * 3)
    if k <= 0: return
    style = e.get("style", "quote"); s = e.get("s", 40)
    w_ = {"quote": "serif", "orange": "xb", "ink": "xb", "soft": "b"}[style]; f = F(w_, s)
    sc = 0.55 + 0.45 * back(u); tw = cv.tl(e["text"], f); pw, ph = (tw + 2.0 * s) * sc, s * 2.1 * sc
    x, y = e["x"], e["y"]; b = [x - pw / 2, y - ph / 2, x + pw / 2, y + ph / 2]
    fill, tc = {"quote": (WHITE, INK), "orange": (ORANGE, WHITE), "ink": (INK, WHITE), "soft": (TINT, ORANGE)}[style]
    if style in ("quote", "orange"): cv.shadow(b, ph / 2, k, blur=16, dy=8, alpha=0.12)
    cv.rect(b, ph / 2, fill=fill, k=k)
    cv.text(x, y + (2 if w_ != "serif" else 0), e["text"], F(w_, s * sc), tc, k)

def e_tag(cv, e, t, T):
    """Series tag: solid blocks (white text on ink / orange) that stack, staggered, one after another."""
    k0 = T.fade(e, t); s = e.get("s", 54); f = F("xb", s); ph = s * 1.75; gap = e.get("gap", 10); dx = e.get("dx", 70)
    lines = e["lines"]; n = len(lines); y_top = e["y"] - (n * ph + (n - 1) * gap) / 2
    for i, ln in enumerate(lines):
        u = clamp((t - T.t_in(e) - i * e.get("stagger", 0.14)) / 0.38)
        if e.get("instant"): u = 1.0
        if u <= 0 or k0 <= 0: continue
        tw = cv.tl(ln["text"], f); pw = tw + s * 1.1
        cx = e["x"] + (i - (n - 1) / 2) * dx                     # staggered: each block shifts right
        side = -1 if i % 2 == 0 else 1; slide = (1 - back(u, 1.4)) * 260 * side
        x0 = cx - pw / 2 + slide; y0 = y_top + i * (ph + gap); k = k0 * clamp(u * 4)
        fill = ORANGE if ln.get("style") == "orange" else INK
        cv.shadow([x0, y0, x0 + pw, y0 + ph], 12, k, blur=14, dy=8, alpha=0.18)
        cv.rect([x0, y0, x0 + pw, y0 + ph], 12, fill=fill, k=k)
        cv.text(x0 + pw / 2, y0 + ph / 2 + 2, ln["text"], f, WHITE, k)

def e_chart(cv, e, t, T):
    k = T.fade(e, t); x0, x1, base, y = e["x0"], e["x1"], e["base"], e["y"]; labels = e.get("labels", [])
    if k <= 0: return
    for gy in e.get("grid", []): dashed(cv, [(x0, gy), (x1, gy)], LINE, 2, k, on=8, off=10)
    cv.line([(x0, base), (x1, base)], MUTED, 3, k, caps=False)
    n = len(labels)
    for i, l in enumerate(labels):
        x = x0 + (x1 - x0) * i / max(n - 1, 1); cv.line([(x, base - 8), (x, base + 8)], MUTED, 3, k, caps=False)
        cv.text(x, base + 40, l, F("b", 30), GREY, k)
    if e.get("label"): cv.text(x0, e.get("label_y", y - 230), e["label"], F("xb", 38), INK, k, anchor="lm")
    frac = ease(T.u(e, t, e.get("dur", 0.9)))
    pts = [(x0 + (x1 - x0) * i / 40, y + 3 * math.sin(i * 1.3) * (i % 3 == 0)) for i in range(41)]
    p = partial(pts, frac)
    if frac > 0:
        cv.poly(p + [(p[-1][0], base), (x0, base)], ORANGE, k * 0.10)
        cv.line(p, ORANGE, 11, k)
        hx, hy = p[-1]; ph = ((t - T.t_in(e)) % 1.3) / 1.3
        cv.circle(hx, hy, 18 + 30 * ph, fill=ORANGE, k=k * 0.28 * (1 - ph)); cv.circle(hx, hy, 15, fill=ORANGE, k=k)
        cv.circle(hx, hy, 6, fill=WHITE, k=k)

def e_card(cv, e, t, T):
    u = T.u(e, t, 0.5); k = T.fade(e, t) * clamp(u * 2.5)
    if k <= 0: return
    x, y, w, h = e["x"], e["y"] + (1 - back(u)) * 40, e["w"], e["h"]
    cv.shadow([x, y, x + w, y + h], 18, k); cv.rect([x, y, x + w, y + h], 18, fill=WHITE, k=k)
    cv.rect([x, y, x + 10, y + h], 0, fill=ORANGE, k=k)
    cy = y + 58
    if e.get("kicker"): cv.text(x + 50, cy, e["kicker"], F("xb", 26), GREY, k, anchor="lm"); cy += 78
    tf = F("serif_b", e.get("title_s", 58)); tw = cv.tl(e["title"], tf); hl = T.at(e, "highlight")
    if hl is not None and t >= hl: cv.rect([x + 42, cy - 36, x + 42 + (tw + 18) * ease((t - hl) / 0.55), cy + 34], 6, fill=HILITE, k=k)
    cv.text(x + 50, cy, e["title"], tf, INK, k, anchor="lm"); cy += 62
    if e.get("subtitle"): cv.text(x + 50, cy, e["subtitle"], F("serif", 38), INK, k, anchor="lm"); cy += 74
    for i, l in enumerate(e.get("lines", [])): cv.text(x + 50, cy + i * 46, l, F("b" if i == 0 else "m", 30), INK if i == 0 else GREY, k, anchor="lm")

def e_panel(cv, e, t, T):
    u = T.u(e, t, 0.45); k = T.fade(e, t) * clamp(u * 2.5)
    if k <= 0: return
    x, y, w, h = e["x"], e["y"] + (1 - back(u)) * 36, e["w"], e["h"]
    cv.shadow([x, y, x + w, y + h], 24, k); cv.rect([x, y, x + w, y + h], 24, fill=WHITE, k=k)
    if e.get("accent"): cv.rect([x, y, x + w, y + h], 24, outline=ORANGE, w=4, k=k)

def e_bars(cv, e, t, T):
    k = T.fade(e, t); base = e["base"]
    if k <= 0: return
    tops = []
    for b in e["bars"]:
        if b.get("ghost"): tops.append(base - b["h"]); continue       # geometry only (drawn by an earlier scene)
        tb = T.anchor(b.get("at", 0)); g = 1.0 if b.get("instant") else back(clamp((t - tb) / 0.8), 1.2) if t >= tb else 0
        h = b["h"] * g; x, w = b["x"], b["w"]; col = COLS.get(b.get("col", "muted"), MUTED); tops.append(base - b["h"])
        if g > 0:
            cv.rect([x, base - h, x + w, base], 16, fill=col, k=k); cv.rect([x, base - min(h, 16), x + w, base], 0, fill=col, k=k)
        lk = k * clamp((t - tb) / 0.3) if not b.get("instant") else k
        for i, l in enumerate(b.get("label", "").split("\n")): cv.text(x + w / 2, base + 36 + i * 40, l, F("b", 32), GREY, lk)
    cv.line([(e.get("x0", 90), base), (e.get("x1", 990), base)], INK, 3, k, caps=False)
    br = e.get("bracket")
    if br and t >= T.anchor(br["at"]):
        u = ease((t - T.anchor(br["at"])) / 0.5); a, b = e["bars"][br["a"]], e["bars"][br["b"]]; yb = min(tops[br["a"]], tops[br["b"]]) - 34
        xa, xb = a["x"] + a["w"] / 2, b["x"] + b["w"] / 2; xm = (xa + xb) / 2; half = (xb - xa) / 2 * u
        cv.line([(xm - half, yb), (xm + half, yb)], GREY, 4, k)
        cv.line([(xm - half, yb), (xm - half, yb + 18 * u)], GREY, 4, k); cv.line([(xm + half, yb), (xm + half, yb + 18 * u)], GREY, 4, k)
        cv.text(xm, yb - 44, br["label"], F("xb", 46), GREY, k * u)
    gn = e.get("gain")
    if gn and t >= T.anchor(gn["at"]):
        u = clamp((t - T.anchor(gn["at"])) / 0.9); a, b = e["bars"][gn["from"]], e["bars"][gn["to"]]
        ya, yb = tops[gn["from"]], tops[gn["to"]]
        dashed(cv, [(a["x"] + a["w"], ya), (a["x"] + a["w"] + (b["x"] + b["w"] - a["x"] - a["w"]) * ease(u * 1.5), ya)], ORANGE, 3, k, on=10, off=8)
        val = int(round(gn["value"] * ease(u)))
        cv.text(b["x"] + b["w"] / 2, yb - 58, gn["text"].replace("{v}", str(val)), F("xb", 70 * (0.8 + 0.2 * back(u))), ORANGE, k * clamp(u * 3))
    if e.get("note") and t >= T.anchor(e["note"]["at"]):
        cv.text(e["note"].get("x", 480), e["note"]["y"], e["note"]["text"], F("m", 28), GREY, k * ease((t - T.anchor(e["note"]["at"])) / 0.4))

_wall = {}
def e_lock(cv, e, t, T):
    u = T.u(e, t, 0.5); k = T.fade(e, t) * clamp(u * 2.5)
    if k <= 0: return
    x, y, w, h = e["x"], e["y"] + (1 - back(u)) * 50, e["w"], e["h"]; r = 64
    cv.shadow([x, y, x + w, y + h], r, k, blur=30, dy=20, alpha=0.18); cv.rect([x, y, x + w, y + h], r, fill=INK, k=k)
    key = (w, h)
    if key not in _wall:
        iw, ih = (w - 28) * S, (h - 28) * S; gy = np.linspace(0, 1, ih)[:, None, None]
        top, bot = np.array((70, 48, 40), float), np.array((205, 92, 50), float)
        arr = (top * (1 - gy) + bot * gy).repeat(iw, axis=1).astype("uint8"); wall = Image.fromarray(arr, "RGB")
        m = Image.new("L", (iw, ih), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, iw - 1, ih - 1], (r - 14) * S, fill=255)
        _wall[key] = (wall, m)
    wall, m = _wall[key]
    cv.im.paste(wall, (int((x + 14) * S), int((y + 14) * S)), m.point(lambda v: int(v * clamp(k) * cv.g)))
    cv.rect([x + w / 2 - 70, y + 34, x + w / 2 + 70, y + 66], 16, fill=INK, k=k)
    cv.text(x + w / 2, y + 150, e.get("date", "Monday, March 3"), F("b", 28), WHITE, k * 0.85)
    cv.text(x + w / 2, y + 230, e.get("time", "9:41"), F("xb", 120), WHITE, k)
    ny = y + 360
    for i, n in enumerate(e["notifs"]):
        tn = T.anchor(n["at"])
        if t < tn: continue
        v = clamp((t - tn) / 0.45); yy = ny + i * 132 - (1 - back(v)) * 60; kk = k * clamp(v * 3)
        b = [x + 30, yy, x + w - 30, yy + 116]; cv.rect(b, 28, fill=(255, 250, 246), k=kk * 0.94)
        cv.rect([b[0] + 20, yy + 26, b[0] + 84, yy + 90], 16, fill=ORANGE, k=kk)
        cv.line([(b[0] + 52, yy + 40), (b[0] + 52, yy + 66)], WHITE, 6, kk); cv.circle(b[0] + 52, yy + 77, 4, fill=WHITE, k=kk)
        cv.text(b[0] + 104, yy + 42, n.get("app", "REMINDER"), F("b", 22), GREY, kk, anchor="lm")
        cv.text(b[2] - 24, yy + 42, n.get("when", "now"), F("m", 22), GREY, kk, anchor="rm")
        cv.text(b[0] + 104, yy + 80, n["text"], F("xb", 32), INK, kk, anchor="lm")

def e_target(cv, e, t, T):
    u = T.u(e, t, 0.5); k = T.fade(e, t) * clamp(u * 2.5)
    if k <= 0: return
    x, y, r = e["x"], e["y"], e["r"] * (0.7 + 0.3 * back(u))
    for rr, col in [(1.0, TINT), (0.7, TINT2), (0.42, ORANGE)]: cv.circle(x, y, r * rr, fill=col, k=k)
    cv.circle(x, y, r * 0.16, fill=WHITE, k=k)
    hit = T.at(e, "hit")
    if hit is not None and t >= hit - 0.35:
        v = ease(clamp((t - hit + 0.35) / 0.35)); sx, sy = x + r * 1.5, y - r * 1.5; hx, hy = sx + (x - sx) * v, sy + (y - sy) * v
        L = math.dist((sx, sy), (x, y)); dx, dy = (x - sx) / L, (y - sy) / L; px, py = -dy, dx   # flight direction, normal
        tx, ty = hx - dx * L * 0.55, hy - dy * L * 0.55                                          # tail end of the shaft
        cv.line([(tx, ty), (hx - dx * 20, hy - dy * 20)], INK, 7, k)
        cv.poly([(hx, hy), (hx - dx * 34 + px * 16, hy - dy * 34 + py * 16), (hx - dx * 34 - px * 16, hy - dy * 34 - py * 16)], INK, k)
        for s_ in (1, -1):                                                                        # fletching at the tail
            cv.poly([(tx + dx * 6, ty + dy * 6), (tx - dx * 18 + px * 16 * s_, ty - dy * 18 + py * 16 * s_), (tx - dx * 28, ty - dy * 28)], ORANGE, k)
        if v >= 1:
            ph = clamp((t - hit) / 0.6); cv.circle(x, y, r * (0.2 + 0.9 * ph), outline=ORANGE, w=5, k=k * (1 - ph))

def e_qring(cv, e, t, T):
    u = T.u(e, t, 0.5); k = T.fade(e, t) * clamp(u * 2.5)
    if k <= 0: return
    x, y, r = e["x"], e["y"], e["r"] * (0.85 + 0.15 * ease(u)); n = 36
    for i in range(0, n, 2):
        a0, a1 = 2 * math.pi * i / n + t * 0.3, 2 * math.pi * (i + 1) / n + t * 0.3
        cv.line([(x + r * math.cos(a), y + r * math.sin(a)) for a in np.linspace(a0, a1, 5)], MUTED, 6, k)
    cv.text(x, y + 6, "?", F("xb", r * 0.9), MUTED, k)

def e_accounts(cv, e, t, T):
    u = T.u(e, t, 0.5); k = T.fade(e, t) * clamp(u * 2.5)
    if k <= 0: return
    x, y, w, h = e["x"], e["y"] + (1 - back(u)) * 50, e["w"], e["h"]; r = 64
    cv.shadow([x, y, x + w, y + h], r, k, blur=30, dy=20, alpha=0.16); cv.rect([x, y, x + w, y + h], r, fill=INK, k=k)
    cv.rect([x + 14, y + 14, x + w - 14, y + h - 14], r - 14, fill=(250, 248, 246), k=k)
    cv.rect([x + w / 2 - 70, y + 34, x + w / 2 + 70, y + 66], 16, fill=INK, k=k)
    cv.text(x + 56, y + 140, e.get("title", "Accounts"), F("xb", 50), INK, k, anchor="lm")
    ry = y + 210
    for row in e["rows"]:
        b = [x + 40, ry, x + w - 40, ry + 190]; cv.shadow(b, 24, k, blur=12, dy=6, alpha=0.08); cv.rect(b, 24, fill=WHITE, k=k)
        sw = T.anchor(row["swap"]) if row.get("swap") is not None else None; done = sw is not None and t >= sw + 0.3
        cv.circle(b[0] + 62, ry + 95, 32, fill=TINT if done else LINE, k=k)
        cv.text(b[0] + 62, ry + 97, row.get("icon", "$"), F("xb", 30), ORANGE if done else GREY, k)
        cv.text(b[0] + 118, ry + 58, row["label"], F("b", 24), GREY, k, anchor="lm")
        f = F("xb", row.get("s", 44)); tx, ty = b[0] + 118, ry + 118
        if sw is None or t < sw + 0.3:
            cv.text(tx, ty, row["from"], f, INK, k, anchor="lm")
            if sw is not None and t >= sw:
                fw = cv.tl(row["from"], f); cv.line([(tx - 4, ty), (tx - 4 + (fw + 8) * ease((t - sw) / 0.3), ty)], RED, 5, k)
        else:
            full = row["to"]; nch = int(len(full) * clamp((t - sw - 0.3) / max(0.25, 0.045 * len(full)))); s_ = full[:nch]
            cv.text(tx, ty, s_, f, ORANGE, k, anchor="lm")
            if nch < len(full) or int(t * 2.4) % 2 == 0:
                cx = tx + cv.tl(s_, f) + 4; cv.line([(cx, ty - 26), (cx, ty + 26)], ORANGE, 4, k, caps=False)
        ry += 214

def e_avatar(cv, e, t, T):
    u = T.u(e, t, 0.45); k = T.fade(e, t) * clamp(u * 3)
    if k <= 0: return
    x, y, r = e["x"], e["y"], e.get("r", 80) * (0.6 + 0.4 * back(u)); col = TINT if e.get("tone") != "ink" else MUTED
    cv.shadow([x - r, y - r, x + r, y + r], r, k, blur=14, dy=8, alpha=0.10)
    cv.circle(x, y, r, fill=col, k=k); cv.circle(x, y - r * 0.22, r * 0.3, fill=ORANGE if e.get("tone") != "ink" else INK, k=k)
    cv.d.pieslice([(x - r * 0.55) * S, (y + r * 0.18) * S, (x + r * 0.55) * S, (y + r * 1.1) * S], 180, 360,
                  fill=cv.c(ORANGE if e.get("tone") != "ink" else INK, k))
    cv.text(x, y + r + 44, e["label"], F("xb", 38), INK, k)

def e_curve(cv, e, t, T):
    k = T.fade(e, t); frac = ease(T.u(e, t, e.get("dur", 0.7)))
    if frac <= 0 or k <= 0: return
    pts = partial(bezier(tuple(e["p0"]), tuple(e["c"]), tuple(e["p1"])), frac)
    dashed(cv, pts, COLS.get(e.get("col", "orange"), ORANGE), 5, k, on=14, off=10)

def e_ticket(cv, e, t, T):
    u = T.u(e, t, 0.5); k = T.fade(e, t) * clamp(u * 2.5)
    if k <= 0: return
    sc = 0.7 + 0.3 * back(u); w, h = e["w"] * sc, e["h"] * sc; x, y = e["x"] - w / 2, e["y"] - h / 2
    cv.shadow([x, y, x + w, y + h], 26, k, blur=22, dy=12, alpha=0.16); cv.rect([x, y, x + w, y + h], 26, fill=ORANGE, k=k)
    for cx in (x, x + w): cv.circle(cx, y + h / 2, 22 * sc, fill=CREAM, k=k)
    cv.text(x + w / 2, y + h * 0.42, e["title"], F("xb", 56 * sc), WHITE, k)
    if e.get("sub"): cv.text(x + w / 2, y + h * 0.74, e["sub"], F("b", 28 * sc), (255, 222, 205), k)

def e_clock(cv, e, t, T):
    u = T.u(e, t, 0.45); k = T.fade(e, t) * clamp(u * 3)
    if k <= 0: return
    x, y, r = e["x"], e["y"], e.get("r", 60) * (0.6 + 0.4 * back(u)); f = ease(T.u(e, t, e.get("dur", 1.2)))
    cv.circle(x, y, r, fill=WHITE, outline=INK, w=5, k=k)
    # The sweep completes the full circle: a clock that stops short reads as "not done" (Srini, 2026-11-25).
    if f > 0: cv.pie(x, y, r - 6, -90, -90 + 360 * f, TINT2, k)
    a = math.radians(-90 + 360 * f); cv.line([(x, y), (x + (r - 16) * math.cos(a), y + (r - 16) * math.sin(a))], INK, 5, k)
    cv.circle(x, y, 6, fill=INK, k=k)
    if e.get("label"): cv.text(x, y + r + 40, e["label"], F("xb", 36), ORANGE, k)

def e_line(cv, e, t, T):
    k = T.fade(e, t); pts = [tuple(p) for p in e["pts"]]
    frac = 1 if e.get("instant") else ease(T.u(e, t, e.get("dur", 0.7)))
    if frac <= 0: return
    p = partial(pts, frac); col = COLS.get(e.get("col", "ink"), INK)
    if e.get("dash"): dashed(cv, p, col, e.get("width", 4), k)
    else: cv.line(p, col, e.get("width", 4), k)

def e_statement(cv, e, t, T):
    """A US credit-card statement's Payment Information box, the part people recognise: New Balance, Minimum Payment
    Due, Payment Due Date, then the Late Payment / Minimum Payment Warnings in small print. "hl" highlights the
    minimum row (orange marker sweep) on a phrase. Generic issuer, no real bank's name or logo."""
    u = T.u(e, t, 0.5); k = T.fade(e, t) * clamp(u * 2.5)
    if k <= 0: return
    x, y, w, h = e["x"], e["y"] + (1 - back(u)) * 40, e["w"], e["h"]
    cv.shadow([x, y, x + w, y + h], 6, k, blur=26, dy=16, alpha=0.16); cv.rect([x, y, x + w, y + h], 6, fill=WHITE, k=k)
    NAVY = (24, 44, 84); RULE = (196, 201, 210); SMALL = (88, 92, 100)
    pad = 44; cy = y + 52
    cv.rect([x + pad, cy - 22, x + pad + 62, cy + 18], 6, fill=NAVY, k=k)            # generic card chip/logo
    cv.rect([x + pad + 10, cy - 8, x + pad + 30, cy + 6], 3, fill=(214, 182, 96), k=k)
    cv.text(x + pad + 84, cy - 2, e.get("issuer", "Credit Card Statement"), F("xb", 30), NAVY, k, anchor="lm")
    cv.text(x + w - pad, cy - 2, e.get("acct", "Account ending in 4821"), F("m", 24), SMALL, k, anchor="rm")
    cy += 50; cv.line([(x + pad, cy), (x + w - pad, cy)], NAVY, 3, k, caps=False)
    cy += 46; cv.text(x + pad, cy, "Payment Information", F("xb", 34), INK, k, anchor="lm")
    cy += 28
    rows = e.get("rows", [["New Balance", "$3,482.17"], ["Minimum Payment Due", "$98.00"], ["Payment Due Date", "12/18/26"]])
    hl = T.at(e, "hl")
    for i, (a, b) in enumerate(rows):
        ry = cy + 36 + i * 72
        if i == e.get("hl_row", 1) and hl is not None and t >= hl:
            cv.rect([x + pad - 12, ry - 32, x + pad - 12 + (w - 2 * pad + 24) * ease((t - hl) / 0.5), ry + 32], 6, fill=HILITE, k=k)
        bold = i == e.get("hl_row", 1)
        cv.text(x + pad, ry, a, F("xb" if bold else "b", 36), INK, k, anchor="lm")
        cv.text(x + w - pad, ry, b, F("xb" if bold else "b", 36), INK, k, anchor="rm")
        cv.line([(x + pad, ry + 36), (x + w - pad, ry + 36)], RULE, 2, k, caps=False)
    cy += 36 + len(rows) * 72 + 10
    for head, body in e.get("warnings", [["Late Payment Warning:", "If we do not receive your minimum payment by the date listed above, you may have to pay a late fee."],
                                         ["Minimum Payment Warning:", "If you make only the minimum payment each period, you will pay more in interest and it will take you longer to pay off your balance."]]):
        f = F("m", 22); fb = F("xb", 22); lines = wrap(cv, head + " " + body, f, w - 2 * pad)
        for li, l in enumerate(lines):
            if li == 0 and l.startswith(head):
                cv.text(x + pad, cy, head, fb, INK, k, anchor="lm")
                cv.text(x + pad + cv.tl(head + " ", fb), cy, l[len(head):].strip(), f, SMALL, k, anchor="lm")
            else: cv.text(x + pad, cy, l, f, SMALL, k, anchor="lm")
            cy += 32
        cy += 12

def e_dot(cv, e, t, T):
    k = T.k(e, t)
    if k <= 0: return
    x, y = e["x"], e["y"]; col = COLS.get(e.get("col", "orange"), ORANGE); r = e.get("r", 13)
    if e.get("pulse"):
        ph = ((t - T.t_in(e)) % 1.4) / 1.4; cv.circle(x, y, r + 28 * ph, fill=col, k=k * 0.3 * (1 - ph))
    cv.circle(x, y, r * (0.5 + 0.5 * back(T.u(e, t, 0.4))), fill=col, k=k)

_spr = {}
def sprite(who, mood, h):
    k = (who, mood, int(h))
    if k not in _spr:
        im = Image.open(os.path.join(HERE, "assets", "characters", "couple_c", f"{who}_{mood}.png")).convert("RGBA")
        _spr[k] = im.resize((int(im.width * h * S / im.height), int(h * S)), Image.LANCZOS)
    return _spr[k]

def e_couple(cv, e, t, T):
    u = T.u(e, t, 0.5); k = T.fade(e, t) * clamp(u * 3)
    if k <= 0: return
    h, gap = e.get("h", 240), e.get("gap", e.get("h", 240) * 0.66); show = e.get("show", "both")
    cur, since = {"him": "neutral", "her": "neutral"}, {"him": -9.0, "her": -9.0}
    for m in e.get("moods", []):
        tm = T.anchor(m.get("at", 0))
        if t >= tm:
            for who in ("him", "her"):
                if who in m and m[who] != cur[who]: cur[who] = m[who]; since[who] = tm
    X = e["x"]
    if e.get("move"):                                       # slide to a new x, e.g. to make room for a second couple
        mv = e["move"]; X = X + (mv["x"] - X) * ease((t - T.anchor(mv["at"])) / mv.get("dur", 0.5))
    if e.get("label"): cv.text(X, e["y"] + h / 2 + 40, e["label"], F("xb", e.get("label_s", 32)), COLS.get(e.get("label_col", "ink"), INK), k)
    for i, who in enumerate(("him", "her")):
        if show not in ("both", who): continue
        cx = X + ((i - 0.5) * gap if show == "both" else 0)
        b = t - since[who]; bounce = math.sin(min(b / 0.35, 1) * math.pi) * 0.06 if 0 <= b < 0.35 else 0.0
        sc = (0.6 + 0.4 * back(u)) * (1 + bounce); hh = h * sc
        im = sprite(who, cur[who], hh)
        if k < 1: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * k)))
        x0, y0 = cx - im.width / S / 2, e["y"] + h / 2 - hh               # feet stay on the floor line
        cv.im.paste(im, (int(x0 * S), int(y0 * S)), im)
        if e.get("q") and cur[who] == "confused": cv.text(cx + hh * 0.33, y0 + hh * 0.12, "?", F("xb", hh * 0.16), ORANGE, k)
        if e.get("labels"): cv.text(cx, e["y"] + h / 2 + 40, e["labels"][i], F("xb", 38), INK, k)
    cv.d = ImageDraw.Draw(cv.im, "RGBA")

def e_crowd(cv, e, t, T):
    """Rows of small figures (him/her alternating) popping in one by one, with a number counting up above them."""
    k = T.fade(e, t)
    if k <= 0: return
    t0 = T.t_in(e); dur = e.get("dur", 1.6); cols, rows, h, sp = e.get("cols", 10), e.get("rows", 2), e.get("h", 90), e.get("sp", 78)
    n = cols * rows; moods = e.get("moods", ["neutral", "happy"])
    if e.get("count"):
        u = ease((t - t0) / dur); v = int(round(e["count"] * u / 50.0)) * 50
        txt = f"{v:,}" + (e.get("suffix", "") if u >= 0.999 else "")
        if t >= t0: cv.text(e["x"], e["y"] - 120, txt, F("xb", e.get("count_s", 96)), ORANGE, k)
        if e.get("label") and t >= t0: cv.text(e["x"], e["y"] - 50, e["label"], F("b", 36), GREY, k)
    for i in range(n):
        ti = t0 + dur * 0.85 * i / n; u = clamp((t - ti) / 0.3)
        if u <= 0: continue
        r, c = divmod(i, cols); who = "him" if (r + c) % 2 == 0 else "her"
        hh = h * (0.5 + 0.5 * back(u)); im = sprite(who, moods[(i * 7) % len(moods)], hh)
        if k < 1: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v_: int(v_ * k)))
        cx = e["x"] + (c - (cols - 1) / 2) * sp; fy = e["y"] + 40 + r * (h + 18) + h
        cv.im.paste(im, (int((cx - im.width / S / 2) * S), int((fy - hh) * S)), im)
    cv.d = ImageDraw.Draw(cv.im, "RGBA")

def e_research(cv, e, t, T):
    """A study paper slides up, a magnifier sweeps over it, and a $ coin with a spark pops: "research -> money tip"."""
    k = T.fade(e, t); t0 = T.t_in(e)
    if k <= 0 or t < t0: return
    x, y = e["x"], e["y"]; u = ease((t - t0) / 0.45); yy = y + (1 - u) * 60; ku = k * u
    b = [x - 170, yy - 210, x + 170, yy + 210]
    cv.shadow(b, 22, ku, blur=18, dy=10, alpha=0.14); cv.rect(b, 22, fill=WHITE, outline=INK, w=5, k=ku)
    cv.text(x - 130, yy - 160, "STUDY", F("xb", 26), ORANGE, ku, anchor="lm")
    for i, lw in enumerate([260, 230, 250, 180, 240, 150]):
        cv.line([(x - 130, yy - 105 + i * 50), (x - 130 + lw * ease((t - t0 - 0.2 - i * 0.07) / 0.3), yy - 105 + i * 50)], MUTED, 10, ku)
    m = ease((t - t0 - 0.55) / 0.7)                          # magnifier sweeps across the lines
    if m > 0:
        mx, my = x - 110 + 150 * m, yy - 40 + 40 * math.sin(m * math.pi)
        cv.circle(mx, my, 62, fill=(255, 255, 255), k=k * 0.35); cv.circle(mx, my, 62, outline=INK, w=9, k=k)
        cv.line([(mx + 44, my + 44), (mx + 100, my + 100)], INK, 16, k)
    c = T.u({"at": 0}, t - (t0 - T.sc["t0"]) - 1.15, 0.45) if False else clamp((t - t0 - 1.15) / 0.45)
    if c > 0:                                                # the coin pops at the top right with a little spark
        r = 70 * (0.5 + 0.5 * back(c)); cx, cy = x + 175, yy - 200
        cv.shadow([cx - r, cy - r, cx + r, cy + r], r, k, blur=12, dy=6, alpha=0.18)
        cv.circle(cx, cy, r, fill=ORANGE, k=k); cv.circle(cx, cy, r * 0.78, outline=WHITE, w=4, k=k)
        cv.text(cx, cy + 2, "$", F("xb", r * 1.1), WHITE, k)
        for a in range(0, 360, 45):
            ra = math.radians(a); d0, d1 = r + 14, r + 14 + 26 * ease(c)
            cv.line([(cx + math.cos(ra) * d0, cy + math.sin(ra) * d0), (cx + math.cos(ra) * d1, cy + math.sin(ra) * d1)], ORANGE, 6, k * (1 - clamp((t - t0 - 1.6) / 0.4)))

DRAW = {"research": e_research, "crowd": e_crowd, "couple": e_couple, "text": e_text, "chip": e_chip, "chart": e_chart, "card": e_card, "panel": e_panel, "bars": e_bars, "lock": e_lock,
        "target": e_target, "qring": e_qring, "accounts": e_accounts, "avatar": e_avatar, "curve": e_curve,
        "ticket": e_ticket, "tag": e_tag, "clock": e_clock, "line": e_line, "dot": e_dot, "statement": e_statement}

# ---------------- timeline ----------------
class Timing:
    """Resolves "at"/"until" anchors for one scene against its spoken words."""
    def __init__(self, sc, words):
        self.sc, self.words = sc, words
    def anchor(self, a):
        if a is None: return None
        if isinstance(a, (int, float)): return self.sc["t0"] + a
        target = [norm(w) for w in strip_tags(a).split() if norm(w)]
        ws = [norm(w) for w, _, _ in self.words]
        for i in range(len(ws) - len(target) + 1):
            if ws[i:i + len(target)] == target: return self.words[i][1]
        sys.exit(f"anchor {a!r} not found in scene {self.sc['title']!r}")
    def at(self, e, key): return self.anchor(e.get(key)) if e.get(key) is not None else None
    def t_in(self, e): return self.anchor(e.get("at", 0))
    def u(self, e, t, d):
        """Entrance progress 0..1 over d seconds ("instant" elements are already in)."""
        return 1.0 if e.get("instant") else clamp((t - self.t_in(e)) / d)
    def fade(self, e, t):
        u = self.at(e, "until"); k = 1.0
        if u is not None: k = 1 - ease((t - u) / 0.3)
        return k * self.sc["_g"]
    def k(self, e, t):
        if e.get("instant"): return self.fade(e, t)
        return ease((t - self.t_in(e)) / 0.35) * self.fade(e, t) if t >= self.t_in(e) else 0.0

def take(spec, tmp):
    """One voice-over take for the whole script -> audio, [(word, start, end)], words per scene.
    Pauses are capped at max_gap, then each scene is time-stretched by its own speed (pitch kept)."""
    import soundfile as sf
    _, vid, model = spec["voice"].split(":")
    text = " ".join(sc["text"] for sc in spec["scenes"])
    audio, words = speak(vid, model, text, spec.get("voice_settings"))
    counts = [len([w for w in strip_tags(sc["text"]).split() if w.strip()]) for sc in spec["scenes"]]
    if sum(counts) != len(words): sys.exit(f"word count mismatch: script {sum(counts)} vs take {len(words)}")
    gap, cuts = spec.get("max_gap"), []
    lead_in = words[0][1]                                  # trim silence (or a breath) before the first word
    if lead_in > 0.05: cuts.append((0.0, lead_in - 0.03))
    if gap:
        for (_, _, e0), (_, s1, _) in zip(words, words[1:]):
            if s1 - e0 > gap: cuts.append((e0 + gap / 2, s1 - gap / 2))
    def remap(x): return x - sum(min(max(x - c0, 0), c1 - c0) for c0, c1 in cuts)
    keep, prev = [], 0.0
    for c0, c1 in cuts: keep.append(audio[int(prev * SR):int(c0 * SR)]); prev = c1
    keep.append(audio[int(prev * SR):]); audio = np.concatenate(keep)
    words = [(w, remap(a), remap(b)) for w, a, b in words]
    # per-scene speed: split at the midpoint of each scene boundary pause, stretch each piece
    bounds, i = [0.0], 0
    for n in counts[:-1]:
        i += n; bounds.append((words[i - 1][2] + words[i][1]) / 2)
    bounds.append(len(audio) / SR)
    pieces, out_t0, new_words, i = [], 0.0, [], 0
    for j, sc in enumerate(spec["scenes"]):
        sp = sc.get("speed", spec.get("speed", 1.0)); a0, a1 = bounds[j], bounds[j + 1]
        seg = audio[int(a0 * SR):int(a1 * SR)]
        if sp != 1.0:
            p_in, p_out = os.path.join(tmp, f"s{j}.wav"), os.path.join(tmp, f"s{j}x.wav"); sf.write(p_in, seg, SR)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", p_in, "-filter:a", f"atempo={sp}", p_out], check=True)
            seg, _ = sf.read(p_out)
        for w, a, b in words[i:i + counts[j]]: new_words.append((w, out_t0 + (a - a0) / sp, out_t0 + (b - a0) / sp))
        i += counts[j]; pieces.append(seg); out_t0 += len(seg) / SR
    return np.concatenate(pieces), [(w, a + LEAD, b + LEAD) for w, a, b in new_words], counts

def captions(sc, words):
    """Split a scene's words into caption chunks at punctuation; a phrase over 8 words is split into even halves,
    so no chunk is a lone leftover word."""
    phrases, cur = [], []
    sentence = sc.get("cap_split") == "sentence"; mx = sc.get("cap_max", 12) if sentence else 8
    for w in words:
        cur.append(w)
        if re.search(r"[.?!:;]['\"”’]?$" if sentence else r"[.,?!:;]['\"”’]?$", w[0]): phrases.append(cur); cur = []
    if cur: phrases.append(cur)
    chunks = []
    for p in phrases:
        n = max(1, math.ceil(len(p) / mx)); size = math.ceil(len(p) / n)
        chunks += [p[i:i + size] for i in range(0, len(p), size)]
    merged = []
    for c in chunks:                                   # a 1-2 word phrase joins the previous chunk if it fits
        short, room = (5, mx) if sentence else (2, 9)
        if merged and len(c) <= short and len(merged[-1]) + len(c) <= room: merged[-1] = merged[-1] + c
        else: merged.append(c)
    return [(c[0][1], " ".join(x[0] for x in c), c) for c in merged]

def karaoke(cv, cap, t):
    """Spoken words in a dark box: said words white, the current word on an orange pill, upcoming words dimmed."""
    st, _, ws = cap; kc = ease((t - st + 0.04) / 0.12); size = 48 if len(ws) <= 12 else 42; f = F("xb", size); sp = cv.tl(" ", f) + 8; lh = 72
    def lay(maxw):
        out, cur, cw = [], [], 0.0
        for w in ws:
            tw = cv.tl(w[0], f)
            if cur and cw + sp + tw > maxw: out.append(cur); cur, cw = [], 0.0
            cw += (sp if cur else 0) + tw; cur.append((w, tw))
        return out + ([cur] if cur else [])
    lines = lay(CAP_W - 60); n = len(lines); mw = CAP_W - 60
    while n > 1 and len(lay(mw - 10)) == n: mw -= 10        # balance the lines: no lone word on the last line
    lines = lay(mw)
    bw = max(sum(tw for _, tw in l) + sp * (len(l) - 1) for l in lines) + 64; bh = lh * len(lines) + 34
    cy = min(CAP_Y, 1640 - bh / 2) + (1 - ease((t - st + 0.04) / 0.14)) * 14; b = [CAP_CX - bw / 2, cy - bh / 2, CAP_CX + bw / 2, cy + bh / 2]
    cv.shadow(b, 26, kc, blur=16, dy=8, alpha=0.22); cv.rect(b, 26, fill=INK, k=kc * 0.94)
    now = [w for w, _ in sum(lines, []) if w[1] <= t + 0.03]; cur_w = now[-1] if now else None
    for li, l in enumerate(lines):
        x = CAP_CX - (sum(tw for _, tw in l) + sp * (len(l) - 1)) / 2; y = cy - bh / 2 + 17 + lh * li + lh / 2
        for w, tw in l:
            said = w[1] <= t + 0.03
            if w is cur_w:
                u = clamp((t - w[1] + 0.03) / 0.12); pad = 10 + 4 * (1 - u)
                cv.rect([x - pad, y - size * 0.62 - 2, x + tw + pad, y + size * 0.62 - 2], 14, fill=ORANGE, k=kc)
            cv.text(x, y, w[0], f, WHITE, kc * (1.0 if said else 0.42), anchor="lm")
            x += tw + sp

def click(n, gain):
    t = np.arange(int(0.06 * SR)) / SR
    return (np.sin(2 * np.pi * 1500 * t) * np.exp(-t / 0.014) + np.random.default_rng(n).normal(0, 1, len(t)) * np.exp(-t / 0.003) * 0.25) * gain

def main():
    import soundfile as sf
    spec_path = sys.argv[1]; check = "--check" in sys.argv
    at = [float(x) for x in sys.argv[sys.argv.index("--at") + 1:]] if "--at" in sys.argv else None
    spec = json.load(open(spec_path)); rid = spec["id"]
    tmp = os.path.join(HERE, ".cache", "tmp_" + rid); os.makedirs(tmp, exist_ok=True)
    audio, words, counts = take(spec, tmp)
    scenes, i = spec["scenes"], 0
    for sc, n in zip(scenes, counts):
        sc["_words"] = words[i:i + n]; i += n
    for j, sc in enumerate(scenes): sc["t0"] = 0.0 if j == 0 else sc["_words"][0][1] - 0.18
    total = words[-1][2] + TAIL
    for j, sc in enumerate(scenes): sc["t1"] = scenes[j + 1]["t0"] if j + 1 < len(scenes) else total
    caps = []
    for sc in scenes: caps += captions(sc, sc["_words"])
    for sc in scenes: sc["_T"] = Timing(sc, sc["_words"])

    def owners(j):
        """Scenes whose diagrams are on screen during scene j (a keep_prev chain)."""
        out = [j]
        while scenes[out[-1]].get("keep_prev") and out[-1] > 0: out.append(out[-1] - 1)
        return out

    def draw(t):
        cv = Canvas(); j = max(x for x in range(len(scenes)) if scenes[x]["t0"] <= t)
        nxt = scenes[j + 1] if j + 1 < len(scenes) else None
        for o in reversed(owners(j)):
            sc = scenes[o]; out = 1.0
            if nxt is not None and o not in owners(j + 1): out = 1 - ease((t - (nxt["t0"] - 0.2)) / 0.2)
            fin = 1.0 if o == 0 else ease((t - scenes[o]["t0"]) / 0.22)  # a new scene fades in (incl. "instant" parts)
            op = out * fin; sc["_g"] = 1.0                                # no fade at the end: the last frame holds
            if op <= 0: continue
            if op >= 1:
                for e in sc.get("elements", []): DRAW[e["type"]](cv, e, t, sc["_T"])
            else:                                  # fade the scene as one flat layer, so stacked shapes don't go muddy
                lay = Canvas(); lay.im = cv.im.copy(); lay.d = ImageDraw.Draw(lay.im, "RGBA")
                for e in sc.get("elements", []): DRAW[e["type"]](lay, e, t, sc["_T"])
                cv.im = Image.blend(cv.im, lay.im, op); cv.d = ImageDraw.Draw(cv.im, "RGBA")
        sc = scenes[j]; prev = scenes[j - 1]["title"] if j else None
        kt = 1.0 if (prev == sc["title"] or j == 0) else ease((t - sc["t0"]) / 0.3)
        rich(cv, W / 2, TITLE_Y, sc["title"], 44, kt)
        cur = [c for c in caps if c[0] <= t + 0.04]
        if cur and spec.get("cap_style") == "karaoke": karaoke(cv, cur[-1], t)
        elif cur:
            st, s, _ = cur[-1]; kc = ease((t - st + 0.04) / 0.1); f = F("b", 50)
            lines = wrap(cv, strip_tags(s), f, CAP_W)
            for li, l in enumerate(lines): cv.text(CAP_CX, CAP_Y - (len(lines) - 1) * 31 + li * 62, l, f, INK, kc, rise=6)
        return cv.out()

    def zones(im):
        im = im.convert("RGBA"); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        for b in [(0, 0, W, 255), (0, 1660, W, H), (905, 1150, W, H), (0, 0, 55, H), (W - 55, 0, W, H)]: d.rectangle(b, fill=(255, 0, 0, 45))
        return Image.alpha_composite(im, ov).convert("RGB")

    if "--cover" in sys.argv:
        j, ph = spec["cover_at"]; tc = scenes[j]["_T"].anchor(ph) + 0.25
        out = os.path.join(ROOT, "reels", rid + "_cover.jpg"); draw(tc).save(out, quality=92); print(out, f"{tc:.2f}s"); return
    if check or at:
        times = at or [min((sc["t0"] + sc["t1"]) / 2 + 0.8, sc["t1"] - 0.05) for sc in scenes]
        sz = (W // 2, H // 2) if at else (W // 3, H // 3); ims = [zones(draw(x)).resize(sz) for x in times]
        cols = min(4, len(ims)); rows = (len(ims) + cols - 1) // cols; sheet = Image.new("RGB", (cols * sz[0], rows * sz[1]), (40, 40, 40))
        for k_, im in enumerate(ims): sheet.paste(im, ((k_ % cols) * sz[0], (k_ // cols) * sz[1]))
        out = os.path.join(ROOT, "reels", rid + ("_at.jpg" if at else "_check.jpg")); sheet.save(out, quality=88)
        print(out, f"{total:.1f}s", "scene starts:", [f"{sc['t0']:.1f}" for sc in scenes], "times:", [f"{x:.1f}" for x in times]); return

    n = int((total + 0.2) * SR); mixd = np.zeros(n); a0 = int(LEAD * SR); mixd[a0:a0 + len(audio)] += audio[:n - a0]
    pk = np.max(np.abs(mixd)) or 1; mixd *= 0.89 / pk
    ticks = set()
    for sc in scenes:
        for e in sc.get("elements", []):
            if e.get("instant") or e.get("silent"): continue
            tt = round(sc["_T"].t_in(e), 2)
            if tt > 0.2: ticks.add(tt)
    for k_, tt in enumerate(sorted(ticks)):
        c = click(k_, 0.05); i0 = int(tt * SR); mixd[i0:i0 + len(c)] += c[:max(0, n - i0)]
    wav = os.path.join(tmp, "mix.wav"); sf.write(wav, mixd, SR)
    out = os.path.join(ROOT, "reels", rid + ".mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-shortest", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    assert ff.stdin is not None
    for f in range(int(total * FPS)): ff.stdin.write(draw(f / FPS).tobytes())
    ff.stdin.close(); ff.wait()
    print(out, f"{total:.1f}s")

if __name__ == "__main__":
    main()
