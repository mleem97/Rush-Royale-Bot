"""
Rush Royale Bot GUI - Modern CustomTkinter Interface
Python 3.13 Compatible with Dark/Light Mode Support

Features:
- Visual 3x5 grid dashboard
- Tab-based configuration
- ML training interface
- WCAG-compliant accessibility
"""
from __future__ import annotations

import configparser
import logging
import os
import threading
from pathlib import Path
from typing import Any

import customtkinter as ctk
import numpy as np
from PIL import Image

# Internal modules
import bot_handler
import bot_logger

# =============================================================================
# Configuration
# =============================================================================

ctk.set_appearance_mode("System")  # "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

# Color palette for consistent theming (Light, Dark) - WCAG compliant
# Using #1e1e2e instead of pure black for OLED-friendly dark mode
COLORS = {
    "sidebar_bg": ("#e8e8e8", "#1e1e2e"),
    "content_bg": ("#f5f5f5", "#16213e"),
    "card_bg": ("#ffffff", "#2d3250"),
    "accent": ("#3b82f6", "#60a5fa"),
    "success": ("#16a34a", "#4ade80"),
    "warning": ("#d97706", "#fbbf24"),
    "danger": ("#dc2626", "#f87171"),
    "text_primary": ("#1f2937", "#f1f5f9"),
    "text_secondary": ("#6b7280", "#94a3b8"),
    # Unit colors for grid visualization
    "unit_empty": ("#d1d5db", "#374151"),
    "unit_demon_hunter": ("#7c3aed", "#a78bfa"),
    "unit_dryad": ("#15803d", "#4ade80"),
    "unit_harlequin": ("#db2777", "#f472b6"),
    "unit_chemist": ("#0891b2", "#22d3ee"),
    "unit_knight_statue": ("#b45309", "#fbbf24"),
    "unit_shaman": ("#7c2d12", "#fb923c"),
    "unit_default": ("#6366f1", "#818cf8"),
}

# Unit color mapping
UNIT_COLORS = {
    "demon_hunter": COLORS["unit_demon_hunter"],
    "dryad": COLORS["unit_dryad"],
    "harlequin": COLORS["unit_harlequin"],
    "chemist": COLORS["unit_chemist"],
    "knight_statue": COLORS["unit_knight_statue"],
    "shaman": COLORS["unit_shaman"],
    "empty": COLORS["unit_empty"],
}


# =============================================================================
# Main Application
# =============================================================================


