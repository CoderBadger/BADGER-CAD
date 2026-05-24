"""Nivel (Floor Level) — a horizontal structural plane at a given elevation.

Every ``Nivel`` represents one horizontal slice of the building.  The
foundation is always at ``cota = 0.0 m``; all other elevations are measured
upward from that datum.

Ordering
--------
``Nivel`` implements ``__lt__`` so that ``sorted(project.niveles)`` and
``project.niveles_ordenados()`` return floors in bottom-up order without
a custom key.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import uuid


@dataclass
class Nivel:
    """A structural floor level defined by its elevation above the foundation.

    Attributes
    ----------
    nombre : str
        Display name shown in the UI and floor tree, e.g. ``"Planta 1"``,
        ``"Cubierta"``, ``"Cimentación"``.
    cota : float
        Elevation in metres measured from the foundation datum (Z = 0).
        The foundation level itself is conventionally ``cota = 0.0``.
        All other floors must have a strictly positive cota.
    id : str
        Auto-generated unique identifier (8-char lowercase hex).
        Used as a foreign key in ``Pilar.nivel_desde_id`` / ``nivel_hasta_id``
        and in ``Grupo.nivel_ids``.
    """
    nombre: str
    cota:   float   # metres above foundation datum (Z = 0)

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def __repr__(self) -> str:  # pragma: no cover
        return f"Nivel('{self.nombre}', cota={self.cota:.2f} m, id={self.id})"

    def __lt__(self, other: "Nivel") -> bool:
        """Enable ``sorted(niveles)`` to return bottom-up order by cota."""
        return self.cota < other.cota
