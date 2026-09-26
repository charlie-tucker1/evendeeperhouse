"""Sections + cues (directive P0.7).

Structure is found at *bar* resolution on the beat-feature cache:
  1. bar features = mean over the 4 beats of each bar: z-scored log-mel ⊕ chroma;
  2. self-similarity (cosine) → Foote checkerboard novelty (kernel = ``kernel_bars`` each side);
  3. plus a low-band energy-change novelty — the kick/bass dropping out or returning is the
     archetypal house boundary and the SSM alone under-weights it;
  4. peaks → boundaries; the 8-bar phrase phase is the residue class of bars that boundaries
     favour (``phrase0_bar``);
  5. sections get energy / vocal / bass_active / harm_density attributes and a coarse label;
  6. cues: phrase starts in the first 30 % (``cues_in``, prefer low density, no vocal, low energy)
     and in the last 40 % (``cues_out``, prefer falling energy, no vocal), capped at 6 per side.
All of it is heuristic, all of it is override-able in the sidecar, and all of it is scored,
never gated (NORTHSTAR §5.4).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from .grid import GridFit


@dataclass
class Section:
    start_bar: int
    end_bar: int
    label: str
    energy: float
    vocal: bool
    bass_active: bool
    harm_density: float


@dataclass
class Cue:
    bar: int
    energy: float
    vocal: bool
    bass_active: bool
    harm_density: float
    score: float
    kind: str                     # "in" | "out"


@dataclass
class Structure:
    n_bars: int
    phrase0_bar: int
    boundaries: list[int]
    novelty: list[float]
    sections: list[Section]
    cues_in: list[Cue]
    cues_out: list[Cue]
    bar_energy: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_bars": self.n_bars, "phrase0_bar": self.phrase0_bar, "boundaries": self.boundaries,
            "novelty": [round(float(v), 4) for v in self.novelty],
            "sections": [asdict(s) for s in self.sections],
            "cues_in": [asdict(c) for c in self.cues_in], "cues_out": [asdict(c) for c in self.cues_out],
            "bar_energy": [round(float(v), 4) for v in self.bar_energy],
        }


# ----------------------------------------------------------------------------- bar features


def bar_matrix(x: np.ndarray, g: GridFit, n_bars: int) -> np.ndarray:
    """Mean of beat rows over each bar, bars counted from the first downbeat. ``x``: [n_beats, F] or [n_beats]."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    off = g.downbeat_offset
    out = np.zeros((n_bars, x.shape[1]))
    for b in range(n_bars):
        s = off + 4 * b
        out[b] = x[s:s + 4].mean(axis=0)
    return out


