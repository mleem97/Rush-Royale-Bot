"""
RushBot GUI - Content Frame
Main content area with tabbed interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk
import pandas as pd

from rush_bot.gui.tabs import AboutTab
from rush_bot.gui.tabs import CombatTab
from rush_bot.gui.tabs import ConfigTab
from rush_bot.gui.tabs import DashboardTab
from rush_bot.gui.tabs import LogTab
from rush_bot.gui.tabs import TrainingTab
from rush_bot.gui.theme import COLORS

if TYPE_CHECKING:
    from rush_bot.gui.main_window import RushBotApp


class ContentFrame(ctk.CTkFrame):
    """Main content area with tabbed navigation."""

    def __init__(self, master: RushBotApp, **kwargs) -> None:
        super().__init__(master, fg_color=COLORS["content_bg"], **kwargs)
        self.master = master

        # Configure grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_tabview()

    def _create_tabview(self) -> None:
        """Create tabbed interface."""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Add tabs
        self.tabview.add("🎮 Dashboard")
        self.tabview.add("📊 Combat Info")
        self.tabview.add("⚙️ Konfiguration")
        self.tabview.add("🧠 Training")
        self.tabview.add("📝 Log")
        self.tabview.add("ℹ️ About")

        # Setup tab content
        self._setup_tabs()

    def _setup_tabs(self) -> None:
        """Initialize all tabs."""
        # Dashboard
        dashboard_parent = self.tabview.tab("🎮 Dashboard")
        dashboard_parent.grid_rowconfigure(0, weight=1)
        dashboard_parent.grid_columnconfigure(0, weight=1)
        self.dashboard_tab = DashboardTab(dashboard_parent, self)
        self.dashboard_tab.grid(row=0, column=0, sticky="nsew")

        # Combat Info
        combat_parent = self.tabview.tab("📊 Combat Info")
        combat_parent.grid_rowconfigure(0, weight=1)
        combat_parent.grid_columnconfigure(0, weight=1)
        self.combat_tab = CombatTab(combat_parent, self)
        self.combat_tab.grid(row=0, column=0, sticky="nsew")

        # Config
        config_parent = self.tabview.tab("⚙️ Konfiguration")
        config_parent.grid_rowconfigure(0, weight=1)
        config_parent.grid_columnconfigure(0, weight=1)
        self.config_tab = ConfigTab(config_parent, self)
        self.config_tab.grid(row=0, column=0, sticky="nsew")

        # Training
        training_parent = self.tabview.tab("🧠 Training")
        training_parent.grid_rowconfigure(0, weight=1)
        training_parent.grid_columnconfigure(0, weight=1)
        self.training_tab = TrainingTab(training_parent, self)
        self.training_tab.grid(row=0, column=0, sticky="nsew")

        # Log
        log_parent = self.tabview.tab("📝 Log")
        log_parent.grid_rowconfigure(0, weight=1)
        log_parent.grid_columnconfigure(0, weight=1)
        self.log_tab = LogTab(log_parent, self)
        self.log_tab.grid(row=0, column=0, sticky="nsew")

        # About
        about_parent = self.tabview.tab("ℹ️ About")
        about_parent.grid_rowconfigure(0, weight=1)
        about_parent.grid_columnconfigure(0, weight=1)
        self.about_tab = AboutTab(about_parent, self)
        self.about_tab.grid(row=0, column=0, sticky="nsew")

        # Store reference for logger
        self.log_frame = self.log_tab

    def update_grid(
        self, grid_df: pd.DataFrame | None, combat: int, step: int, output: str
    ) -> None:
        """Update the dashboard grid."""
        self.dashboard_tab.update(grid_df, combat, step, output)

    # Compatibility properties for old code
    @property
    def status_combat(self):
        return self.dashboard_tab.status_combat

    @property
    def status_step(self):
        return self.dashboard_tab.status_step

    @property
    def status_state(self):
        return self.dashboard_tab.status_state

    @property
    def status_dps(self):
        return self.dashboard_tab.status_dps

    @property
    def grid_cells(self):
        return self.dashboard_tab.grid_cells
