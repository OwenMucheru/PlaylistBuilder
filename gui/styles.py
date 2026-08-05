"""
gui.styles
==========

Centralized Qt stylesheet (QSS) for OmniPlaylist's dark theme, plus a
small palette dict other widgets can reference for chart/plot colors.
"""

from __future__ import annotations

PALETTE = {
    "bg": "#121417",
    "bg_alt": "#181b20",
    "surface": "#1e2227",
    "surface_alt": "#262b32",
    "border": "#31363d",
    "text": "#e8e9eb",
    "text_dim": "#9aa0a8",
    "accent": "#4f8cff",
    "accent_hover": "#6ea0ff",
    "accent_dim": "#2c3e63",
    "success": "#4fd68c",
    "warning": "#f5b942",
    "danger": "#f0596b",
}

DARK_QSS = f"""
* {{
    font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
    color: {PALETTE['text']};
}}

QMainWindow, QWidget#centralWidget {{
    background-color: {PALETTE['bg']};
}}

QWidget#sidebar {{
    background-color: {PALETTE['bg_alt']};
    border-right: 1px solid {PALETTE['border']};
}}

QPushButton#navButton {{
    text-align: left;
    padding: 10px 16px;
    border: none;
    border-radius: 6px;
    background-color: transparent;
    font-size: 13px;
}}

QPushButton#navButton:hover {{
    background-color: {PALETTE['surface_alt']};
}}

QPushButton#navButton:checked {{
    background-color: {PALETTE['accent_dim']};
    color: {PALETTE['accent_hover']};
    font-weight: 600;
}}

QPushButton {{
    background-color: {PALETTE['surface_alt']};
    border: 1px solid {PALETTE['border']};
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {PALETTE['border']};
}}

QPushButton:pressed {{
    background-color: {PALETTE['bg_alt']};
}}

QPushButton#primaryButton {{
    background-color: {PALETTE['accent']};
    border: none;
    color: white;
    font-weight: 600;
}}

QPushButton#primaryButton:hover {{
    background-color: {PALETTE['accent_hover']};
}}

QPushButton#primaryButton:disabled {{
    background-color: {PALETTE['surface_alt']};
    color: {PALETTE['text_dim']};
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 5px;
    padding: 6px 8px;
    selection-background-color: {PALETTE['accent']};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {PALETTE['accent']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QCheckBox {{
    spacing: 8px;
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {PALETTE['border']};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {PALETTE['accent']};
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}}

QTableWidget, QTableView {{
    background-color: {PALETTE['surface']};
    alternate-background-color: {PALETTE['bg_alt']};
    gridline-color: {PALETTE['border']};
    border: 1px solid {PALETTE['border']};
    border-radius: 6px;
    selection-background-color: {PALETTE['accent_dim']};
    selection-color: {PALETTE['text']};
}}

QHeaderView::section {{
    background-color: {PALETTE['surface_alt']};
    color: {PALETTE['text_dim']};
    padding: 6px;
    border: none;
    border-bottom: 1px solid {PALETTE['border']};
    font-weight: 600;
}}

QTabWidget::pane {{
    border: 1px solid {PALETTE['border']};
    border-radius: 6px;
}}

QGroupBox {{
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {PALETTE['text_dim']};
}}

QLabel#pageTitle {{
    font-size: 22px;
    font-weight: 700;
}}

QLabel#pageSubtitle {{
    color: {PALETTE['text_dim']};
    font-size: 12px;
}}

QLabel#statCard {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    padding: 14px;
}}

QProgressBar {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 5px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {PALETTE['accent']};
    border-radius: 5px;
}}

QScrollBar:vertical {{
    background: {PALETTE['bg']};
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: {PALETTE['border']};
    border-radius: 5px;
    min-height: 24px;
}}

QToolTip {{
    background-color: {PALETTE['surface_alt']};
    color: {PALETTE['text']};
    border: 1px solid {PALETTE['border']};
    padding: 4px;
}}
"""
