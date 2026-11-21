"""Movie-style characters made from one Runway still plus mouth/eye patches (see build_movie_char.py).
Same contract as animals.sprite / characters.sprite: sprite(name, mouth, blink, mood, height) -> RGBA image."""
import os
from functools import lru_cache
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "assets", "characters")
CHARS = {"raccoon_movie": dict(dir="raccoon_movie", mouth_box=(430, 560), eyes_box=(440, 380))}
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

def _mouth_img(name, v):
    img = _part(name, "base").copy()
    if v: img.alpha_composite(_part(name, f"mouth_{v}"), CHARS[name]["mouth_box"])
    return img

def smooth(vis, fps=30, lead=2):
    """Make the per-frame viseme track readable: hold every shape at least ~100 ms (closed lips for m/b/p ~67 ms),
    use the big wide-open shape only on longer vowels, and blend one frame at each change.
    Returns per-frame tuples (shape_from, shape_to, w) for sprite()."""
    runs = []
    for v in vis:
        v = VISEME.get(v, None) if isinstance(v, str) else LEVEL.get(int(v))
        v = v or "rest"
        if runs and runs[-1][0] == v: runs[-1][1] += 1
        else: runs.append([v, 1])
    def min_len(v): return 2 if v == "rest" else 3
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for i, (v, k) in enumerate(runs):
            if k < min_len(v):
                j = i + 1 if i + 1 < len(runs) else i - 1           # fold short runs into the NEXT shape (anticipate, never lag)
                runs[j][1] += k; del runs[i]; changed = True; break
        merged = []
        for v, k in runs:
            if merged and merged[-1][0] == v: merged[-1][1] += k
            else: merged.append([v, k])
        runs = merged
    for r in runs:
        if r[0] == "A" and r[1] < 5: r[0] = "E"                     # short vowels: medium open, not a shout
    seq = [v for v, k in runs for _ in range(k)]
    seq = seq[lead:] + [seq[-1]] * lead                              # lips lead the sound by `lead` frames
    out = []
    for f, v in enumerate(seq):                                       # blend on the frame BEFORE each change
        nxt = seq[f + 1] if f + 1 < len(seq) else v
        out.append((v, nxt, 0.5) if nxt != v else (v, v, 1.0))
    return out

def audio_track(vis, env, lead=1):
    """Mouth track driven by the actual voice: how OPEN the mouth is comes from the loudness of the sound in each
    frame (so it can't drift from what you hear); the letters only pick the KIND of shape (round for o/u/w,
    teeth on lip for f/v, closed lips for m/b/p). `env` = per-frame loudness 0..1 aligned with the video frames.
    Lips lead the sound by `lead` frames. Returns per-frame tuples (shape_from, shape_to, w) for sprite()."""
    import numpy as np
    n = len(vis); env = np.asarray(env, float)[:n]
    if len(env) < n: env = np.pad(env, (0, n - len(env)))
    e = np.concatenate([env[lead:], np.zeros(lead)]) if lead else env
    kinds = [VISEME.get(v) if isinstance(v, str) else None for v in vis]
    seq = []
    for f in range(n):
        win = [kinds[j] for j in range(max(0, f - 1), min(n, f + 3)) if kinds[j]]     # letters near this moment
        x = e[f]
        if x < 0.10: v = "rest"
        elif "M" in [vis[j] for j in range(max(0, f), min(n, f + 2))] and x < 0.45: v = "rest"   # m/b/p: lips close
        elif "F" in win[:2] and x < 0.5: v = "F"
        elif any(k in ("O", "U") for k in win):
            v = "U" if x < 0.35 else "O"
        else:
            v = "S" if x < 0.30 else "E" if x < 0.80 else "A"
        seq.append(v)
    for f in range(1, n - 1):                                         # drop single-frame flickers
        if seq[f - 1] == seq[f + 1] != seq[f]: seq[f] = seq[f - 1]
    out = []
    for f, v in enumerate(seq):
        nxt = seq[f + 1] if f + 1 < n else v
        out.append((v, nxt, 0.5) if nxt != v else (v, v, 1.0))
    return out

@lru_cache(maxsize=96)
def sprite(name, mouth=0, blink=False, mood="neutral", height=720):
    c = CHARS[name]
    if isinstance(mouth, tuple):
        a, b, w = mouth
        img = _mouth_img(name, VISEME.get(b))
        if w < 1: img = Image.blend(_mouth_img(name, VISEME.get(a)), img, w)
    else:
        img = _mouth_img(name, VISEME.get(mouth) if isinstance(mouth, str) else LEVEL.get(int(mouth)))
    if blink: img.alpha_composite(_part(name, "eyes_closed"), c["eyes_box"])
    img.putalpha(_faded_alpha(name))           # patches never change his outline; waist fades out softly
    w = round(height * img.width / img.height)
    return img.resize((w, height), Image.LANCZOS)
