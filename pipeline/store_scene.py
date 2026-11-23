"""Supermarket scene for rules Reels, drawn in code (no image generation): a storefront with sliding doors, a shopper
pushing a cart who walks, stops, checks a phone and goes in and out of the store, a price tag over the cart, and a
phone card at the bottom that shows the shopper's numbers (balance vs safe-to-spend, today's number, tomorrow's).

Spec key "store" (all times are a sentence index `at` plus `delay` seconds, or `word` to start at a phrase):
{ "ground": 1335, "door_x": 880, "scale": 0.85,
  "moves": [{"at": 0, "delay": 0.2, "x": 880, "dur": 0, "cart": "full", "from_inside": true}, ...],
      # each move walks from the previous x to `x` over `dur` s; "inside": true fades the shopper into the store on
      # arrival, "from_inside": true fades them out of it at the start; "pose": "phone" while standing
  "tags": [{"at": 0, "delay": 1.0, "text": "$140", "end_at": 1, "end_delay": 1.0}],
  "card": {"y": 1500, "w": 780, "x": 520,
           "stages": [{"at": 2, "kind": "balance", "balance": "$1,240", "safe": "$38", "strike_word": "lying", "tick_word": "trust"}, ...]} }
"""
import math
from PIL import Image, ImageOps
from make_reel import W, S, INK, GREY, ORANGE, WHITE, font, appear
from make_beat_reel import mark, GREEN, RED
from make_split_reel import sprite, place, pop_scale

SKIN, HAIR, SHIRT, PANTS = (232, 188, 156), (64, 46, 40), (238, 124, 82), (54, 66, 98)
WIRE, WHEEL = (138, 150, 162), (58, 60, 66)
FACADE, TRIM, GLASS, GLASS_HI = (243, 236, 224), (214, 202, 186), (196, 222, 226), (226, 242, 244)
AWN_G = (52, 150, 104); SIDEWALK = (224, 220, 214)

def _smooth(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)

