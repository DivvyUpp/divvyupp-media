"""Build the movie-style Dollar Bill sprite parts from Runway outputs.

Inputs (one folder): base.jpg (the original still), cutout.png (same still, background removed),
A/E/O/U/F/S.png (Runway edits with only the mouth changed), blink.png (only the eyes closed).
Each edit is aligned to the base on the unchanged eye/body area, then only a feathered mouth (or eye)
patch is kept, so the rest of him never changes between frames.

Usage: python3 pipeline/build_movie_char.py <input_dir>  -> pipeline/assets/characters/raccoon_movie/
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), "assets", "characters", "raccoon_movie")
MOUTH_BOX = (500, 590, 1100, 1000)     # patch area in base pixels (x0, y0, x1, y1)
EYES_BOX = (440, 380, 1110, 650)

def ellipse_alpha(box, size, feather):
    x0, y0, x1, y1 = box
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse((x0 + feather, y0 + feather, x1 - feather, y1 - feather), fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather / 2))

def align(base, img, ref_box, r=10):
    """Best integer shift (dx, dy) of img onto base, judged on ref_box (an area the edit should not change)."""
    x0, y0, x1, y1 = ref_box
    b = base[y0:y1, x0:x1].mean(2)
    best = (1e18, 0, 0)
    for dy in range(-r, r + 1, 2):
        for dx in range(-r, r + 1, 2):
            c = img[y0 - dy:y1 - dy, x0 - dx:x1 - dx].mean(2)
            e = np.mean((c - b) ** 2)
            if e < best[0]: best = (e, dx, dy)
    _, bx, by = best
    for dy in range(by - 1, by + 2):
        for dx in range(bx - 1, bx + 2):
            c = img[y0 - dy:y1 - dy, x0 - dx:x1 - dx].mean(2)
            e = np.mean((c - b) ** 2)
            if e < best[0]: best = (e, dx, dy)
    return best[1], best[2]

def patch(base_rgb, edit_path, box, ref_box, feather=70):
    size = base_rgb.size
    ed = Image.open(edit_path).convert("RGB").resize(size, Image.LANCZOS)
    dx, dy = align(np.asarray(base_rgb, float), np.asarray(ed, float), ref_box)
    shifted = Image.new("RGB", size); shifted.paste(ed, (dx, dy))
    a = ellipse_alpha(box, size, feather)
    rgba = shifted.convert("RGBA"); rgba.putalpha(a)
    print(f"  {os.path.basename(edit_path)}: shift {dx:+d},{dy:+d}")
    return rgba.crop(box)

def main(src):
    os.makedirs(OUT, exist_ok=True)
    base = Image.open(os.path.join(src, "base.jpg")).convert("RGB")
    cut = Image.open(os.path.join(src, "cutout.png")).convert("RGBA").resize(base.size, Image.LANCZOS)
    full = base.convert("RGBA"); full.putalpha(cut.split()[3])          # sharp original pixels, Runway's fur matte
    full.save(os.path.join(OUT, "base.png"))
    eyes_ref = (450, 400, 1100, 640)     # unchanged by mouth edits
    mouth_ref = (300, 1050, 1250, 1600)  # chest, unchanged by the blink edit
    for v in "AEOUFS":
        patch(base, os.path.join(src, f"{v}.png"), MOUTH_BOX, eyes_ref).save(os.path.join(OUT, f"mouth_{v}.png"))
    patch(base, os.path.join(src, "blink.png"), EYES_BOX, mouth_ref, feather=50).save(os.path.join(OUT, "eyes_closed.png"))
    print("wrote", OUT)

if __name__ == "__main__":
    main(sys.argv[1])
