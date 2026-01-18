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
        version_label.grid(row=1, column=0, padx=20, pady=(0, 10))

        # ADB Connection Status Indicator
        self.adb_status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.adb_status_frame.grid(row=2, column=0, padx=20, pady=(0, 15))

        self.adb_indicator = ctk.CTkLabel(
            self.adb_status_frame,
            text="●",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["danger"],
        )
        self.adb_indicator.grid(row=0, column=0, padx=(0, 5))

        self.adb_status_label = ctk.CTkLabel(
            self.adb_status_frame,
            text="ADB Disconnected",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        )
        self.adb_status_label.grid(row=0, column=1)

        # Reconnect button
        self.reconnect_button = ctk.CTkButton(
            self.adb_status_frame,
            text="🔄",
            width=28,
            height=28,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            hover_color=COLORS["accent"],
            command=self._reconnect_adb,
        )
        self.reconnect_button.grid(row=0, column=2, padx=(8, 0))

        # Flag to track if we can update UI
        self._adb_check_scheduled = False
        self._adb_connected = False

    def _reconnect_adb(self) -> None:
        """Manually reconnect to ADB device."""
        import threading

        self.reconnect_button.configure(state="disabled", text="⏳")
        self.adb_status_label.configure(text="Connecting...", text_color=COLORS["warning"])
        self.adb_indicator.configure(text_color=COLORS["warning"])

        def connect_thread():
            connected = False
            try:
                import sys

                from rush_bot import PROJECT_ROOT

                src_path = PROJECT_ROOT / "Src"
                if str(src_path) not in sys.path:
                    sys.path.insert(0, str(src_path))

                import port_scan

                # Use improved device detection
                device = port_scan.get_device(force_scan=False)
                connected = device is not None

                if connected:
                    print(f"[INFO] ADB connected to: {device}")

            except Exception as e:
                print(f"[ERROR] Connection failed: {e}")
                connected = False

            self._adb_connected = connected
            self._adb_reconnect_done = True

        self._adb_reconnect_done = False
        threading.Thread(target=connect_thread, daemon=True).start()

        # Poll for result
        self._poll_reconnect_result()

    def _poll_reconnect_result(self) -> None:
        """Poll for reconnect result and update UI."""
        if hasattr(self, "_adb_reconnect_done") and self._adb_reconnect_done:
            self._update_adb_status(self._adb_connected)
            self.reconnect_button.configure(state="normal", text="🔄")

            # Log result
            if hasattr(self.master_app, "logger"):
                if self._adb_connected:
                    self.master_app.logger.info("ADB connected successfully!")
                else:
                    self.master_app.logger.warning(
                        "ADB connection failed. Is the emulator running?"
                    )

            # Start periodic monitoring after initial connection attempt
            self.after(5000, self._check_adb_connection)
        else:
            self.after(100, self._poll_reconnect_result)

    def _check_adb_connection(self) -> None:
        """Periodically check ADB connection status."""
        import threading

        def check_thread():
            connected = False
            try:
                import sys

                from rush_bot import PROJECT_ROOT

                src_path = PROJECT_ROOT / "Src"
                if str(src_path) not in sys.path:
                    sys.path.insert(0, str(src_path))

                import port_scan

                # Quick check for existing device (no scan)
                device = port_scan.get_adb_device()
                if device:
                    connected = True
                else:
                    # Try adbutils
                    try:
                        from adbutils import adb

                        devices = adb.device_list()
                        connected = len(devices) > 0
                    except Exception:
                        pass

            except Exception:
                connected = False

            # Store result for main thread to pick up
            self._adb_connected = connected
            self._adb_check_done = True

        self._adb_check_done = False
        threading.Thread(target=check_thread, daemon=True).start()

        # Poll for result
        self._poll_adb_result()

    def _poll_adb_result(self) -> None:
        """Poll for ADB check result and update UI."""
        if hasattr(self, "_adb_check_done") and self._adb_check_done:
            self._update_adb_status(self._adb_connected)
            # Schedule next check in 5 seconds
            self.after(5000, self._check_adb_connection)
        else:
            # Keep polling every 100ms
            self.after(100, self._poll_adb_result)

    def start_adb_monitoring(self) -> None:
        """Start the ADB connection monitoring. Call after GUI is ready.

        Automatically attempts to connect to emulator on startup.
        """
        # Try to connect automatically on startup
        self._reconnect_adb()

    def _update_adb_status(self, connected: bool) -> None:
        """Update the ADB status indicator."""
        if connected:
            self.adb_indicator.configure(text_color=COLORS["success"])
            self.adb_status_label.configure(
                text="ADB Connected",
                text_color=COLORS["success"],
            )
        else:
            self.adb_indicator.configure(text_color=COLORS["danger"])
            self.adb_status_label.configure(
                text="ADB Disconnected",
                text_color=COLORS["danger"],
            )

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
        self.start_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

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
        self.stop_button.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        # Auto-Detect Units Button
        self.detect_button = ctk.CTkButton(
            self,
            text="🔍 Auto-Detect Units",
            command=self._on_detect_units,
            fg_color=COLORS["accent"],
            height=35,
            font=ctk.CTkFont(size=13),
        )
        self.detect_button.grid(row=5, column=0, padx=20, pady=(15, 5), sticky="ew")

    def _create_options(self) -> None:
        """Create game mode options."""
        # Game Mode
        mode_label = ctk.CTkLabel(
            self,
            text="Game Mode",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        mode_label.grid(row=6, column=0, padx=20, pady=(20, 5), sticky="w")

        self.game_mode_var = ctk.StringVar(value="PVE")
        self.game_mode_menu = ctk.CTkOptionMenu(
            self,
            variable=self.game_mode_var,
            values=["PVP", "PVE", "TRAIN(PVP)", "TRAIN(PVE)"],
            width=150,
        )
        self.game_mode_menu.grid(row=7, column=0, padx=20, pady=5, sticky="w")

        # Mana upgrades
        mana_label = ctk.CTkLabel(
            self,
            text="Mana Upgrades",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        mana_label.grid(row=8, column=0, padx=20, pady=(20, 5), sticky="w")

        mana_frame = ctk.CTkFrame(self, fg_color="transparent")
        mana_frame.grid(row=9, column=0, padx=20, pady=5, sticky="ew")

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
        floor_label.grid(row=10, column=0, padx=20, pady=(20, 5), sticky="w")

        floor_frame = ctk.CTkFrame(self, fg_color="transparent")
        floor_frame.grid(row=11, column=0, padx=20, pady=5, sticky="ew")

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
        appearance_label.grid(row=13, column=0, padx=20, pady=(20, 5), sticky="w")

        current_mode = ctk.get_appearance_mode()
        self.appearance_menu = ctk.CTkOptionMenu(
            self,
            values=["System", "Dark", "Light"],
            command=self._change_appearance,
            width=140,
        )
        self.appearance_menu.set(current_mode)
        self.appearance_menu.grid(row=14, column=0, padx=20, pady=5, sticky="w")

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

    def _on_detect_units(self) -> None:
        """Auto-detect deck units from home screen."""
        import threading

        self.detect_button.configure(state="disabled", text="🔍 Detecting...")
        logger = self.master_app.logger

        def detect_thread():
            try:
                import sys

                from rush_bot import PROJECT_ROOT

                # Add Src to path
                src_path = PROJECT_ROOT / "Src"
                if str(src_path) not in sys.path:
                    sys.path.insert(0, str(src_path))

                import detect_deck
                import port_scan

                # Get device using improved detection (no server kill)
                logger.info("Checking for connected device...")
                device = port_scan.get_device(force_scan=False)

                if not device:
                    logger.error("No device found! Start emulator first.")
                    self.after(
                        0,
                        lambda: self.detect_button.configure(
                            state="normal", text="🔍 Auto-Detect Units"
                        ),
                    )
                    return

                logger.info(f"Using device: {device}")

                # Get a bot instance for screenshot
                import bot_core

                bot = bot_core.Bot(device=device)

                logger.info("Taking screenshot from home screen...")
                detected = detect_deck.detect_deck_from_device(bot)

                # Log detected units
                logger.info("Detected deck units:")
                detected_names = []
                for i, (unit, conf) in enumerate(detected, 1):
                    display_name = detect_deck.format_unit_name(unit)
                    logger.info(f"  Slot {i}: {display_name} (match: {conf:.0f})")
                    detected_names.append(unit)

                # Update config with detected units
                config = self.master_app.config

                # Ensure [bot] section exists
                if not config.has_section("bot"):
                    config.add_section("bot")

                # Update individual unit fields
                for i, unit_name in enumerate(detected_names, 1):
                    if unit_name != "unknown":
                        config.set("bot", f"unit_{i}", f"{unit_name}.png")

                # Update the combined units string (main field used by bot)
                valid_units = [u for u in detected_names if u != "unknown"]
                if valid_units:
                    config.set("bot", "units", ", ".join(valid_units))
                    logger.info(f"Updated units config: {', '.join(valid_units)}")

                # Save config
                config_path = PROJECT_ROOT / "config.ini"
                with open(config_path, "w") as f:
                    config.write(f)

                logger.info("Config saved to config.ini!")

                # Update dashboard legend (use correct reference)
                def update_ui():
                    try:
                        if hasattr(self.master_app, "content") and hasattr(
                            self.master_app.content, "dashboard_tab"
                        ):
                            self.master_app.content.dashboard_tab.update_legend(detected_names)
                            logger.info("Dashboard legend updated!")
                    except Exception as e:
                        logger.warning(f"Could not update dashboard: {e}")

                self.after(0, update_ui)

            except Exception as e:
                logger.error(f"Detection failed: {e}")
            finally:
                self.after(
                    0,
                    lambda: self.detect_button.configure(
                        state="normal", text="🔍 Auto-Detect Units"
                    ),
                )

        threading.Thread(target=detect_thread, daemon=True).start()

    def _change_appearance(self, new_mode: str) -> None:
        """Change appearance mode."""
        ctk.set_appearance_mode(new_mode)
