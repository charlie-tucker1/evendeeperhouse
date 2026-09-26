"""Pluggable beat / downbeat tracker backends.

Each backend returns a ``BeatEstimate`` — raw tracker output that the grid
fitter then regularises into a constant-tempo grid. Backends are resolved by
name; heavy dependencies are imported lazily so the package imports cleanly
on machines without them (tests run on ``librosa`` everywhere).

  librosa    — always available; DP beat tracker, no downbeats.
  beat_this  — CPJKU transformer (GPU); beats + downbeats. Preferred on the 5070 box.
  madmom     — RNN + DBN downbeat tracker; beats + downbeats. Fallback.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

HOP = 512  # frames for librosa tracking / onset envelope


@dataclass
class BeatEstimate:
    beats_s: np.ndarray                      # sorted beat times (s)
    downbeats_s: np.ndarray | None = None    # subset of beats_s, or None if backend has none
    tempo_hint: float | None = None          # backend's own tempo estimate, if any
    backend: str = ""
    meta: dict = field(default_factory=dict)


def available_backends() -> list[str]:
    out = ["librosa"]
    for name, mod in (("beat_this", "beat_this"), ("madmom", "madmom")):
        if importlib.util.find_spec(mod) is not None:
            out.append(name)
    return out


def resolve(name: str) -> str:
    """'auto' -> best available: beat_this > madmom > librosa."""
    if name != "auto":
        return name
    avail = available_backends()
    for pref in ("beat_this", "madmom", "librosa"):
        if pref in avail:
            return pref
    return "librosa"


def track(
    y: np.ndarray,
    sr: int,
    backend: str = "auto",
    start_bpm: float = 123.0,
    path: Path | None = None,
) -> BeatEstimate:
    backend = resolve(backend)
    if backend == "librosa":
        return _track_librosa(y, sr, start_bpm)
    if backend == "beat_this":
        return _track_beat_this(y, sr, path)
    if backend == "madmom":
        return _track_madmom(y, sr)
    raise ValueError(f"unknown tracker backend {backend!r}")


# --------------------------------------------------------------------------- librosa


def _track_librosa(y: np.ndarray, sr: int, start_bpm: float) -> BeatEstimate:
    import librosa

    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    tempo, beat_frames = librosa.beat.beat_track(
        onset_envelope=oenv, sr=sr, hop_length=HOP, start_bpm=start_bpm, tightness=100,
        trim=False, units="frames",
    )
    beats_s = librosa.frames_to_time(beat_frames, sr=sr, hop_length=HOP)
    tempo_f = float(np.atleast_1d(tempo)[0])
    return BeatEstimate(beats_s=np.asarray(beats_s, dtype=np.float64), downbeats_s=None,
                        tempo_hint=tempo_f, backend="librosa")


# --------------------------------------------------------------------------- beat_this


def _track_beat_this(y: np.ndarray, sr: int, path: Path | None) -> BeatEstimate:
    try:
        from beat_this.inference import Audio2Beats
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("beat_this not installed: uv pip install git+https://github.com/CPJKU/beat_this") from e
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    a2b = Audio2Beats(checkpoint_path="final0", device=device, dbn=False)
    beats, downbeats = a2b(y.astype(np.float32), sr)
    return BeatEstimate(
        beats_s=np.asarray(beats, dtype=np.float64),
        downbeats_s=np.asarray(downbeats, dtype=np.float64),
        tempo_hint=None, backend="beat_this", meta={"device": device},
    )


# --------------------------------------------------------------------------- madmom


def _track_madmom(y: np.ndarray, sr: int) -> BeatEstimate:
    try:
        from madmom.features.downbeats import DBNDownBeatTrackingProcessor, RNNDownBeatProcessor
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("madmom not installed") from e
    import librosa

    # madmom expects 44.1 kHz mono float
    if sr != 44100:
        y = librosa.resample(y, orig_sr=sr, target_sr=44100)
    act = RNNDownBeatProcessor()(y.astype(np.float32))
    proc = DBNDownBeatTrackingProcessor(beats_per_bar=[4], fps=100)
    out = proc(act)  # [[time, beat_position], ...] with position 1 == downbeat
    beats_s = out[:, 0].astype(np.float64)
    downbeats_s = out[out[:, 1] == 1, 0].astype(np.float64)
    return BeatEstimate(beats_s=beats_s, downbeats_s=downbeats_s, tempo_hint=None, backend="madmom")
