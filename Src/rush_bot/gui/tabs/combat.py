"""
RushBot GUI - Combat Info Tab
Display combat statistics and game state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from rush_bot.gui.theme import COLORS

if TYPE_CHECKING:
    from rush_bot.gui.content import ContentFrame


class CombatTab(ctk.CTkFrame):
    """Combat information display tab."""

    def __init__(self, parent: ctk.CTkFrame, master_content: ContentFrame, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.master_content = master_content

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_combat_info()

    def _create_combat_info(self) -> None:
        """Create combat info display."""
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        info_frame.grid_columnconfigure(1, weight=1)

        # Stats labels
        stats = [
            ("Combats:", "0"),
            ("Win Rate:", "-"),
            ("Avg. Duration:", "-"),
            ("Units Merged:", "0"),
            ("Mana Used:", "0"),
        ]

        for i, (label, value) in enumerate(stats):
            lbl = ctk.CTkLabel(
                info_frame,
                text=label,
                font=ctk.CTkFont(size=14, weight="bold"),
            )
            lbl.grid(row=i, column=0, padx=20, pady=10, sticky="w")

            val = ctk.CTkLabel(
                info_frame,
                text=value,
                font=ctk.CTkFont(size=14),
                text_color=COLORS["text_secondary"],
            )
            val.grid(row=i, column=1, padx=20, pady=10, sticky="w")
