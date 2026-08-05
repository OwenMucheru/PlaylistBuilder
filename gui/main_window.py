"""
gui.main_window
================

The top-level QMainWindow: sidebar navigation (Dashboard / Generate
Playlist / Presets / Settings / History), a stacked page area, and the
"Browse Database" action that drives everything else.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.classifier import classify_tracks, genre_distribution
from core.energy import score_tracks
from core.models import Track
from core.parser import parse_database
from core.utils import (
    list_presets,
    load_config,
    load_preset,
    save_config,
    setup_logging,
)
from gui.playlist_page import PlaylistPage
from gui.settings_page import SettingsPage
from gui.styles import DARK_QSS
from gui.widgets import NavButton, StatCard, WorkerThread

logger = logging.getLogger("omniplaylist.gui.main_window")

HISTORY_FILE = Path("output") / "history.json"


# ----------------------------------------------------------------------
# Dashboard page
# ----------------------------------------------------------------------
class DashboardPage(QWidget):
    """Landing page: library stats + quick "Browse Database" action."""

    def __init__(self, on_browse, parent=None):
        super().__init__(parent)
        self.on_browse = on_browse
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Your VirtualDJ library, at a glance.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        browse_row = QHBoxLayout()
        self.browse_btn = QPushButton("Browse Database…")
        self.browse_btn.setObjectName("primaryButton")
        self.browse_btn.clicked.connect(self.on_browse)
        browse_row.addWidget(self.browse_btn)
        browse_row.addStretch()
        root.addLayout(browse_row)

        self.db_path_label = QLabel("No database loaded.")
        self.db_path_label.setStyleSheet("color: #9aa0a8;")
        root.addWidget(self.db_path_label)

        cards_row = QHBoxLayout()
        self.tracks_card = StatCard("Total Tracks", "0")
        self.duration_card = StatCard("Library Duration", "0h 0m")
        self.genres_card = StatCard("Detected Genres", "0")
        self.avg_bpm_card = StatCard("Average BPM", "--")
        for card in (
            self.tracks_card,
            self.duration_card,
            self.genres_card,
            self.avg_bpm_card,
        ):
            cards_row.addWidget(card)
        root.addLayout(cards_row)

        root.addWidget(QLabel("Top Genres"))
        self.genre_list = QListWidget()
        root.addWidget(self.genre_list, stretch=1)

    def update_stats(self, tracks: list[Track], db_path: str) -> None:
        self.db_path_label.setText(f"Loaded: {db_path}")
        self.tracks_card.set_value(str(len(tracks)))

        total_seconds = sum(t.length_seconds for t in tracks)
        hours, remainder = divmod(int(total_seconds), 3600)
        minutes = remainder // 60
        self.duration_card.set_value(f"{hours}h {minutes}m")

        dist = genre_distribution(tracks)
        self.genres_card.set_value(str(len(dist)))

        bpms = [t.bpm for t in tracks if t.has_bpm]
        avg_bpm = sum(bpms) / len(bpms) if bpms else 0
        self.avg_bpm_card.set_value(f"{avg_bpm:.0f}" if avg_bpm else "--")

        self.genre_list.clear()
        for genre, count in list(dist.items())[:15]:
            pct = (count / len(tracks) * 100) if tracks else 0
            self.genre_list.addItem(
                QListWidgetItem(f"{genre:<20}  {count:>5} tracks  ({pct:.1f}%)")
            )


# ----------------------------------------------------------------------
# Presets page
# ----------------------------------------------------------------------
class PresetsPage(QWidget):
    """Read-only browser of the JSON presets shipped in /presets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Presets")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Built-in event presets that shape genre mix, BPM range, and energy curve."
        )
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        body = QHBoxLayout()
        self.preset_list = QListWidget()
        self.preset_list.setFixedWidth(220)
        for name in list_presets():
            self.preset_list.addItem(name)
        self.preset_list.currentTextChanged.connect(self._show_preset)
        body.addWidget(self.preset_list)

        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        body.addWidget(self.detail_view, stretch=1)

        root.addLayout(body, stretch=1)

        if self.preset_list.count():
            self.preset_list.setCurrentRow(0)

    def _show_preset(self, name: str) -> None:
        if not name:
            return
        try:
            data = load_preset(name)
        except (FileNotFoundError, ValueError) as exc:
            self.detail_view.setPlainText(f"Could not load preset: {exc}")
            return
        self.detail_view.setPlainText(json.dumps(data, indent=2))


