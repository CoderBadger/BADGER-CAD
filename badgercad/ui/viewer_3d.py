"""viewer_3d.py — On-demand 3D perspective viewer (QDialog).

Opens when the user presses "Vista 3D" in the ribbon.
Builds and renders the complete structural model in perspective.
Closing the dialog destroys the QtInteractor → GPU/RAM freed.

Camera behaviour
----------------
``enable_terrain_style()`` is used instead of the default TrackballCamera:
- Left drag   → Orbit (Pitch + Yaw only, **no Roll accumulation**)
- Middle drag → Pan
- Right drag  → Zoom (dolly)
- Wheel       → Zoom
- Z-up vector (0, 0, 1) is enforced after every view preset change.
"""
from __future__ import annotations
import os
os.environ.setdefault("QT_API", "pyqt6")

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QWidget, QFrame,
)
from PyQt6.QtCore import Qt
from pyvistaqt import QtInteractor

from badgercad.core.project import Project
from badgercad.render.scene import render_3d_complete

# ------------------------------------------------------------------ styles
_BAR_STYLE = "background: #12181F; border-bottom: 1px solid #1E2A3A;"
_STAT_STYLE = "color: #4A90D9; font-size: 11px; font-weight: 700;"
_INFO_STYLE = "color: #5A6A7A; font-size: 11px;"
_SEP_STYLE  = "background: #1E2A3A;"

_BTN_VIEW_STYLE = """
QPushButton {
    background: #1A2232;
    color: #A0B4CC;
    border: 1px solid #2A3A50;
    border-radius: 4px;
    padding: 4px 14px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}
QPushButton:hover {
    background: #243048;
    color: #E0ECFF;
    border-color: #4A90D9;
}
QPushButton:pressed {
    background: #4A90D9;
    color: #FFFFFF;
    border-color: #4A90D9;
}
"""

_BTN_CLOSE_STYLE = (
    "QPushButton{background:#1E2838;color:#C0CDE0;border:1px solid #4A90D9;"
    "border-radius:4px;padding:6px 20px;font-weight:700;}"
    "QPushButton:hover{background:#4A90D9;color:#fff;}"
)

# Standard view presets: (label, icon, preset_key)
_VIEW_PRESETS = [
    ("Isométrica",  "◈",  "iso"),
    ("Planta XY",   "▣",  "xy"),
    ("Frente XZ",   "▤",  "xz"),
    ("Perfil YZ",   "▥",  "yz"),
]


class Viewer3D(QDialog):
    """Non-modal 3D perspective viewer.

    This dialog is kept alive as a singleton on ``MainWindow`` (see
    ``_open_3d_viewer``).  When the user closes it, ``plotter.close()``
    frees GPU resources; when it's reopened, ``_render()`` refreshes
    the scene on the *same* OpenGL context.
    """

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("BadgerCAD — Vista 3D del Edificio")
        self.resize(1200, 760)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )
        self._build_ui()
        self._render()
        self._setup_camera()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_info_bar())
        root.addWidget(self._make_view_bar())
        root.addWidget(self._make_sep())

        # ── PyVista plotter ─────────────────────────────────────────────
        self.plotter = QtInteractor(self)
        root.addWidget(self.plotter)

        root.addWidget(self._make_sep())
        root.addWidget(self._make_close_bar())

    def _make_info_bar(self) -> QWidget:
        """Top bar: status note + element counts."""
        bar = QWidget()
        bar.setFixedHeight(32)
        bar.setStyleSheet(_BAR_STYLE)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(8)

        info = QLabel(
            "🏗  Vista 3D — Solo lectura  ·  "
            "Arrastra para orbitar · Rueda para zoom · Botón central para pan"
        )
        info.setStyleSheet(_INFO_STYLE)
        lay.addWidget(info)
        lay.addStretch()

        s = self.project.stats()
        stat = QLabel(
            f"Niveles: {s['niveles']}  |  "
            f"Pilares: {s['pilares']}  |  "
            f"Losas: {s['losas']}"
        )
        stat.setStyleSheet(_STAT_STYLE)
        lay.addWidget(stat)
        return bar

    def _make_view_bar(self) -> QWidget:
        """Quick-view button bar for standard engineering projections."""
        bar = QWidget()
        bar.setFixedHeight(38)
        bar.setStyleSheet("background: #0F151E;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 4, 14, 4)
        lay.setSpacing(6)

        lbl = QLabel("Vista:")
        lbl.setStyleSheet("color: #4A5A6A; font-size: 10px; font-weight: 700;")
        lay.addWidget(lbl)

        for label, icon, key in _VIEW_PRESETS:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setStyleSheet(_BTN_VIEW_STYLE)
            btn.setToolTip(f"Cambiar a vista {label}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Capture key in closure
            btn.clicked.connect(lambda checked, k=key: self._set_view(k))
            lay.addWidget(btn)

        lay.addStretch()

        # Camera lock indicator
        lock_lbl = QLabel("🔒 Z-up bloqueado")
        lock_lbl.setStyleSheet("color: #2A6A3A; font-size: 10px;")
        lay.addWidget(lock_lbl)
        return bar

    def _make_sep(self) -> QFrame:
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(_SEP_STYLE)
        return sep

    def _make_close_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet("background: #0F151E;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 6, 14, 6)
        lay.addStretch()
        btn = QPushButton("  ✕  Cerrar Vista 3D")
        btn.setFixedWidth(180)
        btn.setStyleSheet(_BTN_CLOSE_STYLE)
        btn.clicked.connect(self.close)
        lay.addWidget(btn)
        return bar

    # ------------------------------------------------------------------ render
    def _render(self) -> None:
        """Rebuild the full 3D scene."""
        render_3d_complete(self.plotter, self.project)

    def _setup_camera(self) -> None:
        """Apply terrain-style orbit (no roll) and enforce Z-up vector."""
        # vtkInteractorStyleTerrain: orbit with locked Z-up, no roll accumulation.
        # Left drag  → orbit (pitch + yaw only)
        # Middle     → pan
        # Right/Wheel → zoom
        self.plotter.enable_terrain_style()
        self.plotter.camera.up = (0.0, 0.0, 1.0)
        self.plotter.render()

    # ------------------------------------------------------------------ view presets
    def _set_view(self, preset: str) -> None:
        """Apply a standard engineering view and re-lock Z-up + terrain style.

        Args:
            preset: One of "iso", "xy", "xz", "yz".
        """
        if preset == "iso":
            self.plotter.view_isometric()
            self.plotter.camera.up = (0.0, 0.0, 1.0)

        elif preset == "xy":
            # Plan view: camera looks straight down along -Z.
            # Up vector must be Y (since Z is now the camera axis, not the world up).
            self.plotter.view_xy()
            self.plotter.camera.up = (0.0, 1.0, 0.0)

        elif preset == "xz":
            # Front/elevation: camera looks along -Y axis.
            self.plotter.view_xz()
            self.plotter.camera.up = (0.0, 0.0, 1.0)

        elif preset == "yz":
            # Side/profile: camera looks along -X axis.
            self.plotter.view_yz()
            self.plotter.camera.up = (0.0, 0.0, 1.0)

        # Re-apply terrain style so orbit behaviour matches the new view direction.
        # This also resets the style's internal "up" reference to match.
        self.plotter.enable_terrain_style()
        self.plotter.render()

    # ------------------------------------------------------------------ cleanup
    def closeEvent(self, event) -> None:  # noqa: N802
        self.plotter.close()
        super().closeEvent(event)
