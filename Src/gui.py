from tkinter import *
from tkinter import ttk
import os
import numpy as np
import threading
import logging
import configparser

# internal
import bot_handler
import bot_logger
import config_manager


# GUI Class
class RR_bot:

    def __init__(self):
        # State variables
        self.stop_flag = False
        self.running = False
        self.info_ready = threading.Event()
        # Read config file
        self.config_mgr = config_manager.ConfigManager()
        # Create tkinter window base
        self.root = create_base()
        self.frames = self.root.winfo_children()
        # Setup frame 1 (options)
        self.ads_var, self.pve_var, self.mana_vars, self.floor, self.unit_vars = create_options(self.frames[0], self.config_mgr)
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
        
        # Add control buttons
        start_button = Button(self.frames[2], text="Start Bot", command=self.start_command)
        stop_button = Button(self.frames[2], text='Stop Bot', command=self.stop_bot, padx=20)
        leave_dungeon = Button(self.frames[2], text='Quit Floor', command=self.leave_game, bg='#ff0000', fg='#000000')
        save_settings = Button(self.frames[2], text='Save Settings', command=self.save_settings, bg='#00ff00', fg='#000000')
        
        start_button.grid(row=0, column=0, padx=10)
        stop_button.grid(row=0, column=1, padx=5)
        leave_dungeon.grid(row=0, column=2, padx=5)
        save_settings.grid(row=0, column=3, padx=5)

        self.frames[0].pack(padx=0, pady=0, side=TOP, anchor=NW)
        self.frames[1].pack(padx=10, pady=10, side=RIGHT, anchor=SE)
        self.frames[2].pack(padx=10, pady=10, side=BOTTOM, anchor=SW)
        self.frames[3].pack(padx=10, pady=10, side=LEFT, anchor=SW)
        self.logger.debug('GUI started!')
        self.root.mainloop()

    # Clear loggers, collect threads, and close window
    def __exit__(self, exc_type, exc_value, traceback):
        self.logger.info('Exiting GUI')
        self.logger.handlers.clear()
        if hasattr(self, 'thread_run'):
            self.thread_run.join()
        if hasattr(self, 'thread_init'):
            self.thread_init.join()
        self.root.destroy()
        try:
            self.bot_instance.client.stop()
        except:
            pass

    # Initialize the thread for main bot
    def start_command(self):
        self.stop_flag = False
        self.save_settings()
        if self.running:
            return
        self.running = True
        # Start main thread
        self.thread_run = threading.Thread(target=self.start_bot, args=())
        self.thread_run.start()

    # Save settings to config
    def save_settings(self):
        # Update unit selection
        selected_units = [unit for i, unit in enumerate(os.listdir("all_units")) if i < len(self.unit_vars) and self.unit_vars[i].get()]
        
        # Format as comma-separated string
        unit_string = ", ".join([unit.replace('.png', '') for unit in selected_units])
        self.config_mgr.set('bot', 'units', unit_string)
        
        # Update floor
        floor_var = int(self.floor.get())
        self.config_mgr.set('bot', 'floor', str(floor_var))
        
        # Update mana levels
        card_level = [var.get() for var in self.mana_vars] * np.arange(1, 6)
        card_level = card_level[card_level != 0]
        self.config_mgr.set('bot', 'mana_level', ", ".join(map(str, card_level)))
        
        # Update PVE setting
        self.config_mgr.set('bot', 'pve', str(bool(self.pve_var.get())))
        
        # Save to file
        self.config_mgr.save()
        self.logger.info("Stored settings to config!")
        
        # Update units in unit directory
        self.update_units()

    # Update unit selection
    def update_units(self):
        selected_units = [unit for i, unit in enumerate(os.listdir("all_units")) if i < len(self.unit_vars) and self.unit_vars[i].get()]
        
        if not bot_handler.select_units(selected_units):
            valid_units = ' '.join(os.listdir("all_units")).replace('.png', '').split(' ')
            self.logger.info(f'Invalid units in config file! Valid units: {valid_units}')
        else:
            self.logger.info(f'Selected units: {", ".join([u.replace(".png", "") for u in selected_units])}')

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
        self.bot_instance.config = self.config_mgr.config  # For backward compatibility
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


