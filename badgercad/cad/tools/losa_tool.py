"""losa_tool.py — Polygonal slab drawing tool.

Workflow:
  1. User activates tool from ribbon.
  2. Each LEFT CLICK adds a vertex; a dynamic preview line follows the cursor.
  3. RIGHT CLICK or ENTER with ≥3 vertices closes the polygon and opens
     LosaPropsDialog. With <3 vertices, shows a warning in the status bar.
  4. On dialog accept, the Losa is added to the active Grupo.
  5. ESC cancels any in-progress polygon, clears ghosts and FULLY deactivates
     the tool (returns to neutral state, unchecks ribbon button).
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
            "▭ Losa — Clic para añadir vértices · "
            "RClick/Enter = cerrar · ESC = salir"
        )

    def deactivate(self) -> None:
        """Clean up: always remove the ghost and reset vertex list."""
        self._vertices.clear()
        try:
            self.plotter.remove_actor("ghost_losa_line")
        except Exception:
            pass  # safe – actor may not exist yet

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
        n = len(self._vertices)
        self._canvas.set_status(
            f"▭ Losa — {n} vértice(s) · "
            "RClick/Enter = cerrar · ESC = salir"
        )

    def on_right_click(self, world_x: float, world_y: float) -> None:
        """Right-click closes the polygon (same as ENTER)."""
        self._try_close_polygon()

    def on_key_press(self, key: str) -> None:
        key_l = key.lower()
        if key_l in ("return", "enter"):
            self._try_close_polygon()
        elif key_l == "escape":
            # ESC: abort polygon in progress and FULLY deactivate
            # deactivate() handles cleanup; canvas clears the tool reference
            # and emits tool_deactivated so the ribbon unchecks the button.
            self._canvas.deactivate_tool()

    # ------------------------------------------------------------------ internal
    def _try_close_polygon(self) -> None:
        """Attempt to close the current polygon.

        Requires ≥3 vertices. Shows warning in status bar if not met.
        After dialog accept the tool resets for a new polygon WITHOUT
        deactivating — the user can draw the next slab immediately.
        After dialog cancel or insufficient vertices, the tool stays active.
        """
        if len(self._vertices) < 3:
            self._canvas.set_status(
                "⚠ Se necesitan al menos 3 vértices para cerrar la losa."
            )
            return

        # Snapshot vertices before any dialog interaction
        verts_snapshot = list(self._vertices)

        # Open properties dialog
        from badgercad.ui.dialogs.losa_props import LosaPropsDialog
        dlg = LosaPropsDialog(
            self._canvas.window(),
            grupo_activo=self.project.grupo_activo,
        )
        if dlg.exec():
            props = dlg.get_props()
            losa = Losa(
                vertices=verts_snapshot,
                tipo=props["tipo"],
                espesor=props["espesor"],
                grupo_id=props["grupo_id"],
            )
            self.project.add_losa(losa)
            self._refresh()

        # Reset for next polygon WITHOUT deactivating the tool
        self._vertices.clear()
        try:
            self.plotter.remove_actor("ghost_losa_line")
        except Exception:
            pass
        self._canvas.set_status(
            "▭ Losa — Clic para añadir vértices · "
            "RClick/Enter = cerrar · ESC = salir"
        )
