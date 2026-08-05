"""Shared pytest fixtures for OmniPlaylist's test suite."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from core.classifier import classify_tracks
from core.energy import score_tracks
from core.models import Track

GENRE_FOLDERS = [
    "Kenyan/Gengetone",
    "Afrobeats",
    "Amapiano",
    "Afro House",
    "House",
    "Hip Hop",
    "R&B",
    "Reggae",
    "Dancehall",
    "Old School",
    "Gospel",
    "Pop",
]

ARTISTS = [
    "DJ Marvelous",
    "Sauti Sol",
    "Bien",
    "Nyashinski",
    "Khaligraph Jones",
    "Burna Boy",
    "Kabza De Small",
    "Focalistic",
    "Diamond Platnumz",
    "Otile Brown",
    "Wizkid",
    "Davido",
    "Tanasha Donna",
    "King Kaka",
]


def _make_track(i: int, rng: random.Random) -> Track:
    folder = rng.choice(GENRE_FOLDERS)
    artist = rng.choice(ARTISTS)
    bpm = round(rng.uniform(70, 145), 1)
    key_num = rng.randint(1, 12)
    ring = rng.choice(["A", "B"])
    return Track(
        filepath=f"/music/{folder}/{artist} - Track {i}.mp3",
        artist=artist,
        title=f"Track {i}",
        genre=folder.split("/")[-1],
        bpm=bpm,
        musical_key=f"{key_num}{ring}",
        camelot_key=f"{key_num}{ring}",
        length_seconds=rng.uniform(150, 280),
        rating=rng.randint(0, 5),
        play_count=rng.randint(0, 40),
        favorite=rng.random() > 0.85,
        folder=f"/music/{folder}",
    )


@pytest.fixture
def sample_tracks() -> list[Track]:
    """A deterministic pool of 120 synthetic tracks spanning many genres/BPMs."""
    rng = random.Random(42)
    tracks = [_make_track(i, rng) for i in range(120)]
    classify_tracks(tracks)
    score_tracks(tracks)
    return tracks


@pytest.fixture
def sample_database_xml(tmp_path: Path) -> Path:
    """Write a small but structurally realistic VirtualDJ database.xml to disk."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<VirtualDJ_Database Version="2025">
  <Song FilePath="/music/House/Track A.mp3" FileSize="5242880">
    <Tags Author="DJ Marvelous" Title="Track A" Genre="House" Bpm="124.0" Key="8A"/>
    <Infos SongLength="215" Rating="4" PlayCount="12" FirstSeen="1700000000"/>
  </Song>
  <Song FilePath="/music/Amapiano/Track B.mp3" FileSize="6291456">
    <Tags Author="Kabza De Small" Title="Track B" Genre="Amapiano" Bpm="112.5" Key="9B"/>
    <Infos SongLength="260" Rating="5" PlayCount="30" FirstSeen="1701000000"/>
  </Song>
  <Song FilePath="/music/Afrobeats/Track C.mp3" FileSize="4194304">
    <Tags Author="Burna Boy" Title="Track C" Genre="Afrobeats" Bpm="102.0" Key="10A"/>
    <Infos SongLength="190" Rating="3" PlayCount="5" FirstSeen="1702000000"/>
  </Song>
  <Song FilePath="/music/NoMeta/Track D.mp3" FileSize="3145728">
  </Song>
</VirtualDJ_Database>
"""
    path = tmp_path / "database.xml"
    path.write_text(xml, encoding="utf-8")
    return path
