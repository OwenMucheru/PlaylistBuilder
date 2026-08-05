"""
core.camelot
============

Camelot Wheel utilities: normalization of arbitrary VirtualDJ key strings
into Camelot notation, and computation of harmonic compatibility between
two keys.

The Camelot Wheel maps all 24 musical keys onto a 12-position wheel split
into an "A" (minor) ring and a "B" (major) ring. Two keys are harmonically
compatible if they are:

* identical                      (perfect match)
* adjacent on the same ring      (+1 / -1, a "smooth" transition)
* same number, opposite ring     (relative major/minor)
* +2 on the same ring            (energy boost, used sparingly)
"""

from __future__ import annotations

import re

# Standard key name -> Camelot notation
_KEY_TO_CAMELOT = {
    "Cmaj": "8B",
    "C": "8B",
    "Amin": "8A",
    "Am": "8A",
    "A": "8A",
    "Gmaj": "9B",
    "G": "9B",
    "Emin": "9A",
    "Em": "9A",
    "Dmaj": "10B",
    "D": "10B",
    "Bmin": "10A",
    "Bm": "10A",
    "Amaj": "11B",
    "Emaj": "12B",
    "E": "12B",
    "Fmin": "4A",
    "Fm": "4A",
    "Bmaj": "1B",
    "B": "1B",
    "G#min": "1A",
    "Abmin": "1A",
    "G#m": "1A",
    "F#maj": "2B",
    "Gbmaj": "2B",
    "F#": "2B",
    "Gb": "2B",
    "D#min": "2A",
    "Ebmin": "2A",
    "D#m": "2A",
    "Ebm": "2A",
    "Dbmaj": "3B",
    "C#maj": "3B",
    "Db": "3B",
    "C#": "3B",
    "Bbmin": "3A",
    "A#min": "3A",
    "Bbm": "3A",
    "A#m": "3A",
    "Abmaj": "4B",
    "Ab": "4B",
    "Ebmaj": "5B",
    "Eb": "5B",
    "Cmin": "5A",
    "Cm": "5A",
    "Bbmaj": "6B",
    "Bb": "6B",
    "Gmin": "6A",
    "Gm": "6A",
    "Fmaj": "7B",
    "F": "7B",
    "Dmin": "7A",
    "Dm": "7A",
    "Amin7": "8A",
    "Bmin": "10A",
    "Dmaj7": "10B",
    "C#min": "12A",
    "Dbmin": "12A",
    "C#m": "12A",
    "F#min": "11A",
    "Gbmin": "11A",
    "F#m": "11A",
}

_CAMELOT_RE = re.compile(r"^(?P<num>[1-9]|1[0-2])(?P<ring>[AB])$", re.IGNORECASE)


def normalize_to_camelot(raw_key: str) -> str:
    """Best-effort normalization of a raw VirtualDJ key string to Camelot.

    Accepts already-Camelot values ("8A"), traditional names ("Cmaj",
    "Am", "F#m"), and is tolerant of whitespace/case. Returns "" if the
    key cannot be interpreted.
    """
    if not raw_key:
        return ""

    key = raw_key.strip()

    # Already Camelot notation, e.g. "8A", "11B"
    match = _CAMELOT_RE.match(key.replace(" ", ""))
    if match:
        return f"{match.group('num')}{match.group('ring').upper()}"

    # Try direct lookup (case-sensitive first, then normalized)
    if key in _KEY_TO_CAMELOT:
        return _KEY_TO_CAMELOT[key]

    cleaned = key.replace(" ", "").replace("major", "maj").replace("minor", "min")
    cleaned = cleaned.replace("Major", "maj").replace("Minor", "min")
    if cleaned in _KEY_TO_CAMELOT:
        return _KEY_TO_CAMELOT[cleaned]

    # Try case-insensitive match against the table
    lowered = cleaned.lower()
    for name, camelot in _KEY_TO_CAMELOT.items():
        if name.lower() == lowered:
            return camelot

    return ""


def camelot_parts(camelot: str) -> tuple[int, str] | None:
    """Split "8A" -> (8, "A"). Returns None if invalid."""
    match = _CAMELOT_RE.match(camelot.replace(" ", "").upper())
    if not match:
        return None
    return int(match.group("num")), match.group("ring").upper()


class TransitionType:
    PERFECT = "perfect_match"
    ADJACENT = "adjacent"
    RELATIVE = "relative_major_minor"
    ENERGY_BOOST = "energy_boost"
    ENERGY_DROP = "energy_drop"
    CLASH = "clash"


def compatibility(key_a: str, key_b: str) -> str:
    """Classify the harmonic transition from key_a -> key_b.

    Returns one of the :class:`TransitionType` constants. If either key is
    unparseable, returns TransitionType.CLASH conservatively (caller should
    treat unknown keys as "harmonic mixing not applicable" rather than a
    hard failure).
    """
    a = camelot_parts(key_a)
    b = camelot_parts(key_b)
    if a is None or b is None:
        return TransitionType.CLASH

    num_a, ring_a = a
    num_b, ring_b = b

    if num_a == num_b and ring_a == ring_b:
        return TransitionType.PERFECT

    if num_a == num_b and ring_a != ring_b:
        return TransitionType.RELATIVE

    diff = (num_b - num_a) % 12
    if ring_a == ring_b and diff in (1, 11):
        return TransitionType.ADJACENT

    if ring_a == ring_b and diff == 2:
        return TransitionType.ENERGY_BOOST

    if ring_a == ring_b and diff == 10:
        return TransitionType.ENERGY_DROP

    return TransitionType.CLASH


# Compatibility -> numeric score used by the selector to rank candidates.
# Higher is better.
_SCORE_TABLE = {
    TransitionType.PERFECT: 100,
    TransitionType.ADJACENT: 85,
    TransitionType.RELATIVE: 80,
    TransitionType.ENERGY_BOOST: 60,
    TransitionType.ENERGY_DROP: 55,
    TransitionType.CLASH: 0,
}


def harmonic_score(key_a: str, key_b: str) -> float:
    """Numeric 0-100 harmonic compatibility score between two Camelot keys."""
    if not key_a or not key_b:
        return 50.0  # neutral - unknown key shouldn't tank a candidate
    return float(_SCORE_TABLE[compatibility(key_a, key_b)])


def is_compatible(key_a: str, key_b: str, allow_energy_shift: bool = True) -> bool:
    """Simple boolean check used when strict harmonic mixing is enforced."""
    result = compatibility(key_a, key_b)
    if result in (
        TransitionType.PERFECT,
        TransitionType.ADJACENT,
        TransitionType.RELATIVE,
    ):
        return True
    if allow_energy_shift and result in (
        TransitionType.ENERGY_BOOST,
        TransitionType.ENERGY_DROP,
    ):
        return True
    return False
