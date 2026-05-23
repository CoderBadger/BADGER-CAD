"""losa_tool.py — Polygonal slab drawing tool.

Workflow:
  1. User activates tool from ribbon.
  2. Each LEFT CLICK adds a vertex; a dynamic preview line follows the cursor.
  3. ENTER or double-click closes the polygon and opens LosaPropsDialog.
  4. On dialog accept, the Losa is added to the active Grupo.
  5. ESC cancels without saving.
"""
from __future__ import annotations
from typing import List, Optional, Tuple

from .base_tool import BaseTool
from badgercad.core.elements.losa import Losa
from badgercad.render.scene import add_ghost_losa_line


class LosaTool(BaseTool):
    """Draw a slab polygon vertex-by-vertex."""

    def __init__(self, canvas) -> None:
        super().__init__(canvas)
        self._vertices: List[Tuple[float, float]] = []
        self._cursor_pos: Tuple[float, float] = (0.0, 0.0)

    # ------------------------------------------------------------------ lifecycle
    def activate(self) -> None:
        self._vertices.clear()
        self._canvas.set_status(
            "▭ Losa — Clic para añadir vértices · ENTER para cerrar · ESC para cancelar"
        )

    def deactivate(self) -> None:
        self._vertices.clear()
        self.plotter.remove_actor("ghost_losa_line")

    # ------------------------------------------------------------------ events
    def on_mouse_move(self, world_x: float, world_y: float) -> None:
        sx, sy = self._snap(world_x, world_y)
        self._cursor_pos = (sx, sy)
        if self._vertices:
            add_ghost_losa_line(
                self.plotter, self._vertices, preview_end=(sx, sy)
            )
            self.plotter.render()

    def on_left_click(self, world_x: float, world_y: float) -> None:
        sx, sy = self._snap(world_x, world_y)
        self._vertices.append((sx, sy))
        add_ghost_losa_line(self.plotter, self._vertices)
        self.plotter.render()
        self._canvas.set_status(
            f"▭ Losa — {len(self._vertices)} vértice(s) · "
            "ENTER para cerrar · ESC para cancelar"
        )

    def on_key_press(self, key: str) -> None:
        if key.lower() in ("return", "enter"):
            self._close_polygon()
        elif key.lower() == "escape":
            self._canvas.deactivate_tool()

    # ------------------------------------------------------------------ internal
    def _close_polygon(self) -> None:
        if len(self._vertices) < 3:
            self._canvas.set_status(
                "⚠ Se necesitan al menos 3 vértices para cerrar la losa."
            )
            return

        # Ask for slab properties via dialog
        from badgercad.ui.dialogs.losa_props import LosaPropsDialog
        dlg = LosaPropsDialog(
            self._canvas,
            grupo_activo=self.project.grupo_activo,
        )
        if dlg.exec():
            props = dlg.get_props()
            losa = Losa(
                vertices=list(self._vertices),
                tipo=props["tipo"],
                espesor=props["espesor"],
                grupo_id=props["grupo_id"],
            )
            self.project.add_losa(losa)
            self._refresh()

        # Reset for next polygon
        self._vertices.clear()
        self.plotter.remove_actor("ghost_losa_line")
        self._canvas.set_status(
            "▭ Losa — Clic para añadir vértices · ENTER para cerrar · ESC para cancelar"
        )
