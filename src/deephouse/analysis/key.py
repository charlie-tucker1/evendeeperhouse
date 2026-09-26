"""Key detection (P0.6) → Camelot.

Backends:
  essentia         — ``KeyExtractor(profileType='edma')``, tuned for electronic music. Preferred.
  chroma_template  — Krumhansl–Schmuckler correlation of the beat-mean chroma against 24 key
                     profiles (Temperley's revised weights). Always available; used in tests.

Confidence = (best − second best) correlation margin, mapped to 0..1. Stored with the
Camelot code; a human ``override`` in the sidecar wins everywhere downstream.
"""

from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from . import camelot

# Temperley (2001) revised Krumhansl profiles, index 0 = tonic.
_MAJOR = np.array([5.0, 2.0, 3.5, 2.0, 4.5, 4.0, 2.0, 4.5, 2.0, 3.5, 1.5, 4.0])
_MINOR = np.array([5.0, 2.0, 3.5, 4.5, 2.0, 4.0, 2.0, 4.5, 3.5, 2.0, 1.5, 4.0])


@dataclass
class KeyEstimate:
    camelot: str
    name: str
    pitch_class: int
    minor: bool
    confidence: float
    backend: str
    scores: dict[str, float] | None = None
    override: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> KeyEstimate:
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})

    def effective_camelot(self) -> camelot.Camelot:
        return camelot.parse(self.override) if self.override else camelot.parse(self.camelot)


def estimate_from_chroma(chroma: np.ndarray) -> KeyEstimate:
    """``chroma``: ``[n, 12]`` beat-synchronous chroma (or a single 12-vector), pitch class 0 = C."""
    c = np.asarray(chroma, dtype=np.float64)
    v = c.mean(axis=0) if c.ndim == 2 else c
    v = v - v.mean()
    if np.allclose(v, 0):
        return KeyEstimate("8A", "A minor", 9, True, 0.0, "chroma_template")
    scores: dict[str, float] = {}
    best: tuple[float, int, bool] | None = None
    ranked: list[float] = []
    for minor, prof in ((False, _MAJOR), (True, _MINOR)):
        for pc in range(12):
            p = np.roll(prof, pc)
            p = p - p.mean()
            r = float(v @ p / (np.linalg.norm(v) * np.linalg.norm(p)))
            code = camelot.from_key(pc, minor).code
            scores[code] = r
            ranked.append(r)
            if best is None or r > best[0]:
                best = (r, pc, minor)
    assert best is not None
    ranked.sort(reverse=True)
    margin = ranked[0] - ranked[1]
    conf = float(np.clip(margin / 0.15, 0.0, 1.0))      # 0.15 corr margin ≈ unambiguous
    cam = camelot.from_key(best[1], best[2])
    return KeyEstimate(cam.code, cam.key_name, best[1], best[2], conf, "chroma_template", scores)


def _essentia_available() -> bool:
    return importlib.util.find_spec("essentia") is not None


def estimate_essentia(y: np.ndarray, sr: int, profile: str = "edma") -> KeyEstimate:
    import essentia.standard as es

    if sr != 44100:
        import soxr

        y = soxr.resample(y, sr, 44100, quality="HQ")
    key, scale, strength = es.KeyExtractor(profileType=profile, sampleRate=44100)(np.asarray(y, dtype=np.float32))
    cam = camelot.from_key_name(f"{key} {scale}")
    return KeyEstimate(cam.code, cam.key_name, cam.pitch_class, cam.is_minor, float(np.clip(strength, 0, 1)), f"essentia:{profile}")


def estimate_key(y: np.ndarray | None, sr: int, chroma: np.ndarray | None, backend: str = "auto",
                 essentia_profile: str = "edma") -> KeyEstimate:
    if backend == "auto":
        backend = "essentia" if (_essentia_available() and y is not None) else "chroma_template"
    if backend == "essentia":
        if y is None:
            raise ValueError("essentia backend needs audio")
        return estimate_essentia(y, sr, essentia_profile)
    if backend == "chroma_template":
        if chroma is None:
            raise ValueError("chroma_template backend needs chroma")
        return estimate_from_chroma(chroma)
    raise ValueError(f"unknown key backend {backend!r}")
