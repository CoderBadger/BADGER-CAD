"""Losa (Slab) — a polygonal horizontal structural slab belonging to a Grupo."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import uuid

LOSA_TIPOS = ["MACIZA", "RETICULAR", "VIGUETAS", "MIXTA"]


@dataclass
class Losa:
    """A polygonal reinforced-concrete slab.

    Vertices are stored in plan (X, Y) coordinates [m].
    The slab belongs to a Grupo, not to a single Nivel — it is replicated
    automatically to every floor in the group.

    Attributes:
        vertices:   Ordered list of (x, y) vertices defining the slab perimeter.
        tipo:       One of LOSA_TIPOS.
        espesor:    Slab thickness [m].
        grupo_id:   ID of the Grupo this slab belongs to.
        id:         Auto-generated unique identifier (8-char hex).
    """
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    tipo: str = "MACIZA"
    espesor: float = 0.20          # m
    grupo_id: str = ""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    # ------------------------------------------------------------------ helpers
    def is_valid(self) -> bool:
        """A losa needs at least 3 vertices to be a valid polygon."""
        return len(self.vertices) >= 3

    def area_aproximada(self) -> float:
        """Shoelace formula for polygon area [m²]."""
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

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Losa({self.tipo} e={self.espesor:.2f}m "
            f"verts={len(self.vertices)} id={self.id})"
        )
