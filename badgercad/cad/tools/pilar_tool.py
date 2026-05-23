"""pilar_tool.py — CYPECAD mass-production column placement tool.

Workflow (matches CYPECAD exactly):
  1. User presses "Colocar Pilar" in the ribbon.
  2. PilarPropsDialog opens IMMEDIATELY (before any click).
  3. User defines section, material, spans, vinculación → OK.
  4. Cursor becomes a ghost (semi-transparent pilar footprint).
  5. Every LEFT CLICK places one identical copy at the snapped position.
  6. ESC or activating another tool ends the session.
"""
from __future__ import annotations
from typing import Optional

from .base_tool import BaseTool
from badgercad.core.elements.pilar import Pilar
from badgercad.render.scene import add_ghost_pilar, remove_ghost_pilar


class PilarTool(BaseTool):
    """Place identical columns with repeated left-clicks until ESC."""

    def __init__(self, canvas, pilar_props: dict) -> None:
        """
        Args:
            canvas:       The Canvas2D instance.
            pilar_props:  Dict with keys: ancho, largo, material,
                          nivel_desde_id, nivel_hasta_id,
                          con_vinculacion_exterior.
        """
        super().__init__(canvas)
        self._props = pilar_props
        self._ghost_actor = None
        self._count = 0          # columns placed this session

    # ------------------------------------------------------------------ lifecycle
    def activate(self) -> None:
        self._ghost_actor = add_ghost_pilar(
            self.plotter,
            self._props["ancho"],
            self._props["largo"],
        )
        self._canvas.set_status(
            f"🏛 Pilar {self._props['ancho']*100:.0f}×"
            f"{self._props['largo']*100:.0f} cm — "
            "Clic para colocar · ESC para terminar"
        )

    def deactivate(self) -> None:
        remove_ghost_pilar(self.plotter)
        self._ghost_actor = None
        self._canvas.set_status(
            f"✔ {self._count} pilar(es) colocado(s)"
        )

    # ------------------------------------------------------------------ events
    def on_mouse_move(self, world_x: float, world_y: float) -> None:
        """Move the ghost to the snapped cursor position."""
        if self._ghost_actor is None:
            return
        sx, sy = self._snap(world_x, world_y)
        self._ghost_actor.SetPosition(sx, sy, 0.0)
        self.plotter.render()

    def on_left_click(self, world_x: float, world_y: float) -> None:
        """Place a Pilar at the snapped position."""
        sx, sy = self._snap(world_x, world_y)

        pilar = Pilar(
            x=sx,
            y=sy,
            ancho=self._props["ancho"],
            largo=self._props["largo"],
            angulo=self._props.get("angulo", 0.0),
            material=self._props.get("material", "H25"),
            nivel_desde_id=self._props.get("nivel_desde_id", ""),
            nivel_hasta_id=self._props.get("nivel_hasta_id", ""),
            con_vinculacion_exterior=self._props.get(
                "con_vinculacion_exterior", True
            ),
        )
        self.project.add_pilar(pilar)
        self._count += 1

        # Refresh the scene (re-draws all element actors)
        self._refresh()

        # Update status with running count
        self._canvas.set_status(
            f"🏛 Pilar {self._props['ancho']*100:.0f}×"
            f"{self._props['largo']*100:.0f} cm — "
            f"{self._count} colocado(s) · ESC para terminar"
        )

    def on_key_press(self, key: str) -> None:
        if key.lower() == "escape":
            self._canvas.deactivate_tool()

    # ------------------------------------------------------------------ props update
    def update_props(self, new_props: dict) -> None:
        """Allow the user to change dimensions mid-session without restarting."""
        self._props = new_props
        remove_ghost_pilar(self.plotter)
        self._ghost_actor = add_ghost_pilar(
            self.plotter,
            self._props["ancho"],
            self._props["largo"],
        )
