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
    swing: float = 0.5
    pump_depth_db: float = 0.0
    pump_release_s: float = 0.25
    hats: str = "offbeat8"
    bass: str = "sustain"

    @property
    def swing_delay_s(self) -> float:
        return (self.swing - 0.5) * (60.0 / self.bpm) / 2.0

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
    swing: float = 0.5,
    pump_depth_db: float = 0.0,
    pump_release_s: float = 0.25,
    hats: str = "offbeat8",
    bass: str = "sustain",
    arrangement: list[tuple[int, set[str]]] | None = None,
) -> tuple[np.ndarray, SynthTruth]:
    """Return ``(audio, truth)``.

    ``style='clicks'``: pure clicks (1 kHz), accented (1.5 kHz, louder) on downbeats.
    ``style='house'``: kick on every beat, hats, bass, a sustained pad, louder kick +
    a chord stab on downbeats, plus a small random per-hit gain variation so the
    material is not perfectly periodic. Groove controls (house only):

    * ``swing`` — 16th-note swing as a fraction of the eighth: 0.5 straight, 0.58 rolling,
      0.667 triplet. Odd 16ths are delayed by ``(swing - 0.5) * eighth``.
    * ``pump_depth_db`` / ``pump_release_s`` — sidechain: pad + bass gain drops by
      ``pump_depth_db`` at every beat and recovers linearly (in dB) over ``pump_release_s``.
    * ``hats`` — ``"offbeat8"`` (positions 2,6,10,14) or ``"16ths"`` (every 16th, odd ones swung).
    * ``bass`` — ``"sustain"`` (held 55 Hz) or ``"offbeat"`` (short notes on the off-8ths).
    * ``arrangement`` — list of ``(n_bars, layers)`` from the first downbeat, layers ⊆
      {"kick", "hats", "bass", "pad", "stab"}; the last entry repeats to the end. ``None`` = all on.
      Section boundaries fall on bar starts, giving ground truth for structure detection.
    """
    if not 0 <= downbeat_offset <= 3:
        raise ValueError("downbeat_offset must be in 0..3")
    if not 0 <= beat0_s < 60.0 / bpm:
        raise ValueError("beat0_s must satisfy 0 <= beat0_s < period")

    rng = np.random.default_rng(seed)
    n = int(round(duration_s * sr))
    y = np.zeros(n, dtype=np.float64)
    period = 60.0 / bpm

    bar_s = 4 * period
    first_down = beat0_s + downbeat_offset * period

    def layer_on(layer: str, t: float) -> bool:
        if arrangement is None:
            return True
        bar = int(np.floor((t - first_down) / bar_s))
        if bar < 0:
            return True
        acc = 0
        for n_bars, layers in arrangement:
            acc += n_bars
            if bar < acc:
                return layer in layers
        return layer in arrangement[-1][1]

    def layer_gate(layer: str) -> np.ndarray:
        """Per-sample 0/1 gate with 20 ms edges for sustained layers."""
        if arrangement is None:
            return np.ones(n)
        t_all_ = np.arange(n) / sr
        bars = np.floor((t_all_ - first_down) / bar_s).astype(int)
        gate = np.ones(n)
        acc = 0
        for n_bars, layers in arrangement:
            sel = (bars >= acc) & (bars < acc + n_bars)
            gate[sel] = 1.0 if layer in layers else 0.0
            acc += n_bars
        gate[bars >= acc] = 1.0 if layer in arrangement[-1][1] else 0.0
        k = max(int(0.02 * sr), 1)
        return np.convolve(gate, np.ones(k) / k, mode="same")

    if style == "clicks":
        click = _decaying_sine(sr, 1000.0, 0.03, 0.006)
        accent = _decaying_sine(sr, 1500.0, 0.04, 0.008)
        k = 0
        while True:
            at = int(round((beat0_s + k * period) * sr))
            if at >= n:
                break
            is_down = (k - downbeat_offset) % 4 == 0
            _place(y, accent if is_down else click, at, 1.0 if is_down else 0.6)
            k += 1
    else:
        kick = _kick(sr)
        hat = _hat(sr, rng)
        stab = sum(_decaying_sine(sr, f, 0.5, 0.15) for f in (220.0, 261.63, 329.63)) / 3.0
        bass_note = _decaying_sine(sr, 55.0, 0.18, 0.06)
        n_att = int(0.005 * sr)                      # 5 ms attack ramp: real basses are not clicks
        bass_note[:n_att] *= np.linspace(0.0, 1.0, n_att)
        p16 = period / 4.0
        swing_delay = (swing - 0.5) * period / 2.0
        hat_positions = (2, 6, 10, 14) if hats == "offbeat8" else tuple(range(16))
        t_all = np.arange(n) / sr
        # sustained layers, then sidechain-pumped to the beat grid
        sustained = np.zeros(n)
        if bass == "sustain":
            sustained += 0.15 * np.sin(2 * np.pi * 55.0 * t_all) * layer_gate("bass")
        pad = sum(np.sin(2 * np.pi * f * t_all) for f in (220.0, 261.63, 329.63)) / 3.0
        sustained += 0.2 * pad * layer_gate("pad")
        # downbeat chord stabs are sidechained like everything that is not kick or hats
        k = 0
        while True:
            t_beat = beat0_s + k * period
            at = int(round(t_beat * sr))
            if at >= n:
                break
            if (k - downbeat_offset) % 4 == 0 and layer_on("stab", t_beat):
                _place(sustained, stab, at, 0.2)
            k += 1
        if pump_depth_db > 0:
            tau = (t_all - beat0_s) % period                       # time since last beat
            db = -pump_depth_db * np.clip(1.0 - tau / pump_release_s, 0.0, 1.0)
            sustained *= 10 ** (db / 20)
        y += sustained
        k = 0
        while True:
            t_beat = beat0_s + k * period
            at = int(round(t_beat * sr))
            if at >= n:
                break
            is_down = (k - downbeat_offset) % 4 == 0
            g = 1.0 + 0.05 * rng.standard_normal()
            if layer_on("kick", t_beat):
                _place(y, kick, at, (1.0 if is_down else 0.8) * g)
            # 16th sub-grid within this beat: positions 4k..4k+3 in the bar
            bar_pos0 = ((k - downbeat_offset) % 4) * 4
            for q in range(4):
                pos = bar_pos0 + q
                t_q = t_beat + q * p16 + (swing_delay if q % 2 == 1 else 0.0)
                if pos in hat_positions and layer_on("hats", t_q):
                    _place(y, hat, int(round(t_q * sr)), 0.8 + 0.1 * rng.standard_normal())
                if bass == "offbeat" and pos in (2, 6, 10, 14) and layer_on("bass", t_q):
                    _place(y, bass_note, int(round(t_q * sr)), 0.9)
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
        bpm=bpm, beat0_s=beat0_s, downbeat_offset=downbeat_offset, sr=sr, duration_s=duration_s,
        swing=swing, pump_depth_db=pump_depth_db, pump_release_s=pump_release_s, hats=hats, bass=bass,
    )
    return y, truth
