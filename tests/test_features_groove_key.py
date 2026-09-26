"""Tests for beat features (P0.5), groove profile (P0.8) and key detection (P0.6)."""

from __future__ import annotations

import numpy as np
import pytest

from deephouse.analysis.features import (
    N_MELS,
    STEMS,
    compute_beat_features,
    load_features,
    save_features,
)
from deephouse.analysis.grid import GridFit, fit_grid, grid_beat_times
from deephouse.analysis.groove import bands_from_mix, compute_groove, groove_compat
from deephouse.analysis.key import estimate_from_chroma
from deephouse.synth import make_click_track

from .conftest import to_mono


@pytest.fixture(scope="module")
def house_pair(sr):
    """(audio_mono, truth, grid) for a straight track and a swung+pumped track."""
    out = {}
    for name, kw in (
        ("straight", {}),
        ("swung", dict(swing=0.58, hats="16ths", pump_depth_db=6.0, pump_release_s=0.25)),
        ("bounce", dict(bass="offbeat", pump_depth_db=4.0, pump_release_s=0.3, swing=0.55, hats="16ths")),
    ):
        y, tr = make_click_track(bpm=124.0, beat0_s=0.2, downbeat_offset=1, duration_s=60.0, sr=sr,
                                 snr_db=25.0, style="house", seed=5, **kw)
        m = to_mono(y)
        g = fit_grid(m, sr, tracker="librosa")
        out[name] = (m, tr, g)
    return out


# ------------------------------------------------------------------ features


def test_beat_features_contract(house_pair, sr, tmp_path):
    m, tr, g = house_pair["straight"]
    stems = {s: m * 0.25 for s in STEMS}                 # shape contract only
    f = compute_beat_features({"mix": m, **stems}, sr, g)
    n = len(grid_beat_times(g, len(m) / sr))
    assert f["beat_times"].shape == (n,) and f["beat_times"].dtype == np.float64
    assert f["mel_mix"].shape == (n, N_MELS) and f["mel_mix"].dtype == np.float32
    assert f["chroma"].shape == (n, 12)
    assert f["rms_mix"].shape == (n,) and f["onset_env_beat"].shape == (n,)
    for s in STEMS:
        assert f[f"mel_{s}"].shape == (n, N_MELS) and f[f"rms_{s}"].shape == (n,)
    # rms of a 0.25-scaled copy is 0.25 × the mix rms
    assert np.allclose(f["rms_bass"][5:-5], 0.25 * f["rms_mix"][5:-5], rtol=1e-3)
    p = tmp_path / "x.npz"
    save_features(p, f)
    assert p.exists() and not p.with_suffix(".npz.tmp").exists()
    back = load_features(p)
    assert set(back) == set(f) and np.array_equal(back["mel_mix"], f["mel_mix"])


def test_beat_aggregation_is_stretch_invariant_by_construction(sr):
    """Same material at two tempos → per-beat features line up index-for-index."""
    feats = []
    for bpm in (120.0, 126.0):
        y, tr = make_click_track(bpm=bpm, beat0_s=0.1, duration_s=40.0, sr=sr, snr_db=30, style="house", seed=2)
        g = GridFit(bpm=tr.bpm, beat0_s=tr.beat0_s, downbeat_offset=0, confidence=1.0)
        feats.append(compute_beat_features({"mix": to_mono(y)}, sr, g))
    a, b = feats
    n = min(len(a["rms_mix"]), len(b["rms_mix"])) - 2
    # the accented downbeat class (index 0 mod 4) is the loudest class at both tempos,
    # i.e. beat index k means the same musical thing regardless of BPM
    for f in (a, b):
        cls = [f["rms_mix"][p:n:4].mean() for p in range(4)]
        assert int(np.argmax(cls)) == 0
    assert np.corrcoef(a["chroma"][:n].ravel(), b["chroma"][:n].ravel())[0, 1] > 0.9


# ------------------------------------------------------------------ groove


def test_groove_swing_recovered(house_pair, sr):
    m, tr, g = house_pair["swung"]
    pr = compute_groove(bands_from_mix(m, sr), sr, g, len(m) / sr)
    assert pr.swing_confidence > 0.8
    assert abs(pr.swing_pct - tr.swing) < 0.008                       # 1.5 ms at 124 BPM
    d = np.array(pr.delta_ms["high"])
    assert abs(d[1::2].mean() - tr.swing_delay_s * 1000) < 2.0
    assert np.abs(d[0::2]).mean() < 2.0
    m0, tr0, g0 = house_pair["straight"]
    pr0 = compute_groove(bands_from_mix(m0, sr), sr, g0, len(m0) / sr)
    assert pr0.swing_confidence == 0.0 and pr0.swing_pct == 0.5     # off-beat-8th hats: swing undefined


