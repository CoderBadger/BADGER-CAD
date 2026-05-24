"""nivel_manager.py — Dialog for managing floor levels and groups.

Allows:
  - Adding / deleting floors.
  - Editing floor name and elevation inline (double-click).
  - Assigning / changing a floor's group via an inline QComboBox.
  - Adding new groups.

All changes are committed to the Project model on 'Aplicar'.
"""
from __future__ import annotations
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QDoubleSpinBox, QLineEdit,
    QDialogButtonBox, QLabel, QGroupBox, QWidget,
    QAbstractItemView, QMessageBox, QComboBox,
    QStyledItemDelegate, QApplication,
)
from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtGui import QColor

from badgercad.core.project import Project
from badgercad.core.elements.nivel import Nivel
from badgercad.core.elements.grupo import Grupo

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
QPushButton#btn_add_grupo{border-color:#D9A84A;color:#D9A84A;}
QPushButton#btn_add_grupo:hover{background:#D9A84A;color:#000;}
QComboBox{background:#252932;border:1px solid #2E3A4E;border-radius:4px;
  color:#E0E6F0;padding:2px 6px;font-size:12px;}
QComboBox:focus{border-color:#4A90D9;}
QComboBox QAbstractItemView{background:#252932;color:#E0E6F0;
  selection-background-color:#1D3A5F;}
QDialogButtonBox QPushButton{background:#2E3A4E;color:#E0E6F0;
  border:1px solid #4A90D9;border-radius:4px;padding:6px 20px;font-weight:600;}
QDialogButtonBox QPushButton:hover{background:#4A90D9;color:#fff;}
"""

# Column indices
COL_NOMBRE = 0
COL_COTA   = 1
COL_GRUPO  = 2


class _GrupoDelegate(QStyledItemDelegate):
    """Inline QComboBox editor for the Grupo column."""

    def __init__(self, project: Project, parent=None) -> None:
        super().__init__(parent)
        self.project = project

    def createEditor(self, parent, option, index: QModelIndex):  # noqa: N802
        combo = QComboBox(parent)
        combo.setStyleSheet(
            "background:#252932;border:1px solid #4A90D9;"
            "color:#E0E6F0;font-size:12px;"
        )
        combo.addItem("— Sin grupo —", userData=None)
        for g in self.project.grupos:
            combo.addItem(g.nombre, userData=g.id)
        return combo

    def setEditorData(self, editor: QComboBox, index: QModelIndex) -> None:  # noqa: N802
        current_grupo_id = index.data(Qt.ItemDataRole.UserRole + 1)
        for i in range(editor.count()):
            if editor.itemData(i) == current_grupo_id:
                editor.setCurrentIndex(i)
                return
        editor.setCurrentIndex(0)

    def setModelData(self, editor: QComboBox, model, index: QModelIndex) -> None:  # noqa: N802
        grupo_id   = editor.currentData()
        grupo_name = editor.currentText()
        model.setData(index, grupo_name, Qt.ItemDataRole.DisplayRole)
        model.setData(index, grupo_id,   Qt.ItemDataRole.UserRole + 1)

    def updateEditorGeometry(self, editor, option, index) -> None:  # noqa: N802
        editor.setGeometry(option.rect)


class NivelManagerDialog(QDialog):
    """Manage floors and groups — add, rename, set elevation, assign group."""

    def __init__(
        self,
        project: Project,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Gestión de Plantas y Grupos")
        self.resize(600, 540)
        self.setStyleSheet(_STYLE)
        self._build_ui()
        self._refresh_table()

    # ------------------------------------------------------------------ UI
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

        # ── Floors table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Nombre", "Cota (m)", "Grupo"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.SelectedClicked
        )
        # Install custom delegate for the Grupo column
        self._grupo_delegate = _GrupoDelegate(self.project, self._table)
        self._table.setItemDelegateForColumn(COL_GRUPO, self._grupo_delegate)
        root.addWidget(self._table)

        # ── Add / Delete floor buttons
        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("+ Añadir Planta")
        self._btn_add.setObjectName("btn_add")
        self._btn_del = QPushButton("✕ Eliminar Planta")
        self._btn_del.setObjectName("btn_del")
        self._btn_add.clicked.connect(self._add_nivel)
        self._btn_del.clicked.connect(self._delete_nivel)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_del)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # ── Add group mini-form
        grp_box = QGroupBox("Nuevo Grupo")
        grp_layout = QHBoxLayout(grp_box)
        grp_layout.setContentsMargins(8, 12, 8, 8)
        grp_layout.setSpacing(8)

        self._new_grupo_name = QLineEdit()
        self._new_grupo_name.setPlaceholderText("Nombre del grupo (ej. Tipo A)")
        self._btn_add_grupo = QPushButton("+ Crear Grupo")
        self._btn_add_grupo.setObjectName("btn_add_grupo")
        self._btn_add_grupo.clicked.connect(self._add_grupo)
        grp_layout.addWidget(QLabel("Nombre:"))
        grp_layout.addWidget(self._new_grupo_name, stretch=1)
        grp_layout.addWidget(self._btn_add_grupo)
        root.addWidget(grp_box)

        note = QLabel(
            "ⓘ  Doble clic en Nombre o Cota para editar.  "
            "Doble clic en Grupo para asignar a un grupo existente.  "
            "Las plantas sin grupo aparecen en naranja."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#5A8FA8;font-size:10px;")
        root.addWidget(note)

        # ── OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aplicar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------ table helpers
    def _refresh_table(self) -> None:
        """Re-populate the table from the project model."""
        self._table.setRowCount(0)
        for nivel in self.project.niveles_ordenados():
            row = self._table.rowCount()
            self._table.insertRow(row)

            # Col 0 — Nombre (editable)
            name_item = QTableWidgetItem(nivel.nombre)
            name_item.setData(Qt.ItemDataRole.UserRole, nivel.id)
            self._table.setItem(row, COL_NOMBRE, name_item)

            # Col 1 — Cota (editable)
            cota_item = QTableWidgetItem(f"{nivel.cota:.2f}")
            cota_item.setData(Qt.ItemDataRole.UserRole, nivel.id)
            self._table.setItem(row, COL_COTA, cota_item)

            # Col 2 — Grupo (editable via delegate combo)
            grupo = self.project.get_grupo_de_nivel(nivel.id)
            grupo_name = grupo.nombre if grupo else "— Sin grupo —"
            grupo_id   = grupo.id     if grupo else None

            g_item = QTableWidgetItem(grupo_name)
            # nivel.id stored in UserRole so we can look it up in _apply()
            g_item.setData(Qt.ItemDataRole.UserRole,     nivel.id)
            # selected grupo_id stored in UserRole+1 for the delegate
            g_item.setData(Qt.ItemDataRole.UserRole + 1, grupo_id)

            if grupo is None:
                g_item.setForeground(QColor("#D9A84A"))  # orange = unassigned

            self._table.setItem(row, COL_GRUPO, g_item)

    def _refresh_delegate(self) -> None:
        """Recreate the delegate so new groups appear in its combo list."""
        self._grupo_delegate = _GrupoDelegate(self.project, self._table)
        self._table.setItemDelegateForColumn(COL_GRUPO, self._grupo_delegate)

    # ------------------------------------------------------------------ actions
    def _add_nivel(self) -> None:
        existing_cotas = [n.cota for n in self.project.niveles]
        new_cota  = max(existing_cotas) + 3.0 if existing_cotas else 3.0
        new_nivel = Nivel(f"Planta {len(self.project.niveles)}", new_cota)
        self.project.add_nivel(new_nivel)

        # Auto-assign to the last group if one exists
        if self.project.grupos:
            last_grupo = self.project.grupos[-1]
            last_grupo.nivel_ids.append(new_nivel.id)

        self._refresh_table()

    def _delete_nivel(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        nivel_id = self._table.item(row, COL_NOMBRE).data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Eliminar planta",
            "¿Eliminar esta planta? Los pilares y losas asociados pueden quedar huérfanos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.project.remove_nivel(nivel_id)
            self._refresh_table()

    def _add_grupo(self) -> None:
        nombre = self._new_grupo_name.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Nombre requerido", "Escribe un nombre para el grupo.")
            return
        # Check for duplicate name
        existing = [g.nombre.lower() for g in self.project.grupos]
        if nombre.lower() in existing:
            QMessageBox.warning(self, "Nombre duplicado",
                                f"Ya existe un grupo llamado '{nombre}'.")
            return
        nuevo = Grupo(nombre)
        self.project.add_grupo(nuevo)
        self._new_grupo_name.clear()
        self._refresh_delegate()  # update delegate so new group appears in combos
        self._refresh_table()

    # ------------------------------------------------------------------ apply
    def _apply(self) -> None:
        """Write all table edits back to the project model."""
        # Step 1: Update nivel names and cotas
        for row in range(self._table.rowCount()):
            nivel_id = self._table.item(row, COL_NOMBRE).data(Qt.ItemDataRole.UserRole)
            nivel    = self.project.get_nivel_by_id(nivel_id)
            if nivel is None:
                continue
            new_name = self._table.item(row, COL_NOMBRE).text().strip()
            if new_name:
                nivel.nombre = new_name
            try:
                nivel.cota = float(self._table.item(row, COL_COTA).text())
            except ValueError:
                pass

        # Step 2: Rebuild group memberships from the Grupo column
        # First, clear all current nivel_ids across all groups
        for g in self.project.grupos:
            g.nivel_ids.clear()

        # Then re-assign according to the table
        for row in range(self._table.rowCount()):
            nivel_id = self._table.item(row, COL_NOMBRE).data(Qt.ItemDataRole.UserRole)
            grupo_id = self._table.item(row, COL_GRUPO).data(Qt.ItemDataRole.UserRole + 1)
            if grupo_id is not None:
                grupo = self.project.get_grupo_by_id(grupo_id)
                if grupo and nivel_id not in grupo.nivel_ids:
                    grupo.nivel_ids.append(nivel_id)

        # Step 3: Re-sort and emit
        self.project.niveles.sort(key=lambda n: n.cota)
        self.project.niveles_changed.emit()
        self.accept()
