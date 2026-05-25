"""normativa.py — Motor de combinaciones de carga normativas (NB 1225002)."""
import numpy as np
from typing import Dict

# Factores de mayoración [Factor PP, Factor CM, Factor CV]
COMBINACIONES_ELU = {
    "ELU_1": np.array([1.4, 1.4, 0.0]),
    "ELU_2": np.array([1.2, 1.2, 1.6]),
}

def calcular_envolventes(
    resultados_base: Dict[str, Dict[int, float]]
) -> Dict[str, Dict[int, float]]:
    """Calcula las combinaciones ELU y la Envolvente a partir de los resultados base (PP, CM, CV).
    
    Args:
        resultados_base: Diccionario de la forma:
                         {
                             "PP": {tag: valor, ...},
                             "CM": {tag: valor, ...},
                             "CV": {tag: valor, ...}
                         }
                         
    Returns:
        Un diccionario expandido con las hipótesis base, los combos y la envolvente:
        {
            "PP": {...}, "CM": {...}, "CV": {...},
            "ELU_1": {...}, "ELU_2": {...}, "Envolvente": {...}
        }
    """
    if not resultados_base:
        return {}
        
    tags = list(resultados_base["PP"].keys())
    if not tags:
        return resultados_base
        
    # Convert arrays for fast computation
    v_pp = np.array([resultados_base["PP"].get(t, 0.0) for t in tags])
    v_cm = np.array([resultados_base["CM"].get(t, 0.0) for t in tags])
    v_cv = np.array([resultados_base["CV"].get(t, 0.0) for t in tags])
    
    matriz_casos = np.column_stack((v_pp, v_cm, v_cv)) # Shape: (N_tags, 3)
    
    resultados_finales = {
        "PP": resultados_base["PP"],
        "CM": resultados_base["CM"],
        "CV": resultados_base["CV"],
    }
    
    todas_combinaciones = []
    
    for combo_nombre, factores in COMBINACIONES_ELU.items():
        # matrix mult: (N_tags, 3) dot (3,) -> (N_tags,)
        v_combo = matriz_casos.dot(factores)
        resultados_finales[combo_nombre] = {tag: val for tag, val in zip(tags, v_combo)}
        todas_combinaciones.append(v_combo)
        
    if todas_combinaciones:
        matriz_combos = np.column_stack(todas_combinaciones) # Shape: (N_tags, n_combos)
        
        # Envolvente: máximo absoluto pero conservando el signo del máximo absoluto
        # Para hacer eso de forma robusta con numpy:
        indices_max_abs = np.argmax(np.abs(matriz_combos), axis=1)
        v_envolvente = matriz_combos[np.arange(len(tags)), indices_max_abs]
        
        resultados_finales["Envolvente"] = {tag: val for tag, val in zip(tags, v_envolvente)}
        
    return resultados_finales
