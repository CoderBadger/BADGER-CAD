"""pilar_props.py — Dialog for defining column properties before placement."""
from __future__ import annotations
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDoubleSpinBox, QComboBox, QCheckBox, QDialogButtonBox,
    QLabel, QGroupBox, QWidget,
)
from PyQt6.QtCore import Qt

from badgercad.core.elements.pilar import MATERIAL_OPTIONS
from badgercad.core.project import Project, get_project


_DIALOG_STYLE = """
QDialog {
    background: #1E2330;
    color: #E0E6F0;
}
QGroupBox {
    border: 1px solid #2E3A4E;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 8px;
    color: #8090A8;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; }
QLabel  { color: #C0CDE0; font-size: 12px; }
QDoubleSpinBox, QComboBox {
    background: #252932;
    border: 1px solid #2E3A4E;
    border-radius: 4px;
    color: #E0E6F0;
    padding: 4px 8px;
    font-size: 12px;
    min-width: 100px;
}
QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #4A90D9;
}
QCheckBox { color: #C0CDE0; spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #4A90D9;
    border-radius: 3px;
    background: #252932;
}
QCheckBox::indicator:checked { background: #4A90D9; }
QDialogButtonBox QPushButton {
    background: #2E3A4E;
    color: #E0E6F0;
    border: 1px solid #4A90D9;
    border-radius: 4px;
    padding: 6px 20px;
    font-weight: 600;
}
QDialogButtonBox QPushButton:hover   { background: #4A90D9; color: #fff; }
QDialogButtonBox QPushButton:default { background: #4A90D9; color: #fff; }
"""


class PilarPropsDialog(QDialog):
    """Column properties dialog — opened BEFORE the first click (CYPECAD pattern)."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        project: Optional[Project] = None,
        initial_props: Optional[dict] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Propiedades del Pilar")
        self.setFixedWidth(380)
        self.setStyleSheet(_DIALOG_STYLE)
        self._project = project or get_project()

        self._build_ui()
        if initial_props:
            self._apply_props(initial_props)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        # Header
        title = QLabel("⬛  Definición de Pilar / Columna")
        title.setStyleSheet(
            "font-size:14px;font-weight:700;color:#4A90D9;"
            "padding-bottom:4px;border-bottom:1px solid #2E3A4E;"
        )
        root.addWidget(title)

        # --- Section group -------------------------------------------
        sec_grp = QGroupBox("Sección")
        sec_lay = QFormLayout(sec_grp)
        sec_lay.setSpacing(8)

        self._ancho = QDoubleSpinBox()
        self._ancho.setRange(0.10, 2.00)
        self._ancho.setSingleStep(0.05)
        self._ancho.setValue(0.30)
        self._ancho.setSuffix(" m")
        self._ancho.setDecimals(2)

        self._largo = QDoubleSpinBox()
        self._largo.setRange(0.10, 2.00)
        self._largo.setSingleStep(0.05)
        self._largo.setValue(0.30)
        self._largo.setSuffix(" m")
        self._largo.setDecimals(2)

        self._angulo = QDoubleSpinBox()
        self._angulo.setRange(0.0, 90.0)
        self._angulo.setSingleStep(15.0)
        self._angulo.setValue(0.0)
        self._angulo.setSuffix("°")
        self._angulo.setDecimals(1)

        sec_lay.addRow("Ancho (X):", self._ancho)
        sec_lay.addRow("Largo (Y):", self._largo)
        sec_lay.addRow("Rotación:", self._angulo)
        root.addWidget(sec_grp)

        # --- Material group ------------------------------------------
        mat_grp = QGroupBox("Material")
        mat_lay = QFormLayout(mat_grp)
        mat_lay.setSpacing(8)

        self._material = QComboBox()
        self._material.addItems(MATERIAL_OPTIONS)
        self._material.setCurrentText("H25")
        mat_lay.addRow("Hormigón:", self._material)
        root.addWidget(mat_grp)

        # --- Spans group ---------------------------------------------
        span_grp = QGroupBox("Altura — Niveles")
        span_lay = QFormLayout(span_grp)
        span_lay.setSpacing(8)

        self._nivel_desde = QComboBox()
        self._nivel_hasta = QComboBox()
        self._populate_niveles()

        span_lay.addRow("Nace en nivel:", self._nivel_desde)
        span_lay.addRow("Muere en nivel:", self._nivel_hasta)
        root.addWidget(span_grp)

        # --- Foundation group ----------------------------------------
        found_grp = QGroupBox("Cimentación")
        found_lay = QVBoxLayout(found_grp)

        self._vinculacion = QCheckBox(
            "Con vinculación exterior (empotrado a cimentación)"
        )
        self._vinculacion.setChecked(True)
        self._vinculacion.setToolTip(
            "Activar si el pilar nace en la cimentación.\n"
            "OpenSees aplicará un apoyo fijo (Fixed BC).\n"
            "Desactivar si el pilar nace sobre viga o losa de transición."
        )
        found_lay.addWidget(self._vinculacion)

        vin_note = QLabel(
            "ⓘ  Requerido para el módulo de Zapatas (Hito 5)"
        )
        vin_note.setStyleSheet("color:#5A8FA8;font-size:10px;")
        found_lay.addWidget(vin_note)
        root.addWidget(found_grp)

        # --- Buttons -------------------------------------------------
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _populate_niveles(self) -> None:
        for cb in (self._nivel_desde, self._nivel_hasta):
            cb.clear()
        niveles = self._project.niveles_ordenados()
        for n in niveles:
            label = f"{n.nombre}  ({n.cota:+.2f} m)"
            self._nivel_desde.addItem(label, userData=n.id)
            self._nivel_hasta.addItem(label, userData=n.id)

        # Sensible defaults: desde=lowest, hasta=highest
        if len(niveles) >= 2:
            self._nivel_desde.setCurrentIndex(0)
            self._nivel_hasta.setCurrentIndex(len(niveles) - 1)

    def _apply_props(self, props: dict) -> None:
        self._ancho.setValue(props.get("ancho", 0.30))
        self._largo.setValue(props.get("largo", 0.30))
        self._angulo.setValue(props.get("angulo", 0.0))
        self._material.setCurrentText(props.get("material", "H25"))
        self._vinculacion.setChecked(props.get("con_vinculacion_exterior", True))

    # ------------------------------------------------------------------ result
    def get_props(self) -> dict:
        return {
            "ancho":                   self._ancho.value(),
            "largo":                   self._largo.value(),
            "angulo":                  self._angulo.value(),
            "material":                self._material.currentText(),
            "nivel_desde_id":          self._nivel_desde.currentData(),
            "nivel_hasta_id":          self._nivel_hasta.currentData(),
            "con_vinculacion_exterior": self._vinculacion.isChecked(),
        }
