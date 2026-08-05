"""Tests for core.selector: candidate eligibility and scoring."""

from __future__ import annotations

from core.energy import DEFAULT_ENERGY_CURVE
from core.harmonic import HarmonicEngine
from core.models import PlaylistRequest, Track
from core.selector import SelectionContext, TrackSelector


def _ctx(previous, recent_artists=None, request=None) -> SelectionContext:
    return SelectionContext(
        previous_track=previous,
        recent_artists=recent_artists or [],
        current_phase=DEFAULT_ENERGY_CURVE[1],
        progress=0.3,
        request=request or PlaylistRequest(duration_minutes=60),
    )


class TestEligibility:
    def test_already_used_track_ineligible_by_default(self):
        selector = TrackSelector(HarmonicEngine())
        track = Track(filepath="/a.mp3", bpm=120)
        ctx = _ctx(previous=None)
        assert selector.is_eligible(track, used_ids={track.track_id}, ctx=ctx) is False

    def test_allow_duplicates_overrides_used_check(self):
        selector = TrackSelector(HarmonicEngine())
        track = Track(filepath="/a.mp3", bpm=120)
        request = PlaylistRequest(duration_minutes=60, allow_duplicates=True)
        ctx = _ctx(previous=None, request=request)
        assert selector.is_eligible(track, used_ids={track.track_id}, ctx=ctx) is True

    def test_artist_separation_blocks_recent_artist(self):
        selector = TrackSelector(HarmonicEngine())
        track = Track(filepath="/a.mp3", artist="Burna Boy", bpm=120)
        request = PlaylistRequest(duration_minutes=60, artist_separation=3)
        ctx = _ctx(
            previous=None, recent_artists=["Burna Boy", "X", "Y"], request=request
        )
        assert selector.is_eligible(track, used_ids=set(), ctx=ctx) is False

    def test_artist_separation_allows_after_window(self):
        selector = TrackSelector(HarmonicEngine())
        track = Track(filepath="/a.mp3", artist="Burna Boy", bpm=120)
        request = PlaylistRequest(duration_minutes=60, artist_separation=2)
        ctx = _ctx(
            previous=None, recent_artists=["Burna Boy", "X", "Y"], request=request
        )
        assert selector.is_eligible(track, used_ids=set(), ctx=ctx) is True

    def test_extreme_bpm_jump_hard_filtered(self):
        selector = TrackSelector(HarmonicEngine())
        previous = Track(filepath="/prev.mp3", bpm=90)
        candidate = Track(filepath="/next.mp3", bpm=180)
        request = PlaylistRequest(duration_minutes=60, max_bpm_jump=2.0)
        ctx = _ctx(previous=previous, request=request)
        assert selector.is_eligible(candidate, used_ids=set(), ctx=ctx) is False

    def test_genre_filter_excludes_non_matching(self):
        selector = TrackSelector(HarmonicEngine())
        candidate = Track(
            filepath="/a.mp3", bpm=120, genre="Gospel", detected_genres=["Gospel"]
        )
        request = PlaylistRequest(duration_minutes=60, genre_filter=["Amapiano"])
        ctx = _ctx(previous=None, request=request)
        assert selector.is_eligible(candidate, used_ids=set(), ctx=ctx) is False


class TestScoring:
    def test_small_bpm_jump_scores_higher_than_large(self):
        selector = TrackSelector(HarmonicEngine())
        previous = Track(filepath="/prev.mp3", bpm=100)
        close = Track(filepath="/close.mp3", bpm=101)
        far = Track(filepath="/far.mp3", bpm=112)
        request = PlaylistRequest(duration_minutes=60, max_bpm_jump=2.0)
        ctx = _ctx(previous=previous, request=request)
        assert selector.score_candidate(close, ctx) > selector.score_candidate(far, ctx)

    def test_pick_next_returns_none_when_pool_exhausted(self):
        selector = TrackSelector(HarmonicEngine())
        track = Track(filepath="/a.mp3", bpm=120)
        ctx = _ctx(previous=None)
        result = selector.pick_next([track], used_ids={track.track_id}, ctx=ctx)
        assert result is None

    def test_rank_candidates_sorted_descending(self):
        selector = TrackSelector(HarmonicEngine())
        previous = Track(filepath="/prev.mp3", bpm=100)
        pool = [
            Track(filepath="/a.mp3", bpm=101),
            Track(filepath="/b.mp3", bpm=140),
            Track(filepath="/c.mp3", bpm=102),
        ]
        ctx = _ctx(previous=previous)
        ranked = selector.rank_candidates(pool, used_ids=set(), ctx=ctx)
        scores = [s for _, s in ranked]
        assert scores == sorted(scores, reverse=True)
