"""Pilar (Column) — a vertical structural member spanning one or more floor levels.

In BadgerCAD's BIM-like model, a ``Pilar`` is defined by its plan position,
rectangular cross-section, rotation, material, and the two ``Nivel`` IDs that
bracket its vertical extent.  All geometric helpers return data in the same
coordinate system as the canvas: X and Y in metres, Z = elevation.

Hito connections
----------------
- **Hito 1**: 2D/3D rendering, placement tool, undo stack.
- **Hito 2**: ``footprint_2d()`` feeds ``shapely.Polygon`` for beam-bay
  detection and slab auto-creation.
- **Hito 5**: ``con_vinculacion_exterior`` → OpenSeesPy ``fix()`` boundary
  condition at the column base.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import uuid

MATERIAL_OPTIONS = ["H21", "H25", "H28", "H30", "H35", "ACERO"]


@dataclass
class Pilar:
    """A rectangular reinforced-concrete (or steel) column.

    Coordinate convention
    ---------------------
    - ``x``, ``y``: plan position of the column **centroid** [m].
    - ``ancho``:    cross-section dimension aligned with the global **X** axis
                    *before* rotation [m].
    - ``largo``:    cross-section dimension aligned with the global **Y** axis
                    *before* rotation [m].
    - ``angulo``:   counter-clockwise rotation in plan [degrees].
      A 90° pilar has its long dimension aligned with X.

    Attributes
    ----------
    x : float
        Centroid X-coordinate in plan [m].
    y : float
        Centroid Y-coordinate in plan [m].
    ancho : float
        Section width (X dimension before rotation) [m]. Default 0.30 m.
    largo : float
        Section depth (Y dimension before rotation) [m]. Default 0.30 m.
    angulo : float
        Counter-clockwise rotation in plan [degrees]. Default 0°.
    material : str
        Concrete grade (``"H25"``) or ``"ACERO"``.
        Must be one of ``MATERIAL_OPTIONS``.
    nivel_desde_id : str
        ID of the ``Nivel`` at the column base (start of vertical span).
    nivel_hasta_id : str
        ID of the ``Nivel`` at the column top  (end   of vertical span).
    con_vinculacion_exterior : bool
        ``True``  → column base is fixed to the foundation (OpenSeesPy will
                     apply a ``fix()`` boundary condition at ``nivel_desde``).
        ``False`` → column originates on a slab or transfer beam; no ground
                     constraint is applied.
    id : str
        Auto-generated unique identifier (8-char lowercase hex).
    """
    x: float
    y: float

    ancho:    float = 0.30   # m — X dimension before rotation
    largo:    float = 0.30   # m — Y dimension before rotation
    angulo:   float = 0.0    # degrees, counter-clockwise
    material: str   = "H25"

    nivel_desde_id: str = ""
    nivel_hasta_id: str = ""

    con_vinculacion_exterior: bool = True  # → fixed base for foundation module

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    # ------------------------------------------------------------------ helpers
    @property
    def seccion_label(self) -> str:
        """Human-readable cross-section string, e.g. ``"30x50"`` [cm × cm].

        Returns:
            String ``"{ancho_cm}x{largo_cm}"`` where dimensions are in
            whole centimetres (``int(dim * 100)``).
        """
        return f"{int(self.ancho * 100)}x{int(self.largo * 100)}"

    def bounds_2d(self) -> tuple[float, float, float, float]:
        """Axis-aligned bounding box (AABB) of the column footprint in plan.

        **Ignores rotation** (``angulo``).  This is intentional — the AABB is
        used for fast broad-phase spatial filtering.  For exact geometry
        (e.g. Shapely intersection tests), use ``footprint_2d()`` instead.

        Returns:
            ``(x_min, x_max, y_min, y_max)`` [m].
        """
        return (
            self.x - self.ancho / 2, self.x + self.ancho / 2,
            self.y - self.largo / 2, self.y + self.largo / 2,
        )

    def footprint_2d(self) -> list[tuple[float, float]]:
        """Four corner vertices of the column footprint in plan, rotation applied.

        Returns vertices in **counter-clockwise** order:
        ``[top-right, top-left, bottom-left, bottom-right]``
        (in local frame before rotation).

        The result is a direct drop-in for ``shapely.Polygon``::

            from shapely.geometry import Polygon
            poly = Polygon(pilar.footprint_2d())
            assert poly.is_valid

        And is compatible with Gmsh ``addPlaneSurface`` point lists (Hito 2).

        Mathematical derivation (2D rotation matrix):
            ``x' = cx·cos(θ) − cy·sin(θ) + pilar.x``
            ``y' = cx·sin(θ) + cy·cos(θ) + pilar.y``

        Returns:
            List of 4 ``(x, y)`` tuples [m] in world coordinates.
        """
        import math
        a, l  = self.ancho / 2, self.largo / 2
        local = [(a, l), (-a, l), (-a, -l), (a, -l)]   # CCW: TR, TL, BL, BR
        if self.angulo:
            cos_a = math.cos(math.radians(self.angulo))
            sin_a = math.sin(math.radians(self.angulo))
            return [
                (self.x + cx * cos_a - cy * sin_a,
                 self.y + cx * sin_a + cy * cos_a)
                for cx, cy in local
            ]
        return [(self.x + cx, self.y + cy) for cx, cy in local]

    def __repr__(self) -> str:  # pragma: no cover
        vin = "CON_VIN" if self.con_vinculacion_exterior else "SIN_VIN"
        return (
            f"Pilar({self.seccion_label} @ ({self.x:.2f},{self.y:.2f}) "
            f"∠{self.angulo}° {vin} id={self.id})"
        )
