"""Groove profile (P0.8, see docs/GROOVE.md): the micro-timing layer beneath the beat grid.

Everything here is a *fold* — average the track's band-limited energy (or its attack
signal) over hundreds of bars at a fixed phase, so per-hit noise averages out and the
record's habitual micro-timing, pattern, and pump shape remain. Cheap, stable, deterministic.

Bands (from stems when available, else zero-phase band splits of the mix):
  low   <150 Hz   kick + bass          (stem: bass + drums low)
  mid   150–5k    pads, chords, vocals (stem: other)
  high  >5 kHz    hats, percussion     (stem: drums high)

Sixteenth positions are numbered 0..15 from the downbeat: beat 1 = 0, 'e' = 1, '&' = 2, 'a' = 3,
beat 2 = 4, … Odd positions are the ones 16th-note swing delays.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
from scipy.signal import butter, sosfiltfilt

from .grid import GridFit

ENV_RATE_TARGET = 4000.0   # Hz — envelope rate for folding (0.25 ms resolution)
BANDS = ("low", "mid", "high")


@dataclass
class GrooveProfile:
    delta_ms: dict[str, list[float]] = field(default_factory=dict)   # band -> 16 offsets (ms)
    hit: dict[str, list[float]] = field(default_factory=dict)        # band -> 16 strengths (0..1)
    swing_pct: float = 0.5
    swing_confidence: float = 0.0
    kick_rise_ms: float = 0.0
    kick_decay_ms: float = 0.0
    kick_sub_ratio: float = 0.0
    bass_pattern: list[float] = field(default_factory=list)          # 16, sums to 1
    hat_pattern: list[float] = field(default_factory=list)           # 16, sums to 1
    pump_depth_db: float = 0.0
    pump_release_ms: float = 0.0
    bars_used: int = 0
    source: str = ""                                                 # "stems" | "bandsplit"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GrooveProfile:
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})


# ----------------------------------------------------------------------------- envelopes


def _sos(kind: str, sr: int, f1: float, f2: float | None = None):
    if kind == "low":
        return butter(4, f1, btype="low", fs=sr, output="sos")
    if kind == "high":
        return butter(4, f1, btype="high", fs=sr, output="sos")
    return butter(4, [f1, f2], btype="band", fs=sr, output="sos")


def bands_from_mix(y: np.ndarray, sr: int) -> dict[str, np.ndarray]:
    """Zero-phase band splits (sosfiltfilt keeps timing exact)."""
    y = np.asarray(y, dtype=np.float32)
    return {
        "low": sosfiltfilt(_sos("low", sr, 150.0), y).astype(np.float32),
        "mid": sosfiltfilt(_sos("band", sr, 150.0, 5000.0), y).astype(np.float32),
        "high": sosfiltfilt(_sos("high", sr, 5000.0), y).astype(np.float32),
    }


def bands_from_stems(stems: dict[str, np.ndarray], sr: int) -> dict[str, np.ndarray]:
    """low = bass + low(drums); mid = other (+ vocals); high = high(drums)."""
    drums = np.asarray(stems["drums"], dtype=np.float32)
    low = np.asarray(stems["bass"], dtype=np.float32) + sosfiltfilt(_sos("low", sr, 150.0), drums)
    mid = np.asarray(stems["other"], dtype=np.float32) + np.asarray(stems.get("vocals", 0.0), dtype=np.float32)
    high = sosfiltfilt(_sos("high", sr, 5000.0), drums)
    return {"low": low.astype(np.float32), "mid": np.asarray(mid, dtype=np.float32), "high": high.astype(np.float32)}


def envelope(x: np.ndarray, sr: int, smooth_ms: float = 1.0) -> tuple[np.ndarray, float]:
    """Smoothed power envelope decimated to ~ENV_RATE_TARGET. Returns (env, env_rate)."""
    D = max(int(round(sr / ENV_RATE_TARGET)), 1)
    n_sm = max(int(round(sr * smooth_ms / 1000.0)), 1)
    p = np.convolve(np.asarray(x, dtype=np.float64) ** 2, np.ones(n_sm) / n_sm, mode="same")
    return p[::D], sr / D


def attack_signal(env: np.ndarray, env_rate: float, smooth_ms: float = 1.0) -> np.ndarray:
    n_sm = max(int(round(env_rate * smooth_ms / 1000.0)), 1)
    d = np.diff(env, prepend=env[:1])
    return np.convolve(np.maximum(d, 0.0), np.ones(n_sm) / n_sm, mode="same")


def fold(sig: np.ndarray, rate: float, period_s: float, phase_s: float, t_start: float, t_end: float,
         before_s: float = 0.0) -> np.ndarray:
    """Mean of ``sig`` over every cycle ``phase_s + k*period_s`` in [t_start, t_end).

    Returns a profile of length ``round(period_s*rate)`` (+ ``before_s`` lead-in) whose index 0
    corresponds to ``-before_s`` relative to the cycle start.
    """
    L = int(round(period_s * rate))
    B = int(round(before_s * rate))
    k0 = int(np.ceil((t_start + before_s - phase_s) / period_s))
    k1 = int(np.floor((t_end - phase_s) / period_s)) - 1
    if k1 < k0:
        return np.zeros(L + B)
    starts = np.round((phase_s + period_s * np.arange(k0, k1 + 1)) * rate).astype(np.int64) - B
    starts = starts[(starts >= 0) & (starts + L + B <= len(sig))]
    if len(starts) == 0:
        return np.zeros(L + B)
    idx = starts[:, None] + np.arange(L + B)[None, :]
    return sig[idx].mean(axis=0)


# ----------------------------------------------------------------------------- measurements


def _micro_timing(att_bar: np.ndarray, rate: float, p16: float, search_frac: float = 0.4) -> tuple[list[float], list[float]]:
    """Per 16th position: attack peak offset (ms) from nominal and normalised peak strength."""
    deltas, peaks = [], []
    W = int(round(search_frac * p16 * rate))
    L = len(att_bar)
    for p in range(16):
        c = int(round(p * p16 * rate))
        lo, hi = c - W, c + W
        seg = att_bar[np.arange(lo, hi) % L]           # circular within the bar
        j = int(np.argmax(seg))
        # parabolic sub-sample refinement
        if 0 < j < len(seg) - 1:
            ym, y0, yp = seg[j - 1], seg[j], seg[j + 1]
            den = ym - 2 * y0 + yp
            j_ref = j + (0.5 * (ym - yp) / den if den != 0 else 0.0)
        else:
            j_ref = float(j)
        deltas.append(((j_ref - W) / rate) * 1000.0)
        peaks.append(float(seg[j]))
    m = max(peaks) or 1.0
    return deltas, [p_ / m for p_ in peaks]


def _pattern(env_bar: np.ndarray, rate: float, p16: float) -> list[float]:
    """Mean band energy per 16th window [−0.25, +0.75) of a 16th around nominal; sums to 1."""
    L = len(env_bar)
    vals = []
    for p in range(16):
        lo = int(round((p - 0.25) * p16 * rate))
        hi = int(round((p + 0.75) * p16 * rate))
        vals.append(float(env_bar[np.arange(lo, hi) % L].mean()))
    s = sum(vals) or 1.0
    return [v / s for v in vals]


def _kick_transient(low_env_beat: np.ndarray, rate: float, before_s: float) -> tuple[float, float]:
    """Rise 10→90 % and decay peak→10 % (ms) of the folded low-band beat profile."""
    e = low_env_beat - np.percentile(low_env_beat, 5)
    e = np.maximum(e, 0.0)
    pk = int(np.argmax(e))
    top = e[pk] or 1.0
    # rise: walk back from the peak
    i10 = pk
    while i10 > 0 and e[i10] > 0.1 * top:
        i10 -= 1
    i90 = pk
    while i90 > 0 and e[i90] > 0.9 * top:
        i90 -= 1
    rise = (i90 - i10) / rate * 1000.0
    j = pk
    while j < len(e) - 1 and e[j] > 0.1 * top:
        j += 1
    decay = (j - pk) / rate * 1000.0
    return float(max(rise, 0.0)), float(max(decay, 0.0))


def _circular_filter(x: np.ndarray, size: int, kind: str) -> np.ndarray:
    from scipy.ndimage import median_filter, minimum_filter1d

    L = len(x)
    t = np.concatenate([x, x, x])
    y = minimum_filter1d(t, size=size, mode="wrap") if kind == "min" else median_filter(t, size=size, mode="wrap")
    return y[L:2 * L]


def _pump(mid_env_beat: np.ndarray, rate: float, period: float) -> tuple[float, float]:
    """Sidechain depth (dB) and release (ms) from a folded mid-band beat envelope.

    Two robust views of the same periodic profile:
      * a 15 ms circular minimum removes the kick's own click and places the trough exactly;
      * a 120 ms circular median removes hat/perc bursts (<60 ms) without shifting the
        recovery ramp, giving the plateau level and the release time.
    A pump ducks *at* the kick and recovers after it: the trough must sit in the first 40 %
    of the beat, the plateau after it, and a real release is never under 20 ms.
    """
    L = len(mid_env_beat)
    n_min = max(int(round(rate * 0.015)), 1)
    n_med = max(int(round(rate * 0.120)) | 1, 3)
    n_sm = max(int(round(rate * 0.005)), 1)
    lo = _circular_filter(mid_env_beat, n_min, "min")
    lo = np.convolve(np.concatenate([lo[-n_sm:], lo, lo[:n_sm]]), np.ones(n_sm) / n_sm, mode="same")[n_sm:-n_sm]
    med = _circular_filter(mid_env_beat, n_med, "median")
    db_lo, db_med = 10 * np.log10(lo + 1e-12), 10 * np.log10(med + 1e-12)
    trough_i = int(np.argmin(db_lo[: int(0.40 * L)]))
    plateau = float(db_med[trough_i:].max())
    depth = plateau - float(db_lo[trough_i])
    if depth <= 1.0:
        return 0.0, 0.0
    target = db_lo[trough_i] + 0.9 * depth
    j = trough_i
    while j < L - 1 and db_med[j] < target:
        j += 1
    release_ms = (j - trough_i) / rate * 1000.0
    if release_ms < 20.0:
        return 0.0, 0.0
    return depth, float(release_ms)


def _non_downbeat_beat_profile(env: np.ndarray, rate: float, g: GridFit, t_start: float, t_end: float) -> np.ndarray:
    """Fold at the bar, then average beats 2–4 so downbeat-only events (stabs) drop out."""
    period = g.period_s
    down0 = g.beat0_s + g.downbeat_offset * period
    bar_prof = fold(env, rate, 4 * period, down0, t_start, t_end)
    L = int(round(period * rate))
    segs = [bar_prof[i * L:(i + 1) * L] for i in (1, 2, 3)]
    n = min(len(x) for x in segs)
    return np.mean([x[:n] for x in segs], axis=0)


def compute_groove(bands: dict[str, np.ndarray], sr: int, g: GridFit, duration_s: float,
                   source: str = "bandsplit", mid_frac: tuple[float, float] = (0.2, 0.8)) -> GrooveProfile:
    """Groove profile from band signals (see module docstring) and the effective grid."""
    period = g.period_s
    p16 = period / 4.0
    bar = 4 * period
    down0 = g.beat0_s + g.downbeat_offset * period
    t_start, t_end = mid_frac[0] * duration_s, mid_frac[1] * duration_s
    if t_end - t_start < 4 * bar:                        # short material: use everything
        t_start, t_end = 0.0, duration_s

    prof = GrooveProfile(source=source)
    envs: dict[str, tuple[np.ndarray, float]] = {b: envelope(bands[b], sr) for b in BANDS}

    for b in BANDS:
        env, rate = envs[b]
        att = attack_signal(env, rate)
        att_bar = fold(att, rate, bar, down0, t_start, t_end)
        d, h = _micro_timing(att_bar, rate, p16)
        prof.delta_ms[b] = d
        prof.hit[b] = h

    # swing from the high band's odd 16ths that actually carry hits
    hi_hit, hi_d = np.array(prof.hit["high"]), np.array(prof.delta_ms["high"])
    odd = np.arange(1, 16, 2)
    w = hi_hit[odd] * (hi_hit[odd] > 0.3)
    if w.sum() > 0:
        swing_delay_ms = float((w * hi_d[odd]).sum() / w.sum())
        prof.swing_pct = 0.5 + swing_delay_ms / 1000.0 / (period / 2.0)
        prof.swing_confidence = float(min(1.0, w.sum() / 4.0))
    else:
        prof.swing_pct, prof.swing_confidence = 0.5, 0.0

    env_low, rate = envs["low"]
    env_high, _ = envs["high"]
    env_mid, _ = envs["mid"]
    prof.bass_pattern = _pattern(fold(env_low, rate, bar, down0, t_start, t_end), rate, p16)
    prof.hat_pattern = _pattern(fold(env_high, rate, bar, down0, t_start, t_end), rate, p16)

    before = 0.02
    low_beat = fold(env_low, rate, period, g.beat0_s, t_start, t_end, before_s=before)
    prof.kick_rise_ms, prof.kick_decay_ms = _kick_transient(low_beat, rate, before)
    sub = sosfiltfilt(_sos("low", sr, 80.0), bands["low"]).astype(np.float32)
    sub_env, _ = envelope(sub, sr)
    sub_beat = fold(sub_env, rate, period, g.beat0_s, t_start, t_end, before_s=before)
    win = slice(0, int(0.08 * rate) + int(before * rate))
    s_e, l_e = float(sub_beat[win].sum()), float(low_beat[win].sum())
    prof.kick_sub_ratio = s_e / (l_e - s_e) if (l_e - s_e) > 0 else float("inf")

    mid_beat = _non_downbeat_beat_profile(env_mid, rate, g, t_start, t_end)
    prof.pump_depth_db, prof.pump_release_ms = _pump(mid_beat, rate, period)
    prof.bars_used = int((t_end - t_start) / bar)
    return prof


# ----------------------------------------------------------------------------- compatibility (L1)


def groove_compat(a: GrooveProfile, b: GrooveProfile, period_s: float) -> dict[str, float]:
    """Pairwise groove-compatibility features (docs/GROOVE.md §3). All scalar, cheap."""
    hA, hB = np.array(a.hit["high"]), np.array(b.hit["high"])
    dA, dB = np.array(a.delta_ms["high"]), np.array(b.delta_ms["high"])
    flam = float((hA * hB * np.abs(dA - dB)).sum() / (hA * hB).sum()) if (hA * hB).sum() > 0 else 0.0
    swing_ms = abs(a.swing_pct - b.swing_pct) * (period_s / 2.0) * 1000.0
    bassA, bassB = np.array(a.bass_pattern), np.array(b.bass_pattern)
    hatA, hatB = np.array(a.hat_pattern), np.array(b.hat_pattern)
    cos = lambda u, v: float(u @ v / ((np.linalg.norm(u) * np.linalg.norm(v)) or 1.0))  # noqa: E731
    return {
        "flam_risk_ms": flam,
        "swing_mismatch_ms": float(swing_ms),
        "bass_placement_step_ms": float(abs(a.delta_ms["low"][0] - b.delta_ms["low"][0])),
        "pattern_density": float((hatA * hatB).sum() * 16.0),      # 1.0 = uniform overlap
        "pump_mismatch": float(abs(a.pump_depth_db - b.pump_depth_db) + abs(a.pump_release_ms - b.pump_release_ms) / 100.0),
        "bass_pattern_continuity": cos(bassA, bassB),
        "kick_rise_mismatch_ms": float(abs(a.kick_rise_ms - b.kick_rise_ms)),
    }
