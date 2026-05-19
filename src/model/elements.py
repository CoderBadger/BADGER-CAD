import numpy as np
import pyvista as pv

class Pilar:
    def __init__(self, x, y, start_z, end_z, width=0.30, depth=0.30):
        self.x = x
        self.y = y
        self.start_z = start_z
        self.end_z = end_z
        self.width = width
        self.depth = depth
        self.mesh = self._create_mesh()
        
    def _create_mesh(self):
        height = abs(self.end_z - self.start_z)
        if height == 0:
            return pv.PolyData()
        center = (self.x, self.y, (self.start_z + self.end_z) / 2)
        mesh = pv.Cube(center=center, x_length=self.width, y_length=self.depth, z_length=height)
        return mesh

class Viga:
    def __init__(self, p1, p2, z_level, width=0.30, height=0.40):
        self.p1 = np.array([p1[0], p1[1], z_level])
        self.p2 = np.array([p2[0], p2[1], z_level])
        self.width = width
        self.height = height
        self.mesh = self._create_mesh()
        
    def _create_mesh(self):
        vec = self.p2 - self.p1
        length = np.linalg.norm(vec)
        if length == 0:
            return pv.PolyData()
            
        dir_norm = vec / length
        up = np.array([0, 0, 1])
        right = np.cross(dir_norm, up)
        
        if np.linalg.norm(right) == 0:
            right = np.array([1, 0, 0])
        else:
            right = right / np.linalg.norm(right)
            
        w2 = self.width / 2
        h = self.height
        
        p1_top_left = self.p1 - right * w2
        p1_top_right = self.p1 + right * w2
        p1_bot_left = self.p1 - right * w2 - up * h
        p1_bot_right = self.p1 + right * w2 - up * h
        
        p2_top_left = self.p2 - right * w2
        p2_top_right = self.p2 + right * w2
        p2_bot_left = self.p2 - right * w2 - up * h
        p2_bot_right = self.p2 + right * w2 - up * h
        
        vertices = np.array([
            p1_bot_left, p1_bot_right, p1_top_right, p1_top_left,
            p2_bot_left, p2_bot_right, p2_top_right, p2_top_left
        ])
        
        faces = np.hstack([
            [4, 0, 1, 2, 3], # front
            [4, 4, 5, 6, 7], # back
            [4, 0, 1, 5, 4], # bottom
            [4, 3, 2, 6, 7], # top
            [4, 0, 3, 7, 4], # left
            [4, 1, 2, 6, 5], # right
        ])
        
        mesh = pv.PolyData(vertices, faces)
        return mesh

class Losa:
    def __init__(self, vertices, z_level, thickness=0.20):
        # vertices es una lista de (x, y)
        self.points = np.array([[v[0], v[1], z_level] for v in vertices])
        self.thickness = thickness
        self.mesh = self._create_mesh()
        
    def _create_mesh(self):
        if len(self.points) < 3:
            return pv.PolyData()
            
        faces = [len(self.points)] + list(range(len(self.points)))
        poly = pv.PolyData(self.points, faces)
        
        mesh = poly.extrude((0, 0, -self.thickness), capping=True)
        return mesh

class Grilla:
    def __init__(self, x_lines, y_lines, z_level=0.0):
        self.x_lines = x_lines
        self.y_lines = y_lines
        self.z_level = z_level
        self.mesh = self._create_mesh()
        
    def _create_mesh(self):
        points = []
        lines = []
        
        if not self.x_lines or not self.y_lines:
            return pv.PolyData()
            
        min_x, max_x = min(self.x_lines), max(self.x_lines)
        min_y, max_y = min(self.y_lines), max(self.y_lines)
        
        idx = 0
        for x in self.x_lines:
            points.append([x, min_y, self.z_level])
            points.append([x, max_y, self.z_level])
            lines.extend([2, idx, idx+1])
            idx += 2
            
        for y in self.y_lines:
            points.append([min_x, y, self.z_level])
            points.append([max_x, y, self.z_level])
            lines.extend([2, idx, idx+1])
            idx += 2
            
        mesh = pv.PolyData(np.array(points), np.array(lines))
        return mesh
