"""Rush Royale bot orchestration and device startup helpers."""
from __future__ import annotations

import functools
import pathlib
import shutil
import time
from pathlib import Path

import cv2
import numpy as np
import requests
from tqdm.auto import tqdm

import bot_core
import bot_perception
from adb_backend import AdbError, find_adb, list_devices

REPO_ROOT = Path(__file__).resolve().parents[1]
UNITS_DIR = REPO_ROOT / "units"
ALL_UNITS_DIR = REPO_ROOT / "all_units"


def download(url, filename):
    response = requests.get(url, stream=True, allow_redirects=True, timeout=60)
    if response.status_code != 200:
        response.raise_for_status()
        raise RuntimeError(f"Request to {url} returned status code {response.status_code}")
    file_size = int(response.headers.get("Content-Length", 0))
    path = pathlib.Path(filename).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    description = "(Unknown total file size)" if file_size == 0 else ""
    response.raw.read = functools.partial(response.raw.read, decode_content=True)
    with tqdm.wrapattr(response.raw, "read", total=file_size, desc=description) as raw:
        with path.open("wb") as output_file:
            shutil.copyfileobj(raw, output_file)
    return path


def select_units(units):
    UNITS_DIR.mkdir(exist_ok=True)
    for existing in UNITS_DIR.iterdir():
        if existing.is_file():
            existing.unlink()
    for new_unit in units:
        source = ALL_UNITS_DIR / new_unit
        target = UNITS_DIR / new_unit
        image = cv2.imread(str(source))
        if image is None:
            print(f"{new_unit} not found")
            continue
        cv2.imwrite(str(target), image)
    return len(list(UNITS_DIR.iterdir())) > 4


def start_bot_class(logger):
    adb_path = find_adb()
    logger.info(f"Using official adb executable: {adb_path}")
    if not check_adb_connection(logger):
        logger.warning(
            "No ADB device is online yet; RushBot will try local emulator port discovery."
        )
    return bot_core.Bot()


def combat_loop(bot, grid_df, mana_targets, user_target="demon_hunter.png"):
    time.sleep(0.2)
    bot.mana_level(mana_targets, hero_power=True)
    bot.click(450, 1360)
    return bot.try_merge(prev_grid=grid_df, merge_target=user_target)


def bot_loop(bot, info_event):
    config = bot.config["bot"]
    user_pve = config.getboolean("pve", True)
    bot.logger.warning(f"PVE is set to {user_pve}")
    user_floor = int(config.get("floor", 5))
    user_level = np.fromstring(config["mana_level"], dtype=int, sep=",")
    user_target = config["dps_unit"].split(".")[0] + ".png"
    require_shaman = config.getboolean("require_shaman", False)
    max_loops = int(config.get("max_loops", 800))
    train_ai = False
    wait = 0
    combat = 0
    watch_ad = False
    grid_df = None
    time.sleep(5)
    bot.logger.debug("Bot mainloop started")

    while not bot.bot_stop:
        output = bot.battle_screen(start=False)
        if output[1] == "fighting":
            watch_ad = True
            wait = 0
            combat += 1
            if combat > max_loops:
                bot.restart_RR()
                combat = 0
                continue
            if bot.bot_stop:
                return
            if require_shaman and not (output[0]["icon"] == "shaman_opponent.png").any():
                bot.logger.info("Shaman not found, checking again...")
                if any(
                    (bot.battle_screen(start=False)[0]["icon"] == "shaman_opponent.png").any()
                    for _ in range(1)
                ):
                    continue
                bot.logger.warning("Leaving game")
                bot.restart_RR(quick_disconnect=True)

            grid_df, bot.unit_series, bot.merge_series, bot.df_groups, bot.info = combat_loop(
                bot, grid_df, user_level, user_target
            )
            bot.grid_df = grid_df.copy()
            bot.combat = combat
            bot.output = output[1]
            bot.combat_step = 1
            info_event.set()
            if combat == 25 and 5 < grid_df["Age"].mean() < 50 and train_ai:
                bot_perception.add_grid_to_dataset()
        elif output[1] == "home" and watch_ad:
            for _ in range(3):
                bot.watch_ads()
            watch_ad = False
        else:
            combat = 0
            bot.logger.info(f"{output[1]}, wait count: {wait}")
            if hasattr(output[0], "values") and len(output[0]) > 0:
                detected_icons = (
                    output[0]["icon"].unique() if "icon" in output[0].columns else []
                )
                bot.logger.debug(f"Detected icons: {list(detected_icons)}")
            else:
                bot.logger.debug("No icons detected on screen")
                screenshot_path = REPO_ROOT / f"bot_feed_{bot.device.split(':')[-1]}.png"
                if screenshot_path.exists():
                    bot.logger.debug(
                        f"Screenshot file exists: {screenshot_path} "
                        f"({screenshot_path.stat().st_size} bytes)"
                    )
                    bot.getScreen()
                    bot.logger.debug("Forced new screenshot capture")
                else:
                    bot.logger.warning(f"Screenshot file missing: {screenshot_path}")
            bot.battle_screen(start=True, pve=user_pve, floor=user_floor)
            wait += 1
            if wait > 40:
                bot.logger.info("RESTARTING")
                bot.restart_RR()
                wait = 0


def check_adb_connection(logger):
    """Check the official adb server for online devices."""
    try:
        adb_path = find_adb()
        devices = list_devices()
        if devices:
            logger.info(f"Found {len(devices)} ADB device(s) via {adb_path}")
            return True
        logger.warning(
            "No ADB devices found. Enable USB debugging or start the Android emulator."
        )
        return False
    except FileNotFoundError as exc:
        logger.error(str(exc))
        return False
    except AdbError as exc:
        logger.error(f"ADB connection failed: {exc}")
        return False
