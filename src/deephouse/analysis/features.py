"""Beat-synchronous features (directive P0.5) — the ``cache/analysis/{sha1}.npz`` contract.

Everything is aggregated *per grid beat* at native tempo. That aggregation is what buys
stretch invariance: once B is stretched to A's tempo, beat k of B lines up with beat k of A,
so all L1 scoring indexes these arrays directly with zero rendering.

Arrays (float32):
  mel_mix        [n_beats, 64]   log-mel dB, mean per beat
  mel_{stem}     [n_beats, 64]   same, per stem (present iff stems exist)
  rms_mix        [n_beats]       linear RMS per beat
  rms_{stem}     [n_beats]
  chroma         [n_beats, 12]   CQT chroma, median per beat, from the mix
  onset_env_beat [n_beats]       summed onset strength per beat (mix)
  beat_times     [n_beats]       float64 — the grid times these rows correspond to
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .grid import GridFit, grid_beat_times

STEMS = ("bass", "drums", "vocals", "other")
N_MELS = 64
HOP_MEL = 512
HOP_CHROMA = 2048


def _beat_index_for_frames(frame_t: np.ndarray, g: GridFit, n_beats: int) -> np.ndarray:
    idx = np.floor((frame_t - g.beat0_s) / g.period_s).astype(np.int64)
    idx[idx < 0] = -1
    idx[idx >= n_beats] = -1
    return idx


def _aggregate(X: np.ndarray, idx: np.ndarray, n_beats: int, how: str = "mean") -> np.ndarray:
    """Aggregate frame matrix ``X [F, T]`` into ``[n_beats, F]`` by beat index (``-1`` dropped)."""
    F = X.shape[0]
    valid = idx >= 0
    out = np.zeros((n_beats, F), dtype=np.float64)
    if how == "mean":
        counts = np.bincount(idx[valid], minlength=n_beats).astype(np.float64)
        np.add.at(out, idx[valid], X[:, valid].T)
        nz = counts > 0
        out[nz] /= counts[nz, None]
    elif how == "median":
        order = np.argsort(idx[valid], kind="stable")
        iv = idx[valid][order]
        Xv = X[:, valid][:, order]
        bounds = np.searchsorted(iv, np.arange(n_beats + 1))
        for b in range(n_beats):
            a, e = bounds[b], bounds[b + 1]
            if e > a:
                out[b] = np.median(Xv[:, a:e], axis=1)
    elif how == "sum":
        np.add.at(out, idx[valid], X[:, valid].T)
    else:
        raise ValueError(how)
    return out.astype(np.float32)


def compute_beat_features(sources: dict[str, np.ndarray], sr: int, g: GridFit) -> dict[str, np.ndarray]:
    """``sources`` must contain ``"mix"`` (mono float32) and may contain any of ``STEMS``."""
    import librosa

    if "mix" not in sources:
        raise ValueError("sources must include 'mix'")
    y = sources["mix"]
    duration = len(y) / sr
    beat_times = grid_beat_times(g, duration)
    n_beats = len(beat_times)
    out: dict[str, np.ndarray] = {"beat_times": beat_times.astype(np.float64)}

    for name, sig in sources.items():
        if name != "mix" and name not in STEMS:
            raise ValueError(f"unknown source {name!r}")
        sig = np.asarray(sig, dtype=np.float32)
        S = librosa.feature.melspectrogram(y=sig, sr=sr, n_fft=2048, hop_length=HOP_MEL, n_mels=N_MELS, power=2.0)
        logS = librosa.power_to_db(S + 1e-10)
        frame_t = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=HOP_MEL)
        idx = _beat_index_for_frames(frame_t, g, n_beats)
        out[f"mel_{name}"] = _aggregate(logS, idx, n_beats, "mean")
        rms = librosa.feature.rms(y=sig, frame_length=2048, hop_length=HOP_MEL)[0]
        # RMS per beat: root of mean power, not mean of RMS
        out[f"rms_{name}"] = np.sqrt(_aggregate((rms**2)[None, :], idx, n_beats, "mean")[:, 0])
        if name == "mix":
            oenv = librosa.onset.onset_strength(S=logS, sr=sr, hop_length=HOP_MEL)
            out["onset_env_beat"] = _aggregate(oenv[None, :], idx, n_beats, "sum")[:, 0]

    C = _chroma(sources, sr)
    frame_t = librosa.frames_to_time(np.arange(C.shape[1]), sr=sr, hop_length=HOP_CHROMA)
    idx = _beat_index_for_frames(frame_t, g, n_beats)
    out["chroma"] = _aggregate(C, idx, n_beats, "median")
    return out


CHROMA_SR = 22050


def _chroma(sources: dict[str, np.ndarray], sr: int) -> np.ndarray:
    """CQT chroma frames [12, T] at HOP_CHROMA (in the *original* sr's frame grid).

    Kicks (pitch sweeps, sub tails) and hats vote on key unless removed, so: with stems,
    chroma comes from bass + other + vocals (no drums); without, from the harmonic component
    of the mix (HPSS, hard margin). CQT starts at C2 so sub-bass thumps are excluded. Done at
    22.05 kHz — C2–B7 needs nothing above 4 kHz and it is 4× cheaper.
    """
    import librosa
    import soxr

    if all(k in sources for k in ("bass", "other", "vocals")):
        y = sources["bass"] + sources["other"] + sources["vocals"]
        y = soxr.resample(np.asarray(y, dtype=np.float32), sr, CHROMA_SR, quality="HQ")
    else:
        y = soxr.resample(np.asarray(sources["mix"], dtype=np.float32), sr, CHROMA_SR, quality="HQ")
        y = librosa.effects.harmonic(y, margin=8.0)
    hop = HOP_CHROMA * CHROMA_SR // sr
    return librosa.feature.chroma_cqt(y=y, sr=CHROMA_SR, hop_length=hop, n_chroma=12,
                                      fmin=librosa.note_to_hz("C2"), n_octaves=6)


def save_features(path: Path, feats: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".npz.tmp")
    with tmp.open("wb") as f:  # file object: numpy would otherwise append '.npz' to the tmp name
        np.savez_compressed(f, **feats)
    tmp.replace(path)


def load_features(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as z:
        return {k: z[k] for k in z.files}


def has_stems(stems_dir: Path) -> bool:
    return all((stems_dir / f"{s}.flac").exists() for s in STEMS)
