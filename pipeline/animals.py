"""Original animal presenters for story Reels (same contract as characters.py: bust, only the face moves).

svg(name, mouth, blink, mood) -> SVG string on a 600x720 canvas. mouth = viseme name (rest, M, A, E, O, U, F, S, L)
or a 0-3 openness level; mood = neutral | happy | worried | unimpressed.

    python3 pipeline/animals.py lineup out.jpg
"""
import io, sys
from functools import lru_cache
from PIL import Image

INK = "#1E1714"
VIS = {"A": (1.0, 1.0, False), "E": (1.1, 0.62, False), "O": (0.7, 0.92, True), "U": (0.5, 0.58, True),
       "F": (1.0, 0.4, False), "S": (0.95, 0.4, False), "L": (0.92, 0.66, False)}

ANIMALS = {
    "koala": dict(label="Koala", fur="#A3A8AE", fur_d="#868B92", light="#E6E7E5", nose="#2E2C31", iris="#3B2A20",
                  outfit="hoodie", top="#E8A87C", top_d="#D18E62", sleepy=True),
    "llama": dict(label="Llama", fur="#F1E4CC", fur_d="#DCC9A8", light="#FBF4E6", nose="#5B4636", iris="#3A2A1E",
                  outfit="scarf", top="#E04A1A", top_d="#B93A12", lashes=True),
    "raccoon": dict(label="Raccoon", fur="#9A9CA3", fur_d="#7C7E86", light="#F1EFEA", nose="#26232A", iris="#5A3A1E",
                    outfit="denim", top="#5D7FA6", top_d="#4A6A8F"),
    "raccoon_tweed": dict(label="Brown tweed", fur="#9A9CA3", fur_d="#7C7E86", light="#F1EFEA", nose="#26232A", iris="#5A3A1E",
                    outfit="tweed", top="#7A5A40", top_d="#5E4430", tweed_fleck="#A88466", tie="#E04A1A", cap="#8B6A4E", cap_line="#E04A1A"),
    "raccoon_orange": dict(label="Orange tweed", fur="#9A9CA3", fur_d="#7C7E86", light="#F1EFEA", nose="#26232A", iris="#5A3A1E",
                    outfit="tweed", top="#C8562C", top_d="#A44423", tweed_fleck="#E58A5E", tie="#2E3A4F", cap="#C8562C", cap_line="#2E3A4F"),
    "raccoon_fluffy": dict(label="Fluffy raccoon", fur="#9EA1A8", fur_d="#7D8088", fur_dd="#5F626B", light="#F2F0EC",
                    belly="#C9CBCF", nose="#26232A", iris="#5A3A1E"),
    "capybara": dict(label="Capybara", fur="#B07E55", fur_d="#94653F", light="#C99A70", nose="#4A3326", iris="#2C1D14",
                     outfit="tee", top="#3F5E58", top_d="#314B46"),
    "otter": dict(label="Otter", fur="#8A5D3B", fur_d="#6F4829", light="#EBD6B8", nose="#2B1E18", iris="#2A1A12",
                  outfit="vest", top="#2E3A4F", top_d="#222C3D"),
}

