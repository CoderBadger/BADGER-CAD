"""losa_tool.py — Slab insertion tool (Hito 2 version).

Workflow:
  1. User activates tool from ribbon.
  2. LEFT CLICK inside a closed bay (paño).
  3. Tool detects the bay using topology.panio_at_point.
  4. Opens LosaPropsDialog.
  5. On accept, Losa is created matching the exact bay geometry.
  6. ESC fully deactivates the tool.
"""
from __future__ import annotations
from typing import Optional, Tuple

from .base_tool import BaseTool
from badgercad.core.elements.losa import Losa
from badgercad.core.topology import detect_panios, panio_at_point, polygon_to_vertices


class LosaTool(BaseTool):
    """Inject a slab into a closed beam bay."""

    def __init__(self, canvas) -> None:
        super().__init__(canvas)
        self._current_props = {
            "tipo": "Maciza",
            "espesor": 0.20,
            "grupo_id": ""
        }

    # ------------------------------------------------------------------ lifecycle
    def activate(self) -> None:
        if self.project.grupo_activo:
            self._current_props["grupo_id"] = self.project.grupo_activo.id
        
        if not self._open_props_dialog():
            self._canvas.deactivate_tool()
            return
            
        self._canvas.set_status(
            "▭ Losa — Clic dentro de recintos para inyectar · RClick = Propiedades · ESC = salir"
        )

    def _open_props_dialog(self) -> bool:
        from badgercad.ui.dialogs.losa_props import LosaPropsDialog
        dlg = LosaPropsDialog(
            self._canvas.window(),
            grupo_activo=self.project.grupo_activo,
        )
        if dlg.exec():
            self._current_props = dlg.get_props()
            self._canvas.release_mouse_state()
            return True
        self._canvas.release_mouse_state()
        return False

    def deactivate(self) -> None:
        pass

    # ------------------------------------------------------------------ events
    def on_mouse_move(self, world_x: float, world_y: float) -> None:
        # No dynamic preview needed for Hito 2 Losa click-in-bay
        pass

    def on_left_click(self, world_x: float, world_y: float) -> None:
        if self.project.grupo_activo is None:
            self._canvas.set_status("⚠ Active un Nivel/Grupo primero.")
            return

        vigas = self.project.get_vigas_en_grupo(self.project.grupo_activo.id)
        panios = detect_panios(vigas)
        
        # Check if click is inside any panio
        panio = panio_at_point(panios, world_x, world_y)
        if panio is None:
            self._canvas.set_status("⚠ Haga clic DENTRO de un paño cerrado por vigas.")
            return

        # Found a panio, extract vertices
        verts = polygon_to_vertices(panio)

        # Inject immediately
        losa = Losa(
            vertices=verts,
            tipo=self._current_props["tipo"],
            espesor=self._current_props["espesor"],
            grupo_id=self._current_props["grupo_id"],
        )
        self.project.add_losa(losa)
        self._refresh()

        self._canvas.set_status(
            "▭ Losa inyectada — Clic en otro recinto · RClick = Propiedades · ESC = salir"
        )

    def on_right_click(self, world_x: float, world_y: float) -> None:
        self._open_props_dialog()

    def on_key_press(self, key: str) -> None:
        key_l = key.lower()
        if key_l == "escape":
            self._canvas.deactivate_tool()
