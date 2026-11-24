"""Render a talking-head Reel from one real clip: jump-cut to the kept segments (fillers and pauses removed), the
person's own voice, word-timed captions from a speech-to-text transcript, and a "reveal" table under the video whose
values are hidden behind bars that slide away on the exact word each value is spoken.

Usage:  python3 pipeline/make_talking_reel.py hooks/<id>.json           -> reels/<id>.mp4
        python3 pipeline/make_talking_reel.py hooks/<id>.json --check   -> reels/<id>_check_<n>.jpg

Spec:
{ "id": "...", "source": "pipeline/assets/scenes/<x>/raw.mov", "transcript": ".../transcript.json" (ElevenLabs STT),
  "segments": [[start, end], ...]  (source seconds, kept in order; each segment alternates a slight punch-in),
  "panel": {"top": 0, "height": 1120, "focus_y": 0.42}   (video panel; focus_y = where the face sits in the source),
  "hook": {"text": "...", "until": 3.0}, "nametag": {"text": "...", "until": 3.0},
  "table": {"title": "...", "source": "...", "rows": [{"label": "30", "value": "$100K", "word_at": 14.86}, ...]},
  "music": "pipeline/assets/music/....mp3", "music_gain": 0.2, "duck": 0.35,
  "end": {...same as make_scene_reel...} }
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import make_scene_reel as M
from make_scene_reel import W, H, FPS, SR, font, ease, fit, layer, paste, draw_hook, draw_end, INK, GREY, ORANGE, WHITE, GREEN, CREAM

FILLERS = {"um", "uh", "um,", "uh,", "uh.", "um."}

def rel(p): return p if os.path.isabs(p) else os.path.join(ROOT, p)

def timeline(spec):
    """Output time <-> source time over the kept segments."""
    segs, t = [], 0.0
    for sg in spec["segments"]:
        a, b = sg[0], sg[1]; sp = sg[2] if len(sg) > 2 else 1.0
        segs.append((t, t + (b - a) / sp, a, b, sp)); t += (b - a) / sp
    return segs, t

def src_to_out(segs, s):
    for o0, o1, a, b, sp in segs:
        if a <= s <= b: return o0 + (s - a) / sp
    return None

def load_frames(spec):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", rel(spec["source"]), "-an", "-vf",
                          f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)

def captions(spec, segs):
    tr = json.load(open(rel(spec["transcript"]))); out = []
    for w in tr["words"]:
        if w["type"] != "word" or w["text"].lower().strip() in FILLERS: continue
        s = src_to_out(segs, w["start"]); e = src_to_out(segs, w["end"])
        if s is None: continue
        if spec.get("_captions_from") is not None and s < spec["_captions_from"]: continue
        seg = next(i for i, g in enumerate(segs) if g[2] <= w["start"] <= g[3])
        out.append((spec.get("replace", {}).get(w["text"], w["text"]), s, e if e is not None else s + 0.3, seg))
    return out

def draw_caption(img, caps, t, y, cx=W / 2, maxw=860):
    cur = [i for i, c in enumerate(caps) if c[1] - 0.05 <= t <= c[2] + 0.3]
    if not cur: return
    i = cur[-1]; lid = caps[i][3]; first = min(j for j, c in enumerate(caps) if c[3] == lid)
    start = first + ((i - first) // 4) * 4; grp = [c for c in caps[start:start + 4] if c[3] == lid]
    d = ImageDraw.Draw(img); size = 64; words = [c[0] for c in grp]
    while size > 40 and font("xb", size).getlength(" ".join(words)) > maxw: size -= 2
    x = cx - font("xb", size).getlength(" ".join(words)) / 2
    for w, s, e, _ in grp:
        col = (255, 214, 64) if s - 0.05 <= t <= e + 0.05 else WHITE
        d.text((x, y), w, font=font("xb", size), fill=col, stroke_width=7, stroke_fill=INK)
        x += font("xb", size).getlength(w + " ")

def draw_logo_icon(d, x, y, size, a=255):
    """DivvyUpp mark: orange rounded square with the white branching arrow (same geometry as make_reel.logo)."""
    d.rounded_rectangle([x, y, x + size, y + size], size * 0.28, fill=ORANGE + (a,))
    c = x + size / 2; sw = max(3, int(size * 0.1)); top, bot = y + size * 0.27, y + size * 0.73; arm = size * 0.19
    col = WHITE + (a,)
    d.line([(c, top), (c, bot)], fill=col, width=sw); d.line([(c - arm, top + arm), (c, top), (c + arm, top + arm)], fill=col, width=sw, joint="curve")
    for px, py in [(c, bot), (c - arm, top + arm), (c + arm, top + arm), (c, top)]:
        d.ellipse([px - sw / 2, py - sw / 2, px + sw / 2, py + sw / 2], fill=col)

def draw_nametag(img, nt, t):
    """Pill, top right: [logo] DivvyUpp | Srini · Founder. Pops in with a small scale bounce."""
    k = ease((t - nt.get("from", 0)) / 0.3)
    if k <= 0: return
    pop = 1 + 0.12 * math.sin(min(1.0, (t - nt.get("from", 0)) / 0.35) * math.pi)       # quick overshoot
    lay = Image.new("RGBA", (900, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    fb, fw = font("xb", 34), font("b", 32); ic = 46; x = 22
    brand = "DivvyUpp"; who = nt.get("text", "Srini · Founder")
    wb, ww = fb.getlength(brand), fw.getlength(who); total = 22 + ic + 12 + wb + 22 + 2 + 22 + ww + 26
    d.rounded_rectangle([0, 20, total, 20 + 74], 37, fill=(255, 255, 255, 240))
    draw_logo_icon(d, x, 20 + 14, ic); x += ic + 12
    d.text((x, 57), brand, font=fb, fill=INK, anchor="lm"); x += wb + 22
    d.line([(x, 38), (x, 76)], fill=(215, 208, 200), width=2); x += 24
    d.text((x, 57), who, font=fw, fill=GREY, anchor="lm")
    lay = lay.crop((0, 0, int(total) + 2, 120))
    if pop != 1: lay = lay.resize((int(lay.width * pop), int(lay.height * pop)), Image.BICUBIC)
    a = np.array(lay); a[..., 3] = (a[..., 3] * k).astype(np.uint8); lay = Image.fromarray(a)
    x1 = nt.get("x1", W - 46); yy = nt.get("y", 270)
    img.alpha_composite(lay, (int(x1 - lay.width), int(yy - (lay.height - 120) / 2)))

def draw_sky_hook(img, sh, t):
    """Big hook text over the opening shot; fades out as the camera moves."""
    k = 1.0 - ease((t - sh["until"] + 0.25) / 0.25) if t > sh["until"] - 0.25 else 1.0
    if k <= 0: return
    lay = layer(); d = ImageDraw.Draw(lay); lines = sh["text"].split("\n"); y = sh.get("y", 330)
    for ln in lines:
        size = fit(ln, "xb", sh.get("size", 96), 940); tw = font("xb", size).getlength(ln)
        d.rounded_rectangle([W / 2 - tw / 2 - 32, y - 16, W / 2 + tw / 2 + 32, y + size + 26], 28, fill=(255, 255, 255, 246))
        d.text((W / 2, y), ln, font=font("xb", size), fill=INK, anchor="ma"); y += size + 56
    paste(img, lay, k)

def draw_callout(img, co, t):
    """Orange pill that pops in on the video (e.g. 'The one thing you're missing:') between its out-times."""
    if not (co["_from"] <= t < co["_until"]): return
    k = ease((t - co["_from"]) / 0.25) * (1 - ease((t - co["_until"] + 0.25) / 0.25))
    pop = 1 + 0.1 * math.sin(min(1.0, (t - co["_from"]) / 0.3) * math.pi)
    f = font("xb", co.get("size", 64)); tw = f.getlength(co["text"])
    lay = Image.new("RGBA", (int(tw + 90), 130), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 10, tw + 80, 120], 55, fill=ORANGE); d.text((40, 65), co["text"], font=f, fill=WHITE, anchor="lm")
    lay = lay.resize((int(lay.width * pop), int(lay.height * pop)), Image.BICUBIC)
    a = np.array(lay); a[..., 3] = (a[..., 3] * k).astype(np.uint8)
    img.alpha_composite(Image.fromarray(a), (int((W - lay.width) / 2), int(co.get("y", 300) - (lay.height - 130) / 2)))

