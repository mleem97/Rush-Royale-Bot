"""
RushBot Core - Custom Logger
Colored logging with GUI integration.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import customtkinter as ctk


class BotLogger:
    """Custom logger with GUI and console output."""

    def __init__(self, log_widget: ctk.CTkTextbox | None = None) -> None:
        """Initialize logger.
        
        Args:
            log_widget: Optional CTkTextbox for GUI output.
        """
        self.log_widget = log_widget
        
        # Setup Python logger
        self.logger = logging.getLogger("RushBot")
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("[%(levelname)s] %(message)s")
            )
            self.logger.addHandler(handler)

    def _log(self, level: str, message: str) -> None:
        """Internal log method.
        
        Args:
            level: Log level name.
            message: Log message.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"
        
        # Console output
        getattr(self.logger, level.lower(), self.logger.info)(message)
        
        # GUI output
        if self.log_widget:
            try:
                self.log_widget.configure(state="normal")
                self.log_widget.insert("end", formatted + "\n")
                self.log_widget.see("end")
                self.log_widget.configure(state="disabled")
            except Exception:
                pass

    def debug(self, message: str) -> None:
        """Log debug message."""
        self._log("DEBUG", message)

    def info(self, message: str) -> None:
        """Log info message."""
        self._log("INFO", message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self._log("WARNING", message)

    def error(self, message: str) -> None:
        """Log error message."""
        self._log("ERROR", message)

    def critical(self, message: str) -> None:
        """Log critical message."""
        self._log("CRITICAL", message)
