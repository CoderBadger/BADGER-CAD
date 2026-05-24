"""Grupo (Floor Group) — a set of floors that share identical structural geometry.

CYPECAD concept
---------------
In CYPECAD (and in BadgerCAD), if floors 2, 3 and 4 are structurally
identical (same slab layout, same beam spans, same loads), they are placed
in a single ``Grupo``.  The engineer draws slabs and beams once at the group
level; the application replicates the geometry to every ``Nivel`` in the
group at render and analysis time.

Example structure:
    - Grupo 0 → [Cimentación]   (beams not modelled; only pile-cap slabs)
    - Grupo 1 → [Planta 1]      (unique floor with different slab layout)
    - Grupo 2 → [Planta 2, Planta 3, Cubierta]  (identical floors)

Hito roadmap
------------
- **Hito 1**: ``losa_ids`` membership and load attributes (carga_muerta,
  sobrecarga_uso) are defined.
- **Hito 2**: ``viga_ids`` will be populated by the Viga tool; Shapely bay
  detection will use the combined set of vigas to auto-create losas.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import uuid


@dataclass
class Grupo:
    """A logical group of structurally identical floor levels.

    Attributes
    ----------
    nombre : str
        Display name shown in the floor tree, e.g. ``"Grupo 1"``,
        ``"Pisos Tipo"``.
    nivel_ids : List[str]
        Ordered list (bottom-up by ``cota``) of ``Nivel.id`` values belonging
        to this group.  A ``Nivel`` can belong to at most one ``Grupo``.
    carga_muerta : float
        Superimposed dead load applied uniformly to all slabs in this group
        [kN/m²].  Default: 2.0 kN/m² (typical finishing + partitions).
    sobrecarga_uso : float
        Characteristic live load applied to all slabs [kN/m²].
        Default: 2.0 kN/m² (residential; adjust per applicable code).
    losa_ids : List[str]
        IDs of ``Losa`` objects belonging to this group.  Maintained
        automatically by ``Project.add_losa()`` and ``Project.remove_losa()``.
    viga_ids : List[str]
        IDs of ``Viga`` objects belonging to this group (Hito 2).
        Reserved field; empty in Hito 1.
    id : str
        Auto-generated unique identifier (8-char lowercase hex).
    """
    nombre:     str
    nivel_ids:  List[str] = field(default_factory=list)

    carga_muerta:   float = 2.0   # kN/m² — superimposed dead load
    sobrecarga_uso: float = 2.0   # kN/m² — characteristic live load

    losa_ids: List[str] = field(default_factory=list)
    viga_ids: List[str] = field(default_factory=list)  # reserved for Hito 2

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Grupo('{self.nombre}', niveles={len(self.nivel_ids)}, "
            f"losas={len(self.losa_ids)}, id={self.id})"
        )