###
### END OF GUI CLASS
###


def create_options(frame1, config_mgr):
    frame1.grid_rowconfigure(0, weight=1)
    frame1.grid_columnconfigure(0, weight=1)

    # Create notebook for tabs
    tab_control = ttk.Notebook(frame1)
    
    # Create tabs
    tab1 = Frame(tab_control)
    tab2 = Frame(tab_control)
    
    tab_control.add(tab1, text="General Options")
    tab_control.add(tab2, text="Unit Selection")
    tab_control.grid(row=0, column=0, columnspan=6, sticky="nsew")

    # General options (Tab 1)
    Label(tab1, text="Game Options", justify=LEFT, font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=W, pady=5)
    
    # PVE/PVP option
    user_pvp = config_mgr.getboolean('bot', 'pve', True)
    pve_var = IntVar(value=int(user_pvp))
    Checkbutton(tab1, text='PVE Mode', variable=pve_var, justify=LEFT).grid(row=1, column=0, sticky=W)
    
    # Ads option
    ads_var = IntVar()
    #Checkbutton(tab1, text='Watch ads', variable=ads_var, justify=LEFT).grid(row=1, column=1, sticky=W)
    
    # Dungeon floor
    Label(tab1, text="Dungeon Floor:", justify=LEFT).grid(row=2, column=0, sticky=W, pady=5)
    floor = Entry(tab1, name='floor_entry', width=5)
    floor.insert(0, config_mgr.get('bot', 'floor', '5'))
    floor.grid(row=2, column=1, sticky=W)
    
    # Mana level targets
    Label(tab1, text="Mana Level Targets:", justify=LEFT, font=('Arial', 10, 'bold')).grid(row=3, column=0, sticky=W, pady=5)
    mana_levels = config_mgr.getlist('bot', 'mana_level', [1, 2, 3, 4, 5], dtype=int)
    
    mana_vars = [IntVar(value=int(i in mana_levels)) for i in range(1, 6)]
    mana_frame = Frame(tab1)
    mana_frame.grid(row=4, column=0, columnspan=4, sticky=W)
    
    for i in range(5):
        Checkbutton(mana_frame, text=f'Card {i+1}', variable=mana_vars[i], justify=LEFT).grid(row=0, column=i, padx=10)
    
    # Unit selection (Tab 2)
    Label(tab2, text="Select 5 Units for Your Deck:", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=3, sticky=W, pady=5)
    
    # Get available units
    available_units = os.listdir("all_units")
    # Get selected units from config
    selected_units = config_mgr.getlist('bot', 'units', [], dtype=str)
    selected_units = [u + '.png' if not u.endswith('.png') else u for u in selected_units]
    
    # Create scrollable frame for units
    unit_frame = Frame(tab2)
    canvas = Canvas(unit_frame, height=300)
    scrollbar = Scrollbar(unit_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Create checkboxes for each unit
    unit_vars = []
    for i, unit in enumerate(available_units):
        unit_name = unit.replace('.png', '')
        
        # Check if this unit is in selected units
        is_selected = unit in selected_units
        
        var = IntVar(value=int(is_selected))
        unit_vars.append(var)
        
        row = i // 3
        col = i % 3
        
        unit_frame = Frame(scrollable_frame)
        unit_frame.grid(row=row, column=col, padx=5, pady=5)
        
        Checkbutton(unit_frame, text=unit_name, variable=var).pack()
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    unit_frame.grid(row=1, column=0, columnspan=6, sticky="nsew")
    
    return ads_var, pve_var, mana_vars, floor, unit_vars


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
    root.title("Rush Royale Bot")
    root.geometry("900x700")
    # Set dark background
    root.configure(background='#575559')
    # Set window icon to png
    root.iconbitmap('calculon.ico')
    root.resizable(True, True)
    # Add frames
    frame1 = Frame(root, bg='#575559')
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