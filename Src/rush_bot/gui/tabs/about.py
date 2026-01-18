"""
RushBot GUI - About Tab
Application information and credits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from rush_bot import __version__
from rush_bot.gui.theme import COLORS

if TYPE_CHECKING:
    from rush_bot.gui.content import ContentFrame


class AboutTab(ctk.CTkFrame):
    """About and credits tab."""

    def __init__(self, parent: ctk.CTkFrame, master_content: ContentFrame, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.master_content = master_content

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_about_info()

    def _create_about_info(self) -> None:
        """Create about information display."""
        about_frame = ctk.CTkFrame(self)
        about_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        # Title
        title = ctk.CTkLabel(
            about_frame,
            text="🤖 RushBot",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.pack(pady=(30, 10))

        # Version
        version = ctk.CTkLabel(
            about_frame,
            text=f"Version {__version__}",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"],
        )
        version.pack(pady=5)

        # Description
        desc = ctk.CTkLabel(
            about_frame,
            text="Automated Bot for Rush Royale\nwith ML-based unit recognition",
            font=ctk.CTkFont(size=13),
            justify="center",
        )
        desc.pack(pady=20)

        # Links
        links_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        links_frame.pack(pady=20)

        github_btn = ctk.CTkButton(
            links_frame,
            text="📦 GitHub",
            command=lambda: self._open_url("https://github.com/mleem97/RushBot"),
            width=120,
        )
        github_btn.grid(row=0, column=0, padx=10)

        wiki_btn = ctk.CTkButton(
            links_frame,
            text="📚 Wiki",
            command=lambda: self._open_url("https://rushbot.wiki"),
            width=120,
        )
        wiki_btn.grid(row=0, column=1, padx=10)

    def _open_url(self, url: str) -> None:
        """Open URL in browser."""
        import webbrowser

        webbrowser.open(url)