# ---------- shared parts ----------
def _shoulders(c):
    t, td = c["top"], c["top_d"]; o = c["outfit"]
    base = (f'<path d="M70,720 C70,600 150,520 240,500 L360,500 C450,520 530,600 530,720Z" fill="{t}"/>'
            f'<path d="M70,720 C70,640 110,580 170,548 C150,600 146,660 150,720Z" fill="{td}" opacity=".55"/>'
            f'<path d="M530,720 C530,640 490,580 430,548 C450,600 454,660 450,720Z" fill="{td}" opacity=".55"/>')
    if o == "hoodie":
        base += (f'<path d="M210,505 C230,560 370,560 390,505 C380,540 350,566 300,568 C250,566 220,540 210,505Z" fill="{td}"/>'
                 f'<path d="M270,560 L262,640" stroke="#FFF4EC" stroke-width="7" stroke-linecap="round"/>'
                 f'<path d="M330,560 L338,640" stroke="#FFF4EC" stroke-width="7" stroke-linecap="round"/>'
                 f'<circle cx="262" cy="646" r="7" fill="#FFF4EC"/><circle cx="338" cy="646" r="7" fill="#FFF4EC"/>')
    elif o == "scarf":
        base += (f'<path d="M196,470 C250,520 350,520 404,470 L414,512 C350,566 250,566 186,512Z" fill="{t}"/>'
                 f'<path d="M190,494 C250,540 350,540 410,494" stroke="#F6C64F" stroke-width="9" fill="none"/>'
                 f'<path d="M360,520 L392,650 L344,654 L330,528Z" fill="{t}"/>'
                 f'<path d="M346,560 L384,556 M352,590 L388,586 M356,620 L390,616" stroke="#F6C64F" stroke-width="8"/>'
                 f'<path d="M346,654 L344,672 M360,653 L360,672 M374,652 L376,671 M388,651 L392,670" stroke="{td}" stroke-width="5" stroke-linecap="round"/>')
    elif o == "denim":
        base += (f'<path d="M232,500 L300,600 L368,500 L352,500 L300,572 L248,500Z" fill="#F1EFEA"/>'
                 f'<path d="M232,500 L196,560 L250,560 L300,600Z" fill="{td}"/><path d="M368,500 L404,560 L350,560 L300,600Z" fill="{td}"/>'
                 f'<path d="M150,640 L230,640 M370,640 L450,640" stroke="#E8B04A" stroke-width="4" stroke-dasharray="8 7"/>')
    elif o == "tweed":
        tf, tie = c["tweed_fleck"], c["tie"]
        base = (f'<defs><pattern id="hb" width="16" height="16" patternUnits="userSpaceOnUse">'
                f'<path d="M0,16 L8,0 M8,16 L16,0" stroke="{tf}" stroke-width="2" opacity=".55"/>'
                f'<path d="M0,0 L8,16 M8,0 L16,16" stroke="{td}" stroke-width="1.5" opacity=".35"/></pattern></defs>' + base +
                f'<path d="M70,720 C70,600 150,520 240,500 L360,500 C450,520 530,600 530,720Z" fill="url(#hb)"/>'
                f'<path d="M244,500 L300,560 L356,500Z" fill="#F7F3EE"/>'                                     # shirt
                f'<path d="M244,500 L268,530 L300,552 L282,512Z" fill="#FFFFFF"/><path d="M356,500 L332,530 L300,552 L318,512Z" fill="#FFFFFF"/>'
                f'<path d="M232,500 L300,640 L276,720 L196,720 L204,560 Z" fill="{td}"/><path d="M368,500 L300,640 L324,720 L404,720 L396,560 Z" fill="{td}"/>'
                f'<path d="M232,500 L300,640 L276,720 L196,720 L204,560 Z" fill="url(#hb)"/><path d="M368,500 L300,640 L324,720 L404,720 L396,560 Z" fill="url(#hb)"/>'
                f'<path d="M232,500 L206,566 L250,580 Z" fill="{t}"/><path d="M368,500 L394,566 L350,580 Z" fill="{t}"/>'   # lapel notches
                f'<path d="M300,560 L262,540 C254,552 254,576 262,588 L300,568 L338,588 C346,576 346,552 338,540Z" fill="{tie}"/>'
                f'<rect x="290" y="554" width="20" height="20" rx="6" fill="{tie}"/><path d="M291,556 L309,572" stroke="#000" stroke-opacity=".15" stroke-width="3"/>'
                f'<path d="M412,620 L452,616 L448,640 L414,642Z" fill="{tie}"/><path d="M416,622 L430,606 L438,622 L446,610" stroke="{tie}" stroke-width="5" fill="none" stroke-linejoin="round"/>')
    elif o == "tee":
        base += f'<path d="M240,500 C256,536 344,536 360,500 L346,500 C330,522 270,522 254,500Z" fill="{td}"/>'
    elif o == "vest":
        base += (f'<path d="M236,500 L300,610 L364,500Z" fill="#F3EFEA"/>'
                 f'<path d="M262,500 L300,560 L338,500 L322,500 L300,532 L278,500Z" fill="#E04A1A"/>'
                 f'<path d="M300,560 L294,720 L306,720Z" fill="#E04A1A"/>'
                 f'<path d="M236,500 L180,720 L300,720 L300,612Z" fill="{t}"/><path d="M364,500 L420,720 L300,720 L300,612Z" fill="{t}"/>'
                 f'<circle cx="290" cy="650" r="5" fill="#C9B79C"/><circle cx="288" cy="690" r="5" fill="#C9B79C"/>')
    return base

