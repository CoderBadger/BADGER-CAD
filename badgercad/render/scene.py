"""scene.py — PyVista rendering helpers for 2D canvas and on-demand 3D viewer."""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List

import numpy as np
import pyvista as pv

if TYPE_CHECKING:
    from pyvistaqt import QtInteractor
    from ..core.project import Project
    from ..core.elements.nivel import Nivel

# ------------------------------------------------------------------ palette
BG_COLOR         = "#0D1117"
GRID_COLOR       = "#1E2D3D"
GRID_COLOR_MAJOR = "#243547"
PILAR_COLOR      = "#4A90D9"
PILAR_EDGE_COLOR = "#2260A8"
PILAR_VIN_COLOR  = "#4AD97A"   # green  = con vinculación (fixed to foundation)
PILAR_SIN_COLOR  = "#D97A4A"   # orange = sin vinculación (floating base)
LOSA_COLOR       = "#2A6496"
LOSA_EDGE_COLOR  = "#4A90D9"
AXIS_X_COLOR     = "#E05252"
AXIS_Y_COLOR     = "#52C752"
LABEL_COLOR      = "#FFFFFF"


# ================================================================== mesh builders
def _pilar_box_2d(pilar) -> pv.PolyData:
    """Flat box (z=0) representing a column footprint for 2D plan view.

    Built centred at origin, rotated by pilar.angulo, then translated.
    """
    a, l = pilar.ancho / 2, pilar.largo / 2
    box = pv.Box(bounds=(-a, a, -l, l, -0.02, 0.02))
    if pilar.angulo:
        box.rotate_z(pilar.angulo, inplace=True)
    box.translate([pilar.x, pilar.y, 0.0], inplace=True)
    return box


def _pilar_box_3d(pilar, z_bottom: float, z_top: float) -> pv.PolyData:
    """Full-height 3D box for a column in the perspective viewer.

    Built centred at origin, rotated by pilar.angulo, then translated.
    """
    a, l  = pilar.ancho / 2, pilar.largo / 2
    z_mid = (z_bottom + z_top) / 2
    half_h = (z_top - z_bottom) / 2
    box = pv.Box(bounds=(-a, a, -l, l, -half_h, half_h))
    if pilar.angulo:
        box.rotate_z(pilar.angulo, inplace=True)
    box.translate([pilar.x, pilar.y, z_mid], inplace=True)
    return box


def _losa_polygon(losa, z: float = 0.0) -> Optional[pv.PolyData]:
    """Flat filled polygon for a slab — used only in the 2D plan canvas."""
    if not losa.is_valid():
        return None
    verts = np.array([[v[0], v[1], z] for v in losa.vertices], dtype=float)
    n = len(verts)
    faces = np.array([n, *range(n)], dtype=int)
    mesh = pv.PolyData(verts, faces)
    return mesh


def _losa_solid_3d(losa, z_top: float) -> Optional[pv.PolyData]:
    """Extruded solid for a slab in the 3D perspective viewer.

    The polygon is placed at ``z_top`` (the floor elevation) and extruded
    downward by ``losa.espesor`` metres, producing a volumetric solid whose
    thickness matches the value the engineer entered in LosaPropsDialog.
    """
    if not losa.is_valid():
        return None

    espesor = max(losa.espesor, 0.01)   # safety floor: never zero-thickness
    z_bot   = z_top - espesor

    # Build top and bottom face vertices
    top_verts = np.array([[v[0], v[1], z_top] for v in losa.vertices], dtype=float)
    bot_verts = np.array([[v[0], v[1], z_bot] for v in losa.vertices], dtype=float)
    n = len(top_verts)

    all_verts = np.vstack([top_verts, bot_verts])  # top: 0..n-1, bot: n..2n-1

    faces: list[int] = []

    # Top face (facing up)
    faces += [n] + list(range(n))

    # Bottom face (facing down — reversed winding)
    faces += [n] + list(range(2 * n - 1, n - 1, -1))

    # Side quad faces
    for i in range(n):
        j = (i + 1) % n
        # quad: top_i, top_j, bot_j, bot_i
        faces += [4, i, j, j + n, i + n]

    mesh = pv.PolyData(all_verts, np.array(faces, dtype=int))
    return mesh


def _ghost_box(ancho: float, largo: float) -> pv.PolyData:
    """Pilar ghost mesh centred at origin — use SetPosition() to move it."""
    a, l = ancho / 2, largo / 2
    return pv.Box(bounds=(-a, a, -l, l, -0.02, 0.02))


# ================================================================== 2D canvas
def setup_canvas_2d(plotter: "QtInteractor") -> None:
    """Configure plotter for top-down orthographic 2D CAD view."""
    plotter.set_background(BG_COLOR)
    plotter.enable_parallel_projection()
    plotter.camera.position    = (0.0, 0.0, 50.0)
    plotter.camera.focal_point = (0.0, 0.0,  0.0)
    plotter.camera.up          = (0.0, 1.0,  0.0)
    plotter.camera.parallel_scale = 20.0
    plotter.enable_2d_style()          # locks rotation — pan + zoom only
    plotter.renderer.SetUseFXAA(True)  # anti-aliasing


