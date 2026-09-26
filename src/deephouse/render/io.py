"""Load registry tracks into ``engine.Track`` objects and persist render results."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from ..analysis import store
from ..analysis.features import STEMS, has_stems
from ..audio import load_audio, write_wav
from ..config import Config
from ..ingest import RegistryEntry, audio_path_for
from .engine import RenderConfig, RenderResult, Track


def load_track(cfg: Config, entry: RegistryEntry, with_stems: bool = True) -> Track:
    doc = store.load_analysis(cfg, entry.sha1)
    if not doc or not doc.get("grid"):
        raise SystemExit(f"{entry.sha1[:10]}: no grid — run `deephouse analyze` first")
    g = store.get_grid(doc)
    sr = int(cfg.audio.sample_rate)
    y, _ = load_audio(audio_path_for(cfg, entry), sr=sr)
    if y.ndim == 1:
        y = np.stack([y, y], axis=1)
    stems = None
    sdir = cfg.path("cache_stems") / entry.sha1
    if with_stems and has_stems(sdir):
        stems = {}
        for s in STEMS:
            ys, _ = load_audio(sdir / f"{s}.flac", sr=sr)
            stems[s] = ys if ys.ndim == 2 else np.stack([ys, ys], axis=1)
    return Track(entry.sha1, y.astype(np.float32), sr, g, stems=stems)


def render_config_from(cfg: Config, **overrides) -> RenderConfig:
    rc = cfg.raw.get("render", {}) or {}
    known = set(RenderConfig.__dataclass_fields__)
    kw = {k: v for k, v in rc.items() if k in known}
    kw.update({k: v for k, v in overrides.items() if v is not None})
    return RenderConfig(**kw)


def save_render(cfg: Config, res: RenderResult, run_id: str | None = None, name: str | None = None) -> Path:
    run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
    out_dir = cfg.path("renders") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    name = name or f"{res.meta['a'][:8]}_{res.meta['cue_out_bar']}__{res.meta['b'][:8]}_{res.meta['cue_in_bar']}__{res.meta['recipe_key']}"
    write_wav(out_dir / f"{name}.wav", res.audio, res.sr, subtype="PCM_24")
    with (out_dir / f"{name}.render_meta.json").open("w") as f:
        json.dump(res.meta, f, indent=1, sort_keys=True, default=float)
    return out_dir / f"{name}.wav"
