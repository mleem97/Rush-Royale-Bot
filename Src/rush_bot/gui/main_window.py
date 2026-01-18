"""
RushBot GUI - Main Window
Modern CustomTkinter Interface with sidebar navigation.
"""

from __future__ import annotations

import configparser
import threading
from typing import Any

import customtkinter as ctk

from rush_bot import PROJECT_ROOT
from rush_bot.gui.content import ContentFrame
from rush_bot.gui.sidebar import SidebarFrame
from rush_bot.gui.theme import setup_theme

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
        # Note: bot_instance can be either the new Bot class or legacy bot_core.Bot
        # Using Any to accommodate both during migration period
        self.bot_instance: Any = None
        self.thread_run: threading.Thread | None = None

        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read(PROJECT_ROOT / "config.ini")

        # Window setup
        self._setup_window()
        self._create_layout()
        self._setup_logger()

        self.logger.debug("Modern GUI started!")

        # Start ADB monitoring after GUI is ready
        self.after(500, self.sidebar.start_adb_monitoring)

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
            log_widget=self.content.log_frame.log_text
            if hasattr(self.content, "log_frame")
            else None
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

        # Use the legacy bot_handler which has full implementation
        import sys

        from rush_bot import PROJECT_ROOT

        # Add Src to path to use legacy modules
        src_path = PROJECT_ROOT / "Src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        try:
            import bot_handler

            # Get game mode from sidebar
            game_mode = self.sidebar.game_mode_var.get()
            floor = self.sidebar.floor_entry.get() or "5"

            # Update config based on GUI selections
            if game_mode == "PvP":
                self.config.set("bot", "pve", "false")
            else:
                self.config.set("bot", "pve", "true")
            self.config.set("bot", "floor", floor)

            # Get mana upgrades from checkboxes
            mana_levels = [str(i + 1) for i, var in enumerate(self.sidebar.mana_vars) if var.get()]
            self.config.set(
                "bot", "mana_level", ",".join(mana_levels) if mana_levels else "1,2,3,4,5"
            )

            # Check ADB connection first
            if not bot_handler.check_adb_connection(self.logger):
                self.logger.error("No ADB device found! Make sure emulator is running.")
                self.running = False
                self.sidebar.start_button.configure(state="normal")
                self.sidebar.stop_button.configure(state="disabled")
                return

            # Select units from config
            units = [
                self.config.get("bot", f"unit_{i}", fallback=f"empty_{i}.png") for i in range(1, 6)
            ]
            if not bot_handler.select_units(units):
                self.logger.warning("Some units not found, continuing anyway...")

            # Start the bot
            self.bot_instance = bot_handler.start_bot_class(self.logger)
            self.bot_instance.bot_stop = False

            # Run bot loop in thread
            def run_legacy_bot():
                try:
                    bot_handler.bot_loop(self.bot_instance, self.info_ready)
                except Exception as e:
                    self.logger.error(f"Bot error: {e}")
                finally:
                    self.running = False
                    self.after(0, lambda: self.sidebar.start_button.configure(state="normal"))
                    self.after(0, lambda: self.sidebar.stop_button.configure(state="disabled"))

            self.thread_run = threading.Thread(target=run_legacy_bot, daemon=True)
            self.thread_run.start()
            self.logger.info(f"Bot started in {game_mode} mode!")

        except ImportError as e:
            self.logger.error(f"Failed to import legacy modules: {e}")
            self.running = False
            self.sidebar.start_button.configure(state="normal")
            self.sidebar.stop_button.configure(state="disabled")

    def stop_bot(self) -> None:
        """Stop the running bot."""
        if not self.running:
            self.logger.warning("Bot is not running!")
            return

        self.stop_flag = True

        # Stop the legacy bot instance
        if self.bot_instance is not None:
            self.bot_instance.bot_stop = True

        self.logger.info("Stopping bot...")

    def update_grid(self, grid_df, combat: int, step: int, output: str) -> None:
        """Update the visual grid on the dashboard."""
        if hasattr(self.content, "update_grid"):
            self.content.update_grid(grid_df, combat, step, output)


def main() -> None:
    """Entry point for the RushBot GUI."""
    setup_theme()
    app = RushBotApp()
    app.mainloop()


if __name__ == "__main__":
    main()
