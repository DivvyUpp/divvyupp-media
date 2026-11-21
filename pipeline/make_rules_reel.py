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
PAIRS_TOP, PAIRS_BOT, PAIRS_R = 400, 1140, W - 80      # rule rows end above the button rail (y>=1150)
SPK_TOP, SPK_H = 1170, 700                             # speaker at the bottom; may run into covered areas

def card(w, h, text, ok, size):
    """One rule card. All cards in a Reel share the same size and font size (set by fit_size) so they read as a set."""
    def paint(f):
        f.rrect([0, 0, w, h], 24, SOFT_G if ok else SOFT_R, 1)
        f.rrect([0, 0, 10, h], 5, GREEN if ok else RED, 1)                 # colour edge on the left
        lines = wrap(f, text, "b", size, w - 112)[:2]
        lh = size * 1.2; y0 = h / 2 - lh * len(lines) / 2 + lh / 2
        for i, l in enumerate(lines):
            f.text((34, y0 + i * lh), l, font("b", size), INK if ok else (110, 92, 88), 1, anchor="lm", dy=0)
        mark(f, w - 44, h / 2, 24, "check" if ok else "x", 1)
    return sprite(("card", round(w), round(h), text, ok, round(size)), w, h, paint)

_IMG = {}
def prop(path, h):
    k = (path, h)
    if k not in _IMG:
        im = Image.open(path if os.path.isabs(path) else os.path.join(ROOT, path)).convert("RGBA")
        bb = im.getbbox(); im = im.crop(bb) if bb else im
        _IMG[k] = im.resize((int(im.width * h * S / im.height), int(h * S)), Image.LANCZOS)
    return _IMG[k]

TEAL = (22, 140, 130)
def notif(w, h, text, stage, n, sub, color=None):
    """A generic delivery notification (our own design, no third-party branding): icon, 'Delivery · now', the
    message, and an n-step progress tracker with `stage` steps filled."""
    AC = tuple(color) if color else TEAL
    def paint(f):
        f.rrect([0, 0, w, h], 30, WHITE, 1)
        f.rrect([22, 22, 86, 86], 18, AC, 1)                                   # app icon: a simple bag glyph
        f.rrect([38, 46, 70, 74], 5, WHITE, 1); f.line([(46, 46), (46, 38), (62, 38), (62, 46)], WHITE + (255,), 4)
        f.text((104, 22), sub, font("b", 24), GREY, 1, dy=0)
        f.text((104, 52), text, font("xb", fit(f, text, "xb", 36, w - 130)), INK, 1, dy=0)
        x0, x1, yy = 104, w - 40, h - 30
        f.line([(x0, yy), (x1, yy)], (225, 220, 216, 255), 6)
        if stage > 1: f.line([(x0, yy), (x0 + (x1 - x0) * (stage - 1) / (n - 1), yy)], AC + (255,), 6)
        for i in range(n):
            cx = x0 + (x1 - x0) * i / (n - 1); r = 11 if i < stage else 8
            f.ellipse([cx - r, yy - r, cx + r, yy + r], (AC if i < stage else (225, 220, 216)) + (255,))
    return sprite(("notif", round(w), round(h), text, stage, n, sub, AC), w, h, paint)

import random as _rnd
def scenery(seed=4, length=2600):
    """Simple flat scenery (buildings, trees, lamp posts) laid out along a loop of `length` px."""
    r = _rnd.Random(seed); far, near, x = [], [], 0
    while x < length:
        w_ = r.randint(110, 190); h_ = r.randint(140, 260)
        far.append((x, w_, h_, r.choice([(236, 214, 205), (226, 220, 232), (214, 228, 226), (240, 226, 206)]))); x += w_ + r.randint(10, 40)
    x = 0
    while x < length:
        near.append((x, r.choice(["tree", "tree", "lamp"]))); x += r.randint(170, 300)
    return far, near

