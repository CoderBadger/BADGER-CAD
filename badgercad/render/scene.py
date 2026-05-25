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
VIGA_COLOR       = "#A2845E"
VIGA_EDGE_COLOR  = "#C2A781"
ZUNCHO_COLOR     = "#4A5A6A"
ZUNCHO_EDGE      = "#6A7A8A"
PANIO_COLOR      = "#1F3324"
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


def _viga_box_2d(viga, pilares_union=None) -> pv.PolyData:
    """Flat polygon for a beam, cut around pillars using boolean difference."""
    import numpy as np
    try:
        from shapely.geometry import LineString, Polygon
        line = LineString([viga.nodo_inicial, viga.nodo_final])
        poly = line.buffer(viga.ancho / 2, cap_style=2)
        if pilares_union is not None and not pilares_union.is_empty:
            poly = poly.difference(pilares_union)
            
        def extract_polys(p):
            if isinstance(p, Polygon):
                return [p]
            elif hasattr(p, "geoms"):
                return list(p.geoms)
            return []
            
        polys = extract_polys(poly)
        
        all_verts = []
        faces = []
        offset = 0
        for p in polys:
            if p.is_empty: continue
            v = list(p.exterior.coords)
            n = len(v) - 1
            arr = np.array([[c[0], c[1], 0.0] for c in v[:n]], dtype=float)
            all_verts.append(arr)
            faces.extend([n] + list(range(offset, offset + n)))
            offset += n
            
        if not all_verts:
            return pv.PolyData()
            
        return pv.PolyData(np.vstack(all_verts), np.array(faces, dtype=int))
    except ImportError:
        # Fallback to rotated box if Shapely is missing
        import math
        x1, y1 = viga.nodo_inicial
        x2, y2 = viga.nodo_final
        dx = x2 - x1
        dy = y2 - y1
        l = math.hypot(dx, dy)
        cx = x1 + dx / 2
        cy = y1 + dy / 2
        ang = math.degrees(math.atan2(dy, dx))
        a = viga.ancho / 2
        box = pv.Box(bounds=(-l/2, l/2, -a, a, -0.01, 0.01))
        box.rotate_z(ang, inplace=True)
        box.translate([cx, cy, 0.0], inplace=True)
        return box


def _viga_box_3d(viga, z_top: float, pilares_union=None) -> pv.PolyData:
    """Full depth 3D solid for a beam, cut around pillars."""
    if getattr(viga, "tipo", "") == "ZUNCHO_BORDE":
        return pv.PolyData()
        
    flat_mesh = _viga_box_2d(viga, pilares_union)
    if flat_mesh.n_points == 0:
        return pv.PolyData()
        
    # Move to z_top
    flat_mesh.points[:, 2] = z_top
    
    # Extrude downwards by canto
    solid = flat_mesh.extrude((0, 0, -viga.canto), capping=True)
    return solid


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
            render_lines_as_tubes=False,
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

    # --- Vigas & Paños --------------------------------------------------
    vigas = project.get_vigas_en_grupo(grupo.id) if grupo else []
    
    # Pre-calculate pillars union for boolean differences
    try:
        from shapely.ops import unary_union
        from shapely.geometry import Polygon
        pilares_polys = [Polygon(p.footprint_2d()) for p in project.pilares]
        pilares_union = unary_union(pilares_polys) if pilares_polys else None
    except ImportError:
        pilares_union = None

    from badgercad.core.topology import detect_panios
    panios = detect_panios(vigas)
    
    # Render paños (bays)
    for i, panio in enumerate(panios):
        import hashlib
        # Use a hash of the coordinates to create a stable ID for the panio
        coords_str = str(list(panio.exterior.coords))
        panio_hash = hashlib.md5(coords_str.encode()).hexdigest()[:8]
        verts = np.array([[x, y, -0.015] for x, y in panio.exterior.coords], dtype=float)
        n = len(verts) - 1 # shapely closes the ring
        faces = np.array([n] + list(range(n)), dtype=int)
        mesh = pv.PolyData(verts[:n], faces)
        plotter.add_mesh(
            mesh, color=PANIO_COLOR, opacity=0.3, show_edges=False,
            name=f"panio_2d_{panio_hash}"
        )

    # Render vigas
    for viga in vigas:
        mesh = _viga_box_2d(viga, pilares_union)
        is_zuncho = getattr(viga, "tipo", "") == "ZUNCHO_BORDE"
        color = ZUNCHO_COLOR if is_zuncho else VIGA_COLOR
        edge_color = ZUNCHO_EDGE if is_zuncho else VIGA_EDGE_COLOR
        opacity = 0.5 if is_zuncho else 1.0
        
        plotter.add_mesh(
            mesh, color=color, opacity=opacity, show_edges=True,
            edge_color=edge_color, line_width=1.5,
            name=f"viga_2d_{viga.id}", pickable=True,
            render_lines_as_tubes=False,
        )
        # Section label
        pt = np.array([[(viga.nodo_inicial[0]+viga.nodo_final[0])/2, (viga.nodo_inicial[1]+viga.nodo_final[1])/2, 0.05]])
        plotter.add_point_labels(
            pt, [viga.seccion_label],
            font_size=8, text_color=LABEL_COLOR,
            always_visible=True, shadow=False,
            shape_opacity=0.0, fill_shape=False,
            name=f"label_viga_{viga.id}",
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
                    render_lines_as_tubes=False,
                )


