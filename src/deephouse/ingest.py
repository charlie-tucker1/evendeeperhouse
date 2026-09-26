"""Ingest (directive P0.1): decode anything ffmpeg reads → canonical FLAC + registry.

* Track identity is the SHA-1 of the *raw source bytes*. A re-encode is a new track.
* Tracks are canonicalised to 44.1 kHz / stereo / 16-bit FLAC (TPDF dither via ffmpeg's
  aresample, soxr resampler when the build has it).
* Recorded sets are registered but *not* canonicalised (they are hours long; the miner
  decodes them on the fly). NORTHSTAR §8: hoard sets as compressed audio.
* The registry (``library/registry.json``) maps sha1 → {source_path, kind, canonical, …}
  and is the only place paths live; every other artefact is keyed by sha1.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import Config

AUDIO_EXTS = {".mp3", ".m4a", ".mp4", ".wav", ".aiff", ".aif", ".flac", ".ogg", ".opus", ".webm", ".mkv"}


@dataclass
class RegistryEntry:
    sha1: str
    kind: str                      # "track" | "set"
    source_path: str
    canonical_path: str | None     # relative to repo root; None for sets
    duration_s: float | None
    ingested_at: float
    tags: list[str] = field(default_factory=list)


class Registry:
    def __init__(self, path: Path):
        self.path = path
        self.entries: dict[str, RegistryEntry] = {}
        if path.exists():
            with path.open() as f:
                raw = json.load(f)
            for sha, d in raw.get("entries", {}).items():
                self.entries[sha] = RegistryEntry(**d)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with tmp.open("w") as f:
            json.dump({"version": 1, "entries": {k: asdict(v) for k, v in self.entries.items()}}, f, indent=1, sort_keys=True)
        tmp.replace(self.path)

    def by_kind(self, kind: str) -> list[RegistryEntry]:
        return [e for e in self.entries.values() if e.kind == kind]

    def lookup(self, key: str) -> RegistryEntry | None:
        """Resolve a sha1, sha1 prefix, source path or canonical path."""
        if key in self.entries:
            return self.entries[key]
        pref = [e for s, e in self.entries.items() if s.startswith(key)]
        if len(pref) == 1:
            return pref[0]
        for e in self.entries.values():
            if key in (e.source_path, e.canonical_path) or Path(e.source_path).name == key:
                return e
        return None


def sha1_of_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def iter_audio_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        if root.suffix.lower() in AUDIO_EXTS:
            yield root
        return
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            yield p


def ffprobe_duration(ffmpeg_bin: str, path: Path) -> float | None:
    ffprobe = ffmpeg_bin.replace("ffmpeg", "ffprobe") if "ffmpeg" in ffmpeg_bin else "ffprobe"
    if shutil.which(ffprobe) is None:
        return None
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return float(out) if out else None
    except (subprocess.CalledProcessError, ValueError):
        return None


def _ffmpeg_has_soxr(ffmpeg_bin: str) -> bool:
    try:
        out = subprocess.run([ffmpeg_bin, "-hide_banner", "-buildconf"], capture_output=True, text=True).stdout
        return "--enable-libsoxr" in out
    except OSError:
        return False


def canonicalize(ffmpeg_bin: str, src: Path, dst: Path, sr: int = 44100, channels: int = 2) -> None:
    """Decode → resample (soxr if available) → TPDF dither → 16-bit FLAC. Idempotent."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp.flac")
    resampler = "soxr" if _ffmpeg_has_soxr(ffmpeg_bin) else "swr"
    af = f"aresample=resampler={resampler}:osr={sr}:dither_method=triangular"
    cmd = [
        ffmpeg_bin, "-y", "-v", "error", "-nostdin", "-i", str(src), "-vn", "-map_metadata", "-1",
        "-ac", str(channels), "-af", af, "-sample_fmt", "s16", "-c:a", "flac", "-compression_level", "5", str(tmp),
    ]
    subprocess.run(cmd, check=True)
    tmp.replace(dst)


def ingest_path(cfg: Config, root: Path, kind: str = "track", tags: list[str] | None = None,
                force: bool = False, log=print) -> list[RegistryEntry]:
    """Ingest every audio file under ``root``. Returns the entries touched."""
    if kind not in ("track", "set"):
        raise ValueError("kind must be 'track' or 'set'")
    reg = Registry(cfg.path("registry"))
    canon_dir = cfg.path("library_canonical")
    ffmpeg_bin = cfg.audio.ffmpeg_bin
    sr, ch = int(cfg.audio.sample_rate), int(cfg.audio.channels)
    touched: list[RegistryEntry] = []
    files = list(iter_audio_files(root))
    log(f"[ingest] {len(files)} audio file(s) under {root} as kind={kind}")
    for i, src in enumerate(files, 1):
        sha = sha1_of_file(src)
        existing = reg.entries.get(sha)
        if existing and not force and (kind == "set" or (existing.canonical_path and (cfg.root / existing.canonical_path).exists())):
            log(f"  [{i}/{len(files)}] skip (already ingested) {src.name} -> {sha[:10]}")
            touched.append(existing)
            continue
        canonical_rel: str | None = None
        if kind == "track":
            dst = canon_dir / f"{sha}.flac"
            t0 = time.time()
            canonicalize(ffmpeg_bin, src, dst, sr=sr, channels=ch)
            canonical_rel = str(dst.relative_to(cfg.root))
            log(f"  [{i}/{len(files)}] {src.name} -> {sha[:10]}.flac ({time.time() - t0:.1f}s)")
        else:
            log(f"  [{i}/{len(files)}] registered set {src.name} -> {sha[:10]}")
        entry = RegistryEntry(
            sha1=sha, kind=kind, source_path=str(src.resolve()), canonical_path=canonical_rel,
            duration_s=ffprobe_duration(ffmpeg_bin, src), ingested_at=time.time(), tags=list(tags or []),
        )
        reg.entries[sha] = entry
        touched.append(entry)
        reg.save()  # save incrementally: a crash mid-batch loses nothing
    return touched


def audio_path_for(cfg: Config, entry: RegistryEntry) -> Path:
    """The file analysis should read: canonical FLAC for tracks, the source for sets."""
    if entry.canonical_path:
        return cfg.root / entry.canonical_path
    return Path(entry.source_path)
