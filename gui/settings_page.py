"""
gui.settings_page
==================

Settings page: max BPM jump, artist separation, target duration default,
genre percentage overrides, harmonic mixing toggle, dark mode toggle.
Persists to ``config.json`` via :mod:`core.utils`.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.utils import load_config, save_config


class SettingsPage(QWidget):
    """Lets the user tune global generation defaults and appearance."""

    def __init__(self, on_settings_changed=None, parent=None):
        super().__init__(parent)
        self.on_settings_changed = on_settings_changed
        self.config = load_config()
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Defaults applied to every new playlist generation.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        group = QGroupBox("Generation Defaults")
        form = QFormLayout(group)
        form.setSpacing(12)

        self.max_bpm_jump = QDoubleSpinBox()
        self.max_bpm_jump.setRange(0.5, 20.0)
        self.max_bpm_jump.setSingleStep(0.5)
        self.max_bpm_jump.setValue(self.config.get("max_bpm_jump", 2.0))
        form.addRow("Maximum BPM jump", self.max_bpm_jump)

        self.artist_separation = QSpinBox()
        self.artist_separation.setRange(0, 20)
        self.artist_separation.setValue(self.config.get("artist_separation", 3))
        form.addRow("Artist separation (tracks)", self.artist_separation)

        self.duration_tolerance = QSpinBox()
        self.duration_tolerance.setRange(30, 600)
        self.duration_tolerance.setValue(
            self.config.get("duration_tolerance_seconds", 120)
        )
        self.duration_tolerance.setSuffix(" sec")
        form.addRow("Duration tolerance", self.duration_tolerance)

        self.harmonic_mixing = QCheckBox("Enable harmonic (Camelot) mixing")
        self.harmonic_mixing.setChecked(self.config.get("harmonic_mixing", True))
        form.addRow(self.harmonic_mixing)

        root.addWidget(group)

        appearance_group = QGroupBox("Appearance")
        appearance_form = QFormLayout(appearance_group)
        self.dark_mode = QCheckBox("Dark mode")
        self.dark_mode.setChecked(self.config.get("dark_mode", True))
        appearance_form.addRow(self.dark_mode)
        root.addWidget(appearance_group)

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save)
        root.addWidget(save_btn)

        root.addStretch()

    def _save(self) -> None:
        self.config.update(
            {
                "max_bpm_jump": self.max_bpm_jump.value(),
                "artist_separation": self.artist_separation.value(),
                "duration_tolerance_seconds": self.duration_tolerance.value(),
                "harmonic_mixing": self.harmonic_mixing.isChecked(),
                "dark_mode": self.dark_mode.isChecked(),
            }
        )
        save_config(self.config)
        if self.on_settings_changed:
            self.on_settings_changed(self.config)
        QMessageBox.information(
            self, "Settings saved", "Your defaults have been saved to config.json."
        )