def _clear_element_actors(plotter: "QtInteractor") -> None:
    """Remove only element actors (pilar_*, viga_*, panio_*, losa_*, label_*) not the grid."""
    prefixes = ("pilar_2d_", "viga_2d_", "panio_2d_", "losa_2d_", "label_pilar_", "label_viga_")
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


def _structural_bounds(project: "Project") -> tuple[float, float, float, float]:
    """Compute (cx, cy, half_x, half_y) of the structural elements.

    Used to size ghost floor planes so they do not bloat the camera
    bounding box beyond the actual structure footprint.
    Falls back to a 10 m half-extent if the project has no elements.
    """
    xs: list[float] = []
    ys: list[float] = []

    for p in project.pilares:
        xs.append(p.x)
        ys.append(p.y)
        
    for v in project.vigas:
        xs.append(v.nodo_inicial[0])
        xs.append(v.nodo_final[0])
        ys.append(v.nodo_inicial[1])
        ys.append(v.nodo_final[1])

    for lo in project.losas:
        for vx, vy in lo.vertices:
            xs.append(vx)
            ys.append(vy)

    if not xs:
        return 0.0, 0.0, 10.0, 10.0

    margin = 3.0
    cx  = (min(xs) + max(xs)) / 2
    cy  = (min(ys) + max(ys)) / 2
    hx  = (max(xs) - min(xs)) / 2 + margin
    hy  = (max(ys) - min(ys)) / 2 + margin
    return cx, cy, hx, hy


