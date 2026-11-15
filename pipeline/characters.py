"""Original illustrated presenters for story Reels, drawn as SVG (flat editorial style) and rasterised with cairosvg.

Each character is a bust (head and shoulders). Only the face moves: mouth shape (driven by the voice), blinks and the
brows/mouth mood. `sprite(name, mouth, blink, mood, height)` returns an RGBA PIL image (cached).

    python3 pipeline/characters.py lineup out.png    -> a lineup of every character, neutral and talking
"""
import io, sys
from functools import lru_cache
from PIL import Image

# ---------- palettes ----------
CHARS = {
    "a": dict(label="A", sex="f", skin="#C68A62", skin_d="#A86E4A", hair="#2A1C17", hair_h="#4A3128", style="curls",
              top="#E8DCCF", top_d="#CDBEAE", outer="#7A8C6E", outer_d="#64765A", outfit="cardigan", iris="#4A2E1E",
              lip="#A9584E", earring=True),
    "b": dict(label="B", sex="f", skin="#F1C9AE", skin_d="#D9A88A", hair="#8A5A34", hair_h="#B07A4C", style="bob",
              top="#5D7FA6", top_d="#4A6A8F", outer=None, outer_d=None, outfit="denim", iris="#4E6B4A",
              lip="#C26F68", earring=False),
    "c": dict(label="C", sex="f", skin="#B97B57", skin_d="#9A603F", hair="#1E1512", hair_h="#3A2A22", style="ponytail",
              top="#F3EFEA", top_d="#DAD3CB", outer="#2E3A4F", outer_d="#222C3D", outfit="blazer", iris="#3A2418",
              lip="#9C4F48", earring=True),
    "d": dict(label="D", sex="m", skin="#8A5638", skin_d="#6E4128", hair="#1A1311", hair_h="#2E2320", style="fade",
              top="#3F5E58", top_d="#314B46", outer=None, outer_d=None, outfit="quarterzip", iris="#2E1C12",
              lip="#6A3A2C", earring=False, beard=True),
    "e": dict(label="E", sex="m", skin="#EBC2A2", skin_d="#CF9F7E", hair="#6B4A2E", hair_h="#8C6744", style="tousled",
              top="#B5533C", top_d="#97422F", outer=None, outer_d=None, outfit="henley", iris="#5A6E86",
              lip="#B06A5E", earring=False, stubble=True, glasses=True),
}

def _hair_back(c):
    h, hh = c["hair"], c["hair_h"]
    if c["style"] == "curls":
        blobs = [(300, 128, 112), (215, 175, 70), (385, 175, 70), (240, 110, 70), (360, 110, 70), (300, 72, 62),
                 (195, 240, 52), (405, 240, 52)]
        return "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{h}"/>' for x, y, r in blobs) + \
               "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{hh}" opacity=".35"/>' for x, y, r in [(270, 80, 22), (350, 95, 18), (225, 140, 16)])
    if c["style"] == "bob":
        return f'<path d="M178,250 C170,140 230,92 300,92 C372,92 430,140 422,250 C420,320 432,380 440,410 L340,412 L260,412 L160,410 C168,380 180,320 178,250Z" fill="{h}"/>'
    if c["style"] == "ponytail":
        return f'<path d="M190,240 C186,150 236,104 300,104 C366,104 414,150 410,240 L404,300 L196,300Z" fill="{h}"/>' \
               f'<path d="M392,300 C430,340 436,430 410,520 C400,560 372,560 370,520 C384,450 380,380 360,330Z" fill="{h}"/>' \
               f'<path d="M398,360 C410,410 404,470 392,510" stroke="{hh}" stroke-width="6" fill="none" stroke-linecap="round" opacity=".6"/>'
    if c["style"] in ("tousled", "fade"):
        return f'<ellipse cx="300" cy="186" rx="104" ry="{78 if c["style"] == "tousled" else 70}" fill="{h}"/>'
    return ""

