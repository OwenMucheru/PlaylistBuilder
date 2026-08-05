"""
gui.playlist_page
==================

The "Generate Playlist" page: form for generation parameters, a live
preview table (# / Title / Artist / Genre / BPM / Key / Duration /
Running Time), and export buttons (M3U / CSV / JSON / Report).
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.exporter import export_all
from core.harmonic import HarmonicEngine  # noqa: F401 - re-exported for GUI convenience
from core.models import PlaylistRequest, PlaylistResult, Track
from core.playlist_engine import PlaylistEngine
from core.utils import format_duration, list_presets
from gui.widgets import WorkerThread

logger = logging.getLogger("omniplaylist.gui.playlist_page")


class PlaylistPage(QWidget):
    """Generation form + results preview + export actions."""

    def __init__(self, get_tracks_callback, on_generated=None, parent=None):
        super().__init__(parent)
        self._get_tracks = get_tracks_callback
        self._on_generated = on_generated
        self._result: PlaylistResult | None = None
        self._worker: WorkerThread | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Generate Playlist")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Configure a set and let OmniPlaylist program it for you.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        form_box = QGroupBox("Parameters")
        form = QHBoxLayout(form_box)
        form.setSpacing(16)

        # Duration
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Duration (minutes)"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 600)
        self.duration_spin.setValue(60)
        col1.addWidget(self.duration_spin)
        form.addLayout(col1)

        # Preset
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Preset"))
        self.preset_combo = QComboBox()
        presets = list_presets() or ["freestyle"]
        self.preset_combo.addItems(presets)
        if "freestyle" in presets:
            self.preset_combo.setCurrentText("freestyle")
        col2.addWidget(self.preset_combo)
        form.addLayout(col2)

        # Start / End BPM
        col3 = QVBoxLayout()
        col3.addWidget(QLabel("Start BPM (optional)"))
        self.start_bpm_spin = QDoubleSpinBox()
        self.start_bpm_spin.setRange(0, 220)
        self.start_bpm_spin.setSpecialValueText("Auto")
        col3.addWidget(self.start_bpm_spin)
        form.addLayout(col3)

        col4 = QVBoxLayout()
        col4.addWidget(QLabel("End BPM (optional)"))
        self.end_bpm_spin = QDoubleSpinBox()
        self.end_bpm_spin.setRange(0, 220)
        self.end_bpm_spin.setSpecialValueText("Auto")
        col4.addWidget(self.end_bpm_spin)
        form.addLayout(col4)

        # Output name
        col5 = QVBoxLayout()
        col5.addWidget(QLabel("Output name"))
        self.output_name_edit = QLineEdit("OmniPlaylist_Set")
        col5.addWidget(self.output_name_edit)
        form.addLayout(col5)

        root.addWidget(form_box)

        # Action buttons
        actions = QHBoxLayout()
        self.generate_btn = QPushButton("Generate Playlist")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        actions.addWidget(self.generate_btn)

        self.export_m3u_btn = QPushButton("Export M3U")
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_json_btn = QPushButton("Export JSON")
        for btn in (self.export_m3u_btn, self.export_csv_btn, self.export_json_btn):
            btn.setEnabled(False)
            actions.addWidget(btn)
        self.export_m3u_btn.clicked.connect(lambda: self._export("m3u"))
        self.export_csv_btn.clicked.connect(lambda: self._export("csv"))
        self.export_json_btn.clicked.connect(lambda: self._export("json"))

        actions.addStretch()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #9aa0a8;")
        actions.addWidget(self.status_label)
        root.addLayout(actions)

        # Preview table
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["#", "Title", "Artist", "Genre", "BPM", "Key", "Duration", "Running Time"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        root.addWidget(self.table, stretch=1)

    # ------------------------------------------------------------------
    def _on_generate_clicked(self) -> None:
        tracks: list[Track] = self._get_tracks()
        if not tracks:
            QMessageBox.warning(
                self, "No library loaded", "Browse a VirtualDJ database.xml first."
            )
            return

        request = PlaylistRequest(
            duration_minutes=float(self.duration_spin.value()),
            preset_name=self.preset_combo.currentText() or "freestyle",
            start_bpm=self.start_bpm_spin.value() or None,
            end_bpm=self.end_bpm_spin.value() or None,
        )

        self.generate_btn.setEnabled(False)
        self.status_label.setText("Generating…")

        engine = PlaylistEngine(tracks)
        self._worker = WorkerThread(engine.generate, request)
        self._worker.finished_ok.connect(self._on_generation_done)
        self._worker.failed.connect(self._on_generation_failed)
        self._worker.start()

    def _on_generation_done(self, result: PlaylistResult) -> None:
        self._result = result
        self.generate_btn.setEnabled(True)
        self._populate_table(result)

        has_tracks = bool(result.tracks)
        for btn in (self.export_m3u_btn, self.export_csv_btn, self.export_json_btn):
            btn.setEnabled(has_tracks)

        status = f"{result.track_count} tracks · {format_duration(result.total_duration_seconds)}"
        if result.warnings:
            status += f" · {len(result.warnings)} warning(s)"
        self.status_label.setText(status)

        if result.warnings:
            logger.warning("Generation warnings: %s", result.warnings)

        if self._on_generated:
            self._on_generated(result)

    def _on_generation_failed(self, message: str) -> None:
        self.generate_btn.setEnabled(True)
        self.status_label.setText("Generation failed.")
        QMessageBox.critical(self, "Generation failed", message)

    def _populate_table(self, result: PlaylistResult) -> None:
        self.table.setRowCount(0)
        self.table.setRowCount(len(result.tracks))
        for row, t in enumerate(result.tracks):
            values = [
                str(t.playlist_position or row + 1),
                t.title or Path(t.filepath).stem,
                t.artist,
                ", ".join(t.detected_genres) or t.genre,
                f"{t.bpm:.0f}" if t.has_bpm else "--",
                t.camelot_key or "--",
                format_duration(t.length_seconds),
                format_duration(t.running_time_seconds),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (0, 4, 5, 6, 7):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

    # ------------------------------------------------------------------
    def _export(self, fmt: str) -> None:
        if not self._result or not self._result.tracks:
            return

        default_name = self.output_name_edit.text().strip() or "OmniPlaylist_Set"
        ext_map = {
            "m3u": "M3U Playlist (*.m3u)",
            "csv": "CSV File (*.csv)",
            "json": "JSON File (*.json)",
        }
        path_str, _ = QFileDialog.getSaveFileName(
            self, f"Export {fmt.upper()}", f"{default_name}.{fmt}", ext_map[fmt]
        )
        if not path_str:
            return

        target = Path(path_str)
        results = export_all(self._result, target.parent, target.stem)
        QMessageBox.information(self, "Export complete", f"Saved: {results[fmt]}")
