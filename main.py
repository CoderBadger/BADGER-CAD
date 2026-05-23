"""main.py — BadgerCAD entry point.

Run with:
    python main.py
"""
import sys
import os

# Force PyQt6 as Qt binding for pyvistaqt
os.environ["QT_API"] = "pyqt6"

# High-DPI support
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

import pyvista as pv

from badgercad.ui.main_window import MainWindow


def main() -> None:
    # Configure PyVista for off-screen / Qt integration
    pv.set_plot_theme("dark")

    app = QApplication(sys.argv)
    app.setApplicationName("BadgerCAD")
    app.setApplicationDisplayName("BadgerCAD — Structural Engineering Platform")
    app.setOrganizationName("CoderBadger")

    # Global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Global dark palette (fills gaps not covered by QSS)
    app.setStyle("Fusion")
    _apply_dark_palette(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def _apply_dark_palette(app: QApplication) -> None:
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    dark    = QColor("#0D1117")
    mid     = QColor("#1E2330")
    light   = QColor("#4A90D9")
    text    = QColor("#E0E6F0")
    dim     = QColor("#6A7A90")
    palette.setColor(QPalette.ColorRole.Window,          dark)
    palette.setColor(QPalette.ColorRole.WindowText,      text)
    palette.setColor(QPalette.ColorRole.Base,            mid)
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor("#252932"))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     mid)
    palette.setColor(QPalette.ColorRole.ToolTipText,     text)
    palette.setColor(QPalette.ColorRole.Text,            text)
    palette.setColor(QPalette.ColorRole.Button,          mid)
    palette.setColor(QPalette.ColorRole.ButtonText,      text)
    palette.setColor(QPalette.ColorRole.BrightText,      QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Link,            light)
    palette.setColor(QPalette.ColorRole.Highlight,       light)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, dim)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, dim)
    app.setPalette(palette)


if __name__ == "__main__":
    main()
