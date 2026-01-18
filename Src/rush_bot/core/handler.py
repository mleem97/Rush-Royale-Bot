"""
RushBot Core - Bot Handler
Manages bot lifecycle and threading.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rush_bot.gui.main_window import RushBotApp


class BotHandler:
    """Handles bot lifecycle and execution."""

    @staticmethod
    def run(gui: RushBotApp) -> None:
        """Run the bot in a loop.

        Args:
            gui: GUI instance for feedback and control.
        """
        from rush_bot.core import Bot

        bot = Bot(gui)
        gui.bot_instance = bot

        try:
            while not gui.stop_flag:
                # Main bot loop
                # Implementation will be migrated from Src/bot_handler.py
                time.sleep(0.1)
        except Exception as e:
            if hasattr(gui, "logger"):
                gui.logger.error(f"Bot error: {e}")
        finally:
            gui.running = False
            bot.stop()

    @staticmethod
    def select_units(unit_files: list[str]) -> bool:
        """Load and validate unit icon files.

        Args:
            unit_files: List of unit icon filenames.

        Returns:
            True if all units loaded successfully.
        """
        from rush_bot import UNITS_DIR

        for unit_file in unit_files:
            unit_path = UNITS_DIR / unit_file
            if not unit_path.exists():
                return False
        return True
