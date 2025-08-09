"""
Rush Royale Bot Handler - Python 3.13 Compatible
Enhanced download and installation handling
"""
from __future__ import annotations

import os
import time
import numpy as np
import logging
from subprocess import Popen, DEVNULL
from typing import Optional, Dict, Any, List
from pathlib import Path

# Image processing
import cv2
# internal
import port_scan
import bot_core
import bot_perception

import zipfile
import functools
import pathlib
import shutil
import requests
from tqdm.auto import tqdm


# from here https://stackoverflow.com/a/63831344
def download(url, filename):
    r = requests.get(url, stream=True, allow_redirects=True)
    if r.status_code != 200:
        r.raise_for_status()  # Will only raise for 4xx codes, so...
        raise RuntimeError(f"Request to {url} returned status code {r.status_code}")
    file_size = int(r.headers.get('Content-Length', 0))

    path = pathlib.Path(filename).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    desc = "(Unknown total file size)" if file_size == 0 else ""
    r.raw.read = functools.partial(r.raw.read, decode_content=True)  # Decompress if needed
    with tqdm.wrapattr(r.raw, "read", total=file_size, desc=desc) as r_raw:
        with path.open("wb") as f:
            shutil.copyfileobj(r_raw, f)

    return path


# Moves selected units from collection folder to deck folder for unit recognition options
def select_units(units):
    if os.path.isdir('units'):
        [os.remove('units/' + unit) for unit in os.listdir("units")]
    else:
        os.mkdir('units')
    # Read and write all images
    for new_unit in units:
        try:
            cv2.imwrite('units/' + new_unit, cv2.imread('all_units/' + new_unit))
        except Exception as e:
            print(e)
            print(f'{new_unit} not found')
            continue
    # Verify enough units were selected
    return len(os.listdir("units")) > 4


def start_bot_class(logger):
    # auto-install ADB if needed (removed scrcpy dependency)
    # ADB is included with pure-python-adb, no manual installation needed
    logger.info('Using pure-python-adb for Android device control')
    bot = bot_core.Bot()
    return bot


# Loop for combat actions
def combat_loop(bot, grid_df, mana_targets, user_target='demon_hunter.png'):
    time.sleep(0.2)
    # Upgrade units
    bot.mana_level(mana_targets, hero_power=True)
    # Spawn units
    bot.click(450, 1360)
    # Try to merge units
    grid_df, unit_series, merge_series, df_groups, info = bot.try_merge(prev_grid=grid_df, merge_target=user_target)
    return grid_df, unit_series, merge_series, df_groups, info


# Run the bot
def bot_loop(bot, info_event):
    # Load user config
    config = bot.config['bot']
    user_pve = config.getboolean('pve', True)
    bot.logger.warning(f'PVE is set to {user_pve}')
    user_floor = int(config.get('floor', 5))
    user_level = np.fromstring(config['mana_level'], dtype=int, sep=',')
    user_target = config['dps_unit'].split('.')[0] + '.png'
    # Load optional settings
    require_shaman = config.getboolean('require_shaman', False)
    max_loops = int(config.get('max_loops', 800))  # this will increase time waiting when logging in from mobile
    # Dev options (only adds images to dataset, rank ai can be trained with bot_perception.quick_train_model)
    train_ai = False
    # State variables
    wait = 0
    combat = 0
    watch_ad = False
    grid_df = None
    # Wait for login
    time.sleep(5)
    # Main loop
    bot.logger.debug(f'Bot mainloop started')
    # Wait for game to load
    while (not bot.bot_stop):
        # Fetch screen and check state
        output = bot.battle_screen(start=False)
        if output[1] == 'fighting':
            watch_ad = True
            wait = 0
            combat += 1
            if combat > max_loops:
                bot.restart_RR()
                combat = 0
                continue
            elif bot.bot_stop:
                return
            elif require_shaman and not (output[0]['icon'] == 'shaman_opponent.png').any():
                bot.logger.info('Shaman not found, checking again...')
                if any([(bot.battle_screen(start=False)[0]['icon'] == 'shaman_opponent.png').any() for i in range(1)]):
                    continue
                bot.logger.warning('Leaving game')
                bot.restart_RR(quick_disconnect=True)
            # Combat Section
            grid_df, bot.unit_series, bot.merge_series, bot.df_groups, bot.info = combat_loop(
                bot, grid_df, user_level, user_target)
            bot.grid_df = grid_df.copy()
            bot.combat = combat
            bot.output = output[1]
            bot.combat_step = 1
            info_event.set()
            # Wait until late stage in combat and if consistency is ok, not stagnate save all units for ML model
            if combat == 25 and 5 < grid_df['Age'].mean() < 50 and train_ai:
                bot_perception.add_grid_to_dataset()
        elif output[1] == 'home' and watch_ad:
            [bot.watch_ads() for i in range(3)]
            watch_ad = False
        else:
            combat = 0
            bot.logger.info(f'{output[1]}, wait count: {wait}')
            # Debug: Show what icons are detected
            if hasattr(output[0], 'values') and len(output[0]) > 0:
                detected_icons = output[0]['icon'].unique() if 'icon' in output[0].columns else []
                bot.logger.debug(f'Detected icons: {list(detected_icons)}')
            else:
                bot.logger.debug('No icons detected on screen')
                # Additional debug: Check if screenshot exists and is valid
                import os
                screenshot_path = f'bot_feed_{bot.device.split(":")[-1]}.png'
                if os.path.exists(screenshot_path):
                    file_size = os.path.getsize(screenshot_path)
                    bot.logger.debug(f'Screenshot file exists: {screenshot_path} ({file_size} bytes)')
                    # Force a new screenshot
                    bot.getScreen()
                    bot.logger.debug('Forced new screenshot capture')
                else:
                    bot.logger.warning(f'Screenshot file missing: {screenshot_path}')
            output = bot.battle_screen(start=True, pve=user_pve, floor=user_floor)
            wait += 1
            if wait > 40:
                bot.logger.info('RESTARTING')
                bot.restart_RR(),
                wait = 0


def check_adb_connection(logger):
    """Check if ADB can connect to devices (replaces scrcpy check)"""
    try:
        from ppadb.client import Client as AdbClient
        client = AdbClient()
        devices = client.devices()
        if devices:
            logger.info(f'Found {len(devices)} ADB device(s)')
            return True
        else:
            logger.warning('No ADB devices found - make sure BlueStacks is running')
            return False
    except ImportError:
        logger.error('pure-python-adb not installed')
        return False
    except Exception as e:
        logger.error(f'ADB connection failed: {e}')
        return False