# ================================================================== 3D viewer
def render_3d_complete(plotter: "QtInteractor", project: "Project") -> None:
    """Build the full 3D perspective model (all groups and levels).

    Camera framing strategy
    -----------------------
    ``reset_camera()`` is called **after** structural actors (pilares + losas)
    but **before** ghost floor planes and axes.  This ensures the camera fits
    the actual structure, not the decorative 60×60 m planes that would
    otherwise push the framing 3–4× too far out.

    Floor planes are additionally sized to the structural footprint + 3 m
    margin (instead of a fixed 60 m), so even if PyVista ever resets the
    camera automatically, the planes will not balloon the bounding box.
    """
    plotter.clear()
    plotter.set_background("#0D1117", top="#1A2A3A")

    # ── 1. Structural elements ────────────────────────────────────────────
    # --- Pilares 3D --------------------------------------------------
    for pilar in project.pilares:
        nd = project.get_nivel_by_id(pilar.nivel_desde_id)
        nh = project.get_nivel_by_id(pilar.nivel_hasta_id)
        if nd is None or nh is None:
            continue
        mesh  = _pilar_box_3d(pilar, nd.cota, nh.cota)
        color = PILAR_VIN_COLOR if pilar.con_vinculacion_exterior else PILAR_SIN_COLOR
        plotter.add_mesh(mesh, color=color, show_edges=True,
                         edge_color=PILAR_EDGE_COLOR, line_width=1.0,
                         name=f"p3d_{pilar.id}", render_lines_as_tubes=False)

    # --- Vigas 3D --------------------------------------------------
    try:
        from shapely.ops import unary_union
        from shapely.geometry import Polygon
        pilares_polys = [Polygon(p.footprint_2d()) for p in project.pilares]
        pilares_union = unary_union(pilares_polys) if pilares_polys else None
    except ImportError:
        pilares_union = None
        
    for grupo in project.grupos:
        niveles_del_grupo = [project.get_nivel_by_id(nid) for nid in grupo.nivel_ids]
        vigas_del_grupo = project.get_vigas_en_grupo(grupo.id)
        for nivel_rep in (nv for nv in niveles_del_grupo if nv is not None):
            z_top = nivel_rep.cota
            for viga in vigas_del_grupo:
                mesh = _viga_box_3d(viga, z_top, pilares_union)
                if mesh.n_points > 0:
                    plotter.add_mesh(mesh, color=VIGA_COLOR, show_edges=True,
                                     edge_color=VIGA_EDGE_COLOR, line_width=1.0,
                                     name=f"v3d_{viga.id}_{nivel_rep.id}", render_lines_as_tubes=False)

    # --- Losas 3D --------------------------------------------------
    for grupo in project.grupos:
        niveles_del_grupo = [project.get_nivel_by_id(nid) for nid in grupo.nivel_ids]
        for nivel_rep in (nv for nv in niveles_del_grupo if nv is not None):
            z_top = nivel_rep.cota
            for losa in project.get_losas_en_grupo(grupo.id):
                mesh = _losa_solid_3d(losa, z_top=z_top)
                if mesh is not None:
                    plotter.add_mesh(
                        mesh, color=LOSA_COLOR, opacity=0.70,
                        show_edges=True, edge_color=LOSA_EDGE_COLOR, line_width=0.8,
                        name=f"l3d_{losa.id}_{nivel_rep.id}",
                        render_lines_as_tubes=False,
                    )

    # ── 2. Fit camera to structural extent (BEFORE decorative elements) ───
    plotter.reset_camera()

    # ── 3. Decorative elements (do not affect camera framing) ─────────────
    cx, cy, hx, hy = _structural_bounds(project)
    ix = max(hx * 2, 4.0)   # floor plane width  (at least 4 m)
    iy = max(hy * 2, 4.0)   # floor plane height (at least 4 m)

    for nivel in project.niveles_ordenados()[1:]:
        plane = pv.Plane(
            center=(cx, cy, nivel.cota),
            direction=(0, 0, 1),
            i_size=ix, j_size=iy,
        )
        plotter.add_mesh(plane, color="#1A2A3A", opacity=0.12,
                         name=f"floor_{nivel.id}")

    plotter.add_axes(color="white")

