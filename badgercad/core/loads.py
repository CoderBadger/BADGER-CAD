"""loads.py — Data models for structural loads and hypotheses."""
from __future__ import annotations
from dataclasses import dataclass, field
import uuid
from typing import Tuple

DENSIDAD_HORMIGON = 25.0  # kN/m3 - Densidad estándar del hormigón armado

class Hipotesis:
    """Enumeration of standard load hypotheses (NB 1225002 / ASCE 7)."""
    PP = "PP"  # Peso Propio (Self-weight)
    CM = "CM"  # Carga Muerta / Superimpuesta (Dead Load)
    CV = "CV"  # Sobrecarga de Uso (Live Load)

@dataclass
class CargaLineal:
    """A linear load applied on a floor, typically representing masonry walls."""
    p1: Tuple[float, float]
    p2: Tuple[float, float]
    magnitud: float        # kN/m
    hipotesis: str = Hipotesis.CM
    grupo_id: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def __repr__(self) -> str:
        return f"CargaLineal(mag={self.magnitud}kN/m, hip={self.hipotesis}, id={self.id})"
