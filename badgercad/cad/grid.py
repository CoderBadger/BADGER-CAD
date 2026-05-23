"""grid.py — CAD grid mesh generation and coordinate snapping."""
from __future__ import annotations
import numpy as np
import pyvista as pv

GRID_COLOR       = "#1A2D3D"
GRID_COLOR_MAJOR = "#243D52"
AXIS_COLOR_X     = "#E05252"
AXIS_COLOR_Y     = "#52C752"


def build_grid_mesh(extent: float = 60.0,
                    spacing: float = 1.0) -> pv.PolyData:
    """Return a PolyData line-mesh representing the CAD grid.

    Args:
        extent:  Total half-size of the grid  [m].  Grid goes from -extent to +extent.
        spacing: Distance between grid lines  [m].
    """
    n = int(extent / spacing)
    half = n * spacing

    points: list[list[float]] = []
    lines:  list[int]          = []
    idx = 0

    for i in range(-n, n + 1):
        v = i * spacing
        # Horizontal line
        points += [[-half, v, 0.0], [half, v, 0.0]]
        lines  += [2, idx, idx + 1];  idx += 2
        # Vertical line
        points += [[v, -half, 0.0], [v, half, 0.0]]
        lines  += [2, idx, idx + 1];  idx += 2

    mesh = pv.PolyData()
    mesh.points = np.array(points, dtype=np.float32)
    mesh.lines  = np.array(lines,  dtype=np.int32)
    return mesh


def build_major_grid_mesh(extent: float = 60.0,
                           major_spacing: float = 5.0) -> pv.PolyData:
    """Coarser grid lines drawn on top for major intervals (e.g. every 5 m)."""
    return build_grid_mesh(extent=extent, spacing=major_spacing)


def build_axes_mesh(length: float = 3.0) -> tuple[pv.PolyData, pv.PolyData]:
    """Return (x_axis_mesh, y_axis_mesh) as coloured lines at the origin."""
    x_pts   = np.array([[0, 0, 0.01], [length, 0, 0.01]], dtype=float)
    x_lines = np.array([2, 0, 1], dtype=int)
    x_mesh  = pv.PolyData(x_pts, lines=x_lines)

    y_pts   = np.array([[0, 0, 0.01], [0, length, 0.01]], dtype=float)
    y_lines = np.array([2, 0, 1], dtype=int)
    y_mesh  = pv.PolyData(y_pts, lines=y_lines)

    return x_mesh, y_mesh


def snap_to_grid(x: float, y: float,
                 spacing: float = 1.0) -> tuple[float, float]:
    """Round (x, y) to the nearest grid intersection.

    Args:
        x, y:    Raw world coordinates.
        spacing: Grid spacing to snap to  [m].

    Returns:
        Snapped (x, y) as floats rounded to three decimal places.
    """
    sx = round(round(x / spacing) * spacing, 3)
    sy = round(round(y / spacing) * spacing, 3)
    return sx, sy


def add_grid_to_plotter(plotter,
                        extent: float   = 60.0,
                        spacing: float  = 1.0,
                        major: float    = 5.0) -> None:
    """Add minor + major grid and axes to a plotter (clears previous grid first)."""
    plotter.remove_actor("grid_minor")
    plotter.remove_actor("grid_major")
    plotter.remove_actor("axis_x")
    plotter.remove_actor("axis_y")

    minor_mesh = build_grid_mesh(extent, spacing)
    plotter.add_mesh(minor_mesh, color=GRID_COLOR,       line_width=0.5,
                     name="grid_minor", pickable=False)

    major_mesh = build_major_grid_mesh(extent, major)
    plotter.add_mesh(major_mesh, color=GRID_COLOR_MAJOR, line_width=1.0,
                     name="grid_major", pickable=False)

    x_mesh, y_mesh = build_axes_mesh()
    plotter.add_mesh(x_mesh, color=AXIS_COLOR_X, line_width=2.5,
                     name="axis_x", pickable=False)
    plotter.add_mesh(y_mesh, color=AXIS_COLOR_Y, line_width=2.5,
                     name="axis_y", pickable=False)
