"""base_tool.py — Abstract base class for all CAD drawing tools."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyvistaqt import QtInteractor


class BaseTool(ABC):
    """All CAD tools (PilarTool, LosaTool, …) derive from this class.

    The canvas calls the five hook methods below; each tool overrides only
    the ones it needs.  The canvas owns a single ``active_tool`` reference;
    swapping tools is as simple as replacing that reference.

    ESC Contract
    ------------
    Pressing ESC must **always** result in a full deactivation:
    the tool clears any in-progress geometry, removes ghost actors,
    and calls ``self._canvas.deactivate_tool()`` which:
      1. calls ``self.deactivate()`` for cleanup
      2. sets ``_active_tool = None``
      3. emits ``tool_deactivated`` so the Ribbon unchecks its buttons
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
        """Called when the tool is replaced or ESC is pressed.
        Override to clean up actors and reset internal state.
        """

    # ------------------------------------------------------------------ events
    def on_mouse_move(self, world_x: float, world_y: float) -> None:
        """Called every time the mouse moves over the canvas (world coords)."""

    def on_left_click(self, world_x: float, world_y: float) -> None:
        """Called on left mouse button press (world coords)."""

    def on_right_click(self, world_x: float, world_y: float) -> None:
        """Called on right mouse button press (world coords).

        Default behaviour: finish/confirm current operation (like ENTER).
        Override for tool-specific right-click semantics.
        """
        # Default: treat right-click the same as pressing ENTER
        self.on_key_press("Return")

    def on_key_press(self, key: str) -> None:
        """Called when a keyboard key is pressed while this tool is active.

        Subclasses should handle at minimum:
            - "Return" / "Enter"  → confirm / close geometry
            - "Escape"            → abort and fully deactivate
        """

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
        """Snap world coordinates to grid, respecting canvas.snap_enabled."""
        if not self._canvas.snap_enabled:
            return (x, y)
        from badgercad.cad.grid import snap_to_grid
        return snap_to_grid(x, y, self.grid_spacing)

    def _refresh(self) -> None:
        """Re-render the canvas 2D scene."""
        self._canvas.refresh_scene()

    @property
    def name(self) -> str:
        return self.__class__.__name__