def _hair_front(c):
    h, hh = c["hair"], c["hair_h"]
    if c["style"] == "curls":
        pts = [(214, 196, 26), (236, 168, 26), (264, 150, 26), (296, 144, 26), (328, 150, 26), (358, 166, 26), (384, 192, 26)]
        return "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{h}"/>' for x, y, r in pts)
    if c["style"] == "bob":
        return f'<path d="M196,250 C190,160 240,118 306,118 C366,118 408,160 404,232 C380,196 330,170 268,176 C238,190 214,214 196,250Z" fill="{h}"/>' \
               f'<path d="M262,132 C300,122 352,132 384,168" stroke="{hh}" stroke-width="7" fill="none" stroke-linecap="round" opacity=".7"/>' \
               f'<path d="M196,250 C192,300 196,350 206,392 L186,396 C176,340 176,290 196,250Z" fill="{h}"/>' \
               f'<path d="M404,232 C410,300 406,350 396,392 L416,396 C426,340 424,280 404,232Z" fill="{h}"/>'
    if c["style"] == "ponytail":
        return f'<path d="M200,250 C194,166 240,124 300,124 L302,128 C270,150 236,190 218,262Z" fill="{h}"/>' \
               f'<path d="M298,124 C360,124 406,166 400,250 L382,262 C366,190 334,150 298,128Z" fill="{h}"/>' \
               f'<path d="M250,146 C236,168 226,196 220,228" stroke="{hh}" stroke-width="5" fill="none" stroke-linecap="round" opacity=".6"/>'
    if c["style"] == "fade":
        return f'<path d="M204,214 C200,146 244,112 302,112 C360,112 402,146 396,214 C386,180 360,160 330,156 L270,156 C240,160 214,180 204,214Z" fill="{h}"/>' \
               f'<path d="M204,214 L206,250 L214,250 L212,210Z" fill="{h}" opacity=".7"/><path d="M396,214 L394,250 L386,250 L388,210Z" fill="{h}" opacity=".7"/>'
    if c["style"] == "tousled":
        return f'<path d="M202,232 C188,150 238,100 304,104 C352,98 404,130 402,214 C398,196 384,184 370,182 C376,166 362,150 344,156 ' \
               f'C334,140 312,140 302,154 C286,140 262,146 258,164 C238,164 220,186 216,214 C212,220 206,228 202,232Z" fill="{h}"/>' \
               f'<path d="M262,128 C292,112 336,114 362,132" stroke="{hh}" stroke-width="7" fill="none" stroke-linecap="round" opacity=".7"/>'
    return ""

def _outfit(c):
    o = c["outfit"]; top, top_d = c["top"], c["top_d"]
    body = 'M70,720 C78,570 150,480 258,458 L342,458 C450,480 522,570 530,720Z'
    s = f'<path d="{body}" fill="{top}"/>'
    if o == "cardigan":
        s += f'<path d="M70,720 C78,570 150,480 252,458 L300,600 L270,720Z" fill="{c["outer"]}"/>' \
             f'<path d="M530,720 C522,570 450,480 348,458 L300,600 L330,720Z" fill="{c["outer"]}"/>' \
             f'<path d="M252,458 L300,600 L348,458" stroke="{c["outer_d"]}" stroke-width="10" fill="none"/>' \
             f'<circle cx="290" cy="650" r="6" fill="{c["outer_d"]}"/><circle cx="292" cy="694" r="6" fill="{c["outer_d"]}"/>'
    elif o == "denim":
        s += f'<path d="M258,458 L300,520 L276,560 L232,476Z" fill="{top_d}"/><path d="M342,458 L300,520 L324,560 L368,476Z" fill="{top_d}"/>' \
             f'<path d="M300,520 L300,720" stroke="{top_d}" stroke-width="5"/>' \
             f'<circle cx="300" cy="590" r="5" fill="#E7E1D8"/><circle cx="300" cy="650" r="5" fill="#E7E1D8"/>' \
             f'<path d="M150,600 L230,600 L230,640 L150,640Z" fill="none" stroke="{top_d}" stroke-width="4"/>'
    elif o == "blazer":
        s += f'<path d="M70,720 C78,570 150,480 256,458 L292,560 L250,720Z" fill="{c["outer"]}"/>' \
             f'<path d="M530,720 C522,570 450,480 344,458 L308,560 L350,720Z" fill="{c["outer"]}"/>' \
             f'<path d="M256,458 L292,560 L236,520Z" fill="{c["outer_d"]}"/><path d="M344,458 L308,560 L364,520Z" fill="{c["outer_d"]}"/>'
    elif o == "quarterzip":
        s += f'<path d="M262,456 C270,490 330,490 338,456 L346,470 C336,512 264,512 254,470Z" fill="{top_d}"/>' \
             f'<path d="M300,494 L300,600" stroke="#C9CDD2" stroke-width="5"/><rect x="294" y="596" width="12" height="20" rx="3" fill="#C9CDD2"/>'
    elif o == "henley":
        s += f'<path d="M262,458 C272,486 328,486 338,458" stroke="{top_d}" stroke-width="10" fill="none"/>' \
             f'<path d="M300,482 L300,570" stroke="{top_d}" stroke-width="6"/><circle cx="300" cy="510" r="5" fill="#EDE3D6"/><circle cx="300" cy="545" r="5" fill="#EDE3D6"/>'
    return s

