"""Movie-style characters made from one Runway still plus mouth/eye patches (see build_movie_char.py).
Same contract as animals.sprite / characters.sprite: sprite(name, mouth, blink, mood, height) -> RGBA image."""
import os
from functools import lru_cache
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "assets", "characters")
CHARS = {"raccoon_movie": dict(dir="raccoon_movie", mouth_box=(500, 590), eyes_box=(440, 380))}
VISEME = {"rest": None, "M": None, "A": "A", "E": "E", "O": "O", "U": "U", "F": "F", "S": "S", "L": "S"}
LEVEL = {0: None, 1: "S", 2: "E", 3: "A"}           # legacy loudness levels

@lru_cache(maxsize=8)
def _part(name, part):
    return Image.open(os.path.join(ROOT, CHARS[name]["dir"], part + ".png")).convert("RGBA")

@lru_cache(maxsize=4)
def _faded_alpha(name):
    import numpy as np
    a = np.asarray(_part(name, "base").split()[3], float); h = a.shape[0]; f0 = int(h * 0.90)
    a[f0:] *= np.linspace(1, 0, h - f0)[:, None]
    return Image.fromarray(a.astype("uint8"))

@lru_cache(maxsize=64)
def sprite(name, mouth=0, blink=False, mood="neutral", height=720):
    c = CHARS[name]
    v = VISEME.get(mouth) if isinstance(mouth, str) else LEVEL.get(int(mouth))
    img = _part(name, "base").copy()
    if v: img.alpha_composite(_part(name, f"mouth_{v}"), c["mouth_box"])
    if blink: img.alpha_composite(_part(name, "eyes_closed"), c["eyes_box"])
    img.putalpha(_faded_alpha(name))           # patches never change his outline; waist fades out softly
    w = round(height * img.width / img.height)
    return img.resize((w, height), Image.LANCZOS)
