"""viga_props.py — Dialog for beam (Viga) properties."""
from __future__ import annotations
from typing import Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDialogButtonBox, QLabel, QDoubleSpinBox, QComboBox,
    QGroupBox, QWidget,
)
from PyQt6.QtCore import Qt


class VigaPropsDialog(QDialog):
    """Dialog for setting/changing beam properties before drawing."""

    def __init__(self, parent: Optional[QWidget] = None, current_props: Optional[dict] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Propiedades de Viga")
        self.setFixedSize(300, 250)
        self.setStyleSheet("""
            QDialog { background: #161C26; color: #E0ECEF; }
            QLabel { font-size: 12px; }
            QGroupBox { border: 1px solid #2A3444; margin-top: 10px; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; }
            QDoubleSpinBox, QComboBox { background: #0D1117; color: #E0ECEF; border: 1px solid #2A3444; padding: 4px; border-radius: 2px; }
            QPushButton { background: #2A3444; color: #E0ECEF; border: none; padding: 6px 12px; border-radius: 2px; }
            QPushButton:hover { background: #3A4A5F; }
        """)

        self._ancho = 0.25
        self._canto = 0.50
        self._material = "H25"
        self._tipo = "RECTANGULAR"

        if current_props:
            self._ancho = current_props.get("ancho", 0.25)
            self._canto = current_props.get("canto", 0.50)
            self._material = current_props.get("material", "H25")
            self._tipo = current_props.get("tipo", "RECTANGULAR")

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        group = QGroupBox("Sección Transversal")
        form = QFormLayout(group)
        
        self.spin_ancho = QDoubleSpinBox()
        self.spin_ancho.setRange(0.10, 2.00)
        self.spin_ancho.setSingleStep(0.05)
        self.spin_ancho.setDecimals(2)
        self.spin_ancho.setSuffix(" m")
        self.spin_ancho.setValue(self._ancho)

        self.spin_canto = QDoubleSpinBox()
        self.spin_canto.setRange(0.10, 3.00)
        self.spin_canto.setSingleStep(0.05)
        self.spin_canto.setDecimals(2)
        self.spin_canto.setSuffix(" m")
        self.spin_canto.setValue(self._canto)

        self.combo_mat = QComboBox()
        self.combo_mat.addItems(["H20", "H25", "H30", "H35", "H40"])
        self.combo_mat.setCurrentText(self._material)

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Viga Rectangular de Hormigón", "Zuncho de Borde (Límite topológico)"])
        if self._tipo == "ZUNCHO_BORDE":
            self.combo_tipo.setCurrentIndex(1)
        else:
            self.combo_tipo.setCurrentIndex(0)
            
        self.combo_tipo.currentIndexChanged.connect(self._on_tipo_changed)

        form.addRow("Tipo:", self.combo_tipo)
        form.addRow("Ancho (b):", self.spin_ancho)
        form.addRow("Canto (h):", self.spin_canto)
        form.addRow("Hormigón:", self.combo_mat)

        layout.addWidget(group)
        layout.addStretch()

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        self._on_tipo_changed()

    def _on_tipo_changed(self) -> None:
        is_zuncho = self.combo_tipo.currentIndex() == 1
        self.spin_canto.setEnabled(not is_zuncho)
        if is_zuncho:
            self.spin_canto.setValue(0.0)

    def get_props(self) -> dict[str, Any]:
        return {
            "ancho": self.spin_ancho.value(),
            "canto": self.spin_canto.value(),
            "material": self.combo_mat.currentText(),
            "tipo": "ZUNCHO_BORDE" if self.combo_tipo.currentIndex() == 1 else "RECTANGULAR"
        }
