"""nivel_panel.py — Left-side dock panel showing the floor/group hierarchy."""
from __future__ import annotations
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel,
    QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor

from badgercad.core.project import Project
from badgercad.core.elements.nivel import Nivel
from badgercad.ui.utils.icon_manager import IconManager

_PANEL_STYLE = """
QWidget#nivel_panel {
    background: #161C26;
    border-right: 1px solid #2E3A4E;
}
QLabel#panel_title {
    color: #8090A8;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 8px 12px 4px 12px;
}
QListWidget {
    background: transparent;
    border: none;
    color: #C0CDE0;
    font-size: 12px;
    outline: 0;
}
QListWidget::item {
    padding: 5px 10px;
    border-radius: 4px;
    margin: 1px 6px;
}
QListWidget::item:selected, QListWidget::item:hover {
    background: #1D2A3A;
    color: #FFFFFF;
}
QListWidget::item[active="true"] {
    background: #1D3A5F;
    color: #4A90D9;
    font-weight: 700;
}
QPushButton#nav_btn {
    background: #1E2330;
    border: 1px solid #2E3A4E;
    border-radius: 4px;
    color: #C0CDE0;
    font-size: 11px;
    padding: 4px 8px;
    min-width: 28px;
}
QPushButton#nav_btn:hover { background: #2E3A4E; color: #FFFFFF; }
QPushButton#nav_btn:disabled { color: #404A5A; border-color: #2A3040; }
QFrame#separator { background: #2E3A4E; max-height: 1px; }
"""

_GROUP_ICON  = "📦"
_LEVEL_ICON  = "▸"
_ACTIVE_ICON = "►"


class NivelPanel(QWidget):
    """Vertical panel listing Grupos and their Niveles.

    The active level is highlighted; clicking any level makes it active.

    Signals:
        nivel_selected(nivel_id): Emitted when the user clicks a level.
    """

    nivel_selected = pyqtSignal(str)  # nivel id

    def __init__(self, project: Project, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("nivel_panel")
        self.setFixedWidth(190)
        self.project = project
        self._build_ui()
        self._refresh()

        # Auto-refresh when model changes
        self.project.niveles_changed.connect(self._refresh)
        self.project.nivel_activo_changed.connect(self._refresh)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.setStyleSheet(_PANEL_STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title
        title = QLabel("PLANTAS")
        title.setObjectName("panel_title")
        root.addWidget(title)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # List
        self._list = QListWidget()
        self._list.setIconSize(QSize(16, 16))
        self._list.itemClicked.connect(self._on_item_clicked)
        root.addWidget(self._list)

        sep2 = QFrame()
        sep2.setObjectName("separator")
        sep2.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep2)

        # Up / Down navigation buttons
        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(8, 6, 8, 6)
        nav_row.setSpacing(6)

        self._btn_up = QPushButton("Subir")
        self._btn_up.setIcon(IconManager.get_icon("nav_up", "▲"))
        self._btn_up.setObjectName("nav_btn")
        self._btn_dn = QPushButton("Bajar")
        self._btn_dn.setIcon(IconManager.get_icon("nav_down", "▼"))
        self._btn_dn.setObjectName("nav_btn")
        self._btn_up.clicked.connect(self._go_up)
        self._btn_dn.clicked.connect(self._go_down)
        nav_row.addWidget(self._btn_up)
        nav_row.addWidget(self._btn_dn)
        root.addLayout(nav_row)

    # ------------------------------------------------------------------ data
    def _refresh(self) -> None:
        self._list.clear()
        activo_id = (
            self.project.nivel_activo.id
            if self.project.nivel_activo else None
        )

        for grupo in self.project.grupos:
            # Group header
            g_item = QListWidgetItem(f" {grupo.nombre}")
            g_item.setIcon(IconManager.get_icon("group", _GROUP_ICON))
            g_item.setFlags(Qt.ItemFlag.NoItemFlags)
            g_item.setForeground(QColor("#5A8FA8"))
            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            g_item.setFont(font)
            self._list.addItem(g_item)

            # Floors inside this group (bottom-up)
            group_niveles = [
                self.project.get_nivel_by_id(nid)
                for nid in grupo.nivel_ids
            ]
            group_niveles = sorted(
                [n for n in group_niveles if n is not None],
                key=lambda n: n.cota, reverse=True,
            )
            for nivel in group_niveles:
                is_active = nivel.id == activo_id
                
                icon_name = "level_active" if is_active else "level"
                fallback_char = _ACTIVE_ICON if is_active else _LEVEL_ICON
                
                label = f" {nivel.nombre}  ({nivel.cota:+.1f} m)"
                item  = QListWidgetItem(label)
                item.setIcon(IconManager.get_icon(icon_name, fallback_char))
                
                item.setData(Qt.ItemDataRole.UserRole, nivel.id)
                if is_active:
                    item.setForeground(QColor("#4A90D9"))
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)
                self._list.addItem(item)

        self._update_nav_buttons()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        nivel_id = item.data(Qt.ItemDataRole.UserRole)
        if nivel_id:
            nivel = self.project.get_nivel_by_id(nivel_id)
            if nivel:
                self.project.nivel_activo = nivel
                self.nivel_selected.emit(nivel_id)

    # ------------------------------------------------------------------ navigation
    def _active_index_in_sorted(self) -> int:
        sorted_lvls = self.project.niveles_ordenados()
        activo = self.project.nivel_activo
        if activo is None:
            return -1
        try:
            return sorted_lvls.index(activo)
        except ValueError:
            return -1

    def _go_up(self) -> None:
        sorted_lvls = self.project.niveles_ordenados()
        idx = self._active_index_in_sorted()
        if idx < len(sorted_lvls) - 1:
            self.project.nivel_activo = sorted_lvls[idx + 1]

    def _go_down(self) -> None:
        sorted_lvls = self.project.niveles_ordenados()
        idx = self._active_index_in_sorted()
        if idx > 0:
            self.project.nivel_activo = sorted_lvls[idx - 1]

    def _update_nav_buttons(self) -> None:
        sorted_lvls = self.project.niveles_ordenados()
        idx = self._active_index_in_sorted()
        self._btn_up.setEnabled(idx < len(sorted_lvls) - 1)
        self._btn_dn.setEnabled(idx > 0)
