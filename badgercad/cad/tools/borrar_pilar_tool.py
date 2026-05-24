"""borrar_pilar_tool.py — Tool for deleting existing columns by clicking them.

Workflow (CYPECAD-style category-specific deletion):
  1. User presses "Borrar Pilar" in the ribbon → tool activates.
  2. Cursor changes meaning: clicks are now DELETE hits, not placements.
  3. LEFT CLICK near a pilar → removes it from the model (undoable via Ctrl+Z).
  4. ESC → fully deactivates and returns to idle state.
"""
from __future__ import annotations

from .base_tool import BaseTool


# Click tolerance in metres.  A click within this radius of a pilar
# boundary (or inside it) will select that pilar for deletion.
_HIT_TOLERANCE = 0.20


class BorrarPilarTool(BaseTool):
    """Delete columns by clicking their footprint on the 2D plan canvas."""

    # ------------------------------------------------------------------ lifecycle
    def activate(self) -> None:
        self._canvas.set_status(
            "🗑  Borrar Pilar — Clic sobre el pilar a eliminar · ESC para salir"
        )

    def deactivate(self) -> None:
        pass  # no ghost actors to clean up

    # ------------------------------------------------------------------ events
    def on_left_click(self, world_x: float, world_y: float) -> None:
        """Find the pilar under the cursor and delete it."""
        pilar = self._find_pilar_at(world_x, world_y)
        if pilar is not None:
            self.project.remove_pilar(pilar.id)   # recorded in undo stack
            self._refresh()
            self._canvas.set_status(
                f"✔  Pilar eliminado ({pilar.seccion_label})  ·  "
                "Clic para borrar otro · Ctrl+Z para deshacer · ESC para salir"
            )
        else:
            self._canvas.set_status(
                "⚠  No hay pilar en esa posición · "
                "Clic para borrar otro · ESC para salir"
            )

    def on_key_press(self, key: str) -> None:
        if key.lower() == "escape":
            self._canvas.deactivate_tool()

    # ------------------------------------------------------------------ geometry
    def _find_pilar_at(self, wx: float, wy: float):
        """Return the first Pilar whose footprint contains (wx, wy).

        Uses Shapely for accurate hit-testing, including rotated pillars.
        Falls back to a simple distance check if Shapely is unavailable.
        """
        try:
            return self._find_pilar_shapely(wx, wy)
        except ImportError:
            return self._find_pilar_distance(wx, wy)

    def _find_pilar_shapely(self, wx: float, wy: float):
        """Shapely-based hit test (supports rotation)."""
        from shapely.geometry import Point
        from shapely.geometry import box as shapely_box
        from shapely.affinity import rotate as shapely_rotate, translate

        click_pt = Point(wx, wy)

        for pilar in self.project.pilares:
            a, l = pilar.ancho / 2, pilar.largo / 2
            footprint = shapely_box(-a, -l, a, l)
            if pilar.angulo:
                footprint = shapely_rotate(footprint, -pilar.angulo, origin=(0, 0))
            footprint = translate(footprint, pilar.x, pilar.y)
            # Distance ≤ 0 means the point is inside; ≤ tolerance catches
            # near-misses when the user clicks just outside the edge.
            if footprint.distance(click_pt) <= _HIT_TOLERANCE:
                return pilar
        return None

    def _find_pilar_distance_fallback(self, wx: float, wy: float):
        """Simple Euclidean distance fallback (ignores rotation)."""
        for pilar in self.project.pilares:
            r = max(pilar.ancho, pilar.largo) / 2 + _HIT_TOLERANCE
            dist = ((wx - pilar.x) ** 2 + (wy - pilar.y) ** 2) ** 0.5
            if dist <= r:
                return pilar
        return None
