"""
core.playlist_engine
=====================

The orchestrator: takes a parsed & classified track pool, a
:class:`~core.models.PlaylistRequest`, and a preset, and produces a
:class:`~core.models.PlaylistResult` — an ordered list of tracks whose
BPM progression, harmonic transitions, artist spacing, and energy curve
all respect the request's constraints, targeting the requested duration
within tolerance.

Algorithm overview
-------------------
1.  Filter the pool down to tracks matching the preset's genre mix (soft
    preference, not a hard filter, so a thin library still produces a
    full-length set).
2.  Determine a target energy curve (Warmup/Build/Peak/Finale) scaled to
    the requested duration.
3.  Greedily build the set: at each step, compute progress through the
    target duration, resolve the current energy phase, and ask
    :class:`~core.selector.TrackSelector` for the best next track given
    BPM continuity, harmonic compatibility, artist spacing, and energy
    fit.
4.  Stop when total duration is within tolerance of the target, or the
    candidate pool is exhausted.
"""

from __future__ import annotations

import logging
import random
from collections import Counter

from .energy import DEFAULT_ENERGY_CURVE, EnergyCurvePoint, score_tracks
from .harmonic import HarmonicEngine
from .models import PlaylistRequest, PlaylistResult, Track
from .selector import SelectionContext, TrackSelector
from .utils import load_preset

logger = logging.getLogger("omniplaylist.engine")


