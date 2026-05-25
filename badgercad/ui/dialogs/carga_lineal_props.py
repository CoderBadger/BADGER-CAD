"""carga_lineal_props.py — Dialog for linear loads properties."""
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox,
    QDoubleSpinBox, QComboBox, QGroupBox
)
from badgercad.core.loads import Hipotesis

_STYLE = """
QDialog { background: #1E2330; color: #E0E6F0; }
QGroupBox {
    border: 1px solid #2E3A4E; border-radius: 6px;
    margin-top: 8px; padding-top: 12px;
    color: #8090A8; font-size: 11px; font-weight: 700;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; }
QLabel { color: #C0CDE0; font-size: 12px; }
QDoubleSpinBox {
    background: #252932; border: 1px solid #2E3A4E;
    border-radius: 4px; color: #E0E6F0; padding: 4px 8px; font-size: 12px;
}
QDoubleSpinBox:focus { border-color: #4A90D9; }
QComboBox {
    background: #252932; border: 1px solid #2E3A4E;
    border-radius: 4px; color: #E0E6F0; padding: 4px 8px; font-size: 12px;
}
QComboBox:focus { border-color: #4A90D9; }
QDialogButtonBox QPushButton {
    background: #2E3A4E; color: #E0E6F0;
    border: 1px solid #4A90D9; border-radius: 4px; padding: 6px 20px; font-weight: 600;
}
QDialogButtonBox QPushButton:hover { background: #4A90D9; color: #fff; }
"""

class CargaLinealPropsDialog(QDialog):
    def __init__(self, parent=None, current_props: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Propiedades de Carga Lineal")
        self.resize(300, 200)
        self.setStyleSheet(_STYLE)

        self._magnitud = 5.0
        self._hipotesis = Hipotesis.CM

        if current_props:
            self._magnitud = current_props.get("magnitud", 5.0)
            self._hipotesis = current_props.get("hipotesis", Hipotesis.CM)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        group = QGroupBox("Parámetros de la Carga")
        form = QFormLayout(group)
        form.setContentsMargins(12, 16, 12, 12)
        form.setSpacing(10)

        self.spin_mag = QDoubleSpinBox()
        self.spin_mag.setRange(0.01, 1000.0)
        self.spin_mag.setDecimals(2)
        self.spin_mag.setSingleStep(0.5)
        self.spin_mag.setSuffix(" kN/m")
        self.spin_mag.setValue(self._magnitud)

        self.combo_hip = QComboBox()
        self.combo_hip.addItems([Hipotesis.CM, Hipotesis.CV])
        self.combo_hip.setCurrentText(self._hipotesis)

        form.addRow("Magnitud (q):", self.spin_mag)
        form.addRow("Hipótesis:", self.combo_hip)

        layout.addWidget(group)
        layout.addStretch()

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_props(self) -> dict[str, Any]:
        return {
            "magnitud": self.spin_mag.value(),
            "hipotesis": self.combo_hip.currentText()
        }
