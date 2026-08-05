"""Tests for core.utils: presets, config, formatting helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.utils import (
    format_duration,
    list_presets,
    load_config,
    load_preset,
    safe_filename,
    save_config,
)


class TestFormatDuration:
    def test_seconds_under_a_minute(self):
        assert format_duration(45) == "0:45"

    def test_minutes_and_seconds(self):
        assert format_duration(185) == "3:05"

    def test_hours_minutes_seconds(self):
        assert format_duration(3725) == "1:02:05"


class TestPresets:
    def test_list_presets_includes_shipped_defaults(self):
        names = list_presets()
        for expected in ("wedding", "club", "graduation", "corporate", "freestyle"):
            assert expected in names

    def test_load_preset_has_required_keys(self):
        preset = load_preset("wedding")
        for key in (
            "display_name",
            "target_bpm_range",
            "genre_percentages",
            "energy_curve",
            "artist_separation",
        ):
            assert key in preset

    def test_missing_preset_raises(self):
        with pytest.raises(FileNotFoundError):
            load_preset("does_not_exist_preset")


class TestConfig:
    def test_load_config_returns_defaults_when_missing(self, tmp_path: Path):
        config = load_config(tmp_path / "no_such_config.json")
        assert config["max_bpm_jump"] == 2.0
        assert config["harmonic_mixing"] is True

    def test_save_and_reload_roundtrip(self, tmp_path: Path):
        path = tmp_path / "config.json"
        config = load_config(path)
        config["max_bpm_jump"] = 5.5
        save_config(config, path)

        reloaded = load_config(path)
        assert reloaded["max_bpm_jump"] == 5.5

    def test_corrupt_config_falls_back_to_defaults(self, tmp_path: Path):
        path = tmp_path / "config.json"
        path.write_text("{not valid json", encoding="utf-8")
        config = load_config(path)
        assert config["max_bpm_jump"] == 2.0


class TestSafeFilename:
    def test_strips_invalid_characters(self):
        assert safe_filename('My:Set "Live"') == "MySet Live"

    def test_empty_name_falls_back(self):
        assert safe_filename("") == "playlist"

    def test_truncates_to_max_length(self):
        long_name = "a" * 300
        assert len(safe_filename(long_name, max_length=50)) == 50
