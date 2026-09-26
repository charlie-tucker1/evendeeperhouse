"""Analysis sidecar store: ``cache/analysis/{sha1}.json`` (+ ``.npz`` from P0.5 onward).

The JSON is the human-readable, override-able record described in directive §3.
This module owns reading/writing it and applying overrides; nothing else touches
the files directly.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..config import Config
from .grid import GridFit

SCHEMA_VERSION = 1


def analysis_json_path(cfg: Config, sha1: str) -> Path:
    return cfg.path("cache_analysis") / f"{sha1}.json"


def load_analysis(cfg: Config, sha1: str) -> dict[str, Any] | None:
    p = analysis_json_path(cfg, sha1)
    if not p.exists():
        return None
    with p.open() as f:
        return json.load(f)


def save_analysis(cfg: Config, sha1: str, doc: dict[str, Any]) -> Path:
    p = analysis_json_path(cfg, sha1)
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = dict(doc)
    doc["schema_version"] = SCHEMA_VERSION
    doc["updated_at"] = time.time()
    tmp = p.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(doc, f, indent=1, sort_keys=True, default=_json_default)
    tmp.replace(p)
    return p


def _json_default(o: Any) -> Any:
    import numpy as np

    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not JSON serialisable: {type(o)}")


def new_doc(sha1: str, source_path: str, duration_s: float) -> dict[str, Any]:
    return {
        "sha1": sha1,
        "source_path": source_path,
        "duration_s": duration_s,
        "grid": None,
        "key": None,
        "bars": None,
        "sections": None,
        "cues_in": None,
        "cues_out": None,
    }


def get_grid(doc: dict[str, Any], apply_override: bool = True) -> GridFit | None:
    g = doc.get("grid")
    if not g:
        return None
    fit = GridFit.from_dict(g)
    return fit.effective() if apply_override else fit


def set_grid(doc: dict[str, Any], grid: GridFit) -> None:
    """Store a fresh fit, *preserving* any existing human override / review flag."""
    prev = doc.get("grid") or {}
    d = grid.to_dict()
    if prev.get("override"):
        d["override"] = prev["override"]
    if prev.get("reviewed"):
        d["reviewed"] = True
    doc["grid"] = d
    eff = GridFit.from_dict(d).effective()
    doc["bars"] = {"bar0_beat": int(eff.downbeat_offset), "phrase0_bar": doc.get("bars", {}).get("phrase0_bar", 0) if doc.get("bars") else 0}


def set_grid_override(doc: dict[str, Any], **override: Any) -> None:
    """Merge override keys (bpm, beat0_s, downbeat_offset, downbeat_shift). None values clear."""
    if not doc.get("grid"):
        raise ValueError("no grid to override; run analyze first")
    cur = dict(doc["grid"].get("override") or {})
    for k, v in override.items():
        if v is None:
            cur.pop(k, None)
        else:
            cur[k] = v
    doc["grid"]["override"] = cur or None
    eff = GridFit.from_dict(doc["grid"]).effective()
    doc["bars"] = {"bar0_beat": int(eff.downbeat_offset), "phrase0_bar": (doc.get("bars") or {}).get("phrase0_bar", 0)}


def mark_reviewed(doc: dict[str, Any], reviewed: bool = True) -> None:
    if not doc.get("grid"):
        raise ValueError("no grid to review; run analyze first")
    doc["grid"]["reviewed"] = bool(reviewed)
