"""Phase 1 renderer tests: recipe contract, DSP primitives, determinism, alignment, loudness."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest

from deephouse.analysis.grid import GridFit, fit_grid
from deephouse.render import dsp
from deephouse.render.engine import RenderConfig, RenderError, Track, render
from deephouse.render.recipe import TransitionRecipe, default_grid
from deephouse.synth import make_click_track

GOLDEN = Path(__file__).parent / "fixtures" / "render_golden.json"


# ------------------------------------------------------------------ recipe


def test_recipe_grid_and_roundtrip():
    grid = default_grid()
    assert len(grid) == 16 and len({r.key for r in grid}) == 16
    r = grid[3]
    assert TransitionRecipe.from_dict(json.loads(json.dumps(r.to_dict()))) == r
    with pytest.raises(ValueError):
        TransitionRecipe.from_dict({"overlap_bars": 16, "mystery": 1})
    with pytest.raises(ValueError):
        TransitionRecipe(overlap_bars=12)
    assert TransitionRecipe().key == "ov16_eqp_bs50_hpf0"


# ------------------------------------------------------------------ dsp


def test_equal_power_and_breakpoints():
    fo, fi = dsp.equal_power_pair(1000)
    assert np.allclose(fo**2 + fi**2, 1.0, atol=1e-6)
    g = dsp.gain_from_breakpoints([(100, 0.0), (200, -6.0), (300, float("-inf"))], 400)
    assert g[0] == 1.0 and g[100] == 1.0 and abs(g[200] - 10 ** (-6 / 20)) < 1e-6 and g[350] == 0.0
    assert np.all(np.diff(g[100:300]) <= 1e-7)


def test_lr4_split_is_magnitude_flat(sr):
    rng = np.random.default_rng(0)
    y = rng.standard_normal((sr * 2, 2)).astype(np.float32) * 0.1
    lo, hi = dsp.lr4_split(y, sr, 120.0)
    s = lo + hi
    Y, S = np.abs(np.fft.rfft(y[:, 0])), np.abs(np.fft.rfft(s[:, 0]))
    f = np.fft.rfftfreq(len(y), 1 / sr)
    band = (f > 40) & (f < 8000)
    # smooth the spectra over 50 bins before comparing (single-bin noise otherwise)
    k = np.ones(50) / 50
    ratio = np.convolve(S[band], k, "same") / np.convolve(Y[band], k, "same")
    assert np.all(np.abs(20 * np.log10(ratio[60:-60])) < 0.5)


def test_sweep_filter_bypass_and_continuity(sr):
    rng = np.random.default_rng(1)
    y = rng.standard_normal((sr, 2)).astype(np.float32) * 0.1
    out = dsp.sweep_filter(y, sr, np.full(20, 20.0), sr // 20, kind="hpf")
    assert np.array_equal(out, y)                                  # <=20 Hz HPF is a bypass
    cut = np.geomspace(250.0, 20.0, 20)
    out = dsp.sweep_filter(y, sr, cut, sr // 20, kind="hpf")
    assert np.isfinite(out).all() and out.shape == y.shape
    # no clicks at block boundaries: sample-to-sample jumps stay in the same range as the input
    assert np.abs(np.diff(out[:, 0])).max() < 3 * np.abs(np.diff(y[:, 0])).max()


def test_resample_stretch_changes_tempo_exactly(sr):
    y, tr = make_click_track(bpm=120.0, beat0_s=0.1, duration_s=30.0, sr=sr, style="clicks", seed=0)
    rate = 124.0 / 120.0
    st = dsp.time_stretch(y, sr, rate, backend="resample")
    assert abs(len(st) - len(y) / rate) <= 2
    g = fit_grid(st.mean(axis=1), sr, tracker="librosa")
    assert abs(g.bpm - 124.0) < 0.02


def test_limiter_respects_ceiling_and_is_transparent_when_quiet(sr):
    q = np.full((sr, 2), 0.1, dtype=np.float32)
    assert np.array_equal(dsp.limiter(q, sr, ceiling_db=-1.0), q)
    loud = np.sin(np.linspace(0, 2 * np.pi * 50, sr)).astype(np.float32)[:, None] * np.float32(2.0)
    out = dsp.limiter(np.repeat(loud, 2, axis=1), sr, ceiling_db=-1.0)
    assert np.abs(out).max() <= 10 ** (-1 / 20) + 1e-4


# ------------------------------------------------------------------ engine


@pytest.fixture(scope="module")
def pair(sr):
    """A at 124 BPM, B at 120 BPM (rate 1.033), with synthetic stems that sum to the mix."""

    def make(bpm, beat0, seed, dur):
        y, tr = make_click_track(bpm=bpm, beat0_s=beat0, downbeat_offset=0, duration_s=dur, sr=sr,
                                 snr_db=30, style="house", seed=seed, pump_depth_db=3.0)
        g = GridFit(bpm=tr.bpm, beat0_s=tr.beat0_s, downbeat_offset=0, confidence=1.0)
        # zero-phase split for the fixture: demucs stems are time-aligned with the mix, and a
        # causal crossover would put ~3 ms of group delay into the "bass" stem
        from scipy.signal import butter, sosfiltfilt

        lo = sosfiltfilt(butter(4, 150.0, btype="low", fs=sr, output="sos"), y, axis=0).astype(np.float32)
        hi = (y - lo).astype(np.float32)
        stems = {"bass": lo, "drums": hi * np.float32(0.5), "other": hi * np.float32(0.5), "vocals": np.zeros_like(y)}
        return Track(f"synth{seed}", y, sr, g, stems=stems)

    return make(124.0, 0.2, 1, 45.0), make(120.0, 0.3, 2, 60.0)


CFG = RenderConfig(lead_in_bars=4, tail_bars=8, stretch_backend="resample")


def test_render_is_deterministic_and_matches_golden(pair):
    a, b = pair
    r1 = render(a, 8, b, 2, TransitionRecipe(), CFG)
    r2 = render(a, 8, b, 2, TransitionRecipe(), CFG)
    assert np.array_equal(r1.audio, r2.audio)
    n_bar = r1.meta["samples_per_bar"]
    assert len(r1.audio) == (4 + 16 + 8) * n_bar
    h = hashlib.sha256(r1.audio.tobytes()).hexdigest()
    key = f"{r1.meta['recipe_key']}|{r1.meta['config_digest']}|{r1.meta['stretch_backend']}"
    golden = json.loads(GOLDEN.read_text()) if GOLDEN.exists() else {}
    if key in golden and not os.environ.get("DEEPHOUSE_UPDATE_GOLDEN"):
        assert golden[key] == h, "render output changed — set DEEPHOUSE_UPDATE_GOLDEN=1 if intentional"
    else:
        golden[key] = h
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(golden, indent=1, sort_keys=True))


def test_null_lead_in_is_bit_exact_pre_master(pair):
    a, b = pair
    cfg = RenderConfig(lead_in_bars=4, tail_bars=8, stretch_backend="resample", master=False)
    r = render(a, 8, b, 2, TransitionRecipe(), cfg)
    n_lead = r.meta["overlap_start_sample"]
    s = int(round((a.bar_time(8) - 4 * 4 * a.grid.period_s) * a.sr))
    st = a.stems
    ref = st["bass"][s:s + n_lead] + (st["drums"][s:s + n_lead] + st["other"][s:s + n_lead]) + st["vocals"][s:s + n_lead]
    assert np.array_equal(r.audio[:n_lead], ref)


def test_alignment_b_tail_is_at_a_tempo_and_phase(pair, sr):
    a, b = pair
    r = render(a, 8, b, 2, TransitionRecipe(overlap_bars=16), CFG)
    n_bar = r.meta["samples_per_bar"]
    mono = r.audio.mean(axis=1)
    # whole render: A's tempo, downbeat at sample 0
    g = fit_grid(mono, sr, tracker="librosa")
    P = 60 / 124.0
    assert abs(g.bpm - 124.0) < 0.02
    ph = g.beat0_s % P
    assert min(ph, P - ph) < 0.004
    # B-alone tail: its kicks must sit on A's grid — fold the tail at A's period from phase 0
    # and locate the attack; the stretch + cut must have landed B's downbeat within 3 ms.
    from deephouse.analysis.grid import refine_phase

    lead = mono[: r.meta["overlap_start_sample"]]
    tail = mono[r.meta["overlap_end_sample"]:]
    beat0_lead, _ = refine_phase(lead, sr, P, 0.0, window_s=0.06)
    beat0_tail, contrast = refine_phase(tail, sr, P, 0.0, window_s=0.06)
    assert abs(beat0_tail - beat0_lead) < 0.001, f"B tail kicks are {(beat0_tail - beat0_lead) * 1000:.2f} ms off A's kicks"
    assert abs(beat0_tail) < 0.003
    assert contrast > 1.5                                            # on-beat energy > anti-beat (hats live there)
    assert r.meta["path"] == "stems" and abs(r.meta["stretch_rate"] - 124 / 120) < 1e-9
    assert r.meta["bass_swap_sample"] == 4 * n_bar + 8 * n_bar


def test_bands_path_when_no_stems(pair, sr):
    a, b = pair
    a2 = Track(a.sha1, a.audio, sr, a.grid, stems=None)
    b2 = Track(b.sha1, b.audio, sr, b.grid, stems=None)
    r = render(a2, 8, b2, 2, TransitionRecipe(entry_hpf_sweep=True, entry_curve="stepped"), CFG)
    assert r.meta["path"] == "bands" and np.isfinite(r.audio).all()
    assert np.abs(r.audio).max() <= 10 ** (-1 / 20) + 1e-3


def test_loudness_continuity_across_seam(pair, sr):
    a, b = pair
    r = render(a, 8, b, 2, TransitionRecipe(), CFG)
    n_lead, n_end = r.meta["overlap_start_sample"], r.meta["overlap_end_sample"]
    la = dsp.integrated_lufs(r.audio[:n_lead], sr)
    lb = dsp.integrated_lufs(r.audio[n_end:], sr)
    assert abs(la - lb) < 1.5
    # synthetic material has an extreme crest factor, so the peak limiter eats a few LU after the
    # trim; real masters land near target. Peaks must respect the ceiling regardless.
    assert abs(dsp.integrated_lufs(r.audio, sr) - CFG.target_lufs) < 3.0
    assert np.abs(r.audio).max() <= 10 ** ((CFG.ceiling_dbtp - 0.3) / 20) + 1e-4


def test_all_16_recipes_render(pair):
    a, b = pair
    for rec in default_grid():
        if rec.overlap_bars > 16:
            continue  # B fixture is not long enough for 32-bar overlaps + tail
        r = render(a, 8, b, 2, rec, CFG)
        assert np.isfinite(r.audio).all() and len(r.audio) == (4 + rec.overlap_bars + 8) * r.meta["samples_per_bar"]


def test_stretch_limit_enforced(pair, sr):
    a, b = pair
    far = Track("far", b.audio, sr, GridFit(bpm=110.0, beat0_s=0.3, downbeat_offset=0, confidence=1.0))
    with pytest.raises(RenderError):
        render(a, 8, far, 2, TransitionRecipe(), CFG)


def test_low_band_stays_flat_through_the_seam(pair, sr):
    """Regression: A's bass must not follow the crossfade, and the swap must not notch.
    Per-beat low-band RMS across lead-in → overlap → tail stays within ±2.5 dB of the lead-in."""
    from scipy.signal import butter, sosfiltfilt

    a, b = pair
    r = render(a, 8, b, 2, TransitionRecipe(bass_swap_frac=0.5), CFG)
    mono = r.audio.mean(axis=1)
    low = sosfiltfilt(butter(4, 150.0, btype="low", fs=sr, output="sos"), mono)
    n_beat = r.meta["samples_per_bar"] // 4
    n = len(low) // n_beat
    rms_db = 20 * np.log10(np.sqrt((low[: n * n_beat].reshape(n, n_beat) ** 2).mean(axis=1)) + 1e-9)
    lead_beats = r.meta["overlap_start_sample"] // n_beat
    ref = np.median(rms_db[:lead_beats])
    assert np.all(np.abs(rms_db[2:-2] - ref) < 2.5), f"low band deviates up to {np.abs(rms_db[2:-2] - ref).max():.1f} dB"