def render_canvas_2d(plotter: "QtInteractor", project: "Project") -> None:
    """Clear and fully re-render the 2D plan for the currently active level."""
    # Remove all element actors (keep ghost if present)
    _clear_element_actors(plotter)

    nivel = project.nivel_activo
    if nivel is None:
        return

    grupo = project.get_grupo_de_nivel(nivel.id)

    # --- Pilares -------------------------------------------------------
    for pilar in project.get_pilares_en_nivel(nivel.id):
        mesh  = _pilar_box_2d(pilar)
        color = PILAR_VIN_COLOR if pilar.con_vinculacion_exterior else PILAR_SIN_COLOR
        plotter.add_mesh(
            mesh, color=color, show_edges=True,
            edge_color=PILAR_EDGE_COLOR, line_width=1.5,
            name=f"pilar_2d_{pilar.id}", pickable=True,
        )
        # Section label
        pt = np.array([[pilar.x, pilar.y, 0.05]])
        plotter.add_point_labels(
            pt, [pilar.seccion_label],
            font_size=8, text_color=LABEL_COLOR,
            always_visible=True, shadow=False,
            shape_opacity=0.0, fill_shape=False,
            name=f"label_pilar_{pilar.id}",
        )

    # --- Losas ----------------------------------------------------------
    if grupo is not None:
        for losa in project.get_losas_en_grupo(grupo.id):
            mesh = _losa_polygon(losa, z=0.0)
            if mesh is not None:
                plotter.add_mesh(
                    mesh, color=LOSA_COLOR, opacity=0.40,
                    show_edges=True, edge_color=LOSA_EDGE_COLOR, line_width=1.5,
                    name=f"losa_2d_{losa.id}",
                )


def _clear_element_actors(plotter: "QtInteractor") -> None:
    """Remove only element actors (pilar_*, losa_*, label_*) not the grid."""
    prefixes = ("pilar_2d_", "losa_2d_", "label_pilar_")
    keys_to_remove = [
        k for k in plotter.renderer.actors
        if any(k.startswith(p) for p in prefixes)
    ]
    for k in keys_to_remove:
        plotter.remove_actor(k)


# ================================================================== ghost actor
def add_ghost_pilar(plotter: "QtInteractor", ancho: float, largo: float):
    """Add a semi-transparent ghost pilar centred at origin.

    Returns the vtkActor so the tool can call SetPosition() on it.
    """
    mesh = _ghost_box(ancho, largo)
    actor = plotter.add_mesh(
        mesh, color=PILAR_COLOR, opacity=0.45,
        show_edges=True, edge_color="#AACCFF", line_width=1.5,
        name="ghost_pilar",
    )
    return actor


def remove_ghost_pilar(plotter: "QtInteractor") -> None:
    plotter.remove_actor("ghost_pilar")


def add_ghost_losa_line(plotter: "QtInteractor",
                        vertices: List[tuple],
                        preview_end: Optional[tuple] = None) -> None:
    """Draw a polyline preview for the losa being drawn."""
    plotter.remove_actor("ghost_losa_line")
    pts = list(vertices)
    if preview_end is not None:
        pts = pts + [preview_end]
    if len(pts) < 2:
        return
    arr = np.array([[v[0], v[1], 0.01] for v in pts], dtype=float)
    spline = pv.Spline(arr, n_points=len(arr))
    # Use lines directly
    n = len(arr)
    lines = []
    for i in range(n - 1):
        lines += [2, i, i + 1]
    poly = pv.PolyData()
    poly.points = arr
    poly.lines = np.array(lines, dtype=int)
    plotter.add_mesh(
        poly, color="#FFD700", line_width=2.0,
        name="ghost_losa_line",
    )


# ================================================================== 3D viewer
def render_3d_complete(plotter: "QtInteractor", project: "Project") -> None:
    """Build the full 3D perspective model (all groups and levels)."""
    plotter.clear()
    plotter.set_background("#0D1117", top="#1A2A3A")

    # --- Pilares 3D ------------------------------------------------
    for pilar in project.pilares:
        nd = project.get_nivel_by_id(pilar.nivel_desde_id)
        nh = project.get_nivel_by_id(pilar.nivel_hasta_id)
        if nd is None or nh is None:
            continue
        mesh  = _pilar_box_3d(pilar, nd.cota, nh.cota)
        color = PILAR_VIN_COLOR if pilar.con_vinculacion_exterior else PILAR_SIN_COLOR
        plotter.add_mesh(
            mesh, color=color, show_edges=True,
            edge_color=PILAR_EDGE_COLOR, line_width=1.0,
            name=f"p3d_{pilar.id}",
        )

    # --- Losas 3D --------------------------------------------------
    # Each grupo may span multiple niveles; render the slab at every nivel
    # it belongs to so repeated floors are visible.
    for grupo in project.grupos:
        niveles_del_grupo = [
            project.get_nivel_by_id(nid)
            for nid in grupo.nivel_ids
        ]
        niveles_del_grupo = [nv for nv in niveles_del_grupo if nv is not None]

        for nivel_rep in niveles_del_grupo:
            z_top = nivel_rep.cota
            for losa in project.get_losas_en_grupo(grupo.id):
                mesh = _losa_solid_3d(losa, z_top=z_top)
                if mesh is not None:
                    plotter.add_mesh(
                        mesh,
                        color=LOSA_COLOR, opacity=0.70,
                        show_edges=True, edge_color=LOSA_EDGE_COLOR, line_width=0.8,
                        name=f"l3d_{losa.id}_{nivel_rep.id}",
                    )

    # --- Level planes (ghost floors) --------------------------------
    for nivel in project.niveles_ordenados()[1:]:
        plane = pv.Plane(
            center=(0, 0, nivel.cota),
            direction=(0, 0, 1),
            i_size=60, j_size=60,
        )
        plotter.add_mesh(plane, color="#1A2A3A", opacity=0.12, name=f"floor_{nivel.id}")

    plotter.add_axes(color="white")
    plotter.reset_camera()
