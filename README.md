# OmniPlaylist

**Intelligent DJ Playlist Generator for VirtualDJ**

OmniPlaylist reads a VirtualDJ `database.xml` and automatically programs
professional, VirtualDJ-compatible `.m3u` playlists — arranging songs by
BPM progression, harmonic (Camelot) compatibility, genre balance, artist
spacing, and a target energy curve (Warmup → Build → Peak → Finale), the
way an experienced DJ would build a set.

Built for wedding DJs, club DJs, corporate DJs, mobile DJs, and radio DJs.

---

## Features

- **VirtualDJ database parser** — tolerant of schema drift across VirtualDJ
  2021 / 2023 / 2024 / 2025; extracts artist, title, remix, album, genre,
  year, BPM, musical key, length, rating, play count, timestamps, and more.
- **Genre detection** — fuzzy-matches folder names, filenames, and artist
  names against a curated taxonomy (Kenyan/Gengetone, Afrobeats, Amapiano,
  Afro House, House, Hip Hop, Dancehall, R&B, Reggae, Gospel, Old School,
  and more), assigning multiple genres per track where applicable.
- **BPM engine** — sorts and sequences tracks to avoid large BPM jumps,
  with a configurable maximum jump (default 2 BPM).
- **Camelot harmonic mixing engine** — same key, ±1, relative major/minor,
  and energy boost/drop transitions; can be disabled entirely.
- **Energy engine** — scores every track 0–100 from BPM, genre, and
  popularity, and places tracks along a 4-phase energy curve.
- **Playlist engine** — greedily builds a set to a target duration
  (±configurable tolerance), avoiding duplicate songs and enforcing
  minimum artist spacing.
- **6 built-in presets** — Wedding, Club, Graduation, Corporate,
  Freestyle, Birthday — each defining genre percentages, target BPM
  range, energy curve, and artist spacing.
- **Dark-themed PySide6 desktop app** — Dashboard, Generate Playlist,
  Presets, Settings, and History pages.
- **Export** to `.m3u` (VirtualDJ-ready), `.csv`, `.json`, and a
  plain-text playlist report.

---

## Project structure

```
OmniPlaylist/
├── app.py                  # Entry point
├── config.json              # App-level defaults
├── requirements.txt
├── build.bat                 # Windows: create venv + install deps
├── build_exe.bat              # Windows: PyInstaller build
├── core/
│   ├── parser.py             # database.xml -> Track objects
│   ├── models.py              # Track / PlaylistRequest / PlaylistResult
│   ├── classifier.py           # Genre detection
│   ├── camelot.py               # Camelot Wheel key logic
│   ├── harmonic.py               # Harmonic scoring engine
│   ├── energy.py                  # Energy scoring + curve
│   ├── selector.py                 # Candidate ranking
│   ├── playlist_engine.py           # Orchestrator
│   ├── exporter.py                   # M3U / CSV / JSON / report export
│   └── utils.py                       # Logging, presets, config helpers
├── gui/
│   ├── main_window.py         # Sidebar + Dashboard/Presets/History
│   ├── playlist_page.py        # Generate Playlist page
│   ├── settings_page.py         # Settings page
│   ├── widgets.py                # Shared small widgets
│   └── styles.py                  # Dark theme QSS
├── presets/                # wedding.json, club.json, graduation.json,
│                            # corporate.json, freestyle.json, birthday.json
├── tests/                  # pytest suite (82 tests)
└── output/                 # Generated playlists land here
```

---

## Getting started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

(Windows users can instead run `build.bat`, which creates a virtual
environment and installs everything automatically.)

### 2. Run the app

```bash
python app.py
```

### 3. Generate a playlist

1. **Dashboard** → click **Browse Database…** and select your VirtualDJ
   `database.xml` (typically `%APPDATA%\VirtualDJ\database.xml` on
   Windows, or `~/Library/Application Support/VirtualDJ/database.xml`
   on macOS).
2. **Generate Playlist** → set a duration, pick a preset, optionally set
   start/end BPM, then click **Generate Playlist**.
3. Review the preview table, then **Export M3U** to save a VirtualDJ-ready
   playlist (or export CSV/JSON for other tools).

---

## Running the tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

All 82 tests should pass. The suite covers key normalization, genre
detection, energy scoring, the playlist engine end-to-end, candidate
selection rules, and every export format.

---

## Building a standalone executable (Windows)

```bash
build.bat        # first time: sets up the virtual environment
build_exe.bat     # builds dist\OmniPlaylist\OmniPlaylist.exe with PyInstaller
```

---

## Configuration

`config.json` holds app-level defaults, editable from the **Settings**
page or directly:

| Key | Default | Description |
|---|---|---|
| `max_bpm_jump` | `2.0` | Max BPM difference the selector favors between consecutive tracks |
| `artist_separation` | `3` | Minimum tracks between repeats of the same artist |
| `harmonic_mixing` | `true` | Enable/disable Camelot-based harmonic scoring |
| `duration_tolerance_seconds` | `120` | How close the final duration must land to the target (±) |
| `dark_mode` | `true` | GUI theme |
| `default_preset` | `"freestyle"` | Preset selected by default |

---

## Presets

Each file in `presets/` defines:

```json
{
  "display_name": "...",
  "target_bpm_range": [min, max],
  "genre_percentages": { "Genre": weight, ... },
  "artist_separation": 3,
  "energy_curve": [
    { "phase": "warmup", "start_fraction": 0.0, "end_fraction": 0.15,
      "target_energy_min": 20, "target_energy_max": 45 },
    ...
  ]
}
```

Add your own preset by dropping a new `<name>.json` file into `presets/`
following this shape — it will automatically appear in the app's preset
list.

---

## Architecture notes

- **Parser is alias-based, not schema-fixed.** VirtualDJ's XML attribute
  names have drifted release to release. Rather than branching on version
  number, `core/parser.py` tries an ordered list of `(element, attribute)`
  aliases per logical field, so it keeps working as VirtualDJ evolves.
- **Selection is scored, not rule-chained.** Instead of applying BPM,
  harmonic, and energy rules as sequential hard filters (which tends to
  produce brittle, empty results on smaller libraries), `core/selector.py`
  scores every eligible candidate on a weighted blend of BPM continuity,
  harmonic fit, energy-curve fit, and track quality, and picks the best
  overall next track. Hard filters are reserved for true dealbreakers
  (duplicates, extreme BPM jumps, artist spacing, genre filters).
- **Presets are data, not code.** Adding or tuning an event type never
  requires touching the engine — just the JSON.

---

## License

MIT — see `LICENSE`.
