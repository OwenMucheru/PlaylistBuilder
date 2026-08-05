"""
core.classifier
================

Automatic genre detection for tracks whose VirtualDJ ``Genre`` tag is
missing, wrong, or too generic. Uses folder names, filenames, artist
names, and existing metadata as signal, with fuzzy matching (RapidFuzz)
against a curated keyword taxonomy so minor spelling variants
("afro-house", "AfroHouse", "afro house") still resolve correctly.

Multiple genres may be detected per track (e.g. a track can be both
"Amapiano" and "Afro House").
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

from rapidfuzz import fuzz

from .models import Track

logger = logging.getLogger("omniplaylist.classifier")


# Canonical genre -> keyword variants that signal it. Keys are the
# canonical display names used everywhere else in OmniPlaylist.
GENRE_TAXONOMY: dict[str, list[str]] = {
    "Kenyan": [
        "kenyan",
        "kenya",
        "genge",
        "gengetone",
        "boomba",
        "arbantone",
        "kapuka",
    ],
    "Afrobeats": ["afrobeats", "afrobeat", "naija", "afropop"],
    "Amapiano": ["amapiano", "piano", "yanos"],
    "Afro House": ["afro house", "afrohouse", "afro-house", "afro tech"],
    "House": ["house", "deep house", "tech house", "electro house"],
    "Hip Hop": ["hip hop", "hiphop", "hip-hop", "rap", "trap"],
    "Dancehall": ["dancehall", "dance hall"],
    "R&B": ["r&b", "rnb", "r n b", "rhythm and blues"],
    "Reggae": ["reggae", "roots reggae", "lovers rock"],
    "Pop": ["pop", "top 40", "chart"],
    "Gospel": ["gospel", "praise", "worship", "christian"],
    "Old School": ["old school", "oldschool", "throwback", "classics", "retro"],
    "Bongo": ["bongo", "bongo flava", "tanzanian"],
    "Zouk": ["zouk", "kizomba"],
    "Soukous": ["soukous", "lingala", "rumba"],
    "Latin": ["latin", "reggaeton", "salsa", "bachata"],
    "EDM": ["edm", "electronic dance", "festival"],
    "Rock": ["rock", "classic rock"],
    "Soul": ["soul", "funk", "motown"],
}

_FUZZY_THRESHOLD = 82  # rapidfuzz partial_ratio threshold for a keyword "hit"

_WORD_SPLIT_RE = re.compile(r"[\\/_\-\.,()\[\]]+")


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = _WORD_SPLIT_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text


_MIN_FUZZY_HAYSTACK_LENGTH = (
    4  # below this, partial_ratio trivially scores ~100 on substrings
)


def _keyword_hits(haystack: str, taxonomy: dict[str, list[str]]) -> set[str]:
    """Return the set of canonical genres whose keywords fuzzy-match haystack."""
    hits: set[str] = set()
    if not haystack:
        return hits
    for canonical, keywords in taxonomy.items():
        for keyword in keywords:
            if keyword in haystack:
                hits.add(canonical)
                break
            # Guard against RapidFuzz's partial_ratio trivially scoring ~100
            # when the haystack is shorter than (or close to) the keyword
            # itself - e.g. a single-letter filename stem "fuzzy-matching"
            # every keyword that happens to share a character. Only trust
            # fuzzy matching once the haystack carries enough signal.
            if len(haystack) < _MIN_FUZZY_HAYSTACK_LENGTH:
                continue
            score = fuzz.partial_ratio(keyword, haystack)
            if score >= _FUZZY_THRESHOLD:
                hits.add(canonical)
                break
    return hits


def detect_genres(
    track: Track, taxonomy: dict[str, list[str]] | None = None
) -> list[str]:
    """Detect one or more canonical genres for a track.

    Signal sources, in order of trust: existing ``genre`` tag, folder
    name, filename, artist name. All signals are combined; the union of
    all matches across sources is returned so a track sitting in an
    "Amapiano" folder but tagged "House" ends up classified as both.
    """
    taxonomy = taxonomy or GENRE_TAXONOMY

    signals = [
        _normalize(track.genre),
        _normalize(track.folder),
        _normalize(track.title),
        _normalize(track.artist),
    ]

    hits: set[str] = set()
    for signal in signals:
        hits |= _keyword_hits(signal, taxonomy)

    if not hits and track.genre:
        # Fall back to the raw tag, title-cased, if nothing in our
        # taxonomy matched but VirtualDJ did have *something* tagged.
        hits.add(track.genre.strip().title())

    return sorted(hits) if hits else ["Unclassified"]


def classify_tracks(
    tracks: Iterable[Track], taxonomy: dict[str, list[str]] | None = None
) -> list[Track]:
    """Populate ``track.detected_genres`` for every track in-place, return the list."""
    tracks = list(tracks)
    for track in tracks:
        track.detected_genres = detect_genres(track, taxonomy)
    logger.info(
        "Classified %d tracks across %d genre categories",
        len(tracks),
        len(taxonomy or GENRE_TAXONOMY),
    )
    return tracks


def genre_distribution(tracks: Iterable[Track]) -> dict[str, int]:
    """Count how many tracks fall into each detected genre (a track may count in >1 bucket)."""
    counts: dict[str, int] = {}
    for track in tracks:
        genres = track.detected_genres or detect_genres(track)
        for genre in genres:
            counts[genre] = counts.get(genre, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))
