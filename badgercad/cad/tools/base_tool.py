"""base_tool.py — Abstract base class for all CAD drawing tools."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyvistaqt import QtInteractor


class BaseTool(ABC):
    """All CAD tools (PilarTool, LosaTool, …) derive from this class.

    The canvas calls the four hook methods below; each tool overrides only
    the ones it needs.  The canvas owns a single ``active_tool`` reference;
    swapping tools is as simple as replacing that reference.
    """

    def __init__(self, canvas) -> None:
        """
        Args:
            canvas: The Canvas2D instance that owns this tool.
        """
        self._canvas = canvas

    # ------------------------------------------------------------------ lifecycle
    def activate(self) -> None:
        """Called when the tool becomes active.  Override to set up state."""

    def deactivate(self) -> None:
        """Called when the tool is replaced.  Override to clean up actors."""

    # ------------------------------------------------------------------ events
    def on_mouse_move(self, world_x: float, world_y: float) -> None:
        """Called every time the mouse moves over the canvas (world coords)."""

    def on_left_click(self, world_x: float, world_y: float) -> None:
        """Called on left mouse button press (world coords)."""

    def on_key_press(self, key: str) -> None:
        """Called when a keyboard key is pressed while this tool is active."""

    # ------------------------------------------------------------------ helpers
    @property
    def plotter(self) -> "QtInteractor":
        return self._canvas.plotter

    @property
    def project(self):
        return self._canvas.project

    @property
    def grid_spacing(self) -> float:
        return self._canvas.grid_spacing

    def _snap(self, x: float, y: float) -> tuple[float, float]:
        from badgercad.cad.grid import snap_to_grid
        return snap_to_grid(x, y, self.grid_spacing)

    def _refresh(self) -> None:
        """Re-render the canvas 2D scene."""
        self._canvas.refresh_scene()

    @property
    def name(self) -> str:
        return self.__class__.__name__
