from PyQt6.QtWidgets import QMainWindow, QToolBar, QPushButton, QStatusBar, QComboBox, QLabel, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from src.cad.state_manager import StateManager, CadMode
from src.cad.tools import CadEngine
from src.gui.viewport import Viewport3D
from src.model.elements import Grilla
from src.model.levels import Building

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BADGER CAD - Hito 1.5 (Flujo CYPECAD)")
        self.resize(1024, 768)
        
        self.building = Building()
        self.state_manager = StateManager()
        self.cad_engine = CadEngine(self.building)
        
        self.viewport = Viewport3D(self.cad_engine, self.state_manager, self.building, self)
        self.setCentralWidget(self.viewport)
        
        self.setup_toolbar()
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Listo. Modo: SELECCION")
        
        self.state_manager.add_observer(self.update_status_bar)
        
        self.crear_grilla_test()
        
    def setup_toolbar(self):
        toolbar = QToolBar("Herramientas CAD")
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
        
        # Selector de Planta
        label = QLabel(" Planta Activa:")
        label.setStyleSheet("color: white; font-weight: bold; margin-top: 10px;")
        toolbar.addWidget(label)
        
        self.combo_planta = QComboBox()
        for i, nivel in enumerate(self.building.levels):
            self.combo_planta.addItem(f"{nivel.name} (Z={nivel.elevation}m)")
        self.combo_planta.setCurrentIndex(self.building.active_level_index)
        self.combo_planta.currentIndexChanged.connect(self.on_planta_changed)
        toolbar.addWidget(self.combo_planta)
        
        toolbar.addSeparator()
        
        btn_sel = QPushButton("Selección")
        btn_sel.clicked.connect(lambda: self.state_manager.set_mode(CadMode.SELECCION))
        toolbar.addWidget(btn_sel)
        
        btn_pilar = QPushButton("Dibujar Pilar")
        btn_pilar.clicked.connect(lambda: self.state_manager.set_mode(CadMode.DIBUJAR_PILAR))
        toolbar.addWidget(btn_pilar)
        
        btn_viga = QPushButton("Dibujar Viga")
        btn_viga.clicked.connect(lambda: self.state_manager.set_mode(CadMode.DIBUJAR_VIGA))
        toolbar.addWidget(btn_viga)
        
        btn_losa = QPushButton("Asignar Losa")
        btn_losa.clicked.connect(lambda: self.state_manager.set_mode(CadMode.ASIGNAR_LOSA))
        toolbar.addWidget(btn_losa)
        
        toolbar.addSeparator()
        
        self.btn_modo_vista = QPushButton("Cambiar a Vista 3D")
        self.btn_modo_vista.setCheckable(True)
        self.btn_modo_vista.setStyleSheet("background-color: #34495e; color: white;")
        self.btn_modo_vista.clicked.connect(self.on_toggle_vista)
        toolbar.addWidget(self.btn_modo_vista)
        
    def on_planta_changed(self, index):
        self.building.set_active_level(index)
        self.viewport.refresh_scene()
        self.statusBar.showMessage(f"Planta cambiada a: {self.building.get_active_level().name}")
        
    def on_toggle_vista(self, checked):
        if checked:
            self.btn_modo_vista.setText("Volver a Planta (2D)")
            self.btn_modo_vista.setStyleSheet("background-color: #27ae60; color: white;")
            self.viewport.set_3d_mode()
            self.statusBar.showMessage("Vista 3D activada (Solo visualización)")
        else:
            self.btn_modo_vista.setText("Cambiar a Vista 3D")
            self.btn_modo_vista.setStyleSheet("background-color: #34495e; color: white;")
            self.viewport.set_2d_mode()
            self.statusBar.showMessage("Vista de Planta 2D activada (Dibujo)")
            
    def crear_grilla_test(self):
        x_lines = list(range(0, 21, 5))
        y_lines = list(range(0, 21, 5))
        z_act = self.building.get_active_level().elevation
        grilla = Grilla(x_lines, y_lines, z_act)
        self.cad_engine.set_grilla(grilla)
        self.viewport.refresh_scene()
        
    def update_status_bar(self, mode):
        if not self.viewport.is_2d_mode:
            self.statusBar.showMessage(f"Modo actual: {mode.name} (Desactivado en 3D)")
        else:
            self.statusBar.showMessage(f"Modo actual: {mode.name}")