class RushBotApp(ctk.CTk):
    """Modern Rush Royale Bot GUI with CustomTkinter."""

    def __init__(self):
        super().__init__()

        # State variables
        self.stop_flag = False
        self.running = False
        self.info_ready = threading.Event()
        self.bot_instance = None
        self.thread_run = None

        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")

        # Window setup
        self._setup_window()
        self._create_layout()
        self._setup_logger()

        self.logger.debug("Modern GUI started!")

    def _setup_window(self):
        """Configure main window properties."""
        self.title("Rush Royale Bot")
        self.geometry("1000x700")
        self.minsize(900, 600)

        # Try to load icon
        icon_path = Path("favicon.ico")
        if icon_path.exists():
            self.iconbitmap(str(icon_path))

        # Configure grid weights for responsiveness
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def _create_layout(self):
        """Create the main layout with sidebar and content area."""
        # Sidebar (fixed width)
        self.sidebar = SidebarFrame(self, width=240)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Main content area (expandable)
        self.content = ContentFrame(self)
        self.content.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    def _setup_logger(self):
        """Initialize logging to the log widget."""
        self.logger = bot_logger.create_log_feed(self.content.log_frame.log_text)

    # -------------------------------------------------------------------------
    # Bot Control Methods
    # -------------------------------------------------------------------------

    def start_command(self):
        """Initialize and start the bot."""
        self.stop_flag = False
        self._update_config()

        if self.running:
            self.logger.warning("Bot is already running!")
            return

        self.running = True
        self.sidebar.update_button_states(running=True)

        # Start main thread
        self.thread_run = threading.Thread(target=self._start_bot, daemon=True)
        self.thread_run.start()

    def _update_config(self):
        """Save current settings to config.ini."""
        floor_var = int(self.sidebar.floor_entry.get() or "5")
        card_level = [var.get() for var in self.sidebar.mana_vars] * np.arange(1, 6)
        card_level = card_level[card_level != 0]

        self.config.read("config.ini")
        self.config["bot"]["floor"] = str(floor_var)
        self.config["bot"]["mana_level"] = np.array2string(card_level, separator=",")[1:-1]
        self.config["bot"]["pve"] = str(bool(self.sidebar.pve_var.get()))
        self.config["bot"]["unit_update"] = str(bool(self.sidebar.unit_update_var.get()))

        with open("config.ini", "w") as configfile:
            self.config.write(configfile)

        self.logger.info("Settings saved to config!")

    def _update_units(self):
        """Load and validate unit selection from config."""
        self.selected_units = self.config["bot"]["units"].replace(" ", "").split(",")
        self.logger.info(f'Selected units: {", ".join(self.selected_units)}')

        if not bot_handler.select_units([unit + ".png" for unit in self.selected_units]):
            all_units_dir = Path("cv-images/all_units")
            valid_units = sorted(
                {
                    p.stem
                    for p in all_units_dir.rglob("*.png")
                    if p.is_file() and "missing_units" not in p.parts
                }
            )
            self.logger.warning(f"Invalid units in config! Valid: {valid_units}")

    def _start_bot(self):
        """Bot main loop (runs in thread)."""
        self.logger.warning("Starting bot...")

        try:
            self.bot_instance = bot_handler.start_bot_class(self.logger)
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            self.running = False
            self.after(0, lambda: self.sidebar.update_button_states(running=False))
            return

        # Display startup message
        startup_path = Path("src/startup_message.txt")
        if startup_path.exists():
            self.logger.info(startup_path.read_text(encoding="utf-8", errors="ignore"))

        self._update_units()

        # Pass GUI info to bot
        self.bot_instance.bot_stop = False
        self.bot_instance.logger = self.logger
        self.bot_instance.config = self.config

        infos_ready = threading.Event()
        bot = self.bot_instance

        # Start bot thread
        thread_bot = threading.Thread(
            target=bot_handler.bot_loop, args=(bot, infos_ready), daemon=True
        )
        thread_bot.start()

        # Update GUI with bot info
        while True:
            infos_ready.wait(timeout=5)
            self._update_display(
                bot.combat_step,
                bot.combat,
                bot.output,
                bot.grid_df,
                bot.unit_series,
                bot.merge_series,
                bot.info,
            )
            infos_ready.clear()

            if self.stop_flag:
                self.bot_instance.bot_stop = True
                self.logger.warning("Exiting main loop...")
                thread_bot.join(timeout=10)

                if hasattr(self.bot_instance, "scrcpy_process") and self.bot_instance.scrcpy_process:
                    self.bot_instance.stop_scrcpy()

                self.logger.info("Bot stopped!")
                self.running = False
                self.after(0, lambda: self.sidebar.update_button_states(running=False))
                return

    def stop_bot(self):
        """Signal bot to stop."""
        self.running = False
        self.stop_flag = True
        self.logger.info("Stopping bot...")
        self.sidebar.update_button_states(running=False)

    def leave_game(self):
        """Leave current co-op game."""
        if hasattr(self, "bot_instance") and self.bot_instance:
            thread_bot = threading.Thread(
                target=self.bot_instance.restart_game, args=(True,), daemon=True
            )
            thread_bot.start()
            self.logger.info("Leaving current game...")
        else:
            self.logger.warning("Bot has not been started yet!")

    def _update_display(self, i, combat, output, grid_df, unit_series, merge_series, info):
        """Update combat info display and dashboard grid."""
        # Update text-based combat info
        self.content.combat_frame.update_data(
            combat, i, output, info, grid_df, unit_series, merge_series
        )

        # Update visual dashboard grid
        self._update_dashboard_grid(combat, i, output, grid_df)

    def _update_dashboard_grid(self, combat, step, output, grid_df):
        """Update the visual 3x5 grid on the dashboard."""
        # Update status labels
        self.content.status_combat.configure(text=f"Combat: {combat}")
        self.content.status_step.configure(text=f"Step: {step + 1}/8")
        self.content.status_state.configure(text=f"State: {output}")

        if grid_df is None:
            return

        # Calculate DPS ranks
        df = grid_df.copy()
        df["unit"] = df["unit"].str.replace(".png", "", regex=False)
        num_demons = df[df["unit"] == "demon_hunter"]["rank"].sum()
        self.content.status_dps.configure(text=f"DPS Ranks: {num_demons}")

        # Update grid cells (grid_df has 15 rows, indices 0-14)
        # Layout: 3 rows x 5 cols, left-to-right, top-to-bottom
        for idx, row in df.iterrows():
            grid_row = idx // 5
            grid_col = idx % 5

            unit_name = row["unit"]
            rank = row.get("rank", 0)

            # Get color based on unit type
            if unit_name in UNIT_COLORS:
                color = UNIT_COLORS[unit_name]
            elif unit_name == "empty" or unit_name == "-":
                color = COLORS["unit_empty"]
            else:
                color = COLORS["unit_default"]

            # Format display text
            if unit_name == "empty" or unit_name == "-":
                display_name = "-"
                rank_text = ""
            else:
                # Format unit name (capitalize, replace underscores)
                display_name = unit_name.replace("_", " ").title()
                # Truncate long names
                if len(display_name) > 12:
                    display_name = display_name[:10] + "..."
                # Star rating based on rank
                rank_text = "⭐" * min(rank, 7) if rank > 0 else ""

            # Update cell components (now using dict structure)
            cell = self.content.grid_cells[grid_row][grid_col]
            cell["frame"].configure(fg_color=color)
            cell["name"].configure(text=display_name)
            cell["rank"].configure(text=rank_text)


# =============================================================================
# Sidebar Frame
# =============================================================================


