"""
RushBot GUI - Dashboard Tab
Visual 3x5 grid showing unit positions and status.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk
import pandas as pd

from rush_bot.gui.theme import COLORS

if TYPE_CHECKING:
    from rush_bot.gui.content import ContentFrame

# Fixed slot colors (1-5) - consistent colors per column position
SLOT_COLORS = [
    "#E74C3C",  # Slot 1 - Red
    "#3498DB",  # Slot 2 - Blue
    "#2ECC71",  # Slot 3 - Green
    "#F39C12",  # Slot 4 - Orange
    "#9B59B6",  # Slot 5 - Purple
]


class DashboardTab(ctk.CTkFrame):
    """Visual 3x5 grid dashboard showing current game state."""

    def __init__(self, parent: ctk.CTkFrame, master_content: ContentFrame, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.master_content = master_content

        # Configure grid
        self.grid_rowconfigure(0, weight=0)  # Status row
        self.grid_rowconfigure(1, weight=1)  # Grid row
        self.grid_rowconfigure(2, weight=0)  # Legend row
        self.grid_columnconfigure(0, weight=1)

        self._create_status_bar()
        self._create_grid()
        self._create_legend()

    def _create_status_bar(self) -> None:
        """Create status bar with combat info."""
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.status_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.status_combat = ctk.CTkLabel(
            self.status_frame, text="Combat: -", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.status_combat.grid(row=0, column=0, padx=10, pady=5)

        self.status_step = ctk.CTkLabel(
            self.status_frame, text="Step: -/8", font=ctk.CTkFont(size=14)
        )
        self.status_step.grid(row=0, column=1, padx=10, pady=5)

        self.status_state = ctk.CTkLabel(
            self.status_frame, text="State: Idle", font=ctk.CTkFont(size=14)
        )
        self.status_state.grid(row=0, column=2, padx=10, pady=5)

        self.status_dps = ctk.CTkLabel(
            self.status_frame, text="DPS Ranks: 0", font=ctk.CTkFont(size=14)
        )
        self.status_dps.grid(row=0, column=3, padx=10, pady=5)

    def _create_grid(self) -> None:
        """Create the 3x5 visual grid with fixed slot colors."""
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Configure grid weights for even distribution
        for r in range(3):
            self.grid_frame.grid_rowconfigure(r, weight=1)
        for c in range(5):
            self.grid_frame.grid_columnconfigure(c, weight=1)

        # Create 15 grid cells (3 rows x 5 columns)
        self.grid_cells: list[list[dict]] = []
        for row in range(3):
            row_cells = []
            for col in range(5):
                # Fixed color per slot (column) position
                slot_color = SLOT_COLORS[col]

                cell_frame = ctk.CTkFrame(
                    self.grid_frame,
                    corner_radius=10,
                    fg_color=COLORS["unit_empty"],
                    border_width=3,
                    border_color=slot_color,
                )
                cell_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
                cell_frame.grid_rowconfigure(0, weight=1)
                cell_frame.grid_columnconfigure(0, weight=1)

                # Merge Level label (centered, bold)
                merge_label = ctk.CTkLabel(
                    cell_frame,
                    text="?",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=COLORS["text_primary"],
                )
                merge_label.grid(row=0, column=0, padx=5, pady=8, sticky="nsew")

                cell_data = {
                    "frame": cell_frame,
                    "merge": merge_label,
                    "slot_color": slot_color,
                }
                row_cells.append(cell_data)
            self.grid_cells.append(row_cells)

    def _create_legend(self) -> None:
        """Create unit legend with slot colors based on config."""
        self.legend_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.legend_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        # Store legend labels for updates
        self.legend_labels: list[ctk.CTkLabel] = []

        # Get units from config
        config = self.master_content.master.config
        config_units = (
            config.get(
                "bot", "units", fallback="demon_hunter,dryad,harlequin,chemist,knight_statue"
            )
            .replace(" ", "")
            .split(",")
        )

        # Ensure we have 5 slots
        while len(config_units) < 5:
            config_units.append("empty")
        legend_units = config_units[:5]

        for i, unit in enumerate(legend_units):
            slot_color = SLOT_COLORS[i]
            display_name = unit.replace("_", " ").title() if unit != "empty" else "Empty"
            lbl = ctk.CTkLabel(
                self.legend_frame,
                text=f"● Slot {i + 1}: {display_name}",
                text_color=slot_color,
                font=ctk.CTkFont(size=11, weight="bold"),
            )
            lbl.grid(row=0, column=i, padx=8)
            self.legend_labels.append(lbl)

    def update_legend(self, units: list[str] | None = None) -> None:
        """Update legend with detected or config units."""
        if units is None:
            # Read from config
            config = self.master_content.master.config
            units_str = config.get(
                "bot", "units", fallback="demon_hunter,dryad,harlequin,chemist,knight_statue"
            ).replace(" ", "")
            units = units_str.split(",")

        # Ensure we have 5 slots
        while len(units) < 5:
            units.append("empty")

        for i, unit in enumerate(units[:5]):
            if i < len(self.legend_labels):
                display_name = unit.replace("_", " ").title() if unit != "empty" else "Empty"
                self.legend_labels[i].configure(text=f"● Slot {i + 1}: {display_name}")

    def update(self, grid_df: pd.DataFrame | None, combat: int, step: int, output: str) -> None:
        """Update the dashboard with new game state."""
        # Update status
        self.status_combat.configure(text=f"Combat: {combat}")
        self.status_step.configure(text=f"Step: {step + 1}/8")
        self.status_state.configure(text=f"State: {output}")

        if grid_df is None:
            return

        # Process grid data
        df = grid_df.copy()
        df["unit"] = df["unit"].str.replace(".png", "", regex=False)

        # Calculate DPS ranks
        num_demons = df[df["unit"] == "demon_hunter"]["rank"].sum()
        self.status_dps.configure(text=f"DPS Ranks: {num_demons}")

        # Update grid cells
        for idx, row in df.iterrows():
            grid_row = idx // 5
            grid_col = idx % 5

            unit_name = row["unit"]
            rank = row.get("rank", 0)

            # Get cell with fixed slot color
            cell = self.grid_cells[grid_row][grid_col]
            slot_color = cell["slot_color"]

            # Format display: "Merge LVL: X" or "?" for empty
            if unit_name in ("empty", "-"):
                merge_text = "?"
                fg_color = COLORS["unit_empty"]
            else:
                merge_text = f"Merge LVL: {min(rank, 7)}" if rank > 0 else "Merge LVL: ?"
                # Use lighter version of slot color for filled cells
                fg_color = slot_color + "40"  # Add alpha for lighter shade

            # Update cell
            cell["frame"].configure(fg_color=fg_color)
            cell["merge"].configure(text=merge_text)
