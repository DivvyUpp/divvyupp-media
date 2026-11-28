"""Tests for the V2 diagram elements (2026-11-28). Run: python3 -m pytest -q pipeline"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_diagram_reel as m


def test_diverge_starts_level_and_ends_at_offset():
    pts = m.diverge_points(100, 700, 500, 180, 1.0, 1.0)
    assert pts[0] == (100, 500)
    assert abs(pts[-1][0] - 700) < 1e-9 and abs(pts[-1][1] - 680) < 1e-9


def test_diverge_is_flat_before_split():
    pts = m.diverge_points(100, 700, 500, 180, 1.0, 0.0)
    assert all(y == 500 for _, y in pts)


def test_diverge_partial_draw_stops_early():
    pts = m.diverge_points(100, 700, 500, 0, 0.5, 1.0)
    assert pts[-1][0] == 400


def test_diverge_stays_level_for_first_part():
    pts = m.diverge_points(0, 1000, 0, 100, 1.0, 1.0)
    assert all(y == 0 for x, y in pts if x < 180)
    ys = [y for _, y in pts]
    assert ys == sorted(ys)  # monotone drop, no wiggle


def test_new_elements_registered():
    assert m.DRAW["diverge"] is m.e_diverge and m.DRAW["bubble"] is m.e_bubble


def test_voice_onset_finds_sound_before_late_timestamp():
    import numpy as np
    sr = m.SR; a = np.zeros(int(1.0 * sr)); a[int(0.10 * sr):int(0.6 * sr)] = 0.3  # speech starts at 0.10 s
    assert abs(m.voice_onset(a) - 0.10) < 0.011


def test_voice_onset_silent_audio_is_zero():
    import numpy as np
    assert m.voice_onset(np.zeros(m.SR)) == 0.0
