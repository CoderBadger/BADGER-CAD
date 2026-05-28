"""viga.py — Viga (Beam) — a horizontal structural member at a floor level.

Beams are defined by two plan endpoints and a rectangular cross-section.
They are the primary input for Hito 2's bay detection: ``shapely.ops.polygonize``
turns a planar graph of ``LineString`` segments into closed ``Polygon`` bays.

Hito connections
----------------
- **Hito 2 (current)**: ``as_shapely_line()`` feeds ``topology.detect_panios()``.
- **Hito 4**: cross-section attributes (``ancho``, ``canto``, ``material``)
  will be used to build ``elasticBeamColumn`` elements in OpenSeesPy.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any
import math
import uuid


@dataclass
class Viga:
    """A horizontal reinforced-concrete beam at a given floor level.

    The beam is defined as a line in plan (XY) between two endpoint nodes.
    No Z coordinate is stored — the elevation is determined at render time
    from ``Nivel.cota`` of the beam's floor.

    Attributes
    ----------
    nodo_inicial : tuple[float, float]
        Start-point (x, y) in plan coordinates [m].
    nodo_final : tuple[float, float]
        End-point (x, y) in plan coordinates [m].
    ancho : float
        Beam section width (horizontal) [m]. Default 0.25 m.
    canto : float
        Beam section depth (vertical, i.e. height below slab) [m]. Default 0.50 m.
    material : str
        Concrete grade, e.g. ``"H25"``.
    grupo_id : str
        ID of the ``Grupo`` this beam belongs to. Beams are assigned to functional
        groups (plants) rather than raw Z-levels.
    id : str
        Auto-generated unique identifier (8-char lowercase hex).
    """
    nodo_inicial: tuple[float, float]
    nodo_final:   tuple[float, float]

    ancho:    float = 0.25   # m — section width
    canto:    float = 0.50   # m — section depth
    material: str   = "H25"
    tipo:     str   = "RECTANGULAR"
    grupo_id: str   = ""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    _poligono_2d_recortado: Optional[Any] = field(default=None, init=False, repr=False)

    def invalidate_cache(self) -> None:
        """Clear the cached 2D footprint."""
        self._poligono_2d_recortado = None

    def get_polygon_2d(self, pilares_union=None):
        """Returns the shapely geometry of the beam minus the pillars."""
        if self._poligono_2d_recortado is not None:
            return self._poligono_2d_recortado
            
        try:
            from shapely.geometry import LineString, Polygon
            line = LineString([self.nodo_inicial, self.nodo_final])
            poly = line.buffer(self.ancho / 2, cap_style=2)
            if pilares_union is not None and not pilares_union.is_empty:
                poly = poly.difference(pilares_union)
            self._poligono_2d_recortado = poly
            return poly
        except ImportError:
            return None

    # ------------------------------------------------------------------ helpers
    def as_shapely_line(self):
        """Return this beam as a Shapely ``LineString``.

        Used by ``topology.detect_panios()`` to build the planar graph that
        ``shapely.ops.polygonize`` converts into closed bay polygons.

        Returns
        -------
        shapely.geometry.LineString
            A 2-D line from ``nodo_inicial`` to ``nodo_final``.
        """
        from shapely.geometry import LineString
        return LineString([self.nodo_inicial, self.nodo_final])

    @property
    def longitud(self) -> float:
        """Compute the Euclidean distance between ``nodo_inicial`` and ``nodo_final``."""
        x1, y1 = self.nodo_inicial
        x2, y2 = self.nodo_final
        return math.hypot(x2 - x1, y2 - y1)

    @property
    def seccion_label(self) -> str:
        """Human-readable section string, e.g. ``"25x50"`` [cm × cm]."""
        return f"{int(self.ancho * 100)}x{int(self.canto * 100)}"

    @property
    def peso_propio(self) -> float:
        """Linear self-weight in kN/m."""
        from badgercad.core.loads import DENSIDAD_HORMIGON
        return self.ancho * self.canto * DENSIDAD_HORMIGON

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Viga({self.seccion_label} "
            f"({self.nodo_inicial[0]:.2f},{self.nodo_inicial[1]:.2f}) → "
            f"({self.nodo_final[0]:.2f},{self.nodo_final[1]:.2f}) "
            f"id={self.id})"
        )
