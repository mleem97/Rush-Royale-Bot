from tkinter import *
import os
import numpy as np
import threading
import logging
import configparser

# internal
import bot_handler
import bot_logger


class RRBotGUI:
    def __init__(self):
        self.stop_flag = False
        self.running = False
        self.info_ready = threading.Event()

        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        self.root = Tk()
        self.root.title("Rush Royale Bot")
        self.root.geometry("900x600")
        self.root.configure(background='#575559')
        self.root.resizable(True, True)

        # Frames für bessere Strukturierung
        self.frame_controls = Frame(self.root, bg='#444', padx=10, pady=5)
        self.frame_options = Frame(self.root, bg='#575559', padx=10, pady=5)
        self.frame_log = Frame(self.root, bg='#333', padx=10, pady=5)
        self.frame_status = Frame(self.root, bg='#575559', padx=10, pady=5)
        self.frame_combat = Frame(self.root, bg='#222', padx=10, pady=5)  # Kampfanzeige, wird versteckt

        self.frame_controls.pack(side=TOP, fill=X)
        self.frame_options.pack(side=LEFT, fill=Y, padx=10, pady=10)
        self.frame_log.pack(side=RIGHT, fill=BOTH, expand=True, padx=10, pady=10)
        self.frame_status.pack(side=BOTTOM, fill=X, padx=10, pady=10)
        
        self.create_controls()
        self.create_options()
        self.create_log_view()
        self.create_status_view()
        self.create_combat_view()
        
        self.frame_combat.pack_forget()  # Standardmäßig versteckt

        self.logger.debug('GUI started!')
        self.root.mainloop()

    def create_controls(self):
        Button(self.frame_controls, text="Start Bot", command=self.start_command, bg="#28a745", fg="#fff", padx=10).pack(side=LEFT, padx=5)
        Button(self.frame_controls, text="Stop Bot", command=self.stop_bot, bg="#dc3545", fg="#fff", padx=10).pack(side=LEFT, padx=5)
        Button(self.frame_controls, text="Quit Floor", command=self.leave_game, bg="#ffc107", fg="#000", padx=10).pack(side=LEFT, padx=5)

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

    def update_combat_view(self, text, in_combat):
        if in_combat:
            self.frame_combat.pack(side=BOTTOM, fill=X, padx=10, pady=10)
            self.combat_text.config(state=NORMAL)
            self.combat_text.delete(1.0, END)
            self.combat_text.insert(END, text)
            self.combat_text.config(state=DISABLED)
        else:
            self.frame_combat.pack_forget()

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
            # Hier prüft der Bot, ob ein Kampf läuft und aktualisiert das UI
            output = "Aktuelle Kampf-Infos..."  # Hier den tatsächlichen Kampflog einsetzen
            in_combat = "fighting" in output  # Prüft, ob "fighting" im Status ist
            self.update_combat_view(output, in_combat)

            self.root.update_idletasks()
            self.root.update()

        self.status_text.config(text="Gestoppt", fg="red")
        self.frame_combat.pack_forget()

if __name__ == "__main__":
    RRBotGUI()
