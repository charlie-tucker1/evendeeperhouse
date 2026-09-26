"""Audio I/O helpers. Everything downstream works in float32, [-1, 1]."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf


def load_audio(path: Path, sr: int | None = None, mono: bool = False, offset_s: float = 0.0,
               duration_s: float | None = None, ffmpeg_bin: str = "ffmpeg") -> tuple[np.ndarray, int]:
    """Load audio as float32. Shape ``[n, ch]`` (or ``[n]`` if mono).

    Uses soundfile for formats it understands (FLAC/WAV/OGG); falls back to ffmpeg
    decoding to raw float for everything else (mp3/m4a/mp4). Optional resample via soxr.
    """
    path = Path(path)
    try:
        with sf.SoundFile(str(path)) as f:
            file_sr = f.samplerate
            start = int(round(offset_s * file_sr))
            frames = -1 if duration_s is None else int(round(duration_s * file_sr))
            f.seek(start)
            y = f.read(frames=frames, dtype="float32", always_2d=True)
    except (sf.LibsndfileError, RuntimeError):
        y, file_sr = _load_via_ffmpeg(path, offset_s, duration_s, ffmpeg_bin)

    if sr is not None and sr != file_sr:
        import soxr

        y = soxr.resample(y, file_sr, sr, quality="HQ").astype(np.float32)
        file_sr = sr
    if mono and y.ndim == 2:
        y = y.mean(axis=1).astype(np.float32)
    return y, file_sr


def _load_via_ffmpeg(path: Path, offset_s: float, duration_s: float | None, ffmpeg_bin: str) -> tuple[np.ndarray, int]:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate,channels",
         "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True,
    ).stdout.split()
    file_sr, ch = int(probe[0]), int(probe[1])
    cmd = [ffmpeg_bin, "-v", "error", "-nostdin"]
    if offset_s:
        cmd += ["-ss", f"{offset_s:.6f}"]
    cmd += ["-i", str(path)]
    if duration_s is not None:
        cmd += ["-t", f"{duration_s:.6f}"]
    cmd += ["-vn", "-f", "f32le", "-acodec", "pcm_f32le", "-ac", str(ch), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    y = np.frombuffer(raw, dtype=np.float32).reshape(-1, ch)
    return y, file_sr


def write_wav(path: Path, y: np.ndarray, sr: int, subtype: str = "PCM_24") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.clip(y, -1.0, 1.0), sr, subtype=subtype)


def duration_of(path: Path) -> float:
    try:
        info = sf.info(str(path))
        return info.frames / info.samplerate
    except (sf.LibsndfileError, RuntimeError):
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return float(out)
