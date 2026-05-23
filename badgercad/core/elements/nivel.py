"""Nivel (Floor Level) — represents a horizontal structural floor at a given elevation."""
from __future__ import annotations
from dataclasses import dataclass, field
import uuid


@dataclass
class Nivel:
    """A structural floor level defined by its elevation (cota) above foundation.

    Attributes:
        nombre: Display name, e.g. "Planta 1", "Cubierta".
        cota:   Elevation in metres measured from the foundation datum (Z=0).
        id:     Auto-generated unique identifier (8-char hex).
    """
    nombre: str
    cota: float  # metres from foundation

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def __repr__(self) -> str:  # pragma: no cover
        return f"Nivel('{self.nombre}', cota={self.cota:.2f} m, id={self.id})"

    def __lt__(self, other: "Nivel") -> bool:
        return self.cota < other.cota
