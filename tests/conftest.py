"""conftest.py — Shared pytest configuration for the BadgerCAD test suite.

Sets platform to offscreen so Qt/PyVista never attempt to open a display,
which is required both on CI machines and when running locally without
a Wayland/X11/Win32 display attached to the test process.
"""
import os
import sys

# ── Headless Qt (must be set BEFORE any PyQt6 import) ───────────────────────
os.environ.setdefault("QT_API",          "pyqt6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
