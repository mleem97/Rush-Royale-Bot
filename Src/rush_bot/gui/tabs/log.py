"""
RushBot GUI - Log Tab
Real-time log display with filtering.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from rush_bot.gui.theme import COLORS

if TYPE_CHECKING:
    from rush_bot.gui.content import ContentFrame


class LogTab(ctk.CTkFrame):
    """Log display tab with real-time updates."""

    def __init__(self, parent: ctk.CTkFrame, master_content: ContentFrame, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.master_content = master_content
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_log_display()

    def _create_log_display(self) -> None:
        """Create log text widget."""
        # Log text area
        self.log_text = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
            state="disabled",
        )
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Configure tags for colored log levels
        # Note: CTkTextbox doesn't support tags the same way as Tkinter
        # This is a placeholder for future implementation

    def append_log(self, message: str, level: str = "INFO") -> None:
        """Append a log message to the display."""
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{level}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear_log(self) -> None:
        """Clear all log messages."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
