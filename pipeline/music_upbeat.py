"""An upbeat music bed: 118 bpm, C - G - Am - F, kick/clap/hat, bouncy bass and plucked stabs. Synthesised from
scratch (no samples, no licensing). Used by make_realnumbers_reel.py; music.py is the slower 88 bpm pad."""
import numpy as np
import music

def upbeat_bed(seconds, sr=24000, seed=5):
    bpm = 118; beat = 60 / bpm; n = int(seconds * sr); out = np.zeros(n + sr * 2)
    prog = [[60, 64, 67], [67, 71, 74], [69, 72, 76], [65, 69, 72]]             # C G Am F
    rng = np.random.default_rng(seed); tb = np.arange(int(beat * sr)) / sr
    kick = np.sin(2 * np.pi * (45 + 75 * np.exp(-tb * 30)) * tb) * np.exp(-tb * 9)
    th = np.arange(int(0.06 * sr)) / sr; hat = rng.normal(0, 1, len(th)) * np.exp(-th * 60); hat = np.diff(np.r_[0, hat])
    tc = np.arange(int(0.18 * sr)) / sr; clap = rng.normal(0, 1, len(tc)) * np.exp(-tc * 22)
    def add(sig, at, g):
        s = int(at * sr); e = min(len(out), s + len(sig))
        if s < len(out): out[s:e] += sig[:e - s] * g
    nbeats = int(seconds / beat) + 2
    for b in range(nbeats):
        t0 = b * beat; ch = prog[(b // 4) % 4]
        add(kick, t0, 0.55)
        if b % 2 == 1: add(clap, t0, 0.16)
        add(hat, t0 + beat / 2, 0.22)
        root = ch[0] - 24; tn = np.arange(int(beat / 2 * sr)) / sr          # bouncy eighth-note bass
        for half in (0, 1):
            f = music.hz(root + (12 if half else 0))
            add(np.sin(2 * np.pi * f * tn) * np.exp(-tn * 6), t0 + half * beat / 2, 0.30)
        for j, sub in enumerate((0, 0.5)):                                    # bright plucked chord stabs
            if (b + j) % 2 == 0:
                note = ch[(b + j) % 3] + 12
                add(music.pluck(music.hz(note), 0.5, sr, rng), t0 + sub * beat, 0.16)
    out = out[:n]
    fade = int(0.8 * sr); out[:fade] *= np.linspace(0, 1, fade); out[-fade:] *= np.linspace(1, 0, fade)
    return out / (np.abs(out).max() + 1e-9) * 0.16
