"""Constant-tempo beat-grid fitting (directive P0.2).

House is DAW-quantised: one BPM, one phase, for the whole track. That single
assumption is the strongest prior in the system, and this module exploits it:

  1. a beat tracker proposes beat (and maybe downbeat) times;
  2. those times are regressed onto integer beat indices (``t = beat0 + k*period``)
     with RANSAC-lite outlier rejection (drop |residual| > 30 ms, refit, repeat);
  3. BPM is folded into the genre band (half/double disambiguation);
  4. the phase is refined to sub-hop precision by folding a fine onset envelope
     modulo the period, *constrained* to ±reject window around the tracker consensus
     so it can polish but never flip to the off-beat;
  5. the downbeat offset is voted — from tracker downbeats when available, else
     from a per-beat spectral-novelty + low-band accent heuristic.

Conventions:
  * ``beat0_s`` — time of grid beat index 0, the first beat at or after t=0 (0 <= beat0 < period).
  * ``downbeat_offset`` — index (0..3) of the first downbeat. Beat k is a downbeat iff
    ``(k - downbeat_offset) % 4 == 0``.
  * A ``GridFit`` is a pure value object; ``effective()`` applies a human override.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from . import trackers

# ============================================================================ value object


@dataclass
class GridFit:
    bpm: float
    beat0_s: float
    downbeat_offset: int
    confidence: float
    # --- diagnostics (all optional; never consumed by downstream math) ---
    inlier_frac: float = 1.0
    coverage: float = 1.0
    onset_contrast: float = 0.0
    lowband_on_off_ratio: float = 0.0
    residual_rms_ms: float = 0.0
    n_tracker_beats: int = 0
    n_refit_iters: int = 0
    tracker: str = ""
    downbeat_method: str = ""
    downbeat_confidence: float = 0.0
    folded_from_bpm: float | None = None
    flags: list[str] = field(default_factory=list)
    # --- human override (griddoctor writes this; effective() applies it) ---
    override: dict[str, Any] | None = None
    reviewed: bool = False

    @property
    def period_s(self) -> float:
        return 60.0 / self.bpm

    def downbeat_mask(self, n_beats: int) -> np.ndarray:
        k = np.arange(n_beats)
        return (k - self.downbeat_offset) % 4 == 0

    def effective(self) -> GridFit:
        """Return a copy with ``override`` applied (bpm / beat0_s / downbeat_offset / downbeat_shift)."""
        if not self.override:
            return self
        g = GridFit(**{**asdict(self), "override": None})
        o = self.override
        if "bpm" in o and o["bpm"] is not None:
            g.bpm = float(o["bpm"])
        if "beat0_s" in o and o["beat0_s"] is not None:
            g.beat0_s = float(o["beat0_s"]) % g.period_s
        if "downbeat_offset" in o and o["downbeat_offset"] is not None:
            g.downbeat_offset = int(o["downbeat_offset"]) % 4
        if "downbeat_shift" in o and o["downbeat_shift"]:
            g.downbeat_offset = (g.downbeat_offset + int(o["downbeat_shift"])) % 4
        g.override = dict(o)
        return g

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["flags"] = list(self.flags)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GridFit:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def grid_beat_times(g: GridFit, duration_s: float) -> np.ndarray:
    """Exact beat times (float64) for beats in [0, duration)."""
    p = g.period_s
    n = int(np.floor((duration_s - g.beat0_s) / p)) + 1
    n = max(n, 0)
    return g.beat0_s + p * np.arange(n, dtype=np.float64)


def beat_index_at(g: GridFit, t_s: float) -> float:
    """Fractional beat index at time t (can be negative before beat0)."""
    return (t_s - g.beat0_s) / g.period_s


def fold_bpm_into_band(bpm: float, lo: float, hi: float) -> float:
    """Double/halve ``bpm`` until it lies in [lo, hi]. Unchanged if impossible."""
    b = float(bpm)
    for _ in range(4):
        if lo <= b <= hi:
            return b
        b = b * 2 if b < lo else b / 2
    return float(bpm) if not (lo <= b <= hi) else b


# ============================================================================ RANSAC-lite


@dataclass
class _LinFit:
    period: float
    intercept: float
    inlier: np.ndarray
    residual: np.ndarray
    iters: int


def ransac_linear_fit(beats_s: np.ndarray, period0: float, reject_s: float, max_iters: int) -> _LinFit:
    """Regress beat times onto integer indices with iterative outlier rejection.

    Index assignment is recomputed every iteration from the current fit, so a
    tracker that skipped or doubled a beat is handled naturally.
    """
    t = np.asarray(beats_s, dtype=np.float64)
    if t.size < 4:
        raise ValueError("need at least 4 tracker beats to fit a grid")
    # Initial index assignment is *incremental*: consecutive tracker differences are
    # accurate to ±hop, whereas a rough global period accumulates drift over hundreds
    # of beats and scrambles indices mid-track. A skipped beat becomes a jump of 2.
    k = np.concatenate([[0.0], np.cumsum(np.maximum(np.round(np.diff(t) / period0), 1.0))])
    period, intercept = period0, t[0]
    inlier = np.ones_like(t, dtype=bool)
    iters = 0
    for iters in range(1, max_iters + 1):
        if iters > 1:
            k = np.round((t - intercept) / period)
        A = np.stack([np.ones_like(k), k], axis=1)
        coef, *_ = np.linalg.lstsq(A[inlier], t[inlier], rcond=None)
        intercept, period = float(coef[0]), float(coef[1])
        residual = t - (intercept + period * k)
        new_inlier = np.abs(residual) <= reject_s
        if new_inlier.sum() < 4:
            break
        if np.array_equal(new_inlier, inlier):
            inlier = new_inlier
            break
        inlier = new_inlier
    k = np.round((t - intercept) / period)
    residual = t - (intercept + period * k)
    return _LinFit(period=period, intercept=intercept, inlier=inlier, residual=residual, iters=iters)


# ============================================================================ phase refinement (time domain)


def _fold_energy(y: np.ndarray, sr: int, period: float, beat0: float, window_s: float) -> np.ndarray:
    """Sum y² over ±window around every grid beat → folded energy profile at sample resolution.

    Index 0 of the result corresponds to ``-window_s`` relative to the grid beat.
    """
    W = int(round(window_s * sr))
    n = len(y)
    first_k = int(np.ceil((window_s - beat0) / period))
    last_k = int(np.floor(((n - 1) / sr - window_s - beat0) / period))
    if last_k < first_k:
        return np.zeros(2 * W, dtype=np.float64)
    centers = np.round((beat0 + period * np.arange(first_k, last_k + 1)) * sr).astype(np.int64)
    idx = centers[:, None] + np.arange(-W, W)[None, :]
    seg = y[idx].astype(np.float64)
    return (seg * seg).sum(axis=0)


def _smooth(x: np.ndarray, n: int) -> np.ndarray:
    n = max(int(n), 1)
    return np.convolve(x, np.ones(n) / n, mode="same")


def _attack_strength(profile: np.ndarray, sr: int) -> np.ndarray:
    """Positive slope of the 1 ms-smoothed energy profile — an 'attack detector'."""
    env = _smooth(profile, sr // 1000)
    d = np.diff(env, prepend=env[:1])
    return _smooth(np.maximum(d, 0.0), sr // 1000)


def lowband_phase_check(y: np.ndarray, sr: int, period: float, beat0: float, window_s: float = 0.025,
                        flip_ratio: float = 1.5) -> tuple[float, float, bool]:
    """Genre prior: four-on-the-floor means the kick *is* the beat.

    Compare low-band (<150 Hz) attack energy at grid beats vs at anti-beats. If the
    anti-beat wins decisively (``flip_ratio``), the tracker locked onto the off-beat
    (hats/bass bounce) and the phase is flipped by half a period.

    Returns (beat0, on_off_ratio, flipped).
    """
    from scipy.signal import butter, sosfiltfilt

    sos = butter(4, 150.0, btype="low", fs=sr, output="sos")
    y_low = sosfiltfilt(sos, y).astype(np.float32)
    on = _attack_strength(_fold_energy(y_low, sr, period, beat0, window_s), sr).max()
    off = _attack_strength(_fold_energy(y_low, sr, period, beat0 + period / 2, window_s), sr).max()
    ratio = float(on / off) if off > 0 else float("inf")
    if off > flip_ratio * on:
        return (beat0 + period / 2) % period, ratio, True
    return beat0, ratio, False


def refine_phase(y: np.ndarray, sr: int, period: float, beat0: float, window_s: float) -> tuple[float, float]:
    """Sub-hop phase refinement: fold the signal's energy at sample resolution around the
    consensus beat and place the beat at the steepest energy rise (the attack).

    Confined to ±window of the tracker consensus so it polishes but cannot jump beats.
    Returns (refined_beat0, onset_contrast) where onset_contrast = on-beat / anti-beat
    folded energy (diagnostic).
    """
    prof_on = _fold_energy(y, sr, period, beat0, window_s)
    if not prof_on.any():
        return beat0, 0.0
    att = _attack_strength(prof_on, sr)
    W = len(prof_on) // 2
    tau = (int(np.argmax(att)) - W) / sr
    refined = beat0 + tau
    prof_off = _fold_energy(y, sr, period, beat0 + period / 2, window_s)
    core = slice(W - sr // 100, W + sr // 100)  # ±10 ms
    on_e, off_e = prof_on[core].sum(), prof_off[core].sum()
    contrast = float(on_e / off_e) if off_e > 0 else float("inf")
    return float(refined), contrast


# ============================================================================ downbeat vote


def _vote_from_tracker_downbeats(downbeats_s: np.ndarray, g: GridFit) -> tuple[int, float]:
    j = np.round(beat_index_at(g, downbeats_s)).astype(int)
    counts = np.bincount(j % 4, minlength=4).astype(float)
    if counts.sum() == 0:
        return 0, 0.0
    off = int(np.argmax(counts))
    return off, float(counts[off] / counts.sum())


def _vote_from_novelty(y: np.ndarray, sr: int, g: GridFit) -> tuple[int, float]:
    """Heuristic downbeat vote when the tracker has none.

    Two per-beat cues, z-scored and summed, then averaged per phase class (k mod 4):

    * ``accent`` — full-band onset strength of the hit *at* the beat (downbeats hit
      harder: louder kick, stab, crash).
    * ``flux`` — half-wave-rectified beat-level spectral flux in *magnitude* units:
      new energy arriving at beat k. Rectified so the beat after a downbeat (when the
      accent leaves) does not tie; magnitude-domain so a loud arrival outweighs a
      quiet one, which dB flux cannot express.

    Bars in house begin with the change, so the downbeat class wins on average.
    Confidence = margin between the best and second-best class, normalised.
    """
    import librosa

    hop = 512
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=2048, hop_length=hop, n_mels=64, power=1.0)
    oenv = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S + 1e-10), sr=sr, hop_length=hop)
    n_frames = S.shape[1]
    frame_t = librosa.frames_to_time(np.arange(n_frames), sr=sr, hop_length=hop)
    beats = grid_beat_times(g, duration_s=frame_t[-1] + hop / sr)
    if len(beats) < 8:
        return 0, 0.0
    edges = np.clip(np.searchsorted(frame_t, beats), 0, n_frames - 1)
    # segment-mean magnitude per band, and accent = onset strength in [-1, +3] frames of the beat
    feats, accent = [], []
    for a, b in zip(edges[:-1], edges[1:], strict=True):
        feats.append(S[:, a:b].mean(axis=1) if b > a else S[:, a])
        lo, hi = max(a - 1, 0), min(a + 4, n_frames)
        accent.append(oenv[lo:hi].sum())
    F = np.stack(feats)                                              # [n_beats-1, 64]
    accent = np.asarray(accent)
    flux = np.r_[0.0, np.maximum(np.diff(F, axis=0), 0.0).sum(axis=1)]

    def z(x: np.ndarray) -> np.ndarray:
        return (x - x.mean()) / (x.std() + 1e-9)

    score = z(accent) + z(flux)
    k = np.arange(len(score))
    cls = np.array([score[k % 4 == p].mean() for p in range(4)])
    off = int(np.argmax(cls))
    srt = np.sort(cls)[::-1]
    conf = float(np.clip((srt[0] - srt[1]) / (np.abs(cls).max() + 1e-9), 0.0, 1.0))
    return off, conf


# ============================================================================ main entry


def fit_grid(
    y: np.ndarray,
    sr: int,
    tracker: str = "auto",
    bpm_min: float = 116.0,
    bpm_max: float = 130.0,
    reject_ms: float = 30.0,
    max_refit_iters: int = 6,
    confidence_flag_threshold: float = 0.9,
) -> GridFit:
    """Fit a constant-tempo grid to mono audio ``y``.

    ``y`` must be mono float; callers downmix first. Deterministic for fixed inputs.
    """
    y = np.asarray(y, dtype=np.float32)
    if y.ndim != 1:
        raise ValueError("fit_grid expects mono audio; downmix first")
    duration = len(y) / sr
    reject_s = reject_ms / 1000.0
    flags: list[str] = []

    est = trackers.track(y, sr, backend=tracker, start_bpm=0.5 * (bpm_min + bpm_max))
    beats = np.sort(est.beats_s)
    if beats.size < 8:
        flags.append("too_few_tracker_beats")
        bpm = est.tempo_hint or 0.5 * (bpm_min + bpm_max)
        return GridFit(bpm=fold_bpm_into_band(bpm, bpm_min, bpm_max), beat0_s=0.0, downbeat_offset=0,
                       confidence=0.0, n_tracker_beats=int(beats.size), tracker=est.backend, flags=flags)

    # --- 1. initial period from median inter-beat interval, folded into band
    period0 = float(np.median(np.diff(beats)))
    bpm0 = 60.0 / period0
    bpm0_folded = fold_bpm_into_band(bpm0, bpm_min, bpm_max)
    folded_from = None
    if abs(bpm0_folded - bpm0) > 1e-6:
        folded_from = bpm0
        period0 = 60.0 / bpm0_folded
        flags.append("tempo_folded")

    # --- 2. RANSAC-lite linear fit on tracker beats
    lf = ransac_linear_fit(beats, period0, reject_s, max_refit_iters)
    period, intercept = lf.period, lf.intercept
    bpm = 60.0 / period
    if not (bpm_min <= bpm <= bpm_max):
        flags.append("bpm_out_of_band")

    inlier_frac = float(lf.inlier.mean())
    residual_rms_ms = float(np.sqrt(np.mean(lf.residual[lf.inlier] ** 2)) * 1000) if lf.inlier.any() else float("nan")

    # coverage: grid beats inside tracker span that have a tracker beat within reject
    span_lo, span_hi = beats[0] - reject_s, beats[-1] + reject_s
    k_lo = int(np.ceil((span_lo - intercept) / period))
    k_hi = int(np.floor((span_hi - intercept) / period))
    grid_in_span = intercept + period * np.arange(k_lo, k_hi + 1)
    if grid_in_span.size:
        nearest = np.abs(grid_in_span[:, None] - beats[None, :]).min(axis=1)
        coverage = float((nearest <= reject_s).mean())
    else:
        coverage = 0.0

    # --- 3. normalise beat0 into [0, period)
    beat0 = intercept % period

    # --- 4a. genre prior: the kick is the beat. Flip half a period if the tracker locked
    #         onto the off-beat (hats / bass bounce). Flagged so griddoctor surfaces it.
    beat0, lowband_ratio, flipped = lowband_phase_check(y, sr, period, beat0)
    if flipped:
        flags.append("phase_flipped_lowband")

    # --- 4b. sub-hop phase refinement (time-domain attack), confined to ±reject window
    beat0_ref, contrast = refine_phase(y, sr, period, beat0, window_s=reject_s)
    beat0 = beat0_ref % period

    g = GridFit(
        bpm=bpm, beat0_s=beat0, downbeat_offset=0, confidence=0.0,
        inlier_frac=inlier_frac, coverage=coverage, onset_contrast=contrast,
        lowband_on_off_ratio=lowband_ratio,
        residual_rms_ms=residual_rms_ms, n_tracker_beats=int(beats.size), n_refit_iters=lf.iters,
        tracker=est.backend, folded_from_bpm=folded_from, flags=flags,
    )

    # --- 5. downbeat vote
    if est.downbeats_s is not None and len(est.downbeats_s) >= 2:
        off, dconf = _vote_from_tracker_downbeats(np.asarray(est.downbeats_s), g)
        g.downbeat_method = f"tracker:{est.backend}"
    else:
        off, dconf = _vote_from_novelty(y, sr, g)
        g.downbeat_method = "novelty_vote"
    g.downbeat_offset, g.downbeat_confidence = off, dconf
    if dconf < 0.5:
        flags.append("downbeat_uncertain")

    # --- 6. confidence
    conf = inlier_frac * coverage
    if "bpm_out_of_band" in flags:
        conf *= 0.5
    if duration < 20.0:
        flags.append("short_audio")
    g.confidence = float(np.clip(conf, 0.0, 1.0))
    if g.confidence < confidence_flag_threshold:
        flags.append("needs_griddoctor")
    g.flags = flags
    return g
