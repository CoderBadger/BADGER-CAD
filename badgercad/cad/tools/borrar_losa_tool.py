"""borrar_losa_tool.py — Tool to delete slabs by clicking inside them."""
from __future__ import annotations
from .base_tool import BaseTool
from shapely.geometry import Point, Polygon


class BorrarLosaTool(BaseTool):
    """Delete a Losa if the user clicks inside its 2D boundary."""

    def activate(self) -> None:
        self._canvas.set_status("🗑 Borrar Losa — Haga clic dentro de la losa para eliminarla · ESC = salir")

    def on_left_click(self, world_x: float, world_y: float) -> None:
        grupo = self.project.grupo_activo
        if not grupo:
            return

        click_pt = Point(world_x, world_y)
        losas = self.project.get_losas_en_grupo(grupo.id)
        
        for losa in losas:
            poly = Polygon(losa.vertices)
            if click_pt.within(poly):
                self.project.remove_losa(losa.id)
                self._refresh()
                return  # only delete one at a time

    def on_key_press(self, key: str) -> None:
        if key.lower() == "escape":
            self._canvas.deactivate_tool()
