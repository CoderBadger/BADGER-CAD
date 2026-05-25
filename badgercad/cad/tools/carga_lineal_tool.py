"""carga_lineal_tool.py — Tool for continuous drawing of linear loads.
"""
from __future__ import annotations
from typing import Optional, Tuple

from .base_tool import BaseTool
from badgercad.core.loads import CargaLineal, Hipotesis
import pyvista as pv


class CargaLinealTool(BaseTool):
    """Draw continuous linear loads snapping to grid."""

    def __init__(self, canvas) -> None:
        super().__init__(canvas)
        self._start_node: Optional[Tuple[float, float]] = None
        self._cursor_pos: Tuple[float, float] = (0.0, 0.0)
        self._current_props = {
            "magnitud": 5.0,
            "hipotesis": Hipotesis.CM
        }

    # ------------------------------------------------------------------ lifecycle
    def activate(self) -> None:
        self._start_node = None
        # Force dialog on first activation
        if not self._open_props_dialog():
            self._canvas.deactivate_tool()
            return
        self._update_status()

    def deactivate(self) -> None:
        self._start_node = None
        try:
            self.plotter.remove_actor("ghost_carga_line")
        except Exception:
            pass

    def _open_props_dialog(self) -> bool:
        from badgercad.ui.dialogs.carga_lineal_props import CargaLinealPropsDialog
        dlg = CargaLinealPropsDialog(self._canvas.window(), self._current_props)
        if dlg.exec():
            self._current_props = dlg.get_props()
            self._canvas.release_mouse_state()
            return True
        self._canvas.release_mouse_state()
        return False

    # ------------------------------------------------------------------ events
    def on_mouse_move(self, world_x: float, world_y: float) -> None:
        sx, sy = self._snap(world_x, world_y)
        self._cursor_pos = (sx, sy)

        if self._start_node is not None:
            self._draw_ghost(self._start_node, self._cursor_pos)
            self.plotter.render()

    def on_left_click(self, world_x: float, world_y: float) -> None:
        if self.project.grupo_activo is None:
            self._canvas.set_status("⚠ Active un Nivel/Grupo primero.")
            return

        sx, sy = self._snap(world_x, world_y)

        if self._start_node is None:
            # Start new chain
            self._start_node = (sx, sy)
            self._update_status()
        else:
            # Finish segment
            if self._start_node != (sx, sy):
                self._commit_segment(self._start_node, (sx, sy))
                self._refresh()
                # Continuous drawing: new start is current end
                self._start_node = (sx, sy)
                self._update_status()

    def on_right_click(self, world_x: float, world_y: float) -> None:
        """Right click re-opens the properties dialog."""
        self._open_props_dialog()
        self._update_status()

    def on_key_press(self, key: str) -> None:
        key_l = key.lower()
        if key_l in ("return", "enter"):
            self._break_chain()
        elif key_l == "escape":
            if self._start_node is not None:
                self._break_chain()
            else:
                self._canvas.deactivate_tool()

    # ------------------------------------------------------------------ internal
    def _commit_segment(self, p_a: Tuple[float, float], p_b: Tuple[float, float]) -> None:
        """Add load segment A-B."""
        grupo_id = self.project.grupo_activo.id
        
        carga = CargaLineal(
            p1=p_a,
            p2=p_b,
            magnitud=self._current_props["magnitud"],
            hipotesis=self._current_props["hipotesis"],
            grupo_id=grupo_id
        )
        self.project.add_carga_lineal(carga)

    def _break_chain(self) -> None:
        self._start_node = None
        try:
            self.plotter.remove_actor("ghost_carga_line")
            self.plotter.render()
        except Exception:
            pass
        self._update_status()

    def _update_status(self) -> None:
        if self._start_node is None:
            self._canvas.set_status("🔴 Carga Lineal — Clic inicial · RClick = Propiedades · ESC = salir")
        else:
            self._canvas.set_status("🔴 Carga Lineal — Clic final · RClick = Propiedades · ESC = soltar")

    def _draw_ghost(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> None:
        self.plotter.remove_actor("ghost_carga_line")
        if p1 == p2:
            return
        
        import numpy as np
        arr = np.array([[p1[0], p1[1], 0.05], [p2[0], p2[1], 0.05]], dtype=float)
        poly = pv.PolyData()
        poly.points = arr
        poly.lines = np.array([2, 0, 1], dtype=int)
        
        self.plotter.add_mesh(
            poly, color="#FF4500", line_width=3.0,
            name="ghost_carga_line", render_lines_as_tubes=False,
        )
