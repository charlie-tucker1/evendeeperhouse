"""TransitionRecipe (directive §3): a versioned, serialisable description of *how* to blend.

v1 is a small fixed grid (16 combinations). NORTHSTAR §4 requires it to stay evolvable into a
list-of-ops program, so: every field has a default, unknown keys are rejected loudly, the
``version`` is stored, and ``ops`` is reserved (empty in v1) for the program representation.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import asdict, dataclass, field
from typing import Any

ENTRY_CURVES = ("equal_power", "stepped")
VOCAL_RULES = ("duck_A", "none")
TEMPO_POLICIES = ("stretch_B_to_A",)
SIDECHAIN_SOURCES = ("none", "A_kick")


@dataclass(frozen=True)
class TransitionRecipe:
    version: int = 1
    overlap_bars: int = 16
    entry_curve: str = "equal_power"
    bass_swap_frac: float = 0.5
    entry_hpf_sweep: bool = False
    vocal_rule: str = "duck_A"
    tempo_policy: str = "stretch_B_to_A"
    # v1.1 ops (docs/GROOVE.md §4) — accepted, default off, not yet rendered
    groove_transfer: bool = False
    sidechain_source: str = "none"
    ops: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.overlap_bars not in (8, 16, 32):
            raise ValueError("overlap_bars must be 8, 16 or 32")
        if self.entry_curve not in ENTRY_CURVES:
            raise ValueError(f"entry_curve must be one of {ENTRY_CURVES}")
        if not 0.0 < self.bass_swap_frac < 1.0:
            raise ValueError("bass_swap_frac must be in (0, 1)")
        if self.vocal_rule not in VOCAL_RULES:
            raise ValueError(f"vocal_rule must be one of {VOCAL_RULES}")
        if self.tempo_policy not in TEMPO_POLICIES:
            raise ValueError(f"tempo_policy must be one of {TEMPO_POLICIES}")
        if self.sidechain_source not in SIDECHAIN_SOURCES:
            raise ValueError(f"sidechain_source must be one of {SIDECHAIN_SOURCES}")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ops"] = list(self.ops)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TransitionRecipe:
        known = set(cls.__dataclass_fields__)
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"unknown recipe keys {sorted(unknown)} (recipe version {d.get('version')})")
        d = dict(d)
        d["ops"] = tuple(d.get("ops") or ())
        return cls(**d)

    @property
    def key(self) -> str:
        """Short stable id, e.g. ``ov16_eqp_bs50_hpf0``."""
        return (f"ov{self.overlap_bars}_{'eqp' if self.entry_curve == 'equal_power' else 'stp'}"
                f"_bs{int(round(self.bass_swap_frac * 100)):02d}_hpf{int(self.entry_hpf_sweep)}"
                + ("_gt" if self.groove_transfer else "") + ("_sc" if self.sidechain_source != "none" else ""))

    @property
    def digest(self) -> str:
        return hashlib.sha1(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:10]


def default_grid() -> list[TransitionRecipe]:
    """The v1 2×2×2×2 grid = 16 recipes."""
    out = []
    for ov, curve, bs, hpf in itertools.product((16, 32), ENTRY_CURVES, (0.5, 0.75), (False, True)):
        out.append(TransitionRecipe(overlap_bars=ov, entry_curve=curve, bass_swap_frac=bs, entry_hpf_sweep=hpf))
    return out
