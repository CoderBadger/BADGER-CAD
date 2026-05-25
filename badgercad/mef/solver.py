"""solver.py — Structural FEA solver using OpenSeesPy."""
import openseespy.opensees as ops
from typing import Dict, Any, List
from shapely.geometry import Point
from badgercad.core.elements.losa import Losa
from badgercad.core.elements.pilar import Pilar

def resolver_losa(losa: Losa, mesh: Dict[str, Any], pilares: List[Pilar], carga_qz: float = 10000.0) -> Dict[str, Any]:
    """Builds and solves the FEA model for the meshed slab.
    
    Args:
        losa: The slab being solved.
        mesh: Dict containing "nodes" and "elements" from mesher.py.
        pilares: List of pilares to act as boundary conditions.
        carga_qz: Surface load in Z direction (N/m2), e.g. 10000 for 10 kN/m2.
        
    Returns:
        dict: {
            "displacements": {node_tag: dz, ...},
            "forces_mxx": {ele_tag: mxx_avg, ...},
            "forces_myy": {ele_tag: myy_avg, ...}
        }
    """
    ops.wipe()
    ops.model('basic', '-ndm', 3, '-ndf', 6)
    
    # 1. Define Material and Section
    # ElasticMembranePlateSection requires: tag, E, nu, h, rho
    E = 25e9   # N/m2
    nu = 0.2
    h = max(losa.espesor, 0.01)
    rho = 2500 # kg/m3
    
    sec_tag = 1
    ops.section('ElasticMembranePlateSection', sec_tag, E, nu, h, rho)
    
    # 2. Define Nodes and BCs
    nodes = mesh["nodes"]
    
    # Pre-build pilar footprint polygons for fast checking
    from shapely.ops import unary_union
    from shapely.geometry import Polygon
    pilar_polys = [Polygon(p.footprint_2d()) for p in pilares]
    pilar_union = unary_union(pilar_polys) if pilar_polys else None
    
    for tag, (x, y, z) in nodes.items():
        ops.node(tag, x, y, 0.0)
        
        # Check boundary condition
        if pilar_union is not None:
            pt = Point(x, y)
            if pt.within(pilar_union) or pt.intersects(pilar_union):
                # Fixed support at columns
                ops.fix(tag, 1, 1, 1, 1, 1, 1)
                
    # 3. Define Elements
    elements = mesh["elements"]
    for tag, n_tags in elements.items():
        # ShellMITC4: eleTag, iNode, jNode, kNode, lNode, secTag
        ops.element('ShellMITC4', tag, n_tags[0], n_tags[1], n_tags[2], n_tags[3], sec_tag)
        
    # 4. Loads
    # Surface load applied directly to the shell elements
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    for tag in elements.keys():
        # ops.eleLoad('-ele', eleTag, '-type', '-surface', p1, p2, p3)
        # For ShellMITC4, surface load is in local Z if p1 is not 0? 
        # Actually OpenSeesPy surface load for ShellMITC4 takes: 
        # ops.eleLoad('-ele', eleTag, '-type', '-surface', q1, q2, q3) where q3 is global Z or local Z depending on the shell element.
        # But generally for plates flat in XY, local Z = global Z.
        ops.eleLoad('-ele', tag, '-type', '-surface', 0.0, 0.0, -carga_qz)
        
    # 5. Analysis Settings
    ops.system('BandSPD')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')
    
    # 6. Solve
    ok = ops.analyze(1)
    if ok != 0:
        raise RuntimeError("OpenSeesPy analysis failed.")
        
    # 7. Extract Results
    displacements = {}
    for tag in nodes.keys():
        dz = ops.nodeDisp(tag, 3)
        displacements[tag] = dz
        
    forces_mxx = {}
    forces_myy = {}
    for tag in elements.keys():
        # ShellMITC4 forces: 8 components per node (Fxx, Fyy, Fxy, Mxx, Myy, Mxy, Vxz, Vyz) = 32 values
        forces = ops.eleResponse(tag, 'forces')
        if forces and len(forces) == 32:
            mxx_avg = (forces[3] + forces[11] + forces[19] + forces[27]) / 4.0
            myy_avg = (forces[4] + forces[12] + forces[20] + forces[28]) / 4.0
            forces_mxx[tag] = mxx_avg
            forces_myy[tag] = myy_avg
        else:
            forces_mxx[tag] = 0.0
            forces_myy[tag] = 0.0
            
    ops.wipe()
    
    return {
        "displacements": displacements,
        "forces_mxx": forces_mxx,
        "forces_myy": forces_myy
    }
