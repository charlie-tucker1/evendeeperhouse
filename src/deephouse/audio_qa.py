"""Ingest QA (docs/SOURCING.md §4): measure a file's *effective bandwidth* and compare it to what
its container claims, so a transcode ("fake 320", MP3-sourced "lossless") is flagged at the door
and the critic can never learn bitrate instead of quality.

Method: long-term power spectrum (Welch over ~60 s from the middle of the track) → the highest
frequency whose level is still within ``drop_db`` of the 1–5 kHz plateau. Reference lowpass
table (LAME `optimum_bandwidth`, verified): 128 → 17.0 kHz, 160 → 17.5, 192 → 18.6, 224 → 19.4,
256 → 19.7, 320 → 20.5 kHz; V0 → 19.5. AAC-LC ≈ 16 kHz @128, ~19–20 kHz @256. Opus is a 20 kHz
band-pass at *every* bitrate, so a 20 kHz shelf on Opus is normal, not a transcode.

Cutoff is neither necessary nor sufficient (arXiv 2407.21545): quiet or dark masters can read
"lossy", and a transcoder can leave noise above the cutoff. So this is a *flag*, stored with the
measurement, for a human to confirm — never an automatic reject.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

LAME_CUTOFF_HZ = {128: 17000, 160: 17500, 192: 18600, 224: 19400, 256: 19700, 320: 20500}


@dataclass
class BandwidthQA:
    bandwidth_hz: float       # highest f within drop_db of the 1–5 kHz plateau (a measurement)
    cliff_hz: float           # where the steepest 1 kHz drop sits in 13–21.5 kHz
    cliff_db: float           # size of that drop; encoders' lowpass filters leave ≥18 dB cliffs
    plateau_db: float
    noise_floor_db: float
    codec: str | None
    declared_kbps: int | None
    expected_min_hz: float | None
    flag: str                 # ok | transcode_suspect | dark_master | opus_normal | unknown
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _spectrum_db(y: np.ndarray, sr: int, seconds: float = 60.0, n_fft: int = 8192) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y, dtype=np.float32)
    if y.ndim == 2:
        y = y.mean(axis=1)
    n = len(y)
    L = int(min(seconds * sr, n))
    s = max((n - L) // 2, 0)
    seg = y[s:s + L]
    if len(seg) < n_fft:
        seg = np.pad(seg, (0, n_fft - len(seg)))
    hop = n_fft // 2
    win = np.hanning(n_fft).astype(np.float32)
    nfr = 1 + (len(seg) - n_fft) // hop
    frames = np.lib.stride_tricks.as_strided(seg, shape=(nfr, n_fft), strides=(seg.strides[0] * hop, seg.strides[0]))
    spec = (np.abs(np.fft.rfft(frames * win, axis=1)) ** 2).mean(axis=0)
    f = np.fft.rfftfreq(n_fft, 1 / sr)
    db = 10 * np.log10(spec + 1e-20)
    k = max(int(round(200 / (sr / n_fft))), 1)              # ~200 Hz smoothing
    return f, np.convolve(db, np.ones(k) / k, mode="same")


def effective_bandwidth(y: np.ndarray, sr: int, drop_db: float = 25.0, seconds: float = 60.0,
                        n_fft: int = 8192) -> tuple[float, float, float]:
    """Return (bandwidth_hz, plateau_db, floor_db): the highest frequency still within ``drop_db``
    of the 1–5 kHz plateau of the long-term spectrum (Welch over the track's middle)."""
    f, db_s = _spectrum_db(y, sr, seconds, n_fft)
    plateau = float(np.median(db_s[(f >= 1000) & (f <= 5000)]))
    floor = float(np.percentile(db_s[f >= 0.9 * f[-1]], 10))
    above = np.where((db_s >= plateau - drop_db) & (f >= 1000))[0]
    return (float(f[above[-1]]) if len(above) else 0.0), plateau, floor


def cliff(y: np.ndarray, sr: int, lo: float = 13000.0, hi: float = 21500.0, width_hz: float = 1000.0) -> tuple[float, float]:
    """Steepest drop over ``width_hz`` in [lo, hi]: returns (cliff_hz, cliff_db). Encoder lowpass
    filters are brick walls (≥18 dB within 1 kHz); mastered music rolls off gradually (<10 dB/kHz)."""
    f, db_s = _spectrum_db(y, sr)
    step = int(round(width_hz / (f[1] - f[0])))
    idx = np.where((f >= lo) & (f <= hi - width_hz))[0]
    if len(idx) == 0:
        return 0.0, 0.0
    drops = db_s[idx] - db_s[idx + step]
    j = int(np.argmax(drops))
    return float(f[idx[j]]), float(drops[j])


def assess(y: np.ndarray, sr: int, codec: str | None, declared_kbps: int | None, cliff_threshold_db: float = 18.0) -> BandwidthQA:
    bw, plateau, floor = effective_bandwidth(y, sr)
    c_hz, c_db = cliff(y, sr)
    has_cliff = c_db >= cliff_threshold_db
    codec_l = (codec or "").lower()
    expected: float | None = None
    flag, note = "unknown", ""
    lossless = codec_l in ("flac", "pcm_s16le", "pcm_s24le", "pcm_f32le", "alac", "wav", "aiff", "pcm_s16be")
    if lossless:
        expected = 20000.0
        if has_cliff and c_hz < 20500:
            flag, note = "transcode_suspect", f"lossless container but a {c_db:.0f} dB cliff at {c_hz / 1000:.1f} kHz — lossy source"
        elif bw < 17000:
            flag, note = "dark_master", f"no encoder cliff; bandwidth {bw / 1000:.1f} kHz is a gradual rolloff"
        else:
            flag = "ok"
    elif codec_l == "opus":
        expected = 19500.0
        flag, note = "opus_normal", "Opus band-passes at 20 kHz at every bitrate"
        if has_cliff and c_hz < 18500:
            flag, note = "transcode_suspect", f"{c_db:.0f} dB cliff at {c_hz / 1000:.1f} kHz below Opus's own 20 kHz band edge"
    elif codec_l in ("mp3", "aac", "vorbis", "mp4a"):
        if declared_kbps:
            table = LAME_CUTOFF_HZ if codec_l == "mp3" else {128: 16000, 160: 17000, 192: 18000, 256: 19000, 320: 20000}
            nearest = min(sorted(table), key=lambda k_: abs(k_ - declared_kbps))
            expected = float(table[nearest]) - 800.0
            if has_cliff and c_hz < expected:
                flag, note = "transcode_suspect", f"declared {declared_kbps} kbps but a {c_db:.0f} dB cliff at {c_hz / 1000:.1f} kHz (expected ≥{expected / 1000:.1f} kHz) — re-encoded from a lower bitrate"
            elif bw < 17000 and not has_cliff:
                flag, note = "dark_master", f"no encoder cliff below {expected / 1000:.1f} kHz; bandwidth {bw / 1000:.1f} kHz is a gradual rolloff"
            else:
                flag = "ok"
        else:
            flag = "ok" if not (has_cliff and c_hz < 16500) else "transcode_suspect"
    return BandwidthQA(bandwidth_hz=bw, cliff_hz=c_hz, cliff_db=c_db, plateau_db=plateau, noise_floor_db=floor, codec=codec,
                       declared_kbps=declared_kbps, expected_min_hz=expected, flag=flag, note=note)
