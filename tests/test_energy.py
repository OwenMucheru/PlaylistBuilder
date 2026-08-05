"""Tests for core.energy: energy scoring and the phase curve."""

from __future__ import annotations

from core.energy import (
    DEFAULT_ENERGY_CURVE,
    EnergyPhase,
    compute_energy_score,
    fits_phase,
    phase_for_progress,
    score_tracks,
)
from core.models import Track


class TestComputeEnergyScore:
    def test_higher_bpm_yields_higher_energy(self):
        low = Track(filepath="/a.mp3", bpm=75, genre="House")
        high = Track(filepath="/b.mp3", bpm=145, genre="House")
        assert compute_energy_score(high) > compute_energy_score(low)

    def test_score_bounded_0_to_100(self):
        track = Track(filepath="/a.mp3", bpm=300, genre="EDM", rating=5, play_count=100)
        score = compute_energy_score(track)
        assert 0.0 <= score <= 100.0

    def test_zero_bpm_does_not_crash(self):
        track = Track(filepath="/a.mp3", bpm=0, genre="Gospel")
        score = compute_energy_score(track)
        assert 0.0 <= score <= 100.0

    def test_custom_weights_respected(self):
        track = Track(
            filepath="/a.mp3", bpm=150, genre="Gospel"
        )  # high bpm, low-energy genre
        bpm_heavy = compute_energy_score(
            track, weights={"bpm": 1.0, "genre": 0.0, "popularity": 0.0}
        )
        genre_heavy = compute_energy_score(
            track, weights={"bpm": 0.0, "genre": 1.0, "popularity": 0.0}
        )
        assert bpm_heavy > genre_heavy


class TestScoreTracks:
    def test_populates_energy_score_in_place(self, sample_tracks):
        for t in sample_tracks:
            assert 0.0 <= t.energy_score <= 100.0

    def test_returns_equivalent_list(self):
        tracks = [Track(filepath="/a.mp3", bpm=100)]
        result = score_tracks(tracks)
        assert result == tracks
        assert result[0].energy_score == tracks[0].energy_score


class TestEnergyCurve:
    def test_phase_for_progress_covers_full_range(self):
        assert phase_for_progress(0.0).phase == EnergyPhase.WARMUP
        assert phase_for_progress(0.99).phase == EnergyPhase.FINALE

    def test_curve_phases_are_contiguous(self):
        curve = DEFAULT_ENERGY_CURVE
        for i in range(len(curve) - 1):
            assert curve[i].end_fraction == curve[i + 1].start_fraction

    def test_fits_phase_within_tolerance(self):
        track = Track(filepath="/a.mp3")
        track.energy_score = 60.0  # within [65-12, 100+12] of the PEAK phase
        peak = next(p for p in DEFAULT_ENERGY_CURVE if p.phase == EnergyPhase.PEAK)
        assert fits_phase(track, peak, tolerance=12.0) is True

    def test_fits_phase_rejects_far_outlier(self):
        track = Track(filepath="/a.mp3")
        track.energy_score = 5.0
        peak = next(p for p in DEFAULT_ENERGY_CURVE if p.phase == EnergyPhase.PEAK)
        assert fits_phase(track, peak, tolerance=12.0) is False
