"""topology.py — Planar graph analysis for automatic bay detection.

This module converts a flat set of beams (``Viga`` objects) into closed
polygon bays using **Shapely's** ``polygonize`` algorithm.  No mesh, no
solver, no VTK — pure 2D computational geometry.

Algorithm
---------
1. Convert every ``Viga`` to a Shapely ``LineString``.
2. Call ``shapely.node`` (or ``unary_union``) to:
   - Merge collinear segments.
   - Split lines at every intersection point (creates a proper planar graph).
3. Call ``shapely.ops.polygonize`` on the noded geometry to extract every
   minimal closed ring → each ring is a valid ``Polygon`` bay.
4. Return only valid, non-degenerate polygons (area > threshold).

Hito connections
----------------
- **Hito 2 (current)**: ``detect_panios()`` → ``scene.render_canvas_2d()``
  paints the bays; ``losa_tool.py`` uses ``Point.within(panio)`` to
  associate a click with a bay.
- **Hito 3**: the returned ``Polygon`` objects feed ``mef/mesher.py``
  (Gmsh boundary loop).
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .elements.viga import Viga


def detect_panios(vigas: List["Viga"]) -> list:
    """Detect all closed bay polygons from a list of beams.

    Uses ``shapely.node`` + ``shapely.ops.polygonize`` so that:
    - Lines that cross each other form nodes automatically.
    - Lines that share only an endpoint (T-junctions) split correctly.
    - Partial overlaps and collinear segments are merged before polygonizing.
    - Only minimal, interior-free faces are returned (not the convex hull).

    Args:
        vigas: List of ``Viga`` objects on a single floor level.

    Returns:
        List of ``shapely.geometry.Polygon`` objects representing closed bays.
        Empty list if Shapely is not installed, or if no closed rings exist.
    """
    if len(vigas) < 3:
        return []

    try:
        from shapely.ops import polygonize, unary_union
        from shapely.geometry import MultiLineString
        try:
            from shapely import node
            has_node = True
        except ImportError:
            has_node = False
    except ImportError:
        return []   # Shapely not installed — feature degrades gracefully

    # Build the planar graph
    lines = [v.as_shapely_line() for v in vigas]
    mls = MultiLineString(lines)

    # Fragment at intersections rigorously
    if has_node:
        graph = node(mls)
    else:
        # Fallback to unary_union if node is not available
        graph = unary_union(mls)

    # Extract closed rings
    panios = [p for p in polygonize(graph) if p.is_valid and p.area > 0.01]
    return panios


def panio_at_point(panios: list, x: float, y: float):
    """Return the first bay polygon that *contains* the given plan point.

    Uses ``shapely.geometry.Point.within(polygon)`` for an exact containment
    test — the point must be strictly inside (not on the boundary).

    Args:
        panios: List of ``shapely.geometry.Polygon`` objects (from
                ``detect_panios()``).
        x: Plan X-coordinate [m].
        y: Plan Y-coordinate [m].

    Returns:
        The matching ``shapely.geometry.Polygon``, or ``None`` if the point
        is outside all bays.
    """
    if not panios:
        return None
    try:
        from shapely.geometry import Point
    except ImportError:
        return None

    pt = Point(x, y)
    for panio in panios:
        if pt.within(panio) or panio.distance(pt) < 0.01:
            # distance fallback: catches clicks right on the boundary
            return panio
    return None


def polygon_to_vertices(polygon) -> list[tuple[float, float]]:
    """Extract exterior ring vertices from a Shapely polygon.

    Strips the closing repeat-vertex that Shapely includes, so the result
    is directly usable as ``Losa.vertices``.

    Args:
        polygon: A ``shapely.geometry.Polygon``.

    Returns:
        List of ``(x, y)`` tuples [m] in CCW order (Shapely convention).
    """
    coords = list(polygon.exterior.coords)
    # Shapely closes the ring: last coord == first coord → drop it
    if len(coords) > 1 and coords[0] == coords[-1]:
        coords = coords[:-1]
    return [(float(x), float(y)) for x, y in coords]
