"""Rush Royale Bot Core.

Enhanced error handling and modern Python features.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from subprocess import DEVNULL, Popen
from typing import Optional

import numpy as np
import pandas as pd

# Android ADB - Updated for pure-python-adb + scrcpy hybrid
try:
    from ppadb.client import Client as AdbClient
    from ppadb.device import Device

    ADB_AVAILABLE = True

    # Try to import scrcpy for enhanced screenshot capability
    try:
        import scrcpy

        SCRCPY_AVAILABLE = True
    except ImportError:
        SCRCPY_AVAILABLE = False

    # Create constants for touch actions (replacing scrcpy const)
    class TouchConstants:
        ACTION_DOWN = 0
        ACTION_UP = 1
        KEYCODE_BACK = 4

    const = TouchConstants()
except ImportError:
    # Fallback for missing dependencies
    class AdbClient:
        def __init__(self, host="127.0.0.1", port=5037):
            self.host = host
            self.port = port

        def devices(self):
            return []

    class Device:
        def __init__(self):
            self.serial = None

        def shell(self, command):
            pass

        def input_tap(self, x, y):
            pass

        def input_swipe(self, x1, y1, x2, y2, duration=1000):
            pass

    class TouchConstants:
        ACTION_DOWN = 0
        ACTION_UP = 1
        KEYCODE_BACK = 4

    ADB_AVAILABLE = False
    SCRCPY_AVAILABLE = False

    const = TouchConstants()

# internal
import bot_perception

# Image processing
import cv2
import ocr_utils
import port_scan

# default delay between sequential actions (seconds)
# lowered for snappier reaction time
SLEEP_DELAY = 0.02


class Bot:
    def __init__(self, device=None):
        self.bot_stop = False
        self.combat = (
            self.output
        ) = (
            self.grid_df
        ) = (
            self.unit_series
        ) = self.merge_series = self.df_groups = self.info = self.combat_step = None
        self.logger = logging.getLogger("__main__")
        if device is None:
            device = port_scan.get_device()
        if not device:
            raise Exception("No device found!")
        self.device = device
        self.bot_id = self.device.split(":")[-1]

        # Initialize ADB client
        self.adb_client = AdbClient()
        self.adb_device = None

        # Initialize scrcpy process for screenshots
        self.scrcpy_process = None
        self.scrcpy_executable = self.find_scrcpy_executable()

        # Connect to device
        devices = self.adb_client.devices()
        for dev in devices:
            if dev.serial == self.device:
                self.adb_device = dev
                break

        if not self.adb_device:
            # Try to connect
            self.shell(f"adb connect {self.device}")
            devices = self.adb_client.devices()
            for dev in devices:
                if dev.serial == self.device:
                    self.adb_device = dev
                    break

        if not self.adb_device:
            raise Exception(f"Could not connect to device {self.device}")

        # Launch application through ADB shell
        self.adb_device.shell("monkey -p com.my.defense 1")

        # Check if 'bot_feed.png' exists
        if not os.path.isfile(f"bot_feed_{self.bot_id}.png"):
            self.getScreen()
        self.screenRGB = cv2.imread(f"bot_feed_{self.bot_id}.png")
        self.last_screenshot_time = None

        self.logger.info("Connected to Android device via ADB")
        time.sleep(0.5)

    def __exit__(self, exc_type, exc_value, traceback):
        self.bot_stop = True
        self.logger.info("Exiting bot")
        # Stop scrcpy process if running
        if self.scrcpy_process:
            self.stop_scrcpy()

    def find_scrcpy_executable(self) -> Optional[str]:
        """Find scrcpy executable in common locations"""
        possible_paths = [
            "scrcpy.exe",  # In PATH
            r"C:\Program Files\scrcpy\scrcpy.exe",
            r"C:\Program Files (x86)\scrcpy\scrcpy.exe",
            r".\scrcpy\scrcpy.exe",  # Local directory
            r".\bin\scrcpy.exe",
        ]

        for path in possible_paths:
            if shutil.which(path) or os.path.exists(path):
                self.logger.info(f"Found scrcpy at: {path}")
                return path

        self.logger.warning("scrcpy executable not found - will use ADB screencap fallback")
        return None

    def start_scrcpy(self) -> bool:
        """Start scrcpy process for screen mirroring"""
        if not self.scrcpy_executable:
            return False

        try:
            # Start scrcpy in window mode with no controls (view only)
            cmd = [
                self.scrcpy_executable,
                "--serial",
                self.device,
                "--no-control",  # View only
                "--window-title",
                f"RR Bot {self.device}",
                "--window-width",
                "800",
                "--window-height",
                "450",
            ]

            self.scrcpy_process = Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
            self.logger.info("Started scrcpy process for screen mirroring")
            time.sleep(2)  # Give scrcpy time to start
            return True

        except Exception as e:
            self.logger.error(f"Failed to start scrcpy: {e}")
            self.scrcpy_process = None
            return False

    def stop_scrcpy(self):
        """Stop scrcpy process"""
        if self.scrcpy_process:
            try:
                self.scrcpy_process.terminate()
                self.scrcpy_process.wait(timeout=5)
                self.logger.info("Stopped scrcpy process")
            except subprocess.TimeoutExpired:
                self.scrcpy_process.kill()
                self.logger.warning("Force killed scrcpy process")
            except Exception as e:
                self.logger.error(f"Error stopping scrcpy: {e}")
            finally:
                self.scrcpy_process = None

    # Function to send ADB shell command
    def shell(self, cmd):
        if self.adb_device:
            return self.adb_device.shell(cmd)
        else:
            # Fallback to system ADB
            p = Popen(["adb", "-s", self.device, "shell", cmd], stdout=DEVNULL, stderr=DEVNULL)
            p.wait()

    def log_think_time(self, action: str = "") -> float | None:
        """Log ms since last screenshot to measure decision latency."""
        if self.last_screenshot_time is None:
            return None
        dt = (time.time() - self.last_screenshot_time) * 1000.0
        self.logger.debug(f"Thinking time {dt:.1f} ms {action}")
        return dt

    # Send ADB to click screen
    def click(self, x, y, delay_mult=1):
        self.log_think_time(f"click({x},{y})")
        if self.adb_device:
            self.adb_device.input_tap(x, y)
        else:
            # Fallback to shell command
            self.shell(f"input tap {x} {y}")
        time.sleep(SLEEP_DELAY * delay_mult)

    # Click button coords offset and extra delay
    def click_button(self, pos):
        coords = np.array(pos) + 10
        self.click(*coords)
        # reduced post-click delay for faster response
        time.sleep(SLEEP_DELAY * 4)

    # Swipe on combat grid to merge units
    def swipe(self, start, end):
        boxes, box_size = get_grid()
        # Offset from box edge
        offset = 60
        start_pos = boxes[start[0], start[1]] + offset
        end_pos = boxes[end[0], end[1]] + offset

        if self.adb_device:
            self.adb_device.input_swipe(start_pos[0], start_pos[1], end_pos[0], end_pos[1], 300)
        else:
            # Fallback to shell command
            self.shell(f"input swipe {start_pos[0]} {start_pos[1]} {end_pos[0]} {end_pos[1]} 300")

    # Send key command
    def key_input(self, key):
        if self.adb_device:
            self.adb_device.input_keyevent(key)
        else:
            self.shell(f"input keyevent {key}")

    # Wait until a given icon is no longer detected on screen
    def wait_until_icon_absent(
        self, icon_filename: str, timeout: float = 60.0, poll: float = 0.5
    ) -> bool:
        """Poll the screen until the provided icon is not detected anymore.
        Returns True if the icon disappeared within timeout, False otherwise.
        If the icon never appears, returns True immediately (no waiting needed).
        """
        start = time.time()
        seen_once = False
        while (time.time() - start) < timeout and not self.bot_stop:
            df = self.get_current_icons(available=True)
            present = (not df.empty) and (df["icon"] == icon_filename).any()
            if present:
                seen_once = True
            elif seen_once:
                self.logger.info(f"{icon_filename} cleared after {time.time() - start:.1f}s")
                return True
            time.sleep(poll)
        if not seen_once:
            # Icon was never seen; nothing to wait for
            return True
        self.logger.warning(f"Timeout waiting for {icon_filename} to disappear")
        return False

    # Force restart the game through ADB, or spam 10 disconnects to abandon match
    def restart_RR(self, quick_disconnect=False):
        if quick_disconnect:
            for i in range(15):
                if self.adb_device:
                    self.adb_device.shell("monkey -p com.my.defense 1")
                else:
                    self.shell(
                        "monkey -p com.my.defense 1"
                    )  # disconnects really quick for unknown reasons
            return
        # Force kill game through ADB shell
        if self.adb_device:
            self.adb_device.shell("am force-stop com.my.defense")
        else:
            self.shell("am force-stop com.my.defense")
        time.sleep(2)
        # Launch application through ADB shell
        if self.adb_device:
            self.adb_device.shell("monkey -p com.my.defense 1")
        else:
            self.shell("monkey -p com.my.defense 1")
        time.sleep(10)  # wait for app to load

    # Take screenshot of device screen and load pixel values
    def getScreen(self):
        bot_id = self.device.split(":")[-1]
        screenshot_path = f"bot_feed_{bot_id}.png"

        # Method 1: Try scrcpy executable screenshot (fastest, highest quality)
        if self.scrcpy_executable and self._try_scrcpy_screenshot(screenshot_path):
            self.logger.debug("Screenshot taken via scrcpy executable")
        # Method 2: Try pure-python-adb (reliable)
        elif self._try_adb_screenshot(screenshot_path):
            self.logger.debug("Screenshot taken via pure-python-adb")
        # Method 3: Fallback to shell ADB (last resort)
        elif self._try_shell_screenshot(screenshot_path):
            self.logger.debug("Screenshot taken via ADB shell")
        else:
            self.logger.error("All screenshot methods failed!")
            return

        # Load screenshot and validate
        try:
            new_img = cv2.imread(screenshot_path)
            if new_img is not None and new_img.shape[0] > 0 and new_img.shape[1] > 0:
                self.screenRGB = new_img
                self.last_screenshot_time = time.time()
                self.logger.debug(f"Screenshot loaded successfully: {new_img.shape}")
            else:
                self.logger.warning(f"Invalid screenshot file: {screenshot_path}")
        except Exception as e:
            self.logger.error(f"Failed to load screenshot: {e}")

    def _try_scrcpy_screenshot(self, output_path: str) -> bool:
        """Try taking screenshot using the scrcpy python client if available."""
        if not SCRCPY_AVAILABLE:
            return False
        try:
            client = scrcpy.Client(device=self.device, control=False)
            frame = client.last_frame
            if frame is None:
                client.start(threaded=True)
                # Wait briefly for a frame
                for _ in range(10):
                    if client.last_frame is not None:
                        frame = client.last_frame
                        break
                    time.sleep(0.05)
            client.stop()
            if frame is not None:
                cv2.imwrite(output_path, frame)
                return True
        except Exception as e:
            self.logger.debug(f"scrcpy screenshot failed: {e}")
        return False

    def _try_adb_screenshot(self, output_path: str) -> bool:
        """Try taking screenshot using pure-python-adb"""
        try:
            if self.adb_device:
                screencap = self.adb_device.screencap()
                if screencap and len(screencap) > 1000:  # Reasonable size check
                    with open(output_path, "wb") as f:
                        f.write(screencap)
                    return True
        except Exception as e:
            self.logger.debug(f"ADB screencap failed: {e}")
        return False

    def _try_shell_screenshot(self, output_path: str) -> bool:
        """Try taking screenshot using shell ADB command"""
        try:
            cmd = ["adb", "-s", self.device, "exec-out", "screencap", "-p"]
            with open(output_path, "wb") as f:
                p = subprocess.run(cmd, stdout=f, stderr=DEVNULL, timeout=10)
                return p.returncode == 0
        except Exception:
            return False

    # Crop latest screenshot taken
    def crop_img(self, x, y, dx, dy, name="icon.png"):
        # Load screen
        img_rgb = self.screenRGB
        img_rgb = img_rgb[y : y + dy, x : x + dx]
        cv2.imwrite(name, img_rgb)

    def getMana(self):
        return int(self.getText(220, 1360, 90, 50, new=False, digits=True))

    # find icon on screen
    def getXYByImage(self, target, new=True):
        valid_targets = ["battle_icon", "pvp_button", "back_button", "cont_button", "fighting"]
        if target not in valid_targets:
            return "INVALID TARGET"
        if new:
            self.getScreen()
        imgSrc = f"icons/{target}.png"
        img_rgb = self.screenRGB
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        template = cv2.imread(imgSrc, 0)
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = np.where(res >= threshold)
        if len(loc[0]) > 0:
            y = loc[0][0]
            x = loc[1][0]
            return [x, y]

    def get_store_state(self):
        x, y = [140, 1412]
        store_states_names = ["refresh", "new_store", "nothing", "new_offer", "spin_only"]
        store_states = np.array(
            [[255, 255, 255], [27, 235, 206], [63, 38, 12], [48, 253, 251], [80, 153, 193]]
        )
        store_rgb = self.screenRGB[y : y + 1, x : x + 1]
        store_rgb = store_rgb[0][0]
        # Take mean square of rgb value and store states
        store_mse = ((store_states - store_rgb) ** 2).mean(axis=1)
        closest_state = store_mse.argmin()
        return store_states_names[closest_state]

    # Check if any icons are on screen
    def get_current_icons(self, new=True, available=False):
        current_icons = []
        # Update screen and load screenshot as grayscale
        if new:
            self.getScreen()
        img_rgb = self.screenRGB
        if img_rgb is None:
            self.logger.warning("Screenshot is None - cannot detect icons")
            return pd.DataFrame(columns=["icon", "available", "pos [X,Y]"])

        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        self.logger.debug(f"Screenshot shape: {img_gray.shape}")

        # OCR fallback for chapter headers
        try:
            ocr_chapters = ocr_utils.find_chapter_headers(img_rgb)
        except Exception as e:
            ocr_chapters = {}
            self.logger.debug(f"Chapter OCR failed: {e}")

        # Check every target in dir
        icon_count = 0
        for target in os.listdir("icons"):
            x = 0  # reset position
            y = 0
            # Load icon
            imgSrc = f"icons/{target}"
            template = cv2.imread(imgSrc, 0)
            if template is None:
                self.logger.debug(f"Could not load template: {imgSrc}")
                continue

            # Compare images
            res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
            threshold = 0.8
            max_val = res.max()
            loc = np.where(res >= threshold)
            icon_found = len(loc[0]) > 0

            if icon_found:
                y = loc[0][0]
                x = loc[1][0]
            elif target.startswith("chapter_"):
                # Fallback to OCR if chapter icon not found
                try:
                    num = int(target.split("_")[1].split(".")[0])
                    if num in ocr_chapters:
                        x, y = ocr_chapters[num]
                        icon_found = True
                        self.logger.debug(f"OCR detected {target} at position {(x, y)}")
                except Exception:
                    pass

            # Debug for key icons
            if target in ["home_screen.png", "battle_icon.png"] or "chapter_" in target:
                self.logger.debug(f"Icon {target}: max_val={max_val:.3f}, found={icon_found}")

            if icon_found:
                icon_count += 1
            current_icons.append([target, icon_found, (x, y)])

        self.logger.debug(f"Total icons found: {icon_count}/{len(current_icons)}")
        icon_df = pd.DataFrame(current_icons, columns=["icon", "available", "pos [X,Y]"])
        # filter out only available buttons
        if available:
            icon_df = icon_df[icon_df["available"]].reset_index(drop=True)
        return icon_df

    # Scan battle grid, update OCR images
    def scan_grid(self, new=False):
        boxes, box_size = get_grid()
        # should be enabled by default
        if new:
            self.getScreen()
        box_list = boxes.reshape(15, 2)
        names = []
        if not os.path.isdir("OCR_inputs"):
            os.mkdir("OCR_inputs")
        for i in range(len(box_list)):
            file_name = f"OCR_inputs/icon_{str(i)}.png"
            self.crop_img(*box_list[i], *box_size, name=file_name)
            names.append(file_name)
        return names

    # Take random unit in series, find corresponding dataframe and merge two random ones
    def merge_unit(self, df_split, merge_series):
        # Pick a random filtered target
        if len(merge_series) > 0:
            merge_target = merge_series.sample().index[0]
        else:
            return merge_series
        # Collect unit dataframe
        merge_df = df_split.get_group(merge_target)
        if len(merge_df) > 1:
            merge_df = merge_df.sample(n=2)
        else:
            return merge_df
        self.log_merge(merge_df)
        # Extract unit position from dataframe
        unit_chosen = merge_df["grid_pos"].tolist()
        # Send Merge
        self.swipe(*unit_chosen)
        time.sleep(0.2)
        return merge_df

    # Merge special units ['harlequin.png','dryad.png','mime.png','scrapper.png']
    # Add logging event
    def merge_special_unit(self, df_split, merge_series, special_type):
        # Get special merge unit
        special_unit, normal_unit = [
            adv_filter_keys(merge_series, units=special_type, remove=remove)
            for remove in [False, True]
        ]  # scrapper support not tested
        # Get corresponding dataframes
        special_df, normal_df = [
            df_split.get_group(unit.index[0]).sample() for unit in [special_unit, normal_unit]
        ]
        merge_df = pd.concat([special_df, normal_df])
        self.log_merge(merge_df)
        # Merge 'em
        unit_chosen = merge_df["grid_pos"].tolist()
        self.swipe(*unit_chosen)
        time.sleep(0.2)
        return merge_df

    def log_merge(self, merge_df):
        merge_df["unit"] = merge_df["unit"].apply(lambda x: x.replace(".png", ""))
        unit1, unit2 = merge_df.iloc[0:2]["unit"]
        rank = merge_df.iloc[0]["rank"]
        log_msg = f"Rank {rank} {unit1}-> {unit2}"
        # Determine log level from rank
        if rank > 4:
            self.logger.error(log_msg)
        elif rank > 2:
            self.logger.debug(log_msg)
        else:
            self.logger.info(log_msg)

    # Find targets for special merge
    def special_merge(self, df_split, merge_series, target="zealot.png"):
        merge_df = None
        # Try to rank up dryads
        dryads_series = adv_filter_keys(merge_series, units="dryad.png")
        if not dryads_series.empty:
            dryads_rank = dryads_series.index.get_level_values("rank")
            for rank in dryads_rank:
                merge_series_dryad = adv_filter_keys(
                    merge_series, units=["harlequin.png", "dryad.png"], ranks=rank
                )
                merge_series_zealot = adv_filter_keys(
                    merge_series, units=["dryad.png", target], ranks=rank
                )
                if len(merge_series_dryad.index) == 2:
                    merge_df = self.merge_special_unit(
                        df_split, merge_series_dryad, special_type="harlequin.png"
                    )
                    break
                if len(merge_series_zealot.index) == 2:
                    merge_df = self.merge_special_unit(
                        df_split, merge_series_zealot, special_type="dryad.png"
                    )
                    break
        return merge_df

    # Harley Merge target
    def harley_merge(self, df_split, merge_series, target="knight_statue.png"):
        merge_df = None
        # Try to copy target
        hq_series = adv_filter_keys(merge_series, units="harlequin.png")
        if not hq_series.empty:
            hq_rank = hq_series.index.get_level_values("rank")
            for rank in hq_rank:
                merge_series_target = adv_filter_keys(
                    merge_series, units=["harlequin.png", target], ranks=rank
                )
                if len(merge_series_target.index) == 2:
                    merge_df = self.merge_special_unit(
                        df_split, merge_series_target, special_type="harlequin.png"
                    )
                    break
        return merge_df

    # Try to find a merge target and merge it
    def try_merge(self, rank=1, prev_grid=None, merge_target="zealot.png"):
        info = ""
        merge_df = None
        names = self.scan_grid(new=False)
        grid_df = bot_perception.grid_status(names, prev_grid=prev_grid)
        df_split, unit_series, df_groups, group_keys = grid_meta_info(grid_df)
        # Select stuff to merge
        merge_series = unit_series.copy()
        # Remove empty groups
        merge_series = adv_filter_keys(merge_series, units="empty.png", remove=True)
        # Do special merge with dryad/Harley
        self.special_merge(df_split, merge_series, merge_target)
        # Use harely on high dps targets
        if merge_target == "demon_hunter.png":
            self.harley_merge(df_split, merge_series, target=merge_target)
            # Remove all demons (for co-op)
            demons = adv_filter_keys(merge_series, units="demon_hunter.png")
            num_demon = sum(demons)
            if num_demon >= 11:
                # If board is mostly demons, chill out
                self.logger.info("Board is full of demons, waiting...")
                time.sleep(10)
            if self.config.getboolean("bot", "require_shaman"):
                merge_series = adv_filter_keys(merge_series, units="demon_hunter.png", remove=True)
        merge_series = preserve_unit(merge_series, target="chemist.png")
        # Remove 4x cauldrons
        for _ in range(4):
            merge_series = preserve_unit(merge_series, target="cauldron.png", keep_min=True)
        # Try to keep knight_statue numbers even (can conflict if special_merge already merged)
        num_knight = sum(adv_filter_keys(merge_series, units="knight_statue.png"))
        if num_knight % 2 == 1:
            self.harley_merge(df_split, merge_series, target="knight_statue.png")
        # Preserve 2 highest knight statues
        for _ in range(2):
            merge_series = preserve_unit(merge_series, target="knight_statue.png")
        # Select stuff to merge
        merge_series = merge_series[merge_series >= 2]  # At least 2 units
        merge_series = adv_filter_keys(merge_series, ranks=7, remove=True)  # Remove max ranks
        # Try to merge high priority units
        merge_prio = adv_filter_keys(
            merge_series,
            units=["chemist.png", "bombardier.png", "summoner.png", "knight_statue.png"],
        )
        if not merge_prio.empty:
            info = "Merging High Priority!"
            merge_df = self.merge_unit(df_split, merge_prio)
        # Merge if board is getting full
        if df_groups["empty.png"] <= 2:
            info = "Merging!"
            # Add criteria
            low_series = adv_filter_keys(merge_series, ranks=rank, remove=False)
            if not low_series.empty:
                merge_df = self.merge_unit(df_split, low_series)
            else:
                # If grid seems full, merge more units
                info = "Merging high level!"
                merge_series = adv_filter_keys(
                    merge_series,
                    ranks=[3, 4, 5, 6, 7],
                    units=["zealot.png", "crystal.png", "bruser.png", merge_target],
                    remove=True,
                )
                if not merge_series.empty:
                    merge_df = self.merge_unit(df_split, merge_series)
        else:
            info = "need more units!"
        return grid_df, unit_series, merge_series, merge_df, info

    # Mana level cards
    def mana_level(self, cards, hero_power=False):
        upgrade_pos_dict = {
            1: [100, 1500],
            2: [200, 1500],
            3: [350, 1500],
            4: [500, 1500],
            5: [650, 1500],
        }
        # Level each card
        for card in cards:
            self.click(*upgrade_pos_dict[card])
        if hero_power:
            self.click(800, 1500)

    # Start a dungeon floor from PvE page
    def play_dungeon(self, floor=5):
        self.logger.debug(f"Starting Dungeon floor {floor}")
        # Explicit mapping of floors to chapters
        floor_map = {
            1: range(1, 4),
            2: range(4, 7),
            3: range(7, 10),
            4: range(10, 13),
            5: [13],
            6: [14],
        }
        chapter_num = 1
        for chap, floors in floor_map.items():
            if floor in floors:
                chapter_num = chap
                break
        self.logger.debug(f"Looking for chapter {chapter_num}")
        pos = np.array([0, 0])
        avail_buttons = self.get_current_icons(available=True)
        # Check if on dungeon page
        if (avail_buttons["icon"] == "dungeon_page.png").any():
            # Swipe to the top
            [self.swipe([0, 0], [2, 0]) for _ in range(14)]
            self.click(30, 600, 5)  # stop scroll and scan screen for buttons
            self.getScreen()
            # Log visible floors for debugging
            visible = ocr_utils.find_chapter_headers(self.screenRGB)
            for chap, xy in visible.items():
                floors_here = ocr_utils.read_floor_from_chapter(self.screenRGB, xy)
                self.logger.debug(f"Visible chapter {chap} floors: {floors_here}")

            for i in range(12):
                self.getScreen()
                chapters = ocr_utils.find_chapter_headers(self.screenRGB)
                self.logger.debug(f"Iteration {i}: OCR chapters {chapters}")
                if chapter_num in chapters:
                    pos = np.array(chapters[chapter_num])
                    self.logger.info(f"Found chapter {chapter_num} at {pos}")
                    # Expand chapter only if a collapse icon is detected
                    icons = self.get_current_icons(available=True)
                    chapter_icon = f"chapter_{chapter_num}.png"
                    if (icons["icon"] == chapter_icon).any():
                        self.logger.debug(f"Chapter {chapter_num} collapsed, expanding")
                        self.click_button(pos)
                        self.getScreen()
                    if pos[1] < 550 and floor % 3 != 0:
                        break
                else:
                    [self.swipe([2, 0], [0, 0]) for _ in range(2)]
                    self.click(30, 600)

            if not (pos == np.array([0, 0])).any():
                self.logger.info(f"Clicking floor {floor} for chapter at position {pos}")
                slot_offsets = {
                    1: np.array([30, -460]),
                    2: np.array([30, 485]),
                    3: np.array([30, 885]),
                }
                chosen_offset = None
                try:
                    floors = ocr_utils.read_floor_from_chapter(
                        self.screenRGB, (int(pos[0]), int(pos[1]))
                    )
                    for slot, (val, conf) in floors.items():
                        if val == floor and conf >= 0.55 and slot in slot_offsets:
                            chosen_offset = slot_offsets[slot]
                            self.logger.debug(
                                f"OCR selected slot {slot} (conf={conf:.2f}) for floor {floor}"
                            )
                            break
                except Exception as e:
                    self.logger.debug(f"OCR floor read failed, falling back: {e}")

                if chosen_offset is None:
                    if floor % 3 == 0:
                        chosen_offset = slot_offsets[1]
                    elif floor % 3 == 1:
                        chosen_offset = slot_offsets[2]
                    else:
                        chosen_offset = slot_offsets[3]

                self.click_button(pos + chosen_offset)
                # Play selected floor then choose random partner
                self.click_button((500, 600))  # Play
                time.sleep(0.5)
                self.click_button((500, 800))  # Random
                for i in range(10):
                    time.sleep(2)
                    avail_buttons = self.get_current_icons(available=True)
                    self.logger.info(f"Waiting for match to start {i}")
                    if avail_buttons["icon"].isin(["back_button.png", "fighting.png"]).any():
                        break
            else:
                self.logger.error(f"Could not find chapter for floor {floor}")

    # Locate game home screen and try to start fight is chosen
    def battle_screen(self, start=False, pve=True, floor=5, new=True):
        # Scan screen for any key buttons
        df = self.get_current_icons(new=new, available=True)
        if not df.empty:
            # list of buttons
            if (df["icon"] == "fighting.png").any() and not (
                df["icon"] == "0cont_button.png"
            ).any():
                return df, "fighting"
            if (df["icon"] == "friend_menu.png").any():
                self.click_button(np.array([100, 600]))
                return df, "friend_menu"
            # Start pvp if homescreen
            if (df["icon"] == "home_screen.png").any() and (df["icon"] == "battle_icon.png").any():
                if pve and start:
                    # Add a 500 pixel offset for PvE button
                    self.click_button(np.array([640, 1259]))
                    self.play_dungeon(floor=floor)
                elif start:
                    self.click_button(np.array([140, 1259]))
                    # After pressing PvP, wait for loading indicator to disappear
                    try:
                        self.wait_until_icon_absent("pvp_loading.png", timeout=120.0, poll=1.0)
                    except Exception:
                        pass
                time.sleep(1)
                return df, "home"
            # Check first button is clickable
            df_click = df[
                df["icon"].isin(
                    ["back_button.png", "battle_icon.png", "0cont_button.png", "1quit.png"]
                )
            ]
            if not df_click.empty:
                button_pos = df_click["pos [X,Y]"].tolist()[0]
                self.click_button(button_pos)
                return df, "menu"
        self.key_input(const.KEYCODE_BACK)  # Force back
        return df, "lost"

    # Navigate and locate store refresh button from battle screen
    def find_store_refresh(self):
        self.click_button((100, 1500))  # Click store button
        [self.swipe([0, 0], [2, 0]) for i in range(5)]  # swipe to top
        self.click(30, 150)  # stop scroll
        avail_buttons = self.get_current_icons(available=True)
        if (avail_buttons["icon"] == "refresh_button.png").any():
            pos = get_button_pos(avail_buttons, "refresh_button.png")
            return pos

    # Refresh items in shop when available
    def refresh_shop(self):
        self.click_button((100, 1500))  # Click store button
        self.click_button((475, 1300))  # Click store button
        # Scroll up and find the refresh button
        pos = self.find_store_refresh()
        if isinstance(pos, np.ndarray):
            self.click_button(pos - [300, 820])  # Click first (free) item
            self.click(400, 1165)  # buy
            self.click(30, 150)  # remove pop-up
            self.click_button(pos + [400, -400])  # Click last item (possible legendary)
            self.click(400, 1165)  # buy
            self.click(30, 150)  # remove pop-up
            self.logger.warning("Bought store units!")
            # Try to refresh shop (watch ad)
            self.click_button(pos)

    def watch_ads(self):
        avail_buttons = self.get_current_icons(available=True)
        # Watch ad if available
        if (avail_buttons["icon"] == "quest_done.png").any():
            pos = get_button_pos(avail_buttons, "quest_done.png")
            self.click_button(pos)
            self.click(700, 600)  # collect second completed quest
            self.click(700, 400)  # collect second completed quest
            [self.click(150, 250) for i in range(2)]  # click dailies twice
            self.click(420, 420)  # collect ad chest
        elif (avail_buttons["icon"] == "ad_season.png").any():
            pos = get_button_pos(avail_buttons, "ad_season.png")
            self.click_button(pos)
        elif (avail_buttons["icon"] == "ad_pve.png").any():
            pos = get_button_pos(avail_buttons, "ad_pve.png")
            self.click_button(pos)
        elif (avail_buttons["icon"] == "battle_icon.png").any():
            self.refresh_shop()
        else:
            # self.logger.info('Watched all ads!')
            return
        # Check if ad was started
        avail_buttons, status = self.battle_screen()
        if (
            status == "menu"
            or status == "home"
            or (avail_buttons["icon"] == "refresh_button.png").any()
        ):
            self.logger.info("FINISHED AD")
        # Watch ad
        else:
            time.sleep(30)
            # Keep watching until back in menu
            for i in range(10):
                avail_buttons, status = self.battle_screen()
                if status == "menu" or status == "home":
                    self.logger.info("FINISHED AD")
                    return  # Exit function
                time.sleep(2)
                self.click(870, 30)  # skip forward/click X
                self.click(870, 100)  # click X playstore popup
                if i > 5:
                    self.key_input(const.KEYCODE_BACK)  # Force back
                self.logger.info(f"AD TIME {i} {status}")
            # Restart game if can't escape ad
            self.restart_RR()


# ----
# END OF CLASS
# ----


# Get fight grid pixel values
def get_grid():
    # Grid dimensions
    top_box = (153, 945)
    box_size = (120, 120)
    gap = 0
    height = 3
    width = 5
    # x_cords
    x_cord = list(range(top_box[0], top_box[0] + (box_size[0] + gap) * width, box_size[0] + gap))
    y_cord = list(range(top_box[1], top_box[1] + (box_size[1] + gap) * height, box_size[1] + gap))
    boxes = []
    # Create list of all boxes
    for y_point in y_cord:
        for x_point in x_cord:
            boxes.append((x_point, y_point))
    # Convert to np array (4x4) with x,y coords
    boxes = np.array(boxes).reshape(height, width, 2)
    return boxes, box_size


def get_unit_count(grid_df):
    df_split = grid_df.groupby("unit")
    df_groups = df_split["unit"].count()
    if "empty.png" not in df_groups:
        df_groups["empty.png"] = 0
    unit_list = list(df_groups.index)
    return df_split, df_groups, unit_list


# Removes 1x of the highest rank unit from the merge_series
def preserve_unit(unit_series, target="chemist.png", keep_min=False):
    """
    Remove 1x of the highest rank unit from the merge_series
    param: merge_series - pandas series of units to remove
    param: target - target unit to keep
    param: keep_min - if true, keep the lowest rank unit instead of highest
    """
    merge_series = unit_series.copy()
    preserve_series = adv_filter_keys(merge_series, units=target, remove=False)
    if not preserve_series.empty:
        if keep_min:
            preserve_unit = preserve_series.index.min()
        else:
            preserve_unit = preserve_series.index.max()
        # Remove 1 count of highest/lowest rank
        merge_series[merge_series.index == preserve_unit] = (
            merge_series[merge_series.index == preserve_unit] - 1
        )
        # Remove 0 counts
        return merge_series[merge_series > 0]
    else:
        return merge_series


def grid_meta_info(grid_df, min_age=0):
    """
    Split grid df into unique units and ranks
    Shows total count of unit and count of each rank
    param: grid_df - pandas dataframe of grid
    param: min_age - minimum age of unit to include in meta info
    """
    # Split by unique unit
    df_groups = get_unit_count(grid_df)[1]
    grid_df = grid_df[grid_df["Age"] >= min_age].reset_index(drop=True)
    df_split = grid_df.groupby(["unit", "rank"])
    # Count number of unit of each rank
    unit_series = df_split["unit"].count()
    # unit_series = unit_series.sort_values(ascending=False)
    group_keys = list(unit_series.index)
    return df_split, unit_series, df_groups, group_keys


def filter_units(unit_series, units):
    if not isinstance(units, list):  # Make units a list if not already
        units = [units]
    # Create temp series to hold matches
    series = []
    merge_series = unit_series.copy()
    for token in units:
        if isinstance(token, int):
            exists = merge_series.index.get_level_values("rank").isin([token]).any()
            if exists:
                series.append(merge_series.xs(token, level="rank", drop_level=False))
            else:
                continue  # skip if nothing matches criteria
        elif isinstance(token, str):
            if token in merge_series:
                series.append(merge_series.xs(token, level="unit", drop_level=False))
            else:
                continue
    if not len(series) == 0:
        temp_series = pd.concat(series)
        # Select all entries from original series that are in temp_series
        merge_series = merge_series[merge_series.index.isin(temp_series.index)]
        return merge_series
    else:
        return pd.Series(dtype=object)


def adv_filter_keys(unit_series, units=None, ranks=None, remove=False):
    """
    Returns all elements which match units and ranks values
    If one of the parameters is None, it is ignored and all values are kept
    If remove is True, all elements are removed which do not match the criteria
    param: unit_series - pandas series of units to filter
    param: units - string or list of strings of units to filter by
    param: ranks - int or list of ints of ranks to filter by
    param: remove - if true, return filtered series, if false, return only matches
    """
    # return if no units in series
    if unit_series.empty:
        return pd.Series(dtype=object)
    filtered_ranks = pd.Series(dtype=object)
    if units is not None:
        filtered_units = filter_units(unit_series, units)
    else:
        filtered_units = unit_series.copy()
    # if all units are filtered already, return empty series
    if ranks is not None and not filtered_units.empty:
        filtered_ranks = filter_units(filtered_units, ranks)
    else:
        filtered_ranks = filtered_units.copy()
    # Final filtering
    series = unit_series.copy()
    if remove:
        series = series[~series.index.isin(filtered_ranks.index)]
    else:
        series = series[series.index.isin(filtered_ranks.index)]
    return series


# Will spam read all knowledge in knowledge base for free gold, roughly 3k, 100 gems
def read_knowledge(bot):
    spam_click = range(1000)
    for i in spam_click:
        bot.click(450, 1300, 0.1)


def get_button_pos(df, button):
    # button=button+'.png'
    pos = df[df["icon"] == button]["pos [X,Y]"].reset_index(drop=True)[0]
    return np.array(pos)
