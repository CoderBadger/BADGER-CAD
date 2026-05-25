"""ribbon.py — Professional CAD ribbon toolbar (QTabWidget + QToolButton + QSS)."""
from __future__ import annotations
from typing import Optional, Callable

from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QHBoxLayout, QVBoxLayout,
    QToolButton, QLabel, QFrame, QSizePolicy,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon

RIBBON_QSS = """
/* ── Ribbon container ── */
QWidget#ribbon_root {
    background: #1A1E2A;
    border-bottom: 1px solid #2A3444;
}

/* ── Tab bar ── */
QTabWidget#ribbon_tabs { background: transparent; border: none; }
QTabWidget#ribbon_tabs::pane { border: none; background: #1E2330; }

QTabBar { background: #1A1E2A; }
QTabBar::tab {
    background: transparent;
    color: #6A7A90;
    padding: 6px 18px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    border: none;
    border-bottom: 2px solid transparent;
    min-width: 70px;
}
QTabBar::tab:selected {
    color: #4A90D9;
    border-bottom: 2px solid #4A90D9;
    background: transparent;
}
QTabBar::tab:hover:!selected { color: #C0CDE0; }

/* ── Tool buttons ── */
QToolButton {
    background: transparent;
    color: #A0B0C8;
    border: none;
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 10px;
    min-width: 54px;
    max-width: 80px;
    text-align: center;
}
QToolButton:hover  { background: #2A3648; color: #E0EAF8; }
QToolButton:checked {
    background: #1D3A5F;
    color: #4A90D9;
    border: 1px solid #4A90D9;
}
QToolButton:disabled { color: #3A4A5A; }

/* ── Group separators ── */
QFrame#grp_sep {
    background: #2A3444;
    max-width: 1px;
    margin: 6px 4px;
}

/* ── Group labels ── */
QLabel#grp_label {
    color: #4A5A6A;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    padding: 0px 4px;
}

/* ── Combo (grid spacing) ── */
QComboBox {
    background: #252932;
    border: 1px solid #2E3A4E;
    border-radius: 4px;
    color: #C0CDE0;
    padding: 2px 6px;
    font-size: 10px;
    min-width: 70px;
}
QComboBox:focus { border-color: #4A90D9; }
QComboBox QAbstractItemView {
    background: #252932;
    color: #C0CDE0;
    selection-background-color: #1D3A5F;
}
"""


def _separator() -> QFrame:
    sep = QFrame()
    sep.setObjectName("grp_sep")
    sep.setFrameShape(QFrame.Shape.VLine)
    return sep


def _grp_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("grp_label")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def _tool_btn(icon_txt: str, label: str,
              tooltip: str = "",
              checkable: bool = False) -> QToolButton:
    btn = QToolButton()
    btn.setText(f"{icon_txt}\n{label}")
    btn.setToolTip(tooltip)
    btn.setCheckable(checkable)
    btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
    btn.setIconSize(QSize(24, 24))
    btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
    return btn


def _group_widget(label: str, buttons: list[QWidget]) -> QWidget:
    """Vertical group: label at bottom, buttons in a row."""
    frame = QWidget()
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(4, 2, 4, 2)
    outer.setSpacing(2)

    btn_row = QHBoxLayout()
    btn_row.setSpacing(2)
    btn_row.setContentsMargins(0, 0, 0, 0)
    for w in buttons:
        btn_row.addWidget(w)
    outer.addLayout(btn_row)
    outer.addWidget(_grp_label(label))
    return frame


