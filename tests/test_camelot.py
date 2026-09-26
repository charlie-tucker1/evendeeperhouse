"""Exhaustive Camelot wheel tests (Gate G0)."""

from __future__ import annotations

import itertools

import pytest

from deephouse.analysis import camelot as C

# Ground truth: the standard Camelot wheel (Mixed In Key).
WHEEL = {
    "1A": "G# minor", "1B": "B major",
    "2A": "D# minor", "2B": "F# major",
    "3A": "A# minor", "3B": "C# major",
    "4A": "F minor", "4B": "G# major",
    "5A": "C minor", "5B": "D# major",
    "6A": "G minor", "6B": "A# major",
    "7A": "D minor", "7B": "F major",
    "8A": "A minor", "8B": "C major",
    "9A": "E minor", "9B": "G major",
    "10A": "B minor", "10B": "D major",
    "11A": "F# minor", "11B": "A major",
    "12A": "C# minor", "12B": "E major",
}


@pytest.mark.parametrize("code,name", sorted(WHEEL.items()))
def test_code_to_name_and_back(code, name):
    c = C.parse(code)
    assert c.key_name == name
    assert C.from_key_name(name).code == code
    assert C.from_key(c.pitch_class, c.is_minor).code == code


def test_all_24_codes_unique_pitch_mode_pairs():
    seen = set()
    for n, letter in itertools.product(range(1, 13), "AB"):
        c = C.Camelot(n, letter)
        seen.add((c.pitch_class, c.is_minor))
    assert len(seen) == 24


def test_adjacent_numbers_are_a_fifth_apart():
    for n in range(1, 13):
        a = C.Camelot(n, "B")
        b = C.move(a, +1)
        assert (b.pitch_class - a.pitch_class) % 12 == 7  # perfect fifth up


def test_relative_shares_number_and_is_minor_third_below():
    for n in range(1, 13):
        maj = C.Camelot(n, "B")
        rel = C.move(maj, 0, flip_mode=True)
        assert rel.number == n and rel.is_minor
        assert (maj.pitch_class - rel.pitch_class) % 12 == 3


def test_wraparound():
    assert C.move(C.parse("12A"), +1).code == "1A"
    assert C.move(C.parse("1B"), -1).code == "12B"


@pytest.mark.parametrize(
    "a,b,ok",
    [
        ("8A", "8A", True), ("8A", "9A", True), ("8A", "7A", True), ("8A", "8B", True),
        ("8A", "10A", False), ("8A", "9B", False), ("8A", "2A", False), ("12A", "1A", True),
    ],
)
def test_v1_compatibility_policy(a, b, ok):
    moves = ["same", "plus_one", "minus_one", "relative"]
    assert C.is_compatible(C.parse(a), C.parse(b), moves) is ok


def test_energy_boost_is_one_semitone_up():
    for code in WHEEL:
        c = C.parse(code)
        up = C.compatible_set(c, ["energy_boost"]).pop()
        assert (up.pitch_class - c.pitch_class) % 12 == 1
        assert up.is_minor == c.is_minor


def test_wheel_distance_symmetric_and_bounded():
    codes = [C.parse(k) for k in WHEEL]
    for a, b in itertools.product(codes, codes):
        d = C.wheel_distance(a, b)
        assert 0 <= d <= 6
        assert d == C.wheel_distance(b, a)


def test_key_name_parsing_variants():
    assert C.from_key_name("Am").code == "8A"
    assert C.from_key_name("a minor").code == "8A"
    assert C.from_key_name("C").code == "8B"
    assert C.from_key_name("Bb").code == "6B"
    assert C.from_key_name("Bbm").code == "3A"
    assert C.from_key_name("F# min").code == "11A"
    assert C.from_key_name("Dbmaj").code == "3B"
    with pytest.raises(ValueError):
        C.from_key_name("H major")
    with pytest.raises(ValueError):
        C.parse("13A")
