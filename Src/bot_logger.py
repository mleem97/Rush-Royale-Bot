"""
Rush Royale Bot Logger - Python 3.13 Compatible
Enhanced logging with modern Python features and type hints
"""
from __future__ import annotations

import logging
from tkinter import *
import re
import threading
from typing import Optional, Dict, Any, List, Union


# Logger classes
class TextHandler(logging.StreamHandler):

    def __init__(self, textctrl):
        logging.StreamHandler.__init__(self)  # initialize parent
        self.textctrl = textctrl
        self.root = textctrl.master
        
        # Find the root window
        while hasattr(self.root, 'master') and self.root.master:
            self.root = self.root.master
            
        # Load color map
        self.ansi_color_fg = {39: 'foreground default'}
        self.ansi_color_bg = {49: 'background default'}
        self.ansi_colors_dark = ['black', 'red', 'green', 'yellow', 'royal blue', 'magenta', 'cyan', 'light gray']
        self.ansi_colors_light = [
            'dark gray', 'tomato', 'light green', 'light goldenrod', 'light blue', 'pink', 'light cyan', 'white'
        ]
        # regular expressionto find ansi codes in string
        self.ansi_regexp = re.compile(r"\x1b\[((\d+;)*\d+)m")

        self.textctrl.tag_configure('foreground default', foreground=self.textctrl["fg"])
        self.textctrl.tag_configure('background default', background=self.textctrl["bg"])
        for i, (col_dark, col_light) in enumerate(zip(self.ansi_colors_dark, self.ansi_colors_light)):
            self.ansi_color_fg[30 + i] = 'foreground ' + col_dark
            self.ansi_color_fg[90 + i] = 'foreground ' + col_light
            self.ansi_color_bg[40 + i] = 'background ' + col_dark
            self.ansi_color_bg[100 + i] = 'background ' + col_light
            # tag configuration
            self.textctrl.tag_configure('foreground ' + col_dark, foreground=col_dark)
            self.textctrl.tag_configure('background ' + col_dark, background=col_dark)
            self.textctrl.tag_configure('foreground ' + col_light, foreground=col_light)
            self.textctrl.tag_configure('background ' + col_light, background=col_light)

    def emit(self, record):
        """Thread-safe emit method that schedules GUI updates in main thread"""
        msg = self.format(record)
        
        # Check if we're in the main thread
        if threading.current_thread() is threading.main_thread():
            # We're in the main thread, safe to update GUI directly
            self._emit_to_gui(msg)
        else:
            # We're in a worker thread, schedule GUI update in main thread
            try:
                if self.root and hasattr(self.root, 'after'):
                    self.root.after(0, self._emit_to_gui, msg)
                else:
                    # Fallback: print to console if GUI is not available
                    print(f"[THREAD LOG] {msg}")
            except Exception as e:
                # Emergency fallback: print to console
                print(f"[LOGGER ERROR] {msg}")
                print(f"[LOGGER ERROR] GUI update failed: {e}")

    def _emit_to_gui(self, msg):
        """Update GUI with log message - must be called from main thread"""
        try:
            if self.textctrl and hasattr(self.textctrl, 'config'):
                self.textctrl.config(state="normal")
                self.insert_ansi(msg, "end")
                # scroll to the bottom
                self.textctrl.see("end")
                self.textctrl.config(state="disabled")
        except Exception as e:
            # If GUI update fails, print to console
            print(f"[GUI UPDATE ERROR] {msg}")
            print(f"[GUI UPDATE ERROR] {e}")

    # Functions to color messages according to utf-8 color codes set by formatter
    def insert_ansi(self, txt, index="insert"):
        first_line, first_char = map(int, str(self.textctrl.index(index)).split("."))
        if index == "end":
            first_line -= 1

        lines = txt.splitlines()
        if not lines:
            return
        # insert text without ansi codes
        self.textctrl.insert(index, self.ansi_regexp.sub('', txt) + '\n')
        # find all ansi codes in txt and apply corresponding tags
        opened_tags = {}  # we need to keep track of the opened tags to be able to do

        # text.tag_add(tag, start, end) when we reach a "closing" ansi code

        def apply_formatting(code, code_index):
            if code == 0:  # reset all by closing all opened tag
                for tag, start in opened_tags.items():
                    self.textctrl.tag_add(tag, start, code_index)
                opened_tags.clear()
            elif code in self.ansi_color_fg:  # open foreground color tag (and close previously opened one if any)
                for tag in tuple(opened_tags):
                    if tag.startswith('foreground'):
                        self.textctrl.tag_add(tag, opened_tags[tag], code_index)
                        opened_tags.remove(tag)
                opened_tags[self.ansi_color_fg[code]] = code_index
            elif code in self.ansi_color_bg:  # open background color tag (and close previously opened one if any)
                for tag in tuple(opened_tags):
                    if tag.startswith('background'):
                        self.textctrl.tag_add(tag, opened_tags[tag], code_index)
                        opened_tags.remove(tag)
                opened_tags[self.ansi_color_bg[code]] = code_index

        def find_ansi(line_txt, line_nb, char_offset):
            delta = -char_offset  # difference between the character position in the original line and in the text widget
            # (initial offset due to insertion position if first line + extra offset due to deletion of ansi codes)
            for match in self.ansi_regexp.finditer(line_txt):
                codes = [int(c) for c in match.groups()[0].split(';')]
                start, end = match.span()
                for code in codes:
                    apply_formatting(code, "{}.{}".format(line_nb, start - delta))
                delta += end - start  # take into account offste due to deletion of ansi code

        find_ansi(lines[0], first_line, first_char)  # first line, with initial offset due to insertion position
        for line_nb, line in enumerate(lines[1:], first_line + 1):
            find_ansi(line, line_nb, 0)  # next lines, no offset
        # close still opened tag
        for tag, start in opened_tags.items():
            self.textctrl.tag_add(tag, start, "end")

    def flush(self):
        """Thread-safe flush method"""
        # Nothing needed here since emit() handles everything
        pass


class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    blue = "\x1b[36;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = '[%(asctime)s] %(message)s'

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, "%H:%M")
        return formatter.format(record)


# function used by bot gui to create color coded logs
def create_log_feed(log_feed):
    logging.basicConfig(filename='RR_bot.log', level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.handlers.clear()
    guiHandler = TextHandler(log_feed)
    formatter = CustomFormatter()
    guiHandler.setFormatter(formatter)
    logger.addHandler(guiHandler)
    return logger