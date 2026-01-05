"""
Rush Royale Bot - Modern GUI
Python 3.13 Compatible

CustomTkinter-based interface with:
- Dark/Light theme support
- High-DPI scaling
- Modern rounded widgets
"""
from __future__ import annotations

import os
import threading
import logging
import configparser
from typing import Optional

import numpy as np
import customtkinter as ctk

# Handle imports - support both package and direct execution
try:
    from . import bot_handler
    from . import bot_logger
    from .utils.icons import icon
except ImportError:
    import bot_handler
    import bot_logger
    try:
        from utils.icons import icon
    except ImportError:
        from Src.utils.icons import icon


# Configure CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ModernBotGUI(ctk.CTk):
    """
    Modern Rush Royale Bot GUI using CustomTkinter.
    
    Features:
    - Dark mode by default
    - Responsive layout
    - Modern widget styling
    """
    
    # Color scheme
    COLORS = {
        'bg': '#1a1a2e',
        'fg': '#eaeaea',
        'accent': '#0f3460',
        'danger': '#e94560',
        'success': '#00d9ff',
    }
    
    def __init__(self):
        super().__init__()
        
        # State variables
        self.stop_flag = False
        self.running = False
        self.info_ready = threading.Event()
        self.bot_instance = None
        self.thread_run: Optional[threading.Thread] = None
        
        # Load config
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        
        # Setup window
        self._setup_window()
        self._create_widgets()
        
        # Setup logger
        self.logger = self._setup_logger()
        self.logger.debug('Modern GUI started!')
    
    def _setup_window(self) -> None:
        """Configure main window properties."""
        self.title("Rush Royale Bot - Modern Edition")
        self.geometry("900x700")
        self.minsize(800, 600)
        
        # Set icon if available
        if os.path.exists('calculon.ico'):
            self.iconbitmap('calculon.ico')
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)
    
    def _create_widgets(self) -> None:
        """Create all GUI widgets."""
        # Header
        self._create_header()
        
        # Left panel (controls)
        self._create_control_panel()
        
        # Right panel (info display)
        self._create_info_panel()
        
        # Bottom panel (log)
        self._create_log_panel()
    
    def _create_header(self) -> None:
        """Create header with title and theme toggle."""
        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        
        title = ctk.CTkLabel(
            header,
            text=f"{icon('game')} Rush Royale Bot",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(side="left", padx=20, pady=10)
        
        # Theme toggle
        self.theme_switch = ctk.CTkSwitch(
            header,
            text="Dark Mode",
            command=self._toggle_theme,
            onvalue="dark",
            offvalue="light"
        )
        self.theme_switch.select()  # Default to dark
        self.theme_switch.pack(side="right", padx=20, pady=10)
    
    def _create_control_panel(self) -> None:
        """Create left control panel with options."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Options section
        options_label = ctk.CTkLabel(
            panel,
            text=f"{icon('settings')} Options",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        options_label.pack(padx=10, pady=(10, 5), anchor="w")
        
        # PvE mode toggle
        pve_default = self.config.getboolean('bot', 'pve', fallback=True)
        self.pve_var = ctk.BooleanVar(value=pve_default)
        self.pve_check = ctk.CTkCheckBox(
            panel,
            text="PvE Mode (Dungeon)",
            variable=self.pve_var
        )
        self.pve_check.pack(padx=20, pady=5, anchor="w")
        
        # Dungeon floor
        floor_frame = ctk.CTkFrame(panel, fg_color="transparent")
        floor_frame.pack(padx=10, pady=10, fill="x")
        
        floor_label = ctk.CTkLabel(floor_frame, text="Dungeon Floor:")
        floor_label.pack(side="left", padx=5)
        
        floor_default = self.config.get('bot', 'floor', fallback='5')
        self.floor_entry = ctk.CTkEntry(floor_frame, width=60)
        self.floor_entry.insert(0, floor_default)
        self.floor_entry.pack(side="left", padx=5)
        
        # Mana level targets
        mana_label = ctk.CTkLabel(
            panel,
            text=f"{icon('mana')} Mana Level Targets",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        mana_label.pack(padx=10, pady=(15, 5), anchor="w")
        
        # Parse stored mana levels
        stored_str = self.config.get('bot', 'mana_level', fallback='1,2,3')
        stored_values = np.fromstring(stored_str, dtype=int, sep=',')
        
        self.mana_vars = []
        mana_frame = ctk.CTkFrame(panel, fg_color="transparent")
        mana_frame.pack(padx=10, pady=5, fill="x")
        
        for i in range(5):
            var = ctk.BooleanVar(value=(i + 1) in stored_values)
            self.mana_vars.append(var)
            
            cb = ctk.CTkCheckBox(
                mana_frame,
                text=f"Card {i + 1}",
                variable=var,
                width=80
            )
            cb.pack(side="left", padx=2)
        
        # Control buttons
        buttons_frame = ctk.CTkFrame(panel, fg_color="transparent")
        buttons_frame.pack(padx=10, pady=20, fill="x")
        
        self.start_button = ctk.CTkButton(
            buttons_frame,
            text=f"{icon('play')} Start Bot",
            command=self.start_command,
            fg_color="#00aa00",
            hover_color="#008800"
        )
        self.start_button.pack(pady=5, fill="x")
        
        self.stop_button = ctk.CTkButton(
            buttons_frame,
            text=f"{icon('stop')} Stop Bot",
            command=self.stop_bot,
            fg_color="#aa6600",
            hover_color="#884400"
        )
        self.stop_button.pack(pady=5, fill="x")
        
        self.quit_button = ctk.CTkButton(
            buttons_frame,
            text=f"{icon('exit')} Quit Floor",
            command=self.leave_game,
            fg_color=self.COLORS['danger'],
            hover_color="#cc3355"
        )
        self.quit_button.pack(pady=5, fill="x")
    
    def _create_info_panel(self) -> None:
        """Create right info display panel."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=2)
        panel.grid_rowconfigure(1, weight=1)
        
        # Grid status
        grid_label = ctk.CTkLabel(
            panel,
            text=f"{icon('grid')} Grid Status",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        grid_label.grid(row=0, column=0, sticky="nw", padx=10, pady=5)
        
        self.grid_display = ctk.CTkTextbox(
            panel,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none"
        )
        self.grid_display.grid(row=0, column=0, sticky="nsew", padx=10, pady=(30, 10))
        
        # Unit info frame
        unit_frame = ctk.CTkFrame(panel, fg_color="transparent")
        unit_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        unit_frame.grid_columnconfigure(0, weight=1)
        unit_frame.grid_columnconfigure(1, weight=1)
        
        # Unit series
        unit_label = ctk.CTkLabel(unit_frame, text="Units", font=ctk.CTkFont(weight="bold"))
        unit_label.grid(row=0, column=0, sticky="w", padx=5)
        
        self.unit_display = ctk.CTkTextbox(
            unit_frame,
            font=ctk.CTkFont(family="Consolas", size=10),
            height=150
        )
        self.unit_display.grid(row=1, column=0, sticky="nsew", padx=5)
        
        # Merge series
        merge_label = ctk.CTkLabel(unit_frame, text="Merge Targets", font=ctk.CTkFont(weight="bold"))
        merge_label.grid(row=0, column=1, sticky="w", padx=5)
        
        self.merge_display = ctk.CTkTextbox(
            unit_frame,
            font=ctk.CTkFont(family="Consolas", size=10),
            height=150
        )
        self.merge_display.grid(row=1, column=1, sticky="nsew", padx=5)
    
    def _create_log_panel(self) -> None:
        """Create bottom log panel."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        panel.grid_columnconfigure(0, weight=1)
        
        log_label = ctk.CTkLabel(
            panel,
            text=f"{icon('log')} Log",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        log_label.pack(anchor="w", padx=10, pady=5)
        
        self.log_display = ctk.CTkTextbox(
            panel,
            font=ctk.CTkFont(family="Consolas", size=10),
            height=150
        )
        self.log_display.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger with custom handler for GUI."""
        logger = logging.getLogger('RR_Bot_Modern')
        logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Add GUI handler
        handler = GUILogHandler(self.log_display)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        ))
        logger.addHandler(handler)
        
        return logger
    
    def _toggle_theme(self) -> None:
        """Toggle between dark and light theme."""
        current = ctk.get_appearance_mode()
        if current == "Dark":
            ctk.set_appearance_mode("light")
            self.theme_switch.configure(text="Light Mode")
        else:
            ctk.set_appearance_mode("dark")
            self.theme_switch.configure(text="Dark Mode")
    
    def start_command(self) -> None:
        """Initialize and start the bot."""
        self.stop_flag = False
        self._update_config()
        
        if self.running:
            self.logger.warning("Bot is already running!")
            return
        
        self.running = True
        self.thread_run = threading.Thread(target=self._start_bot, daemon=True)
        self.thread_run.start()
    
    def _update_config(self) -> None:
        """Save current settings to config file."""
        floor_var = int(self.floor_entry.get())
        
        # Build mana level string
        card_levels = [i + 1 for i, var in enumerate(self.mana_vars) if var.get()]
        mana_str = ','.join(map(str, card_levels)) if card_levels else '1'
        
        self.config.read('config.ini')
        self.config['bot']['floor'] = str(floor_var)
        self.config['bot']['mana_level'] = mana_str
        self.config['bot']['pve'] = str(self.pve_var.get())
        
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        
        self.logger.info("Settings saved to config.ini")
    
    def _update_units(self) -> None:
        """Update unit selection from config."""
        selected = self.config.get('bot', 'units', fallback='').replace(' ', '').split(',')
        self.logger.info(f'Selected units: {", ".join(selected)}')
        
        if not bot_handler.select_units([unit + '.png' for unit in selected if unit]):
            valid_units = ' '.join(os.listdir("all_units")).replace('.png', '')
            self.logger.warning(f'Invalid units! Valid: {valid_units}')
    
    def _start_bot(self) -> None:
        """Run the bot (called in separate thread)."""
        self.logger.warning('Starting bot...')
        
        try:
            # Use modern bot architecture
            self.bot_instance = bot_handler.start_bot_class(self.logger, use_modern=True)
        except Exception as e:
            self.logger.error(f'Failed to start bot: {e}')
            self.running = False
            return
        
        # Show startup message
        startup_path = 'src/startup_message.txt'
        if os.path.exists(startup_path):
            with open(startup_path) as f:
                self.logger.info(f.read())
        
        self._update_units()
        
        # Configure bot instance
        self.bot_instance.bot_stop = False
        self.bot_instance.logger = self.logger
        self.bot_instance.config = self.config
        
        infos_ready = threading.Event()
        
        # Start bot loop thread
        thread_bot = threading.Thread(
            target=bot_handler.bot_loop,
            args=(self.bot_instance, infos_ready),
            daemon=True
        )
        thread_bot.start()
        
        # Update GUI with bot info
        while not self.stop_flag:
            infos_ready.wait(timeout=5)
            
            if self.bot_instance:
                self._update_displays()
            
            infos_ready.clear()
        
        # Cleanup
        if self.bot_instance:
            self.bot_instance.bot_stop = True
        
        self.logger.warning('Exiting main loop...')
        thread_bot.join(timeout=10)
        
        # Stop scrcpy
        if hasattr(self.bot_instance, 'scrcpy_process') and self.bot_instance.scrcpy_process:
            self.bot_instance.stop_scrcpy()
        
        self.logger.info('Bot stopped!')
        self.running = False
    
    def _update_displays(self) -> None:
        """Update info displays with bot data."""
        bot = self.bot_instance
        
        if bot.grid_df is not None:
            grid_df = bot.grid_df.copy()
            grid_df['unit'] = grid_df['unit'].str.replace('.png', '', regex=False)
            grid_df['unit'] = grid_df['unit'].str.replace('empty', '-', regex=False)
            
            num_demons = grid_df[grid_df['unit'] == 'demon_hunter']['rank'].sum()
            avg_age = grid_df['Age'].mean()
            
            info_text = (
                f"{bot.combat}, Step {bot.combat_step + 1}/8 {bot.output}\n"
                f"{bot.info}\n\n"
                f"{grid_df.to_string()}\n\n"
                f"Avg Age: {avg_age:.2f} | Demon Ranks: {num_demons}"
            )
            
            self._update_textbox(self.grid_display, info_text)
        
        if bot.unit_series is not None:
            self._update_textbox(self.unit_display, bot.unit_series.to_string())
        
        if bot.merge_series is not None:
            self._update_textbox(self.merge_display, bot.merge_series.to_string())
    
    def _update_textbox(self, textbox: ctk.CTkTextbox, text: str) -> None:
        """Update textbox content thread-safely."""
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.insert("end", text)
        textbox.configure(state="disabled")
    
    def stop_bot(self) -> None:
        """Stop the running bot."""
        self.running = False
        self.stop_flag = True
        self.logger.info('Stopping bot...')
    
    def leave_game(self) -> None:
        """Leave current game/dungeon."""
        if hasattr(self, 'bot_instance') and self.bot_instance:
            thread = threading.Thread(
                target=self.bot_instance.restart_RR,
                args=(True,),
                daemon=True
            )
            thread.start()
            self.logger.info('Leaving current game...')
        else:
            self.logger.warning('Bot has not been started!')
    
    def on_closing(self) -> None:
        """Handle window close."""
        self.stop_flag = True
        
        if self.thread_run and self.thread_run.is_alive():
            self.thread_run.join(timeout=5)
        
        self.destroy()


class GUILogHandler(logging.Handler):
    """Custom logging handler that writes to CTkTextbox."""
    
    # Log level colors (ANSI-style)
    LEVEL_COLORS = {
        'DEBUG': '#888888',
        'INFO': '#00ccff',
        'WARNING': '#ffaa00',
        'ERROR': '#ff4444',
        'CRITICAL': '#ff0000',
    }
    
    def __init__(self, textbox: ctk.CTkTextbox):
        super().__init__()
        self.textbox = textbox
    
    def emit(self, record: logging.LogRecord) -> None:
        """Write log record to textbox."""
        try:
            msg = self.format(record)
            
            # Thread-safe update
            self.textbox.after(0, self._write_log, msg)
        except Exception:
            self.handleError(record)
    
    def _write_log(self, msg: str) -> None:
        """Write message to textbox (called on main thread)."""
        self.textbox.configure(state="normal")
        self.textbox.insert("end", msg + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")


def main():
    """Main entry point."""
    app = ModernBotGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
