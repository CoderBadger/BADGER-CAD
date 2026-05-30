"""icon_manager.py — Centralized utility for loading QIcons with robust fallback."""
from __future__ import annotations
import os
from pathlib import Path

from PyQt6.QtGui import QIcon, QPixmap, QPainter, QFont, QColor
from PyQt6.QtCore import Qt

class IconManager:
    """Manages icon loading and dynamic generation of fallback icons."""

    _ASSETS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "assets" / "icons"
    _CACHE: dict[str, QIcon] = {}

    @classmethod
    def get_icon(cls, icon_name: str, fallback_char: str = "") -> QIcon:
        """
        Attempt to load an SVG icon. If it fails, generates a fallback QIcon using the provided character.
        
        Args:
            icon_name: The base name of the SVG file (without extension).
            fallback_char: The Unicode/Emoji character to draw if the SVG is unavailable.
        """
        cache_key = f"{icon_name}_{fallback_char}"
        if cache_key in cls._CACHE:
            return cls._CACHE[cache_key]

        icon_path = cls._ASSETS_DIR / f"{icon_name}.svg"
        
        icon = QIcon()
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            
        if icon.isNull():
            icon = cls._generate_fallback(fallback_char)
            
        cls._CACHE[cache_key] = icon
        return icon

    @staticmethod
    def _generate_fallback(char: str, size: int = 32) -> QIcon:
        """Generate a transparent QPixmap containing the text char, returned as QIcon."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        if char:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            
            font = QFont("Segoe UI Emoji", int(size * 0.5))
            font.setStyleHint(QFont.StyleHint.SansSerif)
            painter.setFont(font)
            
            painter.setPen(QColor("#A0B0C8"))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, char)
            painter.end()

        return QIcon(pixmap)