# Mouth shapes (visemes). Each: half-width, opening height, round?, top-teeth px, bottom-teeth px.
VISEMES = {"A": (25, 23, False, 4, 0), "E": (28, 14, False, 4, 0), "O": (17, 21, True, 0, 0),
           "U": (12, 13, True, 0, 0), "F": (25, 9, False, 5, 0), "S": (24, 9, False, 4, 3), "L": (23, 15, False, 4, 0)}
# Kokoro/espeak phonemes -> viseme ("M" = lips pressed, "rest" = relaxed closed)
PHONEME_VISEME = {**{p: "A" for p in "aɑæʌɐ"}, **{p: "E" for p in "eɛiɪ"}, **{p: "O" for p in "oɔɒ"},
                  **{p: "U" for p in "uʊwɚɝɜ"}, **{p: "M" for p in "mbp"}, **{p: "F" for p in "fv"},
                  **{p: "L" for p in "lθðntdɾ"}, **{p: "S" for p in "szʃʒʧʤkɡgŋhjɹrəᵻ"}}

def _mouth(c, m, mood):
    """m: a viseme name (rest, M, A, E, O, U, F, S, L) or a legacy openness level 0-3."""
    if not isinstance(m, str): m = "rest" if m <= 0 else ("S", "E", "A")[min(2, int(m) - 1)]
    lip = c["lip"]; dark = "#5A2420"; y = 328
    cd = {"happy": -4, "neutral": -1.5, "worried": 3}[mood]          # corner lift (negative = smile)
    if m in ("rest", "M"):
        w = 24 if m == "rest" else 21; sag = 4 if m == "rest" else 1
        return f'<path d="M{300-w},{y+cd} Q300,{y+sag-cd*0.6} {300+w},{y+cd}" stroke="{dark}" stroke-width="4" fill="none" stroke-linecap="round"/>' \
               f'<path d="M{300-w*0.6},{y+sag*0.6+3} Q300,{y+sag+11} {300+w*0.6},{y+sag*0.6+3} Q300,{y+sag+5} {300-w*0.6},{y+sag*0.6+3}Z" fill="{lip}" opacity=".85"/>'
    w, h, rnd, tt, tb = VISEMES[m]
    if rnd:
        shape = f'<ellipse cx="300" cy="{y+h*0.25}" rx="{w}" ry="{h/2+1}"/>'
    else:
        top = y - h * 0.35; bot = y + h * 0.95
        shape = f'<path d="M{300-w},{y+cd} C{300-w*0.55},{top} {300+w*0.55},{top} {300+w},{y+cd} C{300+w*0.6},{bot} {300-w*0.6},{bot} {300-w},{y+cd}Z"/>'
    inner = f'<g fill="{dark}">{shape}</g>'
    teeth = ""
    if tt: teeth += f'<rect x="{300-w}" y="{y-h}" width="{2*w}" height="{h*0.7+tt}" fill="#F3ECE6"/>'
    if tb: teeth += f'<rect x="{300-w}" y="{y+h*0.95-tb-1}" width="{2*w}" height="{tb+2}" fill="#F3ECE6"/>'
    tongue = f'<ellipse cx="300" cy="{y+h*0.85}" rx="{w*0.5}" ry="{max(2, h*0.22)}" fill="#B9524C"/>' if h >= 10 else ""
    return f'<clipPath id="mc">{shape}</clipPath>{inner}<g clip-path="url(#mc)">{teeth}{tongue}</g>' \
           f'<g fill="none" stroke="{lip}" stroke-width="5" stroke-linejoin="round">{shape}</g>'

