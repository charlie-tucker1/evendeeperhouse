"""Gate G0 unit tests: constant-tempo grid fit on synthetic material.

Acceptance (directive §4, Gate G0): recover BPM within ±0.01 and beat0 within ±5 ms
from synthetic click tracks with known BPM/phase plus noise.
"""

from __future__ import annotations

import numpy as np
import pytest

from deephouse.analysis.grid import GridFit, fit_grid, grid_beat_times
from deephouse.synth import make_click_track

from .conftest import to_mono

BPM_TOL = 0.01
BEAT0_TOL_S = 0.005


def _phase_error(est_beat0: float, true_beat0: float, period: float) -> float:
    """Smallest |Δ| between beat0 estimates modulo the beat period."""
    d = (est_beat0 - true_beat0) % period
    return min(d, period - d)


@pytest.mark.parametrize(
    "bpm,beat0,down,style,snr",
    [
        (124.0, 0.250, 0, "clicks", 30.0),
        (122.37, 0.113, 2, "clicks", 20.0),
        (127.91, 0.401, 1, "house", 25.0),
        (118.5, 0.020, 3, "house", 15.0),
        (129.8, 0.3891, 0, "house", 12.0),
    ],
)
def test_grid_fit_recovers_synthetic_truth(bpm, beat0, down, style, snr, sr):
    y, truth = make_click_track(
        bpm=bpm, beat0_s=beat0, downbeat_offset=down, duration_s=60.0, sr=sr,
        snr_db=snr, style=style, seed=7,
    )
    g: GridFit = fit_grid(to_mono(y), sr, tracker="librosa")

    assert abs(g.bpm - truth.bpm) <= BPM_TOL, f"bpm {g.bpm:.4f} vs {truth.bpm}"
    assert _phase_error(g.beat0_s, truth.beat0_s, truth.period_s) <= BEAT0_TOL_S, (
        f"beat0 {g.beat0_s:.4f} vs {truth.beat0_s}"
    )
    assert g.confidence >= 0.9
    assert 0 <= g.downbeat_offset <= 3


@pytest.mark.parametrize("down", [0, 1, 2, 3])
def test_downbeat_offset_recovered_on_house_style(down, sr):
    """Downbeats carry a chord stab + louder kick; the novelty vote must find them."""
    y, truth = make_click_track(
        bpm=124.0, beat0_s=0.2, downbeat_offset=down, duration_s=60.0, sr=sr,
        snr_db=25.0, style="house", seed=3,
    )
    g = fit_grid(to_mono(y), sr, tracker="librosa")
    # Grid index 0 may be shifted by a whole number of beats relative to truth
    # (beat0 is defined modulo period), so compare downbeat *times* modulo the bar.
    bar = 4 * truth.period_s
    true_down_t = truth.beat0_s + truth.downbeat_offset * truth.period_s
    est_down_t = g.beat0_s + g.downbeat_offset * g.period_s
    d = (est_down_t - true_down_t) % bar
    assert min(d, bar - d) <= BEAT0_TOL_S


def test_half_double_disambiguation_into_genre_band(sr):
    """A tracker that locks to half-time (62 BPM) must be folded back into [116, 130]."""
    from deephouse.analysis.grid import fold_bpm_into_band

    assert abs(fold_bpm_into_band(62.0, 116.0, 130.0) - 124.0) < 1e-9
    assert abs(fold_bpm_into_band(248.0, 116.0, 130.0) - 124.0) < 1e-9
    assert abs(fold_bpm_into_band(124.0, 116.0, 130.0) - 124.0) < 1e-9
    # Out-of-band and un-foldable: returned unchanged (caller flags low confidence).
    assert abs(fold_bpm_into_band(100.0, 116.0, 130.0) - 100.0) < 1e-9


def test_grid_beat_times_are_exact_and_monotonic():
    g = GridFit(bpm=124.0, beat0_s=0.25, downbeat_offset=1, confidence=1.0)
    t = grid_beat_times(g, duration_s=10.0)
    assert t[0] == pytest.approx(0.25)
    assert np.all(np.diff(t) > 0)
    assert np.allclose(np.diff(t), 60.0 / 124.0)
    assert t[-1] < 10.0
    # downbeat mask
    down = g.downbeat_mask(len(t))
    assert down[1] and not down[0] and down[5]


def test_fit_is_deterministic(sr):
    y, _ = make_click_track(bpm=125.0, beat0_s=0.3, duration_s=30.0, sr=sr, seed=1)
    a = fit_grid(to_mono(y), sr, tracker="librosa")
    b = fit_grid(to_mono(y), sr, tracker="librosa")
    assert a.bpm == b.bpm and a.beat0_s == b.beat0_s and a.downbeat_offset == b.downbeat_offset