def _eye(c, cx, cy, r, blink, mood, look=1.0):
    s = ""
    if blink:
        return f'<path d="M{cx-r},{cy} C{cx-r*0.4},{cy+r*0.55} {cx+r*0.4},{cy+r*0.55} {cx+r},{cy}" stroke="{INK}" stroke-width="{max(3, r*0.22)}" fill="none" stroke-linecap="round"/>'
    s += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{INK}"/>'
    s += f'<circle cx="{cx}" cy="{cy}" r="{r*0.78}" fill="{c["iris"]}"/><circle cx="{cx}" cy="{cy}" r="{r*0.5}" fill="{INK}"/>'
    s += f'<circle cx="{cx+r*0.32}" cy="{cy-r*0.36}" r="{r*0.26}" fill="#FFFFFF"/><circle cx="{cx-r*0.3}" cy="{cy+r*0.34}" r="{r*0.11}" fill="#FFFFFF" opacity=".8"/>'
    lid = 0.0
    if c.get("sleepy"): lid = 0.38
    if mood == "unimpressed": lid = 0.55
    if mood == "happy": lid = max(0.0, lid - 0.2)
    if lid > 0:
        y = cy - r + 2 * r * lid
        s += f'<path d="M{cx-r-3},{cy-r-4} L{cx+r+3},{cy-r-4} L{cx+r+3},{y} C{cx+r*0.4},{y-r*0.12} {cx-r*0.4},{y-r*0.12} {cx-r-3},{y}Z" fill="{c["lidfill"]}"/>'
        s += f'<path d="M{cx-r-2},{y} C{cx-r*0.4},{y-r*0.12} {cx+r*0.4},{y-r*0.12} {cx+r+2},{y}" stroke="{INK}" stroke-width="{max(3, r*0.2)}" fill="none" stroke-linecap="round"/>'
    if mood == "happy":   # cheeks push up from below
        s += f'<path d="M{cx-r-4},{cy+r*0.75} C{cx-r*0.3},{cy+r*0.35} {cx+r*0.3},{cy+r*0.35} {cx+r+4},{cy+r*0.75} L{cx+r+4},{cy+r+6} L{cx-r-4},{cy+r+6}Z" fill="{c["lidfill"]}"/>'
    if c.get("lashes"):
        o = 1 if cx > 300 else -1
        s += f'<path d="M{cx+o*r*0.85},{cy-r*0.55} L{cx+o*(r+9)},{cy-r-4}" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/>' \
             f'<path d="M{cx+o*r*0.45},{cy-r*0.92} L{cx+o*(r*0.6+4)},{cy-r-10}" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/>'
    return s

def _brows(c, lx, rx, y, w, mood, col, thick=7):
    lift = {"worried": 1, "neutral": 0, "happy": -0.6, "unimpressed": -0.4}[mood]
    s = ""
    for ex, o in ((lx, -1), (rx, 1)):
        ox, oy = ex + o * w, y + 4 + 4 * lift
        ix, iy = ex - o * w * 0.8, y - 10 * lift
        mx, my = ex, y - 6 - 3 * lift
        if mood == "unimpressed" and o == 1: iy, oy = iy - 8, oy - 6       # one raised brow
        s += f'<path d="M{ox},{oy} Q{mx},{my} {ix},{iy}" stroke="{col}" stroke-width="{thick}" fill="none" stroke-linecap="round"/>'
    return s

def _mouth(c, m, mood, cx, y, sc=1.0, lip=None):
    """Soft animal mouth: a line at rest, a rounded dark opening with a sliver of tongue when talking."""
    if not isinstance(m, str): m = "rest" if m <= 0 else ("S", "E", "A")[min(2, int(m) - 1)]
    dark = "#3A1F1C"; w0 = 26 * sc
    cd = {"happy": -6, "neutral": -2, "worried": 5, "unimpressed": 0}[mood] * sc
    if m in ("rest", "M"):
        if mood == "unimpressed":
            return f'<path d="M{cx-w0},{y+2*sc} Q{cx},{y+4*sc} {cx+w0},{y-6*sc}" stroke="{dark}" stroke-width="{4.5*sc}" fill="none" stroke-linecap="round"/>'
        sag = (5 if m == "rest" else 2) * sc
        return f'<path d="M{cx-w0},{y+cd} Q{cx},{y+sag-cd*0.7} {cx+w0},{y+cd}" stroke="{dark}" stroke-width="{4.5*sc}" fill="none" stroke-linecap="round"/>'
    fw, fh, rnd = VIS[m]; w = w0 * fw; h = 26 * sc * fh
    if rnd:
        shape = f'<ellipse cx="{cx}" cy="{y+h*0.35}" rx="{w*0.75}" ry="{h/2}"/>'
    else:
        shape = f'<path d="M{cx-w},{y+cd} C{cx-w*0.5},{y-h*0.15} {cx+w*0.5},{y-h*0.15} {cx+w},{y+cd} C{cx+w*0.62},{y+h} {cx-w*0.62},{y+h} {cx-w},{y+cd}Z"/>'
    tongue = f'<ellipse cx="{cx}" cy="{y+h*0.82}" rx="{w*0.5}" ry="{h*0.3}" fill="#C8605A"/>' if h > 12 * sc else ""
    clip = f'mc_{abs(hash((cx, y, m)))%10**6}'
    return f'<clipPath id="{clip}">{shape}</clipPath><g fill="{dark}">{shape}</g><g clip-path="url(#{clip})">{tongue}</g>'

def _blush(cx1, cx2, y, rx=30):
    return f'<ellipse cx="{cx1}" cy="{y}" rx="{rx}" ry="{rx*0.55}" fill="url(#bl)"/><ellipse cx="{cx2}" cy="{y}" rx="{rx}" ry="{rx*0.55}" fill="url(#bl)"/>'

