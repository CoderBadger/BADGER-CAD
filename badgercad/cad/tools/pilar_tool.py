"""pilar_tool.py — CYPECAD mass-production column placement tool.

Workflow (matches CYPECAD exactly):
  1. User presses "Colocar Pilar" in the ribbon.
  2. PilarPropsDialog opens IMMEDIATELY (before any click).
  3. User defines section, material, spans, vinculación → OK.
  4. Cursor becomes a ghost (semi-transparent pilar footprint).
  5. Every LEFT CLICK places one identical copy at the snapped position.
  6. RIGHT CLICK or ENTER → reopens PilarPropsDialog to change section
     mid-session (CYPECAD pattern) without going back to the Ribbon.
  7. ESC fully deactivates the tool and unchecks the Ribbon button.
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
            pilar_props:  Dict with keys: ancho, largo, angulo, material,
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
        self._update_status()

    def deactivate(self) -> None:
        remove_ghost_pilar(self.plotter)
        self._ghost_actor = None
        if self._count:
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
        self._refresh()
        self._update_status()

    def on_right_click(self, world_x: float, world_y: float) -> None:
        """Right-click reopens PilarPropsDialog to change section mid-session."""
        self._open_props_dialog()

    def on_key_press(self, key: str) -> None:
        key_l = key.lower()
        if key_l in ("return", "enter"):
            # ENTER also reopens props dialog (CYPECAD pattern)
            self._open_props_dialog()
        elif key_l == "escape":
            # ESC → full deactivation (canvas clears ghost + unchecks ribbon)
            self._canvas.deactivate_tool()

    # ------------------------------------------------------------------ internal
    def _open_props_dialog(self) -> None:
        """Open PilarPropsDialog pre-filled with current props.

        If accepted, updates internal props and refreshes the ghost to match
        the new section, without ending the placement session.
        After the dialog closes, inject fake mouse-release events so the VTK
        interactor does not perform an unintended zoom/pan on next mouse move.
        """
        from badgercad.ui.dialogs.pilar_props import PilarPropsDialog

        dlg = PilarPropsDialog(
            self._canvas.window(),
            project=self.project,
            initial_props=self._props,
        )
        if dlg.exec():
            self._props = dlg.get_props()
            remove_ghost_pilar(self.plotter)
            self._ghost_actor = add_ghost_pilar(
                self.plotter,
                self._props["ancho"],
                self._props["largo"],
            )
        # Always release stuck mouse state after ANY modal dialog
        self._canvas.release_mouse_state()
        self._update_status()

    def _update_status(self) -> None:
        w = self._props["ancho"] * 100
        l = self._props["largo"] * 100
        cnt = f" · {self._count} colocado(s)" if self._count else ""
        self._canvas.set_status(
            f"🏛 Pilar {w:.0f}×{l:.0f} cm{cnt} — "
            "Clic para colocar · Enter/RClick = cambiar sección · ESC = salir"
        )
