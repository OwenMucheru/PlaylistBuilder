"""
core.utils
==========

Small shared helpers: logging setup, duration formatting, and preset
JSON loading/validation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets"


def setup_logging(
    level: int = logging.INFO, log_file: str | Path | None = None
) -> logging.Logger:
    """Configure the root ``omniplaylist`` logger. Safe to call multiple times."""
    logger = logging.getLogger("omniplaylist")
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def format_duration(seconds: float) -> str:
    """Format seconds as H:MM:SS or M:SS."""
    seconds = int(round(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def list_presets() -> list[str]:
    """Return the names of all preset JSON files in /presets (without extension)."""
    if not PRESETS_DIR.exists():
        return []
    return sorted(p.stem for p in PRESETS_DIR.glob("*.json"))


def load_preset(name: str) -> dict[str, Any]:
    """Load a preset JSON by name (e.g. 'wedding' -> presets/wedding.json)."""
    path = PRESETS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Preset not found: {name} (looked in {path})")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    _validate_preset(data, name)
    return data


def _validate_preset(data: dict[str, Any], name: str) -> None:
    required_keys = {
        "display_name",
        "target_bpm_range",
        "genre_percentages",
        "energy_curve",
        "artist_separation",
    }
    missing = required_keys - data.keys()
    if missing:
        raise ValueError(f"Preset '{name}' is missing required keys: {missing}")


def load_config(config_path: str | Path = "config.json") -> dict[str, Any]:
    """Load the application-level config.json, returning defaults if absent."""
    path = Path(config_path)
    defaults: dict[str, Any] = {
        "max_bpm_jump": 2.0,
        "artist_separation": 3,
        "harmonic_mixing": True,
        "dark_mode": True,
        "default_preset": "freestyle",
        "duration_tolerance_seconds": 120,
        "last_database_path": "",
        "output_directory": "output",
    }
    if not path.exists():
        return defaults
    try:
        with open(path, "r", encoding="utf-8") as fh:
            user_config = json.load(fh)
        defaults.update(user_config)
    except (json.JSONDecodeError, OSError):
        logging.getLogger("omniplaylist").warning(
            "Failed to read %s, using defaults", path
        )
    return defaults


def save_config(
    config: dict[str, Any], config_path: str | Path = "config.json"
) -> None:
    path = Path(config_path)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)


def safe_filename(name: str, max_length: int = 120) -> str:
    """Strip characters that are unsafe for filenames across OSes."""
    invalid = '<>:"/\\|?*'
    cleaned = "".join(c for c in name if c not in invalid).strip()
    cleaned = cleaned or "playlist"
    return cleaned[:max_length]
