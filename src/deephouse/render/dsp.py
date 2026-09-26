"""DSP primitives for the renderer: automation curves, band split, block-wise filter sweeps,
time-stretch backends, loudness. All float32/float64 numpy; nothing here has hidden state.
"""

from __future__ import annotations

import importlib.util

import numpy as np
from scipy.signal import butter, sosfilt

DB_FLOOR = -120.0


# ============================================================================ automation


def db_to_lin(db: np.ndarray | float) -> np.ndarray | float:
    return np.where(np.asarray(db) <= DB_FLOOR, 0.0, 10.0 ** (np.asarray(db) / 20.0))


def gain_from_breakpoints(breakpoints: list[tuple[int, float]], n: int) -> np.ndarray:
    """Per-sample linear gain from ``(sample, dB)`` breakpoints, linear-in-dB between them,
    held flat before the first and after the last. ``-inf``/``<= DB_FLOOR`` means silence."""
    if not breakpoints:
        return np.ones(n, dtype=np.float32)
    bp = sorted(breakpoints)
    xs = np.array([max(min(s, n), 0) for s, _ in bp], dtype=np.float64)
    ys = np.array([max(float(d), DB_FLOOR) if np.isfinite(d) else DB_FLOOR for _, d in bp], dtype=np.float64)
    t = np.arange(n, dtype=np.float64)
    db = np.interp(t, xs, ys, left=ys[0], right=ys[-1])
    return db_to_lin(db).astype(np.float32)


def equal_power_pair(n: int) -> tuple[np.ndarray, np.ndarray]:
    """(fade_out, fade_in) over ``n`` samples with cos/sin law: power sums to 1 throughout."""
    theta = np.linspace(0.0, np.pi / 2, n, endpoint=False, dtype=np.float64)
    return np.cos(theta).astype(np.float32), np.sin(theta).astype(np.float32)


def stepped_entry_pair(n: int, step_db: float = -9.0) -> tuple[np.ndarray, np.ndarray]:
    """A holds unity for the first half while B sits at ``step_db``; then equal-power over the
    second half from (unity, step) to (0, unity)."""
    h = n // 2
    a = np.ones(n, dtype=np.float32)
    b = np.full(n, float(db_to_lin(step_db)), dtype=np.float32)
    fo, fi = equal_power_pair(n - h)
    a[h:] = fo
    b[h:] = b[h:] + (1.0 - b[h:]) * fi          # from step level up to unity along the sin law
    return a, b


def ramp(n_total: int, start: int, length: int, from_v: float, to_v: float) -> np.ndarray:
    """Gain array: ``from_v`` before ``start``, linear ramp over ``length`` samples, ``to_v`` after."""
    g = np.full(n_total, from_v, dtype=np.float32)
    s, e = max(start, 0), min(start + max(length, 1), n_total)
    if e > s:
        g[s:e] = np.linspace(from_v, to_v, e - s, dtype=np.float32)
    if e < n_total:
        g[e:] = to_v
    return g


# ============================================================================ filters


def lr4_split(y: np.ndarray, sr: int, fc: float = 120.0) -> tuple[np.ndarray, np.ndarray]:
    """Linkwitz–Riley 4th order: two cascaded 2nd-order Butterworths per side. low + high is
    all-pass flat. Works on ``[n]`` or ``[n, ch]``."""
    lo = butter(2, fc, btype="low", fs=sr, output="sos")
    hi = butter(2, fc, btype="high", fs=sr, output="sos")
    low = sosfilt(lo, sosfilt(lo, y, axis=0), axis=0)
    high = sosfilt(hi, sosfilt(hi, y, axis=0), axis=0)
    return low.astype(np.float32), high.astype(np.float32)


def sweep_filter(y: np.ndarray, sr: int, cutoffs_hz: np.ndarray, block_len: int, kind: str = "hpf",
                 order: int = 2, xfade_s: float = 0.010, warm_s: float = 0.050) -> np.ndarray:
    """Time-varying HPF/LPF (directive P1.3): ``cutoffs_hz[i]`` applies to block ``i`` of
    ``block_len`` samples. Each block is filtered from a warm-up lead-in (state settles, then
    discarded) and adjacent block outputs are *linearly* cross-faded over ``xfade_s`` so
    coefficient changes never click (linear, not equal-power: the two block outputs are the
    same audio through nearly the same filter, i.e. highly correlated, and an equal-power law
    would bump +3 dB mid-fade). A cutoff <= 20 Hz for an HPF (or >= Nyquist for an LPF) passes
    the block through untouched, bit-exactly when its neighbours are bypassed too."""
    y = np.asarray(y, dtype=np.float32)
    n = len(y)
    out = np.zeros_like(y)
    xf = int(round(xfade_s * sr))
    warm = int(round(warm_s * sr))
    n_blocks = int(np.ceil(n / block_len))
    fi = np.linspace(0.0, 1.0, max(xf, 1), endpoint=False, dtype=np.float32)
    fo = (1.0 - fi).astype(np.float32)
    shape = (-1, 1) if y.ndim == 2 else (-1,)
    prev_tail = None
    prev_bypass = True
    for i in range(n_blocks):
        s, e = i * block_len, min((i + 1) * block_len, n)
        fc = float(cutoffs_hz[min(i, len(cutoffs_hz) - 1)])
        seg_s, seg_e = max(s - warm, 0), min(e + xf, n)
        seg = y[seg_s:seg_e]
        bypass = (kind == "hpf" and fc <= 20.0) or (kind == "lpf" and fc >= 0.45 * sr)
        if bypass:
            filt = seg
        else:
            sos = butter(order, fc, btype="high" if kind == "hpf" else "low", fs=sr, output="sos")
            filt = sosfilt(sos, seg, axis=0).astype(np.float32)
        body = filt[s - seg_s:e - seg_s]
        if prev_tail is not None and xf > 0 and not (bypass and prev_bypass):
            k = min(len(prev_tail), len(body), xf)
            body = body.copy()
            body[:k] = prev_tail[:k] * fo[:k].reshape(shape)[:k] + body[:k] * fi[:k].reshape(shape)[:k]
        out[s:e] = body
        prev_tail = filt[e - seg_s:seg_e - seg_s] if seg_e > e else None
        prev_bypass = bypass
    return out


