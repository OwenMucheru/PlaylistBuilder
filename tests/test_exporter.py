"""Tests for core.exporter: M3U/CSV/JSON/report generation."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from core.exporter import (
    build_report_text,
    export_all,
    export_csv,
    export_json,
    export_m3u,
)
from core.models import PlaylistRequest
from core.playlist_engine import PlaylistEngine


def _sample_result(sample_tracks):
    engine = PlaylistEngine(sample_tracks, seed=9)
    request = PlaylistRequest(duration_minutes=20, preset_name="freestyle")
    return engine.generate(request)


class TestExportM3U:
    def test_writes_extm3u_header(self, sample_tracks, tmp_path: Path):
        result = _sample_result(sample_tracks)
        out = export_m3u(result, tmp_path / "set.m3u")
        content = out.read_text(encoding="utf-8")
        assert content.startswith("#EXTM3U")

    def test_one_extinf_per_track(self, sample_tracks, tmp_path: Path):
        result = _sample_result(sample_tracks)
        out = export_m3u(result, tmp_path / "set.m3u")
        content = out.read_text(encoding="utf-8")
        assert content.count("#EXTINF:") == result.track_count

    def test_filepaths_present(self, sample_tracks, tmp_path: Path):
        result = _sample_result(sample_tracks)
        out = export_m3u(result, tmp_path / "set.m3u")
        content = out.read_text(encoding="utf-8")
        for t in result.tracks:
            assert t.filepath in content


class TestExportCSV:
    def test_row_count_matches_track_count(self, sample_tracks, tmp_path: Path):
        result = _sample_result(sample_tracks)
        out = export_csv(result, tmp_path / "set.csv")
        with open(out, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == result.track_count

    def test_empty_playlist_produces_empty_file(self, tmp_path: Path):
        engine = PlaylistEngine([], seed=1)
        result = engine.generate(PlaylistRequest(duration_minutes=10))
        out = export_csv(result, tmp_path / "empty.csv")
        assert out.read_text(encoding="utf-8") == ""


class TestExportJSON:
    def test_structure_and_track_count(self, sample_tracks, tmp_path: Path):
        result = _sample_result(sample_tracks)
        out = export_json(result, tmp_path / "set.json")
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["track_count"] == result.track_count
        assert len(data["tracks"]) == result.track_count
        assert data["preset"] == result.preset_name


class TestReport:
    def test_report_contains_header_and_tracks(self, sample_tracks):
        result = _sample_result(sample_tracks)
        text = build_report_text(result)
        assert "OMNIPLAYLIST" in text
        assert str(result.track_count) in text


class TestExportAll:
    def test_creates_all_four_files(self, sample_tracks, tmp_path: Path):
        result = _sample_result(sample_tracks)
        paths = export_all(result, tmp_path, "My Set")
        for key in ("m3u", "csv", "json", "report"):
            assert paths[key].exists()

    def test_sanitizes_unsafe_filename(self, sample_tracks, tmp_path: Path):
        result = _sample_result(sample_tracks)
        paths = export_all(result, tmp_path, 'Set: <2026> "Live"')
        assert paths["m3u"].exists()
        assert "<" not in paths["m3u"].name
