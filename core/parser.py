"""
core.parser
===========

Parses VirtualDJ ``database.xml`` files into a list of :class:`core.models.Track`.

VirtualDJ's database schema has drifted slightly across versions (2021,
2023, 2024, 2025) but the overall shape has stayed stable:

.. code-block:: xml

    <VirtualDJ_Database Version="...">
      <Song FilePath="..." FileSize="...">
        <Tags Author="..." Title="..." Album="..." Genre="..."
              Year="..." Bpm="..." Key="..." Remix="..." />
        <Infos SongLength="..." FirstSeen="..." LastPlay="..."
               PlayCount="..." Flag="..." Rating="..." Bitrate="..." />
        <Poi ... />
        <Comment>...</Comment>
      </Song>
      ...
    </VirtualDJ_Database>

Because tags and attribute names have varied release to release, this
parser does **not** assume a fixed schema. It walks every ``<Song>``
element, and for every child element, harvests attributes using a list of
known aliases per logical field. Unknown / missing fields simply default
on the :class:`Track` dataclass.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from lxml import etree

from .camelot import normalize_to_camelot
from .models import Track

logger = logging.getLogger("omniplaylist.parser")


# Each logical field maps to a list of (element_tag, attribute_name) pairs
# to try, in priority order. This is what lets a single parser support
# VirtualDJ 2021 through 2025 without branching on version number.
_FIELD_ALIASES: dict[str, list[tuple[str, str]]] = {
    "artist": [("Tags", "Author"), ("Tags", "Artist"), ("Song", "Artist")],
    "title": [("Tags", "Title"), ("Song", "Title")],
    "remix": [("Tags", "Remix"), ("Tags", "Mix")],
    "album": [("Tags", "Album")],
    "genre": [("Tags", "Genre")],
    "year": [("Tags", "Year")],
    "bpm": [("Tags", "Bpm"), ("Tags", "BPM"), ("Scan", "Bpm")],
    "musical_key": [("Tags", "Key"), ("Tags", "MusicalKey")],
    "length_seconds": [("Infos", "SongLength"), ("Infos", "Length")],
    "rating": [("Infos", "Rating")],
    "play_count": [("Infos", "PlayCount")],
    "last_played": [("Infos", "LastPlay"), ("Infos", "LastPlayed")],
    "date_added": [("Infos", "FirstSeen"), ("Infos", "DateAdded")],
    "flag": [("Infos", "Flag")],
    "comments": [("Comment", None), ("Tags", "Comment")],
}


def _first_matching(
    song_el: etree._Element, aliases: list[tuple[str, str]]
) -> str | None:
    """Return the first attribute value (or text content) found for the aliases list."""
    for tag, attr in aliases:
        for child in song_el.findall(tag):
            if attr is None:
                if child.text and child.text.strip():
                    return child.text.strip()
            else:
                value = child.get(attr)
                if value not in (None, ""):
                    return value
    return None


def _to_float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _to_int(value: str | None, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def _parse_vdj_timestamp(value: str | None) -> datetime | None:
    """VirtualDJ stores timestamps as either unix epoch seconds or ISO-ish strings."""
    if not value:
        return None
    value = value.strip()
    # Epoch seconds
    if value.isdigit():
        try:
            return datetime.fromtimestamp(int(value))
        except (ValueError, OSError, OverflowError):
            return None
    # ISO-like "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS"
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _song_to_track(song_el: etree._Element) -> Track | None:
    filepath = song_el.get("FilePath") or song_el.get("Path")
    if not filepath:
        logger.debug("Skipping <Song> element with no FilePath attribute")
        return None

    file_size = _to_int(song_el.get("FileSize"))

    artist = _first_matching(song_el, _FIELD_ALIASES["artist"]) or ""
    title = _first_matching(song_el, _FIELD_ALIASES["title"]) or ""
    remix = _first_matching(song_el, _FIELD_ALIASES["remix"]) or ""
    album = _first_matching(song_el, _FIELD_ALIASES["album"]) or ""
    genre = _first_matching(song_el, _FIELD_ALIASES["genre"]) or ""

    year_raw = _first_matching(song_el, _FIELD_ALIASES["year"])
    year = _to_int(year_raw, default=None) if year_raw else None

    bpm_raw = _first_matching(song_el, _FIELD_ALIASES["bpm"])
    bpm = _to_float(bpm_raw, default=0.0)

    key_raw = _first_matching(song_el, _FIELD_ALIASES["musical_key"]) or ""
    camelot = normalize_to_camelot(key_raw)

    length = _to_float(_first_matching(song_el, _FIELD_ALIASES["length_seconds"]))
    rating = _to_int(_first_matching(song_el, _FIELD_ALIASES["rating"]))
    play_count = _to_int(_first_matching(song_el, _FIELD_ALIASES["play_count"]))
    last_played = _parse_vdj_timestamp(
        _first_matching(song_el, _FIELD_ALIASES["last_played"])
    )
    date_added = _parse_vdj_timestamp(
        _first_matching(song_el, _FIELD_ALIASES["date_added"])
    )
    flag = _first_matching(song_el, _FIELD_ALIASES["flag"]) or ""
    comments = _first_matching(song_el, _FIELD_ALIASES["comments"]) or ""

    favorite = flag.lower() in ("1", "true", "favorite", "star") if flag else False

    return Track(
        filepath=filepath,
        artist=artist.strip(),
        title=title.strip(),
        remix=remix.strip(),
        album=album.strip(),
        genre=genre.strip(),
        year=year,
        bpm=bpm,
        musical_key=key_raw,
        camelot_key=camelot,
        length_seconds=length,
        rating=rating,
        play_count=play_count,
        last_played=last_played,
        date_added=date_added,
        favorite=favorite,
        folder=str(Path(filepath).parent),
        file_size=file_size,
        comments=comments,
    )


def parse_database(
    xml_path: str | Path, skip_missing_files: bool = False
) -> list[Track]:
    """Parse a VirtualDJ ``database.xml`` file into a list of :class:`Track`.

    Parameters
    ----------
    xml_path:
        Path to ``database.xml``.
    skip_missing_files:
        If True, tracks whose ``filepath`` does not exist on disk are
        dropped. Useful when the library has moved drives.
    """
    xml_path = Path(xml_path)
    if not xml_path.exists():
        raise FileNotFoundError(f"database.xml not found: {xml_path}")

    logger.info("Parsing VirtualDJ database: %s", xml_path)

    parser = etree.XMLParser(recover=True, huge_tree=True)
    tree = etree.parse(str(xml_path), parser)
    root = tree.getroot()

    tracks: list[Track] = []
    songs = root.findall(".//Song")
    logger.info("Found %d <Song> entries", len(songs))

    for song_el in songs:
        track = _song_to_track(song_el)
        if track is None:
            continue
        if skip_missing_files and not Path(track.filepath).exists():
            continue
        tracks.append(track)

    logger.info("Successfully parsed %d tracks", len(tracks))
    return tracks


def deduplicate(tracks: Iterable[Track]) -> list[Track]:
    """Remove tracks with duplicate (artist, title, remix) identity, keeping the first."""
    seen: set[str] = set()
    result: list[Track] = []
    for track in tracks:
        if track.track_id in seen:
            continue
        seen.add(track.track_id)
        result.append(track)
    return result
