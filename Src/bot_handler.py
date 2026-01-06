from __future__ import annotations

import functools
import os
import pathlib
import shutil
import time
from pathlib import Path
from subprocess import DEVNULL, check_output

import cv2
import numpy as np
import requests
from tqdm.auto import tqdm

try:
    from adbutils import adb

    _ADBUTILS_AVAILABLE = True
except Exception:
    adb = None
    _ADBUTILS_AVAILABLE = False

import bot_core
import bot_perception

# import port_scan # Uncomment if available


def _resolve_unit_template_path(unit_filename: str) -> Path | None:
    """Resolve a unit template path under `all_units/`.

    Supports both legacy flat layout (`all_units/<name>.png`) and the newer
    categorized layout (`all_units/<rarity>/<name>.png`).
    """

    all_units_dir = Path("all_units")
    direct = all_units_dir / unit_filename
    if direct.exists():
        return direct

    # Fall back to recursive search (small N: only a handful of selected units).
    matches = [p for p in all_units_dir.rglob(unit_filename) if p.is_file()]
    if not matches:
        return None

    # Prefer common rarity folders if multiple matches exist.
    preferred_parts = {"legendary", "rare", "common"}
    matches.sort(
        key=lambda p: (0 if any(part in preferred_parts for part in p.parts) else 1, len(p.parts))
    )
    return matches[0]

"""
Rush Royale Bot Handler - Python 3.13 Compatible
Enhanced download and installation handling
"""

def download(url, filename):
    r = requests.get(url, stream=True, allow_redirects=True)
    if r.status_code != 200:
        r.raise_for_status()  # Will only raise for 4xx codes
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

def select_units(units):
    """Moves selected units from collection folder to deck folder for unit recognition"""
    if os.path.isdir('units'):
        [os.remove('units/' + unit) for unit in os.listdir("units")]
    else:
        os.mkdir('units')
    
    # Read and write all images
    for new_unit in units:
        try:
            src_path = _resolve_unit_template_path(new_unit)
            if src_path is None:
                print(f'{new_unit} not found under all_units/')
                continue

            img = cv2.imread(str(src_path))
            if img is not None:
                cv2.imwrite('units/' + new_unit, img)
            else:
                print(f'Failed to read image: {new_unit} ({src_path})')
                
        except Exception as e:
            print(f'Error processing {new_unit}: {e}')
            continue
            
    # Verify enough units were selected
    return len(os.listdir("units")) > 4

def start_bot_class(logger):
    logger.info("Starting bot")
    bot = bot_core.Bot()
    return bot

def combat_loop(bot, grid_df, mana_targets, user_target='demon_hunter.png'):
    time.sleep(0.2)
    # Upgrade units
    bot.mana_level(mana_targets, hero_power=True)
    # Spawn units
    bot.click(450, 1360)
    # Try to merge units
    grid_df, unit_series, merge_series, df_groups, info = bot.try_merge(
        prev_grid=grid_df, 
        merge_target=user_target
    )
    return grid_df, unit_series, merge_series, df_groups, info

def bot_loop(bot, info_event):
    # Load user config
    config = bot.config['bot']
    unit_update = config.getboolean('unit_update', False)
    if unit_update:
        bot.logger.warning('Unit Update enabled: starting missing-units capture mode.')
        bot.unit_update_capture_missing_units()
        bot.logger.info('Unit Update mode finished. Disable "Unit Update" to run the normal bot.')
        return

    user_pve = config.getboolean('pve', True)
    bot.logger.warning(f'PVE is set to {user_pve}')
    
    user_floor = int(config.get('floor', 5))
    user_level = np.fromstring(config['mana_level'], dtype=int, sep=',')
    
    # Handle dps_unit format safely
    dps_unit = config.get('dps_unit', 'demon_hunter.png')
    user_target = dps_unit.split('.')[0] + '.png'
    
    # Load optional settings
    require_shaman = config.getboolean('require_shaman', False)
    max_loops = int(config.get('max_loops', 800))
    
    # Dev options
    train_ai = False
    
    # State variables
    wait = 0
    combat = 0
    watch_ad = False
    grid_df = None
    
    # Wait for login
    time.sleep(5)
    
    bot.logger.debug('Bot mainloop started')
    
    # Main Loop
    while not bot.bot_stop:
        # Fetch screen and check state
        output = bot.battle_screen(start=False)
        
        if output[1] == 'fighting':
            watch_ad = True
            wait = 0
            combat += 1
            
            if combat > max_loops:
                bot.restart_game()
                combat = 0
                continue
                
            elif bot.bot_stop:
                return
                
            elif require_shaman:
                if not (output[0]['icon'] == 'shaman_opponent.png').any():
                    bot.logger.info('Shaman not found, checking again...')
                # Quick re-check
                retry_screen = bot.battle_screen(start=False)
                if (retry_screen[0]['icon'] == 'shaman_opponent.png').any():
                    continue
                    
                bot.logger.warning('Leaving game (No Shaman)')
                bot.restart_game(quick_disconnect=True)
                continue

            # Combat Section
            grid_df, bot.unit_series, bot.merge_series, bot.df_groups, bot.info = combat_loop(
                bot, grid_df, user_level, user_target
            )
            
            bot.grid_df = grid_df.copy() if grid_df is not None else None
            bot.combat = combat
            bot.output = output[1]
            bot.combat_step = 1
            info_event.set()
            
            # AI Training Data Collection
            if grid_df is not None and combat == 25 and train_ai:
                if 'Age' in grid_df.columns and 5 < grid_df['Age'].mean() < 50:
                    bot_perception.add_grid_to_dataset()

        elif output[1] == 'home' and watch_ad:
            for _ in range(3):
                bot.watch_ads()
            watch_ad = False
            
        else:
            combat = 0
            bot.logger.info(f'{output[1]}, wait count: {wait}')
            
            # Debug: Show detected icons
            if hasattr(output[0], 'values') and len(output[0]) > 0:
                detected = output[0]['icon'].unique() if 'icon' in output[0].columns else []
                bot.logger.debug(f'Detected icons: {list(detected)}')
            else:
                bot.logger.debug('No icons detected on screen')
                
                # Check screenshot validity
                screenshot_path = f'bot_feed_{bot.device.split(":")[-1]}.png'
                if os.path.exists(screenshot_path):
                    file_size = os.path.getsize(screenshot_path)
                    bot.logger.debug(f'Screenshot exists: {file_size} bytes')
                    # Force new capture
                    bot.getScreen()
                else:
                    bot.logger.warning(f'Screenshot missing: {screenshot_path}')

            output = bot.battle_screen(start=True, pve=user_pve, floor=user_floor)
            wait += 1
            
            if wait > 40:
                bot.logger.info('RESTARTING due to timeout')
                bot.restart_game()
                wait = 0

def check_adb_connection(logger):
    """Check if ADB can connect to devices"""
    try:
        if _ADBUTILS_AVAILABLE and adb is not None:
            try:
                devices = adb.device_list()
            except Exception:
                devices = []
            if devices:
                logger.info(f"Found {len(devices)} ADB device(s) via adbutils")
                return True

        adb_path = ".scrcpy\\adb" if os.name == "nt" else "adb"
        out = check_output([adb_path, "devices"], stderr=DEVNULL)
        lines = out.decode("utf-8", errors="ignore").splitlines()
        online = [ln for ln in lines[1:] if "\tdevice" in ln]
        if online:
            logger.info(f"Found {len(online)} ADB device(s) via adb")
            return True

        logger.warning("No ADB devices found - make sure emulator/device is running")
        return False
    except Exception as e:
        logger.error(f'ADB connection failed: {e}')
        return False
    