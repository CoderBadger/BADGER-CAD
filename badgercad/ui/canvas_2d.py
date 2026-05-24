"""canvas_2d.py — Main PyVista orthographic CAD canvas embedded in PyQt6."""
from __future__ import annotations
import os
os.environ.setdefault("QT_API", "pyqt6")

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from pyvistaqt import QtInteractor

from badgercad.core.project import Project
from badgercad.cad.grid import add_grid_to_plotter
from badgercad.render.scene import setup_canvas_2d, render_canvas_2d
from badgercad.cad.tools.base_tool import BaseTool

# ---------------------------------------------------------------------------
# Custom VTK interactor style
# ---------------------------------------------------------------------------
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleImage


class _CAD2DStyle(vtkInteractorStyleImage):
    """Orthographic 2D interactor style for BadgerCAD.

    Inherits from vtkInteractorStyleImage which provides:
        - Middle button + drag  → Pan
        - Mouse wheel           → Zoom (adjusts parallel scale)

    Left and right button camera operations are disabled completely — those
    button events are handled exclusively by our AddObserver callbacks which
    forward world-space coordinates to the active BaseTool.

    Key events are also suppressed at the style level so our KeyPressEvent
    observer is the single authority on keyboard handling.
    """

    # ── Left button: reserved for tool placement ────────────────────────
    def OnLeftButtonDown(self):   pass
    def OnLeftButtonUp(self):     pass

    # ── Right button: reserved for tool context actions ─────────────────
    def OnRightButtonDown(self):  pass
    def OnRightButtonUp(self):    pass

    # ── Keyboard: handled entirely by our KeyPressEvent observer ────────
    def OnKeyDown(self):          pass
    def OnKeyUp(self):            pass
    def OnChar(self):             pass

    # Middle button pan and mouse wheel zoom are fully inherited from
    # vtkInteractorStyleImage — do NOT override them.


# ---------------------------------------------------------------------------
# VTK keyboard shortcuts that must be blocked even at observer level
# (some VTK versions fire them before the style sees them)
# ---------------------------------------------------------------------------
_VTK_BLOCKED_KEYS = frozenset({
    "q", "e",          # VTK quit window
    "r",               # Reset camera (restores 3D perspective)
    "f",               # Pick focal point (repositions camera)
    "p",               # Point picker
    "3",               # Stereo 3D toggle
    "s", "w",          # Surface / wireframe toggle
    "v",               # Volume rendering
})