def _eyes(c, blink, mood):
    ink = "#1E1412"; s = ""
    for ex in (258, 342):
        if blink:
            s += f'<path d="M{ex-18},246 C{ex-8},254 {ex+8},254 {ex+18},246" stroke="{ink}" stroke-width="4" fill="none" stroke-linecap="round"/>'
            continue
        s += f'<ellipse cx="{ex}" cy="245" rx="18" ry="12" fill="#FBF7F3"/>' \
             f'<circle cx="{ex+1}" cy="246" r="9.5" fill="{c["iris"]}"/><circle cx="{ex+1}" cy="246" r="5" fill="{ink}"/>' \
             f'<circle cx="{ex+4}" cy="242" r="2.6" fill="#FFFFFF"/>' \
             f'<path d="M{ex-19},244 C{ex-10},230 {ex+10},230 {ex+19},243" stroke="{ink}" stroke-width="4" fill="none" stroke-linecap="round"/>'
        if c["sex"] == "f":
            o = 1 if ex > 300 else -1
            s += f'<path d="M{ex+o*17},240 L{ex+o*25},234" stroke="{ink}" stroke-width="3.5" stroke-linecap="round"/>'
    # brows
    lift = {"worried": 1, "neutral": 0, "happy": -0.5}[mood]
    bw = 7 if c["sex"] == "m" else 5.5
    for ex, o in ((258, -1), (342, 1)):
        ox, oy = ex + o * 24, 216 + 3 * lift            # outer end
        ix, iy = ex - o * 20, 214 - 9 * lift            # inner end (raised when worried)
        mx, my = ex + o * 2, 205 - 3 * lift
        s += f'<path d="M{ox},{oy} Q{mx},{my} {ix},{iy}" stroke="{c["hair"]}" stroke-width="{bw}" fill="none" stroke-linecap="round"/>'
    return s

