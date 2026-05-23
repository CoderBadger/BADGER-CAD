"""nivel_manager.py — Dialog for managing floor levels and groups."""
from __future__ import annotations
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QDoubleSpinBox, QLineEdit,
    QDialogButtonBox, QLabel, QGroupBox, QWidget,
    QAbstractItemView, QMessageBox,
)
from PyQt6.QtCore import Qt

from badgercad.core.project import Project
from badgercad.core.elements.nivel import Nivel

_STYLE = """
QDialog{background:#1E2330;color:#E0E6F0;}
QTableWidget{background:#252932;border:1px solid #2E3A4E;
  color:#E0E6F0;gridline-color:#2E3A4E;selection-background-color:#1D3A5F;}
QTableWidget::item{padding:4px;}
QHeaderView::section{background:#1A2030;color:#8090A8;
  border:none;padding:4px;font-size:10px;font-weight:600;}
QGroupBox{border:1px solid #2E3A4E;border-radius:6px;margin-top:8px;
  padding-top:8px;color:#8090A8;font-size:10px;font-weight:600;}
QGroupBox::title{subcontrol-origin:margin;left:10px;}
QLabel{color:#C0CDE0;font-size:12px;}
QLineEdit,QDoubleSpinBox{background:#252932;border:1px solid #2E3A4E;
  border-radius:4px;color:#E0E6F0;padding:4px 8px;font-size:12px;}
QLineEdit:focus,QDoubleSpinBox:focus{border-color:#4A90D9;}
QPushButton{background:#2E3A4E;color:#E0E6F0;border:1px solid #3A4A60;
  border-radius:4px;padding:5px 14px;font-size:11px;}
QPushButton:hover{background:#3A4A60;}
QPushButton#btn_add{border-color:#4AD97A;color:#4AD97A;}
QPushButton#btn_add:hover{background:#4AD97A;color:#000;}
QPushButton#btn_del{border-color:#D97A4A;color:#D97A4A;}
QPushButton#btn_del:hover{background:#D97A4A;color:#fff;}
QDialogButtonBox QPushButton{background:#2E3A4E;color:#E0E6F0;
  border:1px solid #4A90D9;border-radius:4px;padding:6px 20px;font-weight:600;}
QDialogButtonBox QPushButton:hover{background:#4A90D9;color:#fff;}
"""


class NivelManagerDialog(QDialog):
    """Manage floors and groups — add, rename, set elevation."""

    def __init__(
        self,
        project: Project,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Gestión de Plantas y Grupos")
        self.resize(560, 480)
        self.setStyleSheet(_STYLE)
        self._build_ui()
        self._refresh_table()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        title = QLabel("🏢  Definición de Plantas Estructurales")
        title.setStyleSheet(
            "font-size:14px;font-weight:700;color:#4A90D9;"
            "padding-bottom:4px;border-bottom:1px solid #2E3A4E;"
        )
        root.addWidget(title)

        # Table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Nombre", "Cota (m)", "Grupo"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.SelectedClicked
        )
        root.addWidget(self._table)

        # Add / Delete buttons
        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("+ Añadir Planta")
        self._btn_add.setObjectName("btn_add")
        self._btn_del = QPushButton("✕ Eliminar")
        self._btn_del.setObjectName("btn_del")
        self._btn_add.clicked.connect(self._add_nivel)
        self._btn_del.clicked.connect(self._delete_nivel)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_del)
        btn_row.addStretch()
        root.addLayout(btn_row)

        note = QLabel(
            "ⓘ  Doble clic en una celda para editarla. "
            "Ordena por cota automáticamente al aceptar."
        )
        note.setStyleSheet("color:#5A8FA8;font-size:10px;")
        root.addWidget(note)

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aplicar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _refresh_table(self) -> None:
        self._table.setRowCount(0)
        for nivel in self.project.niveles_ordenados():
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(nivel.nombre))
            self._table.setItem(row, 1, QTableWidgetItem(f"{nivel.cota:.2f}"))
            grupo = self.project.get_grupo_de_nivel(nivel.id)
            grupo_txt = grupo.nombre if grupo else "—"
            g_item = QTableWidgetItem(grupo_txt)
            g_item.setFlags(g_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            g_item.setData(Qt.ItemDataRole.UserRole, nivel.id)
            self._table.setItem(row, 2, g_item)

    def _add_nivel(self) -> None:
        existing_cotas = [n.cota for n in self.project.niveles]
        new_cota = max(existing_cotas) + 3.0 if existing_cotas else 3.0
        new_nivel = Nivel(f"Planta {len(self.project.niveles)}", new_cota)
        self.project.add_nivel(new_nivel)
        self._refresh_table()

    def _delete_nivel(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        nivel_id = self._table.item(row, 2).data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Eliminar planta",
            "¿Eliminar esta planta? Los pilares y losas asociados pueden quedar huérfanos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.project.remove_nivel(nivel_id)
            self._refresh_table()

    def _apply(self) -> None:
        """Write table edits back to the model."""
        for row in range(self._table.rowCount()):
            nivel_id = self._table.item(row, 2).data(Qt.ItemDataRole.UserRole)
            nivel = self.project.get_nivel_by_id(nivel_id)
            if nivel is None:
                continue
            nivel.nombre = self._table.item(row, 0).text().strip() or nivel.nombre
            try:
                nivel.cota = float(self._table.item(row, 1).text())
            except ValueError:
                pass
        self.project.niveles.sort(key=lambda n: n.cota)
        self.project.niveles_changed.emit()
        self.accept()
