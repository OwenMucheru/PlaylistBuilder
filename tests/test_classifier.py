"""Tests for core.classifier: genre detection heuristics."""

from __future__ import annotations

from core.classifier import classify_tracks, detect_genres, genre_distribution
from core.models import Track


class TestDetectGenres:
    def test_detects_from_explicit_genre_tag(self):
        track = Track(filepath="/x.mp3", genre="Amapiano")
        assert "Amapiano" in detect_genres(track)

    def test_detects_from_folder_name(self):
        track = Track(filepath="/music/Gengetone/song.mp3", folder="/music/Gengetone")
        assert "Kenyan" in detect_genres(track)

    def test_detects_multiple_genres(self):
        track = Track(
            filepath="/music/Amapiano House Fusion/song.mp3",
            folder="/music/Amapiano House Fusion",
        )
        genres = detect_genres(track)
        assert "Amapiano" in genres
        assert "House" in genres

    def test_fuzzy_matches_misspelled_variant(self):
        track = Track(filepath="/x.mp3", genre="afro-house")
        assert "Afro House" in detect_genres(track)

    def test_unclassified_fallback(self):
        track = Track(filepath="/x.mp3", genre="", folder="", artist="", title="")
        assert detect_genres(track) == ["Unclassified"]

    def test_raw_tag_used_when_no_taxonomy_match(self):
        track = Track(filepath="/x.mp3", genre="Vaporwave")
        assert detect_genres(track) == ["Vaporwave"]


class TestClassifyTracks:
    def test_populates_detected_genres_in_place(self):
        tracks = [Track(filepath="/x.mp3", genre="Hip Hop")]
        classify_tracks(tracks)
        assert tracks[0].detected_genres == ["Hip Hop"]


class TestGenreDistribution:
    def test_counts_across_multi_genre_tracks(self):
        tracks = [
            Track(filepath="/a.mp3", genre="Amapiano"),
            Track(filepath="/b.mp3", genre="House"),
            Track(filepath="/c.mp3", genre="Amapiano"),
        ]
        classify_tracks(tracks)
        dist = genre_distribution(tracks)
        assert dist["Amapiano"] == 2
        assert dist["House"] == 1

    def test_sorted_descending_by_count(self):
        tracks = [
            Track(filepath="/a.mp3", genre="Amapiano"),
            Track(filepath="/b.mp3", genre="Amapiano"),
            Track(filepath="/c.mp3", genre="House"),
        ]
        classify_tracks(tracks)
        dist = genre_distribution(tracks)
        assert list(dist.keys())[0] == "Amapiano"
