"""Project — global singleton that holds the entire BadgerCAD structural model.

Emits PyQt6 signals whenever the model changes so that the UI can react
without tight coupling between layers.
"""
from __future__ import annotations
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from .elements.nivel import Nivel
from .elements.grupo import Grupo
from .elements.pilar import Pilar
from .elements.losa import Losa

# Module-level singleton reference
_project_instance: Optional["Project"] = None


class Project(QObject):
    """Singleton project model.

    Signals:
        niveles_changed:      Emitted when the floor list is modified.
        pilares_changed:      Emitted when any column is added / removed.
        losas_changed:        Emitted when any slab is added / removed.
        nivel_activo_changed: Emitted when the active floor changes.
        project_reset:        Emitted when the project is fully reset.
    """

    niveles_changed = pyqtSignal()
    pilares_changed = pyqtSignal()
    losas_changed = pyqtSignal()
    nivel_activo_changed = pyqtSignal()
    project_reset = pyqtSignal()

    def __init__(self, parent=None):
        # QObject requires super().__init__ before ANY attribute access
        super().__init__(parent)
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.nombre: str = "Nuevo Proyecto"
        self.niveles: List[Nivel] = []
        self.grupos: List[Grupo] = []
        self.pilares: List[Pilar] = []
        self.losas: List[Losa] = []

        self._nivel_activo: Optional[Nivel] = None
        self._grupo_activo: Optional[Grupo] = None

        # Undo stack: list of (str, *args) tuples, max 20 entries
        self._undo_stack: list = []

        self._crear_estructura_inicial()

    # ------------------------------------------------------------------ defaults
    def _crear_estructura_inicial(self) -> None:
        """Bootstrap a project with a foundation and three typical floors."""
        n0 = Nivel("Cimentación", 0.0)
        n1 = Nivel("Planta 1",   3.50)
        n2 = Nivel("Planta 2",   7.00)
        n3 = Nivel("Planta 3",  10.50)

        self.niveles = [n0, n1, n2, n3]

        g1 = Grupo("Grupo 1", nivel_ids=[n1.id])
        g2 = Grupo("Grupo 2", nivel_ids=[n2.id, n3.id])
        self.grupos = [g1, g2]

        self._nivel_activo = n1
        self._grupo_activo = g1

    # ------------------------------------------------------------------ properties
    @property
    def nivel_activo(self) -> Optional[Nivel]:
        return self._nivel_activo

    @nivel_activo.setter
    def nivel_activo(self, nivel: Optional[Nivel]) -> None:
        self._nivel_activo = nivel
        if nivel is not None:
            self._grupo_activo = self.get_grupo_de_nivel(nivel.id)
        self.nivel_activo_changed.emit()

    @property
    def grupo_activo(self) -> Optional[Grupo]:
        return self._grupo_activo

    # ------------------------------------------------------------------ queries
    def get_nivel_by_id(self, nivel_id: str) -> Optional[Nivel]:
        return next((n for n in self.niveles if n.id == nivel_id), None)

    def get_grupo_by_id(self, grupo_id: str) -> Optional[Grupo]:
        return next((g for g in self.grupos if g.id == grupo_id), None)

    def get_grupo_de_nivel(self, nivel_id: str) -> Optional[Grupo]:
        """Return the Grupo that contains this Nivel, or None."""
        for g in self.grupos:
            if nivel_id in g.nivel_ids:
                return g
        return None

    def get_pilares_en_nivel(self, nivel_id: str) -> List[Pilar]:
        """Return all columns whose vertical span passes through this floor."""
        nivel = self.get_nivel_by_id(nivel_id)
        if nivel is None:
            return []
        result: List[Pilar] = []
        for p in self.pilares:
            nd = self.get_nivel_by_id(p.nivel_desde_id)
            nh = self.get_nivel_by_id(p.nivel_hasta_id)
            if nd is not None and nh is not None:
                if nd.cota <= nivel.cota <= nh.cota:
                    result.append(p)
        return result

    def get_losas_en_grupo(self, grupo_id: str) -> List[Losa]:
        return [lo for lo in self.losas if lo.grupo_id == grupo_id]

    def niveles_ordenados(self) -> List[Nivel]:
        """Return floors sorted bottom-up by cota."""
        return sorted(self.niveles, key=lambda n: n.cota)

    # ------------------------------------------------------------------ mutators
    def add_pilar(self, pilar: Pilar) -> None:
        self.pilares.append(pilar)
        self._push_undo(('pilar_added', pilar.id))
        self.pilares_changed.emit()

    def remove_pilar(self, pilar_id: str, record: bool = True) -> None:
        pilar = next((p for p in self.pilares if p.id == pilar_id), None)
        if pilar and record:
            self._push_undo(('pilar_removed', pilar))  # save full object for re-add
        self.pilares = [p for p in self.pilares if p.id != pilar_id]
        self.pilares_changed.emit()

    def add_losa(self, losa: Losa) -> None:
        self.losas.append(losa)
        grupo = self.get_grupo_by_id(losa.grupo_id)
        if grupo and losa.id not in grupo.losa_ids:
            grupo.losa_ids.append(losa.id)
        self.losas_changed.emit()

    def remove_losa(self, losa_id: str) -> None:
        self.losas = [lo for lo in self.losas if lo.id != losa_id]
        for g in self.grupos:
            if losa_id in g.losa_ids:
                g.losa_ids.remove(losa_id)
        self.losas_changed.emit()

    def add_nivel(self, nivel: Nivel) -> None:
        self.niveles.append(nivel)
        self.niveles.sort(key=lambda n: n.cota)
        self.niveles_changed.emit()

    def remove_nivel(self, nivel_id: str) -> None:
        self.niveles = [n for n in self.niveles if n.id != nivel_id]
        # Remove from any group that referenced it
        for g in self.grupos:
            if nivel_id in g.nivel_ids:
                g.nivel_ids.remove(nivel_id)
        self.niveles_changed.emit()

    def add_grupo(self, grupo: Grupo) -> None:
        self.grupos.append(grupo)
        self.niveles_changed.emit()

    def reset(self) -> None:
        """Discard all model data and re-create the default structure."""
        self.nombre = "Nuevo Proyecto"
        self.niveles.clear()
        self.grupos.clear()
        self.pilares.clear()
        self.losas.clear()
        self._nivel_activo = None
        self._grupo_activo = None
        self.clear_undo()
        self._crear_estructura_inicial()
        self.project_reset.emit()
        self.niveles_changed.emit()
        self.pilares_changed.emit()
        self.losas_changed.emit()

    # ------------------------------------------------------------------ undo
    def _push_undo(self, cmd: tuple) -> None:
        """Push a command onto the undo stack (max 20 entries)."""
        self._undo_stack.append(cmd)
        if len(self._undo_stack) > 20:
            self._undo_stack.pop(0)

    def undo(self) -> bool:
        """Undo the last recorded action. Returns True if something was undone."""
        if not self._undo_stack:
            return False
        cmd = self._undo_stack.pop()
        action = cmd[0]
        if action == 'pilar_added':
            pilar_id = cmd[1]
            self.pilares = [p for p in self.pilares if p.id != pilar_id]
            self.pilares_changed.emit()
        elif action == 'pilar_removed':
            pilar = cmd[1]
            self.pilares.append(pilar)
            self.pilares_changed.emit()
        return True

    def clear_undo(self) -> None:
        """Clear the undo stack (call on project reset)."""
        self._undo_stack.clear()

    # ------------------------------------------------------------------ stats
    def stats(self) -> dict:
        return {
            "niveles": len(self.niveles),
            "grupos": len(self.grupos),
            "pilares": len(self.pilares),
            "losas": len(self.losas),
        }


# ------------------------------------------------------------------ factory
def get_project() -> "Project":
    """Return the application-wide singleton Project instance.

    The first call creates the instance; subsequent calls return the same object.
    Always use this function instead of calling ``Project()`` directly.
    """
    global _project_instance
    if _project_instance is None:
        _project_instance = Project()
    return _project_instance
