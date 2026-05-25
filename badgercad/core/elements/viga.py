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
        """Beam length in plan [m]."""
        dx = self.nodo_final[0] - self.nodo_inicial[0]
        dy = self.nodo_final[1] - self.nodo_inicial[1]
        return (dx ** 2 + dy ** 2) ** 0.5

    @property
    def seccion_label(self) -> str:
        """Human-readable section string, e.g. ``"25x50"`` [cm × cm]."""
        return f"{int(self.ancho * 100)}x{int(self.canto * 100)}"

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Viga({self.seccion_label} "
            f"({self.nodo_inicial[0]:.2f},{self.nodo_inicial[1]:.2f}) → "
            f"({self.nodo_final[0]:.2f},{self.nodo_final[1]:.2f}) "
            f"id={self.id})"
        )
