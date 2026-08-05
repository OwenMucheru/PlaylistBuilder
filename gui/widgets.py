"""
gui.widgets
===========

Small, reusable widgets shared across pages: sidebar nav buttons, stat
cards for the dashboard, and a QThread worker so long-running work
(parsing a large database, generating a playlist) never blocks the UI.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout


class NavButton(QPushButton):
    """A checkable sidebar navigation entry."""

    def __init__(self, text: str, icon_text: str = "", parent=None):
        super().__init__(f"  {icon_text}  {text}" if icon_text else text, parent)
        self.setObjectName("navButton")
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))


class StatCard(QFrame):
    """Small dashboard card: a big value, a caption, and an optional trend label."""

    def __init__(self, title: str, value: str = "--", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "color: #9aa0a8; font-size: 12px; font-weight: 600;"
        )

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("font-size: 26px; font-weight: 700;")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("color: #9aa0a8; font-size: 11px;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)

    def set_value(self, value: str, subtitle: str | None = None) -> None:
        self.value_label.setText(value)
        if subtitle is not None:
            self.subtitle_label.setText(subtitle)


class WorkerThread(QThread):
    """
    Generic background worker.

    Runs ``fn(*args, **kwargs)`` off the UI thread and emits ``finished_ok``
    with the return value, or ``failed`` with the exception's message.
    Used for database parsing/classification and playlist generation so
    the GUI stays responsive on large libraries.
    """

    finished_ok = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, fn: Callable[..., Any], *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the GUI
            self.failed.emit(str(exc))
