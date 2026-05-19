from PyQt6.QtWidgets import QWidget, QVBoxLayout
from pyvistaqt import QtInteractor
import pyvista as pv
from src.cad.state_manager import CadMode
import numpy as np

class Viewport3D(QWidget):
    def __init__(self, cad_engine, state_manager, parent=None):
        super().__init__(parent)
        self.cad_engine = cad_engine
        self.state_manager = state_manager
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter.interactor)
        
        # Estilo visual moderno y oscuro
        self.plotter.set_background('#2b2b2b')
        self.plotter.show_axes()
        self.plotter.view_xy()
        
        # Rastrear clics del usuario
        self.plotter.track_click_position(callback=self.on_click, side='left')
        
        self.state_manager.add_observer(self.on_mode_changed)
        self.current_viga_start = None
        self.highlight_actors = []
        
    def on_mode_changed(self, mode):
        self.current_viga_start = None
        if mode == CadMode.ASIGNAR_LOSA:
            self.highlight_enclosed_regions()
        else:
            self.clear_highlights()
            
    def render_element(self, element, color, name=None):
        if element and hasattr(element, 'mesh') and element.mesh.n_points > 0:
            self.plotter.add_mesh(element.mesh, color=color, show_edges=True, name=name)
            self.plotter.render()
            
    def on_click(self, pt):
        mode = self.state_manager.current_mode
        if mode == CadMode.DIBUJAR_PILAR:
            pilar = self.cad_engine.add_pilar(pt)
            self.render_element(pilar, '#3498db') # Azul
            
        elif mode == CadMode.DIBUJAR_VIGA:
            snap_pt = self.cad_engine.snap_to_grid(pt)
            if self.current_viga_start is None:
                self.current_viga_start = snap_pt
            else:
                viga = self.cad_engine.add_viga(self.current_viga_start, snap_pt)
                self.render_element(viga, '#e74c3c') # Rojo
                self.current_viga_start = snap_pt
                
        elif mode == CadMode.ASIGNAR_LOSA:
            losa = self.cad_engine.assign_losa(pt)
            if losa:
                self.render_element(losa, '#95a5a6') # Gris
                
    def highlight_enclosed_regions(self):
        polygons = self.cad_engine.find_enclosed_regions()
        for i, poly in enumerate(polygons):
            coords = list(poly.exterior.coords)
            coords_3d = [(c[0], c[1], 0.0) for c in coords[:-1]]
            
            if len(coords_3d) >= 3:
                faces = [len(coords_3d)] + list(range(len(coords_3d)))
                mesh = pv.PolyData(coords_3d, faces)
                actor = self.plotter.add_mesh(mesh, color='#f1c40f', opacity=0.3, show_edges=True, name=f'hl_{i}')
                self.highlight_actors.append(f'hl_{i}')
        self.plotter.render()
        
    def clear_highlights(self):
        for name in self.highlight_actors:
            self.plotter.remove_actor(name)
        self.highlight_actors = []
        self.plotter.render()
        
    def render_grilla(self):
        if self.cad_engine.grilla:
            self.render_element(self.cad_engine.grilla, '#7f8c8d')
