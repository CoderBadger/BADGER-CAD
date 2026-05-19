import numpy as np
from shapely.geometry import Point, LineString
from shapely.ops import polygonize
from src.model.elements import Pilar, Viga, Losa

class CadEngine:
    def __init__(self, building):
        self.building = building
        self.pilares = []
        self.vigas = []
        self.losas = []
        self.grilla = None
        self.grid_snap_distance = 0.5
        
    def set_grilla(self, grilla):
        self.grilla = grilla
        
    def snap_to_grid(self, pt):
        x, y, z = pt
        if not self.grilla:
            return x, y
            
        closest_x = min(self.grilla.x_lines, key=lambda gx: abs(gx - x))
        closest_y = min(self.grilla.y_lines, key=lambda gy: abs(gy - y))
        
        snap_x = closest_x if abs(closest_x - x) < self.grid_snap_distance else x
        snap_y = closest_y if abs(closest_y - y) < self.grid_snap_distance else y
        
        return snap_x, snap_y
        
    def add_pilar(self, pt):
        x, y = self.snap_to_grid(pt)
        start_z = self.building.get_foundation_level().elevation
        end_z = self.building.get_active_level().elevation
        
        if start_z == end_z:
            return None
            
        pilar = Pilar(x, y, start_z, end_z)
        self.pilares.append(pilar)
        return pilar
        
    def add_viga(self, p1, p2):
        snap_p1 = self.snap_to_grid(p1)
        snap_p2 = self.snap_to_grid(p2)
        z_level = self.building.get_active_level().elevation
        viga = Viga(snap_p1, snap_p2, z_level)
        self.vigas.append(viga)
        return viga
        
    def find_enclosed_regions(self):
        lines = []
        z_level = self.building.get_active_level().elevation
        
        # Consider only beams at the current level
        vigas_nivel = [v for v in self.vigas if abs(v.p1[2] - z_level) < 0.01]
        
        for viga in vigas_nivel:
            lines.append(LineString([(viga.p1[0], viga.p1[1]), (viga.p2[0], viga.p2[1])]))
            
        polygons = list(polygonize(lines))
        return polygons
        
    def assign_losa(self, pt):
        polygons = self.find_enclosed_regions()
        point = Point(pt[0], pt[1])
        z_level = self.building.get_active_level().elevation
        
        for poly in polygons:
            if poly.contains(point):
                coords = list(poly.exterior.coords)
                coords_2d = [(c[0], c[1]) for c in coords[:-1]]
                losa = Losa(coords_2d, z_level)
                self.losas.append(losa)
                return losa
        return None