# ----------------------------------------------------------------------
# History page
# ----------------------------------------------------------------------
class HistoryPage(QWidget):
    """Shows previously generated playlists (persisted to output/history.json)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("History")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Playlists generated in past sessions.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        self.list_widget = QListWidget()
        root.addWidget(self.list_widget, stretch=1)

    def refresh(self) -> None:
        self.list_widget.clear()
        entries = _load_history()
        if not entries:
            self.list_widget.addItem("No playlists generated yet.")
            return
        for entry in reversed(entries):
            text = (
                f"{entry.get('timestamp', '?')}  ·  {entry.get('preset', '?')}  ·  "
                f"{entry.get('track_count', 0)} tracks  ·  {entry.get('duration', '?')}"
            )
            self.list_widget.addItem(text)


def _load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def record_history(preset: str, track_count: int, duration: str) -> None:
    entries = _load_history()
    entries.append(
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "preset": preset,
            "track_count": track_count,
            "duration": duration,
        }
    )
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(entries[-100:], indent=2), encoding="utf-8")


# ----------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------
class MainWindow(QWidget):
    """Application shell: sidebar + stacked pages."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OmniPlaylist — Intelligent DJ Playlist Generator")
        self.resize(1200, 780)

        self.config = load_config()
        self.tracks: list[Track] = []
        self.db_path: str = self.config.get("last_database_path", "")

        self._worker: WorkerThread | None = None

        self._build_ui()
        self.setStyleSheet(DARK_QSS)

        if self.db_path and Path(self.db_path).exists():
            self._load_database(self.db_path)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --- Sidebar ---
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 20, 12, 20)
        side_layout.setSpacing(4)

        logo = QLabel("🎧  OmniPlaylist")
        logo.setStyleSheet(
            "font-size: 16px; font-weight: 700; padding: 0 8px 20px 8px;"
        )
        side_layout.addWidget(logo)

        self.nav_buttons: dict[str, NavButton] = {}
        nav_items = [
            ("dashboard", "Dashboard", "🏠"),
            ("generate", "Generate Playlist", "🎚️"),
            ("presets", "Presets", "🗂️"),
            ("settings", "Settings", "⚙️"),
            ("history", "History", "🕘"),
        ]
        for key, label, icon in nav_items:
            btn = NavButton(label, icon)
            btn.clicked.connect(lambda _checked, k=key: self._switch_page(k))
            side_layout.addWidget(btn)
            self.nav_buttons[key] = btn
        side_layout.addStretch()

        outer.addWidget(sidebar)

        # --- Stacked pages ---
        self.stack = QStackedWidget()
        outer.addWidget(self.stack, stretch=1)

        self.dashboard_page = DashboardPage(self._browse_database)
        self.playlist_page = PlaylistPage(
            lambda: self.tracks, self._on_playlist_generated
        )
        self.presets_page = PresetsPage()
        self.settings_page = SettingsPage(self._on_settings_changed)
        self.history_page = HistoryPage()

        self.page_order = ["dashboard", "generate", "presets", "settings", "history"]
        for key, page in zip(
            self.page_order,
            [
                self.dashboard_page,
                self.playlist_page,
                self.presets_page,
                self.settings_page,
                self.history_page,
            ],
        ):
            self.stack.addWidget(page)

        self._switch_page("dashboard")

    def _switch_page(self, key: str) -> None:
        index = self.page_order.index(key)
        self.stack.setCurrentIndex(index)
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)
        if key == "history":
            self.history_page.refresh()

    # ------------------------------------------------------------------
    def _browse_database(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Select VirtualDJ database.xml", "", "VirtualDJ Database (*.xml)"
        )
        if not path_str:
            return
        self._load_database(path_str)

    def _load_database(self, path_str: str) -> None:
        self.dashboard_page.browse_btn.setEnabled(False)
        self.dashboard_page.db_path_label.setText("Parsing database…")

        self._worker = WorkerThread(self._parse_and_classify, path_str)
        self._worker.finished_ok.connect(
            lambda tracks: self._on_database_loaded(tracks, path_str)
        )
        self._worker.failed.connect(self._on_database_failed)
        self._worker.start()

    @staticmethod
    def _parse_and_classify(path_str: str) -> list[Track]:
        tracks = parse_database(path_str)
        classify_tracks(tracks)
        score_tracks(tracks)
        return tracks

    def _on_database_loaded(self, tracks: list[Track], path_str: str) -> None:
        self.tracks = tracks
        self.db_path = path_str
        self.dashboard_page.browse_btn.setEnabled(True)
        self.dashboard_page.update_stats(tracks, path_str)

        self.config["last_database_path"] = path_str
        save_config(self.config)

        logger.info("Loaded %d tracks from %s", len(tracks), path_str)

    def _on_database_failed(self, message: str) -> None:
        self.dashboard_page.browse_btn.setEnabled(True)
        self.dashboard_page.db_path_label.setText("Failed to load database.")
        QMessageBox.critical(self, "Failed to parse database", message)

    def _on_settings_changed(self, config: dict) -> None:
        self.config = config

    def _on_playlist_generated(self, result) -> None:
        from core.utils import format_duration

        record_history(
            result.preset_name,
            result.track_count,
            format_duration(result.total_duration_seconds),
        )


def launch_app() -> None:
    """Entry point used by app.py."""
    import sys

    from PySide6.QtWidgets import QApplication

    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("OmniPlaylist")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
