"""
RushBot GUI - Config Tab
Unit selection and bot configuration.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from rush_bot import CV_IMAGES_DIR
from rush_bot.gui.theme import COLORS

if TYPE_CHECKING:
    from rush_bot.gui.content import ContentFrame


class ConfigTab(ctk.CTkFrame):
    """Configuration tab for unit selection and settings."""

    def __init__(self, parent: ctk.CTkFrame, master_content: ContentFrame, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.master_content = master_content
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_header()
        self._create_unit_selection()
        self._create_save_button()

    def _create_header(self) -> None:
        """Create section header."""
        header = ctk.CTkLabel(
            self,
            text="Unit-Auswahl",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

    def _create_unit_selection(self) -> None:
        """Create unit selection dropdowns."""
        units_frame = ctk.CTkFrame(self)
        units_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        # Load available units
        self.available_units = self._load_available_units()

        # Load current selection from config
        config = self.master_content.master.config
        current_units = config.get(
            "bot", "units",
            fallback="demon_hunter,dryad,harlequin,chemist,knight_statue"
        ).replace(" ", "").split(",")

        # Extend to 5 slots
        while len(current_units) < 5:
            current_units.append(self.available_units[0] if self.available_units else "empty")

        # Create 5 unit dropdowns
        self.unit_vars: list[ctk.StringVar] = []
        unit_labels = [
            f"Slot {i+1}: {u.replace('_', ' ').title()}"
            for i, u in enumerate(current_units[:5])
        ]

        for i in range(5):
            row_frame = ctk.CTkFrame(units_frame, fg_color="transparent")
            row_frame.grid(row=i, column=0, sticky="ew", padx=10, pady=8)
            row_frame.grid_columnconfigure(1, weight=1)

            lbl = ctk.CTkLabel(
                row_frame,
                text=unit_labels[i],
                font=ctk.CTkFont(size=13, weight="bold"),
                width=180,
                anchor="w",
            )
            lbl.grid(row=0, column=0, padx=(0, 10), sticky="w")

            var = ctk.StringVar(value=current_units[i] if i < len(current_units) else "empty")
            self.unit_vars.append(var)

            dropdown = ctk.CTkOptionMenu(
                row_frame,
                variable=var,
                values=self.available_units,
                width=200,
                dynamic_resizing=False,
            )
            dropdown.grid(row=0, column=1, sticky="w")

    def _create_save_button(self) -> None:
        """Create save configuration button."""
        save_btn = ctk.CTkButton(
            self,
            text="💾 Konfiguration speichern",
            command=self._save_config,
            fg_color=COLORS["success"],
            hover_color=("#16a34a", "#22c55e"),
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        save_btn.grid(row=2, column=0, padx=20, pady=20, sticky="ew")

    def _load_available_units(self) -> list[str]:
        """Load available unit names from cv-images folder."""
        units_dir = CV_IMAGES_DIR / "all_units"
        if not units_dir.exists():
            # Fallback to old location
            units_dir = Path("all_units")
        
        if units_dir.exists():
            units = [
                f.stem for f in units_dir.glob("*.png")
                if not f.stem.startswith(".")
            ]
            return sorted(units)
        return ["demon_hunter", "dryad", "harlequin", "chemist", "knight_statue"]

    def _save_config(self) -> None:
        """Save unit configuration to config.ini."""
        config = self.master_content.master.config
        
        # Get selected units
        units = [var.get() for var in self.unit_vars]
        units_str = ", ".join(units)
        
        if "bot" not in config:
            config.add_section("bot")
        config.set("bot", "units", units_str)
        
        # Write to file
        from rush_bot import PROJECT_ROOT
        with open(PROJECT_ROOT / "config.ini", "w") as f:
            config.write(f)
        
        # Show success message
        self.master_content.master.logger.info(f"Configuration saved: {units_str}")
