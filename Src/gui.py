from tkinter import *
import os
import numpy as np
import threading
import logging
import configparser
import json

# internal
import bot_handler
import bot_logger
from debug_system import get_debug_system


# GUI Class
class RR_bot:

    def __init__(self):
        # State variables
        self.stop_flag = False
        self.running = False
        self.info_ready = threading.Event()
        # Read config file
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        
        # Initialize debug system
        self.debug_system = get_debug_system()
        debug_enabled = self.config.getboolean('debug', 'enabled', fallback=False)
        self.debug_system.set_enabled(debug_enabled)
        
        # Create tkinter window base
        self.root = create_base()
        self.frames = self.root.winfo_children()
        
        # Setup frame 1 (options)
        self.ads_var, self.pve_var, self.mana_vars, self.floor = create_options(self.frames[0], self.config)
        
        # Add debug controls to options frame
        self.debug_var = self.create_debug_controls(self.frames[0], debug_enabled)
        
        # Setup frame 2 (combat info)
        self.grid_dump, self.unit_dump, self.merge_dump = create_combat_info(self.frames[1])
        
        # Add debug info frame
        self.debug_info = self.create_debug_info(self.frames[1])
        
        ## rest need to be cleaned up
        # Log frame
        bg = '#575559'
        fg = '#ffffff'
        logger_feed = Text(self.frames[3], height=30, width=38, bg=bg, fg=fg, wrap=WORD, font=('Consolas', 9))
        logger_feed.grid(row=0, sticky=S)
        # Setup & Connect logger to text widget
        self.logger = bot_logger.create_log_feed(logger_feed)
        start_button = Button(self.frames[2], text="Start Bot", command=self.start_command)
        stop_button = Button(self.frames[2], text='Stop Bot', command=self.stop_bot, padx=20)
        leave_dungeon = Button(self.frames[2], text='Quit Floor', command=self.leave_game, bg='#ff0000', fg='#000000')
        debug_export_button = Button(self.frames[2], text='Export Debug', command=self.export_debug, bg='#4CAF50', fg='#000000')
        
        start_button.grid(row=0, column=1, padx=10)
        stop_button.grid(row=0, column=2, padx=5)
        leave_dungeon.grid(row=0, column=3, padx=5)
        debug_export_button.grid(row=0, column=4, padx=5)

        self.frames[0].pack(padx=0, pady=0, side=TOP, anchor=NW)
        self.frames[1].pack(padx=10, pady=10, side=RIGHT, anchor=SE)
        self.frames[2].pack(padx=10, pady=10, side=BOTTOM, anchor=SW)
        self.frames[3].pack(padx=10, pady=10, side=LEFT, anchor=SW)
        self.logger.debug('GUI started!')
        
        # Start debug info update thread
        if debug_enabled:
            self.debug_update_thread = threading.Thread(target=self.update_debug_info, daemon=True)
            self.debug_update_thread.start()
        
        self.root.mainloop()

    # Clear loggers, collect threads, and close window
    def __exit__(self, exc_type, exc_value, traceback):
        self.logger.info('Exiting GUI')
        self.logger.handlers.clear()
        self.thread_run.join()
        self.thread_init.join()
        self.root.destroy()
        try:
            self.bot_instance.client.stop()
        except:
            pass

    # Initilzie the thread for main bot
    def start_command(self):
        self.stop_flag = False
        self.update_config()
        if self.running:
            return
        self.running = True
        # Start main thread
        self.thread_run = threading.Thread(target=self.start_bot, args=())
        self.thread_run.start()

    # Update config file
    def update_config(self):
        # Update config file
        floor_var = int(self.floor.get())
        card_level = [var.get() for var in self.mana_vars] * np.arange(1, 6)
        card_level = card_level[card_level != 0]
        self.config.read('config.ini')
        self.config['bot']['floor'] = str(floor_var)
        self.config['bot']['mana_level'] = np.array2string(card_level, separator=',')[1:-1]
        self.config['bot']['pve'] = str(bool(self.pve_var.get()))
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        self.logger.info("Stored settings to config!")

    # Update unit selection
    def update_units(self):
        self.selected_units = self.config['bot']['units'].replace(' ', '').split(',')
        self.logger.info(f'Selected units: {", ".join(self.selected_units)}')
        if not bot_handler.select_units([unit + '.png' for unit in self.selected_units]):
            valid_units = ' '.join(os.listdir("all_units")).replace('.png', '').split(' ')
            self.logger.info(f'Invalid units in config file! Valid units: {valid_units}')

    # Run the bot
    def start_bot(self):
        # Run startup of bot instance
        self.logger.warning('Starting bot...')
        self.bot_instance = bot_handler.start_bot_class(self.logger)
        os.system("type src\\startup_message.txt")
        self.update_units()
        infos_ready = threading.Event()
        # Pass gui info to bot
        self.bot_instance.bot_stop = False
        self.bot_instance.logger = self.logger
        self.bot_instance.config = self.config
        bot = self.bot_instance
        # Start bot thread
        thread_bot = threading.Thread(target=bot_handler.bot_loop, args=([bot, infos_ready]))
        thread_bot.start()
        # Dump infos to gui whenever ready
        while (1):
            infos_ready.wait(timeout=5)
            self.update_text(bot.combat_step, bot.combat, bot.output, bot.grid_df, bot.unit_series, bot.merge_series,
                             bot.info)
            infos_ready.clear()
            if self.stop_flag:
                self.bot_instance.bot_stop = True
                self.logger.warning('Exiting main loop...')
                thread_bot.join()
                self.bot_instance.client.stop()
                self.logger.info('Bot stopped!')
                self.logger.critical('Safe to close gui')
                return

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

    def create_debug_controls(self, parent_frame, debug_enabled):
        """Create debug control UI elements"""
        # Debug section
        debug_label = Label(parent_frame, text="Debug Controls", justify=LEFT, fg='#FFD700')
        debug_label.grid(row=4, column=0, sticky=W)
        
        debug_var = IntVar(value=int(debug_enabled))
        debug_check = Checkbutton(parent_frame, text='Debug Mode', variable=debug_var, 
                                 command=self.toggle_debug, justify=LEFT, fg='#FFD700')
        debug_check.grid(row=4, column=1, sticky=W)
        
        return debug_var
    
    def create_debug_info(self, parent_frame):
        """Create debug information display"""
        debug_info = Text(parent_frame, height=8, width=60, bg='#2C2C2C', fg='#00FF00', 
                         font=('Consolas', 8))
        debug_info.grid(row=2, columnspan=2, sticky='ew', pady=5)
        return debug_info
    
    def toggle_debug(self):
        """Toggle debug mode on/off"""
        debug_enabled = bool(self.debug_var.get())
        self.debug_system.set_enabled(debug_enabled)
        
        # Update config file
        if not self.config.has_section('debug'):
            self.config.add_section('debug')
        self.config.set('debug', 'enabled', str(debug_enabled))
        
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        
        status = "ENABLED" if debug_enabled else "DISABLED"
        self.logger.info(f"Debug mode {status}")
        
        if debug_enabled and not hasattr(self, 'debug_update_thread'):
            self.debug_update_thread = threading.Thread(target=self.update_debug_info, daemon=True)
            self.debug_update_thread.start()
    
    def update_debug_info(self):
        """Update debug information display in real-time"""
        while True:
            try:
                if self.debug_system.enabled and hasattr(self, 'debug_info'):
                    summary = self.debug_system.get_debug_summary(5)  # Last 5 minutes
                    
                    debug_text = "=== DEBUG STATUS ===\n"
                    debug_text += f"Debug Enabled: {summary.get('debug_enabled', False)}\n"
                    debug_text += f"Recent Events: {summary.get('recent_events', 0)}\n"
                    debug_text += f"Warnings: {summary.get('warnings_count', 0)}\n"
                    debug_text += f"Errors: {summary.get('errors_count', 0)}\n"
                    
                    if 'event_types' in summary:
                        debug_text += "\nEvent Types:\n"
                        for event_type, count in summary['event_types'].items():
                            debug_text += f"  {event_type}: {count}\n"
                    
                    if 'last_event' in summary and summary['last_event']:
                        debug_text += f"\nLast Operation: {summary['last_event']}\n"
                    
                    if summary.get('current_grid_units', 0) > 0:
                        debug_text += f"Grid Units Tracked: {summary['current_grid_units']}\n"
                    
                    # Update GUI
                    if hasattr(self, 'debug_info'):
                        write_to_widget(self.root, self.debug_info, debug_text)
                
                threading.Event().wait(2.0)  # Update every 2 seconds
                
            except Exception as e:
                self.logger.error(f"Debug info update error: {e}")
                threading.Event().wait(5.0)  # Wait longer on error
    
    def export_debug(self):
        """Export debug session data"""
        try:
            if not self.debug_system.enabled:
                self.logger.warning("Debug mode is not enabled - no data to export")
                return
            
            filepath = self.debug_system.export_debug_session()
            self.logger.info(f"Debug data exported to: {filepath}")
            
            # Also show quick summary
            summary = self.debug_system.get_debug_summary(60)  # Last hour
            self.logger.info(f"Debug Summary - Events: {summary.get('recent_events', 0)}, "
                           f"Warnings: {summary.get('warnings_count', 0)}, "
                           f"Errors: {summary.get('errors_count', 0)}")
            
        except Exception as e:
            self.logger.error(f"Failed to export debug data: {e}")


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
    # Import version info
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))
        from version import get_version_info
        version_info = get_version_info()
        title = f"{version_info['name']} v{version_info['version']}"
    except ImportError:
        title = "Rush Royale Bot v2.0.0"
    
    root.title(title)
    root.geometry("800x600")
    # Set dark background
    root.configure(background='#575559')
    # Set window icon to png
    root.iconbitmap('calculon.ico')
    root.resizable(False, False)  # ai
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
    bot_gui = RR_bot()