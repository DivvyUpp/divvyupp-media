"""Movie-style characters made from one Runway still plus mouth/eye patches (see build_movie_char.py).
Same contract as animals.sprite / characters.sprite: sprite(name, mouth, blink, mood, height) -> RGBA image."""
import os
from functools import lru_cache
from PIL import Image
import numpy as np

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

VOWEL = {**{c: "A" for c in "a"}, **{c: "E" for c in "eiy"}, **{c: "O" for c in "o"}, **{c: "U" for c in "uw"}}

def letter_track(ch, st, en, env, lead_s, fps, n):
    """Per-frame (vowel kind, consonant) from the ElevenLabs character timings, cleaned up:
    - words squeezed by the aligner (typically the first word after an [emotion] tag, e.g. "Rule" reported as
      50 ms when it lasts ~350 ms) are re-timed to where the voice actually is, using the loudness `env`;
    - a silent final e ("rule", "save") is ignored;
    - each frame gets the vowel of the syllable it sits in (nearest vowel letter in the same word)."""
    words, cur, tag = [], [], False
    for c, a, b in zip(ch, st, en):
        if c == "[": tag = True
        elif c == "]": tag = False; continue
        if tag: continue
        if c.isalpha() or (c == "'" and cur): cur.append([c.lower(), lead_s + a, lead_s + b])
        elif cur: words.append(cur); cur = []
    if cur: words.append(cur)
    for w in words:                                             # silent final e
        if len(w) >= 4 and w[-1][0] == "e" and w[-2][0] not in "aeiouy" and w[-2][0] != "l" or \
           (len(w) == 4 and w[-1][0] == "e" and w[-2][0] == "l"):
            w[-2][2] = w[-1][2]; w.pop()
    for k, w in enumerate(words):                               # re-time squeezed words
        a, b = w[0][1], w[-1][2]; L = len(w)
        if b - a >= 0.05 * L: continue
        prev_end = words[k - 1][-1][2] if k else 0.0
        nxt = words[k + 1][0][1] if k + 1 < len(words) else b + 0.3
        f = int(a * fps)
        while f - 1 > prev_end * fps and f - 1 >= 0 and env[f - 1] > 0.08: f -= 1
        a2 = min(a, f / fps); b2 = max(b, min(nxt - 0.03, a2 + 0.08 * L))
        for i, l in enumerate(w): l[1] = a2 + (b2 - a2) * i / L; l[2] = a2 + (b2 - a2) * (i + 1) / L
    out = [(None, None)] * n
    for w in words:
        vow = [(l[0], (l[1] + l[2]) / 2) for l in w if l[0] in VOWEL]
        for l in w:
            for f in range(max(0, int(l[1] * fps)), min(n, int(np.ceil(l[2] * fps)))):
                t = (f + 0.5) / fps
                v = VOWEL[min(vow, key=lambda x: abs(x[1] - t))[0]] if vow else None
                c = "M" if l[0] in "mbp" else "F" if l[0] in "fv" else None
                out[f] = (v, c)
    filled = [i for i, x in enumerate(out) if x[0]]                   # gaps between words: borrow the nearest vowel
    import bisect
    for f in range(n):
        if out[f][0] is None and filled:
            k = bisect.bisect_left(filled, f); cand = [filled[j] for j in (k - 1, k) if 0 <= j < len(filled)]
            g = min(cand, key=lambda j: abs(j - f))
            if abs(g - f) <= 5: out[f] = (out[g][0], None)
    return out

def audio_track(letters, env, lead=1):
    """Mouth track driven by the actual voice: how OPEN the mouth is comes from the loudness of the sound in each
    frame (so it can't drift from what you hear); the letters only pick the KIND of shape (round for o/u/w,
    narrow for ee/i, teeth on lip for f/v, closed lips for m/b/p). `letters` = letter_track() output.
    Lips lead the sound by `lead` frames. Returns per-frame tuples (shape_from, shape_to, w) for sprite()."""
    n = len(letters); env = np.asarray(env, float)[:n]
    if len(env) < n: env = np.pad(env, (0, n - len(env)))
    e = np.concatenate([env[lead:], np.zeros(lead)]) if lead else env
    lt = letters[lead:] + [(None, None)] * lead
    seq = []
    for f in range(n):
        x = e[f]; vow, con = lt[f]
        cons_near = [lt[j][1] for j in range(f, min(n, f + 2))]
        if x < 0.10: v = "rest"
        elif "M" in cons_near and x < 0.45: v = "rest"                   # m/b/p: lips close
        elif con == "F" and x < 0.5: v = "F"
        elif vow == "O": v = "U" if x < 0.35 else "O"
        elif vow == "U": v = "U" if x < 0.6 else "O"
        elif vow == "E": v = "S" if x < 0.30 else "E"                     # ee/i: never the wide-open mouth
        else: v = "S" if x < 0.30 else "E" if x < 0.80 else "A"
        seq.append(v)
    for f in range(1, n - 1):                                             # drop single-frame flickers
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
