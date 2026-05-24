"""tests/test_core_project.py — Unit tests for the Project singleton and core data model.

Scope
-----
These tests cover ONLY the ``badgercad.core`` package.  No PyQt6 signals, no
PyVista rendering, no GPU.  The Project class uses QObject internally, which
requires a QApplication to be alive during testing; conftest.py handles that
via a session-scoped fixture that sets QT_QPA_PLATFORM=offscreen.

Test groups
-----------
1. Index Synchronisation  — _nivel_idx / _grupo_idx stay in sync through
   add, remove, and reset operations.
2. Query correctness       — get_nivel_by_id / get_grupo_by_id / get_pilares_en_nivel
                             return correct objects or None.
3. Undo stack              — add_pilar / remove_pilar / undo chain.
4. Pilar geometry          — footprint_2d / bounds_2d mathematics.
5. Losa geometry           — is_valid / area_aproximada (Shoelace).
6. Nivel ordering          — niveles_ordenados returns bottom-up cota sort.
"""
from __future__ import annotations

import math
import os
import sys

import pytest

# ---------------------------------------------------------------------------
# Ensure PyQt6 can run headless before importing anything that triggers Qt
# ---------------------------------------------------------------------------
os.environ.setdefault("QT_API", "pyqt6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ---------------------------------------------------------------------------
# Session-scoped QApplication (required by QObject subclasses)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def qapp():
    """Return (or create) a headless QApplication for the test session."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    return app


# ---------------------------------------------------------------------------
# Fresh Project fixture (function-scoped → clean slate per test)
# ---------------------------------------------------------------------------
@pytest.fixture()
def project(qapp):
    """Return a brand-new Project with the default 4-floor structure."""
    # Import here so Qt env vars are already set
    from badgercad.core.project import Project
    return Project()


# ===========================================================================
# 1. Index Synchronisation
# ===========================================================================
class TestNivelIdx:
    """_nivel_idx must mirror self.niveles at all times."""

    def test_initial_index_populated(self, project):
        """All four default Niveles must be present in _nivel_idx after init."""
        assert len(project._nivel_idx) == len(project.niveles)
        for n in project.niveles:
            assert n.id in project._nivel_idx
            assert project._nivel_idx[n.id] is n

    def test_add_nivel_updates_index(self, project):
        from badgercad.core.elements.nivel import Nivel
        nuevo = Nivel("Cubierta", 14.0)
        project.add_nivel(nuevo)
        assert nuevo.id in project._nivel_idx
        assert project._nivel_idx[nuevo.id] is nuevo

    def test_remove_nivel_updates_index(self, project):
        n = project.niveles[-1]
        nid = n.id
        project.remove_nivel(nid)
        assert nid not in project._nivel_idx
        assert project.get_nivel_by_id(nid) is None

    def test_reset_rebuilds_index(self, project):
        from badgercad.core.elements.nivel import Nivel
        project.add_nivel(Nivel("Extra", 20.0))
        project.reset()
        # After reset the index must exactly mirror the new nivel list
        assert set(project._nivel_idx.keys()) == {n.id for n in project.niveles}

    def test_get_nivel_by_id_returns_correct_instance(self, project):
        for n in project.niveles:
            assert project.get_nivel_by_id(n.id) is n

    def test_get_nivel_by_id_returns_none_for_unknown(self, project):
        assert project.get_nivel_by_id("deadbeef") is None


class TestGrupoIdx:
    """_grupo_idx must mirror self.grupos at all times."""

    def test_initial_index_populated(self, project):
        assert len(project._grupo_idx) == len(project.grupos)
        for g in project.grupos:
            assert g.id in project._grupo_idx
            assert project._grupo_idx[g.id] is g

    def test_add_grupo_updates_index(self, project):
        from badgercad.core.elements.grupo import Grupo
        nuevo = Grupo("Grupo Extra", nivel_ids=[])
        project.add_grupo(nuevo)
        assert nuevo.id in project._grupo_idx
        assert project._grupo_idx[nuevo.id] is nuevo

    def test_reset_rebuilds_grupo_index(self, project):
        from badgercad.core.elements.grupo import Grupo
        project.add_grupo(Grupo("Tmp", nivel_ids=[]))
        project.reset()
        assert set(project._grupo_idx.keys()) == {g.id for g in project.grupos}

    def test_get_grupo_by_id_returns_correct_instance(self, project):
        for g in project.grupos:
            assert project.get_grupo_by_id(g.id) is g

    def test_get_grupo_by_id_returns_none_for_unknown(self, project):
        assert project.get_grupo_by_id("00000000") is None


# ===========================================================================
# 2. Query Correctness
# ===========================================================================
class TestGetPilaresEnNivel:
    """get_pilares_en_nivel must return exactly the columns spanning a floor."""

    def _make_pilar(self, project, x=0.0, y=0.0):
        from badgercad.core.elements.pilar import Pilar
        niveles = project.niveles_ordenados()
        p = Pilar(
            x=x, y=y,
            nivel_desde_id=niveles[0].id,   # Cimentación (cota 0.0)
            nivel_hasta_id=niveles[1].id,   # Planta 1    (cota 3.5)
        )
        project.add_pilar(p)
        return p

    def test_pilar_visible_on_spanning_floor(self, project):
        p = self._make_pilar(project)
        niveles = project.niveles_ordenados()
        # Planta 1 (cota 3.5) is inside [0.0, 3.5]
        result = project.get_pilares_en_nivel(niveles[1].id)
        assert p in result

    def test_pilar_not_visible_above_span(self, project):
        p = self._make_pilar(project)
        niveles = project.niveles_ordenados()
        # Planta 2 (cota 7.0) is above span [0.0, 3.5]
        result = project.get_pilares_en_nivel(niveles[2].id)
        assert p not in result

    def test_unknown_nivel_returns_empty(self, project):
        self._make_pilar(project)
        assert project.get_pilares_en_nivel("nonexistent") == []

    def test_multiple_pilares_only_correct_ones_returned(self, project):
        """Two pilars with different spans should filter correctly."""
        from badgercad.core.elements.pilar import Pilar
        niveles = project.niveles_ordenados()

        p_low = Pilar(x=1.0, y=0.0,
                      nivel_desde_id=niveles[0].id,
                      nivel_hasta_id=niveles[1].id)   # cota 0–3.5
        p_high = Pilar(x=2.0, y=0.0,
                       nivel_desde_id=niveles[1].id,
                       nivel_hasta_id=niveles[2].id)  # cota 3.5–7.0
        project.add_pilar(p_low)
        project.add_pilar(p_high)

        at_p1 = project.get_pilares_en_nivel(niveles[1].id)  # cota 3.5
        assert p_low in at_p1
        assert p_high in at_p1     # 3.5 is the start of p_high → included

        at_p2 = project.get_pilares_en_nivel(niveles[2].id)  # cota 7.0
        assert p_low not in at_p2
        assert p_high in at_p2


# ===========================================================================
# 3. Undo Stack
# ===========================================================================
class TestUndoStack:
    """Undo must reverse add_pilar and remove_pilar operations."""

    def _pilar(self, project):
        from badgercad.core.elements.pilar import Pilar
        n = project.niveles_ordenados()
        return Pilar(x=5.0, y=5.0,
                     nivel_desde_id=n[0].id,
                     nivel_hasta_id=n[1].id)

    def test_undo_add_pilar(self, project):
        p = self._pilar(project)
        project.add_pilar(p)
        assert p in project.pilares
        project.undo()
        assert p not in project.pilares

    def test_undo_remove_pilar(self, project):
        p = self._pilar(project)
        project.add_pilar(p)
        project.undo()       # undo the add
        project.add_pilar(p) # add again
        project.remove_pilar(p.id)
        assert p not in project.pilares
        project.undo()
        assert p in project.pilares

    def test_undo_empty_stack_returns_false(self, project):
        project.clear_undo()
        assert project.undo() is False

    def test_undo_stack_max_20(self, project):
        """Stack should never grow beyond 20 entries."""
        from badgercad.core.elements.pilar import Pilar
        n = project.niveles_ordenados()
        for i in range(25):
            p = Pilar(x=float(i), y=0.0,
                      nivel_desde_id=n[0].id,
                      nivel_hasta_id=n[1].id)
            project.add_pilar(p)
        assert len(project._undo_stack) == 20


# ===========================================================================
# 4. Pilar Geometry
# ===========================================================================
class TestPilarGeometry:
    """footprint_2d and bounds_2d must be mathematically exact."""

    # --- bounds_2d (AABB, no rotation) ------------------------------------
    def test_bounds_2d_axis_aligned(self):
        from badgercad.core.elements.pilar import Pilar
        p = Pilar(x=10.0, y=20.0, ancho=0.4, largo=0.6)
        xmin, xmax, ymin, ymax = p.bounds_2d()
        assert xmin == pytest.approx(9.8)
        assert xmax == pytest.approx(10.2)
        assert ymin == pytest.approx(19.7)
        assert ymax == pytest.approx(20.3)

    # --- footprint_2d — no rotation (angulo = 0) --------------------------
    def test_footprint_2d_no_rotation_centred_at_origin(self):
        from badgercad.core.elements.pilar import Pilar
        p = Pilar(x=0.0, y=0.0, ancho=0.4, largo=0.6, angulo=0.0)
        verts = p.footprint_2d()
        assert len(verts) == 4
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        assert min(xs) == pytest.approx(-0.2)
        assert max(xs) == pytest.approx(+0.2)
        assert min(ys) == pytest.approx(-0.3)
        assert max(ys) == pytest.approx(+0.3)

    def test_footprint_2d_no_rotation_offset_position(self):
        from badgercad.core.elements.pilar import Pilar
        p = Pilar(x=5.0, y=3.0, ancho=0.3, largo=0.5, angulo=0.0)
        verts = p.footprint_2d()
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        assert min(xs) == pytest.approx(5.0 - 0.15)
        assert max(xs) == pytest.approx(5.0 + 0.15)
        assert min(ys) == pytest.approx(3.0 - 0.25)
        assert max(ys) == pytest.approx(3.0 + 0.25)

    # --- footprint_2d — 90° rotation at origin ----------------------------
    def test_footprint_2d_90_degrees_at_origin(self):
        """A 30×50 cm pilar rotated 90° → long axis now horizontal.

        Before rotation (angulo=0):
          half-x = 0.15, half-y = 0.25
          corners ≈ (±0.15, ±0.25)

        After 90° CCW rotation:
          x' = x·cos90 − y·sin90 = −y
          y' = x·sin90 + y·cos90 = +x
          So each (cx, cy) → (−cy, cx)
          corners → (∓0.25, ±0.15)
          i.e. half-x = 0.25, half-y = 0.15
        """
        from badgercad.core.elements.pilar import Pilar
        p = Pilar(x=0.0, y=0.0, ancho=0.30, largo=0.50, angulo=90.0)
        verts = p.footprint_2d()
        assert len(verts) == 4
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        # After 90° rotation the long dimension (0.50) spans X, short (0.30) spans Y
        assert min(xs) == pytest.approx(-0.25, abs=1e-9)
        assert max(xs) == pytest.approx(+0.25, abs=1e-9)
        assert min(ys) == pytest.approx(-0.15, abs=1e-9)
        assert max(ys) == pytest.approx(+0.15, abs=1e-9)

    def test_footprint_2d_45_degrees_diagonal(self):
        """A square pilar rotated 45° must have a diamond footprint."""
        from badgercad.core.elements.pilar import Pilar
        # 0.4×0.4 at origin, 45°
        p = Pilar(x=0.0, y=0.0, ancho=0.4, largo=0.4, angulo=45.0)
        verts = p.footprint_2d()
        # All 4 corners must lie on a circle of radius half_diagonal = 0.2√2
        r = 0.2 * math.sqrt(2)
        for vx, vy in verts:
            dist = math.sqrt(vx ** 2 + vy ** 2)
            assert dist == pytest.approx(r, abs=1e-9)

    def test_footprint_2d_360_is_identity(self):
        """Rotating by 360° must produce the same footprint as 0°."""
        from badgercad.core.elements.pilar import Pilar
        p0   = Pilar(x=1.0, y=2.0, ancho=0.3, largo=0.5, angulo=0.0)
        p360 = Pilar(x=1.0, y=2.0, ancho=0.3, largo=0.5, angulo=360.0)
        for (x0, y0), (x1, y1) in zip(p0.footprint_2d(), p360.footprint_2d()):
            assert x0 == pytest.approx(x1, abs=1e-9)
            assert y0 == pytest.approx(y1, abs=1e-9)

    def test_footprint_2d_shapely_compatible(self):
        """footprint_2d output must be accepted by shapely.Polygon without error."""
        pytest.importorskip("shapely", reason="Shapely not installed — skip")
        from shapely.geometry import Polygon
        from badgercad.core.elements.pilar import Pilar
        p = Pilar(x=3.0, y=4.0, ancho=0.3, largo=0.5, angulo=30.0)
        poly = Polygon(p.footprint_2d())
        assert poly.is_valid
        assert poly.area == pytest.approx(0.3 * 0.5, abs=1e-9)

    def test_seccion_label(self):
        from badgercad.core.elements.pilar import Pilar
        p = Pilar(x=0.0, y=0.0, ancho=0.30, largo=0.40)
        assert p.seccion_label == "30x40"


# ===========================================================================
# 5. Losa Geometry
# ===========================================================================
class TestLosaGeometry:
    """is_valid and area_aproximada using the Shoelace formula."""

    def test_is_valid_with_3_vertices(self):
        from badgercad.core.elements.losa import Losa
        lo = Losa(vertices=[(0, 0), (1, 0), (0, 1)])
        assert lo.is_valid() is True

    def test_is_not_valid_with_fewer_than_3_vertices(self):
        from badgercad.core.elements.losa import Losa
        assert Losa(vertices=[]).is_valid() is False
        assert Losa(vertices=[(0, 0)]).is_valid() is False
        assert Losa(vertices=[(0, 0), (1, 0)]).is_valid() is False

    def test_area_unit_square(self):
        """CCW unit square: area = 1.0 m²."""
        from badgercad.core.elements.losa import Losa
        lo = Losa(vertices=[(0, 0), (1, 0), (1, 1), (0, 1)])
        assert lo.area_aproximada() == pytest.approx(1.0)

    def test_area_known_rectangle(self):
        """3 × 5 rectangle: area = 15.0 m²."""
        from badgercad.core.elements.losa import Losa
        lo = Losa(vertices=[(0, 0), (5, 0), (5, 3), (0, 3)])
        assert lo.area_aproximada() == pytest.approx(15.0)

    def test_area_right_triangle(self):
        """Right triangle with legs 3 and 4: area = 6.0 m²."""
        from badgercad.core.elements.losa import Losa
        lo = Losa(vertices=[(0, 0), (4, 0), (0, 3)])
        assert lo.area_aproximada() == pytest.approx(6.0)

    def test_area_degenerate_returns_zero(self):
        from badgercad.core.elements.losa import Losa
        lo = Losa(vertices=[(0, 0), (1, 0)])
        assert lo.area_aproximada() == pytest.approx(0.0)

    def test_area_is_positive_for_cw_and_ccw(self):
        """Shoelace result must be positive regardless of winding order."""
        from badgercad.core.elements.losa import Losa
        ccw = Losa(vertices=[(0, 0), (2, 0), (2, 2), (0, 2)])
        cw  = Losa(vertices=[(0, 0), (0, 2), (2, 2), (2, 0)])
        assert ccw.area_aproximada() == pytest.approx(4.0)
        assert cw.area_aproximada()  == pytest.approx(4.0)


# ===========================================================================
# 6. Nivel Ordering
# ===========================================================================
class TestNivelOrdering:
    def test_niveles_ordenados_bottom_up(self, project):
        """niveles_ordenados() must return levels sorted by ascending cota."""
        from badgercad.core.elements.nivel import Nivel
        # Default order from _crear_estructura_inicial: cotas 0, 3.5, 7, 10.5
        cotas = [n.cota for n in project.niveles_ordenados()]
        assert cotas == sorted(cotas)

    def test_niveles_ordenados_after_insert(self, project):
        """Adding a nivel out of cota order must still return a sorted list."""
        from badgercad.core.elements.nivel import Nivel
        project.add_nivel(Nivel("Sotano", -3.0))
        cotas = [n.cota for n in project.niveles_ordenados()]
        assert cotas == sorted(cotas)

    def test_nivel_lt_operator(self):
        from badgercad.core.elements.nivel import Nivel
        n1 = Nivel("A", 0.0)
        n2 = Nivel("B", 3.5)
        assert n1 < n2
        assert not n2 < n1


# ===========================================================================
# 7. Project stats
# ===========================================================================
class TestProjectStats:
    def test_stats_initial_values(self, project):
        s = project.stats()
        assert s["niveles"] == 4
        assert s["grupos"] == 2
        assert s["pilares"] == 0
        assert s["losas"] == 0

    def test_stats_after_add_pilar(self, project):
        from badgercad.core.elements.pilar import Pilar
        n = project.niveles_ordenados()
        project.add_pilar(Pilar(x=0.0, y=0.0,
                                nivel_desde_id=n[0].id,
                                nivel_hasta_id=n[1].id))
        assert project.stats()["pilares"] == 1
