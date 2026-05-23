"""Grupo (Floor Group) — a set of floors that share identical structural geometry.

In CYPECAD, if floors 2, 3 and 4 are identical (same slab layout, same beams)
they are placed in a single Grupo.  Slabs and beams are drawn once at the Grupo
level; BadgerCAD replicates them to every Nivel inside the group automatically.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import uuid


@dataclass
class Grupo:
    """A logical group of structurally identical floor levels.

    Attributes:
        nombre:         Display name, e.g. "Grupo 1", "Sotano".
        nivel_ids:      Ordered list of Nivel IDs belonging to this group
                        (sorted bottom-up by cota).
        carga_muerta:   Superimposed dead load applied to all slabs  [kN/m²].
        sobrecarga_uso: Live load applied to all slabs               [kN/m²].
        losa_ids:       IDs of Losa objects belonging to this group.
        viga_ids:       IDs of Viga objects belonging to this group (Hito 2).
        id:             Auto-generated unique identifier (8-char hex).
    """
    nombre: str
    nivel_ids: List[str] = field(default_factory=list)

    carga_muerta: float = 2.0   # kN/m²
    sobrecarga_uso: float = 2.0  # kN/m²

    losa_ids: List[str] = field(default_factory=list)
    viga_ids: List[str] = field(default_factory=list)

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Grupo('{self.nombre}', niveles={len(self.nivel_ids)}, id={self.id})"
        )
