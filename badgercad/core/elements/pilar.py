"""Pilar (Column) — a vertical structural member spanning one or more floor levels."""
from __future__ import annotations
from dataclasses import dataclass, field
import uuid

MATERIAL_OPTIONS = ["H21", "H25", "H28", "H30", "H35", "ACERO"]


@dataclass
class Pilar:
    """A rectangular reinforced-concrete (or steel) column.

    Attributes:
        x, y:                    Position in plan [m] (centroid).
        ancho:                   Section dimension parallel to X-axis [m].
        largo:                   Section dimension parallel to Y-axis [m].
        angulo:                  Rotation in plan [degrees].
        material:                Concrete grade or ACERO.
        nivel_desde_id:          ID of the Nivel where the column starts (bottom).
        nivel_hasta_id:          ID of the Nivel where the column ends   (top).
        con_vinculacion_exterior: True  → column is fixed to foundation (OpenSees
                                          will apply a fixed boundary condition).
                                  False → column originates on a slab or transfer
                                          beam (no ground constraint).
        id:                      Auto-generated unique identifier (8-char hex).
    """
    x: float
    y: float

    ancho: float = 0.30            # m — X dimension
    largo: float = 0.30            # m — Y dimension
    angulo: float = 0.0            # degrees
    material: str = "H25"

    nivel_desde_id: str = ""
    nivel_hasta_id: str = ""

    # CRITICAL for foundation module (Hito 5):
    con_vinculacion_exterior: bool = True

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    # ------------------------------------------------------------------ helpers
    @property
    def seccion_label(self) -> str:
        """Human-readable section, e.g. '30x30'."""
        return f"{int(self.ancho * 100)}x{int(self.largo * 100)}"

    def bounds_2d(self) -> tuple[float, float, float, float]:
        """Return (x_min, x_max, y_min, y_max) of the column footprint."""
        return (
            self.x - self.ancho / 2, self.x + self.ancho / 2,
            self.y - self.largo / 2, self.y + self.largo / 2,
        )

    def __repr__(self) -> str:  # pragma: no cover
        vin = "CON_VIN" if self.con_vinculacion_exterior else "SIN_VIN"
        return (
            f"Pilar({self.seccion_label} @ ({self.x:.2f},{self.y:.2f}) "
            f"{vin} id={self.id})"
        )
