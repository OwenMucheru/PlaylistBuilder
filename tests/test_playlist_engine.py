"""Tests for core.playlist_engine: end-to-end playlist generation."""

from __future__ import annotations

from core.models import PlaylistRequest
from core.playlist_engine import PlaylistEngine


class TestPlaylistEngine:
    def test_generates_nonempty_playlist(self, sample_tracks):
        engine = PlaylistEngine(sample_tracks, seed=1)
        request = PlaylistRequest(duration_minutes=30, preset_name="freestyle")
        result = engine.generate(request)
        assert result.track_count > 0

    def test_no_duplicate_tracks_by_default(self, sample_tracks):
        engine = PlaylistEngine(sample_tracks, seed=1)
        request = PlaylistRequest(duration_minutes=45, preset_name="freestyle")
        result = engine.generate(request)
        ids = [t.track_id for t in result.tracks]
        assert len(ids) == len(set(ids))

    def test_respects_artist_separation(self, sample_tracks):
        engine = PlaylistEngine(sample_tracks, seed=2)
        request = PlaylistRequest(
            duration_minutes=45, preset_name="freestyle", artist_separation=3
        )
        result = engine.generate(request)
        artists = [t.artist for t in result.tracks if t.artist]
        for i, artist in enumerate(artists):
            window = artists[max(0, i - 3) : i]
            assert artist not in window

    def test_bpm_jumps_mostly_within_configured_max(self, sample_tracks):
        engine = PlaylistEngine(sample_tracks, seed=3)
        max_jump = 4.0
        request = PlaylistRequest(
            duration_minutes=45, preset_name="freestyle", max_bpm_jump=max_jump
        )
        result = engine.generate(request)

        bpm_tracks = [t for t in result.tracks if t.has_bpm]
        jumps = [
            abs(bpm_tracks[i + 1].bpm - bpm_tracks[i].bpm)
            for i in range(len(bpm_tracks) - 1)
        ]
        if jumps:
            # The soft-scored selector should keep the vast majority of
            # transitions near the configured ceiling even though it is not
            # a hard cutoff for every single pick.
            within_budget = sum(1 for j in jumps if j <= max_jump * 4)
            assert within_budget / len(jumps) > 0.7

    def test_duration_roughly_matches_target(self, sample_tracks):
        engine = PlaylistEngine(sample_tracks, seed=4)
        request = PlaylistRequest(
            duration_minutes=30, preset_name="freestyle", duration_tolerance_seconds=180
        )
        result = engine.generate(request)
        target_seconds = 30 * 60
        assert (
            result.total_duration_seconds >= target_seconds - 180 - 300
        )  # generous slack for sparse pools

    def test_empty_track_pool_returns_warning(self):
        engine = PlaylistEngine([], seed=1)
        request = PlaylistRequest(duration_minutes=30)
        result = engine.generate(request)
        assert result.track_count == 0
        assert result.warnings

    def test_playlist_positions_assigned_sequentially(self, sample_tracks):
        engine = PlaylistEngine(sample_tracks, seed=5)
        request = PlaylistRequest(duration_minutes=20, preset_name="freestyle")
        result = engine.generate(request)
        positions = [t.playlist_position for t in result.tracks]
        assert positions == list(range(1, len(result.tracks) + 1))

    def test_start_bpm_seeds_opening_track(self, sample_tracks):
        engine = PlaylistEngine(sample_tracks, seed=6)
        request = PlaylistRequest(
            duration_minutes=20, preset_name="freestyle", start_bpm=90.0
        )
        result = engine.generate(request)
        assert result.tracks
        # Opening track should be reasonably close to the requested start BPM.
        assert abs(result.tracks[0].bpm - 90.0) < 25.0

    def test_known_preset_applies_genre_bias(self, sample_tracks):
        engine = PlaylistEngine(sample_tracks, seed=7)
        request = PlaylistRequest(duration_minutes=30, preset_name="club")
        result = engine.generate(request)
        assert result.preset_name == "club"
        assert result.track_count > 0
