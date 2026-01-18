"""
RushBot Core - Bot Logic
Main bot class handling game automation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import pandas as pd

if TYPE_CHECKING:
    from rush_bot.gui.main_window import RushBotApp


class Bot:
    """Main bot class for Rush Royale automation."""

    def __init__(self, gui: RushBotApp | None = None) -> None:
        """Initialize the bot.

        Args:
            gui: Optional GUI instance for visual feedback.
        """
        self.gui = gui
        self.running = False
        self.grid_df: pd.DataFrame | None = None

        # Import device manager
        from rush_bot.core.device import DeviceManager

        self.device = DeviceManager()

    def start(self) -> None:
        """Start the bot automation loop."""
        self.running = True
        # Implementation will be migrated from Src/bot_core.py

    def stop(self) -> None:
        """Stop the bot."""
        self.running = False

    def tap(self, x: int, y: int) -> None:
        """Tap at screen coordinates.

        Args:
            x: X coordinate.
            y: Y coordinate.
        """
        self.device.tap(x, y)

    def swipe(self, start: tuple[int, int], end: tuple[int, int], duration_ms: int = 300) -> None:
        """Swipe from start to end coordinates.

        Args:
            start: Start (x, y) coordinates.
            end: End (x, y) coordinates.
            duration_ms: Swipe duration in milliseconds.
        """
        self.device.swipe(start[0], start[1], end[0], end[1], duration_ms)

    def screenshot(self) -> Any:
        """Capture current screen.

        Returns:
            Screenshot as numpy array or PIL Image.
        """
        return self.device.screenshot()
