"""Synthetic audio generators with *known* ground truth.

Used by the test-suite (grid-fit accuracy), by `deephouse selftest`, and later
by renderer null-tests. Everything here is deterministic given ``seed``.

Conventions (shared with analysis.grid):
  * ``beat0_s``  — time of grid beat index 0, i.e. the first beat at or after t=0.
  * ``downbeat_offset`` — index (0..3) of the first downbeat in the grid.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SynthTruth:
    bpm: float
    beat0_s: float
    downbeat_offset: int
    sr: int
    duration_s: float

    @property
    def period_s(self) -> float:
        return 60.0 / self.bpm


def _decaying_sine(sr: int, freq_hz: float, dur_s: float, decay_s: float) -> np.ndarray:
    n = int(round(dur_s * sr))
    t = np.arange(n) / sr
    return np.sin(2 * np.pi * freq_hz * t) * np.exp(-t / decay_s)


def _kick(sr: int) -> np.ndarray:
    """A synthetic 909-ish kick: pitch sweep 150->45 Hz, ~250 ms."""
    dur = 0.25
    n = int(dur * sr)
    t = np.arange(n) / sr
    f = 45 + 105 * np.exp(-t / 0.035)
    phase = 2 * np.pi * np.cumsum(f) / sr
    env = np.exp(-t / 0.09)
    click = np.exp(-t / 0.002) * 0.5
    return (np.sin(phase) * env + click).astype(np.float32)


def _hat(sr: int, rng: np.random.Generator) -> np.ndarray:
    dur = 0.06
    n = int(dur * sr)
    t = np.arange(n) / sr
    noise = rng.standard_normal(n)
    # crude high-pass: first difference
    noise = np.diff(noise, prepend=0.0)
    return (noise * np.exp(-t / 0.012) * 0.25).astype(np.float32)


def _place(buf: np.ndarray, sample: np.ndarray, at: int, gain: float = 1.0) -> None:
    if at < 0 or at >= len(buf):
        return
    end = min(len(buf), at + len(sample))
    buf[at:end] += gain * sample[: end - at]


def make_click_track(
    bpm: float = 124.0,
    beat0_s: float = 0.25,
    downbeat_offset: int = 0,
    duration_s: float = 60.0,
    sr: int = 44100,
    snr_db: float = 30.0,
    style: str = "house",
    seed: int = 0,
    stereo: bool = True,
) -> tuple[np.ndarray, SynthTruth]:
    """Return ``(audio, truth)``.

    ``style='clicks'``: pure clicks (1 kHz), accented (1.5 kHz, louder) on downbeats.
    ``style='house'``: kick on every beat, off-beat hats, a sustained bass note,
    louder kick + a chord stab on downbeats, plus a small random per-hit gain
    variation so the material is not perfectly periodic.
    """
    if not 0 <= downbeat_offset <= 3:
        raise ValueError("downbeat_offset must be in 0..3")
    if not 0 <= beat0_s < 60.0 / bpm:
        raise ValueError("beat0_s must satisfy 0 <= beat0_s < period")

    rng = np.random.default_rng(seed)
    n = int(round(duration_s * sr))
    y = np.zeros(n, dtype=np.float64)
    period = 60.0 / bpm

    if style == "clicks":
        click = _decaying_sine(sr, 1000.0, 0.03, 0.006)
        accent = _decaying_sine(sr, 1500.0, 0.04, 0.008)
    else:
        kick = _kick(sr)
        hat = _hat(sr, rng)
        stab = sum(
            _decaying_sine(sr, f, 0.5, 0.15) for f in (220.0, 261.63, 329.63)
        ) / 3.0
        bass_t = np.arange(n) / sr
        y += 0.15 * np.sin(2 * np.pi * 55.0 * bass_t)  # sustained A1

    k = 0
    while True:
        t_beat = beat0_s + k * period
        at = int(round(t_beat * sr))
        if at >= n:
            break
        is_down = (k - downbeat_offset) % 4 == 0
        if style == "clicks":
            _place(y, accent if is_down else click, at, 1.0 if is_down else 0.6)
        else:
            g = 1.0 + 0.05 * rng.standard_normal()
            _place(y, kick, at, (1.0 if is_down else 0.8) * g)
            if is_down:
                _place(y, stab, at, 0.35)
            # off-beat hat
            _place(y, hat, int(round((t_beat + period / 2) * sr)), 0.8 + 0.1 * rng.standard_normal())
        k += 1

    # normalise then add white noise at the requested SNR
    peak = np.max(np.abs(y)) or 1.0
    y = 0.8 * y / peak
    sig_pow = np.mean(y**2)
    noise_pow = sig_pow / (10 ** (snr_db / 10))
    y += rng.standard_normal(n) * np.sqrt(noise_pow)
    y = np.clip(y, -1.0, 1.0).astype(np.float32)

    if stereo:
        y = np.stack([y, y], axis=1)
    truth = SynthTruth(
        bpm=bpm, beat0_s=beat0_s, downbeat_offset=downbeat_offset, sr=sr, duration_s=duration_s
    )
    return y, truth
