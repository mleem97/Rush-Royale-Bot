from tkinter import *
import os
import numpy as np
import threading
import logging
import configparser
import time

# internal
import bot_handler
import bot_logger

class RRBotGUI:
    def __init__(self):
        self.stop_flag = False
        self.running = False
        self.paused = False
        self.info_ready = threading.Event()

        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        self.root = Tk()
        self.root.title("Rush Royale Bot")
        self.root.geometry("900x600")
        self.root.configure(background='#575559')
        self.root.resizable(True, True)

        self.frame_controls = Frame(self.root, bg='#444', padx=10, pady=5)
        self.frame_options = Frame(self.root, bg='#575559', padx=10, pady=5)
        self.frame_log = Frame(self.root, bg='#333', padx=10, pady=5)
        self.frame_status = Frame(self.root, bg='#575559', padx=10, pady=5)
        self.frame_combat = Frame(self.root, bg='#222', padx=10, pady=5)

        self.frame_controls.pack(side=TOP, fill=X)
        self.frame_options.pack(side=LEFT, fill=Y, padx=10, pady=10)
        self.frame_log.pack(side=RIGHT, fill=BOTH, expand=True, padx=10, pady=10)
        self.frame_status.pack(side=BOTTOM, fill=X, padx=10, pady=10)
        
        self.create_controls()
        self.create_options()
        self.create_log_view()
        self.create_status_view()
        self.create_combat_view()
        
        self.frame_combat.pack_forget()

        self.logger.debug('GUI started!')
        self.root.mainloop()

    def create_controls(self):
        Button(self.frame_controls, text="Start Bot", command=self.start_command, bg="#28a745", fg="#fff", padx=10).pack(side=LEFT, padx=5)
        Button(self.frame_controls, text="Pause Bot", command=self.pause_bot, bg="#17a2b8", fg="#fff", padx=10).pack(side=LEFT, padx=5)
        Button(self.frame_controls, text="Stop Bot", command=self.stop_bot, bg="#dc3545", fg="#fff", padx=10).pack(side=LEFT, padx=5)
        Button(self.frame_controls, text="Quit Level", command=self.quit_level, bg="#ffc107", fg="#000", padx=10).pack(side=LEFT, padx=5)
    
    def start_command(self):
        self.stop_flag = False
        self.paused = False
        if self.running:
            return
        self.running = True
        threading.Thread(target=self.start_bot, args=()).start()
    
    def start_bot(self):
        self.logger.warning('Bot wird gestartet...')
        self.bot_instance = bot_handler.start_bot_class(self.logger)
        if not self.bot_instance:
            self.logger.error('Bot konnte nicht gestartet werden.')
            return
        self.bot_instance.bot_stop = False
        self.bot_instance.logger = self.logger
        self.bot_instance.config = self.config
        self.status_text.config(text="Läuft", fg="yellow")
        while not self.stop_flag:
            if self.paused:
                time.sleep(1)
                continue
            bot_handler.bot_loop(self.bot_instance, self.info_ready)

    def pause_bot(self):
        self.paused = not self.paused
        if self.paused:
            self.logger.info('Bot pausiert!')
            self.status_text.config(text="Pausiert", fg="orange")
        else:
            self.logger.info('Bot fortgesetzt!')
            self.status_text.config(text="Läuft", fg="yellow")
    
    def stop_bot(self):
        self.running = False
        self.stop_flag = True
        self.logger.info('Bot wird gestoppt!')
        self.status_text.config(text="Gestoppt", fg="red")
    
    def quit_level(self):
        if hasattr(self, 'bot_instance'):
            threading.Thread(target=self.bot_instance.restart_RR, args=(True,)).start()
        else:
            self.logger.warning('Bot wurde noch nicht gestartet!')
    
    def create_options(self):
        Label(self.frame_options, text="Bot Optionen", bg='#575559', fg='white', font=('Arial', 12, 'bold')).pack(anchor=W)
        
        self.pve_var = IntVar(value=int(self.config.getboolean('bot', 'pve')))
        self.floor = StringVar(value=self.config['bot']['floor'])
        self.mana_vars = [IntVar(value=int(i in np.fromstring(self.config['bot']['mana_level'], dtype=int, sep=','))) for i in range(1, 6)]
        
        Checkbutton(self.frame_options, text='PvE Modus', variable=self.pve_var, bg='#575559', fg='white').pack(anchor=W)
        Label(self.frame_options, text="Dungeon Floor", bg='#575559', fg='white').pack(anchor=W)
        Entry(self.frame_options, textvariable=self.floor, width=5).pack(anchor=W)
        
        Label(self.frame_options, text="Mana Level", bg='#575559', fg='white').pack(anchor=W)
        for i in range(5):
            Checkbutton(self.frame_options, text=f'Karte {i+1}', variable=self.mana_vars[i], bg='#575559', fg='white').pack(anchor=W)
    
    def create_log_view(self):
        Label(self.frame_log, text="Bot Log", bg='#333', fg='white', font=('Arial', 12, 'bold')).pack(anchor=W)
        self.logger_feed = Text(self.frame_log, height=30, width=50, bg='#222', fg='#ddd', wrap=WORD, font=('Consolas', 9))
        self.logger_feed.pack(fill=BOTH, expand=True)
        self.logger = bot_logger.create_log_feed(self.logger_feed)
    
    def create_status_view(self):
        Label(self.frame_status, text="Status", bg='#575559', fg='white', font=('Arial', 12, 'bold')).pack(anchor=W)
        self.status_text = Label(self.frame_status, text="Bereit", bg='#575559', fg='lightgreen', font=('Arial', 10))
        self.status_text.pack(anchor=W)
    
    def create_combat_view(self):
        Label(self.frame_combat, text="Kampfstatus", bg='#222', fg='white', font=('Arial', 12, 'bold')).pack(anchor=W)
        self.combat_text = Text(self.frame_combat, height=15, width=80, bg='#111', fg='#ddd', wrap=WORD, font=('Consolas', 9))
        self.combat_text.pack(fill=BOTH, expand=True)

    def update_config(self):
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

    def update_units(self):
        self.selected_units = self.config['bot']['units'].replace(' ', '').split(',')
        self.logger.info(f'Selected units: {", ".join(self.selected_units)}')
        if not bot_handler.select_units([unit + '.png' for unit in self.selected_units]):
            valid_units = ' '.join(os.listdir("all_units")).replace('.png', '').split(' ')
            self.logger.info(f'Invalid units in config file! Valid units: {valid_units}')

    def update_text(self, i, combat, output, grid_df, unit_series, merge_series, info):
        if grid_df is not None:
            grid_df['unit'] = grid_df['unit'].apply(lambda x: x.replace('.png', '').replace('empty', '-'))
            num_demons = str(grid_df[grid_df['unit'] == 'demon_hunter']['rank'].sum())
            avg_age = str(grid_df['Age'].mean().round(2))
            write_to_widget(self.root, self.grid_dump, f"{combat}, {i+1}/8 {output}, {info}\n{grid_df.to_string()}\nAverage age: {avg_age}\tNumber of demon ranks: {num_demons}")
        if unit_series is not None:
            write_to_widget(self.root, self.unit_dump, unit_series.to_string())
        if merge_series is not None:
            write_to_widget(self.root, self.merge_dump, merge_series.to_string())

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

def write_to_widget(root, tbox, text):
    tbox.config(state=NORMAL)
    tbox.delete(1.0, END)
    tbox.insert(END, text)
    tbox.config(state=DISABLED)
    root.update_idletasks()

if __name__ == "__main__":
    RRBotGUI()