# ---------------------------------------------------------------- storefront
def draw_store(fr, ground, door_x, door_open):
    top = ground - 365
    fr.rrect([-10, top, W + 10, ground], 0, FACADE, 1)
    fr.rrect([-10, top, W + 10, top + 14], 0, TRIM, 1)                       # cornice
    fr.rrect([40, top + 26, 330, top + 82], 12, AWN_G, 1)                     # sign, left of the speaker
    fr.text((185, top + 54), "MARKET", font("xb", 38), WHITE, 1, anchor="mm", dy=0)
    ay = top + 100; sw = 60                                                   # striped awning with a scalloped edge
    for i, x in enumerate(range(-10, W + 10, sw)):
        col = AWN_G if i % 2 == 0 else (250, 250, 246)
        fr.rrect([x, ay, x + sw, ay + 40], 0, col, 1)
        fr.ellipse([x, ay + 22, x + sw, ay + 58], col + (fr.a(1),))
    wy0, wy1 = ay + 74, ground - 34
    for x0, x1 in ((30, 300), (330, door_x - 100)):                          # shop windows with produce shelves
        fr.rrect([x0 - 8, wy0 - 8, x1 + 8, wy1 + 8], 8, TRIM, 1)
        fr.rrect([x0, wy0, x1, wy1], 6, GLASS, 1)
        for sy in (wy0 + (wy1 - wy0) * 0.45, wy1 - 12):
            fr.rrect([x0 + 10, sy, x1 - 10, sy + 8], 3, (176, 150, 120), 1)
            cols = [(232, 84, 60), (250, 190, 60), (110, 180, 90), (240, 140, 50), (200, 60, 90)]
            n = int((x1 - x0 - 30) // 34)
            for j in range(n):
                cx = x0 + 26 + j * 34; c = cols[(j * 7 + int(sy)) % len(cols)]
                fr.ellipse([cx - 14, sy - 26, cx + 14, sy + 2], c + (fr.a(1),))
        fr.poly([(x0 + 20, wy0), (x0 + 70, wy0), (x0 + 20, wy0 + 60)], GLASS_HI + (fr.a(1),))
    dw, d0, d1 = 160, ay + 50, ground                                         # sliding doors
    fr.rrect([door_x - dw / 2 - 12, d0 - 12, door_x + dw / 2 + 12, d1], 6, TRIM, 1)
    fr.rrect([door_x - dw / 2, d0, door_x + dw / 2, d1], 2, (120, 132, 140), 1)   # dark interior
    fr.rrect([door_x - dw / 2 + 8, d0 + 40, door_x + dw / 2 - 8, d0 + 60], 3, (240, 232, 200), 1)  # lights inside
    sl = (dw / 2) * 0.92 * _smooth(door_open)
    for side in (-1, 1):
        inner = door_x + side * sl; outer = door_x + side * (dw / 2 + sl)
        a, b = sorted((inner, outer))
        fr.rrect([a, d0, b, d1], 2, GLASS, 1)
        fr.rrect([a + 6, d0 + 6, a + 16, d1 - 6], 3, GLASS_HI, 1)
    fr.rrect([-10, ground, W + 10, ground + 44], 0, SIDEWALK, 1)
    fr.rrect([-10, ground, W + 10, ground + 4], 0, TRIM, 1)

# ---------------------------------------------------------------- shopper + cart
SW, SH, FOOT = 300, 250, 236
def _paint_shopper(f, ph, cart, pose):
    s = math.sin(ph); bob = -4 * abs(math.sin(ph)) if pose == "walk" else 0
    hx, hip = 72, 160 + bob
    for k, sgn in ((0.85, -1), (1.0, 1)):                                     # legs
        fx = hx + sgn * (20 * s if pose == "walk" else 6)
        f.line([(hx, hip), (fx, FOOT - 4)], PANTS + (255,), 15)
        f.ellipse([fx - 9, FOOT - 10, fx + 13, FOOT], (40, 40, 44, 255))
    f.rrect([50, 88 + bob, 94, 166 + bob], 18, SHIRT, 1)                       # torso
    f.ellipse([47, 30 + bob, 97, 78 + bob], HAIR + (255,))                     # hair, then face
    f.ellipse([52, 40 + bob, 94, 86 + bob], SKIN + (255,))
    f.ellipse([48, 30 + bob, 96, 56 + bob], HAIR + (255,))
    f.ellipse([84, 56 + bob, 90, 62 + bob], (40, 30, 30, 255))                 # eye (facing right)
    # basket: back edge at x=128, front at x=280
    full = cart == "full"
    bx0, bx1, by0, by1 = 130, 284, 122, 196
    if full:                                                                   # the haul, behind the front wires
        items = [((150, 58, 186, 128), (224, 70, 50)), ((186, 74, 214, 128), (250, 200, 70)), ((214, 50, 240, 128), (90, 160, 210)),
                 ((238, 84, 272, 128), (250, 150, 60)), ((168, 90, 200, 128), (120, 190, 110))]
        for b, c in items: f.rrect(list(b), 6, c, 1)
        f.ellipse([196, 36, 236, 76], (90, 170, 90, 255))                      # melon
        f.line([(150, 50), (204, 30)], (214, 168, 110, 255), 12)               # baguette
        f.rrect([244, 58, 266, 92], 4, WHITE, 1); f.rrect([244, 52, 266, 62], 3, (60, 120, 210), 1)   # milk
    else:
        f.rrect([240, 92, 262, 128], 4, WHITE, 1); f.rrect([240, 86, 262, 96], 3, (60, 120, 210), 1)  # just the milk
    f.poly([(bx0, by0), (bx1, by0), (bx1 - 14, by1), (bx0 + 12, by1)], (228, 234, 240, 150))
    for x in range(bx0 + 18, bx1 - 4, 20):
        f.line([(x, by0), (x - 4 + (x - bx0) * -0.02, by1)], WIRE + (255,), 3)
    for y in (by0, by0 + 37, by1):
        f.line([(bx0 + (y - by0) * 0.16, y), (bx1 - (y - by0) * 0.19, y)], WIRE + (255,), 4)
    f.line([(bx0 + 12, by1), (bx0 + 8, 214), (bx1 - 20, 214)], WIRE + (255,), 5)
    for wx in (bx0 + 20, bx1 - 30):
        f.ellipse([wx - 11, 214, wx + 11, FOOT], WHEEL + (255,))
    f.line([(bx0, by0), (114, 108)], WIRE + (255,), 6)                          # handle
    f.rrect([104, 100, 122, 114], 5, (220, 70, 60), 1)
    f.line([(80, 104 + bob), (110, 108)], SKIN + (255,), 11)                    # near arm on the handle
    if pose == "phone":                                                         # other arm up, looking at the phone
        f.line([(80, 100), (100, 84), (104, 66)], SHIRT + (255,), 12)
        f.rrect([96, 44, 116, 76], 4, (36, 38, 44), 1); f.rrect([99, 48, 113, 72], 3, (150, 230, 190), 1)
    else:
        f.line([(66, 102 + bob), (100, 110)], SKIN + (255,), 10)

def shopper(ph_i, cart, pose, facing):
    key = ("shopper", ph_i, cart, pose)
    im = sprite(key, SW, SH, lambda f: _paint_shopper(f, ph_i / 12 * 2 * math.pi, cart, pose))
    return ImageOps.mirror(im) if facing < 0 else im

# ---------------------------------------------------------------- choreography
def state(sc, t, tm):
    """Shopper position, alpha, facing, cart and pose at time t. tm(item) -> start time of a move/tag."""
    moves = sc["moves"]; x, cart, pose, face, alpha, walking = moves[0]["x"], "empty", "stand", -1, 1.0, False
    prev_x = x
    for i, m in enumerate(moves):
        t0 = tm(m); dur = m.get("dur", 0)
        if t < t0: break
        cart = m.get("cart", cart)
        u = 1.0 if dur <= 0 else min(1.0, (t - t0) / dur)
        if m["x"] != prev_x: face = 1 if m["x"] > prev_x else -1
        x = prev_x + (m["x"] - prev_x) * _smooth(u); walking = 0 < u < 1 and m["x"] != prev_x
        pose = "walk" if walking else m.get("pose", "stand")
        alpha = 1.0
        if m.get("from_inside"): alpha = min(1.0, (t - t0) / 0.35)
        if m.get("inside") and u >= 1: alpha = max(0.0, 1 - (t - t0 - dur) / 0.35)
        if m.get("face"): face = m["face"]
        prev_x = m["x"]
    if t < tm(moves[0]) and moves[0].get("from_inside"): alpha = 0.0
    return x, alpha, face, cart, pose, walking

def draw_shopper_layer(fr, t, sc, tm):
    ground, door_x = sc.get("ground", 1335), sc.get("door_x", 880)
    x, alpha, face, cart, pose, walking = state(sc, t, tm)
    xs = [state(sc, tt, tm) for tt in (t - 0.45, t + 0.45)]                     # doors open around anyone near them
    near = max([max(0.0, 1 - (abs(s_[0] - door_x) - 50) / 120) * (1.0 if s_[1] > 0 else 0.0) for s_ in xs + [(x, alpha)]])
    draw_store(fr, ground, door_x, near)
    if alpha <= 0: return x
    ph_i = int((t * 2.2 * 12) % 12) if walking else 0
    sc_ = sc.get("scale", 0.85); im = shopper(ph_i, cart, pose, face)
    place(fr, im, x, ground - (FOOT - SH / 2) * sc_, sc_, alpha)
    return x

def draw_tags(fr, t, sc, tm):
    """Price tag over the shopper; drawn in front of the speaker so it is never hidden."""
    ground = sc.get("ground", 1335); sc_ = sc.get("scale", 0.85)
    x, alpha, face, cart, pose, walking = state(sc, t, tm)
    for tg in sc.get("tags", []):                                               # price tag over the cart
        t_in = tm(tg); t_out = tm({"at": tg["end_at"], "delay": tg.get("end_delay", 0)}) if "end_at" in tg else 1e9
        if t_in <= t <= t_out + 0.3:
            k = min(appear(t, t_in, 0.15), max(0.0, (t_out + 0.3 - t) / 0.3)) * alpha
            cx = x; cy = ground - 290 * sc_
            def paint(f, s=tg["text"]):
                f.rrect([0, 0, 170, 70], 35, WHITE, 1); f.rrect([0, 0, 170, 70], 35, (255, 255, 255), 1)
                f.text((85, 36), s, font("xb", 40), ORANGE, 1, anchor="mm", dy=0)
            place(fr, sprite(("tag", tg["text"]), 170, 70, paint), cx, cy, pop_scale(t - t_in, True), k)

# ---------------------------------------------------------------- phone card
def _count(a, b, u):
    return a + (b - a) * _smooth(u)

def draw_card(fr, t, sc, tm):
    cd = sc.get("card"); stages = cd["stages"] if cd else []
    cur, nxt = None, None
    for i, st in enumerate(stages):
        if t >= tm(st): cur = i
    if cur is None: return
    st = stages[cur]; t_in = tm(st)
    t_end = tm(stages[cur + 1]) if cur + 1 < len(stages) else (tm({"at": cd["end_at"], "delay": cd.get("end_delay", 0)}) if "end_at" in cd else 1e9)
    if t > t_end: return
    k = min(1.0, max(0.0, (t_end - t) / 0.25)) if t_end < 1e9 else 1.0
    w = cd.get("w", 780); kind = st["kind"]
    if kind == "hide": return
    rows, RH = 2, 86
    h = 84 + RH * rows
    strike = min(1.0, max(0.0, (t - tm({**st, "word": st["strike_word"], "delay": st.get("strike_delay", 0)})) / 0.4)) if st.get("strike_word") else 0
    tick = t >= tm({**st, "word": st["tick_word"], "delay": st.get("tick_delay", 0)}) if st.get("tick_word") else True
    cnt = min(1.0, max(0.0, (t - tm({**st, "word": st["count_word"], "delay": st.get("count_delay", 0)})) / 0.9)) if st.get("count_word") else 1.0
    save_on = t >= tm({**st, "word": st["save_word"], "delay": st.get("save_delay", 0)}) if st.get("save_word") else True
    sq = round(strike * 10); cq = round(cnt * 20)

    def paint(f):
        f.rrect([0, 0, w, h], 30, WHITE, 1)
        f.rrect([28, 24, 70, 66], 12, ORANGE, 1); f.text((49, 45), "$", font("xb", 30), WHITE, 1, anchor="mm", dy=0)
        f.text((88, 45), st.get("title", ""), font("b", 32), GREY, 1, anchor="lm", dy=0)
        def row(i, label, value, col, bold, hl=None, mk=None, strike_u=0):
            y = 80 + i * RH; cy = y + RH / 2
            if hl: f.rrect([16, y + 4, w - 16, y + RH - 4], 20, hl, 1)
            lf = font("xb" if bold else "b", 40); vf = font("xb", 52)
            f.text((40, cy), label, lf, INK if bold else GREY, 1, anchor="lm", dy=0)
            vx = w - (104 if mk is not None else 40)
            f.text((vx, cy), value, vf, col, 1, anchor="rm", dy=0)
            if strike_u > 0:
                vw = f.tl(value, vf); f.line([(vx - vw - 8, cy + 2), (vx - vw - 8 + (vw + 16) * strike_u, cy + 2)], RED + (255,), 6)
            if mk: mark(f, w - 56, cy, 28, mk, 1)
        if kind == "balance":
            row(0, "Balance", st["balance"], GREY, False, None, "x" if sq >= 10 else None, sq / 10)
            row(1, "Safe to spend today", st["safe"], GREEN, True, (226, 244, 233) if tick else None, "check" if tick else None)
        elif kind == "today":
            row(0, "Safe to spend today", st["safe"], GREEN, True, (226, 244, 233), "check")
            row(1, "Cart limit", st["safe"], INK, False)
        else:
            a, b = st["from"], st["to"]; v = round(_count(a, b, cq / 20))
            row(0, "Tomorrow's safe to spend", f"${v}", ORANGE if cq > 0 else GREEN, True, (255, 240, 228) if cq > 0 else None)
            row(1, "Savings", "untouched" if save_on else "", GREEN, False, None, "check" if save_on else None)
    key = ("pcard", cur, sq, tick, cq, save_on, w)
    place(fr, sprite(key, w, h, paint), cd.get("x", 520), cd.get("y", 1500), pop_scale(t - t_in, False), min(appear(t, t_in, 0.15), k))
