"""
core.models
===========

Domain models used throughout OmniPlaylist.

The central type is :class:`Track`, a rich dataclass representing a single
song pulled from a VirtualDJ ``database.xml`` file, enriched with detected
genres, an energy score, and playlist-time bookkeeping fields.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Track:
    """A single song and every piece of metadata OmniPlaylist cares about.

    Only ``filepath`` is strictly required; everything else has a sane
    default so the parser can build a ``Track`` even from a sparse
    ``<Song>`` entry.
    """

    # --- identity -----------------------------------------------------
    filepath: str
    artist: str = ""
    title: str = ""
    remix: str = ""
    album: str = ""

    # --- musical metadata ----------------------------------------------
    genre: str = ""
    detected_genres: list[str] = field(default_factory=list)
    year: int | None = None
    bpm: float = 0.0
    musical_key: str = ""  # raw key as read from VDJ (e.g. "8A", "Cmaj")
    camelot_key: str = ""  # normalized Camelot notation (e.g. "8A")

    # --- playback metadata ----------------------------------------------
    length_seconds: float = 0.0
    rating: int = 0  # 0-5 stars
    play_count: int = 0
    last_played: datetime | None = None
    date_added: datetime | None = None
    favorite: bool = False

    # --- file metadata ----------------------------------------------
    folder: str = ""
    file_size: int = 0
    comments: str = ""

    # --- derived / engine fields (populated at runtime, not from XML) --
    energy_score: float = 0.0
    popularity_score: float = 0.0
    playlist_position: int | None = None
    running_time_seconds: float = 0.0

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        if not self.title:
            self.title = Path(self.filepath).stem if self.filepath else "Unknown Title"
        if not self.folder and self.filepath:
            self.folder = str(Path(self.filepath).parent)

    @property
    def display_name(self) -> str:
        """Human readable ``Artist - Title (Remix)`` label."""
        base = f"{self.artist} - {self.title}" if self.artist else self.title
        if self.remix:
            base += f" ({self.remix})"
        return base

    @property
    def length_minutes(self) -> float:
        return round(self.length_seconds / 60.0, 2)

    @property
    def has_bpm(self) -> bool:
        return self.bpm and self.bpm > 0

    @property
    def has_key(self) -> bool:
        return bool(self.camelot_key)

    @property
    def track_id(self) -> str:
        """Stable identity hash, used for de-duplication."""
        raw = f"{self.artist.lower().strip()}|{self.title.lower().strip()}|{self.remix.lower().strip()}"
        return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()

    def matches_genre(self, genre: str) -> bool:
        genre = genre.lower().strip()
        if self.genre and genre in self.genre.lower():
            return True
        return any(genre in g.lower() for g in self.detected_genres)

    def to_dict(self) -> dict:
        """Serialize to a flat, JSON-friendly dict (used for CSV/JSON export)."""
        return {
            "position": self.playlist_position,
            "title": self.title,
            "artist": self.artist,
            "remix": self.remix,
            "album": self.album,
            "genre": self.genre,
            "detected_genres": ", ".join(self.detected_genres),
            "year": self.year,
            "bpm": self.bpm,
            "camelot_key": self.camelot_key,
            "musical_key": self.musical_key,
            "length_seconds": self.length_seconds,
            "length_minutes": self.length_minutes,
            "rating": self.rating,
            "play_count": self.play_count,
            "energy_score": round(self.energy_score, 2),
            "running_time_seconds": round(self.running_time_seconds, 2),
            "filepath": self.filepath,
        }

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<Track {self.display_name!r} bpm={self.bpm} key={self.camelot_key}>"


@dataclass
class PlaylistRequest:
    """User-supplied parameters describing the playlist to generate."""

    duration_minutes: float
    preset_name: str = "freestyle"
    start_bpm: float | None = None
    end_bpm: float | None = None
    max_bpm_jump: float = 2.0
    artist_separation: int = 3  # min tracks between repeats of same artist
    harmonic_mixing: bool = True
    genre_filter: list[str] = field(default_factory=list)
    allow_duplicates: bool = False
    duration_tolerance_seconds: float = 120.0  # ±2 minutes


@dataclass
class PlaylistResult:
    """Output of the playlist engine."""

    tracks: list[Track]
    total_duration_seconds: float
    preset_name: str
    warnings: list[str] = field(default_factory=list)

    @property
    def total_duration_minutes(self) -> float:
        return round(self.total_duration_seconds / 60.0, 1)

    @property
    def track_count(self) -> int:
        return len(self.tracks)