def n_full_bars(n_beats: int, g: GridFit) -> int:
    return max((n_beats - g.downbeat_offset) // 4, 0)


def _z(x: np.ndarray) -> np.ndarray:
    return (x - x.mean(axis=0)) / (x.std(axis=0) + 1e-9)


def foote_novelty(S: np.ndarray, L: int) -> np.ndarray:
    """Checkerboard-kernel novelty of a self-similarity matrix; Gaussian-tapered kernel of half-size L."""
    n = len(S)
    k = np.arange(-L, L)
    kern = np.sign(k[:, None] + 0.5) * np.sign(k[None, :] + 0.5)
    taper = np.exp(-0.5 * ((k + 0.5) / (0.5 * L)) ** 2)
    kern = kern * taper[:, None] * taper[None, :]
    Sp = np.pad(S, L, mode="edge")
    nov = np.zeros(n)
    for i in range(n):
        nov[i] = (Sp[i:i + 2 * L, i:i + 2 * L] * kern).sum()
    nov = np.maximum(nov, 0.0)
    return nov / (nov.max() or 1.0)


def _peaks(x: np.ndarray, min_dist: int, thr: float) -> list[int]:
    idx = [i for i in range(1, len(x) - 1) if x[i] >= x[i - 1] and x[i] > x[i + 1] and x[i] >= thr]
    idx.sort(key=lambda i: -x[i])
    keep: list[int] = []
    for i in idx:
        if all(abs(i - j) >= min_dist for j in keep):
            keep.append(i)
    return sorted(keep)


# ----------------------------------------------------------------------------- main


def analyze_structure(feats: dict[str, np.ndarray], g: GridFit, kernel_bars: int = 8, min_section_bars: int = 4,
                      phrase_bars: int = 8, max_cues: int = 6) -> Structure:
    n_beats = len(feats["beat_times"])
    nb = n_full_bars(n_beats, g)
    if nb < 2 * kernel_bars + 2:
        raise ValueError(f"track too short for structure analysis ({nb} bars)")

    mel = bar_matrix(feats["mel_mix"], g, nb)                                  # [nb, 64] dB
    chroma = bar_matrix(feats["chroma"], g, nb)                                # [nb, 12]
    rms = bar_matrix(feats["rms_mix"], g, nb)[:, 0]
    low = bar_matrix(feats["mel_mix"][:, :8].mean(axis=1), g, nb)[:, 0]        # low-band dB
    has_stems = "rms_bass" in feats
    bass_rms = bar_matrix(feats["rms_bass"], g, nb)[:, 0] if has_stems else None
    voc_rms = bar_matrix(feats["rms_vocals"], g, nb)[:, 0] if has_stems else None

    # --- novelty
    F = np.concatenate([_z(mel), 3.0 * _z(chroma)], axis=1)
    Fn = F / (np.linalg.norm(F, axis=1, keepdims=True) + 1e-9)
    S = Fn @ Fn.T
    nov_ssm = foote_novelty(S, kernel_bars)
    d_low = np.abs(np.diff(low, prepend=low[0]))
    nov_low = d_low / (np.percentile(d_low, 99) or 1.0)
    d_rms = np.abs(np.diff(20 * np.log10(rms + 1e-9), prepend=20 * np.log10(rms[0] + 1e-9)))
    nov_rms = d_rms / (np.percentile(d_rms, 99) or 1.0)
    nov = 0.5 * nov_ssm + 0.3 * np.clip(nov_low, 0, 1) + 0.2 * np.clip(nov_rms, 0, 1)
    nov /= nov.max() or 1.0

    thr = float(np.mean(nov) + 1.0 * np.std(nov))
    bounds = _peaks(nov, min_section_bars, thr)
    # 8-bar phrase phase: the residue class boundaries favour, weighted by novelty
    votes = np.zeros(phrase_bars)
    for b in bounds:
        votes[b % phrase_bars] += nov[b]
    phrase0 = int(np.argmax(votes)) if bounds else 0
    edges = [0, *bounds, nb]

    # --- section attributes
    e_norm = rms / (np.percentile(rms, 95) or 1.0)
    low_med = np.median(low)
    def harm_density(c: np.ndarray) -> float:
        p = np.maximum(c, 0) / (np.maximum(c, 0).sum() or 1.0)
        return float(-(p * np.log(p + 1e-12)).sum() / np.log(12))
    if has_stems:
        voc_thr = 0.35 * (np.percentile(voc_rms, 95) or 1.0)
        bass_thr = 0.35 * (np.percentile(bass_rms, 95) or 1.0)

    def attrs(a: int, b: int) -> tuple[float, bool, bool, float]:
        en = float(np.clip(e_norm[a:b].mean(), 0, 1.5))
        voc = bool(voc_rms[a:b].mean() > voc_thr) if has_stems else False
        bass = bool(bass_rms[a:b].mean() > bass_thr) if has_stems else bool(low[a:b].mean() > low_med - 6.0)
        return en, voc, bass, harm_density(chroma[a:b].mean(axis=0))

    sections: list[Section] = []
    for i, (a, b) in enumerate(zip(edges[:-1], edges[1:], strict=True)):
        en, voc, bass, hd = attrs(a, b)
        if i == 0 and (en < 0.75 or not bass):
            label = "intro"
        elif i == len(edges) - 2 and (en < 0.75 or not bass):
            label = "outro"
        elif not bass or en < 0.6:
            label = "breakdown"
        else:
            label = "main"
        sections.append(Section(a, b, label, round(en, 3), voc, bass, round(hd, 3)))

    # --- cues
    def phrase_starts(lo: int, hi: int) -> list[int]:
        return [b for b in range(lo, hi) if (b - phrase0) % phrase_bars == 0]

    def cue(b: int, kind: str) -> Cue:
        a2 = min(b + phrase_bars, nb)
        en, voc, bass, hd = attrs(b, a2)
        if kind == "in":
            # want: quiet, low density, no vocal, and sitting at a boundary
            score = (1 - en) + (1 - hd) + (0.0 if voc else 0.5) + (0.5 if b in bounds or b == 0 else 0.0)
        else:
            prev = e_norm[max(b - phrase_bars, 0):b].mean() if b > 0 else en
            falling = float(np.clip(prev - en, 0, 1))
            score = falling * 2 + (0.0 if voc else 0.5) + (0.5 if b in bounds else 0.0) + (0.3 if not bass else 0.0)
        return Cue(b, round(en, 3), voc, bass, round(hd, 3), round(float(score), 3), kind)

    cues_in = sorted((cue(b, "in") for b in phrase_starts(0, max(int(0.3 * nb), phrase_bars))), key=lambda c: -c.score)[:max_cues]
    out_lo = int(0.6 * nb)
    cand_out = set(phrase_starts(out_lo, nb - phrase_bars + 1)) | {b for b in bounds if b >= out_lo}
    cues_out = sorted((cue(b, "out") for b in sorted(cand_out)), key=lambda c: -c.score)[:max_cues]
    cues_in.sort(key=lambda c: c.bar)
    cues_out.sort(key=lambda c: c.bar)

    return Structure(n_bars=nb, phrase0_bar=phrase0, boundaries=bounds, novelty=nov.tolist(), sections=sections,
                     cues_in=cues_in, cues_out=cues_out, bar_energy=e_norm.tolist())
