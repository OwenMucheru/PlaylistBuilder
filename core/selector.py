"""
core.selector
=============

Given a pool of candidate tracks and the current playlist state (last
track played, recent artist history, current energy target), scores and
ranks candidates so the playlist engine can pick the best next track.

This is the "brain" that keeps the BPM engine, harmonic engine, and
energy curve honest simultaneously rather than each fighting the others
independently.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .energy import EnergyCurvePoint, fits_phase
from .harmonic import HarmonicEngine
from .models import PlaylistRequest, Track

logger = logging.getLogger("omniplaylist.selector")


@dataclass
class SelectionContext:
    """Rolling state the selector needs to score the next candidate."""

    previous_track: Track | None
    recent_artists: list[str]  # last N artists played, most recent last
    current_phase: EnergyCurvePoint
    progress: float  # 0.0-1.0 through target duration
    request: PlaylistRequest


class TrackSelector:
    """Ranks and filters candidate tracks for the next playlist slot."""

    def __init__(self, harmonic_engine: HarmonicEngine):
        self.harmonic_engine = harmonic_engine

    # ------------------------------------------------------------------
    # Hard filters (a track failing any of these is not eligible at all)
    # ------------------------------------------------------------------
    def is_eligible(
        self, candidate: Track, used_ids: set[str], ctx: SelectionContext
    ) -> bool:
        if not ctx.request.allow_duplicates and candidate.track_id in used_ids:
            return False

        separation = ctx.request.artist_separation
        if separation > 0 and candidate.artist:
            recent_window = ctx.recent_artists[-separation:] if separation else []
            if candidate.artist in recent_window:
                return False

        if (
            ctx.previous_track is not None
            and candidate.has_bpm
            and ctx.previous_track.has_bpm
        ):
            jump = abs(candidate.bpm - ctx.previous_track.bpm)
            # Allow a generous multiple of the configured max jump as a hard
            # ceiling; the *soft* scoring below is what really enforces the
            # configured max_bpm_jump under normal circumstances.
            if jump > max(ctx.request.max_bpm_jump * 6, 15):
                return False

        if ctx.request.genre_filter:
            wanted = {g.lower() for g in ctx.request.genre_filter}
            candidate_genres = {
                g.lower() for g in (candidate.detected_genres or [candidate.genre])
            }
            if wanted.isdisjoint(candidate_genres):
                return False

        return True

    # ------------------------------------------------------------------
    # Soft scoring (higher = better next pick)
    # ------------------------------------------------------------------
    def score_candidate(self, candidate: Track, ctx: SelectionContext) -> float:
        bpm_score = self._bpm_score(candidate, ctx)
        harmonic = self.harmonic_engine.score(ctx.previous_track, candidate)
        energy_fit = self._energy_fit_score(candidate, ctx)
        quality = self._quality_score(candidate)

        total = bpm_score * 0.35 + harmonic * 0.30 + energy_fit * 0.25 + quality * 0.10
        return total

    def _bpm_score(self, candidate: Track, ctx: SelectionContext) -> float:
        if (
            ctx.previous_track is None
            or not ctx.previous_track.has_bpm
            or not candidate.has_bpm
        ):
            return 80.0
        jump = abs(candidate.bpm - ctx.previous_track.bpm)
        max_jump = max(ctx.request.max_bpm_jump, 0.1)
        if jump <= max_jump:
            return 100.0
        # Decay smoothly past the configured max jump instead of a cliff.
        overshoot_ratio = jump / max_jump
        return max(0.0, 100.0 - (overshoot_ratio - 1) * 40.0)

    def _energy_fit_score(self, candidate: Track, ctx: SelectionContext) -> float:
        if fits_phase(candidate, ctx.current_phase, tolerance=8.0):
            return 100.0
        lo, hi = (
            ctx.current_phase.target_energy_min,
            ctx.current_phase.target_energy_max,
        )
        if candidate.energy_score < lo:
            distance = lo - candidate.energy_score
        else:
            distance = candidate.energy_score - hi
        return max(0.0, 100.0 - distance * 2.5)

    def _quality_score(self, candidate: Track) -> float:
        rating_component = (
            (candidate.rating / 5.0) * 100.0 if candidate.rating else 50.0
        )
        favorite_bonus = 10.0 if candidate.favorite else 0.0
        return min(100.0, rating_component + favorite_bonus)

    # ------------------------------------------------------------------
    def rank_candidates(
        self, pool: list[Track], used_ids: set[str], ctx: SelectionContext
    ) -> list[tuple[Track, float]]:
        eligible = [t for t in pool if self.is_eligible(t, used_ids, ctx)]
        scored = [(t, self.score_candidate(t, ctx)) for t in eligible]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored

    def pick_next(
        self, pool: list[Track], used_ids: set[str], ctx: SelectionContext
    ) -> Track | None:
        ranked = self.rank_candidates(pool, used_ids, ctx)
        if not ranked:
            return None
        return ranked[0][0]
