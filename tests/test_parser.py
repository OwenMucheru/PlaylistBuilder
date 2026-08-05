"""Tests for core.parser: VirtualDJ database.xml ingestion."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.parser import deduplicate, parse_database


class TestParseDatabase:
    def test_parses_all_song_entries(self, sample_database_xml: Path):
        tracks = parse_database(sample_database_xml)
        assert len(tracks) == 4

    def test_extracts_core_fields(self, sample_database_xml: Path):
        tracks = parse_database(sample_database_xml)
        track_a = next(t for t in tracks if t.title == "Track A")
        assert track_a.artist == "DJ Marvelous"
        assert track_a.genre == "House"
        assert track_a.bpm == 124.0
        assert track_a.camelot_key == "8A"
        assert track_a.rating == 4
        assert track_a.play_count == 12

    def test_handles_sparse_song_entry_gracefully(self, sample_database_xml: Path):
        tracks = parse_database(sample_database_xml)
        track_d = next(t for t in tracks if "Track D" in t.filepath)
        assert track_d.bpm == 0.0
        assert track_d.artist == ""
        assert track_d.title  # falls back to filename stem via __post_init__

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            parse_database(tmp_path / "does_not_exist.xml")

    def test_skip_missing_files_filters_nonexistent_paths(
        self, sample_database_xml: Path
    ):
        tracks = parse_database(sample_database_xml, skip_missing_files=True)
        # None of the synthetic /music/... paths exist on disk in the test env
        assert tracks == []


class TestDeduplicate:
    def test_removes_duplicate_artist_title(self, sample_database_xml: Path):
        tracks = parse_database(sample_database_xml)
        duplicated = tracks + [tracks[0]]
        result = deduplicate(duplicated)
        assert len(result) == len(tracks)

    def test_preserves_order_of_first_occurrence(self, sample_database_xml: Path):
        tracks = parse_database(sample_database_xml)
        result = deduplicate(tracks)
        assert [t.filepath for t in result] == [t.filepath for t in tracks]
