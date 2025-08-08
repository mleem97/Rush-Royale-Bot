"""
Rush Royale Bot GUI - Python 3.13 Compatible
Rebuilt with proper error handling and thread safety
"""
from __future__ import annotations

from tkinter import *
from tkinter import messagebox
import os
import sys
import numpy as np
import threading
import logging
import configparser
import time
from typing import Optional, Dict, Any, List, Tuple

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Internal imports with error handling
try:
    import bot_logger
    LOGGER_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Could not import bot_logger: {e}")
    LOGGER_AVAILABLE = False

try:
    import bot_core
    BOT_CORE_AVAILABLE = True
except ImportError as e:
    print(f"ERROR: Could not import bot_core: {e}")
    BOT_CORE_AVAILABLE = False

try:
    import bot_handler_simple
    BOT_HANDLER_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Could not import bot_handler_simple: {e}")
    BOT_HANDLER_AVAILABLE = False


class RR_bot:
    """Rush Royale Bot GUI with enhanced error handling"""

    def __init__(self):
        print("Creating GUI instance...")
        
        # State variables
        self.stop_flag = False
        self.running = False
        self.bot_instance = None
        self.bot_thread = None
        self.info_event = None
        
        # Validate environment
        if not self.validate_environment():
            messagebox.showerror("Error", "Environment validation failed. Check console for details.")
            sys.exit(1)
        
        # Load configuration
        self.config = configparser.ConfigParser()
        self.load_or_create_config()
        
        # Create GUI
        self.create_gui()
        
        # Setup logger
        self.setup_logger()
        
        print("GUI instance created successfully")

    def validate_environment(self):
        """Validate that required components are available"""
        if not BOT_CORE_AVAILABLE:
            print("ERROR: bot_core module is required but not available")
            return False
        
        # Check for critical directories
        if not os.path.exists('icons'):
            print("WARNING: icons directory not found")
        
        if not os.path.exists('all_units'):
            print("WARNING: all_units directory not found")
        
        return True

    def load_or_create_config(self):
        """Load config or create default"""
        try:
            if os.path.exists('config.ini'):
                self.config.read('config.ini')
                print("Config loaded successfully")
            else:
                self.create_default_config()
                print("Default config created")
        except Exception as e:
            print(f"Config error: {e}")
            self.create_default_config()

    def create_default_config(self):
        """Create default configuration"""
        self.config['bot'] = {
            'floor': '7',
            'mana_level': '1,2,3,4,5',
            'units': 'demo, boreas, robot, dryad, franky_stein',
            'dps_unit': 'boreas',
            'pve': 'True',
            'require_shaman': 'False'
        }
        
        self.config['rl_system'] = {
            'enabled': 'False'
        }
        
        self.save_config()

    def save_config(self):
        """Save configuration to file"""
        try:
            with open('config.ini', 'w') as configfile:
                self.config.write(configfile)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def create_gui(self):
        """Create the main GUI"""
        # Main window
        self.root = Tk()
        self.root.title("RR bot (Keine Rückmeldung)")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Set window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create main frame
        main_frame = Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Options frame
        self.create_options_frame(main_frame)
        
        # Display frame
        self.create_display_frame(main_frame)
        
        # Control buttons
        self.create_control_frame(main_frame)
        
        # Status bar
        self.status_label = Label(main_frame, text="Status: Initializing...", anchor="w")
        self.status_label.pack(fill=X, pady=(5, 0))

    def create_options_frame(self, parent):
        """Create options configuration frame"""
        options_frame = LabelFrame(parent, text="Options", padx=5, pady=5)
        options_frame.pack(fill=X, pady=(0, 10))
        
        # PvE checkbox
        self.pve_var = BooleanVar()
        self.pve_var.set(self.config.getboolean('bot', 'pve', fallback=True))
        pve_check = Checkbutton(options_frame, text="PvE", variable=self.pve_var)
        pve_check.grid(row=0, column=0, sticky="w")
        
        # Mana level targets
        mana_frame = LabelFrame(options_frame, text="Mana Level Targets")
        mana_frame.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(5, 0))
        
        self.mana_vars = []
        for i in range(1, 6):
            var = BooleanVar()
            var.set(True)
            self.mana_vars.append(var)
            check = Checkbutton(mana_frame, text=f"Card {i}", variable=var)
            check.grid(row=0, column=i-1, sticky="w")
        
        # Dungeon floor
        floor_frame = Frame(options_frame)
        floor_frame.grid(row=2, column=0, columnspan=5, sticky="ew", pady=(5, 0))
        
        Label(floor_frame, text="Dungeon Floor:").pack(side=LEFT)
        self.floor_var = StringVar()
        self.floor_var.set(self.config.get('bot', 'floor', fallback='7'))
        floor_entry = Entry(floor_frame, textvariable=self.floor_var, width=5)
        floor_entry.pack(side=LEFT, padx=(5, 0))

    def create_display_frame(self, parent):
        """Create combat display frame"""
        display_frame = LabelFrame(parent, text="Combat Display")
        display_frame.pack(fill=BOTH, expand=True)
        
        # Grid display (3x5)
        self.grid_frame = Frame(display_frame)
        self.grid_frame.pack(side=TOP, fill=X, padx=5, pady=5)
        
        self.grid_labels = []
        for row in range(3):
            label_row = []
            for col in range(5):
                label = Label(self.grid_frame, text="", width=8, height=4,
                             relief=RAISED, bg="lightgray")
                label.grid(row=row, column=col, padx=1, pady=1)
                label_row.append(label)
            self.grid_labels.append(label_row)
        
        # Log display
        log_frame = Frame(display_frame)
        log_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = Text(log_frame, wrap=WORD, state=DISABLED)
        scrollbar = Scrollbar(log_frame, orient=VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

    def create_control_frame(self, parent):
        """Create control buttons frame"""
        button_frame = Frame(parent)
        button_frame.pack(fill=X, pady=(10, 0))
        
        self.start_button = Button(button_frame, text="Start Bot",
                                  command=self.start_bot, bg="lightgreen")
        self.start_button.pack(side=LEFT, padx=(0, 5))
        
        self.stop_button = Button(button_frame, text="Stop Bot",
                                 command=self.stop_bot, bg="lightcoral", state=DISABLED)
        self.stop_button.pack(side=LEFT, padx=(0, 5))
        
        self.quit_button = Button(button_frame, text="Quit Bot",
                                 command=self.on_closing, bg="orange")
        self.quit_button.pack(side=RIGHT)

    def setup_logger(self):
        """Setup logger with GUI integration"""
        try:
            if LOGGER_AVAILABLE:
                self.logger = bot_logger.create_log_feed(self.log_text)
            else:
                # Fallback logger
                self.logger = logging.getLogger('GUI')
                if not self.logger.handlers:
                    handler = logging.StreamHandler()
                    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
                    handler.setFormatter(formatter)
                    self.logger.addHandler(handler)
                    self.logger.setLevel(logging.INFO)
            
            self.logger.info("Logger initialized successfully")
            
        except Exception as e:
            print(f"Logger setup failed: {e}")
            # Emergency fallback
            self.logger = logging.getLogger('FALLBACK')

    def update_status(self, message):
        """Update status bar and log"""
        self.status_label.config(text=f"Status: {message}")
        if hasattr(self, 'logger'):
            self.logger.info(message)

    def log_message(self, message):
        """Add message to log display"""
        try:
            self.log_text.config(state=NORMAL)
            self.log_text.insert(END, f"[{time.strftime('%H:%M:%S')}] {message}\\n")
            self.log_text.see(END)
            self.log_text.config(state=DISABLED)
        except Exception as e:
            print(f"Log message failed: {e}")

    def start_bot(self):
        """Start the bot with comprehensive error handling"""
        if self.running:
            self.update_status("Bot is already running!")
            return
        
        try:
            self.update_status("Initializing bot...")
            
            # Create bot instance
            if not BOT_CORE_AVAILABLE:
                messagebox.showerror("Error", "Bot core not available!")
                return
            
            self.bot_instance = bot_core.Bot(logger=self.logger)
            
            # Test connection
            if not self.bot_instance.is_connected():
                messagebox.showerror("Connection Error",
                                   "Could not connect to Android device.\\n"
                                   "Please check BlueStacks is running and ADB is enabled.")
                return
            
            self.update_status("ADB connection verified")
            
            # Update configuration
            self.update_config_from_gui()
            
            # Configure bot
            self.bot_instance.bot_stop = False
            
            # Start bot thread
            self.info_event = threading.Event()
            
            if BOT_HANDLER_AVAILABLE:
                target_function = bot_handler_simple.bot_loop
            else:
                target_function = self.simple_test_loop
            
            self.bot_thread = threading.Thread(
                target=target_function,
                args=(self.bot_instance, self.info_event),
                daemon=True
            )
            
            self.bot_thread.start()
            
            # Update GUI state
            self.running = True
            self.stop_flag = False
            self.start_button.config(state=DISABLED)
            self.stop_button.config(state=NORMAL)
            
            # Start info update
            self.start_info_updates()
            
            self.update_status("Bot started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            messagebox.showerror("Error", f"Failed to start bot:\\n{str(e)}")

    def simple_test_loop(self, bot, info_event):
        """Simple test loop if bot_handler_simple is not available"""
        iteration = 0
        max_iterations = 10
        
        while not bot.bot_stop and iteration < max_iterations:
            try:
                bot.combat_step = f"Test {iteration + 1}/{max_iterations}"
                bot.combat = "Simple Test Mode"
                
                if bot.getScreen():
                    bot.output = f"Screenshot {iteration + 1} successful"
                else:
                    bot.output = f"Screenshot {iteration + 1} failed"
                
                info_event.set()
                time.sleep(3)
                iteration += 1
                
            except Exception as e:
                bot.output = f"Test error: {str(e)}"
                info_event.set()
                break
        
        bot.output = "Test completed"
        info_event.set()

    def start_info_updates(self):
        """Start the info update thread"""
        def update_thread():
            while self.running and not self.stop_flag:
                try:
                    if self.info_event and self.info_event.wait(timeout=5):
                        self.root.after(0, self.update_display)
                        self.info_event.clear()
                    else:
                        # Check if bot thread is still alive
                        if self.bot_thread and not self.bot_thread.is_alive():
                            self.root.after(0, self.on_bot_stopped)
                            break
                except Exception as e:
                    self.logger.error(f"Update thread error: {e}")
                    break
        
        update_thread = threading.Thread(target=update_thread, daemon=True)
        update_thread.start()

    def update_display(self):
        """Update display with bot information"""
        try:
            if self.bot_instance:
                # Update grid display (simplified)
                for row in range(3):
                    for col in range(5):
                        self.grid_labels[row][col].config(text=f"{row},{col}")
                
                # Update status
                if hasattr(self.bot_instance, 'combat_step'):
                    status = f"Step: {self.bot_instance.combat_step or 'N/A'}"
                    if hasattr(self.bot_instance, 'combat'):
                        status += f" | {self.bot_instance.combat or 'N/A'}"
                    self.status_label.config(text=status)
                
                # Update log
                if hasattr(self.bot_instance, 'output') and self.bot_instance.output:
                    self.log_message(self.bot_instance.output)
                    self.bot_instance.output = ""  # Clear after display
                    
        except Exception as e:
            self.logger.error(f"Display update error: {e}")

    def stop_bot(self):
        """Stop the bot"""
        try:
            self.update_status("Stopping bot...")
            self.stop_flag = True
            
            if self.bot_instance:
                self.bot_instance.bot_stop = True
            
            if self.bot_thread:
                self.bot_thread.join(timeout=5)
                if self.bot_thread.is_alive():
                    self.logger.warning("Bot thread did not stop cleanly")
            
            self.on_bot_stopped()
            
        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")
            self.on_bot_stopped()  # Force state reset

    def on_bot_stopped(self):
        """Handle bot stopped state"""
        self.running = False
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
        self.update_status("Bot stopped")

    def update_config_from_gui(self):
        """Update config from GUI values"""
        try:
            # PvE setting
            self.config.set('bot', 'pve', str(self.pve_var.get()))
            
            # Floor setting
            floor_value = self.floor_var.get()
            if floor_value.isdigit():
                self.config.set('bot', 'floor', floor_value)
            
            # Mana levels
            mana_levels = []
            for i, var in enumerate(self.mana_vars, 1):
                if var.get():
                    mana_levels.append(str(i))
            
            if mana_levels:
                self.config.set('bot', 'mana_level', ','.join(mana_levels))
            
            self.save_config()
            
        except Exception as e:
            self.logger.error(f"Config update error: {e}")

    def update_units(self):
        """Update active units from config"""
        try:
            units_str = self.config.get('bot', 'units', fallback='demo, boreas, robot, dryad, franky_stein')
            units = [unit.strip() for unit in units_str.split(',')]
            
            # Ensure units directory exists
            if not os.path.exists('units'):
                os.makedirs('units')
            
            # Copy units from all_units to units directory
            copied_count = 0
            for unit in units:
                if not unit.endswith('.png'):
                    unit += '.png'
                
                source_path = os.path.join('all_units', unit)
                dest_path = os.path.join('units', unit)
                
                if os.path.exists(source_path):
                    import shutil
                    shutil.copy2(source_path, dest_path)
                    copied_count += 1
                else:
                    self.logger.warning(f"Unit not found: {unit}")
            
            self.logger.info(f"Updated {copied_count} units")
            
        except Exception as e:
            self.logger.error(f"Unit update error: {e}")

    def on_closing(self):
        """Handle window closing"""
        try:
            self.update_status("Shutting down...")
            
            if self.running:
                self.stop_bot()
            
            # Save config
            self.save_config()
            
            # Destroy GUI
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
            self.root.destroy()

    def run(self):
        """Start the GUI main loop"""
        try:
            print("Starting GUI main loop...")
            self.update_status("GUI ready - Connect BlueStacks and click Start Bot")
            self.root.mainloop()
        except Exception as e:
            print(f"GUI error: {e}")


def create_base():
    """Legacy compatibility function"""
    return Tk()


def main():
    """Main entry point"""
    try:
        # Change to script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if script_dir:
            os.chdir(script_dir)
        
        # Create and run GUI
        app = RR_bot()
        app.run()
        
    except KeyboardInterrupt:
        print("\\nInterrupted by user")
    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
