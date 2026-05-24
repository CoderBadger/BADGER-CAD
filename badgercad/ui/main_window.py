"""main_window.py — QMainWindow: wires Ribbon + NivelPanel + Canvas2D + StatusBar."""
from __future__ import annotations
import os
os.environ.setdefault("QT_API", "pyqt6")

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStatusBar, QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from badgercad.core.project import Project, get_project
from badgercad.ui.ribbon import Ribbon
from badgercad.ui.canvas_2d import Canvas2D
from badgercad.ui.panels.nivel_panel import NivelPanel
from badgercad.ui.viewer_3d import Viewer3D

_APP_STYLE = """
QMainWindow { background: #0D1117; }
QStatusBar  { background: #161C26; color: #6A7A90; font-size: 11px;
              border-top: 1px solid #2A3444; }
QStatusBar::item { border: none; }
"""


class MainWindow(QMainWindow):
    """BadgerCAD main application window.

    Layout:
        ┌─────────────────────────────────────┐
        │           Ribbon (fixed 88 px)       │
        ├──────────┬──────────────────────────┤
        │  Nivel   │                          │
        │  Panel   │      Canvas 2D           │
        │ (190 px) │   (fills remaining)      │
        ├──────────┴──────────────────────────┤
        │           Status Bar (24 px)         │
        └─────────────────────────────────────┘
    """

    def __init__(self) -> None:
        super().__init__()
        self.project = get_project()

        self.setWindowTitle("BadgerCAD  —  Hito 1: El Lienzo")
        self.resize(1440, 860)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(_APP_STYLE)

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # ── Ribbon
        self._ribbon = Ribbon(self)
        self.setMenuWidget(self._ribbon)   # places ribbon above central widget

        # ── Central area (nivel panel + canvas)
        central = QWidget()
        central.setStyleSheet("background:#0D1117;")
        h_layout = QHBoxLayout(central)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        self._nivel_panel = NivelPanel(self.project, central)
        self._canvas     = Canvas2D(self.project, central)

        h_layout.addWidget(self._nivel_panel)
        h_layout.addWidget(self._canvas, stretch=1)
        self.setCentralWidget(central)

        # ── Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._lbl_coords = QLabel("X: —.—  Y: —.—")
        self._lbl_coords.setMinimumWidth(160)
        self._lbl_tool   = QLabel("Listo")
        self._lbl_nivel  = QLabel("")
        self._lbl_snap   = QLabel("SNAP: 1.00 m")

        for lbl in (self._lbl_coords, self._lbl_tool, self._lbl_nivel, self._lbl_snap):
            lbl.setStyleSheet("padding: 0 10px;")

        self._status_bar.addWidget(self._lbl_coords)
        self._status_bar.addWidget(_vbar())
        self._status_bar.addWidget(self._lbl_tool)
        self._status_bar.addPermanentWidget(_vbar())
        self._status_bar.addPermanentWidget(self._lbl_nivel)
        self._status_bar.addPermanentWidget(_vbar())
        self._status_bar.addPermanentWidget(self._lbl_snap)

        self._refresh_nivel_label()

    # ------------------------------------------------------------------ signals
    def _connect_signals(self) -> None:
        # Ribbon → tools
        self._ribbon.tool_pilar_requested.connect(self._activate_pilar_tool)
        self._ribbon.tool_borrar_pilar_requested.connect(self._activate_borrar_pilar_tool)
        self._ribbon.tool_losa_requested.connect(self._activate_losa_tool)
        self._ribbon.vista_3d_requested.connect(self._open_3d_viewer)
        self._ribbon.gestionar_plantas.connect(self._open_nivel_manager)
        self._ribbon.datos_generales.connect(self._open_datos_generales)
        self._ribbon.grid_spacing_changed.connect(self._on_grid_changed)
        self._ribbon.nuevo_proyecto.connect(self._nuevo_proyecto)
        self._ribbon.esc_tool.connect(self._canvas.deactivate_tool)
        self._ribbon.esc_tool.connect(self._ribbon.uncheck_all_tools)

        # Canvas → status bar
        self._canvas.mouse_moved.connect(self._on_mouse_moved)
        self._canvas.status_changed.connect(self._on_status_changed)

        # Canvas tool deactivation → uncheck ribbon (covers ESC inside tools)
        self._canvas.tool_deactivated.connect(self._ribbon.uncheck_all_tools)

        # Canvas snap toggle → snap label
        self._canvas.snap_changed.connect(self._on_snap_changed)

        # Project → status bar nivel label
        self.project.nivel_activo_changed.connect(self._refresh_nivel_label)

    # ------------------------------------------------------------------ tool activation
    def _activate_pilar_tool(self) -> None:
        from badgercad.ui.dialogs.pilar_props import PilarPropsDialog
        from badgercad.cad.tools.pilar_tool import PilarTool

        dlg = PilarPropsDialog(self, project=self.project)
        if dlg.exec():
            props = dlg.get_props()
            tool  = PilarTool(self._canvas, props)
            self._canvas.set_tool(tool)
        else:
            self._ribbon.uncheck_all_tools()
        # Release any stuck mouse button state caused by the dialog
        # absorbing the Qt mouse-release event before VTK saw it.
        self._canvas.release_mouse_state()

    def _activate_borrar_pilar_tool(self) -> None:
        from badgercad.cad.tools.borrar_pilar_tool import BorrarPilarTool
        tool = BorrarPilarTool(self._canvas)
        self._canvas.set_tool(tool)

    def _activate_losa_tool(self) -> None:
        from badgercad.cad.tools.losa_tool import LosaTool
        tool = LosaTool(self._canvas)
        self._canvas.set_tool(tool)

    # ------------------------------------------------------------------ dialogs
    def _open_3d_viewer(self) -> None:
        viewer = Viewer3D(self.project, self)
        viewer.show()

    def _open_nivel_manager(self) -> None:
        from badgercad.ui.dialogs.nivel_manager import NivelManagerDialog
        dlg = NivelManagerDialog(self.project, self)
        dlg.exec()

    def _open_datos_generales(self) -> None:
        QMessageBox.information(
            self, "Datos Generales",
            "Módulo de Datos Generales (normativa, materiales, hipótesis de carga)\n"
            "estará disponible en el Hito 3."
        )

    def _nuevo_proyecto(self) -> None:
        reply = QMessageBox.question(
            self, "Nuevo Proyecto",
            "¿Descartar el proyecto actual y crear uno nuevo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._canvas.deactivate_tool()
            self.project.reset()
            self._canvas.refresh_scene()

    # ------------------------------------------------------------------ status bar
    def _on_mouse_moved(self, wx: float, wy: float) -> None:
        self._lbl_coords.setText(f"X: {wx:+8.3f} m   Y: {wy:+8.3f} m")

    def _on_status_changed(self, msg: str) -> None:
        self._lbl_tool.setText(msg)

    def _on_grid_changed(self, spacing: float) -> None:
        self._canvas.update_grid(spacing)
        # Snap label is updated reactively via snap_changed signal when enabled
        # Update directly here too for immediate feedback:
        if self._canvas.snap_enabled:
            self._lbl_snap.setText(f"SNAP: {spacing:.2f} m")

    def _on_snap_changed(self, enabled: bool, spacing: float) -> None:
        if enabled:
            self._lbl_snap.setText(f"SNAP: {spacing:.2f} m")
        else:
            self._lbl_snap.setText("SNAP: OFF")

    def _refresh_nivel_label(self) -> None:
        nivel = self.project.nivel_activo
        if nivel:
            self._lbl_nivel.setText(
                f"📐  {nivel.nombre}  ({nivel.cota:+.2f} m)"
            )
        else:
            self._lbl_nivel.setText("Sin nivel activo")

    # ------------------------------------------------------------------ close
    def closeEvent(self, event) -> None:  # noqa: N802
        self._canvas.deactivate_tool()
        super().closeEvent(event)


def _vbar() -> QWidget:
    """Thin vertical separator for the status bar."""
    f = QWidget()
    f.setFixedWidth(1)
    f.setStyleSheet("background:#2A3444;")
    return f
