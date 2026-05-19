from PyQt6.QtWidgets import QWidget, QVBoxLayout
from pyvistaqt import QtInteractor
import pyvista as pv
from src.cad.state_manager import CadMode
import numpy as np

class Viewport3D(QWidget):
    def __init__(self, cad_engine, state_manager, building, parent=None):
        super().__init__(parent)
        self.cad_engine = cad_engine
        self.state_manager = state_manager
        self.building = building
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter.interactor)
        
        self.plotter.set_background('#2b2b2b')
        self.plotter.show_axes()
        
        self.plotter.track_click_position(callback=self.on_click, side='left')
        
        self.state_manager.add_observer(self.on_mode_changed)
        self.current_viga_start = None
        self.highlight_actors = []
        
        self.is_2d_mode = True
        self.set_2d_mode()
        
    def set_2d_mode(self):
        self.is_2d_mode = True
        # Forzar vista top-down
        self.plotter.view_xy()
        self.plotter.camera.parallel_projection = True
        # Habilitar pan (desplazamiento) con click izquierdo, deshabilitar rotacion
        self.plotter.enable_2d_style()
        self.refresh_scene()
        
    def set_3d_mode(self):
        self.is_2d_mode = False
        self.plotter.camera.parallel_projection = False
        # Habilitar trackball (rotacion) normal
        self.plotter.enable_trackball_style()
        self.plotter.view_isometric()
        self.refresh_scene()
        
    def refresh_scene(self):
        # Limpiar escena conservando configuracion de interaccion
        for actor in list(self.plotter.actors.keys()):
            # Conservamos ejes, luz, etc. si aplica. Normalmente removemos todo y regeneramos
            self.plotter.remove_actor(actor)
            
        self.plotter.show_axes()
        
        z_act = self.building.get_active_level().elevation
        
        # Renderizar grilla en el nivel actual
        if self.cad_engine.grilla:
            self.cad_engine.grilla.z_level = z_act
            self.cad_engine.grilla.mesh = self.cad_engine.grilla._create_mesh()
            self.render_element(self.cad_engine.grilla, '#7f8c8d')
            
        # Renderizar pilares (todos en 3D, y los que llegan al nivel activo en 2D)
        for pilar in self.cad_engine.pilares:
            # Podriamos filtrar, por ahora mostramos todos
            self.render_element(pilar, '#3498db')
            
        # Renderizar vigas y losas (filtrar por nivel activo en 2D)
        for viga in self.cad_engine.vigas:
            if not self.is_2d_mode or abs(viga.p1[2] - z_act) < 0.01:
                self.render_element(viga, '#e74c3c')
                
        for losa in self.cad_engine.losas:
            if not self.is_2d_mode or abs(losa.points[0][2] - z_act) < 0.01:
                self.render_element(losa, '#95a5a6')
                
        if self.state_manager.current_mode == CadMode.ASIGNAR_LOSA:
            self.highlight_enclosed_regions()
            
        self.plotter.render()
        
    def on_mode_changed(self, mode):
        self.current_viga_start = None
        if mode == CadMode.ASIGNAR_LOSA and self.is_2d_mode:
            self.highlight_enclosed_regions()
        else:
            self.clear_highlights()
            
    def render_element(self, element, color, name=None):
        if element and hasattr(element, 'mesh') and element.mesh.n_points > 0:
            self.plotter.add_mesh(element.mesh, color=color, show_edges=True, name=name)
            self.plotter.render()
            
    def on_click(self, pt):
        if not self.is_2d_mode:
            # En modo 3D no permitimos dibujar
            return
            
        mode = self.state_manager.current_mode
        if mode == CadMode.DIBUJAR_PILAR:
            pilar = self.cad_engine.add_pilar(pt)
            if pilar:
                self.render_element(pilar, '#3498db')
            
        elif mode == CadMode.DIBUJAR_VIGA:
            snap_pt = self.cad_engine.snap_to_grid(pt)
            if self.current_viga_start is None:
                self.current_viga_start = snap_pt
            else:
                viga = self.cad_engine.add_viga(self.current_viga_start, snap_pt)
                self.render_element(viga, '#e74c3c')
                self.current_viga_start = snap_pt
                
        elif mode == CadMode.ASIGNAR_LOSA:
            losa = self.cad_engine.assign_losa(pt)
            if losa:
                self.render_element(losa, '#95a5a6')
                self.clear_highlights()
                self.highlight_enclosed_regions()
                
    def highlight_enclosed_regions(self):
        self.clear_highlights()
        polygons = self.cad_engine.find_enclosed_regions()
        z_level = self.building.get_active_level().elevation
        for i, poly in enumerate(polygons):
            coords = list(poly.exterior.coords)
            coords_3d = [(c[0], c[1], z_level) for c in coords[:-1]]
            
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