def fit_size(fr, texts, w, h, start=46):
    """Largest font size at which every card's text fits in two lines."""
    size = start
    while size > 24:
        if all(len(wrap(fr, tx, "b", size, w - 112)) <= 2 for tx in texts) and size * 2.5 < h: return size
        size -= 1
    return size

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
        # rule pairs: the good way always on the left, the bad way always on the right
        PT = spec.get("pairs_top", PAIRS_TOP)
        prs = spec.get("pairs", []); first = min((cue(p["at"], p.get("delay", 0.0)) for p in prs), default=total)
        if prs and not title and t >= first:
            cw = (PAIRS_R - SAFE_L - 24) / 2; lab_h = 0; gap = 18
            rh = min(160, (spec.get("pairs_bot", PAIRS_BOT) - PT - 70 - len(prs) * (lab_h + gap)) / len(prs))
            fs = fit_size(fr, [x for p in prs for x in (p["good_text"], p["bad_text"])], cw, rh)
            hk = appear(t, first - 0.1, 0.25)
            for side, txt, col in ((0, "DO THIS", GREEN), (1, "NOT THIS", RED)):
                x = SAFE_L + side * (cw + 24)
                fr.text((x + cw / 2, PT + 14), txt, font("xb", 34), col, hk, anchor="ma", dy=0)
            for j, p in enumerate(prs):
                t_in = cue(p["at"], p.get("delay", 0.0))
                if t < t_in: continue
                y = PT + 70 + j * (rh + lab_h + gap); age = t - t_in
                for side, ok, txt in ((0, True, p["good_text"]), (1, False, p["bad_text"])):
                    x = SAFE_L + side * (cw + 24); a2 = age - (0.0 if ok else 0.18)    # ✓ first, then ✗
                    if a2 < 0: continue
                    place(fr, card(cw, rh, txt, ok, fs), x + cw / 2, y + lab_h + rh / 2, pop_scale(a2, False), appear(t, t_in + (0 if ok else 0.18), 0.12))
        for fl in spec.get("fly", []):                                           # a prop crossing the screen on a road
            t0 = cue(fl["at"], fl.get("delay", 0.0)); din, hold, dout = fl.get("dur_in", fl.get("dur", 2.8) / 2), fl.get("hold", 0.0), fl.get("dur_out", fl.get("dur", 2.8) / 2)
            t1 = t0 + din + hold + dout
            if t0 - 0.3 <= t <= t1 + 0.3:
                im = prop(fl["img"], fl.get("h", 260)); pw = im.width / S
                start, stop, end = W + pw / 2, fl.get("stop_x", W / 2), -pw / 2
                if t < t0: cx = start
                elif t < t0 + din: u = (t - t0) / din; cx = start + (stop - start) * (1 - (1 - u) ** 2)          # ease out into the stop
                elif t < t0 + din + hold: cx = stop
                elif t <= t1: u = (t - t0 - din - hold) / dout; cx = stop + (end - stop) * u * u                 # ease in away
                else: cx = end
                road_y = fl["y"] + fl.get("h", 260) * 0.46; rk = min(1, (t - (t0 - 0.3)) / 0.3, (t1 + 0.3 - t) / 0.3)
                fr.rrect([0, road_y - 4, W, road_y + 30], 0, (92, 88, 92), rk)
                moving = (t0 <= t < t0 + din) or (t0 + din + hold < t <= t1)
                off = ((t * 420) % 120) if moving else ((t0 + din) * 420 % 120)
                for xx in np.arange(-120 + off, W + 120, 120):
                    fr.rrect([xx, road_y + 10, xx + 60, road_y + 16], 3, (245, 240, 230), rk)
                bob = 5 * np.sin((t - t0) * 18) if moving else 0
                if t0 <= t <= t1:
                    fr.layer.alpha_composite(im, (int(cx * S - im.width / 2), int((fl["y"] + bob) * S - im.height / 2)))
        for dp in spec.get("drop", []):                                          # a prop that lands and stays
            t_in = cue(dp["at"], dp.get("delay", 0.0))
            if t >= t_in:
                place(fr, prop(dp["img"], dp.get("h", 200)), dp["x"], dp["y"], pop_scale(t - t_in, True), appear(t, t_in, 0.12))
                if dp.get("tag"):
                    tf = font("xb", 24); tw_ = fr.tl(dp["tag"], tf); k = appear(t, t_in + 0.2, 0.2)
                    ty = dp["y"] + dp.get("h", 200) / 2 + 8
                    fr.rrect([dp["x"] - tw_ / 2 - 14, ty, dp["x"] + tw_ / 2 + 14, ty + 40], 20, WHITE, k)
                    fr.text((dp["x"], ty + 20), dp["tag"], tf, INK, k, anchor="mm", dy=0)
        sc_ = spec.get("scene")
        if sc_:
            stop_t = cue(sc_["stop_at"], sc_.get("stop_delay", 0.0)) if sc_.get("stop_at") is not None else 1e9
            speed = sc_.get("speed", 240)
            dist = speed * min(t, stop_t) if t < stop_t + 0.6 else speed * stop_t       # world distance travelled
            if stop_t <= t < stop_t + 0.6: dist = speed * stop_t + speed * 0.3 * (1 - (1 - (t - stop_t) / 0.6) ** 2)   # brake
            far, near = scenery(); L = 2600; y0, yr = sc_["y_top"], sc_["y_road"]
            for (x, w_, h_, col) in far:                                        # far buildings, slow parallax
                xx = (x + dist * 0.35) % L - 300
                if -w_ < xx < W: fr.rrect([xx, yr - h_, xx + w_, yr], 10, col, 1)
            for (x, kind) in near:                                              # trees and lamp posts, full speed
                xx = (x + dist) % L - 300
                if not (-120 < xx < W + 120): continue
                if kind == "tree":
                    fr.rrect([xx - 7, yr - 90, xx + 7, yr], 4, (150, 110, 80), 1); fr.ellipse([xx - 48, yr - 175, xx + 48, yr - 75], (120, 178, 120, 255))
                else:
                    fr.rrect([xx - 4, yr - 190, xx + 4, yr], 3, (120, 120, 126), 1); fr.ellipse([xx - 16, yr - 205, xx + 16, yr - 180], (250, 226, 150, 255))
            fr.rrect([0, yr - 2, W, yr + 42], 0, (92, 88, 92), 1)                # road
            for xx in np.arange(-150 + (dist % 150), W + 150, 150): fr.rrect([xx, yr + 17, xx + 70, yr + 23], 3, (245, 240, 230), 1)
            rd = sc_["rider"]; im = prop(rd["img"], rd.get("h", 220)); pw = im.width / S
            t_e = cue(rd.get("enter_at", 0), rd.get("enter_delay", 0.3)); de = rd.get("enter_dur", 1.6)
            if t >= t_e:
                u = min(1.0, (t - t_e) / de); cx = W + pw / 2 + (rd["x"] - W - pw / 2) * (1 - (1 - u) ** 3)
                moving = t < stop_t
                bob = 4 * np.sin(t * 16) if moving else 0
                fr.layer.alpha_composite(im, (int(cx * S - im.width / 2), int((yr - rd.get("h", 220) / 2 + 12 + bob) * S - im.height / 2)))
        mood = phase(spec.get("moods"), t, "mood") or "happy"
        character(fr.layer, W / 2, spec.get("spk_top", SPK_TOP), spec.get("spk_h", SPK_H), t, vis[min(f, n - 1)], mood, fr.g, spec["character"])
        tr = spec.get("tracker")
        if tr:
            stp = tr["steps"]; nw, nh = tr.get("w", 820), tr.get("h", 132)
            for i_, st_ in enumerate(stp):
                t_in = cue(st_["at"], st_.get("delay", 0.0))
                t_end = min(t_in + st_.get("hold", tr.get("hold", 2.6)), cue(stp[i_ + 1]["at"], stp[i_ + 1].get("delay", 0.0)) if i_ + 1 < len(stp) else 1e9)
                if t_in <= t <= t_end:
                    k = min(appear(t, t_in, 0.12), max(0.0, min(1.0, (t_end - t) / 0.25)))
                    im = notif(nw, nh, st_["text"], i_ + 1, len(stp), tr.get("sub", "Dollar Bill's order"), tr.get("color"))
                    place(fr, im, tr.get("x", W / 2), tr.get("y", 1480), pop_scale(t - t_in, False), k)
        rc = spec.get("receipt")
        if rc and t >= cue(rc["at"], rc.get("delay", 0.0)):
            t_in = cue(rc["at"], rc.get("delay", 0.0)); rw, rh_ = rc.get("w", 330), 60 + 44 * (len(rc["items"]) + 2)
            def paint_r(f, rc=rc, rw=rw, rh_=rh_):
                f.rrect([0, 0, rw, rh_], 10, WHITE, 1)
                f.text((rw / 2, 18), rc["title"], font("xb", 26), INK, 1, anchor="ma", dy=0)
                f.line([(20, 56), (rw - 20, 56)], (200, 195, 190, 255), 2)
                for j, (item, price) in enumerate(rc["items"]):
                    f.text((20, 72 + j * 44), item, font("b", fit(f, item, "b", 24, rw - 110)), INK, 1, dy=0)
                    f.text((rw - 20, 72 + j * 44), price, font("b", 24), INK, 1, anchor="ra", dy=0)
                yy = 72 + len(rc["items"]) * 44
                f.line([(20, yy), (rw - 20, yy)], (200, 195, 190, 255), 2)
                f.text((20, yy + 12), rc["total"][0], font("xb", 26), INK, 1, dy=0)
                f.text((rw - 20, yy + 12), rc["total"][1], font("xb", 26), INK, 1, anchor="ra", dy=0)
                f.text((rw / 2, yy + 54), rc["footer"], font("xb", fit(f, rc["footer"], "xb", 24, rw - 30)), GREEN, 1, anchor="ma", dy=0)
            place(fr, sprite(("receipt", rc["title"], tuple(map(tuple, rc["items"]))), rw, rh_, paint_r), rc["x"], rc["y"],
                  pop_scale(t - t_in, True), appear(t, t_in, 0.15))
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
        extra = [cue(st_["at"], st_.get("delay", 0.0)) for st_ in (spec.get("tracker") or {}).get("steps", [])] + \
                [cue(dp["at"], dp.get("delay", 0.0)) for dp in spec.get("drop", [])]
        for tt in extra:
            i0 = int(max(tt, 0) * sr)
            if i0 < len(full): full[i0:i0 + len(tk)] += tk[:len(full) - i0] * 1.3
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