def draw_progress_line(img, pl, t, t0, t1, y):
    """Thin orange line along the bottom edge of the video, filling until the payoff; tiny label above it."""
    p = min(1.0, max(0.0, (t - t0) / max(0.01, t1 - t0))); d = ImageDraw.Draw(img)
    d.rectangle([0, y - 10, W, y], fill=(255, 255, 255, 70)); d.rectangle([0, y - 10, int(W * p), y], fill=ORANGE)
    if pl.get("label"): d.text((W - 24, y - 18), pl["label"], font=font("b", 28), fill=WHITE, anchor="rd", stroke_width=3, stroke_fill=INK)

def draw_payoff(img, po, t, y0):
    """The answer, big, in the table's place: '1 Save first.' then an arrow, then '2 Then spend what's safe.'"""
    cx = W / 2
    k1 = ease((t - po["_l1"]) / 0.3); k2 = ease((t - po["_l2"]) / 0.3); ka = ease((t - po["_l1"] - 0.35) / 0.3)
    size = min(fit(po["line1"], "xb", 92, 760), fit(po["line2"], "xb", 92, 760))
    def line(y, n, txt, col, k):
        if k <= 0: return
        lay = layer(); dd = ImageDraw.Draw(lay); f = font("xb", size); tw = f.getlength(txt)
        x = cx - (tw + 110) / 2
        dd.ellipse([x, y + 6, x + 84, y + 90], fill=col); dd.text((x + 42, y + 48), n, font=font("xb", 54), fill=WHITE, anchor="mm")
        dd.text((x + 110, y + 48), txt, font=f, fill=col, anchor="lm")
        dd.rectangle([x + 110, y + 104, x + 110 + tw * min(1, k * 1.2), y + 114], fill=col)
        paste(img, lay, k, dy=int((1 - k) * 40))
    line(y0 + 40, "1", po["line1"], GREEN, k1)
    if ka > 0:
        lay = layer(); dd = ImageDraw.Draw(lay); ax, ay = cx, y0 + 190
        dd.line([(ax, ay), (ax, ay + 90)], fill=ORANGE, width=14); dd.polygon([(ax - 38, ay + 70), (ax + 38, ay + 70), (ax, ay + 122)], fill=ORANGE)
        paste(img, lay, ka, dy=int((1 - ka) * -20))
    line(y0 + 330, "2", po["line2"], ORANGE, k2)