DEFS = ('<defs><radialGradient id="bl" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#E9806E" stop-opacity=".45"/>'
        '<stop offset="1" stop-color="#E9806E" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="sh" cx=".5" cy=".35" r=".7"><stop offset=".6" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000" stop-opacity=".10"/></radialGradient></defs>')

# ---------- the five ----------
def koala(c, m, blink, mood):
    f, fd, lt = c["fur"], c["fur_d"], c["light"]; c["lidfill"] = f
    s = _shoulders(c)
    s += f'<path d="M246,420 C246,470 222,498 202,512 L398,512 C378,498 354,470 354,420Z" fill="{f}"/>' + f'<ellipse cx="300" cy="442" rx="60.0" ry="22" fill="{fd}" opacity=".55"/>'
    for x, o in ((178, -1), (422, 1)):   # big fluffy ears
        s += f'<circle cx="{x}" cy="182" r="86" fill="{f}"/>'
        s += f'<circle cx="{x}" cy="186" r="58" fill="{lt}"/>'
        s += "".join(f'<path d="M{x+o*a},{186+b} q{o*18},-6 {o*30},4" stroke="#FFFFFF" stroke-width="5" fill="none" stroke-linecap="round" opacity=".9"/>'
                     for a, b in ((-20, -24), (-26, 2), (-18, 26)))
    s += f'<ellipse cx="300" cy="290" rx="168" ry="152" fill="{f}"/>'
    s += f'<ellipse cx="300" cy="290" rx="168" ry="152" fill="url(#sh)"/>'
    s += f'<path d="M180,250 C200,170 250,148 300,148 C250,160 214,196 200,262Z" fill="#FFFFFF" opacity=".12"/>'
    s += f'<ellipse cx="300" cy="368" rx="92" ry="58" fill="{lt}"/>'
    s += _blush(196, 404, 336, 34)
    s += _brows(c, 232, 368, 228, 30, mood, fd, 9)
    s += _eye(c, 232, 266, 21, blink, mood) + _eye(c, 368, 266, 21, blink, mood)
    s += f'<path d="M262,276 C262,250 338,250 338,276 C342,322 322,352 300,354 C278,352 258,322 262,276Z" fill="{c["nose"]}"/>'
    s += f'<path d="M276,272 C284,262 300,260 310,264" stroke="#FFFFFF" stroke-width="6" fill="none" stroke-linecap="round" opacity=".35"/>'
    s += _mouth(c, m, mood, 300, 388, 1.35)
    return s

def llama(c, m, blink, mood):
    f, fd, lt = c["fur"], c["fur_d"], c["light"]; c["lidfill"] = f
    s = f'<path d="M228,360 L222,560 C260,580 340,580 378,560 L372,360Z" fill="{f}"/>'      # long neck
    s += f'<path d="M222,470 L222,560 C260,580 340,580 378,560 L378,470Z" fill="{fd}" opacity=".35"/>'
    s = _shoulders(c).replace('<path d="M196,470', s + '<path d="M196,470', 1) if c["outfit"] == "scarf" else s + _shoulders(c)
    for x, o in ((214, -1), (386, 1)):   # banana ears
        s += f'<path d="M{x},150 C{x+o*10},80 {x+o*36},40 {x+o*44},52 C{x+o*52},76 {x+o*40},126 {x+o*20},168Z" fill="{f}"/>'
        s += f'<path d="M{x+o*8},146 C{x+o*16},96 {x+o*32},70 {x+o*36},76 C{x+o*40},96 {x+o*32},126 {x+o*20},156Z" fill="#E7B9A2"/>'
    s += f'<path d="M206,230 C206,150 250,118 300,118 C350,118 394,150 394,230 C396,300 380,350 376,400 C360,450 240,450 224,400 C220,350 204,300 206,230Z" fill="{f}"/>'
    s += f'<path d="M206,230 C206,150 250,118 300,118 C350,118 394,150 394,230 C396,300 380,350 376,400 C360,450 240,450 224,400 C220,350 204,300 206,230Z" fill="url(#sh)"/>'
    tuft = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{lt}"/>' for x, y, r in
                   ((256, 128, 30), (290, 108, 34), (326, 116, 32), (350, 138, 24), (236, 150, 22), (306, 140, 26)))
    s += tuft
    s += f'<ellipse cx="300" cy="368" rx="80" ry="70" fill="{lt}"/>'
    s += _blush(226, 374, 318, 26)
    s += _brows(c, 252, 348, 220, 24, mood, fd, 7)
    s += _eye(c, 252, 258, 19, blink, mood) + _eye(c, 348, 258, 19, blink, mood)
    s += f'<path d="M278,334 C286,328 296,330 300,338 C304,330 314,328 322,334" stroke="{c["nose"]}" stroke-width="7" fill="none" stroke-linecap="round"/>'
    s += f'<path d="M300,338 L300,362" stroke="{c["nose"]}" stroke-width="5" stroke-linecap="round"/>'
    s += _mouth(c, m, mood, 300, 392, 1.3)
    return s

