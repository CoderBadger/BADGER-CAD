import numpy as np
from shapely.geometry import Point, LineString
from shapely.ops import polygonize
from src.model.elements import Pilar, Viga, Losa

class CadEngine:
    def __init__(self):
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
            return x, y, 0.0
            
        closest_x = min(self.grilla.x_lines, key=lambda gx: abs(gx - x))
        closest_y = min(self.grilla.y_lines, key=lambda gy: abs(gy - y))
        
        # Snap solo si estamos cerca
        snap_x = closest_x if abs(closest_x - x) < self.grid_snap_distance else x
        snap_y = closest_y if abs(closest_y - y) < self.grid_snap_distance else y
        
        return snap_x, snap_y, 0.0
        
    def add_pilar(self, pt):
        x, y, _ = self.snap_to_grid(pt)
        pilar = Pilar(x, y)
        self.pilares.append(pilar)
        return pilar
        
    def add_viga(self, p1, p2):
        snap_p1 = self.snap_to_grid(p1)
        snap_p2 = self.snap_to_grid(p2)
        viga = Viga(snap_p1, snap_p2)
        self.vigas.append(viga)
        return viga
        
    def find_enclosed_regions(self):
        lines = []
        for viga in self.vigas:
            lines.append(LineString([(viga.p1[0], viga.p1[1]), (viga.p2[0], viga.p2[1])]))
            
        polygons = list(polygonize(lines))
        return polygons
        
    def assign_losa(self, pt):
        polygons = self.find_enclosed_regions()
        point = Point(pt[0], pt[1])
        
        for poly in polygons:
            if poly.contains(point):
                coords = list(poly.exterior.coords)
                coords_3d = [(c[0], c[1], 0.0) for c in coords[:-1]]
                losa = Losa(coords_3d)
                self.losas.append(losa)
                return losa
        return None
