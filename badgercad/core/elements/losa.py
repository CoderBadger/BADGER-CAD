"""Losa (Slab) — a polygonal horizontal structural slab belonging to a Grupo.

Model ownership
---------------
A ``Losa`` belongs to a ``Grupo``, **not** to a single ``Nivel``.  The slab
geometry is defined once at the group level; ``render_3d_complete`` replicates
it to every ``Nivel`` in the group at render time.  This matches the CYPECAD
data model where identical floors share a single slab definition.

Polygon convention
------------------
Vertices are stored in plan (X, Y) coordinates [m] in counter-clockwise order
(CCW).  No Z coordinate is stored — the elevation is determined at render time
from the ``Nivel.cota`` of each floor in the parent ``Grupo``.

Hito connections
----------------
- **Hito 1**: 2D polygon rendering (``_losa_polygon``), 3D extrusion
  (``_losa_solid_3d``), area computation (``area_aproximada``).
- **Hito 2**: ``vertices`` feeds directly into ``shapely.Polygon`` for beam
  bay detection::

      from shapely.geometry import Polygon
      poly = Polygon(losa.vertices)   # no conversion needed

  ``espesor`` will be passed to Gmsh for meshing the slab volume.
- **Hito 5**: ``tipo`` determines the reinforcement model used by OpenSeesPy.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import uuid

LOSA_TIPOS = ["MACIZA", "RETICULAR", "VIGUETAS", "MIXTA"]


@dataclass
class Losa:
    """A polygonal reinforced-concrete slab.

    Attributes
    ----------
    vertices : List[Tuple[float, float]]
        Ordered list of ``(x, y)`` vertices defining the slab perimeter [m].
        Minimum 3 vertices for a valid slab (see ``is_valid()``).
        Compatible directly with ``shapely.Polygon(losa.vertices)`` — no
        coordinate conversion required.
    tipo : str
        Slab construction type.  Must be one of ``LOSA_TIPOS``
        (``"MACIZA"``, ``"RETICULAR"``, ``"VIGUETAS"``, ``"MIXTA"``).
        Default: ``"MACIZA"`` (solid flat slab).
    espesor : float
        Slab thickness [m].  Used for 3D extrusion in ``_losa_solid_3d``
        and will be passed to Gmsh in Hito 2.  Default: 0.20 m.
    grupo_id : str
        ID of the ``Grupo`` this slab belongs to.  Set automatically by
        ``Project.add_losa()``.
    id : str
        Auto-generated unique identifier (8-char lowercase hex).
    """
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    tipo:     str   = "MACIZA"
    espesor:  float = 0.20          # m — slab thickness
    grupo_id: str   = ""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    # ------------------------------------------------------------------ helpers
    def is_valid(self) -> bool:
        """Return ``True`` if the slab has at least 3 vertices (a valid polygon).

        A slab with fewer than 3 vertices cannot be triangulated, rendered,
        or meshed and should be treated as an incomplete input.

        Returns:
            ``bool``
        """
        return len(self.vertices) >= 3

    def area_aproximada(self) -> float:
        """Compute the polygon area using the **Shoelace formula** [m²].

        The Shoelace (Gauss's) formula computes the signed area of a polygon
        from its vertices.  The absolute value is returned so both CW and CCW
        winding orders produce a positive result.

        Returns:
            Area in m².  Returns 0.0 for degenerate polygons with fewer than
            3 vertices.

        Note:
            This is a 2D approximation assuming the slab is flat in plan.
            Non-convex (concave) polygons are handled correctly as long as
            the vertices do not self-intersect.
        """
        verts = self.vertices
        n = len(verts)
        if n < 3:
            return 0.0
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += verts[i][0] * verts[j][1]
            area -= verts[j][0] * verts[i][1]
        return abs(area) / 2.0

    @property
    def peso_propio(self) -> float:
        """Superficial self-weight in kN/m2."""
        from badgercad.core.loads import DENSIDAD_HORMIGON
        return self.espesor * DENSIDAD_HORMIGON

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Losa({self.tipo} e={self.espesor:.2f}m "
            f"verts={len(self.vertices)} id={self.id})"
        )
