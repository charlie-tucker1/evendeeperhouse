"""Search v0 (directive Phase 2, P2.1–P2.2): enumerate → L0 → L1, zero renders.

Library      one ``LibTrack`` per analysed track (grid, key, groove, cues, npz features).
Enumerate    (B, cue_out of A, cue_in of B, recipe) triples.
L0           static filters — Camelot, tempo ratio, energy window. ``camelot.mode: soft`` turns
             the key gate into a scored penalty (NORTHSTAR §5.4: filters must be demotable).
L1           beat-domain score on cached per-beat features with the recipe applied *in the
             feature domain* (bass masked before/after the swap, etc.), plus the pairwise groove
             features. Vectorised over all triples; target ≥ 2,000 triples/s.

All weights live in ``deephouse.yaml`` under ``search.l1_weights``; every candidate's feature
vector is returned so it can be persisted (NORTHSTAR §5.3).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ..analysis import camelot, store
from ..analysis.features import load_features
from ..analysis.grid import GridFit
from ..analysis.groove import GrooveProfile, groove_compat
from ..config import Config
from ..ingest import Registry, RegistryEntry
from ..render.recipe import TransitionRecipe, default_grid

LOW_MEL_BANDS = 8            # mel bands 0..7 ≈ < 300 Hz at 64 mels / 22.05 kHz


@dataclass
class LibTrack:
    sha1: str
    name: str
    grid: GridFit
    camelot: camelot.Camelot | None
    key_conf: float
    groove: GrooveProfile | None
    cues_in: list[dict[str, Any]]
    cues_out: list[dict[str, Any]]
    bar_energy: np.ndarray
    n_bars: int
    npz_path: Path
    _feats: dict[str, np.ndarray] | None = field(default=None, repr=False)

    @property
    def bpm(self) -> float:
        return self.grid.bpm

    @property
    def feats(self) -> dict[str, np.ndarray]:
        if self._feats is None:
            self._feats = load_features(self.npz_path)
        return self._feats

    def beat_of_bar(self, bar: int) -> int:
        return self.grid.downbeat_offset + 4 * bar


def load_library(cfg: Config, only: list[str] | None = None) -> list[LibTrack]:
    reg = Registry(cfg.path("registry"))
    out = []
    for e in reg.by_kind("track"):
        if only and e.sha1 not in only:
            continue
        t = _load_libtrack(cfg, e)
        if t is not None:
            out.append(t)
    return out


def _load_libtrack(cfg: Config, e: RegistryEntry) -> LibTrack | None:
    doc = store.load_analysis(cfg, e.sha1)
    if not doc or not doc.get("grid") or not doc.get("structure") or "error" in doc["structure"]:
        return None
    npz = cfg.path("cache_analysis") / f"{e.sha1}.npz"
    if not npz.exists():
        return None
    g = store.get_grid(doc)
    k = doc.get("key") or {}
    cam = None
    code = k.get("override") or k.get("camelot")
    if code:
        cam = camelot.parse(code)
    gr = GrooveProfile.from_dict(doc["groove"]) if doc.get("groove") else None
    st = doc["structure"]
    return LibTrack(
        sha1=e.sha1, name=Path(e.source_path).name, grid=g, camelot=cam, key_conf=float(k.get("confidence", 0.0)),
        groove=gr, cues_in=list(doc.get("cues_in") or []), cues_out=list(doc.get("cues_out") or []),
        bar_energy=np.asarray(st.get("bar_energy", []), dtype=np.float32), n_bars=int(st["n_bars"]), npz_path=npz,
    )


# ----------------------------------------------------------------------------- enumeration + L0


@dataclass
class Candidate:
    b: LibTrack
    cue_out: int
    cue_in: int
    recipe: TransitionRecipe
    l0: dict[str, float] = field(default_factory=dict)
    l1_features: dict[str, float] = field(default_factory=dict)
    l1: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"b": self.b.sha1, "b_name": self.b.name, "cue_out": self.cue_out, "cue_in": self.cue_in,
                "recipe": self.recipe.key, "l0": self.l0, "l1_features": self.l1_features, "l1": self.l1}


def l0_filter(a: LibTrack, b: LibTrack, cfg: Config) -> tuple[bool, dict[str, float]]:
    """Static gate. Returns (passes, penalties). In ``soft`` mode nothing is gated on key; the
    key penalty becomes an L1 feature instead."""
    sc = cfg.raw.get("search", {}) or {}
    max_stretch = float(sc.get("max_stretch_ratio", 1.06))
    ratio = a.bpm / b.bpm
    pen = {"stretch_penalty": float(abs(np.log2(ratio)))}
    if abs(np.log2(ratio)) > np.log2(max_stretch):
        return False, pen
    mode = str(cfg.camelot.mode)
    moves = list(cfg.camelot.allowed_moves)
    if a.camelot is not None and b.camelot is not None:
        compatible = camelot.is_compatible(a.camelot, b.camelot, moves)
        dist = camelot.wheel_distance(a.camelot, b.camelot) + (0 if a.camelot.is_minor == b.camelot.is_minor else 0.5)
        pen["key_penalty"] = 0.0 if compatible else float(dist)
        if mode == "hard" and not compatible:
            return False, pen
    else:
        pen["key_penalty"] = 0.5      # unknown key: mild penalty, never a gate
    return True, pen


def enumerate_candidates(a: LibTrack, library: list[LibTrack], cfg: Config,
                         recipes: list[TransitionRecipe] | None = None, max_per_pair: int = 64) -> list[Candidate]:
    recipes = recipes or default_grid()
    sc = cfg.raw.get("search", {}) or {}
    e_win = float(sc.get("energy_window", 0.35))
    out: list[Candidate] = []
    for b in library:
        if b.sha1 == a.sha1:
            continue
        ok, pen = l0_filter(a, b, cfg)
        if not ok:
            continue
        n = 0
        for co in a.cues_out:
            for ci in b.cues_in:
                # energy window between A's exit and B's entry (absolute; arc slope is v1.1)
                if abs(float(co["energy"]) - float(ci["energy"])) > e_win:
                    continue
                for r in recipes:
                    if co["bar"] + r.overlap_bars > a.n_bars or ci["bar"] + r.overlap_bars > b.n_bars:
                        continue
                    out.append(Candidate(b, int(co["bar"]), int(ci["bar"]), r, l0=dict(pen)))
                    n += 1
                    if n >= max_per_pair:
                        break
                if n >= max_per_pair:
                    break
            if n >= max_per_pair:
                break
    return out


# ----------------------------------------------------------------------------- L1


DEFAULT_L1_WEIGHTS = {
    "bass_clash": -3.0, "masking": -1.0, "vocal_overlap_bars": -0.5, "harmonic": 2.0, "energy_step": -1.5,
    "stretch_penalty": -20.0, "key_penalty": -0.5,
    "flam_risk_ms": -0.05, "swing_mismatch_ms": -0.03, "bass_placement_step_ms": -0.02, "pattern_density": -0.3,
    "pump_mismatch": -0.1, "bass_pattern_continuity": 0.5, "kick_rise_mismatch_ms": -0.02,
}


def _overlap_feats(t: LibTrack, start_beat: int, K: int) -> dict[str, np.ndarray]:
    f = t.feats
    sl = slice(start_beat, start_beat + K)
    out = {"mel": f["mel_mix"][sl], "chroma": f["chroma"][sl], "rms": f["rms_mix"][sl]}
    out["rms_bass"] = f["rms_bass"][sl] if "rms_bass" in f else None
    out["rms_vocals"] = f["rms_vocals"][sl] if "rms_vocals" in f else None
    out["low"] = 10 ** (f["mel_mix"][sl, :LOW_MEL_BANDS] / 10)                      # linear power, low bands
    return out


def l1_score(a: LibTrack, cands: list[Candidate], cfg: Config) -> list[Candidate]:
    """Score every candidate in the beat domain. Vectorised per (B, recipe overlap length)
    group so the per-beat arrays are sliced once per group."""
    sc = cfg.raw.get("search", {}) or {}
    w = dict(DEFAULT_L1_WEIGHTS)
    w.update(sc.get("l1_weights", {}) or {})
    voc_thr_frac = float(sc.get("vocal_active_frac", 0.35))
    groove_cache: dict[str, dict[str, float]] = {}
    a_voc_thr = voc_thr_frac * float(np.percentile(a.feats["rms_vocals"], 95)) if "rms_vocals" in a.feats else None

    for c in cands:
        r = c.recipe
        K = 4 * r.overlap_bars
        A = _overlap_feats(a, a.beat_of_bar(c.cue_out), K)
        B = _overlap_feats(c.b, c.b.beat_of_bar(c.cue_in), K)
        n = min(len(A["rms"]), len(B["rms"]))
        if n < 4:
            c.l1 = -1e9
            continue
        swap = int(round(r.bass_swap_frac * K))
        # recipe in the feature domain: B's lows are off before the swap, A's lows off after
        maskA = np.ones(n, np.float32)
        maskA[swap:] = 0.0
        maskB = 1.0 - maskA
        lowA, lowB = A["low"][:n] * maskA[:, None], B["low"][:n] * maskB[:, None]
        f: dict[str, float] = {}
        if A["rms_bass"] is not None and B["rms_bass"] is not None:
            f["bass_clash"] = float((np.minimum(A["rms_bass"][:n] * maskA, B["rms_bass"][:n] * maskB)).sum() / n)
        else:
            f["bass_clash"] = float(np.minimum(lowA, lowB).sum() / (n * LOW_MEL_BANDS))
        # spectral masking: overlap of linear power, weighted 3× on the low bands
        pa, pb = 10 ** (A["mel"][:n] / 10), 10 ** (B["mel"][:n] / 10)
        pa[:, :LOW_MEL_BANDS] *= maskA[:, None]
        pb[:, :LOW_MEL_BANDS] *= maskB[:, None]
        wgt = np.ones(pa.shape[1], np.float32)
        wgt[:LOW_MEL_BANDS] = 3.0
        f["masking"] = float((np.minimum(pa, pb) * wgt).sum() / (np.maximum(pa, pb) * wgt).sum())
        if A["rms_vocals"] is not None and B["rms_vocals"] is not None and a_voc_thr is not None:
            b_thr = voc_thr_frac * float(np.percentile(c.b.feats["rms_vocals"], 95))
            both = (A["rms_vocals"][:n] > a_voc_thr) & (B["rms_vocals"][:n] > b_thr)
            f["vocal_overlap_bars"] = float(both.sum() / 4.0) if r.vocal_rule == "none" else 0.0
        else:
            f["vocal_overlap_bars"] = 0.0
        ca, cb = A["chroma"][:n], B["chroma"][:n]
        num = (ca * cb).sum(axis=1)
        den = np.linalg.norm(ca, axis=1) * np.linalg.norm(cb, axis=1) + 1e-9
        f["harmonic"] = float((num / den).mean())
        ea = float(a.bar_energy[c.cue_out - 8:c.cue_out].mean()) if c.cue_out >= 8 else float(a.bar_energy[:c.cue_out + 1].mean())
        eb = float(c.b.bar_energy[c.cue_in + r.overlap_bars:c.cue_in + r.overlap_bars + 8].mean()) if len(c.b.bar_energy) > c.cue_in + r.overlap_bars else float(c.b.bar_energy[c.cue_in:].mean())
        f["energy_step"] = float(abs(ea - eb))
        f.update(c.l0)
        if a.groove is not None and c.b.groove is not None:
            if c.b.sha1 not in groove_cache:
                groove_cache[c.b.sha1] = groove_compat(a.groove, c.b.groove, a.grid.period_s)
            f.update(groove_cache[c.b.sha1])
        c.l1_features = {k: round(v, 5) for k, v in f.items()}
        c.l1 = float(sum(w.get(k, 0.0) * v for k, v in f.items()))
    return cands


# ----------------------------------------------------------------------------- driver


@dataclass
class SearchReport:
    a: LibTrack
    n_library: int
    n_enumerated: int
    n_scored: int
    seconds: float
    triples_per_s: float
    ranked: list[Candidate]

    def collapsed(self) -> list[Candidate]:
        """Best recipe per (B, cue_out, cue_in): L1 barely separates recipes by design (that is
        L2's job), so the top-k shown and rendered should be *different transitions*."""
        seen: set[tuple[str, int, int]] = set()
        out = []
        for c in self.ranked:                     # already sorted by L1 desc
            key = (c.b.sha1, c.cue_out, c.cue_in)
            if key not in seen:
                seen.add(key)
                out.append(c)
        return out

    def table(self, k: int = 20, collapse: bool = True) -> str:
        rows = self.collapsed() if collapse else self.ranked
        lines = [f"seed: {self.a.name}  {self.a.bpm:.2f} bpm  {self.a.camelot or '?'}",
                 f"library {self.n_library}  enumerated {self.n_enumerated}  scored {self.n_scored} in {self.seconds:.1f}s ({self.triples_per_s:.0f}/s)"
                 + ("  — best recipe per (B, cues)" if collapse else ""),
                 "", f"{'#':>3} {'L1':>7}  {'B':28s} {'bpm':>7} {'key':>4} {'out':>4} {'in':>4}  recipe               harm  mask  swingΔ flam  eΔ"]
        for i, c in enumerate(rows[:k], 1):
            f = c.l1_features
            lines.append(f"{i:>3} {c.l1:>7.2f}  {c.b.name[:28]:28s} {c.b.bpm:>7.2f} {str(c.b.camelot or '?'):>4} {c.cue_out:>4} {c.cue_in:>4}  {c.recipe.key:20s} "
                         f"{f.get('harmonic', 0):.2f}  {f.get('masking', 0):.2f}  {f.get('swing_mismatch_ms', 0):5.1f} {f.get('flam_risk_ms', 0):4.1f}  {f.get('energy_step', 0):.2f}")
        return "\n".join(lines)


def search_next(cfg: Config, a: LibTrack, library: list[LibTrack], recipes: list[TransitionRecipe] | None = None,
                top: int = 100) -> SearchReport:
    t0 = time.time()
    cands = enumerate_candidates(a, library, cfg, recipes)
    l1_score(a, cands, cfg)
    cands.sort(key=lambda c: -c.l1)
    dt = time.time() - t0
    return SearchReport(a=a, n_library=len(library), n_enumerated=len(cands), n_scored=len(cands), seconds=dt,
                        triples_per_s=len(cands) / dt if dt > 0 else float("inf"), ranked=cands[:top])
