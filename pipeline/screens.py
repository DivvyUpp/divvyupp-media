"""DivvyUpp app screens redrawn in the current brand (cream, orange #E04A1A, near-black, Plus Jakarta Sans), for the
explainer. render(name, w, h) -> RGB image. Drawn at 2x on a 390pt-wide layout and downscaled."""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, ".cache/fonts/package/files/plus-jakarta-sans-latin-%s-normal.woff")
INK = (21, 16, 15); ORANGE = (224, 74, 26); GREY = (110, 104, 100); LINE = (236, 228, 222); CREAM = (255, 250, 247)
TINT = (255, 240, 232); GREEN = (30, 140, 80); GREEN_T = (226, 244, 233); AMBER = (196, 122, 16); AMBER_T = (253, 241, 214)
RED = (200, 40, 30); RED_T = (252, 228, 225); WHITE = (255, 255, 255)
BASE_W = 390
_fc = {}

class C:
    def __init__(self, w, h):
        self.k = w / BASE_W * 2; self.im = Image.new("RGB", (w * 2, h * 2), CREAM); self.d = ImageDraw.Draw(self.im)
        self.h = h * 2 / self.k
    def f(self, w, s):
        key = (w, round(s * self.k))
        if key not in _fc: _fc[key] = ImageFont.truetype(FD % w, round(s * self.k))
        return _fc[key]
    def P(self, *v): return [x * self.k for x in v]
    def text(self, xy, s, w, size, fill=INK, anchor="la"): self.d.text(self.P(*xy), s, font=self.f(w, size), fill=fill, anchor=anchor)
    def rr(self, box, r, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(self.P(*box), r * self.k, fill=fill, outline=outline, width=max(1, int(width * self.k)))
    def line(self, pts, fill, width): self.d.line([tuple(self.P(*p)) for p in pts], fill=fill, width=int(width * self.k), joint="curve")
    def circle(self, cx, cy, r, fill): self.d.ellipse(self.P(cx - r, cy - r, cx + r, cy + r), fill=fill)

def logo(c, x, y, s=28):
    c.rr([x, y, x + s, y + s], s * 0.28, fill=ORANGE)
    cx = x + s / 2; sw = s * 0.11; top, bot = y + s * 0.27, y + s * 0.73; arm = s * 0.19
    for a, b in (((cx, top), (cx, bot)), ((cx - arm, top + arm), (cx, top)), ((cx, top), (cx + arm, top + arm))): c.line([a, b], WHITE, sw)
    for px, py in ((cx, bot), (cx - arm, top + arm), (cx + arm, top + arm), (cx, top)): c.circle(px, py, sw / 2, WHITE)

def status_bar(c):
    c.text((34, 22), "9:41", 700, 15)
    for i, hh in enumerate((5, 8, 11, 14)): c.rr([300 + i * 6, 34 - hh, 304 + i * 6, 34], 1, fill=INK)
    c.rr([334, 22, 360, 34], 3, outline=INK, width=1.5); c.rr([336, 24, 354, 32], 2, fill=INK)

def app_header(c, title=None):
    status_bar(c)
    logo(c, 20, 56); c.text((56, 70), "DivvyUpp", 800, 19, anchor="lm")
    c.circle(358, 70, 12, TINT); c.rr([352, 63, 364, 76], 5, outline=ORANGE, width=2)
    c.line([(20, 98), (370, 98)], LINE, 1)
    if title: c.text((20, 116), title, 800, 24)

def nav(c, active=0):
    y = c.h - 70; c.line([(0, y), (390, y)], LINE, 1)
    for i, lab in enumerate(("Home", "Activity", "Insights", "Profile")):
        x = 49 + i * 97; col = ORANGE if i == active else GREY
        c.rr([x - 9, y + 14, x + 9, y + 30], 4, outline=col, width=2)
        c.text((x, y + 44), lab, 700, 11, fill=col, anchor="ma")

def dashboard(c, tab, update=False):
    app_header(c)
    c.circle(26, 120, 6, ORANGE); c.text((38, 120), "6 day streak", 700, 13, anchor="lm")
    c.text((370, 120), "in bank", 500, 12, fill=GREY, anchor="rm")
    c.text((370 - c.d.textlength("in bank", font=c.f(500, 12)) / c.k - 5, 120), "$6,394.60" if update else "$6,400.00", 800, 13, anchor="rm")
    c.rr([16, 140, 374, 420], 24, fill=TINT)
    c.rr([30, 154, 360, 192], 19, fill=WHITE)
    labs = ("Today", "This Week", "This Month")
    for i, lab in enumerate(labs):
        x0 = 32 + i * 109.3
        if i == tab: c.rr([x0, 156, x0 + 107, 190], 17, fill=ORANGE)
        c.text((x0 + 53.5, 173), lab, 700, 13, fill=WHITE if i == tab else GREY, anchor="mm")
    c.text((195, 218), ("SAFE TO SPEND TODAY", "SAFE TO SPEND THIS WEEK", "SAFE TO SPEND THIS MONTH")[tab], 800, 12, fill=ORANGE, anchor="mm")
    c.text((195, 268), (("$81.26", "$471.57", "$2,544.25") if update else ("$86.66", "$476.97", "$2,549.65"))[tab], 800, 52, anchor="mm")
    c.circle(42, 318, 8, GREEN); c.line([(38, 318), (41, 321), (46, 314)], WHITE, 2)
    c.text((58, 318), "On track to save your $1,200/month goal", 600, 12.5, fill=GREEN, anchor="lm")
    c.rr([32, 346, 358, 396], 25, fill=ORANGE); c.text((195, 371), "Can I spend?", 800, 16, fill=WHITE, anchor="mm")
    for i, (lab, val, sub, frac) in enumerate((("Spent so far", "$5.40" if update else "$0", "of $86.66 today", 0.06 if update else 0.0), ("Saved so far", "$300", "of $1,200 this month", 0.25))):
        x = 16 + i * 183; c.rr([x, 436, x + 175, 540], 18, fill=WHITE, outline=LINE, width=1)
        c.text((x + 14, 452), lab, 600, 12, fill=GREY); c.text((x + 14, 470), val, 800, 24, fill=INK if i == 0 else ORANGE)
        c.text((x + 14, 504), sub, 500, 11, fill=GREY)
        c.rr([x + 14, 522, x + 161, 528], 3, fill=LINE)
        if frac: c.rr([x + 14, 522, x + 14 + 147 * frac, 528], 3, fill=ORANGE)
    c.text((20, 566), "Upcoming bills", 800, 16)
    for i, (n_, d_, a_) in enumerate((("Mortgage", "Due Dec 1", "$2,850.00"), ("Car payment", "Due Dec 3", "$480.00"), ("Electric & gas", "Due Dec 6", "$210.00"))):
        y = 594 + i * 58; c.rr([16, y, 374, y + 50], 14, fill=WHITE, outline=LINE, width=1)
        c.text((32, y + 17), n_, 700, 13.5); c.text((32, y + 35), d_, 500, 11, fill=GREY); c.text((358, y + 25), a_, 800, 13.5, anchor="rm")
    if update:   # a transaction just came in; every number above has already moved
        c.rr([22, 548, 368, 610], 18, fill=INK)
        c.circle(52, 579, 15, ORANGE); c.text((52, 579), "$", 800, 15, fill=WHITE, anchor="mm")
        c.text((78, 568), "Coffee shop  -$5.40", 800, 14, fill=WHITE, anchor="lm")
        c.text((78, 590), "Just now · Today, week and month updated", 500, 11.5, fill=(220, 210, 205), anchor="lm")
    nav(c, 0)

def report(c):
    """A generic budgeting app's lock-screen notification that arrives after the month is over."""
    c.d.rectangle(c.P(0, 0, 390, c.h), fill=(54, 58, 72))
    for i in range(40):                                              # soft vertical gradient
        c.d.rectangle(c.P(0, c.h * i / 40, 390, c.h * (i + 1) / 40), fill=(54 + i, 58 + i, 72 + i))
    status_bar_light = lambda: None
    c.text((195, 96), "Saturday, November 1", 600, 16, fill=(235, 235, 240), anchor="mm")
    c.text((195, 160), "9:41", 700, 76, fill=WHITE, anchor="mm")
    c.rr([16, 250, 374, 360], 22, fill=(248, 247, 250))
    c.rr([32, 266, 56, 290], 6, fill=(150, 150, 160)); c.text((66, 278), "BUDGET APP", 700, 12, fill=GREY, anchor="lm")
    c.text((358, 278), "now", 500, 12, fill=GREY, anchor="rm")
    c.text((32, 308), "Your October recap is ready", 800, 15, anchor="lm")
    c.text((32, 334), "You overspent by $612 last month.", 600, 14, fill=RED, anchor="lm")
    c.rr([95, 420, 295, 480], 30, outline=(255, 120, 110), width=3)
    c.text((195, 450), "A MONTH TOO LATE", 800, 17, fill=(255, 150, 140), anchor="mm")
    c.text((195, 520), "The money is already gone.", 600, 15, fill=(220, 220, 228), anchor="mm")

def plan(c, step):
    app_header(c, "Your plan")
    rows = [("Monthly take-home", "$10,000.00", "Checked against your bank", GREEN, INK),
            ("Fixed bills", "$6,250.35", "Mortgage, car payment, utilities", GREEN, INK),
            ("Flexible money", "$3,749.65", "What's left after bills", GREY, INK),
            ("Savings goal", "$1,200.00", "You choose. It comes out first", GREY, ORANGE),
            ("Safe to spend", "$2,549.65", "About $477 a week, $87 a day", GREY, GREEN)]
    shown = {1: 1, 2: 2, 3: 3, 4: 5}.get(step, 5)
    for i, (lab, val, sub, subc, valc) in enumerate(rows[:shown]):
        y = 160 + i * 92; hl = i == shown - 1
        c.rr([16, y, 374, y + 80], 18, fill=TINT if hl else WHITE, outline=ORANGE if hl else LINE, width=2 if hl else 1)
        c.text((32, y + 20), lab, 700, 14, fill=GREY); c.text((358, y + 22), val, 800, 22, fill=valc, anchor="ra")
        if i < 2: c.circle(40, y + 56, 7, GREEN); c.line([(36, y + 56), (39, y + 59), (44, y + 52)], WHITE, 2); c.text((54, y + 56), sub, 600, 12, fill=GREEN, anchor="lm")
        else: c.text((32, y + 56), sub, 500, 12, fill=subc, anchor="lm")
    if shown >= 3:
        y = 160 + 5 * 92 + 10; tot = 10000
        c.text((20, y), "Where every dollar goes", 800, 14); x = 20
        for v, col in ((6250.35, (196, 186, 178)), (1200, ORANGE), (2549.65, GREEN)):
            if v == 1200 and shown < 4: col = (230, 220, 214)
            if v == 2549.65 and shown < 5: col = (240, 232, 226)
            w = 350 * v / tot; c.d.rectangle(c.P(x, y + 28, x + w, y + 46), fill=col); x += w
    nav(c, 0)

def ask(c, amount=None, what=None, result=None):
    app_header(c, "Can I spend?")
    c.rr([16, 160, 374, 252], 20, fill=WHITE, outline=ORANGE if amount and not result else LINE, width=2)
    c.text((195, 190), "AMOUNT", 800, 11, fill=GREY, anchor="mm")
    c.text((195, 226), amount or "$0", 800, 38, fill=INK if amount else (200, 192, 186), anchor="mm")
    c.rr([16, 264, 374, 304], 14, fill=WHITE, outline=LINE, width=1)
    c.text((32, 284), "For", 600, 13, fill=GREY, anchor="lm"); c.text((76, 284), what or "What's it for?", 700, 13, fill=INK if what else (200, 192, 186), anchor="lm")
    if result is None:
        keys = "123456789.0<"
        for i, kk in enumerate(keys):
            x = 16 + (i % 3) * 121; y = 322 + (i // 3) * 64
            c.rr([x, y, x + 115, y + 56], 16, fill=WHITE, outline=LINE, width=1)
            if kk == "<": c.text((x + 57.5, y + 28), "del", 600, 15, fill=GREY, anchor="mm")
            else: c.text((x + 57.5, y + 28), kk, 700, 22, anchor="mm")
        c.rr([16, 590, 374, 640], 25, fill=ORANGE if amount else (240, 200, 184)); c.text((195, 615), "Check it", 800, 16, fill=WHITE, anchor="mm")
        return
    if result == "checking":
        c.text((20, 336), "Checking...", 800, 18)
        for i, lab in enumerate(("Your budget for today and this week", "Your bank balance", "Your upcoming bills")):
            y = 372 + i * 58; c.rr([16, y, 374, y + 48], 14, fill=WHITE, outline=LINE, width=1)
            c.circle(40, y + 24, 9, GREEN); c.line([(35, y + 24), (39, y + 28), (45, y + 19)], WHITE, 2.2); c.text((60, y + 24), lab, 600, 13, anchor="lm")
        return
    col, tint, head, lines = {
        "yes": (GREEN, GREEN_T, "Go for it", ["You can afford this.", "Fits today's $86.66", "Bills covered, savings on track"]),
        "yesbut": (AMBER, AMBER_T, "Yes, but...", ["Over today's $86.66", "Still fits this week's $476.97", "Tomorrow adjusts to keep you on track"]),
        "no": (RED, RED_T, "Don't do it", ["$3,540 in bills due this week", "Checking would drop below $0", "Your $1,200 savings goal would slip"]),
    }[result]
    c.rr([16, 322, 374, 560], 22, fill=tint)
    c.circle(48, 356, 16, col)
    if result == "no": c.line([(42, 350), (54, 362)], WHITE, 3); c.line([(54, 350), (42, 362)], WHITE, 3)
    elif result == "yesbut": c.text((48, 356), "!", 800, 20, fill=WHITE, anchor="mm")
    else: c.line([(41, 356), (46, 362), (56, 349)], WHITE, 3)
    c.text((74, 356), head, 800, 24, fill=col, anchor="lm")
    for i, l in enumerate(lines):
        y = 404 + i * 46; c.line([(32, y - 14), (358, y - 14)], (255, 255, 255), 1)
        c.text((32, y + 6), l, 700 if i == 0 else 600, 15 if i == 0 else 13.5, fill=INK, anchor="lm")
    c.rr([16, 586, 374, 636], 25, outline=ORANGE, width=2); c.text((195, 611), "Ask about something else", 800, 15, fill=ORANGE, anchor="mm")
    nav(c, 0)

def cta(c):
    status_bar(c)
    logo(c, 155, 170, 80); c.text((195, 290), "DivvyUpp", 800, 30, anchor="mm")
    c.text((195, 336), "Save more. Spend less.", 800, 20, fill=ORANGE, anchor="mm")
    c.rr([28, 400, 362, 470], 20, fill=TINT); c.text((195, 435), "divvyupp.com", 800, 26, anchor="mm")
    c.rr([28, 490, 362, 546], 28, fill=ORANGE); c.text((195, 518), "Get Started", 800, 18, fill=WHITE, anchor="mm")
    c.text((195, 580), "Free during beta · No card needed", 700, 14, fill=GREEN, anchor="mm")

SCREENS = {
    "report": report, "dashboard_today": lambda c: dashboard(c, 0), "dashboard_week": lambda c: dashboard(c, 1),
    "dashboard_month": lambda c: dashboard(c, 2),
    "dashboard_update": lambda c: dashboard(c, 0, update=True),
    "plan_1": lambda c: plan(c, 1), "plan_2": lambda c: plan(c, 2), "plan_3": lambda c: plan(c, 3), "plan_4": lambda c: plan(c, 4),
    "ask_blank": lambda c: ask(c), "ask_60": lambda c: ask(c, "$60", "Dinner out"),
    "ask_60_check": lambda c: ask(c, "$60", "Dinner out", "checking"), "ask_60_yes": lambda c: ask(c, "$60", "Dinner out", "yes"),
    "ask_250": lambda c: ask(c, "$250", "New jacket"), "ask_250_yes": lambda c: ask(c, "$250", "New jacket", "yesbut"),
    "ask_6000": lambda c: ask(c, "$6,000", "Dream vacation"), "ask_6000_no": lambda c: ask(c, "$6,000", "Dream vacation", "no"),
    "cta": cta,
}

def render(name, w, h):
    c = C(w, h); SCREENS[name](c)
    return c.im.resize((w, h), Image.LANCZOS)

if __name__ == "__main__":
    import sys
    out = sys.argv[1]; names = list(SCREENS); w, h = 452, 972
    sheet = Image.new("RGB", ((w + 20) * 6, (h + 20) * ((len(names) + 5) // 6)), (60, 60, 60))
    for i, n in enumerate(names): sheet.paste(render(n, w, h), ((i % 6) * (w + 20) + 10, (i // 6) * (h + 20) + 10))
    sheet.save(out, quality=85)