def raccoon(c, m, blink, mood):
    f, fd, lt = c["fur"], c["fur_d"], c["light"]; c["lidfill"] = "#2A272D"
    s = _shoulders(c)
    s += f'<path d="M250,410 C250,460 226,488 206,502 L394,502 C374,488 350,460 350,410Z" fill="{f}"/>' + f'<ellipse cx="300" cy="432" rx="56.0" ry="22" fill="{fd}" opacity=".55"/>'
    for x, o in ((196, -1), (404, 1)):
        s += f'<path d="M{x-o*34},176 C{x-o*20},120 {x+o*2},84 {x+o*16},82 C{x+o*34},84 {x+o*56},130 {x+o*60},180Z" fill="{fd}"/>'
        s += f'<path d="M{x-o*16},168 C{x-o*6},128 {x+o*8},104 {x+o*16},104 C{x+o*28},106 {x+o*40},136 {x+o*42},170Z" fill="{lt}"/>'
        s += f'<path d="M{x+o*4},100 C{x+o*8},88 {x+o*12},82 {x+o*16},82 C{x+o*22},82 {x+o*26},90 {x+o*29},100 C{x+o*20},96 {x+o*12},96 {x+o*4},100Z" fill="#2A272D"/>'
    s += f'<path d="M150,300 C150,200 220,140 300,140 C380,140 450,200 450,300 C450,380 380,430 300,432 C220,430 150,380 150,300Z" fill="{f}"/>'
    s += f'<path d="M150,300 C150,200 220,140 300,140 C380,140 450,200 450,300 C450,380 380,430 300,432 C220,430 150,380 150,300Z" fill="url(#sh)"/>'
    s += f'<path d="M150,300 C140,330 132,348 120,356 C150,362 176,356 196,340Z" fill="{f}"/><path d="M450,300 C460,330 468,348 480,356 C450,362 424,356 404,340Z" fill="{f}"/>'
    s += f'<path d="M300,180 L292,250 L308,250Z" fill="{fd}"/>'
    # white brows + mask
    s += f'<path d="M184,236 C210,200 262,200 290,226 C262,214 214,220 184,236Z" fill="{lt}"/><path d="M416,236 C390,200 338,200 310,226 C338,214 386,220 416,236Z" fill="{lt}"/>'
    s += (f'<path d="M168,274 C180,232 226,226 262,244 C282,254 292,262 300,262 C308,262 318,254 338,244 C374,226 420,232 432,274 '
          f'C436,306 404,320 368,312 C340,306 320,296 300,296 C280,296 260,306 232,312 C196,320 164,306 168,274Z" fill="#2A272D"/>')
    s += f'<path d="M238,330 C230,300 370,300 362,330 C380,380 340,420 300,422 C260,420 220,380 238,330Z" fill="{lt}"/>'
    s += _brows(c, 230, 370, c.get("brow_y", 214), 30, mood, lt, 9)
    s += _eye(c, 230, 272, 20, blink, mood) + _eye(c, 370, 272, 20, blink, mood)
    s += f'<ellipse cx="300" cy="338" rx="26" ry="18" fill="{c["nose"]}"/><ellipse cx="292" cy="332" rx="8" ry="4" fill="#FFFFFF" opacity=".35"/>'
    s += _mouth(c, m, mood, 300, 386, 1.3)
    return s

