"""
Rush Royale Bot GUI - Python 3.13 Compatible
Legacy Tkinter interface with modern Python features and enhanced error handling
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

# internal
try:
    import bot_handler
    import bot_logger
except ImportError as e:
    print(f"ERROR: Could not import bot modules: {e}")
    print("Make sure all dependencies are installed.")
    sys.exit(1)


# GUI Class
class RR_bot:

    def __init__(self):
        print("Creating GUI instance...")
        
        # State variables
        self.stop_flag = False
        self.running = False
        self.info_ready = threading.Event()
        self.bot_instance = None
        self.bot_thread = None
        
        # Validate environment before starting
        if not self.validate_environment():
            messagebox.showerror("Error", "Environment not properly configured. See console for details.")
            sys.exit(1)
        
        # Read config file
        self.config = configparser.ConfigParser()
        self.load_or_create_config()
        
        # Create tkinter window base
        self.root = create_base()
        
        # Set up window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.frames = self.root.winfo_children()
        # Setup frame 1 (options)
        self.ads_var, self.pve_var, self.mana_vars, self.floor = create_options(self.frames[0], self.config)
        # Setup frame 2 (combat info)
        self.grid_dump, self.unit_dump, self.merge_dump = create_combat_info(self.frames[1])
        ## rest need to be cleaned up
        # Log frame
        bg = '#575559'
        fg = '#ffffff'
        logger_feed = Text(self.frames[3], height=30, width=38, bg=bg, fg=fg, wrap=WORD, font=('Consolas', 9))
        logger_feed.grid(row=0, sticky=S)
        # Setup & Connect logger to text widget
        self.logger = bot_logger.create_log_feed(logger_feed)
        
        # Add system check button
        system_check_button = Button(self.frames[2], text="System Check", command=self.run_system_check, bg='#4CAF50', fg='#000000')
        start_button = Button(self.frames[2], text="Start Bot", command=self.start_command)
        stop_button = Button(self.frames[2], text='Stop Bot', command=self.stop_bot, padx=20)
        leave_dungeon = Button(self.frames[2], text='Quit Floor', command=self.leave_game, bg='#ff0000', fg='#000000')
        
        system_check_button.grid(row=0, column=0, padx=5)
        start_button.grid(row=0, column=1, padx=10)
        stop_button.grid(row=0, column=2, padx=5)
        leave_dungeon.grid(row=0, column=3, padx=5)

        self.frames[0].pack(padx=0, pady=0, side=TOP, anchor=NW)
        self.frames[1].pack(padx=10, pady=10, side=RIGHT, anchor=SE)
        self.frames[2].pack(padx=10, pady=10, side=BOTTOM, anchor=SW)
        self.frames[3].pack(padx=10, pady=10, side=LEFT, anchor=SW)
        self.logger.debug('GUI started!')
        
        print("GUI instance created successfully")
        
        # Don't start mainloop in __init__ - this blocks the constructor
        # mainloop will be started by the main function
    
    def run(self):
        """Start the GUI main loop - call this after creating the instance"""
        self.root.mainloop()

    def validate_environment(self):
        """Validates the environment before starting"""
        try:
            # Check critical directories
            required_dirs = ['icons', 'all_units']
            for dir_path in required_dirs:
                if not os.path.isdir(dir_path):
                    print(f"ERROR: Directory '{dir_path}' not found!")
                    return False
            
            # Check critical modules
            required_modules = ['cv2', 'numpy', 'pandas', 'sklearn']
            for module in required_modules:
                try:
                    __import__(module)
                except ImportError:
                    print(f"ERROR: Module '{module}' not installed!")
                    return False
            
            return True
        except Exception as e:
            print(f"ERROR during environment validation: {e}")
            return False

    def load_or_create_config(self):
        """Loads config.ini or creates a default configuration"""
        if os.path.exists('config.ini'):
            self.config.read('config.ini')
        else:
            # Create default configuration
            self.config['bot'] = {
                'floor': '7',
                'mana_level': '1,2,3,4,5',
                'units': 'demo, boreas, robot, dryad, franky_stein',
                'dps_unit': 'boreas',
                'pve': 'False',
                'require_shaman': 'False'
            }
            self.config['rl_system'] = {
                'enabled': 'False'
            }
            with open('config.ini', 'w') as configfile:
                self.config.write(configfile)

    def run_system_check(self):
        """Runs System Check"""
        try:
            from system_check import main as system_check_main
            self.logger.info("Running System Check...")
            
            # Run System Check in separate thread
            def run_check():
                try:
                    result = system_check_main()
                    if result:
                        self.logger.info("✅ System Check successful!")
                    else:
                        self.logger.warning("⚠️ System Check with warnings!")
                except Exception as e:
                    self.logger.error(f"System Check error: {e}")
            
            thread = threading.Thread(target=run_check)
            thread.start()
            
        except ImportError:
            self.logger.error("System Check module not found!")
        except Exception as e:
            self.logger.error(f"Error during System Check: {e}")

    # Clear loggers, collect threads, and close window
    def cleanup(self):
        """Properly cleanup resources when closing GUI"""
        try:
            self.logger.info('Cleaning up GUI resources...')
            
            # Set stop flags
            self.stop_flag = True
            self.running = False
            
            # Stop bot if running
            if hasattr(self, 'bot_instance') and self.bot_instance:
                self.bot_instance.bot_stop = True
                self.logger.info('Bot stop signal sent')
            
            # Wait for threads to finish
            if hasattr(self, 'thread_run') and self.thread_run.is_alive():
                self.logger.info('Waiting for bot thread to finish...')
                self.thread_run.join(timeout=5)
                
                if self.thread_run.is_alive():
                    self.logger.warning('Bot thread did not finish within timeout')
            
            # Clear logger handlers
            self.logger.handlers.clear()
            
            # Destroy GUI
            if hasattr(self, 'root'):
                self.root.quit()  # Exit mainloop
                self.root.destroy()  # Destroy window
                
            self.logger.info('GUI cleanup completed')
            
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def on_closing(self):
        """Handle window close event"""
        self.cleanup()
    
    def __del__(self):
        """Destructor - ensure cleanup happens"""
        try:
            self.cleanup()
        except:
            pass

    # Initialize the thread for main bot
    def update_config(self):
        """Update configuration based on GUI settings"""
        try:
            # Update config with current GUI values
            self.config.set('bot', 'pve', str(self.pve_var.get()))
            
            # Update mana targets
            mana_targets = []
            for i, var in enumerate(self.mana_vars, 1):
                if var.get():
                    mana_targets.append(str(i))
            self.config.set('bot', 'mana_level', ','.join(mana_targets))
            
            # Update floor
            floor_value = str(self.floor.get())
            if floor_value.isdigit():
                self.config.set('bot', 'floor', floor_value)
            
            # Save to file
            with open('config.ini', 'w') as configfile:
                self.config.write(configfile)
                
            self.logger.debug('Configuration updated')
            
        except Exception as e:
            self.logger.error(f'Failed to update config: {e}')

    # Update unit selection
    def update_units(self):
        self.selected_units = self.config['bot']['units'].replace(' ', '').split(',')
        self.logger.info(f'Selected units: {", ".join(self.selected_units)}')
        if not bot_handler.select_units([unit + '.png' for unit in self.selected_units]):
            valid_units = ' '.join(os.listdir("all_units")).replace('.png', '').split(' ')
            self.logger.info(f'Invalid units in config file! Valid units: {valid_units}')

    # Run the bot
    def start_bot(self):
        """Start bot with comprehensive error handling and connection testing"""
        try:
            self.logger.warning('Starting bot...')
            
            # Check if bot is already running
            if self.running:
                self.logger.warning('Bot is already running!')
                return
            
            # Enhanced error handling for bot creation
            try:
                # Import bot_core directly for better control
                import bot_core
                
                # Create bot instance with logger
                self.bot_instance = bot_core.Bot(logger=self.logger)
                self.logger.info('✅ Bot core instance created successfully')
                
                # Test connection immediately
                if not self.bot_instance.is_connected():
                    self.logger.error('❌ ADB connection test failed')
                    messagebox.showerror("Connection Error", 
                                       "Could not connect to Android device.\n"
                                       "Please check BlueStacks is running and ADB is enabled.")
                    return
                else:
                    self.logger.info('✅ ADB connection verified')
                
            except Exception as e:
                self.logger.error(f'❌ Failed to create bot instance: {e}')
                messagebox.showerror("Bot Creation Error", 
                                   f"Failed to create bot instance:\n{str(e)}")
                return
            
            # Check if startup message exists
            startup_file = r"Src\startup_message.txt"
            if os.path.exists(startup_file):
                try:
                    with open(startup_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.logger.info(f'Startup message:\n{content}')
                except Exception as e:
                    self.logger.debug(f'Could not read startup message: {e}')
            
            # Enhanced error handling for unit update
            try:
                self.update_units()
                self.logger.info('✅ Units updated successfully')
            except Exception as e:
                self.logger.warning(f'⚠️ Failed to update units (continuing anyway): {e}')
            
            # Create event for thread communication
            infos_ready = threading.Event()
            
            # Configure bot with GUI settings
            try:
                self.bot_instance.bot_stop = False
                self.bot_instance.logger = self.logger
                self.bot_instance.config = self.config
                bot = self.bot_instance
                self.logger.info('✅ Bot configuration completed')
            except Exception as e:
                self.logger.error(f'❌ Failed to configure bot: {e}')
                return
            
            # Start bot thread with enhanced error handling
            try:
                # Use simplified bot handler for initial testing
                import bot_handler_simple
                
                thread_bot = threading.Thread(
                    target=bot_handler_simple.bot_loop, 
                    args=(bot, infos_ready),
                    daemon=True  # Daemon thread for cleaner shutdown
                )
                thread_bot.start()
                self.logger.info('✅ Bot thread started successfully')
                
                # Set running state
                self.running = True
                self.stop_flag = False
                
                # Start info update loop
                self.start_info_update_loop(infos_ready, thread_bot)
                
            except Exception as e:
                self.logger.error(f'❌ Failed to start bot thread: {e}')
                messagebox.showerror("Thread Error", 
                                   f"Failed to start bot thread:\n{str(e)}")
                return
            
        except Exception as e:
            self.logger.error(f'❌ Critical error in start_bot: {e}')
            messagebox.showerror("Critical Error", 
                               f"Critical error starting bot:\n{str(e)}")
            self.running = False

    def start_info_update_loop(self, infos_ready, thread_bot):
        """Start the info update loop in a separate method for better organization"""
        def info_update_thread():
            try:
                while self.running and not self.stop_flag and thread_bot.is_alive():
                    try:
                        # Wait for bot to signal new info (with timeout)
                        if infos_ready.wait(timeout=5):
                            # Schedule GUI update in main thread
                            self.root.after(0, self.update_display)
                            infos_ready.clear()
                        else:
                            # Timeout - bot might be stuck
                            self.logger.debug("Info update timeout - bot may be busy")
                            
                    except Exception as e:
                        self.logger.error(f"Info update error: {e}")
                        break
                        
                # Thread ended
                self.root.after(0, self.on_bot_thread_ended)
                
            except Exception as e:
                self.logger.error(f"Info update thread error: {e}")
        
        # Start info update thread
        info_thread = threading.Thread(target=info_update_thread, daemon=True)
        info_thread.start()

    def update_display(self):
        """Update GUI display with bot information (thread-safe)"""
        try:
            if self.bot_instance:
                # Update text displays with bot status
                if hasattr(self.bot_instance, 'combat_step') and self.bot_instance.combat_step:
                    self.update_text(
                        self.bot_instance.combat_step,
                        self.bot_instance.combat or "No combat data",
                        self.bot_instance.output or "No output",
                        "N/A",  # Grid info
                        "N/A",  # Unit info  
                        "N/A",  # Merge info
                        "N/A"   # Additional info
                    )
                    
                # Clear output after displaying
                if hasattr(self.bot_instance, 'output'):
                    self.bot_instance.output = ""
                    
        except Exception as e:
            self.logger.error(f"Display update error: {e}")

    def on_bot_thread_ended(self):
        """Handle bot thread ending (called from main thread)"""
        self.running = False
        self.logger.info("Bot thread has ended")
        
        # Update GUI to reflect stopped state
        try:
            if hasattr(self, 'start_button'):
                self.start_button.config(state=NORMAL)
            if hasattr(self, 'stop_button'):
                self.stop_button.config(state=DISABLED)
        except:
            pass

    def start_command(self):
        """Wrapper for start_bot to maintain compatibility"""
        self.start_bot()

    def stop_bot(self):
        """Stop the bot with proper cleanup"""
        try:
            self.logger.info('Stopping bot...')
            self.stop_flag = True
            
            if self.bot_instance:
                self.bot_instance.bot_stop = True
            
            if self.bot_thread and self.bot_thread.is_alive():
                self.bot_thread.join(timeout=5)
                if self.bot_thread.is_alive():
                    self.logger.warning('Bot thread did not stop cleanly')
            
            self.running = False
            self.logger.info('Bot stopped successfully')
            
        except Exception as e:
            self.logger.error(f'Error stopping bot: {e}')
            self.running = False

    def on_closing(self):
        """Handle window closing with proper cleanup"""
        try:
            if self.running:
                self.stop_bot()
            
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
            self.root.destroy()

    # Raise stop flag to threads
    def stop_bot(self):
        self.running = False
        self.stop_flag = True
        self.logger.info('Stopping bot!')

    # Leave current co-up game
    def leave_game(self):
        # check if bot_instance exists
        if hasattr(self, 'bot_instance'):
            thread_bot = threading.Thread(target=self.bot_instance.restart_RR, args=([True]))
            thread_bot.start()
        else:
            self.logger.warning('Bot has not been started yet!')

    # Update text widgets with latest info
    def update_text(self, i, combat, output, grid_df, unit_series, merge_series, info):
        # info + general info
        if grid_df is not None:
            grid_df['unit'] = grid_df['unit'].apply(lambda x: x.replace('.png', ''))
            grid_df['unit'] = grid_df['unit'].apply(lambda x: x.replace('empty', '-'))
            num_demons = str(grid_df[grid_df['unit'] == 'demon_hunter']['rank'].sum())
            avg_age = str(grid_df['Age'].mean().round(2))
            write_to_widget(
                self.root, self.grid_dump,
                f"{combat}, {i+1}/8 {output}, {info}\n{grid_df.to_string()}\nAverage age: {avg_age}\tNumber of demon ranks: {num_demons}"
            )
        if unit_series is not None:
            #unit_series['unit'] = unit_series['unit'].apply(lambda x: x.replace('.png',''))
            write_to_widget(self.root, self.unit_dump, unit_series.to_string())
        if merge_series is not None:
            #merge_series['unit'] = merge_series['unit'].apply(lambda x: x.replace('.png',''))
            write_to_widget(self.root, self.merge_dump, merge_series.to_string())


###
### END OF GUI CLASS
###


def create_options(frame1, config):
    frame1.grid_rowconfigure(0, weight=1)
    frame1.grid_columnconfigure(0, weight=1)

    # General options
    label = Label(frame1, text="Options", justify=LEFT).grid(row=0, column=0, sticky=W)
    if config.has_option('bot', 'pve'):
        user_pvp = int(config.getboolean('bot', 'pve'))
    pve_var = IntVar(value=user_pvp)
    ads_var = IntVar()
    pve_check = Checkbutton(frame1, text='PvE', variable=pve_var, justify=LEFT).grid(row=0, column=1, sticky=W)
    #ad_check = Checkbutton(frame1, text='Watch ads', variable=ads_var,justify=LEFT).grid(row=0, column=2, sticky=W)
    # Mana level targets
    mana_label = Label(frame1, text="Mana Level Targets", justify=LEFT).grid(row=2, column=0, sticky=W)
    stored_values = np.fromstring(config['bot']['mana_level'], dtype=int, sep=',')
    mana_vars = [IntVar(value=int(i in stored_values)) for i in range(1, 6)]
    mana_buttons = [
        Checkbutton(frame1, text=f'Card {i+1}', variable=mana_vars[i], justify=LEFT).grid(row=2, column=i + 1)
        for i in range(5)
    ]
    # Dungeon Floor
    floor_label = Label(frame1, text="Dungeon Floor", justify=LEFT).grid(row=3, column=0, sticky=W)
    floor = Entry(frame1, name='floor_entry', width=5)
    if config.has_option('bot', 'floor'):
        floor.insert(0, config['bot']['floor'])
    floor.grid(row=3, column=1)
    return ads_var, pve_var, mana_vars, floor


def create_combat_info(frame2):
    # Create text widgets
    grid_dump = Text(frame2, height=18, width=60, bg='#575559', fg='#ffffff')
    unit_dump = Text(frame2, height=10, width=30, bg='#575559', fg='#ffffff')
    merge_dump = Text(frame2, height=10, width=30, bg='#575559', fg='#ffffff')
    grid_dump.grid(row=0, sticky=S)
    unit_dump.grid(row=1, column=0, sticky=W)
    merge_dump.grid(row=1, column=0, sticky=E)
    return grid_dump, unit_dump, merge_dump


def create_base():
    root = Tk()
    root.title("RR bot")
    root.geometry("800x600")
    # Set dark background
    root.configure(background='#575559')
    
    # Set window icon with error handling
    try:
        if os.path.exists('calculon.ico'):
            root.iconbitmap('calculon.ico')
    except Exception as e:
        print(f"Warning: Could not load icon: {e}")
    
    root.resizable(False, False)
    
    # Add frames
    frame1 = Frame(root)
    frame2 = Frame(root)
    frame2.grid_rowconfigure(0, weight=1)
    frame2.grid_columnconfigure(0, weight=1)
    frame3 = Frame(root, bg='#575559')
    frame3.grid_columnconfigure(0, weight=1)
    frame4 = Frame(root)
    return root


# Function to update text widgets
def write_to_widget(root, tbox, text):
    tbox.config(state=NORMAL)
    tbox.delete(1.0, END)
    tbox.insert(END, text)
    tbox.config(state=DISABLED)
    root.update_idletasks()


# Start the actual bot
if __name__ == "__main__":
    try:
        print("Creating GUI instance...")
        bot_gui = RR_bot()
        print("GUI instance created successfully")
        
        print("Starting GUI main loop...")
        bot_gui.run()
        print("GUI closed")
        
    except KeyboardInterrupt:
        print("GUI interrupted by user")
    except Exception as e:
        print(f"GUI failed: {e}")
        import traceback
        traceback.print_exc()