class Canvas2D(QWidget):
    """Top-down orthographic CAD canvas.

    Interaction contract
    --------------------
    - Left button   → BaseTool.on_left_click()  (tool placement / selection)
    - Right button  → BaseTool.on_right_click() (context action)
    - Middle button → Pan  (native vtkInteractorStyleImage)
    - Mouse wheel   → Zoom (native vtkInteractorStyleImage)
    - No 3D rotation is possible — _CAD2DStyle disables it at the VTK level.

    Signals
    -------
    mouse_moved(x, y):        World-space cursor for the status bar.
    status_changed(msg):      Status-bar message from the active tool.
    tool_deactivated():       Active tool was deactivated → Ribbon unchecks.
    snap_changed(bool,float): Snap toggle state.
    """

    mouse_moved      = pyqtSignal(float, float)
    status_changed   = pyqtSignal(str)
    tool_deactivated = pyqtSignal()
    snap_changed     = pyqtSignal(bool, float)

    def __init__(self, project: Project, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.project       = project
        self.grid_spacing  = 1.0
        self.snap_enabled  = True
        self._active_tool: Optional[BaseTool] = None
        self._vtk_observers: list[int] = []

        self._build_ui()
        self._setup_scene()
        self._install_vtk_observers()

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
        setup_canvas_2d(self.plotter)   # sets background, parallel projection, camera
        add_grid_to_plotter(self.plotter, extent=60.0,
                            spacing=self.grid_spacing, major=5.0)
        render_canvas_2d(self.plotter, self.project)

    # ------------------------------------------------------------------ VTK wiring
    def _install_vtk_observers(self) -> None:
        iren = self.plotter.iren.interactor

        # ── 1. Install our custom style ─────────────────────────────────
        # This REPLACES whatever style pyvistaqt set (TrackballCamera by
        # default).  _CAD2DStyle silences left/right/key methods so only
        # middle-button pan and mouse-wheel zoom come from the style level.
        style = _CAD2DStyle()
        style.SetInteractor(iren)
        iren.SetInteractorStyle(style)

        # ── 2. Register event observers ─────────────────────────────────
        # Standard priority (0.0) is fine — the style no longer competes
        # with our observers on left/right buttons.
        self._vtk_observers = [
            iren.AddObserver("MouseMoveEvent",        self._vtk_mouse_move),
            iren.AddObserver("LeftButtonPressEvent",  self._vtk_left_click),
            iren.AddObserver("RightButtonPressEvent", self._vtk_right_click),
            iren.AddObserver("KeyPressEvent",         self._vtk_key_press),
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
        # NOTE: do NOT return or abort — the style needs MouseMove for pan.

    def _vtk_left_click(self, obj, event) -> None:
        """Left click → tool placement.  No camera action (style has pass)."""
        x, y   = self.plotter.iren.interactor.GetEventPosition()
        wx, wy = self._display_to_world(x, y)
        if self._active_tool:
            self._active_tool.on_left_click(wx, wy)

    def _vtk_right_click(self, obj, event) -> None:
        """Right click → tool context action.  No camera action (style has pass)."""
        x, y   = self.plotter.iren.interactor.GetEventPosition()
        wx, wy = self._display_to_world(x, y)
        if self._active_tool:
            self._active_tool.on_right_click(wx, wy)

    def _vtk_key_press(self, obj, event) -> None:
        key = self.plotter.iren.interactor.GetKeySym()
        if not key:
            return

        key_l = key.lower()

        # Block any remaining VTK shortcuts that slipped past the style
        if key_l in _VTK_BLOCKED_KEYS:
            return

        # Ctrl+Z — global undo
        ctrl = self.plotter.iren.interactor.GetControlKey()
        if key_l == "z" and ctrl:
            self._handle_ctrl_z()
            return

        # F3 — toggle snap
        if key == "F3":
            self.snap_enabled = not self.snap_enabled
            self.snap_changed.emit(self.snap_enabled, self.grid_spacing)
            self.set_status("Snap: " + ("ON ✓" if self.snap_enabled else "OFF ✗"))
            return

        # PgUp / + → nivel up
        if key in ("Prior", "KP_Prior", "plus", "KP_Add"):
            self._navigate_nivel(+1)
            return

        # PgDn / - → nivel down
        if key in ("Next", "KP_Next", "minus", "KP_Subtract"):
            self._navigate_nivel(-1)
            return

        # Forward to active tool
        if self._active_tool:
            self._active_tool.on_key_press(key)

    # ------------------------------------------------------------------ undo
    def _handle_ctrl_z(self) -> None:
        if self.project.undo():
            self.refresh_scene()
            self.set_status("↩  Deshacer — OK")
        else:
            self.set_status("⚠  No hay más acciones para deshacer")

    # ------------------------------------------------------------------ level navigation
    def _navigate_nivel(self, direction: int) -> None:
        niveles = self.project.niveles_ordenados()
        if not niveles:
            return
        current = self.project.nivel_activo
        try:
            idx = niveles.index(current) if current is not None else 0
        except ValueError:
            idx = 0
        new_idx   = max(0, min(len(niveles) - 1, idx + direction))
        new_nivel = niveles[new_idx]
        if new_nivel is not current:
            self.project.nivel_activo = new_nivel

    # ------------------------------------------------------------------ mouse state
    def release_mouse_state(self) -> None:
        """Inject fake mouse-release events after a modal dialog closes.

        When Qt absorbs the mouse-button-release during a dialog, the VTK
        interactor style thinks the button is still held.  On next mouse move
        it may start an unintended pan operation.
        Calling this immediately after ``dlg.exec()`` resets that state.
        """
        try:
            iren = self.plotter.iren.interactor
            iren.InvokeEvent("LeftButtonReleaseEvent")
            iren.InvokeEvent("RightButtonReleaseEvent")
            iren.InvokeEvent("MiddleButtonReleaseEvent")
        except Exception:
            pass

    # ------------------------------------------------------------------ tool API
    def set_tool(self, tool: BaseTool) -> None:
        if self._active_tool is not None:
            self._active_tool.deactivate()
        self._active_tool = tool
        if tool is not None:
            tool.activate()

    def deactivate_tool(self) -> None:
        """Deactivate the current tool.  Emits tool_deactivated for Ribbon."""
        if self._active_tool is not None:
            self._active_tool.deactivate()
            self._active_tool = None
        self.set_status("Listo")
        self.tool_deactivated.emit()

    # ------------------------------------------------------------------ scene
    def refresh_scene(self) -> None:
        render_canvas_2d(self.plotter, self.project)
        self.plotter.render()

    def update_grid(self, spacing: float) -> None:
        self.grid_spacing = spacing
        add_grid_to_plotter(self.plotter, spacing=spacing)
        self.plotter.render()
        if self.snap_enabled:
            self.snap_changed.emit(True, spacing)

    # ------------------------------------------------------------------ status
    def set_status(self, msg: str) -> None:
        self.status_changed.emit(msg)

    # ------------------------------------------------------------------ cleanup
    def closeEvent(self, event) -> None:  # noqa: N802
        self._remove_vtk_observers()
        self.plotter.close()
        super().closeEvent(event)
