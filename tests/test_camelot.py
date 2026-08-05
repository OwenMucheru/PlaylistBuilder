"""Tests for core.camelot: key normalization and harmonic compatibility."""

from __future__ import annotations

from core.camelot import (
    TransitionType,
    compatibility,
    harmonic_score,
    is_compatible,
    normalize_to_camelot,
)


class TestNormalization:
    def test_already_camelot_passthrough(self):
        assert normalize_to_camelot("8A") == "8A"
        assert normalize_to_camelot("11b") == "11B"

    def test_traditional_major_key(self):
        assert normalize_to_camelot("Cmaj") == "8B"
        assert normalize_to_camelot("C") == "8B"

    def test_traditional_minor_key(self):
        assert normalize_to_camelot("Am") == "8A"
        assert normalize_to_camelot("Amin") == "8A"

    def test_sharp_and_flat_equivalence(self):
        assert normalize_to_camelot("F#maj") == normalize_to_camelot("Gbmaj")

    def test_unparseable_key_returns_empty(self):
        assert normalize_to_camelot("not a key") == ""
        assert normalize_to_camelot("") == ""

    def test_whitespace_tolerant(self):
        assert normalize_to_camelot(" 8A ") == "8A"


class TestCompatibility:
    def test_identical_key_is_perfect(self):
        assert compatibility("8A", "8A") == TransitionType.PERFECT

    def test_adjacent_keys(self):
        assert compatibility("8A", "9A") == TransitionType.ADJACENT
        assert compatibility("8A", "7A") == TransitionType.ADJACENT

    def test_wraparound_adjacency(self):
        assert compatibility("1A", "12A") == TransitionType.ADJACENT
        assert compatibility("12A", "1A") == TransitionType.ADJACENT

    def test_relative_major_minor(self):
        assert compatibility("8A", "8B") == TransitionType.RELATIVE

    def test_energy_boost_and_drop(self):
        assert compatibility("8A", "10A") == TransitionType.ENERGY_BOOST
        assert compatibility("8A", "6A") == TransitionType.ENERGY_DROP

    def test_unrelated_keys_clash(self):
        assert compatibility("1A", "6B") == TransitionType.CLASH

    def test_invalid_key_clashes_conservatively(self):
        assert compatibility("8A", "not-a-key") == TransitionType.CLASH


class TestScoring:
    def test_perfect_match_scores_highest(self):
        assert harmonic_score("8A", "8A") == 100.0

    def test_clash_scores_zero(self):
        assert harmonic_score("1A", "6B") == 0.0

    def test_unknown_key_is_neutral(self):
        assert harmonic_score("", "8A") == 50.0

    def test_is_compatible_respects_energy_shift_flag(self):
        assert is_compatible("8A", "10A", allow_energy_shift=True) is True
        assert is_compatible("8A", "10A", allow_energy_shift=False) is False
        assert is_compatible("8A", "9A", allow_energy_shift=False) is True