# ============================================================================ time-stretch


def stretch_backends() -> list[str]:
    out = []
    if importlib.util.find_spec("pyrubberband") is not None:
        out.append("rubberband")
    out.append("resample")
    return out


def time_stretch(y: np.ndarray, sr: int, rate: float, backend: str = "auto") -> np.ndarray:
    """Play ``y`` at speed ``rate`` (>1 faster/shorter). Output length ≈ len/rate.

    ``rubberband``: R3 engine, pitch preserved (the box). ``resample``: varispeed via soxr —
    pitch shifts by ``rate`` (±6 % ≈ ±1 semitone, what a vinyl pitch fader does); exact length,
    zero artefacts, deterministic. Used here and as the fallback.
    """
    if backend == "auto":
        backend = stretch_backends()[0]
    if abs(rate - 1.0) < 1e-9:
        return np.asarray(y, dtype=np.float32)
    if backend == "rubberband":
        import pyrubberband as pyrb

        return pyrb.time_stretch(np.asarray(y, dtype=np.float32), sr, rate, rbargs={"-3": "", "--transients": "crisp"}).astype(np.float32)
    if backend == "resample":
        import soxr

        # pretend the input runs at sr*rate and convert to sr: length scales by 1/rate
        return soxr.resample(np.asarray(y, dtype=np.float32), sr * rate, sr, quality="VHQ").astype(np.float32)
    raise ValueError(f"unknown stretch backend {backend!r}")


# ============================================================================ loudness


def integrated_lufs(y: np.ndarray, sr: int) -> float:
    import pyloudnorm as pyln

    y = np.asarray(y, dtype=np.float32)
    if len(y) < int(0.4 * sr) + 1:
        return float("-inf")
    meter = pyln.Meter(sr)
    v = meter.integrated_loudness(y if y.ndim == 2 else y[:, None])
    return float(v)


def short_term_lufs_track(y: np.ndarray, sr: int, hop_s: float = 0.5, win_s: float = 3.0) -> np.ndarray:
    """Short-term loudness trajectory (3 s windows, ``hop_s`` step). Used by L2 later."""
    n, w, h = len(y), int(win_s * sr), int(hop_s * sr)
    return np.array([integrated_lufs(y[s:s + w], sr) for s in range(0, max(n - w, 1), h)])


def true_peak_db(y: np.ndarray, sr: int) -> float:
    import soxr

    up = soxr.resample(np.asarray(y, dtype=np.float32), sr, sr * 4, quality="HQ")
    return float(20 * np.log10(np.max(np.abs(up)) + 1e-12))


def limiter(y: np.ndarray, sr: int, ceiling_db: float = -1.0, lookahead_s: float = 0.002, release_s: float = 0.050) -> np.ndarray:
    """Look-ahead peak limiter on the sample peak (true-peak headroom handled by the caller
    through ``ceiling_db``): gain = min(1, ceiling/peak_env) with instant attack via
    look-ahead max and exponential release."""
    y = np.asarray(y, dtype=np.float32)
    ceiling = 10 ** (ceiling_db / 20)
    peak = np.abs(y).max(axis=1) if y.ndim == 2 else np.abs(y)
    la = max(int(lookahead_s * sr), 1)
    # look-ahead: running max over the next ``la`` samples
    from scipy.ndimage import maximum_filter1d

    peak_la = maximum_filter1d(peak, size=la, origin=-(la // 2), mode="nearest")
    target = np.minimum(1.0, ceiling / np.maximum(peak_la, 1e-9))
    # exponential release toward 1.0, instant attack downward
    out = np.empty_like(target)
    g = 1.0
    a = float(np.exp(-1.0 / (release_s * sr)))
    for i in range(len(target)):
        t = target[i]
        g = t if t < g else a * g + (1 - a) * t
        out[i] = g
    gain = out.astype(np.float32)
    return (y * (gain[:, None] if y.ndim == 2 else gain)).astype(np.float32)
