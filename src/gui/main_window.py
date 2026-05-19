from PyQt6.QtWidgets import QMainWindow, QToolBar, QPushButton, QStatusBar
from PyQt6.QtCore import Qt
from src.cad.state_manager import StateManager, CadMode
from src.cad.tools import CadEngine
from src.gui.viewport import Viewport3D
from src.model.elements import Grilla

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BADGER CAD - Hito 1")
        self.resize(1024, 768)
        
        self.state_manager = StateManager()
        self.cad_engine = CadEngine()
        
        self.viewport = Viewport3D(self.cad_engine, self.state_manager, self)
        self.setCentralWidget(self.viewport)
        
        self.setup_toolbar()
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Listo. Modo: SELECCION")
        
        self.state_manager.add_observer(self.update_status_bar)
        
    def setup_toolbar(self):
        toolbar = QToolBar("Herramientas CAD")
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
        
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
        
        btn_grilla = QPushButton("Mostrar Grilla")
        btn_grilla.clicked.connect(self.crear_grilla_test)
        toolbar.addWidget(btn_grilla)
        
    def crear_grilla_test(self):
        # Grilla de 20x20 metros, espaciada cada 5 metros
        x_lines = list(range(0, 21, 5))
        y_lines = list(range(0, 21, 5))
        grilla = Grilla(x_lines, y_lines)
        self.cad_engine.set_grilla(grilla)
        self.viewport.render_grilla()
        self.statusBar.showMessage("Grilla de prueba creada")
        
    def update_status_bar(self, mode):
        self.statusBar.showMessage(f"Modo actual: {mode.name}")
