"""Search v0 tests on a synthetic library: ranking prefers the compatible track; throughput."""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf

from deephouse.config import load
from deephouse.synth import make_click_track


@pytest.fixture(scope="module")
def synth_library(tmp_path_factory, sr):
    """Seed A: 124 BPM A-minor straight. Library: near-identical twin (best), a 121 BPM
    swung twin (worse), a 116.5 BPM one (stretch too far → L0 reject)."""
    from deephouse.analysis.analyze import analyze_all
    from deephouse.ingest import ingest_path

    root = tmp_path_factory.mktemp("repo")
    for d in ("library/canonical", "cache/analysis", "cache/stems", "renders", "sets"):
        (root / d).mkdir(parents=True)
    src = tmp_path_factory.mktemp("src")
    (root / "deephouse.yaml").write_text((load(__import__("pathlib").Path(__file__).parents[1] / "deephouse.yaml").root / "deephouse.yaml").read_text())
    full = {"kick", "hats", "bass", "pad", "stab"}
    arr = [(8, {"hats", "pad"}), (24, full), (8, {"pad", "stab"}), (24, full), (8, {"kick", "hats"})]
    specs = {
        "seed_124":  dict(bpm=124.0, seed=1, swing=0.5),
        "twin_124":  dict(bpm=124.2, seed=2, swing=0.5),
        "swung_121": dict(bpm=121.0, seed=3, swing=0.60, hats="16ths"),
        "far_116":   dict(bpm=116.5, seed=4, swing=0.5),   # 124/116.5 = 6.4 % > 6 % limit
    }
    for name, kw in specs.items():
        y, _ = make_click_track(beat0_s=0.2, duration_s=150.0, sr=sr, style="house", arrangement=arr, snr_db=25, **kw)
        sf.write(str(src / f"{name}.wav"), y, sr, subtype="PCM_16")
    cfg = load(root / "deephouse.yaml")
    ingest_path(cfg, src, log=lambda *_: None)
    analyze_all(cfg, log=lambda *_: None)
    return cfg


def test_search_ranks_the_compatible_twin_first(synth_library):
    from deephouse.search.engine import load_library, search_next

    cfg = synth_library
    lib = load_library(cfg)
    assert len(lib) == 4
    seed = next(t for t in lib if "seed_124" in t.name)
    rep = search_next(cfg, seed, lib, top=200)
    assert rep.n_enumerated > 0
    names = [c.b.name for c in rep.ranked]
    assert not any("far_116" in n for n in names)                      # L0: > 6 % stretch
    assert "twin_124" in rep.ranked[0].b.name
    best_by_track = {}
    for c in rep.ranked:
        best_by_track.setdefault(c.b.name, c)
    twin, swung = best_by_track["twin_124.wav"], best_by_track["swung_121.wav"]
    assert twin.l1 > swung.l1
    assert swung.l1_features["swing_mismatch_ms"] > 15 and twin.l1_features["swing_mismatch_ms"] < 2
    assert twin.l1_features["stretch_penalty"] < swung.l1_features["stretch_penalty"]
    # every candidate carries its full feature vector (NORTHSTAR §5.3)
    assert all(set(c.l1_features) >= {"masking", "harmonic", "energy_step", "stretch_penalty"} for c in rep.ranked)
    # cues come from the structure stage and respect track length
    assert all(c.cue_out + c.recipe.overlap_bars <= seed.n_bars for c in rep.ranked)


def test_soft_camelot_mode_scores_instead_of_gating(synth_library):
    from deephouse.search.engine import l0_filter, load_library

    cfg = synth_library
    lib = load_library(cfg)
    a, b = lib[0], lib[1]
    cfg.raw["camelot"]["mode"] = "soft"
    ok, pen = l0_filter(a, b, cfg)
    assert ok and "key_penalty" in pen
    cfg.raw["camelot"]["mode"] = "hard"


def test_l1_throughput(synth_library):
    import time

    from deephouse.render.recipe import default_grid
    from deephouse.search.engine import enumerate_candidates, l1_score, load_library

    cfg = synth_library
    lib = load_library(cfg)
    seed = next(t for t in lib if "seed_124" in t.name)
    cands = enumerate_candidates(seed, lib, cfg, default_grid(), max_per_pair=10_000)
    # replicate to get a meaningful count
    cands = cands * max(1, 2000 // max(len(cands), 1))
    t0 = time.time()
    l1_score(seed, cands, cfg)
    rate = len(cands) / (time.time() - t0)
    assert rate > 500, f"L1 too slow: {rate:.0f} triples/s"
    assert np.isfinite([c.l1 for c in cands]).all()
