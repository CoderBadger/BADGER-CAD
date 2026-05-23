"""viewer_3d.py — On-demand 3D perspective viewer (QDialog).

Opens when the user presses "Vista 3D" in the ribbon.
Builds and renders the complete structural model in perspective.
Closing the dialog destroys the QtInteractor → GPU/RAM freed.
"""
from __future__ import annotations
import os
os.environ.setdefault("QT_API", "pyqt6")

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QWidget,
)
from PyQt6.QtCore import Qt
from pyvistaqt import QtInteractor

from badgercad.core.project import Project
from badgercad.render.scene import render_3d_complete


class Viewer3D(QDialog):
    """Non-modal 3D perspective viewer.

    This dialog is created fresh each time the user opens it.
    When closed, ``plotter.close()`` frees GPU resources.
    """

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("BadgerCAD — Vista 3D del Edificio")
        self.resize(1100, 700)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )
        self._build_ui()
        self._render()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Info bar
        bar = QWidget()
        bar.setFixedHeight(32)
        bar.setStyleSheet("background:#1A1E2A;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(12, 0, 12, 0)
        lbl = QLabel(
            "⬛ Vista 3D — Solo lectura.  "
            "Usa el ratón para rotar · Rueda para zoom · Click derecho para pan."
        )
        lbl.setStyleSheet("color:#8090A8; font-size:11px;")
        bar_layout.addWidget(lbl)
        bar_layout.addStretch()

        stats = self.project.stats()
        stat_txt = (
            f"  Niveles: {stats['niveles']}  |  "
            f"Pilares: {stats['pilares']}  |  "
            f"Losas: {stats['losas']}"
        )
        stat_lbl = QLabel(stat_txt)
        stat_lbl.setStyleSheet("color:#4A90D9; font-size:11px; font-weight:600;")
        bar_layout.addWidget(stat_lbl)

        root.addWidget(bar)

        # PyVista plotter
        self.plotter = QtInteractor(self)
        root.addWidget(self.plotter)

        # Close button
        btn_bar = QWidget()
        btn_bar.setFixedHeight(44)
        btn_bar.setStyleSheet("background:#1A1E2A;")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(12, 6, 12, 6)
        btn_layout.addStretch()
        close_btn = QPushButton("Cerrar Vista 3D")
        close_btn.setFixedWidth(160)
        close_btn.setStyleSheet(
            "QPushButton{background:#2E3A4E;color:#E0E6F0;border:1px solid #4A90D9;"
            "border-radius:4px;padding:6px 12px;font-weight:600;}"
            "QPushButton:hover{background:#4A90D9;color:#fff;}"
        )
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        root.addWidget(btn_bar)

    def _render(self) -> None:
        render_3d_complete(self.plotter, self.project)

    # ------------------------------------------------------------------ cleanup
    def closeEvent(self, event) -> None:  # noqa: N802
        self.plotter.close()
        super().closeEvent(event)
