"""
RushBot GUI - Main Window
Modern CustomTkinter Interface with sidebar navigation.
"""
from __future__ import annotations

import configparser
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from rush_bot import PROJECT_ROOT
from rush_bot.gui.theme import COLORS, setup_theme
from rush_bot.gui.sidebar import SidebarFrame
from rush_bot.gui.content import ContentFrame

if TYPE_CHECKING:
    from rush_bot.core import Bot


# =============================================================================
# Main Application
# =============================================================================


class RushBotApp(ctk.CTk):
    """Modern Rush Royale Bot GUI with CustomTkinter."""

    def __init__(self) -> None:
        super().__init__()

        # State variables
        self.stop_flag: bool = False
        self.running: bool = False
        self.info_ready: threading.Event = threading.Event()
        self.bot_instance: Bot | None = None
        self.thread_run: threading.Thread | None = None

        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read(PROJECT_ROOT / "config.ini")

        # Window setup
        self._setup_window()
        self._create_layout()
        self._setup_logger()

        self.logger.debug("Modern GUI started!")

    def _setup_window(self) -> None:
        """Configure main window properties."""
        self.title("RushBot - Rush Royale Automation")
        self.geometry("1280x800")
        self.minsize(1024, 700)

        # Configure grid layout (1x2: sidebar | content)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)  # Sidebar fixed width
        self.grid_columnconfigure(1, weight=1)  # Content expands

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_layout(self) -> None:
        """Create the main layout with sidebar and content area."""
        # Sidebar (fixed width)
        self.sidebar = SidebarFrame(self, width=220)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Content area (expandable)
        self.content = ContentFrame(self)
        self.content.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    def _setup_logger(self) -> None:
        """Initialize logging system."""
        # Import here to avoid circular imports
        from rush_bot.core.logger import BotLogger
        
        self.logger = BotLogger(
            log_widget=self.content.log_frame.log_text if hasattr(self.content, 'log_frame') else None
        )

    def _on_closing(self) -> None:
        """Handle application close."""
        if self.running:
            self.stop_flag = True
            if self.thread_run and self.thread_run.is_alive():
                self.thread_run.join(timeout=2.0)
        self.destroy()

    def start_bot(self) -> None:
        """Start the bot in a separate thread."""
        if self.running:
            self.logger.warning("Bot is already running!")
            return

        self.stop_flag = False
        self.running = True
        
        # Import here to avoid circular imports
        from rush_bot.core import BotHandler
        
        self.thread_run = threading.Thread(
            target=BotHandler.run,
            args=(self,),
            daemon=True
        )
        self.thread_run.start()
        self.logger.info("Bot started!")

    def stop_bot(self) -> None:
        """Stop the running bot."""
        if not self.running:
            self.logger.warning("Bot is not running!")
            return

        self.stop_flag = True
        self.logger.info("Stopping bot...")

    def update_grid(
        self,
        grid_df,
        combat: int,
        step: int,
        output: str
    ) -> None:
        """Update the visual grid on the dashboard."""
        if hasattr(self.content, 'update_grid'):
            self.content.update_grid(grid_df, combat, step, output)


def main() -> None:
    """Entry point for the RushBot GUI."""
    setup_theme()
    app = RushBotApp()
    app.mainloop()


if __name__ == "__main__":
    main()