def draw_table(img, tb, t, y0, hook=None):
    """Title slot shows the hook (bigger, in orange) while it's live, then the table title."""
    d = ImageDraw.Draw(img); x0, x1 = 90, W - 90
    if hook and t < hook.get("until", 3.0):
        lines = hook["text"].split("\n")
        for i, ln in enumerate(lines):
            d.text((W / 2, y0 - 6 + 52 * i), ln, font=font("xb", fit(ln, "xb", 50, 900)), fill=ORANGE, anchor="ma")
    else:
        d.text((W / 2, y0 + 20), tb["title"], font=font("xb", 46), fill=INK, anchor="ma")
    rows = tb["rows"]; rh = 76; y = y0 + 104
    for r in rows:
        d.rounded_rectangle([x0, y, x1, y + rh - 12], 20, fill=(255, 255, 255))
        d.text((x0 + 36, y + (rh - 12) / 2), r["label"], font=font("xb", 42), fill=INK, anchor="lm")
        vx0, vx1 = x0 + 300, x1 - 24
        d.text(((vx0 + vx1) / 2, y + (rh - 12) / 2), r["value"], font=font("xb", 46), fill=GREEN, anchor="mm")
        k = ease((t - r["_out"]) / 0.4) if r.get("_out") is not None else 0.0   # bar slides right and away
        if k < 1:
            bx0 = vx0 + (vx1 - vx0) * k                                  # cover shrinks to the right, inside the row
            if vx1 - bx0 > 6: d.rounded_rectangle([bx0, y + 8, vx1, y + rh - 20], 14, fill=ORANGE)
            if k == 0: d.text(((vx0 + vx1) / 2, y + (rh - 12) / 2), "?", font=font("xb", 40), fill=WHITE, anchor="mm")
        y += rh
    if tb.get("source"): d.text((W / 2, y + 8), tb["source"], font=font("m", 30), fill=GREY, anchor="ma")

