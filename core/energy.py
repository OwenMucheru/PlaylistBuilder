"""
core.energy
===========

Computes a 0-100 "energy score" for every track, and defines the target
energy curve (Warmup -> Build -> Peak -> Finale) that the playlist engine
uses to decide *when* in the set a given track should play.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from .models import Track

logger = logging.getLogger("omniplaylist.energy")


# Genres get a base energy modifier - purely a starting heuristic, later
# blended with BPM, rating, and popularity.
_GENRE_ENERGY_BASE: dict[str, float] = {
    "Amapiano": 65,
    "Afro House": 75,
    "House": 78,
    "EDM": 88,
    "Afrobeats": 68,
    "Kenyan": 70,
    "Hip Hop": 72,
    "Dancehall": 74,
    "R&B": 45,
    "Reggae": 50,
    "Gospel": 40,
    "Old School": 55,
    "Pop": 60,
    "Soul": 42,
    "Rock": 66,
    "Latin": 70,
    "Bongo": 62,
    "Soukous": 58,
    "Zouk": 48,
    "Unclassified": 55,
}

_BPM_ENERGY_MIN = 60.0
_BPM_ENERGY_MAX = 150.0


class EnergyPhase(str, Enum):
    WARMUP = "warmup"
    BUILD = "build"
    PEAK = "peak"
    FINALE = "finale"


@dataclass(frozen=True)
class EnergyCurvePoint:
    """A named phase spanning a fraction of the total playlist duration."""

    phase: EnergyPhase
    start_fraction: float  # 0.0-1.0, inclusive
    end_fraction: float  # 0.0-1.0, exclusive (except last point)
    target_energy_min: float
    target_energy_max: float


# Default 4-phase curve: Warmup(0-15%) -> Build(15-45%) -> Peak(45-85%) -> Finale(85-100%)
DEFAULT_ENERGY_CURVE: list[EnergyCurvePoint] = [
    EnergyCurvePoint(EnergyPhase.WARMUP, 0.00, 0.15, 20, 45),
    EnergyCurvePoint(EnergyPhase.BUILD, 0.15, 0.45, 40, 70),
    EnergyCurvePoint(EnergyPhase.PEAK, 0.45, 0.85, 65, 100),
    EnergyCurvePoint(EnergyPhase.FINALE, 0.85, 1.01, 30, 65),
]


def phase_for_progress(
    progress: float, curve: list[EnergyCurvePoint] | None = None
) -> EnergyCurvePoint:
    """Given progress through the set (0.0-1.0), return the matching curve point."""
    curve = curve or DEFAULT_ENERGY_CURVE
    progress = max(0.0, min(1.0, progress))
    for point in curve:
        if point.start_fraction <= progress < point.end_fraction:
            return point
    return curve[-1]


def _bpm_component(bpm: float) -> float:
    if bpm <= 0:
        return 50.0
    clamped = max(_BPM_ENERGY_MIN, min(_BPM_ENERGY_MAX, bpm))
    return (clamped - _BPM_ENERGY_MIN) / (_BPM_ENERGY_MAX - _BPM_ENERGY_MIN) * 100.0


def _genre_component(track: Track) -> float:
    genres = track.detected_genres or [track.genre or "Unclassified"]
    values = [_GENRE_ENERGY_BASE.get(g, 55.0) for g in genres]
    return sum(values) / len(values) if values else 55.0


def _popularity_component(track: Track) -> float:
    """Blend play_count and rating into a 0-100 popularity figure."""
    rating_component = (track.rating / 5.0) * 100.0 if track.rating else 40.0
    play_component = min(track.play_count, 50) / 50.0 * 100.0
    return (rating_component * 0.6) + (play_component * 0.4)


def compute_energy_score(
    track: Track, weights: dict[str, float] | None = None
) -> float:
    """Compute a track's intrinsic 0-100 energy score.

    Weights default to: BPM 45%, Genre 35%, Popularity 20%. Callers may
    override weights (e.g. a preset that de-emphasizes BPM for a spoken-
    word heavy corporate set).
    """
    weights = weights or {"bpm": 0.45, "genre": 0.35, "popularity": 0.20}

    bpm_score = _bpm_component(track.bpm)
    genre_score = _genre_component(track)
    pop_score = _popularity_component(track)

    score = (
        bpm_score * weights.get("bpm", 0.45)
        + genre_score * weights.get("genre", 0.35)
        + pop_score * weights.get("popularity", 0.20)
    )
    return round(max(0.0, min(100.0, score)), 2)


def score_tracks(
    tracks: Iterable[Track], weights: dict[str, float] | None = None
) -> list[Track]:
    """Populate ``track.energy_score`` and ``track.popularity_score`` in-place."""
    tracks = list(tracks)
    for track in tracks:
        track.energy_score = compute_energy_score(track, weights)
        track.popularity_score = round(_popularity_component(track), 2)
    logger.info("Scored energy for %d tracks", len(tracks))
    return tracks


def fits_phase(track: Track, point: EnergyCurvePoint, tolerance: float = 12.0) -> bool:
    """Whether a track's energy score reasonably fits a curve phase, with slack."""
    lo = point.target_energy_min - tolerance
    hi = point.target_energy_max + tolerance
    return lo <= track.energy_score <= hi