def capybara(c, m, blink, mood):
    f, fd, lt = c["fur"], c["fur_d"], c["light"]; c["lidfill"] = f
    s = _shoulders(c)
    s += f'<path d="M236,430 C236,480 212,508 192,522 L408,522 C388,508 364,480 364,430Z" fill="{f}"/>' + f'<ellipse cx="300" cy="452" rx="70.0" ry="22" fill="{fd}" opacity=".55"/>'
    for x in (214, 386):
        s += f'<ellipse cx="{x}" cy="140" rx="26" ry="20" fill="{fd}"/><ellipse cx="{x}" cy="142" rx="14" ry="10" fill="#6E4A2F"/>'
    hd = "M206,206 C206,150 246,126 300,126 C354,126 394,150 394,206 C404,250 420,300 422,350 C424,420 376,452 300,452 C224,452 176,420 178,350 C180,300 196,250 206,206Z"
    s += f'<path d="{hd}" fill="{f}"/><path d="{hd}" fill="url(#sh)"/>'
    s += f'<path d="M200,330 C206,290 394,290 400,330 C412,370 410,420 380,438 C350,452 250,452 220,438 C190,420 188,370 200,330Z" fill="{lt}"/>'
    # the signature orange on its head, on brand
    s += '<circle cx="300" cy="96" r="40" fill="#F08A2C"/><circle cx="300" cy="96" r="40" fill="url(#sh)"/>' \
         '<path d="M300,58 C306,44 322,40 330,44 C322,54 310,58 300,58Z" fill="#5E8B3E"/><circle cx="288" cy="84" r="9" fill="#FFFFFF" opacity=".35"/>'
    s += _blush(222, 378, 300, 26)
    s += _brows(c, 244, 356, 206, 22, mood, fd, 7)
    s += _eye(c, 244, 238, 15, blink, mood) + _eye(c, 356, 238, 15, blink, mood)
    s += f'<path d="M262,320 C268,306 286,310 284,326 C282,334 270,334 262,320Z" fill="{c["nose"]}"/>' \
         f'<path d="M338,320 C332,306 314,310 316,326 C318,334 330,334 338,320Z" fill="{c["nose"]}"/>' \
         f'<path d="M300,340 L300,372" stroke="{fd}" stroke-width="4" stroke-linecap="round" opacity=".7"/>'
    s += _mouth(c, m, mood, 300, 398, 1.4)
    return s

def otter(c, m, blink, mood):
    f, fd, lt = c["fur"], c["fur_d"], c["light"]; c["lidfill"] = f
    s = _shoulders(c)
    s += f'<path d="M244,420 C244,470 220,498 200,512 L400,512 C380,498 356,470 356,420Z" fill="{f}"/>' + f'<ellipse cx="300" cy="442" rx="62.0" ry="22" fill="{fd}" opacity=".55"/>'
    for x in (186, 414):
        s += f'<circle cx="{x}" cy="200" r="30" fill="{f}"/><circle cx="{x}" cy="202" r="16" fill="{fd}"/>'
    s += f'<path d="M168,290 C168,190 230,148 300,148 C370,148 432,190 432,290 C432,380 380,440 300,442 C220,440 168,380 168,290Z" fill="{f}"/>'
    s += f'<path d="M168,290 C168,190 230,148 300,148 C370,148 432,190 432,290 C432,380 380,440 300,442 C220,440 168,380 168,290Z" fill="url(#sh)"/>'
    s += f'<path d="M196,330 C196,280 250,262 300,286 C350,262 404,280 404,330 C404,400 360,438 300,440 C240,438 196,400 196,330Z" fill="{lt}"/>'
    s += f'<path d="M226,236 C236,214 262,210 276,226 C262,222 240,226 226,236Z" fill="{lt}" opacity=".7"/><path d="M374,236 C364,214 338,210 324,226 C338,222 360,226 374,236Z" fill="{lt}" opacity=".7"/>'
    s += _blush(216, 384, 330, 26)
    s += _brows(c, 244, 356, 218, 24, mood, fd, 8)
    s += _eye(c, 244, 256, 20, blink, mood) + _eye(c, 356, 256, 20, blink, mood)
    s += f'<path d="M272,306 C272,292 328,292 328,306 C328,326 312,336 300,336 C288,336 272,326 272,306Z" fill="{c["nose"]}"/><ellipse cx="290" cy="302" rx="8" ry="4" fill="#FFFFFF" opacity=".35"/>'
    s += "".join(f'<path d="M{x},{y} q{o*40},{-8+k} {o*76},{k}" stroke="#FFFFFF" stroke-width="3" fill="none" stroke-linecap="round" opacity=".9"/>'
                 for o, x in ((-1, 252), (1, 348)) for y, k in ((338, -6), (350, 4), (362, 14)))
    s += _mouth(c, m, mood, 300, 382, 1.3)
    return s

