"""borrar_viga_tool.py — Tool to delete beams by clicking near them."""
from __future__ import annotations
from .base_tool import BaseTool
from shapely.geometry import Point, LineString


class BorrarVigaTool(BaseTool):
    """Delete a Viga if the user clicks within a 20cm buffer of its analytical line."""

    def activate(self) -> None:
        self._canvas.set_status("🗑 Borrar Viga — Haga clic sobre una viga para eliminarla · ESC = salir")

    def on_left_click(self, world_x: float, world_y: float) -> None:
        grupo = self.project.grupo_activo
        if not grupo:
            return

        click_pt = Point(world_x, world_y)
        vigas = self.project.get_vigas_en_grupo(grupo.id)
        
        for viga in vigas:
            line = LineString([viga.nodo_inicial, viga.nodo_final])
            buffer = line.buffer(0.2)  # 20cm click tolerance
            if click_pt.within(buffer):
                self.project.remove_viga(viga.id)
                self._refresh()
                return

    def on_key_press(self, key: str) -> None:
        if key.lower() == "escape":
            self._canvas.deactivate_tool()
