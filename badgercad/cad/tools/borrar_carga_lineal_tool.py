"""borrar_carga_lineal_tool.py — Tool to delete linear loads by clicking near them."""
from __future__ import annotations
from .base_tool import BaseTool
from shapely.geometry import Point, LineString


class BorrarCargaLinealTool(BaseTool):
    """Delete a Carga Lineal if the user clicks within a 20cm buffer of its line."""

    def activate(self) -> None:
        self._canvas.set_status("🗑 Borrar Carga — Haga clic sobre una carga lineal para eliminarla · ESC = salir")

    def on_left_click(self, world_x: float, world_y: float) -> None:
        grupo = self.project.grupo_activo
        if not grupo:
            return

        click_pt = Point(world_x, world_y)
        cargas = self.project.get_cargas_lineales_en_grupo(grupo.id)
        
        for carga in cargas:
            line = LineString([carga.p1, carga.p2])
            buffer = line.buffer(0.2)  # 20cm click tolerance
            if click_pt.within(buffer):
                self.project.remove_carga_lineal(carga.id)
                self._refresh()
                return

    def on_key_press(self, key: str) -> None:
        if key.lower() == "escape":
            self._canvas.deactivate_tool()
