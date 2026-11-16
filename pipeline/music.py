"""A light, original background bed synthesised from scratch (no samples, no licensing): a warm pad plus a soft
plucked arpeggio over C - Am - F - G at 88 bpm. `bed(seconds, sr)` returns mono float audio at roughly -20 dBFS peak;
`mix_under(voice, sr)` lays it under a voice track and ducks it while someone is speaking."""
import numpy as np

BPM = 88
CHORDS = [[48, 55, 60, 64], [45, 52, 57, 60], [41, 48, 53, 57], [43, 50, 55, 59]]  # C, Am, F, G (MIDI)

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

def pluck(f, dur, sr, rng):
    """Karplus-Strong string, softened."""
    n = int(dur * sr); p = max(2, int(sr / f)); buf = rng.uniform(-1, 1, p) * 0.5; out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % p]; buf[i % p] = 0.4975 * (buf[i % p] + buf[(i + 1) % p])
    return out * np.exp(-np.arange(n) / (sr * 0.9))

def bed(seconds, sr=24000, seed=3):
    rng = np.random.default_rng(seed); n = int(seconds * sr); out = np.zeros(n + sr * 4)
    beat = 60 / BPM; bar = 4 * beat; t = np.arange(int(2 * bar * sr)) / sr
    env = np.minimum(1, t / 1.2) * np.minimum(1, (2 * bar - t) / 1.0)            # pad swell per 2-bar chord
    pos, ci = 0, 0
    while pos < n:
        ch = CHORDS[ci % len(CHORDS)]; seg = np.zeros(len(t))
        for m in ch:
            f = hz(m + 12)
            seg += (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t + 0.5) + 0.12 * np.sin(2 * np.pi * 3 * f * t)) \
                   * (1 + 0.15 * np.sin(2 * np.pi * 0.25 * t + m))
        seg *= env * 0.05; end = min(len(out), pos + len(seg)); out[pos:end] += seg[:end - pos]
        arp = [ch[1] + 24, ch[2] + 24, ch[3] + 24, ch[2] + 24]                     # eighth-note arpeggio
        for k in range(16):
            s = pos + int(k * beat / 2 * sr)
            if s >= len(out): break
            note = pluck(hz(arp[k % 4]), 1.2, sr, rng) * (0.10 if k % 4 == 0 else 0.07)
            e = min(len(out), s + len(note)); out[s:e] += note[:e - s]
        pos += len(t); ci += 1
    out = out[:n]
    # gentle one-pole low-pass to keep it soft
    a = np.exp(-2 * np.pi * 3500 / sr); y = np.empty_like(out); acc = 0.0
    for i, v in enumerate(out): acc = (1 - a) * v + a * acc; y[i] = acc
    fade = int(1.5 * sr); y[:fade] *= np.linspace(0, 1, fade); y[-fade:] *= np.linspace(1, 0, fade)
    return y / (np.abs(y).max() + 1e-9) * 0.1        # peak about -20 dBFS

def mix_under(voice, sr, under_speech=0.45):
    """Return voice + bed, with the bed ducked to `under_speech` of its level while the voice is active."""
    m = bed(len(voice) / sr, sr); m = np.pad(m, (0, max(0, len(voice) - len(m))))[:len(voice)]   # exact length (float rounding)
    w = int(0.25 * sr); loud = np.convolve(np.abs(voice), np.ones(w) / w, "same")
    active = np.clip(loud / 0.02, 0, 1)
    sm = int(0.4 * sr); active = np.convolve(active, np.ones(sm) / sm, "same")
    mix = voice + m * (1 - (1 - under_speech) * active)
    return mix / max(1.0, np.abs(mix).max() / 0.98)