def test_groove_patterns(house_pair, sr):
    m, tr, g = house_pair["straight"]
    pr = compute_groove(bands_from_mix(m, sr), sr, g, len(m) / sr)
    hat = np.array(pr.hat_pattern)
    assert hat[[2, 6, 10, 14]].sum() > 0.8                           # off-beat-8th hats
    assert abs(sum(pr.hat_pattern) - 1) < 1e-6 and abs(sum(pr.bass_pattern) - 1) < 1e-6
    mb, trb, gb = house_pair["bounce"]
    prb = compute_groove(bands_from_mix(mb, sr), sr, gb, len(mb) / sr)
    bass_off = np.array(prb.bass_pattern)[[2, 6, 10, 14]].sum()
    bass_off_straight = np.array(pr.bass_pattern)[[2, 6, 10, 14]].sum()
    assert bass_off > 0.3 and bass_off > 3 * bass_off_straight     # off-beat bass shows up


def test_groove_pump(house_pair, sr):
    m, tr, g = house_pair["swung"]
    pr = compute_groove(bands_from_mix(m, sr), sr, g, len(m) / sr)
    assert abs(pr.pump_depth_db - tr.pump_depth_db) < 1.5
    assert abs(pr.pump_release_ms - 0.9 * tr.pump_release_s * 1000) < 60
    m0, _, g0 = house_pair["straight"]
    pr0 = compute_groove(bands_from_mix(m0, sr), sr, g0, len(m0) / sr)
    assert pr0.pump_depth_db == 0.0


def test_groove_kick_and_serialisation(house_pair, sr):
    m, tr, g = house_pair["straight"]
    pr = compute_groove(bands_from_mix(m, sr), sr, g, len(m) / sr)
    assert 0.5 < pr.kick_rise_ms < 15.0 and pr.kick_decay_ms > 0
    assert pr.bars_used >= 15
    d = pr.to_dict()
    assert type(pr).from_dict(d).swing_pct == pr.swing_pct


def test_groove_compat_features(house_pair, sr):
    ms, _, gs = house_pair["straight"]
    mw, _, gw = house_pair["swung"]
    a = compute_groove(bands_from_mix(ms, sr), sr, gs, len(ms) / sr)
    b = compute_groove(bands_from_mix(mw, sr), sr, gw, len(mw) / sr)
    same = groove_compat(a, a, gs.period_s)
    diff = groove_compat(a, b, gs.period_s)
    assert same["swing_mismatch_ms"] == 0 and same["flam_risk_ms"] == 0 and same["pump_mismatch"] == 0
    assert same["bass_pattern_continuity"] == pytest.approx(1.0)
    assert 17 < diff["swing_mismatch_ms"] < 22                      # 0.08 × 242 ms
    assert diff["pump_mismatch"] > 4                                # 0 vs ~6 dB
    assert diff["flam_risk_ms"] < 2.0                               # straight track has no odd-16th hits to flam


# ------------------------------------------------------------------ key


def test_key_from_chroma_on_synthetic_a_minor(house_pair, sr):
    m, tr, g = house_pair["straight"]
    f = compute_beat_features({"mix": m}, sr, g)
    est = estimate_from_chroma(f["chroma"])
    assert est.camelot == "8A" and est.name == "A minor"
    assert est.confidence > 0.2


@pytest.mark.parametrize("pc,minor,code", [(0, False, "8B"), (9, True, "8A"), (7, False, "9B"), (2, True, "7A")])
def test_key_templates_exact(pc, minor, code):
    from deephouse.analysis.key import _MAJOR, _MINOR

    v = np.roll(_MINOR if minor else _MAJOR, pc)
    est = estimate_from_chroma(v)
    assert est.camelot == code
    assert est.confidence > 0.5


# ------------------------------------------------------------------ structure (P0.7)


def test_structure_boundaries_labels_and_cues(sr):
    from deephouse.analysis.sections import analyze_structure

    full = {"kick", "hats", "bass", "pad", "stab"}
    arr = [(8, {"hats", "pad"}), (16, full), (8, {"pad", "stab"}), (16, full), (8, {"kick", "hats"})]
    y, tr = make_click_track(bpm=124.0, beat0_s=0.2, downbeat_offset=1, duration_s=120.0, sr=sr, style="house",
                             arrangement=arr, snr_db=25, seed=3)
    m = to_mono(y)
    g = fit_grid(m, sr, tracker="librosa")
    assert abs(g.bpm - 124.0) < 0.01 and g.confidence > 0.9          # breakdowns must not break the grid
    f = compute_beat_features({"mix": m}, sr, g)
    st = analyze_structure(f, g)
    truth = [8, 24, 32, 48]
    assert all(min(abs(b - t) for b in st.boundaries) <= 1 for t in truth), st.boundaries
    assert len(st.boundaries) <= 6
    labels = [s.label for s in st.sections]
    assert labels[0] == "intro" and labels[-1] == "outro" and "breakdown" in labels and "main" in labels
    assert st.phrase0_bar == 0
    assert any(c.bar in (0, 8) for c in st.cues_in)
    assert st.cues_out and st.cues_out[-1].bar == 48 and max(st.cues_out, key=lambda c: c.score).bar == 48
    d = st.to_dict()
    assert d["n_bars"] == st.n_bars and len(d["sections"]) == len(st.sections)