class PlaylistEngine:
    """Stateful facade over the selection pipeline for one generation run."""

    def __init__(self, tracks: list[Track], seed: int | None = None):
        self.all_tracks = tracks
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    def generate(self, request: PlaylistRequest) -> PlaylistResult:
        warnings: list[str] = []

        preset = self._load_preset_safe(request.preset_name, warnings)
        pool = self._build_pool(request, preset, warnings)

        if not pool:
            return PlaylistResult(
                tracks=[],
                total_duration_seconds=0.0,
                preset_name=request.preset_name,
                warnings=warnings + ["No eligible tracks found for this request."],
            )

        score_tracks(pool)

        harmonic_engine = HarmonicEngine(enabled=request.harmonic_mixing)
        selector = TrackSelector(harmonic_engine)

        target_seconds = request.duration_minutes * 60.0
        curve = self._build_curve(preset)

        selected: list[Track] = []
        used_ids: set[str] = set()
        recent_artists: list[str] = []
        running_time = 0.0
        previous_track: Track | None = None

        # Seed the set near the requested start BPM if given.
        first_track = self._pick_seed_track(pool, request)
        if first_track is None:
            return PlaylistResult(
                tracks=[],
                total_duration_seconds=0.0,
                preset_name=request.preset_name,
                warnings=warnings + ["Could not find a suitable opening track."],
            )

        candidate_pool = pool

        current = first_track
        max_iterations = max(len(candidate_pool) * 3, 500)
        iterations = 0

        while (
            running_time < target_seconds - request.duration_tolerance_seconds
            and iterations < max_iterations
        ):
            iterations += 1

            current.playlist_position = len(selected) + 1
            current.running_time_seconds = running_time
            selected.append(current)
            used_ids.add(current.track_id)
            if current.artist:
                recent_artists.append(current.artist)
            running_time += current.length_seconds or 180.0  # assume 3 min if unknown
            previous_track = current

            if running_time >= target_seconds + request.duration_tolerance_seconds:
                break

            progress = (
                min(1.0, running_time / target_seconds) if target_seconds else 0.0
            )
            phase = self._phase_for(progress, curve)

            ctx = SelectionContext(
                previous_track=previous_track,
                recent_artists=recent_artists,
                current_phase=phase,
                progress=progress,
                request=request,
            )

            next_track = selector.pick_next(candidate_pool, used_ids, ctx)
            if next_track is None:
                if not request.allow_duplicates:
                    warnings.append(
                        f"Track pool exhausted after {len(selected)} tracks "
                        f"({running_time/60:.1f} min); target was {request.duration_minutes} min."
                    )
                break
            current = next_track

        if abs(running_time - target_seconds) > request.duration_tolerance_seconds:
            warnings.append(
                f"Final duration {running_time/60:.1f} min is outside the "
                f"±{request.duration_tolerance_seconds/60:.1f} min tolerance of the "
                f"{request.duration_minutes} min target."
            )

        self._log_genre_balance(selected, preset, warnings)

        return PlaylistResult(
            tracks=selected,
            total_duration_seconds=running_time,
            preset_name=request.preset_name,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load_preset_safe(self, name: str, warnings: list[str]) -> dict:
        try:
            return load_preset(name)
        except (FileNotFoundError, ValueError) as exc:
            warnings.append(
                f"Preset '{name}' could not be loaded ({exc}); using neutral defaults."
            )
            return {
                "display_name": name,
                "target_bpm_range": [90, 128],
                "genre_percentages": {},
                "energy_curve": [],
                "artist_separation": 3,
            }

    def _build_pool(
        self, request: PlaylistRequest, preset: dict, warnings: list[str]
    ) -> list[Track]:
        pool = [t for t in self.all_tracks if t.length_seconds > 0]
        if not pool:
            warnings.append(
                "No tracks with known length found; falling back to full library."
            )
            pool = list(self.all_tracks)

        genre_pct: dict[str, float] = preset.get("genre_percentages", {})
        if genre_pct:
            wanted_genres = {g.lower() for g in genre_pct if genre_pct[g] > 0}
            preferred = [
                t
                for t in pool
                if wanted_genres.intersection(
                    {g.lower() for g in (t.detected_genres or [t.genre])}
                )
            ]
            # Only narrow the pool if doing so still leaves enough material;
            # otherwise keep the full pool so short libraries still work.
            if len(preferred) >= 15:
                pool = preferred
            else:
                warnings.append(
                    "Preset genre preferences matched very few tracks; using full library instead."
                )

        bpm_range = preset.get("target_bpm_range")
        if bpm_range and len(bpm_range) == 2:
            lo, hi = bpm_range
            widened_lo, widened_hi = lo - 15, hi + 15
            bpm_filtered = [
                t for t in pool if not t.has_bpm or widened_lo <= t.bpm <= widened_hi
            ]
            if len(bpm_filtered) >= 15:
                pool = bpm_filtered

        self._rng.shuffle(pool)
        return pool

    def _build_curve(self, preset: dict) -> list[EnergyCurvePoint]:
        raw_curve = preset.get("energy_curve")
        if not raw_curve:
            return DEFAULT_ENERGY_CURVE
        points = []
        try:
            for entry in raw_curve:
                points.append(
                    EnergyCurvePoint(
                        phase=entry["phase"],
                        start_fraction=entry["start_fraction"],
                        end_fraction=entry["end_fraction"],
                        target_energy_min=entry["target_energy_min"],
                        target_energy_max=entry["target_energy_max"],
                    )
                )
            return points
        except (KeyError, TypeError):
            return DEFAULT_ENERGY_CURVE

    def _phase_for(
        self, progress: float, curve: list[EnergyCurvePoint]
    ) -> EnergyCurvePoint:
        for point in curve:
            if point.start_fraction <= progress < point.end_fraction:
                return point
        return curve[-1]

    def _pick_seed_track(
        self, pool: list[Track], request: PlaylistRequest
    ) -> Track | None:
        if request.start_bpm:
            candidates = sorted(
                (t for t in pool if t.has_bpm),
                key=lambda t: abs(t.bpm - request.start_bpm),
            )
            if candidates:
                return candidates[0]
        return pool[0] if pool else None

    def _log_genre_balance(
        self, selected: list[Track], preset: dict, warnings: list[str]
    ) -> None:
        if not selected:
            return
        counts = Counter()
        for t in selected:
            for g in t.detected_genres or [t.genre or "Unclassified"]:
                counts[g] += 1
        logger.info("Final genre balance: %s", dict(counts))
