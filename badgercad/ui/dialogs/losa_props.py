"""losa_props.py — Dialog for slab type and thickness, shown after polygon closure."""
from __future__ import annotations
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QComboBox, QDoubleSpinBox, QDialogButtonBox,
    QLabel, QGroupBox, QWidget,
)
from badgercad.core.elements.losa import LOSA_TIPOS
from badgercad.core.elements.grupo import Grupo

_STYLE = """
QDialog{background:#1E2330;color:#E0E6F0;}
QGroupBox{border:1px solid #2E3A4E;border-radius:6px;margin-top:8px;
          padding-top:8px;color:#8090A8;font-size:10px;font-weight:600;}
QGroupBox::title{subcontrol-origin:margin;left:10px;}
QLabel{color:#C0CDE0;font-size:12px;}
QDoubleSpinBox,QComboBox{background:#252932;border:1px solid #2E3A4E;
  border-radius:4px;color:#E0E6F0;padding:4px 8px;font-size:12px;min-width:120px;}
QDoubleSpinBox:focus,QComboBox:focus{border-color:#4A90D9;}
QDialogButtonBox QPushButton{background:#2E3A4E;color:#E0E6F0;
  border:1px solid #4A90D9;border-radius:4px;padding:6px 20px;font-weight:600;}
QDialogButtonBox QPushButton:hover{background:#4A90D9;color:#fff;}
QDialogButtonBox QPushButton:default{background:#4A90D9;color:#fff;}
"""


class LosaPropsDialog(QDialog):
    """Slab properties dialog, shown once the polygon is closed."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        grupo_activo: Optional[Grupo] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Propiedades de Losa")
        self.setFixedWidth(340)
        self.setStyleSheet(_STYLE)
        self._grupo = grupo_activo
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        title = QLabel("▭  Definición de Losa")
        title.setStyleSheet(
            "font-size:14px;font-weight:700;color:#4A90D9;"
            "padding-bottom:4px;border-bottom:1px solid #2E3A4E;"
        )
        root.addWidget(title)

        grp = QGroupBox("Geometría y Tipo")
        lay = QFormLayout(grp)
        lay.setSpacing(8)

        self._tipo = QComboBox()
        self._tipo.addItems(LOSA_TIPOS)

        self._espesor = QDoubleSpinBox()
        self._espesor.setRange(0.08, 0.60)
        self._espesor.setSingleStep(0.02)
        self._espesor.setValue(0.20)
        self._espesor.setSuffix(" m")
        self._espesor.setDecimals(2)

        lay.addRow("Tipo:", self._tipo)
        lay.addRow("Espesor:", self._espesor)
        root.addWidget(grp)

        info_grp = QGroupBox("Grupo asignado")
        info_lay = QFormLayout(info_grp)
        grupo_txt = self._grupo.nombre if self._grupo else "Sin grupo"
        info_lay.addRow("Grupo:", QLabel(f"<b>{grupo_txt}</b>"))
        root.addWidget(info_grp)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_props(self) -> dict:
        return {
            "tipo":     self._tipo.currentText(),
            "espesor":  self._espesor.value(),
            "grupo_id": self._grupo.id if self._grupo else "",
        }
