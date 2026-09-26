"""Camelot wheel: key <-> Camelot code mapping and DJ compatibility policy.

Camelot layout (Mixed In Key convention):
  number = position on the circle of fifths, 1..12
  letter = 'A' for minor, 'B' for major
  Relative major/minor share the same number (e.g. 8A = A minor, 8B = C major).
  Adjacent numbers (±1, wrapping 12<->1) are a fifth apart and mix cleanly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Pitch class (0=C) for each Camelot number, minor (A) and major (B).
# 1A = Ab minor ... derived from the circle of fifths starting at 1B = B major.
_MINOR_PC_BY_NUMBER = {
    1: 8,   # Ab/G# minor
    2: 3,   # Eb minor
    3: 10,  # Bb minor
    4: 5,   # F minor
    5: 0,   # C minor
    6: 7,   # G minor
    7: 2,   # D minor
    8: 9,   # A minor
    9: 4,   # E minor
    10: 11, # B minor
    11: 6,  # F# minor
    12: 1,  # Db/C# minor
}
_MAJOR_PC_BY_NUMBER = {n: (pc + 3) % 12 for n, pc in _MINOR_PC_BY_NUMBER.items()}

PITCH_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PITCH_NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

_NAME_TO_PC = {}
for _i, (_s, _f) in enumerate(zip(PITCH_NAMES_SHARP, PITCH_NAMES_FLAT, strict=True)):
    _NAME_TO_PC[_s.lower()] = _i
    _NAME_TO_PC[_f.lower()] = _i


@dataclass(frozen=True)
class Camelot:
    number: int  # 1..12
    letter: str  # 'A' minor, 'B' major

    def __post_init__(self) -> None:
        if not 1 <= self.number <= 12:
            raise ValueError(f"Camelot number out of range: {self.number}")
        if self.letter not in ("A", "B"):
            raise ValueError(f"Camelot letter must be A or B, got {self.letter!r}")

    @property
    def code(self) -> str:
        return f"{self.number}{self.letter}"

    @property
    def is_minor(self) -> bool:
        return self.letter == "A"

    @property
    def pitch_class(self) -> int:
        table = _MINOR_PC_BY_NUMBER if self.is_minor else _MAJOR_PC_BY_NUMBER
        return table[self.number]

    @property
    def key_name(self) -> str:
        mode = "minor" if self.is_minor else "major"
        return f"{PITCH_NAMES_SHARP[self.pitch_class]} {mode}"

    def __str__(self) -> str:
        return self.code


def parse(code: str) -> Camelot:
    """Parse '8A' / '12b' style codes."""
    code = code.strip().upper()
    if len(code) < 2:
        raise ValueError(f"bad Camelot code {code!r}")
    return Camelot(int(code[:-1]), code[-1])


def from_key(pitch_class: int, minor: bool) -> Camelot:
    table = _MINOR_PC_BY_NUMBER if minor else _MAJOR_PC_BY_NUMBER
    for n, pc in table.items():
        if pc == pitch_class % 12:
            return Camelot(n, "A" if minor else "B")
    raise ValueError(f"unreachable: pitch class {pitch_class}")


_KEY_RE = re.compile(
    r"^\s*(?P<root>[a-g](?:#|b)?)\s*(?P<mode>minor|min|m|major|maj)?\s*$", re.IGNORECASE
)


def from_key_name(name: str) -> Camelot:
    """'A minor', 'Am', 'C major', 'C', 'F# min', 'Dbmaj' -> Camelot.

    Bare root (no mode) is treated as major. Note 'b' after the root is a flat,
    so 'Bb' is B-flat major and 'Bbm' is B-flat minor.
    """
    m = _KEY_RE.match(name.replace("-", " "))
    if not m:
        raise ValueError(f"unrecognized key name {name!r}")
    root = m.group("root").lower()
    root = root[0].upper() + root[1:]  # normalise 'bb' -> 'Bb', 'f#' -> 'F#'
    mode = (m.group("mode") or "major").lower()
    minor = mode in ("minor", "min", "m")
    pc = _NAME_TO_PC[root.lower()]
    return from_key(pc, minor)


def move(c: Camelot, delta_number: int = 0, flip_mode: bool = False) -> Camelot:
    n = ((c.number - 1 + delta_number) % 12) + 1
    letter = c.letter if not flip_mode else ("B" if c.letter == "A" else "A")
    return Camelot(n, letter)


_MOVE_FUNCS = {
    "same": lambda c: move(c, 0),
    "plus_one": lambda c: move(c, +1),
    "minus_one": lambda c: move(c, -1),
    "relative": lambda c: move(c, 0, flip_mode=True),
    # Extended moves pros use; off by default in v1 config.
    "plus_two": lambda c: move(c, +2),
    "minus_two": lambda c: move(c, -2),
    "energy_boost": lambda c: move(c, +7),  # +1 semitone up (7 steps round the wheel)
    "diagonal_up": lambda c: move(c, +1, flip_mode=True),
    "diagonal_down": lambda c: move(c, -1, flip_mode=True),
}


def compatible_set(c: Camelot, allowed_moves: list[str]) -> set[Camelot]:
    out: set[Camelot] = set()
    for m in allowed_moves:
        if m not in _MOVE_FUNCS:
            raise ValueError(f"unknown camelot move {m!r}; known: {sorted(_MOVE_FUNCS)}")
        out.add(_MOVE_FUNCS[m](c))
    return out


def is_compatible(a: Camelot, b: Camelot, allowed_moves: list[str]) -> bool:
    return b in compatible_set(a, allowed_moves)


def wheel_distance(a: Camelot, b: Camelot) -> int:
    """Minimal steps around the wheel ignoring mode (0..6)."""
    d = abs(a.number - b.number) % 12
    return min(d, 12 - d)