class SidebarFrame(ctk.CTkFrame):
    """Left sidebar with controls and settings."""

    def __init__(self, master: RushBotApp, **kwargs):
        super().__init__(master, corner_radius=0, **kwargs)
        self.master_app = master

        # Configure grid
        self.grid_rowconfigure(10, weight=1)  # Spacer row
        self.grid_columnconfigure(0, weight=1)

        self._create_header()
        self._create_controls()
        self._create_options()
        self._create_mana_settings()
        self._create_floor_setting()
        self._create_appearance_setting()

    def _create_header(self):
        """Create logo and title."""
        # Logo/Title area
        self.logo_label = ctk.CTkLabel(
            self,
            text="🎮 Rush Royale Bot",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Subtitle
        self.subtitle = ctk.CTkLabel(
            self,
            text="Automated Gameplay Assistant",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        )
        self.subtitle.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

    def _create_controls(self):
        """Create start/stop/quit buttons."""
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=2, column=0, padx=15, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure((0, 1), weight=1)

        self.start_button = ctk.CTkButton(
            controls_frame,
            text="▶ Start Bot",
            command=self.master_app.start_command,
            fg_color=COLORS["success"],
            hover_color=("#16a34a", "#22c55e"),
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.start_button.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        self.stop_button = ctk.CTkButton(
            controls_frame,
            text="⏹ Stop",
            command=self.master_app.stop_bot,
            fg_color=COLORS["warning"],
            hover_color=("#d97706", "#f59e0b"),
            height=35,
            state="disabled",
        )
        self.stop_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.quit_button = ctk.CTkButton(
            controls_frame,
            text="🚪 Quit Floor",
            command=self.master_app.leave_game,
            fg_color=COLORS["danger"],
            hover_color=("#dc2626", "#ef4444"),
            height=35,
        )
        self.quit_button.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    def _create_options(self):
        """Create PvE and Unit Update options."""
        options_label = ctk.CTkLabel(
            self,
            text="Game Mode",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        options_label.grid(row=3, column=0, padx=20, pady=(20, 5), sticky="w")

        # Load saved values
        config = self.master_app.config
        pve_default = config.getboolean("bot", "pve", fallback=True)
        unit_update_default = config.getboolean("bot", "unit_update", fallback=False)

        self.pve_var = ctk.IntVar(value=int(pve_default))
        self.unit_update_var = ctk.IntVar(value=int(unit_update_default))

        self.pve_switch = ctk.CTkSwitch(
            self,
            text="PvE Mode (Dungeon)",
            variable=self.pve_var,
            onvalue=1,
            offvalue=0,
        )
        self.pve_switch.grid(row=4, column=0, padx=20, pady=5, sticky="w")

        self.unit_update_switch = ctk.CTkSwitch(
            self,
            text="Unit Capture Mode",
            variable=self.unit_update_var,
            onvalue=1,
            offvalue=0,
        )
        self.unit_update_switch.grid(row=5, column=0, padx=20, pady=5, sticky="w")

    def _create_mana_settings(self):
        """Create mana level target checkboxes."""
        mana_label = ctk.CTkLabel(
            self,
            text="Mana Upgrade Targets",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        mana_label.grid(row=6, column=0, padx=20, pady=(20, 5), sticky="w")

        mana_frame = ctk.CTkFrame(self, fg_color="transparent")
        mana_frame.grid(row=7, column=0, padx=15, pady=5, sticky="ew")

        # Load saved values
        config = self.master_app.config
        stored_values = np.fromstring(
            config.get("bot", "mana_level", fallback="1,3,5"), dtype=int, sep=","
        )

        self.mana_vars = []
        for i in range(5):
            var = ctk.IntVar(value=int((i + 1) in stored_values))
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

    def _create_floor_setting(self):
        """Create dungeon floor entry."""
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

        floor_hint = ctk.CTkLabel(
            floor_frame,
            text="(1-14)",
            text_color=COLORS["text_secondary"],
        )
        floor_hint.grid(row=0, column=1, padx=5, sticky="w")

    def _create_appearance_setting(self):
        """Create appearance mode toggle (Dark/Light/System)."""
        appearance_label = ctk.CTkLabel(
            self,
            text="Appearance",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        appearance_label.grid(row=11, column=0, padx=20, pady=(20, 5), sticky="w")

        # Get current mode
        current_mode = ctk.get_appearance_mode()

        self.appearance_menu = ctk.CTkOptionMenu(
            self,
            values=["System", "Dark", "Light"],
            command=self._change_appearance,
            width=140,
        )
        self.appearance_menu.set(current_mode)
        self.appearance_menu.grid(row=12, column=0, padx=20, pady=5, sticky="w")

        # Scaling option for HiDPI displays
        scaling_label = ctk.CTkLabel(
            self,
            text="UI Scaling",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        )
        scaling_label.grid(row=13, column=0, padx=20, pady=(10, 2), sticky="w")

        self.scaling_menu = ctk.CTkOptionMenu(
            self,
            values=["80%", "90%", "100%", "110%", "125%", "150%"],
            command=self._change_scaling,
            width=100,
        )
        self.scaling_menu.set("100%")
        self.scaling_menu.grid(row=14, column=0, padx=20, pady=5, sticky="w")

    def _change_appearance(self, new_mode: str):
        """Change appearance mode (Dark/Light/System)."""
        ctk.set_appearance_mode(new_mode)

    def _change_scaling(self, new_scaling: str):
        """Change widget scaling for HiDPI displays."""
        scale = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(scale)

    def update_button_states(self, running: bool):
        """Update button states based on running status."""
        if running:
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
        else:
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")


# =============================================================================
# Content Frame
# =============================================================================


class ContentFrame(ctk.CTkFrame):
    """Main content area with combat info and logs."""

    def __init__(self, master: RushBotApp, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        # Configure grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create tabview for organized content
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew")

        # Add tabs
        self.tabview.add("🎮 Dashboard")
        self.tabview.add("📊 Combat Info")
        self.tabview.add("⚙️ Konfiguration")
        self.tabview.add("🧠 Training")
        self.tabview.add("📝 Log")
        self.tabview.add("ℹ️ About")

        # Configure tab content
        self._setup_dashboard_tab()
        self._setup_combat_tab()
        self._setup_config_tab()
        self._setup_training_tab()
        self._setup_log_tab()
        self._setup_about_tab()

    def _setup_dashboard_tab(self):
        """Setup visual 3x5 grid dashboard."""
        tab = self.tabview.tab("🎮 Dashboard")
        tab.grid_rowconfigure(0, weight=0)  # Status row
        tab.grid_rowconfigure(1, weight=1)  # Grid row
        tab.grid_columnconfigure(0, weight=1)

        # Status bar
        self.status_frame = ctk.CTkFrame(tab)
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

        # Visual 3x5 Grid
        self.grid_frame = ctk.CTkFrame(tab)
        self.grid_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Configure grid weights for even distribution
        for r in range(3):
            self.grid_frame.grid_rowconfigure(r, weight=1)
        for c in range(5):
            self.grid_frame.grid_columnconfigure(c, weight=1)

        # Create 15 grid cells (3 rows x 5 columns) as CTkFrame cards
        self.grid_cells = []
        for row in range(3):
            row_cells = []
            for col in range(5):
                # Cell container frame
                cell_frame = ctk.CTkFrame(
                    self.grid_frame,
                    corner_radius=10,
                    fg_color=COLORS["unit_empty"],
                    border_width=2,
                    border_color=COLORS["card_bg"],
                )
                cell_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
                cell_frame.grid_rowconfigure(0, weight=1)
                cell_frame.grid_rowconfigure(1, weight=0)
                cell_frame.grid_columnconfigure(0, weight=1)

                # Unit name label (top)
                name_label = ctk.CTkLabel(
                    cell_frame,
                    text="-",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=COLORS["text_primary"],
                )
                name_label.grid(row=0, column=0, padx=5, pady=(8, 2), sticky="nsew")

                # Rank indicator (bottom)
                rank_label = ctk.CTkLabel(
                    cell_frame,
                    text="",
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS["text_secondary"],
                )
                rank_label.grid(row=1, column=0, padx=5, pady=(0, 6), sticky="s")

                # Store references
                cell_data = {
                    "frame": cell_frame,
                    "name": name_label,
                    "rank": rank_label,
                }
                row_cells.append(cell_data)
            self.grid_cells.append(row_cells)

        # Legend
        legend_frame = ctk.CTkFrame(tab, fg_color="transparent")
        legend_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        legend_units = ["demon_hunter", "dryad", "harlequin", "chemist", "knight_statue", "shaman"]
        for i, unit in enumerate(legend_units):
            color = UNIT_COLORS.get(unit, COLORS["unit_default"])
            lbl = ctk.CTkLabel(
                legend_frame,
                text=f"● {unit.replace('_', ' ').title()}",
                text_color=color,
                font=ctk.CTkFont(size=10),
            )
            lbl.grid(row=0, column=i, padx=8)

    def _setup_combat_tab(self):
        """Setup combat information display."""
        tab = self.tabview.tab("📊 Combat Info")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        self.combat_frame = CombatInfoFrame(tab)
        self.combat_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def _setup_log_tab(self):
        """Setup log display."""
        tab = self.tabview.tab("📝 Log")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        self.log_frame = LogFrame(tab)
        self.log_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def _setup_config_tab(self):
        """Setup configuration with unit dropdowns."""
        tab = self.tabview.tab("⚙️ Konfiguration")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkLabel(
            tab,
            text="Unit-Auswahl",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Unit selection frame
        units_frame = ctk.CTkFrame(tab)
        units_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        # Load available units from cv-images/all_units
        self.available_units = self._load_available_units()

        # Load current selection from config
        config = self.master.config
        current_units = config.get("bot", "units", fallback="demon_hunter,dryad,harlequin,chemist,knight_statue").replace(" ", "").split(",")

        # Extend to 5 slots
        while len(current_units) < 5:
            current_units.append(self.available_units[0] if self.available_units else "empty")

        # Create 5 unit dropdowns
        self.unit_vars = []
        unit_labels = ["Slot 1 (DPS)", "Slot 2 (Support)", "Slot 3 (Support)", "Slot 4 (Utility)", "Slot 5 (Flex)"]

        for i in range(5):
            row_frame = ctk.CTkFrame(units_frame, fg_color="transparent")
            row_frame.grid(row=i, column=0, sticky="ew", padx=10, pady=8)
            row_frame.grid_columnconfigure(1, weight=1)

            lbl = ctk.CTkLabel(
                row_frame,
                text=unit_labels[i],
                font=ctk.CTkFont(size=13, weight="bold"),
                width=120,
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

        # Save button
        save_btn = ctk.CTkButton(
            tab,
            text="💾 Konfiguration speichern",
            command=self._save_unit_config,
            fg_color=COLORS["success"],
            hover_color=("#16a34a", "#22c55e"),
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        save_btn.grid(row=2, column=0, padx=20, pady=20, sticky="ew")

    def _load_available_units(self) -> list[str]:
        """Load available unit names from cv-images/all_units."""
        units_dir = Path("cv-images/all_units")
        if not units_dir.exists():
            return ["demon_hunter", "dryad", "harlequin", "chemist", "knight_statue"]

        units = sorted(
            {p.stem for p in units_dir.glob("*.png") if p.is_file() and p.stem != "empty"}
        )
        return units if units else ["empty"]

    def _save_unit_config(self):
        """Save unit selection to config.ini."""
        selected = [var.get() for var in self.unit_vars]
        config = self.master.config
        config.read("config.ini")
        config["bot"]["units"] = ", ".join(selected)

        with open("config.ini", "w") as f:
            config.write(f)

        # Show confirmation
        self.master.logger.info(f"Units gespeichert: {', '.join(selected)}")

    def _setup_training_tab(self):
        """Setup ML training interface."""
        tab = self.tabview.tab("🧠 Training")
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkLabel(
            tab,
            text="Unit Template Training",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        desc = ctk.CTkLabel(
            tab,
            text="Capture unit screenshots for template matching. Enable 'Unit Capture Mode' in sidebar first.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        )
        desc.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        # Controls frame
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        controls_frame.grid_columnconfigure(0, weight=1)

        # Capture section
        capture_label = ctk.CTkLabel(
            controls_frame,
            text="📸 Screenshot Capture",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        capture_label.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        capture_desc = ctk.CTkLabel(
            controls_frame,
            text="Captured units are saved to 'cv-images/all_units/missing_units/' for labeling.",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        capture_desc.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")

        # Capture count
        self.capture_count_label = ctk.CTkLabel(
            controls_frame,
            text="Pending captures: 0",
            font=ctk.CTkFont(size=12),
        )
        self.capture_count_label.grid(row=2, column=0, padx=15, pady=5, sticky="w")

        # Buttons row
        btn_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=10)

        refresh_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 Refresh Count",
            command=self._refresh_capture_count,
            width=140,
        )
        refresh_btn.grid(row=0, column=0, padx=5)

        open_folder_btn = ctk.CTkButton(
            btn_frame,
            text="📂 Open Folder",
            command=self._open_missing_folder,
            width=140,
        )
        open_folder_btn.grid(row=0, column=1, padx=5)

        # Labeling section
        label_section = ctk.CTkLabel(
            controls_frame,
            text="🏷️ Labeling Workflow",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        label_section.grid(row=4, column=0, padx=15, pady=(20, 5), sticky="w")

        workflow_text = """1. Start bot with 'Unit Capture Mode' enabled
2. Unknown units are saved to missing_units/
3. Open folder and rename files to unit names
4. Move labeled files to cv-images/all_units/
5. Restart bot to use new templates"""

        workflow_label = ctk.CTkLabel(
            controls_frame,
            text=workflow_text,
            font=ctk.CTkFont(family="Consolas", size=11),
            justify="left",
            anchor="nw",
        )
        workflow_label.grid(row=5, column=0, padx=15, pady=10, sticky="w")

        # Quick Label Section
        quick_label_header = ctk.CTkLabel(
            controls_frame,
            text="⚡ Quick Labeling",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        quick_label_header.grid(row=6, column=0, padx=15, pady=(20, 5), sticky="w")

        # Image preview and label controls
        quick_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        quick_frame.grid(row=7, column=0, sticky="ew", padx=15, pady=10)
        quick_frame.grid_columnconfigure(1, weight=1)

        # Preview placeholder
        self.preview_label = ctk.CTkLabel(
            quick_frame,
            text="No image\nloaded",
            width=80,
            height=80,
            fg_color=COLORS["unit_empty"],
            corner_radius=8,
        )
        self.preview_label.grid(row=0, column=0, rowspan=2, padx=(0, 15), pady=5)

        # Unit selection dropdown
        self.label_unit_var = ctk.StringVar(value="Select unit...")
        self.label_dropdown = ctk.CTkOptionMenu(
            quick_frame,
            variable=self.label_unit_var,
            values=self._load_available_units(),
            width=180,
        )
        self.label_dropdown.grid(row=0, column=1, sticky="w", pady=5)

        # Action buttons
        label_btn_frame = ctk.CTkFrame(quick_frame, fg_color="transparent")
        label_btn_frame.grid(row=1, column=1, sticky="w", pady=5)

        self.load_next_btn = ctk.CTkButton(
            label_btn_frame,
            text="📷 Load Next",
            command=self._load_next_unlabeled,
            width=100,
        )
        self.load_next_btn.grid(row=0, column=0, padx=(0, 5))

        self.save_label_btn = ctk.CTkButton(
            label_btn_frame,
            text="💾 Save & Next",
            command=self._save_and_next,
            fg_color=COLORS["success"],
            width=110,
        )
        self.save_label_btn.grid(row=0, column=1, padx=5)

        self.skip_btn = ctk.CTkButton(
            label_btn_frame,
            text="⏭ Skip",
            command=self._skip_current,
            fg_color=COLORS["warning"],
            width=70,
        )
        self.skip_btn.grid(row=0, column=2, padx=5)

        # Progress bar for batch operations
        self.training_progress = ctk.CTkProgressBar(controls_frame, width=400)
        self.training_progress.grid(row=8, column=0, padx=15, pady=(15, 5), sticky="w")
        self.training_progress.set(0)

        self.progress_label = ctk.CTkLabel(
            controls_frame,
            text="Ready",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        self.progress_label.grid(row=9, column=0, padx=15, pady=(0, 15), sticky="w")

        # =====================================================================
        # ML Model Training Section
        # =====================================================================
        ml_section = ctk.CTkLabel(
            controls_frame,
            text="🤖 Rank Model Training",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        ml_section.grid(row=10, column=0, padx=15, pady=(20, 5), sticky="w")

        ml_desc = ctk.CTkLabel(
            controls_frame,
            text="Train/update the rank recognition model (LogisticRegression).",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        ml_desc.grid(row=11, column=0, padx=15, pady=(0, 10), sticky="w")

        # Model status
        self.model_status_label = ctk.CTkLabel(
            controls_frame,
            text="Model: checking...",
            font=ctk.CTkFont(size=12),
        )
        self.model_status_label.grid(row=12, column=0, padx=15, pady=5, sticky="w")
        self._check_model_status()

        # ML Buttons
        ml_btn_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        ml_btn_frame.grid(row=13, column=0, sticky="ew", padx=15, pady=10)

        self.auto_label_btn = ctk.CTkButton(
            ml_btn_frame,
            text="🔄 Auto-Label Grid",
            command=self._auto_label_from_game,
            width=130,
        )
        self.auto_label_btn.grid(row=0, column=0, padx=5)

        self.train_model_btn = ctk.CTkButton(
            ml_btn_frame,
            text="🧠 Train Model",
            command=self._train_new_model,
            fg_color=COLORS["accent"],
            width=120,
        )
        self.train_model_btn.grid(row=0, column=1, padx=5)

        self.open_ml_folder_btn = ctk.CTkButton(
            ml_btn_frame,
            text="📂 Dataset",
            command=self._open_ml_folder,
            width=80,
        )
        self.open_ml_folder_btn.grid(row=0, column=2, padx=5)

        # Dataset info
        self.dataset_info_label = ctk.CTkLabel(
            controls_frame,
            text="Dataset samples: 0",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        self.dataset_info_label.grid(row=14, column=0, padx=15, pady=(5, 15), sticky="w")
        self._update_dataset_info()

        # State for labeling
        self._current_unlabeled_file = None
        self._unlabeled_files = []

    def _load_next_unlabeled(self):
        """Load next unlabeled image from missing_units folder."""
        missing_dir = Path("cv-images/all_units/missing_units")
        if not missing_dir.exists():
            self.progress_label.configure(text="No missing_units folder found")
            return

        # Get list of unlabeled files
        self._unlabeled_files = list(missing_dir.glob("*.png"))

        if not self._unlabeled_files:
            self.progress_label.configure(text="No unlabeled images found!")
            self.preview_label.configure(text="No image\nloaded", image=None)
            self._current_unlabeled_file = None
            return

        # Load first file
        self._current_unlabeled_file = self._unlabeled_files[0]
        self._display_preview(self._current_unlabeled_file)

        remaining = len(self._unlabeled_files)
        self.progress_label.configure(text=f"Loaded: {self._current_unlabeled_file.name} ({remaining} remaining)")

    def _display_preview(self, image_path: Path):
        """Display image preview using CTkImage."""
        try:
            pil_image = Image.open(image_path)
            # Resize for preview (maintain aspect ratio)
            pil_image.thumbnail((80, 80), Image.Resampling.LANCZOS)
            ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(80, 80))
            self.preview_label.configure(image=ctk_image, text="")
            self.preview_label._image = ctk_image  # Keep reference
        except Exception as e:
            self.preview_label.configure(text="Error\nloading", image=None)
            self.progress_label.configure(text=f"Error: {e}")

    def _save_and_next(self):
        """Save current label and load next image."""
        if not self._current_unlabeled_file or not self._current_unlabeled_file.exists():
            self.progress_label.configure(text="No image loaded to label")
            return

        selected_unit = self.label_unit_var.get()
        if selected_unit == "Select unit..." or not selected_unit:
            self.progress_label.configure(text="Please select a unit first!")
            return

        # Move file to all_units with proper name
        target_dir = Path("cv-images/all_units")
        target_path = target_dir / f"{selected_unit}.png"

        # If target exists, create numbered version
        if target_path.exists():
            counter = 1
            while target_path.exists():
                target_path = target_dir / f"{selected_unit}_{counter}.png"
                counter += 1

        try:
            import shutil
            shutil.move(str(self._current_unlabeled_file), str(target_path))
            self.progress_label.configure(text=f"Saved as: {target_path.name}")

            # Update progress
            self._refresh_capture_count()

            # Load next
            self._load_next_unlabeled()
        except Exception as e:
            self.progress_label.configure(text=f"Error saving: {e}")

    def _skip_current(self):
        """Skip current image and load next."""
        if self._unlabeled_files and len(self._unlabeled_files) > 1:
            # Move current to end of list
            self._unlabeled_files.append(self._unlabeled_files.pop(0))
            self._current_unlabeled_file = self._unlabeled_files[0]
            self._display_preview(self._current_unlabeled_file)
            self.progress_label.configure(text=f"Skipped. Now: {self._current_unlabeled_file.name}")
        else:
            self.progress_label.configure(text="No more images to skip to")

    def _refresh_capture_count(self):
        """Count pending captures in missing_units folder."""
        missing_dir = Path("cv-images/all_units/missing_units")
        if missing_dir.exists():
            count = len(list(missing_dir.glob("*.png")))
        else:
            count = 0
        self.capture_count_label.configure(text=f"Pending captures: {count}")

    def _open_missing_folder(self):
        """Open missing_units folder in file explorer (cross-platform)."""
        import subprocess
        import sys
        missing_dir = Path("cv-images/all_units/missing_units").resolve()
        missing_dir.mkdir(parents=True, exist_ok=True)

        # Cross-platform folder opening
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(missing_dir)])
        elif sys.platform == "darwin":  # macOS
            subprocess.Popen(["open", str(missing_dir)])
        else:  # Linux
            subprocess.Popen(["xdg-open", str(missing_dir)])

    def _check_model_status(self):
        """Check if rank_model.pkl exists and is loadable."""
        model_path = Path("rank_model.pkl")
        if model_path.exists():
            try:
                import pickle
                with open(model_path, "rb") as f:
                    model = pickle.load(f)
                classes = getattr(model, "classes_", [])
                self.model_status_label.configure(
                    text=f"Model: ✅ Loaded (classes: {list(classes)})",
                    text_color=COLORS["success"],
                )
            except Exception as e:
                self.model_status_label.configure(
                    text=f"Model: ⚠️ Error loading: {e}",
                    text_color=COLORS["warning"],
                )
        else:
            self.model_status_label.configure(
                text="Model: ❌ Not found (rank_model.pkl missing)",
                text_color=COLORS["danger"],
            )

    def _update_dataset_info(self):
        """Count samples in machine_learning/inputs folder."""
        ml_dir = Path("machine_learning/inputs")
        if ml_dir.exists():
            # Count files matching pattern
            flat_count = len(list(ml_dir.glob("*_input_*.png")))
            # Count files in subdirectories
            sub_count = sum(len(list(sub.glob("*.png"))) for sub in ml_dir.iterdir() if sub.is_dir())
            total = flat_count + sub_count
            self.dataset_info_label.configure(text=f"Dataset samples: {total}")
        else:
            self.dataset_info_label.configure(text="Dataset: folder not found")

    def _auto_label_from_game(self):
        """Use existing model to auto-label current game grid."""
        import threading

        def run_auto_label():
            try:
                self.progress_label.configure(text="Auto-labeling in progress...")
                self.training_progress.set(0.2)

                import bot_perception
                bot_perception.ensure_training_dirs()

                # Check if OCR_inputs has data
                ocr_dir = Path("OCR_inputs")
                if not ocr_dir.exists() or not list(ocr_dir.glob("*.png")):
                    self.master.after(0, lambda: self.progress_label.configure(
                        text="No OCR_inputs found. Start bot first to capture grid."
                    ))
                    return

                self.training_progress.set(0.5)

                # Run auto-labeling (uses current model to label and save)
                bot_perception.add_grid_to_dataset()

                self.training_progress.set(1.0)
                self.master.after(0, lambda: self.progress_label.configure(
                    text="✅ Grid added to dataset!"
                ))
                self.master.after(0, self._update_dataset_info)

            except Exception as e:
                self.master.after(0, lambda: self.progress_label.configure(
                    text=f"Error: {e}"
                ))
            finally:
                self.master.after(500, lambda: self.training_progress.set(0))

        thread = threading.Thread(target=run_auto_label, daemon=True)
        thread.start()

    def _train_new_model(self):
        """Train new rank model from dataset in background thread."""
        import threading

        def run_training():
            try:
                self.progress_label.configure(text="Training model...")
                self.training_progress.set(0.1)

                import bot_perception
                bot_perception.ensure_training_dirs()

                ml_dir = Path("machine_learning/inputs")
                if not ml_dir.exists():
                    self.master.after(0, lambda: self.progress_label.configure(
                        text="Dataset folder not found!"
                    ))
                    return

                self.training_progress.set(0.3)

                # Train model
                model = bot_perception.train_rank_model(ml_dir)

                self.training_progress.set(0.7)

                # Save model
                saved_path = bot_perception.save_rank_model(model)

                self.training_progress.set(1.0)

                classes = list(model.classes_)
                self.master.after(0, lambda: self.progress_label.configure(
                    text=f"✅ Model trained! Classes: {classes}"
                ))
                self.master.after(0, self._check_model_status)

            except Exception as e:
                self.master.after(0, lambda: self.progress_label.configure(
                    text=f"Training error: {e}"
                ))
            finally:
                self.master.after(500, lambda: self.training_progress.set(0))

        thread = threading.Thread(target=run_training, daemon=True)
        thread.start()

    def _open_ml_folder(self):
        """Open machine_learning/inputs folder in file explorer."""
        import subprocess
        import sys
        ml_dir = Path("machine_learning/inputs").resolve()
        ml_dir.mkdir(parents=True, exist_ok=True)

        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(ml_dir)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(ml_dir)])
        else:
            subprocess.Popen(["xdg-open", str(ml_dir)])

    def _setup_about_tab(self):
        """Setup about/info display."""
        tab = self.tabview.tab("ℹ️ About")

        about_text = """
Rush Royale Bot
───────────────
An automated gameplay assistant for Rush Royale.

Features:
• Automatic unit merging and spawning
• Mana upgrade management
• PvE dungeon automation
• Unit template capture mode

Controls:
• Start Bot - Begin automation
• Stop - Safely stop the bot
• Quit Floor - Leave current dungeon

Configuration:
Edit config.ini or use the sidebar controls
to customize bot behavior.

⚠️ Use responsibly and at your own risk.
        """

        about_label = ctk.CTkLabel(
            tab,
            text=about_text,
            font=ctk.CTkFont(family="Consolas", size=12),
            justify="left",
            anchor="nw",
        )
        about_label.pack(padx=20, pady=20, anchor="nw")


# =============================================================================
# Combat Info Frame
# =============================================================================


class CombatInfoFrame(ctk.CTkFrame):
    """Display combat grid and unit information."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Grid status display
        self.grid_text = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none",
        )
        self.grid_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.grid_text.insert("1.0", "Waiting for combat data...")
        self.grid_text.configure(state="disabled")

        # Unit/Merge info row
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        info_frame.grid_columnconfigure((0, 1), weight=1)
        info_frame.grid_rowconfigure(0, weight=1)

        # Unit series
        self.unit_text = ctk.CTkTextbox(
            info_frame,
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="none",
        )
        self.unit_text.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.unit_text.insert("1.0", "Unit Series:\n---")
        self.unit_text.configure(state="disabled")

        # Merge series
        self.merge_text = ctk.CTkTextbox(
            info_frame,
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="none",
        )
        self.merge_text.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.merge_text.insert("1.0", "Merge Series:\n---")
        self.merge_text.configure(state="disabled")

    def update_data(self, combat, step, output, info, grid_df, unit_series, merge_series):
        """Update display with new combat data."""
        # Update grid display
        if grid_df is not None:
            df = grid_df.copy()
            df["unit"] = df["unit"].str.replace(".png", "", regex=False)
            df["unit"] = df["unit"].str.replace("empty", "-", regex=False)

            num_demons = df[df["unit"] == "demon_hunter"]["rank"].sum()
            avg_age = df["Age"].mean().round(2)

            header = f"Combat: {combat} | Step: {step + 1}/8 | State: {output} | {info}\n"
            stats = f"Average Age: {avg_age} | DPS Ranks: {num_demons}\n"
            divider = "─" * 60 + "\n"

            self._update_textbox(self.grid_text, header + stats + divider + df.to_string())
        else:
            self._update_textbox(self.grid_text, "Waiting for combat data...")

        # Update unit series
        if unit_series is not None:
            self._update_textbox(self.unit_text, "Unit Series:\n" + unit_series.to_string())

        # Update merge series
        if merge_series is not None:
            self._update_textbox(self.merge_text, "Merge Series:\n" + merge_series.to_string())

    def _update_textbox(self, textbox: ctk.CTkTextbox, text: str):
        """Safely update a textbox."""
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.insert("1.0", text)
        textbox.configure(state="disabled")


# =============================================================================
# Log Frame
# =============================================================================


class LogFrame(ctk.CTkFrame):
    """Log display with scrollable text."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Log textbox - use Tkinter Text for logger compatibility
        import tkinter as tk

        self.log_text = tk.Text(
            self,
            height=25,
            width=80,
            bg="#1e1e2e",
            fg="#cdd6f4",
            font=("Consolas", 10),
            wrap="word",
            insertbackground="#cdd6f4",
            selectbackground="#45475a",
            relief="flat",
            padx=10,
            pady=10,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(self, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=5)
        self.log_text.configure(yscrollcommand=scrollbar.set)


# =============================================================================
# Entry Point
# =============================================================================


if __name__ == "__main__":
    app = RushBotApp()
    app.mainloop()