def frame_at(spec, frames, segs, caps, total, t):
    end = spec.get("end"); body = segs[-1][1]
    if t >= body and end:
        last = Image.fromarray(frames[min(int(segs[-1][3] * FPS), len(frames) - 1)]).convert("RGBA")
        from PIL import ImageFilter
        img = last.filter(ImageFilter.GaussianBlur(12)); draw_end(img, end, ease((t - body) / 0.4)); return img
    si = next(i for i, g in enumerate(segs) if g[0] <= t < g[1] or i == len(segs) - 1)
    o0, o1, a, b, sp = segs[si]; s = min(b, a + (t - o0) * sp)        # past the body (tail hold): last kept frame
    src = Image.fromarray(frames[min(int(s * FPS), len(frames) - 1)])
    for st in spec.get("stills", []):                                # crossfade the live frame into a still
        if st["_from"] <= t < st["_until"]:                          # (e.g. an aged photo with the same framing)
            fd = st.get("fade", 0.4); fo = st.get("fade_out", fd)
            k = ease((t - st["_from"]) / fd) * (1 - ease((t - st["_until"] + fo) / fo))
            im = st.setdefault("_img", Image.open(rel(st["image"])).convert("RGB").resize((W, H), Image.LANCZOS))
            zk = 1 + st.get("push", 0.04) * (t - st["_from"]) / max(0.01, st["_until"] - st["_from"])
            lt = t - st["_from"]
            if st.get("punch"):                                      # quick zoom punch with overshoot on entry
                zk *= 1 + st["punch"] * math.sin(min(1.0, lt / 0.35) * math.pi) * math.exp(-lt * 2.5) + st["punch"] * 0.4 * ease(lt / 0.2)
            dx = dy = 0.0
            if st.get("shake"):                                      # decaying camera shake
                amp = st["shake"] * math.exp(-lt * 4.0); dx = amp * math.sin(lt * 71); dy = amp * math.cos(lt * 53)
            if st.get("shake"): zk = max(zk, 1 + 2.2 * st["shake"] / H)  # always leave room to shake inside the frame
            if zk != 1 or dx or dy:
                cw, ch = W / zk, H / zk
                x0 = min(max(0.0, (W - cw) / 2 + dx), W - cw); y0 = min(max(0.0, (H - ch) / 2 + dy), H - ch)
                im = im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
            src = Image.blend(src, im, k)
    if spec.get("tail_fade") == "blur" and t > body:                # tail: last frame softly blurs and dims
        from PIL import ImageFilter
        kb = ease((t - body) / max(0.01, spec.get("tail", 1.0) * 0.7))
        src = Image.blend(src.filter(ImageFilter.GaussianBlur(14 * kb)), Image.new("RGB", src.size, INK), 0.35 * kb)
    lf = spec.get("_layout_from")
    if lf is not None and t < lf:                                   # opening: full screen, hook only
        z = 1.16 - 0.16 * ease(t / max(lf, 0.01)) ** 0.8                 # camera push from frame 1
        cw, ch = W / z, H / z; img = src.resize((W, H), Image.BICUBIC, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2)).convert("RGBA")
        g = np.zeros((H, 1), np.float32); g[:900, 0] = np.linspace(0.35, 0, 900)
        a_ = np.zeros((H, W, 4), np.uint8); a_[..., 3] = (np.repeat(g, W, 1) * 255).astype(np.uint8); img.alpha_composite(Image.fromarray(a_))
        sh = spec.get("sky_hook")
        if sh and t < sh["until"]: (draw_sky_hook2 if sh.get("parts") else draw_sky_hook)(img, sh, t)
        return img
    pn = spec["panel"]; ph = pn["height"]; z = 1.0 if si % 2 == 0 else pn.get("punch", 1.07)
    zo = pn.get("zoom_out", 1.0)                       # >1 shows more of the frame; sides filled with a blurred copy
    ch = min(H, ph * zo) / z; cw = W / z; cy = H * pn.get("focus_y", 0.42)
    y0 = min(max(0, cy - ch / 2), H - ch); x0 = (W - cw) / 2
    pw = int(round(cw * ph / ch)) if zo > 1 else W
    fg = src.resize((pw, ph), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    if pw < W:
        from PIL import ImageFilter
        bg = src.resize((W, ph), Image.BILINEAR, box=(0, max(0, cy - ph / 2), W, max(0, cy - ph / 2) + ph)).filter(ImageFilter.GaussianBlur(28))
        bg = Image.blend(bg, Image.new("RGB", bg.size, (20, 16, 15)), 0.25); bg.paste(fg, ((W - pw) // 2, 0)); panel = bg
    else: panel = fg
    img = Image.new("RGBA", (W, H), CREAM + (255,)); img.paste(panel, (0, pn.get("top", 0)))
    g = np.zeros((ph, 1), np.float32); g[ph - 260:, 0] = np.linspace(0, 0.55, 260); g[:420, 0] = np.linspace(0.45, 0, 420)
    a_ = np.zeros((ph, W, 4), np.uint8); a_[..., 3] = (np.repeat(g, W, 1) * 255).astype(np.uint8)
    img.alpha_composite(Image.fromarray(a_), (0, pn.get("top", 0)))
    if spec.get("tail_fade") is True and t > body:                  # tail: the video fades to the background
        kf = ease((t - body) / max(0.01, spec.get("tail", 1.0) * 0.8))
        img.alpha_composite(Image.new("RGBA", (W, H), CREAM + (int(255 * kf),)))
    for co in spec.get("callouts", []): draw_callout(img, co, t)
    if spec.get("label"): draw_label(img, spec["label"])
    for cd in spec.get("cards", []): draw_timed_card(img, cd, t)
    for st in spec.get("stills", []):                                # reaction sticker, e.g. "Whoa! Is that me?"
        pts = st.get("pop_text") or []
        for pt in (pts if isinstance(pts, list) else [pts]):
            if not (st["_from"] + pt.get("delay", 0.1) <= t < st["_until"]): continue
            lt = t - st["_from"] - pt.get("delay", 0.1)
            k = ease(lt / 0.22) * (1 - ease((t - st["_until"] + 0.18) / 0.18))
            pop = 1 + 0.2 * math.sin(min(1.0, lt / 0.3) * math.pi); f = font("xb", pt.get("size", 66)); tw = f.getlength(pt["text"])
            lay = Image.new("RGBA", (int(tw + 72), int(pt.get("size", 66) + 56)), (0, 0, 0, 0)); dd = ImageDraw.Draw(lay)
            wh = pt.get("style") == "white"
            dd.rounded_rectangle([0, 0, lay.width - 1, lay.height - 1], 32, fill=(WHITE if wh else ORANGE) + (250,))
            dd.text((36, 20), pt["text"], font=f, fill=INK if wh else WHITE)
            lay = lay.rotate(pt.get("tilt", -4) + math.sin(t * 10) * 2.0, resample=Image.BICUBIC, expand=True)
            lay = lay.resize((int(lay.width * pop), int(lay.height * pop)), Image.BICUBIC)
            a = np.array(lay); a[..., 3] = (a[..., 3] * k).astype(np.uint8)
            img.alpha_composite(Image.fromarray(a), (int(pt.get("x", W / 2) - lay.width / 2), int(pt.get("y", 420) - lay.height / 2)))
    for st in spec.get("stills", []):                                # small honest tag while a still is on screen
        if st.get("tag") and st["_from"] + 0.2 <= t < st["_until"] - 0.1:
            d = ImageDraw.Draw(img); f = font("b", 30); tw = f.getlength(st["tag"]); x, y = st.get("tag_x", 80), st.get("tag_y", 350)
            d.rounded_rectangle([x, y, x + tw + 40, y + 52], 26, fill=(21, 16, 15, 190)); d.text((x + 20, y + 26), st["tag"], font=f, fill=WHITE, anchor="lm")
    hk = spec.get("hook"); ty = pn.get("top", 0) + ph + spec.get("table_gap", 30)
    po = spec.get("payoff"); kin = ease((t - lf) / 0.4) if lf is not None else 1.0
    kout = ease((t - po["_l1"] + 0.3) / 0.3) if po else 0.0        # table stays until the first payoff word
    if kout < 1 and spec.get("table"):                              # table slides up in, fades out for the payoff
        tl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_table(tl, spec["table"], t, ty, hk if spec.get("hook_in_table", True) else None)
        paste(img, tl, kin * (1 - kout), dy=int((1 - kin) * 260))
    if po and t >= po["_l1"] - 0.05: draw_payoff(img, po, t, ty)
    pl = spec.get("progress")
    if pl and lf is not None and po and lf <= t < po["_from"]: draw_progress_pin(img, pl, t, lf, po["_from"], pn.get("top", 0) + ph)
    if hk and not spec.get("hook_in_table", True) and t < hk.get("until", 3.0): draw_hook(img, hk["text"])
    nt = spec.get("nametag")
    if nt and nt.get("from", 0) <= t < nt.get("until", 3.0): draw_nametag(img, nt, t)
    draw_caption(img, caps, t, pn.get("top", 0) + ph - pn.get("caption_up", 110),
                 spec.get("caption_cx", W / 2), spec.get("caption_maxw", 860))
    return img

def draw_label(img, lb):
    """Series label pinned at the top the whole time, e.g. 'Research-backed money tips · #1'."""
    f = font("xb", lb.get("size", 38)); tw = f.getlength(lb["text"]); y = lb.get("y", 280); cx = lb.get("cx", W / 2)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([cx - tw / 2 - 30, y, cx + tw / 2 + 30, y + lb.get("size", 38) + 34], 30, fill=(255, 255, 255, 235))
    d.text((cx, y + (lb.get("size", 38) + 34) / 2), lb["text"], font=f, fill=INK, anchor="mm")

CARD_STYLE = {"title": ("xb", 54, INK), "big": ("xb", 72, ORANGE), "body": ("b", 46, INK), "small": ("m", 32, GREY),
              "note": ("b", 34, ORANGE)}

def draw_timed_card(img, cd, t):
    """White (or orange) card that pops in at a spoken word and fades at another. lines = [[text, style], ...]
    with style title | big | body | small; long lines wrap to the card width. Box: cx, w, y (top)."""
    if not (cd["_from"] <= t < cd["_until"]): return
    k = ease((t - cd["_from"]) / 0.3) * (1 - ease((t - cd["_until"] + 0.25) / 0.25))
    orange = cd.get("fill") == "orange"; pad = 40; w = cd.get("w", 850); cx = cd.get("cx", W / 2)
    rows = []
    for txt, st in cd["lines"]:
        wt, size, col = CARD_STYLE[st]
        if orange: col = WHITE if st != "small" else (255, 228, 214)
        for ln in M.wrap(txt, wt, size, w - 2 * pad): rows.append((ln, wt, size, col))
    h = pad * 2 + sum(r[2] + 16 for r in rows) - 16
    lay = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
    card(lay, [40, 40, 40 + w, 40 + h], 36, fill=(ORANGE + (250,)) if orange else (255, 255, 255, 248))
    d = ImageDraw.Draw(lay); y = 40 + pad
    for ln, wt, size, col in rows:
        d.text((40 + w / 2, y), ln, font=font(wt, size), fill=col, anchor="ma"); y += size + 16
    pop = 1 + 0.06 * math.sin(min(1.0, (t - cd["_from"]) / 0.3) * math.pi)
    if pop != 1: lay = lay.resize((int(lay.width * pop), int(lay.height * pop)), Image.BICUBIC)
    a = np.array(lay); a[..., 3] = (a[..., 3] * k).astype(np.uint8)
    img.alpha_composite(Image.fromarray(a), (int(cx - lay.width / 2), int(cd["y"] + (h + 80) / 2 - lay.height / 2 - 40 + (1 - k) * 24)))

def whoosh(fx):
    """Airy sweep: noise through a moving low-pass, rising then falling, peaking at fx['peak'] of its length."""
    dur = fx.get("dur", 1.0); n = int(dur * SR); rng = np.random.default_rng(11); x = rng.normal(0, 1, n)
    tt = np.arange(n) / n; pk = fx.get("peak", 0.7)
    cut = 300 + 5200 * np.where(tt < pk, tt / pk, 1 - (tt - pk) / (1 - pk)) ** 1.5
    y = np.empty(n); acc = 0.0
    for i in range(n):
        a = math.exp(-2 * math.pi * cut[i] / SR); acc = (1 - a) * x[i] + a * acc; y[i] = acc
    env = np.where(tt < pk, (tt / pk) ** 2, ((1 - tt) / (1 - pk)) ** 1.6)
    return 0.55 * y / max(1e-6, np.abs(y).max()) * env

def pluck_fx(fx):
    from music import pluck
    rng = np.random.default_rng(5); out = np.zeros(int(0.7 * SR))
    for j, f in enumerate(fx.get("notes", [1318.5, 1975.5])):
        p = pluck(f, 0.6, SR, rng) * (0.5 if j else 0.6); s = int(j * 0.07 * SR); out[s:s + len(p)] += p[:len(out) - s]
    return 0.5 * out / max(1e-6, np.abs(out).max())

def boom_fx(fx):
    """Deep reveal hit: a sine that drops from ~150 Hz to ~40 Hz, a short noise click on the attack, a soft
    sub rumble tail. Synthesized here, no sample."""
    dur = fx.get("dur", 1.1); n = int(dur * SR); tt = np.arange(n) / SR; rng = np.random.default_rng(7)
    f = 40 + 110 * np.exp(-tt * 9.0); ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-tt * 3.2) + 0.35 * np.sin(2 * ph) * np.exp(-tt * 6.0)
    click = rng.normal(0, 1, n) * np.exp(-tt * 90.0) * 0.6
    att = np.clip(tt / 0.004, 0, 1); y = (body + click) * att
    y = np.tanh(1.8 * y)                                                      # a little saturation for weight
    return 0.9 * y / max(1e-6, np.abs(y).max())

def file_fx(fx):
    """An audio file (e.g. a generated reaction sound), decoded to mono at the reel's sample rate."""
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", rel(fx["file"]), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    y = np.frombuffer(pcm, np.float32).astype(np.float64)
    return 0.9 * y / max(1e-6, np.abs(y).max())

SFX = {"whoosh": whoosh, "pluck": pluck_fx, "boom": boom_fx, "file": file_fx}

def audio(spec, segs, total):
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", rel(spec["source"]), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    src = np.frombuffer(pcm, np.float32).astype(np.float64); out = []; f = int(0.015 * SR)
    for _, _, a, b, sp in segs:
        piece = src[int(a * SR):int(b * SR)].copy(); ramp = np.linspace(0, 1, f)
        if sp != 1.0: piece = np.interp(np.arange(0, len(piece), sp), np.arange(len(piece)), piece)
        piece[:f] *= ramp; piece[-f:] *= ramp[::-1]; out.append(piece)
    v = np.concatenate(out); v /= max(1e-6, np.abs(v).max()) / 0.9
    v = np.pad(v, (0, int(total * SR) - len(v)))[:int(total * SR)]
    for fx in spec.get("sfx", []):
        snd = SFX[fx["type"]](fx); i = int(fx["at"] * SR); n = min(len(snd), len(v) - i)
        if n > 0: v[i:i + n] += snd[:n] * fx.get("gain", 1.0)
    spec2 = dict(spec); spec2["scenes"] = []
    return M.mix(spec2, v, total)


# ---------------- polish pass (v7) ----------------
_SHADOW = {}
def card(img, box, r=36, fill=(255, 255, 255, 250), shadow=True, k=1.0):
    """Rounded card with a soft drop shadow (shadow cached per size)."""
    x0, y0, x1, y1 = [int(v) for v in box]; w, h = x1 - x0, y1 - y0
    if shadow:
        key = (w, h, r)
        if key not in _SHADOW:
            from PIL import ImageFilter
            sh = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle([40, 48, 40 + w, 48 + h], r, fill=(60, 40, 30, 70))
            _SHADOW[key] = sh.filter(ImageFilter.GaussianBlur(16))
        shd = _SHADOW[key]
        if k < 1: a = np.array(shd); a[..., 3] = (a[..., 3] * k).astype(np.uint8); shd = Image.fromarray(a)
        img.alpha_composite(shd, (x0 - 40, y0 - 40))
    ImageDraw.Draw(img).rounded_rectangle(box, r, fill=fill[:3] + (int(fill[3] * k),))

def draw_sky_hook2(img, sh, t):
    """Animated opening hook: parts pop in one after another with a small overshoot; 'accent' parts sit on an
    orange pill and wiggle. Fades out as the camera moves."""
    fo = sh.get("fade", 0.25)
    kout = 1.0 - ease((t - sh["until"] + fo) / fo) if t > sh["until"] - fo else 1.0
    if kout <= 0: return
    y = sh.get("y", 300); size = sh.get("size", 110)
    for li, line in enumerate(sh["parts"]):            # line = [[text, "plain"|"accent"], ...]
        f = font("xb", size); widths = [f.getlength(tx) for tx, _ in line]; gap = 24
        total = sum(widths) + gap * (len(line) - 1) + 64 * len(line); x = W / 2 - total / 2
        for pi, (tx, st) in enumerate(line):
            t0 = 0.06 + 0.16 * (li * 2 + pi); k = ease((t - t0) / 0.28)
            if k <= 0: x += widths[pi] + 64 + gap; continue
            pop = 1 + 0.18 * math.sin(min(1.0, (t - t0) / 0.32) * math.pi)
            wob = math.sin(t * 9.0) * 2.2 if st == "accent" else 0.0
            lay = Image.new("RGBA", (int(widths[pi] + 64), int(size + 52)), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            bg = ORANGE if st == "accent" else WHITE; fg = WHITE if st == "accent" else INK
            d.rounded_rectangle([0, 0, lay.width - 1, lay.height - 1], 30, fill=bg + (248,)); d.text((32, 18), tx, font=f, fill=fg)
            lay = lay.rotate(wob, resample=Image.BICUBIC, expand=True)
            lay = lay.resize((int(lay.width * pop), int(lay.height * pop)), Image.BICUBIC)
            a = np.array(lay); a[..., 3] = (a[..., 3] * k * kout).astype(np.uint8)
            cx = x + (widths[pi] + 64) / 2
            img.alpha_composite(Image.fromarray(a), (int(cx - lay.width / 2), int(y + (size + 52) / 2 - lay.height / 2 + (1 - k) * 30)))
            x += widths[pi] + 64 + gap
        y += size + 76

def draw_pin(d, cx, tip_y, s, col):
    """Map-pin marker with its point at (cx, tip_y)."""
    r = s / 2; cy = tip_y - s * 1.05
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    d.polygon([(cx - r * 0.72, cy + r * 0.55), (cx + r * 0.72, cy + r * 0.55), (cx, tip_y)], fill=col)
    d.ellipse([cx - r * 0.38, cy - r * 0.38, cx + r * 0.38, cy + r * 0.38], fill=WHITE)

def draw_progress_pin(img, pl, t, t0, t1, y):
    """Progress track along the top of the table panel: a knob travels toward a destination pin labelled
    'the right order'. Sits below the video, so captions never cover it."""
    p = min(1.0, max(0.0, (t - t0) / max(0.01, t1 - t0))); k = ease((t - t0) / 0.4)
    lay = layer(); d = ImageDraw.Draw(lay); x0, x1 = 70, W - 190; ty = y + 40
    d.rounded_rectangle([x0, ty - 5, x1, ty + 5], 5, fill=(232, 224, 214))
    d.rounded_rectangle([x0, ty - 5, x0 + (x1 - x0) * p, ty + 5], 5, fill=ORANGE)
    kx = x0 + (x1 - x0) * p; d.ellipse([kx - 13, ty - 13, kx + 13, ty + 13], fill=WHITE, outline=ORANGE, width=6)
    draw_pin(d, x1 + 52, ty + 14, 46, ORANGE)
    d.text((x1 + 52, ty + 24), pl.get("label", "the right order"), font=font("b", 26), fill=GREY, anchor="ma")  # centred under the pin, inside the frame
    paste(img, lay, k)

def draw_table(img, tb, t, y0, hook=None):
    """Polished table: one white card, header row, hairline dividers, values on orange chips that peel away
    on the spoken word; the revealed value pops and its row glows green briefly."""
    d = ImageDraw.Draw(img); x0, x1 = 70, W - 70
    if hook and t < hook.get("until", 3.0):
        ln = hook["text"].replace("\n", " ")
        d.text((W / 2, y0 + 22), ln, font=font("xb", fit(ln, "xb", 46, 940)), fill=ORANGE, anchor="ma")
    else:
        d.text((W / 2, y0 + 22), tb["title"], font=font("xb", 44), fill=INK, anchor="ma")
    rows = tb["rows"]; rh = 64; top = y0 + 96; hh = 54
    card(img, [x0, top, x1, top + hh + rh * len(rows) + 8], 34)
    d = ImageDraw.Draw(img); vx0, vx1 = x0 + 300, x1 - 36
    d.text((x0 + 40, top + hh / 2 + 4), "AGE", font=font("b", 26), fill=GREY, anchor="lm")
    d.text((vx1, top + hh / 2 + 4), tb.get("header_right", "SAVED"), font=font("b", 24), fill=GREY, anchor="rm")
    y = top + hh
    for i, r in enumerate(rows):
        d.line([(x0 + 28, y), (x1 - 28, y)], fill=(236, 230, 222), width=2)
        cyy = y + rh / 2; out = r.get("_out"); k = ease((t - out) / 0.35) if out is not None else 0.0
        if out is not None and 0 <= t - out < 1.2:                       # row glow after reveal
            g = 1 - (t - out) / 1.2; d.rounded_rectangle([x0 + 10, y + 4, x1 - 10, y + rh - 4], 18, fill=(30, 140, 80, int(40 * g)))
            d = ImageDraw.Draw(img)
        d.text((x0 + 40, cyy), r["label"], font=font("xb", 44), fill=INK, anchor="lm")
        d.text((x0 + 40 + font("xb", 44).getlength(r["label"]) + 10, cyy + 6), "yrs", font=font("m", 26), fill=GREY, anchor="lm")
        if k > 0:
            pop = 1 + 0.25 * math.sin(min(1.0, (t - out) / 0.35) * math.pi)
            d.text((vx1, cyy), r["value"], font=font("xb", int(48 * pop)), fill=GREEN, anchor="rm")
        if k < 1:
            cw = 230; cx1 = vx1; cx0 = cx1 - cw; sl = cw * k                # chip peels off to the right
            if cw - sl > 8:
                d.rounded_rectangle([cx0 + sl, cyy - 22, cx1, cyy + 22], 22, fill=ORANGE)
                if k == 0: d.text(((cx0 + cx1) / 2, cyy), "? ? ?", font=font("xb", 30), fill=WHITE, anchor="mm")
        y += rh

def draw_payoff(img, po, t, y0):
    """Polished payoff card: STEP 1 / STEP 2 rows with icon badges, a dotted connector and a highlighter sweep."""
    k1 = ease((t - po["_l1"]) / 0.3); k2 = ease((t - po["_l2"]) / 0.3)
    x0, x1 = 70, W - 70; top = y0 + 40; rh = 170
    kc = ease((t - po["_l1"] + 0.1) / 0.3)
    card(img, [x0, top, x1, top + rh * 2 + 40], 36, k=kc)
    def row(y, k, n, label, txt, accent, soft):
        if k <= 0: return
        lay = layer(); d = ImageDraw.Draw(lay); bx = x0 + 44; by = y + 34
        d.ellipse([bx, by, bx + 96, by + 96], fill=accent)
        d.text((bx + 48, by + 50), n, font=font("xb", 52), fill=WHITE, anchor="mm")
        tx = bx + 128; f = font("xb", fit(max(po["line1"], po["line2"], key=len), "xb", 80, x1 - tx - 40)); tw = f.getlength(txt)
        d.text((tx, by + 6), label, font=font("b", 26), fill=accent, anchor="la")
        hl = min(1.0, max(0.0, (t - (po["_l1"] if n == "1" else po["_l2"]) - 0.15) / 0.4))
        d.rounded_rectangle([tx - 8, by + 44, tx - 8 + (tw + 16) * hl, by + 112], 14, fill=soft)
        d.text((tx, by + 78), txt, font=f, fill=INK, anchor="lm")
        paste(img, lay, k * kc, dy=int((1 - k) * 30))
    row(top + 10, k1, "1", "STEP 1", po["line1"], GREEN, (210, 240, 222, 255))
    if k1 > 0:
        d = ImageDraw.Draw(img); cx = x0 + 44 + 48
        for j in range(5):
            yy = top + 10 + 34 + 96 + 12 + j * 14
            if yy < top + rh + 34: d.ellipse([cx - 4, yy, cx + 4, yy + 8], fill=(220, 210, 200, int(255 * min(k1, kc))))
    row(top + rh + 10, k2, "2", "STEP 2", po["line2"], ORANGE, (253, 226, 213, 255))

def main():
    path = sys.argv[1]; check = "--check" in sys.argv
    spec = json.load(open(rel(path))); segs, body = timeline(spec)
    if "--source" in sys.argv: spec["source"] = sys.argv[sys.argv.index("--source") + 1]   # e.g. the full-res original
    total = body + (spec["end"].get("dur", 2.5) if spec.get("end") else spec.get("tail", 0.0))
    rows = spec["table"]["rows"] if spec.get("table") else []
    for r in rows: r["_out"] = src_to_out(segs, r["word_at"]) if r.get("word_at") is not None else None
    if spec.get("captions_from_src") is not None: spec["_captions_from"] = src_to_out(segs, spec["captions_from_src"]) - 0.05
    for st in spec.get("stills", []):
        st["_from"] = src_to_out(segs, st["from_src"]); st["_until"] = src_to_out(segs, st["until_src"])
    for cd in spec.get("cards", []):
        cd["_from"] = src_to_out(segs, cd["from_src"]) - cd.get("lead", 0.0)
        cd["_until"] = src_to_out(segs, cd["until_src"]) if cd.get("until_src") is not None else total + 1
    if spec.get("layout_from_src") is not None: spec["_layout_from"] = src_to_out(segs, spec["layout_from_src"]) - 0.05
    po = spec.get("payoff")
    if po:
        po["_from"] = src_to_out(segs, po["from_src"]) - po.get("lead", 0.0)
        po["_l1"] = src_to_out(segs, po["line1_src"]); po["_l2"] = src_to_out(segs, po["line2_src"])
    for co in spec.get("callouts", []):
        co["_from"] = src_to_out(segs, co["from_src"]) - co.get("lead", 0.0); co["_until"] = src_to_out(segs, co["until_src"])
    for fx in spec.get("sfx", []):
        if "at_src" in fx: fx["at"] = src_to_out(segs, fx["at_src"]) - fx.get("lead", 0.0)
    caps = captions(spec, segs); frames = load_frames(spec)
    out_dir = os.path.join(ROOT, "reels")
    if check:
        ts = spec.get("check_at") or ([0.5] + [r["_out"] + 0.8 for r in rows if r["_out"] is not None] + [total - 1])
        for i, t in enumerate(ts):
            frame_at(spec, frames, segs, caps, total, t).convert("RGB").save(os.path.join(out_dir, f"{spec['id']}_check_{i + 1}.jpg"), quality=85)
        print(f"checks written, total {total:.1f}s"); return
    import soundfile as sf
    wav = os.path.join(M.CACHE, spec["id"] + ".wav"); sf.write(wav, audio(spec, segs, total), SR)
    out = os.path.join(out_dir, spec["id"] + ".mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        p.stdin.write(frame_at(spec, frames, segs, caps, total, fi / FPS).convert("RGB").tobytes())
    p.stdin.close(); p.wait(); print(f"{out}  {total:.1f}s")

if __name__ == "__main__":
    main()
