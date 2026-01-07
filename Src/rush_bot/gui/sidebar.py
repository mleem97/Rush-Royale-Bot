"""
RushBot GUI - Sidebar Frame
Left navigation sidebar with controls and settings.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from rush_bot.gui.theme import COLORS

if TYPE_CHECKING:
    from rush_bot.gui.main_window import RushBotApp


class SidebarFrame(ctk.CTkFrame):
    """Left sidebar with controls and settings."""

    def __init__(self, master: RushBotApp, **kwargs) -> None:
        super().__init__(master, corner_radius=0, fg_color=COLORS["sidebar_bg"], **kwargs)
        self.master_app = master

        # Configure grid
        self.grid_rowconfigure(10, weight=1)  # Spacer row
        self.grid_columnconfigure(0, weight=1)

        self._create_header()
        self._create_controls()
        self._create_options()
        self._create_appearance_setting()

    def _create_header(self) -> None:
        """Create sidebar header with logo."""
        logo_label = ctk.CTkLabel(
            self,
            text="🤖 RushBot",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 5))

        version_label = ctk.CTkLabel(
            self,
            text="v2026.1",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        version_label.grid(row=1, column=0, padx=20, pady=(0, 20))

    def _create_controls(self) -> None:
        """Create Start/Stop buttons."""
        self.start_button = ctk.CTkButton(
            self,
            text="▶️ Start Bot",
            command=self._on_start,
            fg_color=COLORS["success"],
            hover_color=("#16a34a", "#22c55e"),
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.start_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.stop_button = ctk.CTkButton(
            self,
            text="⏹️ Stop Bot",
            command=self._on_stop,
            fg_color=COLORS["danger"],
            hover_color=("#b91c1c", "#ef4444"),
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            state="disabled",
        )
        self.stop_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

    def _create_options(self) -> None:
        """Create game mode options."""
        # Game Mode
        mode_label = ctk.CTkLabel(
            self,
            text="Game Mode",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        mode_label.grid(row=4, column=0, padx=20, pady=(30, 5), sticky="w")

        self.game_mode_var = ctk.StringVar(value="PvE")
        self.game_mode_menu = ctk.CTkOptionMenu(
            self,
            variable=self.game_mode_var,
            values=["PvE", "PvP", "Co-op"],
            width=140,
        )
        self.game_mode_menu.grid(row=5, column=0, padx=20, pady=5, sticky="w")

        # Mana upgrades
        mana_label = ctk.CTkLabel(
            self,
            text="Mana Upgrades",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        mana_label.grid(row=6, column=0, padx=20, pady=(20, 5), sticky="w")

        mana_frame = ctk.CTkFrame(self, fg_color="transparent")
        mana_frame.grid(row=7, column=0, padx=20, pady=5, sticky="ew")

        self.mana_vars: list[ctk.BooleanVar] = []
        for i in range(5):
            var = ctk.BooleanVar(value=True)
            self.mana_vars.append(var)
            cb = ctk.CTkCheckBox(
                mana_frame,
                text=f"{i + 1}",
                variable=var,
                width=40,
                checkbox_width=20,
                checkbox_height=20,
            )
            cb.grid(row=0, column=i, padx=3, pady=5)

        # Floor setting
        floor_label = ctk.CTkLabel(
            self,
            text="Dungeon Floor",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        floor_label.grid(row=8, column=0, padx=20, pady=(20, 5), sticky="w")

        floor_frame = ctk.CTkFrame(self, fg_color="transparent")
        floor_frame.grid(row=9, column=0, padx=20, pady=5, sticky="ew")

        self.floor_entry = ctk.CTkEntry(
            floor_frame,
            width=80,
            placeholder_text="5",
            justify="center",
        )
        config = self.master_app.config
        floor_value = config.get("bot", "floor", fallback="5")
        self.floor_entry.insert(0, floor_value)
        self.floor_entry.grid(row=0, column=0, padx=5, sticky="w")

    def _create_appearance_setting(self) -> None:
        """Create appearance mode toggle."""
        appearance_label = ctk.CTkLabel(
            self,
            text="Appearance",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        appearance_label.grid(row=11, column=0, padx=20, pady=(20, 5), sticky="w")

        current_mode = ctk.get_appearance_mode()
        self.appearance_menu = ctk.CTkOptionMenu(
            self,
            values=["System", "Dark", "Light"],
            command=self._change_appearance,
            width=140,
        )
        self.appearance_menu.set(current_mode)
        self.appearance_menu.grid(row=12, column=0, padx=20, pady=5, sticky="w")

    def _on_start(self) -> None:
        """Handle start button click."""
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.master_app.start_bot()

    def _on_stop(self) -> None:
        """Handle stop button click."""
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.master_app.stop_bot()

    def _change_appearance(self, new_mode: str) -> None:
        """Change appearance mode."""
        ctk.set_appearance_mode(new_mode)