class Ribbon(QWidget):
    """Professional CAD ribbon — tabs → groups → tool buttons.

    Signals:
        tool_pilar_requested:  User wants to start placing columns.
        tool_losa_requested:   User wants to start drawing a slab.
        vista_3d_requested:    User wants to open the 3D viewer.
        gestionar_plantas:     User wants to open NivelManagerDialog.
        datos_generales:       User wants to open DatosGeneralesDialog.
        grid_spacing_changed:  User changed the grid snap spacing.
        nuevo_proyecto:        New project requested.
    """

    tool_pilar_requested        = pyqtSignal()
    tool_borrar_pilar_requested = pyqtSignal()
    tool_viga_requested         = pyqtSignal()
    tool_losa_requested         = pyqtSignal()
    vista_3d_requested          = pyqtSignal()
    gestionar_plantas           = pyqtSignal()
    datos_generales             = pyqtSignal()
    grid_spacing_changed        = pyqtSignal(float)
    nuevo_proyecto              = pyqtSignal()
    esc_tool                    = pyqtSignal()
    calcular_requested          = pyqtSignal()
    ver_deformada_requested     = pyqtSignal()
    ver_esfuerzos_mxx_requested = pyqtSignal()
    ver_esfuerzos_myy_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("ribbon_root")
        self.setFixedHeight(88)
        self.setStyleSheet(RIBBON_QSS)
        self._build_ui()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("ribbon_tabs")
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        self._tabs.tabBar().setDrawBase(False)
        root.addWidget(self._tabs)

        self._tabs.addTab(self._tab_inicio(),  "Inicio")
        self._tabs.addTab(self._tab_pilares(), "Pilares")
        self._tabs.addTab(self._tab_losas(),   "Losas")
        self._tabs.addTab(self._tab_vigas(),   "Vigas")
        self._tabs.addTab(self._tab_cargas(),  "Cargas")
        self._tabs.addTab(self._tab_calcular(),"Calcular")
        
        # Resultados tab initially disabled
        self._tab_resultados_widget = self._tab_resultados()
        self._tabs.addTab(self._tab_resultados_widget, "Resultados")
        self._tabs.setTabEnabled(self._tabs.count() - 1, False)

    # ------------------------------------------------------------------ tabs
    def _tab_inicio(self) -> QWidget:
        w   = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Project group
        self._btn_nuevo = _tool_btn("📄", "Nuevo", "Crear nuevo proyecto")
        self._btn_nuevo.clicked.connect(self.nuevo_proyecto)

        self._btn_abrir = _tool_btn("📂", "Abrir", "Abrir proyecto (.bdr)")
        self._btn_guardar = _tool_btn("💾", "Guardar", "Guardar proyecto")

        lay.addWidget(_group_widget("Proyecto", [self._btn_nuevo, self._btn_abrir, self._btn_guardar]))
        lay.addWidget(_separator())

        # View group
        self._btn_3d = _tool_btn("🏗", "Vista 3D", "Abrir visor 3D del edificio")
        self._btn_3d.clicked.connect(self.vista_3d_requested)

        self._btn_plantas = _tool_btn("📐", "Plantas", "Gestionar plantas y grupos")
        self._btn_plantas.clicked.connect(self.gestionar_plantas)

        lay.addWidget(_group_widget("Vista", [self._btn_3d, self._btn_plantas]))
        lay.addWidget(_separator())

        # Settings group
        self._btn_datos = _tool_btn("⚙", "Datos Gen.", "Datos generales del proyecto")
        self._btn_datos.clicked.connect(self.datos_generales)

        # Grid spacing combo
        grid_widget = QWidget()
        glay = QVBoxLayout(grid_widget)
        glay.setContentsMargins(4, 2, 4, 2)
        glay.setSpacing(2)
        snap_row = QHBoxLayout()
        snap_lbl = QLabel("Snap:")
        snap_lbl.setStyleSheet("color:#8090A8;font-size:9px;")
        self._grid_combo = QComboBox()
        self._grid_combo.addItems(["0.25 m", "0.50 m", "1.00 m", "2.00 m"])
        self._grid_combo.setCurrentIndex(2)
        self._grid_combo.currentIndexChanged.connect(self._on_grid_changed)
        snap_row.addWidget(snap_lbl)
        snap_row.addWidget(self._grid_combo)
        glay.addLayout(snap_row)
        glay.addWidget(_grp_label("Grilla"))

        lay.addWidget(_group_widget("Configuración", [self._btn_datos]))
        lay.addWidget(grid_widget)
        lay.addStretch()
        return w

    def _tab_pilares(self) -> QWidget:
        w   = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._btn_pilar = _tool_btn("⬛", "Colocar\nPilar",
                                    "Colocar pilares de hormigón (CYPECAD flow)",
                                    checkable=True)
        self._btn_pilar.clicked.connect(self._on_pilar_clicked)

        self._btn_borrar_pilar = _tool_btn("🗑", "Borrar\nPilar",
                                           "Borrar pilar existente (clic sobre él)",
                                           checkable=True)
        self._btn_borrar_pilar.clicked.connect(self._on_borrar_pilar_clicked)

        self._btn_pantalla = _tool_btn("🧱", "Pantalla\n/Muro",
                                       "Muro de corte o pantalla [Hito 2]")
        self._btn_pantalla.setEnabled(False)

        lay.addWidget(_group_widget("Soportes Verticales",
                                    [self._btn_pilar, self._btn_pantalla]))
        lay.addWidget(_separator())
        lay.addWidget(_group_widget("Edición", [self._btn_borrar_pilar]))
        lay.addWidget(_separator())

        self._btn_esc_p = _tool_btn("✕", "ESC / Fin",
                                    "Terminar herramienta activa")
        self._btn_esc_p.clicked.connect(self.esc_tool)
        lay.addWidget(_group_widget("Control", [self._btn_esc_p]))
        lay.addStretch()
        return w

    def _tab_losas(self) -> QWidget:
        w   = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._btn_losa = _tool_btn("▭", "Inyectar\nLosa",
                                   "Crear losa haciendo clic en un paño cerrado",
                                   checkable=True)
        self._btn_losa.clicked.connect(self._on_losa_clicked)
        self._btn_losa.setEnabled(True)

        note = QLabel("  ⓘ  Haga clic dentro de recintos cerrados por vigas.")
        note.setStyleSheet("color:#4A5A6A;font-size:11px;")

        lay.addWidget(_group_widget("Losas", [self._btn_losa]))
        lay.addWidget(note)
        lay.addStretch()
        return w

    def _tab_vigas(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self._btn_viga = _tool_btn("📏", "Dibujar\nViga",
                                   "Trazado continuo de vigas (se ancla a pilares)",
                                   checkable=True)
        self._btn_viga.clicked.connect(self._on_viga_clicked)
        
        lay.addWidget(_group_widget("Vigas", [self._btn_viga]))
        
        self._btn_esc_v = _tool_btn("✕", "ESC / Fin",
                                    "Terminar herramienta activa")
        self._btn_esc_v.clicked.connect(self.esc_tool)
        lay.addWidget(_group_widget("Control", [self._btn_esc_v]))
        
        lay.addStretch()
        return w

    def _tab_cargas(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 0, 12, 0)
        lbl = QLabel("⚡  Módulo de Cargas — disponible en Hito 2")
        lbl.setStyleSheet("color:#4A5A6A;font-size:12px;")
        lay.addWidget(lbl)
        return w

    def _tab_calcular(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self._btn_calcular = _tool_btn("▶", "Calcular", "Ejecutar análisis MEF (Gravedad)")
        self._btn_calcular.clicked.connect(self.calcular_requested)
        lay.addWidget(_group_widget("Solver", [self._btn_calcular]))
        
        lay.addStretch()
        return w

    def _tab_resultados(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self._btn_deformada = _tool_btn("🌊", "Ver\nDeformada", "Mapa de Desplazamientos Z")
        self._btn_deformada.clicked.connect(self.ver_deformada_requested)
        
        self._btn_mxx = _tool_btn("💥", "Esfuerzos\nMxx", "Momentos Flectores X")
        self._btn_mxx.clicked.connect(self.ver_esfuerzos_mxx_requested)
        
        self._btn_myy = _tool_btn("💥", "Esfuerzos\nMyy", "Momentos Flectores Y")
        self._btn_myy.clicked.connect(self.ver_esfuerzos_myy_requested)
        
        lay.addWidget(_group_widget("Visualización 3D", [self._btn_deformada, self._btn_mxx, self._btn_myy]))
        lay.addStretch()
        return w

    # ------------------------------------------------------------------ handlers
    def _on_pilar_clicked(self) -> None:
        self._btn_losa.setChecked(False)
        self._btn_borrar_pilar.setChecked(False)
        self._btn_viga.setChecked(False)
        if self._btn_pilar.isChecked():
            self.tool_pilar_requested.emit()
        else:
            self.esc_tool.emit()

    def _on_borrar_pilar_clicked(self) -> None:
        self._btn_pilar.setChecked(False)
        self._btn_losa.setChecked(False)
        self._btn_viga.setChecked(False)
        if self._btn_borrar_pilar.isChecked():
            self.tool_borrar_pilar_requested.emit()
        else:
            self.esc_tool.emit()

    def _on_viga_clicked(self) -> None:
        self._btn_pilar.setChecked(False)
        self._btn_borrar_pilar.setChecked(False)
        self._btn_losa.setChecked(False)
        if self._btn_viga.isChecked():
            self.tool_viga_requested.emit()
        else:
            self.esc_tool.emit()

    def _on_losa_clicked(self) -> None:
        self._btn_pilar.setChecked(False)
        self._btn_borrar_pilar.setChecked(False)
        self._btn_viga.setChecked(False)
        if self._btn_losa.isChecked():
            self.tool_losa_requested.emit()
        else:
            self.esc_tool.emit()

    def _on_grid_changed(self, _idx: int) -> None:
        txt = self._grid_combo.currentText()   # e.g. "0.50 m"
        val = float(txt.split()[0])
        self.grid_spacing_changed.emit(val)

    # ------------------------------------------------------------------ API
    def set_resultados_enabled(self, enabled: bool) -> None:
        idx = self._tabs.count() - 1
        self._tabs.setTabEnabled(idx, enabled)
        if enabled:
            self._tabs.setCurrentIndex(idx)

    # ------------------------------------------------------------------ public
    def uncheck_all_tools(self) -> None:
        """Called when ESC or deactivate_tool fires."""
        self._btn_pilar.setChecked(False)
        self._btn_losa.setChecked(False)
        self._btn_borrar_pilar.setChecked(False)
        self._btn_viga.setChecked(False)
