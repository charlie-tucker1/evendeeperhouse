"""The renderer (directive Phase 1): a pure function from (A, cue_out, B, cue_in, recipe, cfg)
to audio + metadata. No hidden state, no randomness, no ambient config: given the same inputs
it returns bit-identical output (golden-file tested). It is the *simulator* every later phase
searches against (NORTHSTAR §5.1).

Timeline (all in A's tempo; B is stretched to it):

    |<- lead_in bars ->|<------- overlap bars ------->|<---- tail bars ---->|
    A alone            A fading out / B fading in       B alone
                       ^ A's cue_out downbeat == B's cue_in downbeat (sample-exact)

Signal paths:
  stems   — when both tracks have 4 stems: per-stem gains, real bass swap, vocal duck.
  bands   — otherwise: LR4 split at ``cfg.render.split_hz``; the low band is swapped.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..analysis.grid import GridFit
from . import dsp
from .recipe import TransitionRecipe

STEM_NAMES = ("bass", "drums", "vocals", "other")


@dataclass
class Track:
    """In-memory track: stereo float32 audio at ``sr`` plus its effective grid; optional stems."""

    sha1: str
    audio: np.ndarray                 # [n, 2]
    sr: int
    grid: GridFit
    stems: dict[str, np.ndarray] | None = None   # each [n, 2], same sr

    def __post_init__(self) -> None:
        if self.audio.ndim != 2 or self.audio.shape[1] != 2:
            raise ValueError("Track.audio must be [n, 2]")
        if self.stems is not None and set(self.stems) != set(STEM_NAMES):
            raise ValueError(f"stems must be exactly {STEM_NAMES}")

    def bar_time(self, bar: int) -> float:
        g = self.grid
        return g.beat0_s + (g.downbeat_offset + 4 * bar) * g.period_s

    @property
    def n_bars(self) -> int:
        g = self.grid
        return int((len(self.audio) / self.sr - g.beat0_s - g.downbeat_offset * g.period_s) // (4 * g.period_s))


@dataclass
class RenderConfig:
    lead_in_bars: int = 16
    tail_bars: int = 32
    split_hz: float = 120.0
    target_lufs: float = -9.0
    ceiling_dbtp: float = -1.0
    hpf_sweep_from_hz: float = 250.0
    hpf_sweep_to_hz: float = 20.0
    vocal_active_frac: float = 0.35        # bar vocal RMS / track vocal RMS p95 above this = "active"
    stretch_backend: str = "auto"
    master: bool = True

    def digest(self) -> str:
        return hashlib.sha1(json.dumps(self.__dict__, sort_keys=True).encode()).hexdigest()[:10]


@dataclass
class RenderResult:
    audio: np.ndarray                 # [n, 2] float32
    sr: int
    meta: dict[str, Any] = field(default_factory=dict)


class RenderError(ValueError):
    pass


# ----------------------------------------------------------------------------- helpers


def _cut(y: np.ndarray, s: int, e: int) -> np.ndarray:
    """Slice with zero padding outside [0, len)."""
    n = len(y)
    out = np.zeros((e - s, y.shape[1]), dtype=np.float32)
    a, b = max(s, 0), min(e, n)
    if b > a:
        out[a - s:b - s] = y[a:b]
    return out


def _bar_rms(y: np.ndarray, bar_len: int) -> np.ndarray:
    n_bars = len(y) // bar_len
    if n_bars == 0:
        return np.zeros(0)
    seg = y[: n_bars * bar_len].reshape(n_bars, bar_len, -1)
    return np.sqrt((seg**2).mean(axis=(1, 2)))


# ----------------------------------------------------------------------------- main


def render(a: Track, cue_out_bar: int, b: Track, cue_in_bar: int, recipe: TransitionRecipe,
           cfg: RenderConfig | None = None) -> RenderResult:
    t_wall = time.time()
    cfg = cfg or RenderConfig()
    if a.sr != b.sr:
        raise RenderError("A and B must share a sample rate")
    sr = a.sr
    ga, gb = a.grid, b.grid
    rate = ga.bpm / gb.bpm                                   # B playback speed to match A
    if abs(np.log2(rate)) > np.log2(1.06) + 1e-9:
        raise RenderError(f"stretch ratio {rate:.4f} exceeds ±6 % — reject upstream")

    ov, lead, tail = recipe.overlap_bars, cfg.lead_in_bars, cfg.tail_bars
    bar_len = 4 * ga.period_s                                # seconds, A tempo
    n_bar = int(round(bar_len * sr))                         # samples per bar (A tempo) — the master clock
    n_beat = n_bar // 4
    n_lead, n_ov, n_tail = lead * n_bar, ov * n_bar, tail * n_bar
    n_total = n_lead + n_ov + n_tail

    # ---- A: [cue_out - lead, cue_out + overlap) in A samples, sample-exact from the grid
    a_start = int(round((a.bar_time(cue_out_bar) - lead * bar_len) * sr))
    a_seg = _cut(a.audio, a_start, a_start + n_lead + n_ov)
    a_stems = {k: _cut(v, a_start, a_start + n_lead + n_ov) for k, v in a.stems.items()} if a.stems else None

    # ---- B: [cue_in - pad, cue_in + (overlap + tail) bars + pad) in B time, stretched by ``rate``
    pad_bars = 1
    b_bar_len_native = 4 * gb.period_s
    b_t0 = b.bar_time(cue_in_bar) - pad_bars * b_bar_len_native
    b_t1 = b.bar_time(cue_in_bar) + (ov + tail + pad_bars) * b_bar_len_native
    b_s0, b_s1 = int(round(b_t0 * sr)), int(round(b_t1 * sr))

    def stretch_cut(y: np.ndarray) -> np.ndarray:
        raw = _cut(y, b_s0, b_s1)
        st = dsp.time_stretch(raw, sr, rate, backend=cfg.stretch_backend)
        # after stretching, the cue_in downbeat sits at pad_bars * n_bar (A-tempo bars)
        off = pad_bars * n_bar
        return _cut(st, off, off + n_ov + n_tail)

    b_seg = stretch_cut(b.audio)
    b_stems = {k: stretch_cut(v) for k, v in b.stems.items()} if b.stems else None
    use_stems = a_stems is not None and b_stems is not None

    # ---- full-band crossfade gains over the overlap
    if recipe.entry_curve == "equal_power":
        fo, fi = dsp.equal_power_pair(n_ov)
    else:
        fo, fi = dsp.stepped_entry_pair(n_ov)
    gA = np.concatenate([np.ones(n_lead, np.float32), fo])                      # len n_lead + n_ov
    gB = np.concatenate([fi, np.ones(n_tail, np.float32)])                      # len n_ov + n_tail

    # ---- bass swap: the low band does NOT follow the crossfade. A's bass stays at unity until
    #      the swap bar (a DJ keeps the outgoing bass full, then hands over in one motion), and the
    #      handover is an equal-power crossfade over one beat centred on the swap downbeat, so the
    #      two uncorrelated bass lines sum to constant power instead of notching at the crossing.
    swap_bar = int(round(recipe.bass_swap_frac * ov))
    swap_at_A = n_lead + swap_bar * n_bar                                       # in A-seg coords
    swap_at_B = swap_bar * n_bar                                                # in B-seg coords
    fo_sw, fi_sw = dsp.equal_power_pair(n_beat)
    lowA = np.ones(n_lead + n_ov, np.float32)
    lowA[swap_at_A - n_beat // 2: swap_at_A - n_beat // 2 + n_beat] = fo_sw
    lowA[swap_at_A - n_beat // 2 + n_beat:] = 0.0
    lowB = np.zeros(n_ov + n_tail, np.float32)
    lowB[swap_at_B - n_beat // 2: swap_at_B - n_beat // 2 + n_beat] = fi_sw
    lowB[swap_at_B - n_beat // 2 + n_beat:] = 1.0

    # ---- optional HPF sweep on B's entry (non-low content), first half of the overlap
    def hpf_sweep(y: np.ndarray) -> np.ndarray:
        if not recipe.entry_hpf_sweep:
            return y
        half = (ov // 2) * n_bar
        n_blocks = max(half // n_beat, 1)
        cut = np.geomspace(cfg.hpf_sweep_from_hz, cfg.hpf_sweep_to_hz, n_blocks)
        head = dsp.sweep_filter(y[:half], sr, cut, n_beat, kind="hpf")
        return np.concatenate([head, y[half:]], axis=0)

    # ---- build A and B contributions
    vocal_duck_bars: list[int] = []
    if use_stems:
        assert a_stems is not None and b_stems is not None
        A_low = a_stems["bass"] * lowA[:, None]
        A_rest = (a_stems["drums"] + a_stems["other"]) * gA[:, None]
        A_voc = a_stems["vocals"] * gA[:, None]
        if recipe.vocal_rule == "duck_A":
            # both vocal stems active in the same overlap bar -> mute A's vocal for that bar
            ra = _bar_rms(a_stems["vocals"], n_bar)
            rb = _bar_rms(b_stems["vocals"], n_bar)
            thr_a = cfg.vocal_active_frac * (np.percentile(_bar_rms(a.stems["vocals"], n_bar), 95) or 1.0)
            thr_b = cfg.vocal_active_frac * (np.percentile(_bar_rms(b.stems["vocals"], n_bar), 95) or 1.0)
            duck = np.ones(n_lead + n_ov, np.float32)
            for i in range(ov):
                ia, ib = lead + i, i
                if ia < len(ra) and ib < len(rb) and ra[ia] > thr_a and rb[ib] > thr_b:
                    vocal_duck_bars.append(i)
                    s = ia * n_bar
                    duck[s:s + n_bar] = 0.0
            # 50 ms ramps so the mute never clicks
            k = int(0.05 * sr)
            duck = np.convolve(duck, np.ones(k) / k, mode="same").astype(np.float32)
            A_voc = A_voc * duck[:, None]
        A_out = A_low + A_rest + A_voc
        B_low = b_stems["bass"] * lowB[:, None]
        B_rest = hpf_sweep(b_stems["drums"] + b_stems["other"] + b_stems["vocals"]) * gB[:, None]
        B_out = B_low + B_rest
        path = "stems"
    else:
        a_lo, a_hi = dsp.lr4_split(a_seg, sr, cfg.split_hz)
        b_lo, b_hi = dsp.lr4_split(b_seg, sr, cfg.split_hz)
        A_out = a_lo * lowA[:, None] + a_hi * gA[:, None]
        B_out = b_lo * lowB[:, None] + hpf_sweep(b_hi) * gB[:, None]
        path = "bands"

    # ---- program-gain match: B's solo tail vs A's solo lead-in (integrated LUFS)
    lufs_a = dsp.integrated_lufs(A_out[:n_lead], sr)
    lufs_b = dsp.integrated_lufs(B_out[n_ov:], sr)
    b_trim_db = float(np.clip(lufs_a - lufs_b, -12.0, 12.0)) if np.isfinite(lufs_a) and np.isfinite(lufs_b) else 0.0
    B_out = B_out * np.float32(10 ** (b_trim_db / 20))

    # ---- sum on the master timeline
    mix = np.zeros((n_total, 2), dtype=np.float32)
    mix[: n_lead + n_ov] += A_out
    mix[n_lead:] += B_out

    master_trim_db = 0.0
    if cfg.master:
        lufs_mix = dsp.integrated_lufs(mix, sr)
        if np.isfinite(lufs_mix):
            master_trim_db = float(cfg.target_lufs - lufs_mix)
            mix = mix * np.float32(10 ** (master_trim_db / 20))
        mix = dsp.limiter(mix, sr, ceiling_db=cfg.ceiling_dbtp - 0.3)   # 0.3 dB inter-sample headroom

    meta = {
        "render_version": 1,
        "a": a.sha1, "b": b.sha1, "cue_out_bar": cue_out_bar, "cue_in_bar": cue_in_bar,
        "recipe": recipe.to_dict(), "recipe_key": recipe.key, "config": cfg.__dict__, "config_digest": cfg.digest(),
        "path": path, "stretch_rate": rate, "stretch_backend": cfg.stretch_backend,
        "bpm": ga.bpm, "samples_per_bar": n_bar,
        "overlap_start_sample": n_lead, "overlap_end_sample": n_lead + n_ov, "bass_swap_sample": n_lead + swap_bar * n_bar,
        "vocal_duck_bars": vocal_duck_bars,
        "lufs_a_lead_in": lufs_a, "lufs_b_tail_solo": lufs_b, "b_trim_db": b_trim_db, "master_trim_db": master_trim_db,
        "n_samples": n_total, "wall_s": time.time() - t_wall,
    }
    return RenderResult(audio=mix, sr=sr, meta=meta)
