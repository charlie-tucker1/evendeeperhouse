"""Phase-0 analysis orchestrator: runs the per-track analysis steps and writes the sidecar.

Session 1 scope: grid fit (P0.2). Later sessions add stems/features/key/sections/cues
as further steps in ``analyze_track``; each step is idempotent and guarded by a
``--force`` flag so re-runs only compute what is missing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from ..audio import load_audio
from ..config import Config
from ..ingest import Registry, RegistryEntry, audio_path_for
from . import store
from .grid import fit_grid


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
    skipped: bool = False


def analyze_track(cfg: Config, entry: RegistryEntry, force: bool = False) -> AnalyzeResult:
    t0 = time.time()
    path = audio_path_for(cfg, entry)
    name = path.name
    doc = store.load_analysis(cfg, entry.sha1)
    if doc and doc.get("grid") and not force:
        g = store.get_grid(doc)
        return AnalyzeResult(entry.sha1, name, g.bpm, g.beat0_s, g.downbeat_offset, g.confidence,
                             list(g.flags), 0.0, skipped=True)

    y, sr = load_audio(path, mono=True)
    if doc is None:
        doc = store.new_doc(entry.sha1, entry.source_path, len(y) / sr)
    doc["duration_s"] = len(y) / sr

    gc = cfg.grid
    g = fit_grid(
        y, sr, tracker=gc.tracker, bpm_min=float(cfg.genre.bpm_min), bpm_max=float(cfg.genre.bpm_max),
        reject_ms=float(gc.residual_reject_ms), max_refit_iters=int(gc.max_refit_iters),
        confidence_flag_threshold=float(gc.confidence_flag_threshold),
    )
    store.set_grid(doc, g)
    store.save_analysis(cfg, entry.sha1, doc)
    return AnalyzeResult(entry.sha1, name, g.bpm, g.beat0_s, g.downbeat_offset, g.confidence,
                         list(g.flags), time.time() - t0)


def analyze_all(cfg: Config, force: bool = False, only: list[str] | None = None, log=print) -> list[AnalyzeResult]:
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
        r = analyze_track(cfg, e, force=force)
        results.append(r)
        tag = "skip" if r.skipped else f"{r.seconds:5.1f}s"
        flag = f"  ⚠ {' '.join(r.flags)}" if r.flags else ""
        log(f"  [{i}/{len(entries)}] {tag}  {r.bpm:8.3f} bpm  beat0 {r.beat0_s:.3f}s  down {r.downbeat_offset}  conf {r.confidence:.2f}  {r.name[:48]}{flag}")
    return results