def svg(name, mouth=0, blink=False, mood="neutral"):
    c = CHARS[name]; sk, skd = c["skin"], c["skin_d"]
    face = "M204,236 C204,158 248,126 300,126 C352,126 396,158 396,236 C396,300 372,352 300,374 C228,352 204,300 204,236Z"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 720" width="600" height="720">',
             '<defs><radialGradient id="bl" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#E07A6A" stop-opacity=".35"/>'
             '<stop offset="1" stop-color="#E07A6A" stop-opacity="0"/></radialGradient>'
             f'<clipPath id="fc"><path d="{face}"/></clipPath></defs>',
             _hair_back(c),
             f'<path d="M262,330 L262,462 C282,476 318,476 338,462 L338,330Z" fill="{skd}"/>',            # neck
             '<g transform="translate(300,0) scale(1.16,1) translate(-300,-30)">', _outfit(c),
             f'<path d="M262,452 C282,470 318,470 338,452 L338,462 C318,478 282,478 262,462Z" fill="{skd}" opacity=".6"/>', '</g>',
             f'<ellipse cx="204" cy="254" rx="18" ry="28" fill="{sk}"/><ellipse cx="396" cy="254" rx="18" ry="28" fill="{sk}"/>',
             f'<ellipse cx="206" cy="256" rx="8" ry="14" fill="{skd}" opacity=".6"/><ellipse cx="394" cy="256" rx="8" ry="14" fill="{skd}" opacity=".6"/>',
             f'<path d="{face}" fill="{sk}"/>',
             f'<g clip-path="url(#fc)"><path d="M204,236 C204,300 228,352 300,374 C252,346 230,300 224,236Z" fill="{skd}" opacity=".18"/></g>',
             ]
    if c.get("earring"):
        parts.append('<circle cx="202" cy="290" r="6" fill="#D9B45A"/><circle cx="398" cy="290" r="6" fill="#D9B45A"/>')
    if c.get("beard"):
        parts.append(f'<path d="M210,262 C214,330 246,378 300,384 C354,378 386,330 390,262 C380,300 360,316 340,312 C326,308 312,304 300,304 '
                     f'C288,304 274,308 260,312 C240,316 220,300 210,262Z" fill="{c["hair"]}"/>'
                     f'<path d="M262,308 C280,298 320,298 338,308 C326,314 274,314 262,308Z" fill="{c["hair"]}"/>')
    if c.get("stubble"):
        parts.append(f'<path d="M214,270 C220,330 250,370 300,376 C350,370 380,330 386,270 C370,320 340,340 300,342 C260,340 230,320 214,270Z" fill="{c["hair"]}" opacity=".18"/>')
    parts += [f'<ellipse cx="246" cy="292" rx="26" ry="16" fill="url(#bl)"/><ellipse cx="354" cy="292" rx="26" ry="16" fill="url(#bl)"/>',
              f'<path d="M302,252 C298,272 290,288 294,298 C298,304 308,304 314,298" stroke="{skd}" stroke-width="5" fill="none" stroke-linecap="round"/>',
              _eyes(c, blink, mood), _mouth(c, mouth, mood)]
    if c.get("beard"):   # keep the mouth readable over the beard
        pass
    parts.append(_hair_front(c))
    if c.get("glasses"):
        parts.append('<g fill="none" stroke="#2B2523" stroke-width="5"><rect x="226" y="222" width="64" height="48" rx="16"/>'
                     '<rect x="310" y="222" width="64" height="48" rx="16"/><path d="M290,240 C296,234 304,234 310,240"/>'
                     '<path d="M226,238 L206,234"/><path d="M374,238 L394,234"/></g>')
    parts.append("</svg>")
    return "".join(parts)

@lru_cache(maxsize=512)
def sprite(name, mouth=0, blink=False, mood="neutral", height=720):
    import cairosvg
    png = cairosvg.svg2png(bytestring=svg(name, mouth, blink, mood).encode(), output_height=height, output_width=int(height * 600 / 720))
    return Image.open(io.BytesIO(png)).convert("RGBA")

def lineup(out):
    from PIL import ImageDraw, ImageFont
    names = list(CHARS); cw, ch = 600, 720; img = Image.new("RGB", (cw * len(names), ch * 2 + 80), (255, 250, 247))
    d = ImageDraw.Draw(img)
    try: f = ImageFont.truetype("/home/claude/divvyupp-media/pipeline/.cache/fonts/package/files/plus-jakarta-sans-latin-800-normal.woff", 56)
    except Exception: f = None
    for i, n in enumerate(names):
        img.paste(sprite(n, 0, False, "neutral"), (i * cw, 80), sprite(n, 0, False, "neutral"))
        img.paste(sprite(n, 2, False, "worried"), (i * cw, 80 + ch), sprite(n, 2, False, "worried"))
        d.text((i * cw + cw / 2, 12), CHARS[n]["label"], font=f, fill=(224, 74, 26), anchor="ma")
    img.save(out, quality=90)

if __name__ == "__main__":
    if sys.argv[1] == "lineup": lineup(sys.argv[2])
