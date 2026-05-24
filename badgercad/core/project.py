"""Project — global singleton that holds the entire BadgerCAD structural model.

Architecture
------------
``Project`` is a ``QObject`` subclass so it can emit PyQt6 signals whenever
the model changes.  UI widgets connect to those signals instead of polling the
model, keeping the rendering layer fully decoupled from the data layer.

Singleton access
----------------
Always retrieve the application-wide instance via ``get_project()``::

    from badgercad.core.project import get_project
    project = get_project()

Do **not** call ``Project()`` directly in application code; the singleton
factory guarantees there is exactly one model object per process.

Performance notes
-----------------
*O(1) lookups*: ``_nivel_idx`` and ``_grupo_idx`` are plain Python dicts
keyed by element ID.  They are kept in perfect sync with ``self.niveles`` and
``self.grupos`` by every mutating method (``add_nivel``, ``remove_nivel``,
``add_grupo``, ``_crear_estructura_inicial``, ``reset``).  Call
``_rebuild_indices()`` after any bulk reassignment of those lists.

*Undo stack*: a LIFO list of up to 20 ``(action_tag, *args)`` tuples.
Currently tracks ``'pilar_added'`` and ``'pilar_removed'``; extend by pushing
new tuples in ``add_losa`` / ``remove_losa`` as those mutators are added.

Hito roadmap
------------
- Hito 1 (current): Nivel, Grupo, Pilar, Losa model + undo for Pilar ops.
- Hito 2: Viga model, Shapely bay detection (uses ``Pilar.footprint_2d()``).
- Hito 3: Load hypotheses, material DB.
- Hito 5: OpenSeesPy FEM export (uses ``Pilar.con_vinculacion_exterior``).
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
    """Singleton project model — the single source of truth for all structural data.

    Signals
    -------
    niveles_changed :
        Emitted whenever the list of floors or groups is modified (add, remove,
        rename, cota change, group reassignment).
    pilares_changed :
        Emitted whenever a column is added or removed.
    losas_changed :
        Emitted whenever a slab is added or removed.
    nivel_activo_changed :
        Emitted when the currently active floor (used by the 2D canvas) changes.
    project_reset :
        Emitted after ``reset()`` completes; recipients should rebuild any
        cached state derived from the model.

    Attributes
    ----------
    nombre : str
        Human-readable project title shown in the title bar.
    niveles : List[Nivel]
        All floor levels.  **Do not mutate directly** — use ``add_nivel`` /
        ``remove_nivel`` so that ``_nivel_idx`` stays in sync.
    grupos : List[Grupo]
        All floor groups.  Use ``add_grupo`` to keep ``_grupo_idx`` in sync.
    pilares : List[Pilar]
        All column instances, spanning one or more floor levels.
    losas : List[Losa]
        All slab polygons, each belonging to exactly one ``Grupo``.
    """

    # ── Signals ─────────────────────────────────────────────────────────────
    niveles_changed      = pyqtSignal()
    pilares_changed      = pyqtSignal()
    losas_changed        = pyqtSignal()
    nivel_activo_changed = pyqtSignal()
    project_reset        = pyqtSignal()

    def __init__(self, parent=None):
        # QObject requires super().__init__ before ANY attribute access
        super().__init__(parent)
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.nombre: str = "Nuevo Proyecto"
        self.niveles: List[Nivel] = []
        self.grupos:  List[Grupo] = []
        self.pilares: List[Pilar] = []
        self.losas:   List[Losa]  = []

        self._nivel_activo: Optional[Nivel] = None
        self._grupo_activo: Optional[Grupo] = None

        # Undo stack — LIFO list of (action_tag, *payload) tuples, max 20 entries.
        # Supported tags: 'pilar_added' | 'pilar_removed'
        self._undo_stack: list = []

        # O(1) lookup indices — maintained in sync with self.niveles / self.grupos.
        # Updated by add_nivel, remove_nivel, add_grupo and _rebuild_indices().
        self._nivel_idx: dict[str, Nivel] = {}
        self._grupo_idx: dict[str, Grupo] = {}

        self._crear_estructura_inicial()

    # ------------------------------------------------------------------ defaults
    def _crear_estructura_inicial(self) -> None:
        """Bootstrap a project with a Cimentación + three typical floors.

        Creates Niveles at 0.0 m, 3.5 m, 7.0 m, 10.5 m and two default
        Grupos (Grupo 1 → Planta 1; Grupo 2 → Plantas 2 y 3).
        Activates Planta 1 as the default editing floor.
        Rebuilds ``_nivel_idx`` and ``_grupo_idx`` at the end.
        """
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

        # Rebuild lookup indices after setting the lists
        self._rebuild_indices()

    # ------------------------------------------------------------------ properties
    @property
    def nivel_activo(self) -> Optional[Nivel]:
        """The floor currently being edited in the 2D canvas.

        Setting this property also updates ``grupo_activo`` to the group that
        contains the new floor and emits ``nivel_activo_changed``.
        """
        return self._nivel_activo

    @nivel_activo.setter
    def nivel_activo(self, nivel: Optional[Nivel]) -> None:
        self._nivel_activo = nivel
        if nivel is not None:
            self._grupo_activo = self.get_grupo_de_nivel(nivel.id)
        self.nivel_activo_changed.emit()

    @property
    def grupo_activo(self) -> Optional[Grupo]:
        """The group that owns the currently active floor.

        Updated automatically whenever ``nivel_activo`` is set.
        Read-only from the outside — set ``nivel_activo`` instead.
        """
        return self._grupo_activo

    # ------------------------------------------------------------------ queries
    def get_nivel_by_id(self, nivel_id: str) -> Optional[Nivel]:
        """Return the ``Nivel`` with the given ID, or ``None`` if not found.

        Complexity: **O(1)** via ``_nivel_idx``.

        Args:
            nivel_id: The 8-char hex UUID of the level.

        Returns:
            The exact ``Nivel`` instance, or ``None`` if the ID is unknown.
        """
        return self._nivel_idx.get(nivel_id)

    def get_grupo_by_id(self, grupo_id: str) -> Optional[Grupo]:
        """Return the ``Grupo`` with the given ID, or ``None`` if not found.

        Complexity: **O(1)** via ``_grupo_idx``.

        Args:
            grupo_id: The 8-char hex UUID of the group.

        Returns:
            The exact ``Grupo`` instance, or ``None`` if the ID is unknown.
        """
        return self._grupo_idx.get(grupo_id)

    def get_grupo_de_nivel(self, nivel_id: str) -> Optional[Grupo]:
        """Return the ``Grupo`` that contains this ``Nivel``, or ``None``.

        Complexity: O(G) where G = number of groups — typically ≤ 10.

        Args:
            nivel_id: ID of the level to look up.
        """
        for g in self.grupos:
            if nivel_id in g.nivel_ids:
                return g
        return None

    def get_pilares_en_nivel(self, nivel_id: str) -> List[Pilar]:
        """Return all columns whose vertical span *passes through* this floor.

        A column ``p`` is included if ``nd.cota ≤ nivel.cota ≤ nh.cota``
        (both endpoints are inclusive, matching CYPECAD's convention where a
        column declared from Cimentación to Planta 1 is visible on both those
        floors).

        Complexity: **O(m)** where m = total number of pilares.
        Each of the two sub-lookups (``nivel_desde`` / ``nivel_hasta``) is
        **O(1)** via ``_nivel_idx``, down from **O(m × n)** with the old
        linear-scan approach.

        Args:
            nivel_id: ID of the floor to query.

        Returns:
            List of matching ``Pilar`` instances (may be empty).
        """
        nivel = self._nivel_idx.get(nivel_id)
        if nivel is None:
            return []
        cota   = nivel.cota
        result: List[Pilar] = []
        for p in self.pilares:
            nd = self._nivel_idx.get(p.nivel_desde_id)
            nh = self._nivel_idx.get(p.nivel_hasta_id)
            if nd is not None and nh is not None and nd.cota <= cota <= nh.cota:
                result.append(p)
        return result

    def get_losas_en_grupo(self, grupo_id: str) -> List[Losa]:
        """Return all slabs belonging to the given group.

        Args:
            grupo_id: ID of the Grupo.

        Returns:
            Filtered list of ``Losa`` instances; empty if the group is unknown
            or has no slabs.
        """
        return [lo for lo in self.losas if lo.grupo_id == grupo_id]

    def niveles_ordenados(self) -> List[Nivel]:
        """Return all floors sorted bottom-up by elevation (cota).

        Returns:
            New list sorted by ascending ``cota``; the original ``self.niveles``
            list is not modified.
        """
        return sorted(self.niveles, key=lambda n: n.cota)

    # ------------------------------------------------------------------ mutators
    def add_pilar(self, pilar: Pilar) -> None:
        """Add a column to the project and push an undo record.

        Emits ``pilares_changed``.

        Args:
            pilar: A fully initialised ``Pilar`` instance.  Its ``id`` must be
                   unique (auto-generated by the dataclass default factory).
        """
        self.pilares.append(pilar)
        self._push_undo(('pilar_added', pilar.id))
        self.pilares_changed.emit()

    def remove_pilar(self, pilar_id: str, record: bool = True) -> None:
        """Remove a column from the project.

        Emits ``pilares_changed``.

        Args:
            pilar_id: ID of the column to remove.
            record:   If ``True`` (default), push an undo record so the
                      operation can be reversed with ``Ctrl+Z``.  Pass
                      ``False`` when the removal itself is an undo step.
        """
        pilar = next((p for p in self.pilares if p.id == pilar_id), None)
        if pilar and record:
            self._push_undo(('pilar_removed', pilar))  # full object for re-add
        self.pilares = [p for p in self.pilares if p.id != pilar_id]
        self.pilares_changed.emit()

    def add_losa(self, losa: Losa) -> None:
        """Add a slab and register it in its parent Grupo.

        Emits ``losas_changed``.

        Args:
            losa: A ``Losa`` instance with a valid ``grupo_id`` pointing to an
                  existing ``Grupo``.
        """
        self.losas.append(losa)
        grupo = self.get_grupo_by_id(losa.grupo_id)
        if grupo and losa.id not in grupo.losa_ids:
            grupo.losa_ids.append(losa.id)
        self.losas_changed.emit()

    def remove_losa(self, losa_id: str) -> None:
        """Remove a slab and deregister it from its parent Grupo.

        Emits ``losas_changed``.
        """
        self.losas = [lo for lo in self.losas if lo.id != losa_id]
        for g in self.grupos:
            if losa_id in g.losa_ids:
                g.losa_ids.remove(losa_id)
        self.losas_changed.emit()

    def add_nivel(self, nivel: Nivel) -> None:
        """Add a floor level and keep the list sorted by cota.

        Updates ``_nivel_idx`` in O(1).  Emits ``niveles_changed``.
        """
        self.niveles.append(nivel)
        self.niveles.sort(key=lambda n: n.cota)
        self._nivel_idx[nivel.id] = nivel
        self.niveles_changed.emit()

    def remove_nivel(self, nivel_id: str) -> None:
        """Remove a floor level and purge it from any group that referenced it.

        Removes the ID from ``_nivel_idx`` in O(1).  Emits ``niveles_changed``.
        """
        self.niveles = [n for n in self.niveles if n.id != nivel_id]
        self._nivel_idx.pop(nivel_id, None)
        for g in self.grupos:
            if nivel_id in g.nivel_ids:
                g.nivel_ids.remove(nivel_id)
        self.niveles_changed.emit()

    def add_grupo(self, grupo: Grupo) -> None:
        """Add a floor group and update ``_grupo_idx`` in O(1).

        Emits ``niveles_changed`` (because the group list is part of the
        floor tree shown in the Ribbon).
        """
        self.grupos.append(grupo)
        self._grupo_idx[grupo.id] = grupo
        self.niveles_changed.emit()

    def reset(self) -> None:
        """Discard all model data and re-create the default 4-floor structure.

        Clears the undo stack.  Emits ``project_reset``, then
        ``niveles_changed``, ``pilares_changed``, and ``losas_changed`` so all
        connected widgets rebuild from scratch.
        """
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
        """Push a command onto the undo stack (max 20 entries, LIFO).

        When the stack exceeds 20 entries the oldest record is discarded
        (``pop(0)``).  This is intentionally bounded to prevent unbounded
        memory growth in long editing sessions.

        Args:
            cmd: A tuple whose first element is an action tag string and
                 whose remaining elements are the payload needed to reverse
                 the operation.  Currently supported tags:
                 - ``('pilar_added', pilar_id)``
                 - ``('pilar_removed', pilar_obj)``
        """
        self._undo_stack.append(cmd)
        if len(self._undo_stack) > 20:
            self._undo_stack.pop(0)

    def undo(self) -> bool:
        """Undo the last recorded action.

        Returns:
            ``True`` if an action was undone; ``False`` if the stack is empty.
        """
        if not self._undo_stack:
            return False
        cmd    = self._undo_stack.pop()
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
        """Clear the undo stack (called automatically on ``reset()``)."""
        self._undo_stack.clear()

    # ------------------------------------------------------------------ index maintenance
    def _rebuild_indices(self) -> None:
        """Rebuild both O(1) lookup dicts from the current ``niveles`` and ``grupos`` lists.

        Call this after any bulk reassignment of those lists (e.g. after
        ``reset()`` or ``_crear_estructura_inicial()``).  Individual ``add_*``
        / ``remove_*`` methods update the dicts incrementally — they do **not**
        call this method for performance reasons.
        """
        self._nivel_idx = {n.id: n for n in self.niveles}
        self._grupo_idx = {g.id: g for g in self.grupos}

    # ------------------------------------------------------------------ stats
    def stats(self) -> dict:
        """Return a summary dict of element counts.

        Returns:
            ``{"niveles": int, "grupos": int, "pilares": int, "losas": int}``
        """
        return {
            "niveles": len(self.niveles),
            "grupos":  len(self.grupos),
            "pilares": len(self.pilares),
            "losas":   len(self.losas),
        }


# ------------------------------------------------------------------ factory
def get_project() -> "Project":
    """Return the application-wide singleton ``Project`` instance.

    The first call creates the instance; subsequent calls return the same
    object.  Always use this function instead of calling ``Project()``
    directly in application code.

    Returns:
        The singleton ``Project`` instance.
    """
    global _project_instance
    if _project_instance is None:
        _project_instance = Project()
    return _project_instance