def _deerstalker(c):
    cap, ln = c["cap"], c["cap_line"]
    chk = (f'<defs><pattern id="ck" width="28" height="28" patternUnits="userSpaceOnUse">'
           f'<rect width="28" height="28" fill="{cap}"/><path d="M0,14 H28 M14,0 V28" stroke="{ln}" stroke-width="3" opacity=".75"/>'
           f'<path d="M0,5 H28 M5,0 V28" stroke="#FFFFFF" stroke-width="1.5" opacity=".25"/></pattern></defs>')
    crown = "M182,200 C182,118 236,84 300,84 C364,84 418,118 418,200 C380,186 220,186 182,200Z"
    s = chk + f'<path d="M166,204 C200,236 250,240 300,232 C250,226 210,214 186,196Z" fill="{cap}"/>'                  # back peak (left side)
    s += f'<path d="M434,204 C400,236 350,240 300,232 C350,226 390,214 414,196Z" fill="{cap}"/>'
    s += f'<path d="{crown}" fill="url(#ck)"/><path d="{crown}" fill="#000" opacity=".06"/>'
    s += f'<path d="M300,86 L300,190" stroke="#000" stroke-opacity=".12" stroke-width="3"/>'
    s += f'<path d="M206,198 C240,234 360,234 394,198 C392,214 382,222 370,226 C330,240 270,240 230,226 C218,222 208,214 206,198Z" fill="url(#ck)"/>'  # front peak
    s += f'<path d="M206,198 C240,234 360,234 394,198 C392,214 382,222 370,226 C330,240 270,240 230,226 C218,222 208,214 206,198Z" fill="#000" opacity=".12"/>'
    s += f'<path d="M230,104 C250,92 270,90 284,96" stroke="{cap}" stroke-width="10" fill="none" stroke-linecap="round"/>' \
         f'<path d="M316,96 C330,90 350,92 370,104" stroke="{cap}" stroke-width="10" fill="none" stroke-linecap="round"/>'
    s += f'<path d="M300,84 C286,66 270,66 270,78 C270,88 288,88 300,84 C312,88 330,88 330,78 C330,66 314,66 300,84Z" fill="{ln}"/><circle cx="300" cy="84" r="7" fill="{ln}"/>'
    return s

def raccoon_tweed(c, m, blink, mood):
    c["brow_y"] = 232
    s = raccoon(c, m, blink, mood)
    return s + '<g transform="translate(300,0) scale(1.1,1.04) translate(-300,-12)">' + _deerstalker(c) + '</g>' 

import math
def _fluff(cx, cy, rx, ry, n=28, amp=0.07, a0=0.0, a1=360.0, close=True, jitter=0.0):
    """Scalloped (furry) outline around an ellipse arc: each bump is a quadratic curve bulging outward."""
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n); pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f} "
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        am = math.radians(a0 + (a1 - a0) * (i + 0.5) / n); k = 1 + amp * (1 + (jitter if i % 2 else 0))
        qx, qy = cx + rx * k * math.cos(am), cy + ry * k * math.sin(am)
        d += f"Q{qx:.1f},{qy:.1f} {x1:.1f},{y1:.1f} "
    return d + ("Z" if close else "")