# ================================================================== MEF Results
def render_mef_results(plotter, project, mef_results, active_field="Desplazamientos") -> None:
    """Renders the warped MEF results in the 3D viewer.
    
    Args:
        plotter: PyVista plotter instance.
        project: Project containing the geometric data.
        mef_results: Dict from solver.py with 'mesh', 'displacements', 'forces_mxx', 'forces_myy'.
        active_field: "Desplazamientos", "Esfuerzos Mxx", or "Esfuerzos Myy".
    """
    plotter.clear()
    setup_viewer_3d(plotter)
    
    # Render background structural context (Pilares and Vigas) semi-transparently
    try:
        from shapely.ops import unary_union
        from shapely.geometry import Polygon
        pilares_polys = [Polygon(p.footprint_2d()) for p in project.pilares]
        pilares_union = unary_union(pilares_polys) if pilares_polys else None
    except ImportError:
        pilares_union = None

    for pilar in project.pilares:
        mesh = _pilar_box_3d(pilar, 0.0, 10.0) # simplify height for context
        plotter.add_mesh(mesh, color="#AAAAAA", opacity=0.3, show_edges=True,
                         edge_color="#888888", name=f"bg_p_{pilar.id}")
                         
    for grupo in project.grupos:
        vigas_del_grupo = project.get_vigas_en_grupo(grupo.id)
        if not vigas_del_grupo: continue
        z_top = 0.0
        if grupo.nivel_ids:
            nv = project.get_nivel_by_id(grupo.nivel_ids[-1])
            z_top = nv.cota if nv else 0.0
            
        for viga in vigas_del_grupo:
            mesh = _viga_box_3d(viga, z_top, pilares_union)
            if mesh.n_points > 0:
                plotter.add_mesh(mesh, color="#555555", opacity=0.6, show_edges=True,
                                 edge_color="#333333", name=f"bg_v_{viga.id}_{grupo.id}")
    
    if not mef_results:
        return
        
    mesh_data = mef_results["mesh"]
    disps = mef_results["displacements"]
    mxx = mef_results["forces_mxx"]
    myy = mef_results["forces_myy"]
    
    import numpy as np
    import pyvista as pv
    
    nodes = mesh_data["nodes"]
    elements = mesh_data["elements"]
    
    tag_to_idx = {}
    verts = []
    for i, (tag, coords) in enumerate(nodes.items()):
        tag_to_idx[tag] = i
        verts.append(coords)
        
    faces = []
    for tag, n_tags in elements.items():
        if len(n_tags) == 4:
            faces.extend([4, tag_to_idx[n_tags[0]], tag_to_idx[n_tags[1]], 
                          tag_to_idx[n_tags[2]], tag_to_idx[n_tags[3]]])
                          
    mesh = pv.PolyData(np.array(verts, dtype=float), np.array(faces, dtype=int))
    
    dz_array = np.zeros(mesh.n_points)
    for tag, dz in disps.items():
        if tag in tag_to_idx:
            dz_array[tag_to_idx[tag]] = dz
            
    mesh.point_data["Desplazamientos Z"] = dz_array
    
    mxx_array = np.zeros(mesh.n_cells)
    myy_array = np.zeros(mesh.n_cells)
    
    # In PyVista, cell data must map to the order cells are added.
    # Our faces list iterates over `elements.keys()`
    for i, tag in enumerate(elements.keys()):
        mxx_array[i] = mxx.get(tag, 0.0)
        myy_array[i] = myy.get(tag, 0.0)
        
    mesh.cell_data["Mxx"] = mxx_array
    mesh.cell_data["Myy"] = myy_array
    
    # Amplification factor
    warped = mesh.warp_by_scalar("Desplazamientos Z", factor=50.0)
    
    if active_field == "Desplazamientos":
        warped.set_active_scalars("Desplazamientos Z")
        plotter.add_mesh(warped, cmap="coolwarm", show_edges=True, edge_color="#333333")
    elif active_field == "Esfuerzos Mxx":
        warped.set_active_scalars("Mxx")
        plotter.add_mesh(warped, cmap="jet", show_edges=True, edge_color="#333333")
    elif active_field == "Esfuerzos Myy":
        warped.set_active_scalars("Myy")
        plotter.add_mesh(warped, cmap="jet", show_edges=True, edge_color="#333333")
        
    plotter.reset_camera()
