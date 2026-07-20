"""Rush Royale Bot GUI."""
from __future__ import annotations

import configparser
import os
import threading
from pathlib import Path
from tkinter import *

import numpy as np

import bot_handler
import bot_logger

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config.ini"
STARTUP_MESSAGE_PATH = REPO_ROOT / "Src" / "startup_message.txt"
ALL_UNITS_DIR = REPO_ROOT / "all_units"

os.chdir(REPO_ROOT)


class RR_bot:
    def __init__(self):
        self.stop_flag = False
        self.running = False
        self.info_ready = threading.Event()
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_PATH)
        self.root = create_base()
        self.frames = self.root.winfo_children()
        self.ads_var, self.pve_var, self.mana_vars, self.floor = create_options(
            self.frames[0], self.config
        )
        self.grid_dump, self.unit_dump, self.merge_dump = create_combat_info(
            self.frames[1]
        )

        background = "#575559"
        foreground = "#ffffff"
        logger_feed = Text(
            self.frames[3],
            height=30,
            width=38,
            bg=background,
            fg=foreground,
            wrap=WORD,
            font=("Consolas", 9),
        )
        logger_feed.grid(row=0, sticky=S)
        self.logger = bot_logger.create_log_feed(logger_feed)
        Button(self.frames[2], text="Start Bot", command=self.start_command).grid(
            row=0, column=1, padx=10
        )
        Button(
            self.frames[2], text="Stop Bot", command=self.stop_bot, padx=20
        ).grid(row=0, column=2, padx=5)
        Button(
            self.frames[2],
            text="Quit Floor",
            command=self.leave_game,
            bg="#ff0000",
            fg="#000000",
        ).grid(row=0, column=3, padx=5)

        self.frames[0].pack(padx=0, pady=0, side=TOP, anchor=NW)
        self.frames[1].pack(padx=10, pady=10, side=RIGHT, anchor=SE)
        self.frames[2].pack(padx=10, pady=10, side=BOTTOM, anchor=SW)
        self.frames[3].pack(padx=10, pady=10, side=LEFT, anchor=SW)
        self.logger.debug("GUI started!")
        self.root.mainloop()

    def __exit__(self, exc_type, exc_value, traceback):
        self.logger.info("Exiting GUI")
        self.logger.handlers.clear()
        for attribute in ("thread_run", "thread_init"):
            thread = getattr(self, attribute, None)
            if thread and thread.is_alive():
                thread.join(timeout=5)
        self.root.destroy()
        try:
            self.bot_instance.client.stop()
        except (AttributeError, RuntimeError):
            pass

    def start_command(self):
        self.stop_flag = False
        self.update_config()
        if self.running:
            return
        self.running = True
        self.thread_run = threading.Thread(target=self.start_bot, daemon=True)
        self.thread_run.start()

    def update_config(self):
        floor_var = int(self.floor.get())
        card_level = [var.get() for var in self.mana_vars] * np.arange(1, 6)
        card_level = card_level[card_level != 0]
        self.config.read(CONFIG_PATH)
        self.config["bot"]["floor"] = str(floor_var)
        self.config["bot"]["mana_level"] = np.array2string(
            card_level, separator=","
        )[1:-1]
        self.config["bot"]["pve"] = str(bool(self.pve_var.get()))
        with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
            self.config.write(config_file)
        self.logger.info("Stored settings to config!")

    def update_units(self):
        self.selected_units = self.config["bot"]["units"].replace(" ", "").split(",")
        self.logger.info(f"Selected units: {', '.join(self.selected_units)}")
        if not bot_handler.select_units(
            [unit + ".png" for unit in self.selected_units]
        ):
            valid_units = sorted(path.stem for path in ALL_UNITS_DIR.glob("*.png"))
            self.logger.info(
                f"Invalid units in config file! Valid units: {' '.join(valid_units)}"
            )

    def start_bot(self):
        self.logger.warning("Starting bot...")
        self.bot_instance = bot_handler.start_bot_class(self.logger)
        if STARTUP_MESSAGE_PATH.exists():
            startup_message = STARTUP_MESSAGE_PATH.read_text(encoding="utf-8").strip()
            if startup_message:
                self.logger.info(startup_message)
        self.update_units()
        infos_ready = threading.Event()
        self.bot_instance.bot_stop = False
        self.bot_instance.logger = self.logger
        self.bot_instance.config = self.config
        bot = self.bot_instance
        thread_bot = threading.Thread(
            target=bot_handler.bot_loop, args=(bot, infos_ready), daemon=True
        )
        thread_bot.start()
        while True:
            infos_ready.wait(timeout=5)
            self.update_text(
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
                if (
                    hasattr(self.bot_instance, "scrcpy_process")
                    and self.bot_instance.scrcpy_process
                ):
                    self.bot_instance.stop_scrcpy()
                self.logger.info("Bot stopped!")
                self.logger.critical("Safe to close gui")
                return

    def stop_bot(self):
        self.running = False
        self.stop_flag = True
        self.logger.info("Stopping bot!")

    def leave_game(self):
        if hasattr(self, "bot_instance"):
            threading.Thread(
                target=self.bot_instance.restart_RR, args=(True,), daemon=True
            ).start()
        else:
            self.logger.warning("Bot has not been started yet!")

    def update_text(self, index, combat, output, grid_df, unit_series, merge_series, info):
        if grid_df is not None:
            display_grid = grid_df.copy()
            display_grid["unit"] = display_grid["unit"].str.replace(".png", "", regex=False)
            display_grid["unit"] = display_grid["unit"].replace("empty", "-")
            num_demons = str(
                display_grid[display_grid["unit"] == "demon_hunter"]["rank"].sum()
            )
            avg_age = str(display_grid["Age"].mean().round(2))
            step = 0 if index is None else index + 1
            write_to_widget(
                self.root,
                self.grid_dump,
                f"{combat}, {step}/8 {output}, {info}\n{display_grid.to_string()}\n"
                f"Average age: {avg_age}\tNumber of demon ranks: {num_demons}",
            )
        if unit_series is not None:
            write_to_widget(self.root, self.unit_dump, unit_series.to_string())
        if merge_series is not None:
            write_to_widget(self.root, self.merge_dump, merge_series.to_string())


def create_options(frame1, config):
    frame1.grid_rowconfigure(0, weight=1)
    frame1.grid_columnconfigure(0, weight=1)
    Label(frame1, text="Options", justify=LEFT).grid(row=0, column=0, sticky=W)
    user_pve = int(config.getboolean("bot", "pve", fallback=True))
    pve_var = IntVar(value=user_pve)
    ads_var = IntVar()
    Checkbutton(frame1, text="PvE", variable=pve_var, justify=LEFT).grid(
        row=0, column=1, sticky=W
    )
    Label(frame1, text="Mana Level Targets", justify=LEFT).grid(
        row=2, column=0, sticky=W
    )
    stored_values = np.fromstring(config["bot"]["mana_level"], dtype=int, sep=",")
    mana_vars = [IntVar(value=int(index in stored_values)) for index in range(1, 6)]
    for index in range(5):
        Checkbutton(
            frame1,
            text=f"Card {index + 1}",
            variable=mana_vars[index],
            justify=LEFT,
        ).grid(row=2, column=index + 1)
    Label(frame1, text="Dungeon Floor", justify=LEFT).grid(
        row=3, column=0, sticky=W
    )
    floor = Entry(frame1, name="floor_entry", width=5)
    if config.has_option("bot", "floor"):
        floor.insert(0, config["bot"]["floor"])
    floor.grid(row=3, column=1)
    return ads_var, pve_var, mana_vars, floor


def create_combat_info(frame2):
    grid_dump = Text(frame2, height=18, width=60, bg="#575559", fg="#ffffff")
    unit_dump = Text(frame2, height=10, width=30, bg="#575559", fg="#ffffff")
    merge_dump = Text(frame2, height=10, width=30, bg="#575559", fg="#ffffff")
    grid_dump.grid(row=0, sticky=S)
    unit_dump.grid(row=1, column=0, sticky=W)
    merge_dump.grid(row=1, column=0, sticky=E)
    return grid_dump, unit_dump, merge_dump


def create_base():
    root = Tk()
    root.title("RR bot")
    root.geometry("800x600")
    root.configure(background="#575559")
    icon_path = REPO_ROOT / "calculon.ico"
    if icon_path.exists():
        try:
            root.iconbitmap(str(icon_path))
        except TclError:
            pass
    root.resizable(False, False)
    Frame(root)
    frame2 = Frame(root)
    frame2.grid_rowconfigure(0, weight=1)
    frame2.grid_columnconfigure(0, weight=1)
    frame3 = Frame(root, bg="#575559")
    frame3.grid_columnconfigure(0, weight=1)
    Frame(root)
    return root


def write_to_widget(root, text_box, text):
    text_box.config(state=NORMAL)
    text_box.delete(1.0, END)
    text_box.insert(END, text)
    text_box.config(state=DISABLED)
    root.update_idletasks()


if __name__ == "__main__":
    RR_bot()