def raccoon_fluffy(c, m, blink, mood):
    f, fd, fdd, lt, bl = c["fur"], c["fur_d"], c["fur_dd"], c["light"], c["belly"]; c["lidfill"] = "#2A272D"
    s = ""
    # big ringed tail: overlapping fluffy discs along a curve, banded light/dark
    pts = []
    for i in range(23):
        u = i / 22; x = (1-u)**2*430 + 2*(1-u)*u*560 + u*u*500; y = (1-u)**2*720 + 2*(1-u)*u*500 + u*u*300
        pts.append((x, y, 52 - 18 * u))
    for i, (x, y, r) in enumerate(pts):
        col = "#3A3B42" if (i // 3) % 2 else fd
        s += f'<path d="{_fluff(x, y, r, r, 12, 0.09)}" fill="{col}"/>'
    s += f'<path d="{_fluff(pts[-1][0], pts[-1][1]-6, 30, 30, 12, 0.1)}" fill="#3A3B42"/>'
    # big fluffy body
    s += f'<path d="{_fluff(300, 700, 270, 260, 30, 0.05, 180, 360, False)} L570,720 L30,720Z" fill="{f}"/>'
    s += f'<path d="{_fluff(300, 740, 140, 250, 18, 0.05, 180, 360, False)} L440,740 L160,740Z" fill="{bl}"/>'
    s += "".join(f'<path d="M{x},{y} c4,10 10,16 18,18" stroke="#FFFFFF" stroke-width="4" fill="none" stroke-linecap="round" opacity=".45"/>'
                 for x, y in ((236, 540), (330, 556), (268, 620), (356, 640), (216, 668)))
    s += "".join(f'<path d="M{x},{y} c-6,10 -14,16 -24,18" stroke="{fd}" stroke-width="4" fill="none" stroke-linecap="round" opacity=".55"/>'
                 for x, y in ((110, 620), (150, 560), (500, 640), (90, 690)))
    s += f'<path d="{_fluff(300, 700, 270, 260, 30, 0.05, 200, 250, False)}" stroke="#FFFFFF" stroke-opacity=".18" stroke-width="10" fill="none"/>'
    # ears
    for x, o in ((178, -1), (422, 1)):
        s += f'<path d="M{x-o*44},214 C{x-o*40},150 {x-o*6},104 {x+o*14},100 C{x+o*40},104 {x+o*60},160 {x+o*58},226Z" fill="{fd}"/>'
        s += f'<path d="M{x-o*28},206 C{x-o*24},160 {x-o*2},124 {x+o*14},122 C{x+o*32},126 {x+o*44},166 {x+o*42},214Z" fill="{lt}"/>'
        s += f'<path d="M{x-o*14},200 C{x-o*10},170 {x+o*4},146 {x+o*14},146 C{x+o*26},150 {x+o*32},176 {x+o*30},206Z" fill="{fdd}"/>'
    # head with cheek ruffs
    s += f'<path d="{_fluff(300, 300, 190, 150, 34, 0.06)}" fill="{f}"/>'
    for o in (-1, 1):   # cheek ruffs
        s += f'<path d="M{300+o*150},300 L{300+o*222},334 L{300+o*176},346 L{300+o*214},376 L{300+o*160},378 L{300+o*186},410 L{300+o*120},392Z" fill="{f}"/>'
        s += f'<path d="M{300+o*150},330 L{300+o*196},350 L{300+o*160},360 L{300+o*186},384 L{300+o*140},380Z" fill="{lt}"/>'
    s += f'<ellipse cx="300" cy="300" rx="190" ry="150" fill="url(#sh)"/>'
    s += f'<path d="M300,168 L290,252 L310,252Z" fill="{fd}"/>'
    s += "".join(f'<path d="M{x},{y} q6,-12 12,0" stroke="{fd}" stroke-width="4" fill="none" stroke-linecap="round" opacity=".5"/>' for x, y in ((240, 186), (348, 186), (270, 172), (318, 172)))
    # white brows + mask
    by = 226
    s += f'<path d="M168,{by+20} C196,{by-22} 260,{by-22} 290,{by+2} C262,{by-6} 210,{by} 168,{by+20}Z" fill="{lt}"/><path d="M432,{by+20} C404,{by-22} 340,{by-22} 310,{by+2} C338,{by-6} 390,{by} 432,{by+20}Z" fill="{lt}"/>'
    s += (f'<path d="M150,290 C160,240 222,232 262,252 C282,262 292,270 300,270 C308,270 318,262 338,252 C378,232 440,240 450,290 '
          f'C456,326 418,340 376,330 C344,322 322,308 300,308 C278,308 256,322 224,330 C182,340 144,326 150,290Z" fill="#2A272D"/>')
    s += f'<path d="M226,350 C214,316 386,316 374,350 C394,404 350,440 300,442 C250,440 206,404 226,350Z" fill="{lt}"/>'
    s += _brows(c, 226, 374, by + 2, 32, mood, lt, 10)
    s += _eye(c, 228, 284, 23, blink, mood) + _eye(c, 372, 284, 23, blink, mood)
    s += f'<path d="M272,350 C272,336 328,336 328,350 C328,368 312,376 300,376 C288,376 272,368 272,350Z" fill="{c["nose"]}"/><ellipse cx="290" cy="345" rx="9" ry="4.5" fill="#FFFFFF" opacity=".35"/>'
    s += _blush(196, 404, 360, 28)
    s += _mouth(c, m, mood, 300, 404, 1.3)
    return s

DRAW = {"raccoon_fluffy": raccoon_fluffy, "raccoon_tweed": raccoon_tweed, "raccoon_orange": raccoon_tweed, "koala": koala, "llama": llama, "raccoon": raccoon, "capybara": capybara, "otter": otter}

def svg(name, mouth=0, blink=False, mood="neutral"):
    c = dict(ANIMALS[name])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 720" width="600" height="720">{DEFS}'
            f'{DRAW[name](c, mouth, blink, mood)}</svg>')

@lru_cache(maxsize=512)
def sprite(name, mouth=0, blink=False, mood="neutral", height=720):
    import cairosvg
    png = cairosvg.svg2png(bytestring=svg(name, mouth, blink, mood).encode(), output_height=height, output_width=int(height * 600 / 720))
    return Image.open(io.BytesIO(png)).convert("RGBA")

def lineup(out, names=None, poses=(("rest", "neutral"), ("A", "happy"), ("E", "worried"), ("rest", "unimpressed"))):
    from PIL import ImageDraw, ImageFont
    names = names or list(ANIMALS); cw, ch = 600, 720; top = 90
    img = Image.new("RGB", (cw * len(names), top + ch * len(poses)), (255, 250, 247)); d = ImageDraw.Draw(img)
    try: f = ImageFont.truetype("/home/claude/divvyupp-media/pipeline/.cache/fonts/package/files/plus-jakarta-sans-latin-800-normal.woff", 52)
    except Exception: f = None
    for i, n in enumerate(names):
        d.text((i * cw + cw / 2, 18), ANIMALS[n]["label"], font=f, fill=(224, 74, 26), anchor="ma")
        for j, (m, mood) in enumerate(poses):
            sp = sprite(n, m, False, mood); img.paste(sp, (i * cw, top + j * ch), sp)
    img.save(out, quality=90)

if __name__ == "__main__":
    if sys.argv[1] == "lineup": lineup(sys.argv[2])
