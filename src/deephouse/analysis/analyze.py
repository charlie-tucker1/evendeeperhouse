"""Phase-0 analysis orchestrator: runs the per-track analysis stages and writes the sidecar.

Stages (each idempotent, each skippable, each re-runnable with ``force``):
  grid      P0.2  constant-tempo grid → sidecar ``grid``
  features  P0.5  beat-synchronous features → ``{sha1}.npz`` (uses stems if cached)
  groove    P0.8  micro-timing / pattern / pump profile → sidecar ``groove``
  key       P0.6  key → Camelot → sidecar ``key``
  structure P0.7  sections + cues → sidecar ``structure`` (+ ``bars.phrase0_bar``)
Later: stems (P0.4, GPU batch).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from ..audio import load_audio
from ..config import Config
from ..ingest import Registry, RegistryEntry, audio_path_for
from . import store
from .features import STEMS, compute_beat_features, has_stems, load_features, save_features
from .grid import fit_grid
from .groove import bands_from_mix, bands_from_stems, compute_groove
from .key import estimate_key
from .sections import analyze_structure

ALL_STAGES = ("grid", "features", "groove", "key", "structure")


@dataclass
class AnalyzeResult:
    sha1: str
    name: str
    bpm: float
    beat0_s: float
    downbeat_offset: int
    confidence: float
    flags: list[str]
    seconds: float
    stages_run: list[str] = field(default_factory=list)
    camelot: str | None = None
    swing_pct: float | None = None
    pump_db: float | None = None
    n_sections: int | None = None

    @property
    def skipped(self) -> bool:
        return not self.stages_run


def _npz_path(cfg: Config, sha1: str):
    return cfg.path("cache_analysis") / f"{sha1}.npz"


def _load_stems(cfg: Config, sha1: str, sr: int) -> dict[str, np.ndarray] | None:
    d = cfg.path("cache_stems") / sha1
    if not has_stems(d):
        return None
    return {s: load_audio(d / f"{s}.flac", sr=sr, mono=True)[0] for s in STEMS}


def analyze_track(cfg: Config, entry: RegistryEntry, force: bool = False,
                  stages: tuple[str, ...] = ALL_STAGES) -> AnalyzeResult:
    t0 = time.time()
    path = audio_path_for(cfg, entry)
    name = path.name
    doc = store.load_analysis(cfg, entry.sha1)
    y = sr = None
    ran: list[str] = []

    def audio():
        nonlocal y, sr
        if y is None:
            y, sr = load_audio(path, mono=True)
        return y, sr

    # ---- grid
    if "grid" in stages and (force or not doc or not doc.get("grid")):
        y, sr = audio()
        if doc is None:
            doc = store.new_doc(entry.sha1, entry.source_path, len(y) / sr)
        doc["duration_s"] = len(y) / sr
        gc = cfg.grid
        g = fit_grid(
            y, sr, tracker=gc.tracker, bpm_min=float(cfg.genre.bpm_min), bpm_max=float(cfg.genre.bpm_max),
            reject_ms=float(gc.residual_reject_ms), max_refit_iters=int(gc.max_refit_iters),
            confidence_flag_threshold=float(gc.confidence_flag_threshold),
            lowband_flip=str(gc.get("lowband_flip", "auto")),
        )
        store.set_grid(doc, g)
        store.save_analysis(cfg, entry.sha1, doc)
        ran.append("grid")
    if not doc or not doc.get("grid"):
        raise SystemExit(f"{entry.sha1[:10]}: no grid and 'grid' not in stages")
    g = store.get_grid(doc)

    # ---- features
    npz = _npz_path(cfg, entry.sha1)
    stems = None
    if "features" in stages and (force or not npz.exists()):
        y, sr = audio()
        stems = _load_stems(cfg, entry.sha1, sr)
        sources = {"mix": y, **(stems or {})}
        feats = compute_beat_features(sources, sr, g)
        save_features(npz, feats)
        doc["features"] = {"npz": str(npz.relative_to(cfg.root)), "n_beats": int(len(feats["beat_times"])),
                           "stems": stems is not None, "keys": sorted(feats.keys())}
        store.save_analysis(cfg, entry.sha1, doc)
        ran.append("features")

    # ---- groove
    if "groove" in stages and (force or not doc.get("groove")):
        y, sr = audio()
        if stems is None:
            stems = _load_stems(cfg, entry.sha1, sr)
        bands = bands_from_stems(stems, sr) if stems else bands_from_mix(y, sr)
        prof = compute_groove(bands, sr, g, len(y) / sr, source="stems" if stems else "bandsplit")
        doc["groove"] = prof.to_dict()
        store.save_analysis(cfg, entry.sha1, doc)
        ran.append("groove")

    # ---- key
    if "key" in stages and (force or not doc.get("key")):
        kc = cfg.key
        backend = str(kc.backend)
        chroma = load_features(npz)["chroma"] if npz.exists() else None
        if backend == "auto" and chroma is not None and not _essentia_present():
            backend = "chroma_template"
        if backend in ("auto", "essentia"):
            y, sr = audio()
            est = estimate_key(y, sr, chroma, backend=backend, essentia_profile=str(kc.essentia_profile))
        else:
            if chroma is None:
                y, sr = audio()
                chroma = compute_beat_features({"mix": y}, sr, g)["chroma"]
            est = estimate_key(None, sr or 44100, chroma, backend="chroma_template")
        prev = doc.get("key") or {}
        d = est.to_dict()
        d["scores"] = None  # keep the sidecar small
        if prev.get("override"):
            d["override"] = prev["override"]
        doc["key"] = d
        store.save_analysis(cfg, entry.sha1, doc)
        ran.append("key")

    # ---- structure (sections + cues)
    if "structure" in stages and (force or not doc.get("structure")):
        if not npz.exists():
            y, sr = audio()
            save_features(npz, compute_beat_features({"mix": y, **(_load_stems(cfg, entry.sha1, sr) or {})}, sr, g))
        feats = load_features(npz)
        try:
            st = analyze_structure(feats, g, phrase_bars=int(cfg.genre.bars_per_phrase))
            doc["structure"] = st.to_dict()
            doc["bars"] = {"bar0_beat": int(g.downbeat_offset), "phrase0_bar": int(st.phrase0_bar)}
            doc["cues_in"] = [c.__dict__ for c in st.cues_in]
            doc["cues_out"] = [c.__dict__ for c in st.cues_out]
            doc["sections"] = [s_.__dict__ for s_ in st.sections]
        except ValueError as e:                       # too short
            doc["structure"] = {"error": str(e)}
        store.save_analysis(cfg, entry.sha1, doc)
        ran.append("structure")

    gr = doc.get("groove") or {}
    key = doc.get("key") or {}
    return AnalyzeResult(
        entry.sha1, name, g.bpm, g.beat0_s, g.downbeat_offset, g.confidence, list(g.flags),
        time.time() - t0, stages_run=ran, camelot=key.get("override") or key.get("camelot"),
        swing_pct=gr.get("swing_pct"), pump_db=gr.get("pump_depth_db"),
        n_sections=len(doc["sections"]) if doc.get("sections") else None,
    )


def _essentia_present() -> bool:
    import importlib.util

    return importlib.util.find_spec("essentia") is not None


def analyze_all(cfg: Config, force: bool = False, only: list[str] | None = None,
                stages: tuple[str, ...] = ALL_STAGES, log=print) -> list[AnalyzeResult]:
    reg = Registry(cfg.path("registry"))
    entries = reg.by_kind("track")
    if only:
        wanted = [reg.lookup(k) for k in only]
        missing = [k for k, e in zip(only, wanted, strict=True) if e is None]
        if missing:
            raise SystemExit(f"unknown track(s): {missing}")
        entries = [e for e in wanted if e is not None]
    results = []
    for i, e in enumerate(entries, 1):
        r = analyze_track(cfg, e, force=force, stages=stages)
        results.append(r)
        tag = "cached" if r.skipped else f"{r.seconds:5.1f}s {'+'.join(r.stages_run)}"
        flag = f"  ⚠ {' '.join(r.flags)}" if r.flags else ""
        extra = ""
        if r.camelot:
            extra += f"  {r.camelot:>3s}"
        if r.swing_pct is not None:
            extra += f"  swing {r.swing_pct * 100:.0f}%"
        if r.pump_db is not None:
            extra += f"  pump {r.pump_db:.1f}dB"
        if r.n_sections is not None:
            extra += f"  {r.n_sections} sections"
        log(f"  [{i}/{len(entries)}] {tag:22s} {r.bpm:8.3f} bpm  beat0 {r.beat0_s:.3f}s  down {r.downbeat_offset}  conf {r.confidence:.2f}{extra}  {r.name[:40]}{flag}")
    return results
