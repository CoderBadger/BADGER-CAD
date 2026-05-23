"""canvas_2d.py — Main PyVista orthographic CAD canvas embedded in PyQt6."""
from __future__ import annotations
import os
os.environ.setdefault("QT_API", "pyqt6")

from typing import Optional, Callable

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication
from pyvistaqt import QtInteractor

from badgercad.core.project import Project
from badgercad.cad.grid import add_grid_to_plotter
from badgercad.render.scene import setup_canvas_2d, render_canvas_2d
from badgercad.cad.tools.base_tool import BaseTool


class Canvas2D(QWidget):
    """Top-down orthographic CAD canvas.

    This widget owns the PyVista ``QtInteractor``.  It:
    - Sets up the 2D orthographic view (parallel projection, no rotation).
    - Draws the grid.
    - Translates VTK mouse/keyboard events to world coordinates and forwards
      them to the currently active ``BaseTool``.
    - Exposes ``set_tool()`` / ``deactivate_tool()`` for the ribbon.

    Signals:
        mouse_moved(x, y): World-space cursor position updates (for status bar).
        status_changed(msg): Status bar message from active tool.
    """

    mouse_moved    = pyqtSignal(float, float)
    status_changed = pyqtSignal(str)

    def __init__(self, project: Project, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.project       = project
        self.grid_spacing  = 1.0        # metres — user can change via ribbon
        self._active_tool: Optional[BaseTool] = None
        self._vtk_observers: list[int] = []

        self._build_ui()
        self._setup_scene()
        self._install_vtk_observers()

        # Refresh whenever model changes
        self.project.pilares_changed.connect(self.refresh_scene)
        self.project.losas_changed.connect(self.refresh_scene)
        self.project.nivel_activo_changed.connect(self.refresh_scene)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter)

    def _setup_scene(self) -> None:
        setup_canvas_2d(self.plotter)
        add_grid_to_plotter(
            self.plotter,
            extent=60.0,
            spacing=self.grid_spacing,
            major=5.0,
        )
        render_canvas_2d(self.plotter, self.project)

    # ------------------------------------------------------------------ VTK event wiring
    def _install_vtk_observers(self) -> None:
        iren = self.plotter.iren.interactor
        self._vtk_observers = [
            iren.AddObserver("MouseMoveEvent",       self._vtk_mouse_move),
            iren.AddObserver("LeftButtonPressEvent", self._vtk_left_click),
            iren.AddObserver("KeyPressEvent",        self._vtk_key_press),
        ]

    def _remove_vtk_observers(self) -> None:
        iren = self.plotter.iren.interactor
        for tag in self._vtk_observers:
            iren.RemoveObserver(tag)
        self._vtk_observers.clear()

    # ------------------------------------------------------------------ coord conversion
    def _display_to_world(self, disp_x: int, disp_y: int) -> tuple[float, float]:
        """Convert VTK display (pixel) coords → world XY on the Z=0 plane."""
        renderer = self.plotter.renderer
        renderer.SetDisplayPoint(float(disp_x), float(disp_y), 0.0)
        renderer.DisplayToWorld()
        wp = renderer.GetWorldPoint()
        w  = wp[3] if wp[3] != 0.0 else 1.0
        return wp[0] / w, wp[1] / w

    # ------------------------------------------------------------------ VTK callbacks
    def _vtk_mouse_move(self, obj, event) -> None:
        x, y   = self.plotter.iren.interactor.GetEventPosition()
        wx, wy = self._display_to_world(x, y)
        self.mouse_moved.emit(wx, wy)
        if self._active_tool:
            self._active_tool.on_mouse_move(wx, wy)

    def _vtk_left_click(self, obj, event) -> None:
        x, y   = self.plotter.iren.interactor.GetEventPosition()
        wx, wy = self._display_to_world(x, y)
        if self._active_tool:
            self._active_tool.on_left_click(wx, wy)
        else:
            # Default: forward to VTK for standard interaction (pan, select)
            obj.InvokeEvent("LeftButtonPressEvent")

    def _vtk_key_press(self, obj, event) -> None:
        key = self.plotter.iren.interactor.GetKeySym()
        if self._active_tool:
            self._active_tool.on_key_press(key)
        # Always forward to VTK too (so camera shortcuts still work)
        obj.InvokeEvent("KeyPressEvent")

    # ------------------------------------------------------------------ tool API
    def set_tool(self, tool: BaseTool) -> None:
        """Swap in a new active tool, deactivating the previous one."""
        if self._active_tool is not None:
            self._active_tool.deactivate()
        self._active_tool = tool
        if tool is not None:
            tool.activate()

    def deactivate_tool(self) -> None:
        """Deactivate the current tool and return to idle state."""
        if self._active_tool is not None:
            self._active_tool.deactivate()
            self._active_tool = None
        self.set_status("Listo")

    # ------------------------------------------------------------------ scene
    def refresh_scene(self) -> None:
        """Re-render all element actors while keeping the grid intact."""
        render_canvas_2d(self.plotter, self.project)
        self.plotter.render()

    def update_grid(self, spacing: float) -> None:
        """Change grid spacing and redraw."""
        self.grid_spacing = spacing
        add_grid_to_plotter(self.plotter, spacing=spacing)
        self.plotter.render()

    # ------------------------------------------------------------------ status
    def set_status(self, msg: str) -> None:
        self.status_changed.emit(msg)

    # ------------------------------------------------------------------ cleanup
    def closeEvent(self, event) -> None:  # noqa: N802
        self._remove_vtk_observers()
        self.plotter.close()
        super().closeEvent(event)
