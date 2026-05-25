"""viga_tool.py — Tool for continuous drawing of beams (Vigas).

Workflow:
  1. User activates tool from ribbon.
  2. VigaPropsDialog MUST appear to set properties.
  3. LEFT CLICK sets start node (snaps to pilares if nearby).
  4. Next LEFT CLICK sets end node. The segment is automatically split
     if it intersects intermediate pillars (topological noding).
  5. RIGHT CLICK re-opens VigaPropsDialog.
  6. ESC (once) breaks the chain. ESC (twice) deactivates the tool.
"""
from __future__ import annotations
from typing import Optional, Tuple
import math

from .base_tool import BaseTool
from badgercad.core.elements.viga import Viga
import pyvista as pv


class VigaTool(BaseTool):
    """Draw continuous beams snapping to grid and pilares, with topological splitting."""

    def __init__(self, canvas) -> None:
        super().__init__(canvas)
        self._start_node: Optional[Tuple[float, float]] = None
        self._cursor_pos: Tuple[float, float] = (0.0, 0.0)
        self._current_props = {
            "ancho": 0.25,
            "canto": 0.50,
            "material": "H25",
            "tipo": "RECTANGULAR",
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
            self.plotter.remove_actor("ghost_viga_line")
        except Exception:
            pass

    def _open_props_dialog(self) -> bool:
        from badgercad.ui.dialogs.viga_props import VigaPropsDialog
        dlg = VigaPropsDialog(self._canvas.window(), self._current_props)
        if dlg.exec():
            self._current_props = dlg.get_props()
            self._canvas.release_mouse_state()
            return True
        self._canvas.release_mouse_state()
        return False

    # ------------------------------------------------------------------ events
    def on_mouse_move(self, world_x: float, world_y: float) -> None:
        sx, sy = self._snap(world_x, world_y)
        # Check for pillar snapping (override grid snap if close to a pilar)
        px, py = self._snap_to_pilar(world_x, world_y, sx, sy)
        self._cursor_pos = (px, py)

        if self._start_node is not None:
            self._draw_ghost(self._start_node, self._cursor_pos)
            self.plotter.render()

    def on_left_click(self, world_x: float, world_y: float) -> None:
        if self.project.grupo_activo is None:
            self._canvas.set_status("⚠ Active un Nivel/Grupo primero.")
            return

        sx, sy = self._snap(world_x, world_y)
        px, py = self._snap_to_pilar(world_x, world_y, sx, sy)

        if self._start_node is None:
            # Start new chain
            self._start_node = (px, py)
            self._update_status()
        else:
            # Finish segment
            if self._start_node != (px, py):
                self._commit_viga_segment(self._start_node, (px, py))
                self._refresh()
                # Continuous drawing: new start is current end
                self._start_node = (px, py)
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
    def _commit_viga_segment(self, p_a: Tuple[float, float], p_b: Tuple[float, float]) -> None:
        """Add segment A-B, subdividing at any pillar centroids it crosses."""
        import numpy as np
        
        # Vector A->B
        ax, ay = p_a
        bx, by = p_b
        vec_ab = np.array([bx - ax, by - ay])
        len_ab = np.linalg.norm(vec_ab)
        if len_ab < 1e-4:
            return
            
        dir_ab = vec_ab / len_ab
        
        grupo_id = self.project.grupo_activo.id
        
        # Find intersecting pillars
        intersections = []
        for p in self.project.pilares:
            # Check distance to line segment
            vec_ap = np.array([p.x - ax, p.y - ay])
            proj = np.dot(vec_ap, dir_ab)
            
            # If point projects strictly within the segment (excluding exactly A or B)
            if 1e-3 < proj < len_ab - 1e-3:
                # Perpendicular distance
                dist = np.linalg.norm(vec_ap - proj * dir_ab)
                if dist < 1e-3: # Passes through centroid analitically
                    intersections.append((proj, p.x, p.y))
                    
        # Sort by distance from A
        intersections.sort(key=lambda x: x[0])
        
        # Create subsegments
        current_start = p_a
        points = [current_start] + [(px, py) for _, px, py in intersections] + [p_b]
        
        for i in range(len(points) - 1):
            n1 = points[i]
            n2 = points[i+1]
            viga = Viga(
                nodo_inicial=n1,
                nodo_final=n2,
                ancho=self._current_props["ancho"],
                canto=self._current_props["canto"],
                material=self._current_props["material"],
                tipo=self._current_props["tipo"],
                grupo_id=grupo_id,
            )
            self.project.add_viga(viga)

    def _break_chain(self) -> None:
        self._start_node = None
        try:
            self.plotter.remove_actor("ghost_viga_line")
            self.plotter.render()
        except Exception:
            pass
        self._update_status()

    def _update_status(self) -> None:
        if self._start_node is None:
            self._canvas.set_status("📏 Viga — Clic inicial · RClick = Propiedades · ESC = salir")
        else:
            self._canvas.set_status("📏 Viga — Clic final · RClick = Propiedades · ESC = soltar")

    def _snap_to_pilar(self, wx: float, wy: float, sx: float, sy: float) -> Tuple[float, float]:
        """Snap to the closest pilar centroid if within 1.0 m."""
        if self.project.grupo_activo is None:
            return sx, sy
        
        closest_pilar = None
        min_dist = 1.0  # snapping radius
        
        # Pillars are global, snap to any pillar
        for p in self.project.pilares:
            dist = math.hypot(p.x - wx, p.y - wy)
            if dist < min_dist:
                min_dist = dist
                closest_pilar = p
                
        if closest_pilar:
            return closest_pilar.x, closest_pilar.y
        return sx, sy

    def _draw_ghost(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> None:
        self.plotter.remove_actor("ghost_viga_line")
        if p1 == p2:
            return
        
        # Draw the real width footprint if possible
        try:
            from shapely.geometry import LineString
            line = LineString([p1, p2])
            poly = line.buffer(self._current_props["ancho"] / 2, cap_style=2)
            verts = list(poly.exterior.coords)
            import numpy as np
            n = len(verts) - 1
            arr = np.array([[v[0], v[1], 0.02] for v in verts[:n]], dtype=float)
            faces = np.array([n] + list(range(n)), dtype=int)
            mesh = pv.PolyData(arr, faces)
            self.plotter.add_mesh(
                mesh, color="#FFD700", opacity=0.4, show_edges=True,
                name="ghost_viga_line", render_lines_as_tubes=False,
            )
        except Exception:
            # Fallback line
            import numpy as np
            arr = np.array([[p1[0], p1[1], 0.02], [p2[0], p2[1], 0.02]], dtype=float)
            poly = pv.PolyData()
            poly.points = arr
            poly.lines = np.array([2, 0, 1], dtype=int)
            self.plotter.add_mesh(
                poly, color="#FFD700", line_width=2.5,
                name="ghost_viga_line",
                render_lines_as_tubes=False,
            )
