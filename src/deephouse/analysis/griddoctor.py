"""griddoctor (directive P0.3): make a bad grid *audible* and *visible*, and let a human fix it.

Outputs, per track, into ``griddoctor_out/{sha1[:10]}_{name}/``:
  * ``click.wav``   — excerpt with clicks at fitted beats (1 kHz) and accented downbeats (1.5 kHz).
                      If the grid is right, clicks sit exactly on the kicks and the accents on the 1.
  * ``grid.png``    — three panels: onset envelope with grid lines; folded energy profile
                      (on-beat vs anti-beat); tracker-beat residuals vs the fitted grid.
  * ``report.txt``  — the fit's diagnostics and flags.

Overrides are written into the analysis sidecar (``grid.override``) and applied by
``GridFit.effective()`` everywhere downstream. A wrong grid silently poisons every later
phase, so this tool is non-negotiable (NORTHSTAR invariant 1 & doctrine §1.7).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..audio import load_audio, write_wav
from ..config import Config
from ..ingest import Registry, RegistryEntry, audio_path_for
from . import store
from .grid import GridFit, _fold_energy, grid_beat_times


@dataclass
class DoctorOutput:
    out_dir: Path
    click_wav: Path
    png: Path
    report: Path
    grid: GridFit


def _click(sr: int, freq: float, dur_s: float = 0.03, decay_s: float = 0.006) -> np.ndarray:
    t = np.arange(int(dur_s * sr)) / sr
    return (np.sin(2 * np.pi * freq * t) * np.exp(-t / decay_s)).astype(np.float32)


def render_click_overlay(y: np.ndarray, sr: int, g: GridFit, t_start: float, click_hz: float,
                         down_hz: float, click_gain_db: float) -> np.ndarray:
    """Mix clicks at grid beats into excerpt ``y`` (stereo or mono) that begins at ``t_start``."""
    n = len(y)
    dur = n / sr
    beats_all = grid_beat_times(g, duration_s=t_start + dur + 1.0)
    sel = (beats_all >= t_start) & (beats_all < t_start + dur)
    beats_abs = beats_all[sel]
    idx = np.round((beats_abs - g.beat0_s) / g.period_s).astype(int)
    down = (idx - g.downbeat_offset) % 4 == 0
    gain = 10 ** (click_gain_db / 20)
    c, cd = _click(sr, click_hz), _click(sr, down_hz, dur_s=0.045, decay_s=0.009)
    out = y.astype(np.float32).copy()
    if out.ndim == 1:
        out = out[:, None]
    for tb, is_down in zip(beats_abs, down, strict=True):
        at = int(round((tb - t_start) * sr))
        s = cd if is_down else c
        s = s * (gain * (1.4 if is_down else 1.0))
        end = min(n, at + len(s))
        if at < n:
            out[at:end, :] += s[: end - at, None]
    return np.clip(out, -1.0, 1.0)


def _diagnostic_png(path: Path, y_mono: np.ndarray, sr: int, g: GridFit, t_start: float, tracker_beats: np.ndarray | None, title: str) -> None:
    import librosa
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    hop = 256
    oenv = librosa.onset.onset_strength(y=y_mono, sr=sr, hop_length=hop)
    t = librosa.frames_to_time(np.arange(len(oenv)), sr=sr, hop_length=hop) + t_start
    beats = grid_beat_times(g, t[-1] + 1.0)
    beats = beats[(beats >= t[0]) & (beats <= t[-1])]
    kidx = np.round((beats - g.beat0_s) / g.period_s).astype(int)
    is_down = (kidx - g.downbeat_offset) % 4 == 0

    fig, axes = plt.subplots(3, 1, figsize=(14, 9), constrained_layout=True)
    fig.suptitle(title, fontsize=11)

    # 1. onset envelope with grid lines (zoom to the first 8 bars so beats are legible)
    ax = axes[0]
    zoom_end = t_start + min(8 * 4 * g.period_s, t[-1] - t_start)
    m = t <= zoom_end
    ax.plot(t[m], oenv[m], lw=0.8, color="0.25")
    for b, d in zip(beats, is_down, strict=True):
        if b <= zoom_end:
            ax.axvline(b, color="C3" if d else "C0", lw=1.6 if d else 0.8, alpha=0.95 if d else 0.8)
    ax.set_title(f"onset envelope, first 8 bars of excerpt — red = downbeat (offset {g.downbeat_offset}), blue = beat")
    ax.set_xlim(t_start, zoom_end)
    ax.set_ylabel("onset strength")

    # 2. folded energy: on-beat vs anti-beat profile over ±60 ms
    ax = axes[1]
    W = 0.060
    prof_on = _fold_energy(y_mono, sr, g.period_s, (g.beat0_s - t_start) % g.period_s, W)
    prof_off = _fold_energy(y_mono, sr, g.period_s, (g.beat0_s - t_start + g.period_s / 2) % g.period_s, W)
    tt = (np.arange(len(prof_on)) / sr - W) * 1000
    ax.plot(tt, prof_on / (prof_on.max() or 1), label="folded energy at grid beats", color="C3")
    ax.plot(tt, prof_off / (prof_on.max() or 1), label="at anti-beats (+½ period)", color="0.5", lw=0.9)
    ax.axvline(0, color="k", lw=0.8, ls="--")
    ax.set_xlabel("ms relative to grid beat")
    ax.set_ylabel("energy (norm.)")
    ax.set_title("time-domain fold — a correct grid has a sharp rise at 0 ms on the red curve and little on the grey")
    ax.legend(loc="upper right", fontsize=8)

    # 3. tracker residuals vs fitted grid
    ax = axes[2]
    if tracker_beats is not None and len(tracker_beats):
        k = np.round((tracker_beats - g.beat0_s) / g.period_s)
        res = (tracker_beats - (g.beat0_s + k * g.period_s)) * 1000
        ax.scatter(tracker_beats, res, s=6, color="C0")
        ax.axhline(0, color="k", lw=0.8)
        for lim in (30, -30):
            ax.axhline(lim, color="C3", lw=0.6, ls=":")
        ax.set_ylim(-60, 60)
        ax.set_title(f"tracker-beat residuals vs fitted grid (ms) — flat = constant tempo (a constant offset is just tracker latency); a slope = tempo drift → not DAW-quantised; rms {g.residual_rms_ms:.1f} ms")
    else:
        ax.text(0.5, 0.5, "tracker residuals unavailable (cached grid)", ha="center", va="center", transform=ax.transAxes)
    ax.set_xlabel("time (s)")
    fig.savefig(path, dpi=110)
    plt.close(fig)


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)[:48]


def run_griddoctor(cfg: Config, entry: RegistryEntry, out_root: Path | None = None,
                   rerun_tracker: bool = True) -> DoctorOutput:
    doc = store.load_analysis(cfg, entry.sha1)
    if not doc or not doc.get("grid"):
        raise SystemExit(f"no grid for {entry.sha1[:10]} — run `deephouse analyze` first")
    g = store.get_grid(doc)  # override applied
    path = audio_path_for(cfg, entry)
    gd = cfg.griddoctor
    sr = int(cfg.audio.sample_rate)
    dur_total = float(doc.get("duration_s") or 0.0)
    exc = float(gd.excerpt_seconds)
    t_start = max(0.0, min(float(gd.excerpt_offset_frac) * dur_total, max(dur_total - exc, 0.0)))
    # snap the excerpt start to a downbeat so the accent pattern is obvious from the first bar
    k0 = int(np.ceil((t_start - g.beat0_s) / g.period_s))
    k0 += (g.downbeat_offset - k0) % 4
    t_start = g.beat0_s + k0 * g.period_s

    y, sr = load_audio(path, sr=sr, offset_s=t_start, duration_s=exc)
    y_mono = y.mean(axis=1) if y.ndim == 2 else y

    out_dir = (out_root or (cfg.root / "griddoctor_out")) / f"{entry.sha1[:10]}_{_slug(Path(entry.source_path).stem)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    click = render_click_overlay(y, sr, g, t_start, float(gd.click_freq_hz), float(gd.downbeat_click_freq_hz), float(gd.click_gain_db))
    click_wav = out_dir / "click.wav"
    write_wav(click_wav, click, sr, subtype="PCM_16")

    tracker_beats = None
    if rerun_tracker:
        from . import trackers

        est = trackers.track(y_mono, sr, backend=cfg.grid.tracker, start_bpm=g.bpm)
        tracker_beats = np.asarray(est.beats_s) + t_start

    title = (f"{Path(entry.source_path).name}  |  {g.bpm:.3f} BPM  beat0 {g.beat0_s:.3f}s  downbeat_offset {g.downbeat_offset}  "
             f"conf {g.confidence:.2f}  flags {g.flags or '—'}" + ("  [OVERRIDE ACTIVE]" if g.override else ""))
    png = out_dir / "grid.png"
    _diagnostic_png(png, y_mono, sr, g, t_start, tracker_beats, title)

    report = out_dir / "report.txt"
    lines = [title, "", f"excerpt: {t_start:.2f}s – {t_start + exc:.2f}s (starts on a downbeat)", "",
             "grid:"] + [f"  {k}: {v}" for k, v in g.to_dict().items()] + [
             "", "listen: clicks (1 kHz) must sit on the kicks; accents (1.5 kHz) on the 1.",
             "fix:    deephouse griddoctor <track> --downbeat-shift N | --bpm X | --beat0 X | --accept | --clear-override"]
    report.write_text("\n".join(lines))
    return DoctorOutput(out_dir=out_dir, click_wav=click_wav, png=png, report=report, grid=g)


def apply_override(cfg: Config, entry: RegistryEntry, bpm: float | None = None, beat0_s: float | None = None,
                   downbeat_offset: int | None = None, downbeat_shift: int | None = None,
                   accept: bool = False, clear: bool = False) -> GridFit:
    doc = store.load_analysis(cfg, entry.sha1)
    if not doc or not doc.get("grid"):
        raise SystemExit(f"no grid for {entry.sha1[:10]} — run `deephouse analyze` first")
    if clear:
        doc["grid"]["override"] = None
    changes = {k: v for k, v in dict(bpm=bpm, beat0_s=beat0_s, downbeat_offset=downbeat_offset).items() if v is not None}
    if downbeat_shift:
        # fold a shift into an absolute downbeat_offset so repeated shifts compose predictably
        cur = store.get_grid(doc)
        changes["downbeat_offset"] = (cur.downbeat_offset + int(downbeat_shift)) % 4
    if changes:
        store.set_grid_override(doc, **changes)
    if accept:
        store.mark_reviewed(doc, True)
    store.save_analysis(cfg, entry.sha1, doc)
    return store.get_grid(doc)


def resolve_entry(cfg: Config, key: str) -> RegistryEntry:
    reg = Registry(cfg.path("registry"))
    e = reg.lookup(key)
    if e is None:
        raise SystemExit(f"track not found in registry: {key!r}")
    return e
