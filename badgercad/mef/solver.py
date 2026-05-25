"""solver.py — Structural FEA solver using OpenSeesPy."""

class OpenSeesImportError(Exception):
    """Raised when openseespy cannot be imported, usually due to missing DLLs or unsupported Python version."""
    pass

try:
    import openseespy.opensees as ops
except ImportError as e:
    raise OpenSeesImportError(f"Failed to import openseespy: {e}")

from typing import Dict, Any, List, Tuple
from shapely.geometry import Point, LineString, Polygon
from badgercad.core.elements.losa import Losa
from badgercad.core.elements.pilar import Pilar
from badgercad.core.elements.viga import Viga
from badgercad.core.loads import CargaLineal, Hipotesis
from badgercad.core.normativa import calcular_envolventes

def _aplicar_cargas_lineales_cm(cargas: List[CargaLineal], mesh: Dict[str, Any]) -> None:
    """Project linear loads onto the ShellMITC4 elements and apply equivalent nodal loads."""
    for carga in cargas:
        linea = LineString([carga.p1, carga.p2])
        for ele_tag, n_tags in mesh["elements"].items():
            puntos = [mesh["nodes"][nt][:2] for nt in n_tags]
            poly = Polygon(puntos)
            interseccion = linea.intersection(poly)
            
            if not interseccion.is_empty:
                L_dentro = interseccion.length
                F_total = L_dentro * carga.magnitud * 1000.0  # kN -> N
                F_nodo = F_total / 4.0
                
                # TODO: Refinar distribución usando funciones de forma bilineales del ShellMITC4 
                # basada en la distancia al baricentro de la intersección.
                for nt in n_tags:
                    ops.load(nt, 0.0, 0.0, -F_nodo, 0.0, 0.0, 0.0)

def _extract_results(nodes: Dict[int, Any], elements: Dict[int, Any]) -> Tuple[Dict[int, float], Dict[int, float], Dict[int, float]]:
    displacements = {}
    for tag in nodes.keys():
        displacements[tag] = ops.nodeDisp(tag, 3)
        
    forces_mxx = {}
    forces_myy = {}
    for tag in elements.keys():
        forces = ops.eleResponse(tag, 'forces')
        if forces and len(forces) == 32:
            forces_mxx[tag] = (forces[3] + forces[11] + forces[19] + forces[27]) / 4.0
            forces_myy[tag] = (forces[4] + forces[12] + forces[20] + forces[28]) / 4.0
        else:
            forces_mxx[tag] = 0.0
            forces_myy[tag] = 0.0
            
    return displacements, forces_mxx, forces_myy

def resolver_losa(
    losa: Losa, 
    mesh: Dict[str, Any], 
    pilares: List[Pilar], 
    vigas: List[Viga],
    cargas_lineales: List[CargaLineal],
    cm_sup: float,
    cv_sup: float
) -> Dict[str, Any]:
    """Builds and solves the FEA model for the meshed slab sequentially for PP, CM, CV.
    
    Args:
        losa: The slab being solved.
        mesh: Dict containing "nodes" and "elements" from mesher.py.
        pilares: List of pilares to act as boundary conditions.
        vigas: List of beams in the slab's group.
        cargas_lineales: Linear loads in the group.
        cm_sup: Dead load from the group [kN/m2].
        cv_sup: Live load from the group [kN/m2].
        
    Returns:
        dict: Integrated results with "PP", "CM", "CV", "ELU_1", "ELU_2", "Envolvente".
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
        
    # 4. Analysis Settings (shared)
    ops.system('BandSPD')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')
    
    # Base results dictionaries
    base_disp = {}
    base_mxx = {}
    base_myy = {}
    
    # -------------------------------------------------------------
    # 5. LoadPattern PP (Peso Propio)
    # -------------------------------------------------------------
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    
    # PP superficial losa (kN/m2 -> N/m2)
    qz_pp = losa.peso_propio * 1000.0
    for tag in elements.keys():
        ops.eleLoad('-ele', tag, '-type', '-surface', 0.0, 0.0, -qz_pp)
        
    # PP vigas (como cargas lineales)
    class VigaDummyCarga:
        def __init__(self, p1, p2, mag):
            self.p1 = p1
            self.p2 = p2
            self.magnitud = mag
    cargas_vigas_pp = [VigaDummyCarga(v.nodo_inicial, v.nodo_final, v.peso_propio) for v in vigas]
    _aplicar_cargas_lineales_cm(cargas_vigas_pp, mesh)
    
    ok = ops.analyze(1)
    if ok != 0: raise RuntimeError("OpenSeesPy analysis failed at PP.")
    d_pp, mxx_pp, myy_pp = _extract_results(nodes, elements)
    base_disp["PP"], base_mxx["PP"], base_myy["PP"] = d_pp, mxx_pp, myy_pp
    
    ops.remove('loadPattern', 1)
    ops.reset()
    
    # -------------------------------------------------------------
    # 6. LoadPattern CM (Carga Muerta)
    # -------------------------------------------------------------
    ops.pattern('Plain', 2, 1)
    
    qz_cm = cm_sup * 1000.0
    for tag in elements.keys():
        ops.eleLoad('-ele', tag, '-type', '-surface', 0.0, 0.0, -qz_cm)
        
    cargas_cm = [c for c in cargas_lineales if c.hipotesis == Hipotesis.CM]
    _aplicar_cargas_lineales_cm(cargas_cm, mesh)
    
    ok = ops.analyze(1)
    if ok != 0: raise RuntimeError("OpenSeesPy analysis failed at CM.")
    d_cm, mxx_cm, myy_cm = _extract_results(nodes, elements)
    base_disp["CM"], base_mxx["CM"], base_myy["CM"] = d_cm, mxx_cm, myy_cm
    
    ops.remove('loadPattern', 2)
    ops.reset()
    
    # -------------------------------------------------------------
    # 7. LoadPattern CV (Sobrecarga de Uso)
    # -------------------------------------------------------------
    ops.pattern('Plain', 3, 1)
    
    qz_cv = cv_sup * 1000.0
    for tag in elements.keys():
        ops.eleLoad('-ele', tag, '-type', '-surface', 0.0, 0.0, -qz_cv)
        
    cargas_cv = [c for c in cargas_lineales if c.hipotesis == Hipotesis.CV]
    _aplicar_cargas_lineales_cm(cargas_cv, mesh)
    
    ok = ops.analyze(1)
    if ok != 0: raise RuntimeError("OpenSeesPy analysis failed at CV.")
    d_cv, mxx_cv, myy_cv = _extract_results(nodes, elements)
    base_disp["CV"], base_mxx["CV"], base_myy["CV"] = d_cv, mxx_cv, myy_cv
    
    ops.remove('loadPattern', 3)
    ops.wipe()
    
    # 8. Calcular Combinaciones y Envolventes
    disp_res = calcular_envolventes(base_disp)
    mxx_res = calcular_envolventes(base_mxx)
    myy_res = calcular_envolventes(base_myy)
    
    return {
        "displacements": disp_res,
        "forces_mxx": mxx_res,
        "forces_myy": myy_res
    }
