"""storage.py — Native JSON serialization for BadgerCAD projects."""
import json
import os
import dataclasses
from enum import Enum

from badgercad.core.project import Project
from badgercad.core.elements.nivel import Nivel
from badgercad.core.elements.grupo import Grupo
from badgercad.core.elements.pilar import Pilar
from badgercad.core.elements.viga import Viga
from badgercad.core.elements.losa import Losa
from badgercad.core.loads import CargaLineal, Hipotesis

class BadgerEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        return super().default(obj)

def save_project_json(project: Project, filepath: str) -> None:
    """Save the entire project state to a .bgcad JSON file."""
    data = {
        "version": "1.0",
        "nombre": project.nombre,
        "niveles": project.niveles,
        "grupos": project.grupos,
        "pilares": project.pilares,
        "vigas": project.vigas,
        "losas": project.losas,
        "cargas_lineales": project.cargas_lineales
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, cls=BadgerEncoder, indent=4, ensure_ascii=False)

def load_project_json(filepath: str) -> Project:
    """Load a project from a .bgcad JSON file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    project = Project()
    project.nombre = data.get("nombre", "Proyecto Cargado")
    
    project.niveles = [Nivel(**n) for n in data.get("niveles", [])]
    project.grupos = [Grupo(**g) for g in data.get("grupos", [])]
    project.pilares = [Pilar(**p) for p in data.get("pilares", [])]
    
    vigas = []
    for v in data.get("vigas", []):
        viga_data = v.copy()
        if "nodo_inicial" in viga_data: viga_data["nodo_inicial"] = tuple(viga_data["nodo_inicial"])
        if "nodo_final" in viga_data: viga_data["nodo_final"] = tuple(viga_data["nodo_final"])
        vigas.append(Viga(**viga_data))
    project.vigas = vigas
    
    losas = []
    for l in data.get("losas", []):
        losa_data = l.copy()
        if "vertices" in losa_data: losa_data["vertices"] = [tuple(v) for v in losa_data["vertices"]]
        losas.append(Losa(**losa_data))
    project.losas = losas
    
    cargas = []
    for c in data.get("cargas_lineales", []):
        carga_data = c.copy()
        if "p1" in carga_data: carga_data["p1"] = tuple(carga_data["p1"])
        if "p2" in carga_data: carga_data["p2"] = tuple(carga_data["p2"])
        if "hipotesis" in carga_data: carga_data["hipotesis"] = Hipotesis(carga_data["hipotesis"])
        cargas.append(CargaLineal(**carga_data))
    project.cargas_lineales = cargas
    
    project._nivel_activo = project.niveles[0] if project.niveles else None
    project._grupo_activo = project.grupos[0] if project.grupos else None
    
    # Rebuild indices and invalidate caches
    project._rebuild_indices()
    project.invalidate_geometry_cache()
    project._undo_stack.clear()
    
    return project
