"""mesher.py — Meshing engine using Gmsh to generate quadrilateral grids."""
import gmsh
from typing import Dict, Any
from badgercad.core.elements.losa import Losa


def mesh_losa(losa: Losa, target_size: float = 0.50) -> Dict[str, Any]:
    """Generates a predominantly quadrilateral mesh for a slab polygon.
    
    Returns:
        dict: {
            "nodes": {tag: (x, y, z), ...},
            "elements": {tag: [n1, n2, n3, n4], ...}
        }
    """
    try:
        gmsh.initialize()
    except Exception:
        pass  # Already initialized
        
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("losa")
    
    try:
        # Losa.vertices usually comes from shapely and is closed (first == last)
        unique_verts = list(losa.vertices)
        if len(unique_verts) > 1 and unique_verts[0] == unique_verts[-1]:
            unique_verts.pop()
            
        points = []
        for v in unique_verts:
            pt = gmsh.model.geo.addPoint(v[0], v[1], 0.0, target_size)
            points.append(pt)
            
        lines = []
        n = len(points)
        for i in range(n):
            l = gmsh.model.geo.addLine(points[i], points[(i+1)%n])
            lines.append(l)
            
        cl = gmsh.model.geo.addCurveLoop(lines)
        surf = gmsh.model.geo.addPlaneSurface([cl])
        
        gmsh.model.geo.synchronize()
        
        # Force quads for OpenSeesPy ShellMITC4
        gmsh.option.setNumber("Mesh.RecombineAll", 1)
        gmsh.option.setNumber("Mesh.Algorithm", 8)  # Frontal-Delaunay for quads
        gmsh.model.mesh.setRecombine(2, surf)
        
        gmsh.model.mesh.generate(2)
        
        # Extract
        nodeTags, nodeCoords, _ = gmsh.model.mesh.getNodes()
        nodes = {}
        for i, tag in enumerate(nodeTags):
            nodes[int(tag)] = (nodeCoords[3*i], nodeCoords[3*i+1], nodeCoords[3*i+2])
            
        elementTypes, elementTags, eleNodeTags = gmsh.model.mesh.getElements(dim=2)
        elements = {}
        
        # 3 is the element type for 4-node quadrangles in Gmsh
        if 3 in elementTypes:
            idx = list(elementTypes).index(3)
            tags = elementTags[idx]
            ntags = eleNodeTags[idx]
            for i, tag in enumerate(tags):
                elements[int(tag)] = [
                    int(ntags[4*i]), int(ntags[4*i+1]), 
                    int(ntags[4*i+2]), int(ntags[4*i+3])
                ]
                
        return {"nodes": nodes, "elements": elements}
    finally:
        gmsh.clear()
        gmsh.finalize()
