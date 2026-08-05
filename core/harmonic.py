"""
core.harmonic
=============

Thin engine layer on top of :mod:`core.camelot` that scores a *candidate*
track against the *last played* track, folding in whether harmonic mixing
is enabled at all. This is what :mod:`core.selector` calls on every
candidate evaluation.
"""

from __future__ import annotations

from .camelot import harmonic_score, is_compatible
from .models import Track


class HarmonicEngine:
    """Stateless helper around Camelot scoring, parameterized by user settings."""

    def __init__(self, enabled: bool = True, allow_energy_shift: bool = True):
        self.enabled = enabled
        self.allow_energy_shift = allow_energy_shift

    def score(self, previous: Track | None, candidate: Track) -> float:
        """Return a 0-100 harmonic fit score for playing `candidate` after `previous`.

        If harmonic mixing is disabled, or there is no previous track
        (start of set), returns a neutral 100 so it never influences
        ordering.
        """
        if not self.enabled or previous is None:
            return 100.0
        if not previous.has_key or not candidate.has_key:
            return 50.0
        return harmonic_score(previous.camelot_key, candidate.camelot_key)

    def is_transition_allowed(self, previous: Track | None, candidate: Track) -> bool:
        """Hard gate used only when the caller wants strict harmonic enforcement."""
        if not self.enabled or previous is None:
            return True
        if not previous.has_key or not candidate.has_key:
            return True  # unknown key never blocks a transition
        return is_compatible(
            previous.camelot_key, candidate.camelot_key, self.allow_energy_shift
        )
