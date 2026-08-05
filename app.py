#!/usr/bin/env python3
"""
OmniPlaylist — Intelligent DJ Playlist Generator
=================================================

Entry point. Launches the PySide6 desktop application.

Usage
-----
    python app.py

Requires the dependencies in requirements.txt (`pip install -r requirements.txt`).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path when run as `python app.py`
# from any working directory (e.g. after a PyInstaller freeze).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gui.main_window import launch_app


def main() -> None:
    launch_app()


if __name__ == "__main__":
    main()
