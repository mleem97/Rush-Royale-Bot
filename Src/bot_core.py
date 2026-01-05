"""
Rush Royale Bot Core - Python 3.13 Compatible
Enhanced error handling and modern Python features
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from subprocess import DEVNULL, PIPE, Popen
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np
import pandas as pd

import bot_perception
import port_scan

# Android ADB - Updated for pure-python-adb + scrcpy hybrid
try:
    from ppadb.client import Client as AdbClient
    from ppadb.device import Device

    ADB_AVAILABLE = True

    try:
        import scrcpy

        SCRCPY_AVAILABLE = True
    except ImportError:
        SCRCPY_AVAILABLE = False

    class TouchConstants:
        ACTION_DOWN = 0
        ACTION_UP = 1
        KEYCODE_BACK = 4

    const = TouchConstants()
except ImportError:
    class AdbClient:
        def __init__(self, host: str = "127.0.0.1", port: int = 5037) -> None:
            self.host = host
            self.port = port

        def devices(self):
            return []

    class Device:
        def __init__(self) -> None:
            self.serial = None

        def shell(self, command):
            pass

        def input_tap(self, x, y):
            pass

        def input_swipe(self, x1, y1, x2, y2, duration: int = 1000):
            pass

    class TouchConstants:
        ACTION_DOWN = 0
        ACTION_UP = 1
        KEYCODE_BACK = 4

    const = TouchConstants()
    ADB_AVAILABLE = False
    SCRCPY_AVAILABLE = False

SLEEP_DELAY = 0.1


class Bot:
    def __init__(self, device: Optional[str] = None) -> None:
        self.bot_stop = False
        self.combat = self.output = self.grid_df = self.unit_series = self.merge_series = self.df_groups = self.info = self.combat_step = None
        self.logger = logging.getLogger("__main__")

        if device is None:
            device = port_scan.get_device()
        if not device:
            raise Exception("No device found!")
        self.device = device
        self.bot_id = self.device.split(":")[-1]

        self.adb_client: AdbClient = AdbClient()
        self.adb_device: Optional[Device] = None
        self.scrcpy_process: Optional[Popen] = None
        self.scrcpy_executable = self.find_scrcpy_executable()

        devices = self.adb_client.devices()
        for dev in devices:
            if dev.serial == self.device:
                self.adb_device = dev
                break

        if not self.adb_device:
            self.shell(f"adb connect {self.device}")
            devices = self.adb_client.devices()
            for dev in devices:
                if dev.serial == self.device:
                    self.adb_device = dev
                    break

        if not self.adb_device:
            raise Exception(f"Could not connect to device {self.device}")

        self.adb_device.shell("monkey -p com.my.defense 1")

        if not os.path.isfile(f"bot_feed_{self.bot_id}.png"):
            self.getScreen()
        self.screenRGB = cv2.imread(f"bot_feed_{self.bot_id}.png")

        self.logger.info("Connected to Android device via ADB")
        time.sleep(0.5)

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.bot_stop = True
        self.logger.info("Exiting bot")
        if self.scrcpy_process:
            self.stop_scrcpy()

    def find_scrcpy_executable(self) -> Optional[str]:
        possible_paths = [
            "scrcpy.exe",
            r"C:\\Program Files\\scrcpy\\scrcpy.exe",
            r"C:\\Program Files (x86)\\scrcpy\\scrcpy.exe",
            r".\\scrcpy\\scrcpy.exe",
            r".\\bin\\scrcpy.exe",
        ]

        for path in possible_paths:
            if shutil.which(path) or os.path.exists(path):
                self.logger.info(f"Found scrcpy at: {path}")
                return path

        self.logger.warning("scrcpy executable not found - will use ADB screencap fallback")
        return None

    def start_scrcpy(self) -> bool:
        if not self.scrcpy_executable:
            return False

        try:
            cmd = [
                self.scrcpy_executable,
                "--serial",
                self.device,
                "--no-control",
                "--window-title",
                f"RR Bot {self.device}",
                "--window-width",
                "800",
                "--window-height",
                "450",
            ]

            self.scrcpy_process = Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
            self.logger.info("Started scrcpy process for screen mirroring")
            time.sleep(2)
            return True

        except Exception as e:  # pragma: no cover - defensive
            self.logger.error(f"Failed to start scrcpy: {e}")
            self.scrcpy_process = None
            return False

    def stop_scrcpy(self) -> None:
        if self.scrcpy_process:
            try:
                self.scrcpy_process.terminate()
                self.scrcpy_process.wait(timeout=5)
                self.logger.info("Stopped scrcpy process")
            except subprocess.TimeoutExpired:
                self.scrcpy_process.kill()
                self.logger.warning("Force killed scrcpy process")
            except Exception as e:  # pragma: no cover - defensive
                self.logger.error(f"Error stopping scrcpy: {e}")
            finally:
                self.scrcpy_process = None

    def shell(self, cmd: str):
        if self.adb_device:
            return self.adb_device.shell(cmd)
        p = Popen(["adb", "-s", self.device, "shell", cmd], stdout=DEVNULL, stderr=DEVNULL)
        p.wait()

    def click(self, x: int, y: int, delay_mult: float = 1) -> None:
        if self.adb_device:
            self.adb_device.input_tap(x, y)
        else:
            self.shell(f"input tap {x} {y}")
        time.sleep(SLEEP_DELAY * delay_mult)

    def click_button(self, pos) -> None:
        coords = np.array(pos) + 10
        self.click(*coords)
        time.sleep(SLEEP_DELAY * 10)

    def swipe(self, start, end) -> None:
        boxes, box_size = get_grid()
        offset = 60
        start_pos = boxes[start[0], start[1]] + offset
        end_pos = boxes[end[0], end[1]] + offset

        if self.adb_device:
            self.adb_device.input_swipe(start_pos[0], start_pos[1], end_pos[0], end_pos[1], 300)
        else:
            self.shell(f"input swipe {start_pos[0]} {start_pos[1]} {end_pos[0]} {end_pos[1]} 300")

    def key_input(self, key: int) -> None:
        if self.adb_device:
            self.adb_device.input_keyevent(key)
        else:
            self.shell(f"input keyevent {key}")

    def restart_RR(self, quick_disconnect: bool = False) -> None:
        if quick_disconnect:
            for _ in range(15):
                if self.adb_device:
                    self.adb_device.shell("monkey -p com.my.defense 1")
                else:
                    self.shell("monkey -p com.my.defense 1")
            return

        if self.adb_device:
            self.adb_device.shell("am force-stop com.my.defense")
        else:
            self.shell("am force-stop com.my.defense")
        time.sleep(2)

        if self.adb_device:
            self.adb_device.shell("monkey -p com.my.defense 1")
        else:
            self.shell("monkey -p com.my.defense 1")
        time.sleep(10)

    def getScreen(self) -> None:
        bot_id = self.device.split(":")[-1]
        screenshot_path = f"bot_feed_{bot_id}.png"

        if self.scrcpy_executable and self._try_scrcpy_screenshot(screenshot_path):
            self.logger.debug("Screenshot taken via scrcpy executable")
        elif self._try_adb_screenshot(screenshot_path):
            self.logger.debug("Screenshot taken via pure-python-adb")
        elif self._try_shell_screenshot(screenshot_path):
            self.logger.debug("Screenshot taken via ADB shell")
        else:
            self.logger.error("All screenshot methods failed!")
            return

        try:
            new_img = cv2.imread(screenshot_path)
            if new_img is not None and new_img.shape[0] > 0 and new_img.shape[1] > 0:
                self.screenRGB = new_img
                self.logger.debug(f"Screenshot loaded successfully: {new_img.shape}")
            else:
                self.logger.warning(f"Invalid screenshot file: {screenshot_path}")
        except Exception as e:  # pragma: no cover - defensive
            self.logger.error(f"Failed to load screenshot: {e}")

    def _try_scrcpy_screenshot(self, output_path: str) -> bool:
        if not self.scrcpy_executable:
            return False
        try:
            cmd = ["adb", "-s", self.device, "exec-out", "screencap", "-p"]
            with open(output_path, "wb") as f:
                p = subprocess.run(cmd, stdout=f, stderr=DEVNULL, timeout=10)
                return p.returncode == 0
        except Exception:  # pragma: no cover - defensive
            return False

    def _try_adb_screenshot(self, output_path: str) -> bool:
        try:
            if self.adb_device:
                screencap = self.adb_device.screencap()
                if screencap and len(screencap) > 1000:
                    with open(output_path, "wb") as f:
                        f.write(screencap)
                    return True
        except Exception as e:
            self.logger.debug(f"ADB screencap failed: {e}")
        return False

    def _try_shell_screenshot(self, output_path: str) -> bool:
        try:
            cmd = ["adb", "-s", self.device, "exec-out", "screencap", "-p"]
            with open(output_path, "wb") as f:
                p = subprocess.run(cmd, stdout=f, stderr=DEVNULL, timeout=10)
                return p.returncode == 0
        except Exception:  # pragma: no cover - defensive
            return False

    def crop_img(self, x: int, y: int, dx: int, dy: int, name: str = "icon.png") -> None:
        img_rgb = self.screenRGB
        img_rgb = img_rgb[y : y + dy, x : x + dx]
        cv2.imwrite(name, img_rgb)

    def getMana(self) -> int:
        return int(self.getText(220, 1360, 90, 50, new=False, digits=True))

    def getXYByImage(self, target: str, new: bool = True):
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
        store_mse = ((store_states - store_rgb) ** 2).mean(axis=1)
        closest_state = store_mse.argmin()
        return store_states_names[closest_state]

    def get_current_icons(self, new: bool = True, available: bool = False, icon_list=None) -> pd.DataFrame:
        current_icons = []
        if new:
            self.getScreen()
        img_rgb = self.screenRGB
        if img_rgb is None:
            self.logger.warning("Screenshot is None - cannot detect icons")
            return pd.DataFrame(columns=["icon", "available", "pos [X,Y]"])

        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        img_gray_blur = cv2.GaussianBlur(img_gray, (3, 3), 0)
        self.logger.debug(f"Screenshot shape: {img_gray.shape}")

        def match_template_multi_scale(src_gray, tmpl_gray, base_thresh, is_chapter: bool = False):
            best = (False, (0, 0), 0.0)
            scales = [0.9, 1.0, 1.1] if is_chapter else [1.0]
            for sc in scales:
                tmpl = tmpl_gray
                if sc != 1.0:
                    new_w = max(1, int(tmpl_gray.shape[1] * sc))
                    new_h = max(1, int(tmpl_gray.shape[0] * sc))
                    tmpl = cv2.resize(tmpl_gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
                if src_gray.shape[0] < tmpl.shape[0] or src_gray.shape[1] < tmpl.shape[1]:
                    continue
                res = cv2.matchTemplate(src_gray, tmpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val > best[2]:
                    best = (max_val >= base_thresh, (max_loc[0], max_loc[1]), float(max_val))
            if is_chapter and not best[0] and best[2] >= (base_thresh - 0.05):
                return (True, best[1], best[2])
            return best

        icons_to_check = os.listdir("icons") if icon_list is None else icon_list

        icon_count = 0
        for target in icons_to_check:
            x = 0
            y = 0
            imgSrc = f"icons/{target}"
            if not os.path.isfile(imgSrc):
                self.logger.debug(f"Icon file not found: {imgSrc}")
                continue

            template = cv2.imread(imgSrc, 0)
            if template is None:
                self.logger.debug(f"Could not load template: {imgSrc}")
                continue
            template_blur = cv2.GaussianBlur(template, (3, 3), 0)
            is_chapter = "chapter_" in target
            threshold = 0.8
            if is_chapter:
                threshold = 0.75
            elif target in ["dungeon_page.png"]:
                threshold = 0.60
            elif "floor" in target:
                threshold = 0.95
            elif target in ["random.png"]:
                threshold = 0.85
            elif target in ["pve_button.png"]:
                threshold = 0.85

            found, (best_x, best_y), max_val = match_template_multi_scale(
                img_gray_blur, template_blur, threshold, is_chapter=is_chapter
            )

            if target in ["home_screen.png", "battle_icon.png", "dungeon_page.png", "random.png", "pve_button.png"] or "chapter_" in target or "floor" in target:
                self.logger.debug(f"Icon {target}: max_val={max_val:.3f}, found={found}")

            if found:
                y = int(best_y)
                x = int(best_x)
                icon_count += 1
            current_icons.append([target, found, (x, y)])

        self.logger.debug(
            f"Total icons found: {icon_count}/{len(current_icons)} from list of {len(icons_to_check)} to check"
        )
        icon_df = pd.DataFrame(current_icons, columns=["icon", "available", "pos [X,Y]"])
        if available:
            icon_df = icon_df[icon_df["available"] == True].reset_index(drop=True)
        return icon_df

    def scan_grid(self, new: bool = False):
        boxes, box_size = get_grid()
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

    def merge_unit(self, df_split, merge_series):
        if len(merge_series) > 0:
            merge_target = merge_series.sample().index[0]
        else:
            return merge_series
        merge_df = df_split.get_group(merge_target)
        if len(merge_df) > 1:
            merge_df = merge_df.sample(n=2)
        else:
            return merge_df
        self.log_merge(merge_df)
        unit_chosen = merge_df["grid_pos"].tolist()
        self.swipe(*unit_chosen)
        time.sleep(0.2)
        return merge_df

    def merge_special_unit(self, df_split, merge_series, special_type):
        special_unit, normal_unit = [
            adv_filter_keys(merge_series, units=special_type, remove=remove) for remove in [False, True]
        ]
        special_df, normal_df = [df_split.get_group(unit.index[0]).sample() for unit in [special_unit, normal_unit]]
        merge_df = pd.concat([special_df, normal_df])
        self.log_merge(merge_df)
        unit_chosen = merge_df["grid_pos"].tolist()
        self.swipe(*unit_chosen)
        time.sleep(0.2)
        return merge_df

    def log_merge(self, merge_df) -> None:
        merge_df["unit"] = merge_df["unit"].apply(lambda x: x.replace(".png", ""))
        unit1, unit2 = merge_df.iloc[0:2]["unit"]
        rank = merge_df.iloc[0]["rank"]
        log_msg = f"Rank {rank} {unit1}-> {unit2}"
        if rank > 4:
            self.logger.error(log_msg)
        elif rank > 2:
            self.logger.debug(log_msg)
        else:
            self.logger.info(log_msg)

    def special_merge(self, df_split, merge_series, target: str = "zealot.png"):
        merge_df = None
        dryads_series = adv_filter_keys(merge_series, units="dryad.png")
        if not dryads_series.empty:
            dryads_rank = dryads_series.index.get_level_values("rank")
            for rank in dryads_rank:
                merge_series_dryad = adv_filter_keys(merge_series, units=["harlequin.png", "dryad.png"], ranks=rank)
                merge_series_zealot = adv_filter_keys(merge_series, units=["dryad.png", target], ranks=rank)
                if len(merge_series_dryad.index) == 2:
                    merge_df = self.merge_special_unit(df_split, merge_series_dryad, special_type="harlequin.png")
                    break
                if len(merge_series_zealot.index) == 2:
                    merge_df = self.merge_special_unit(df_split, merge_series_zealot, special_type="dryad.png")
                    break
        return merge_df

    def harley_merge(self, df_split, merge_series, target: str = "knight_statue.png"):
        merge_df = None
        hq_series = adv_filter_keys(merge_series, units="harlequin.png")
        if not hq_series.empty:
            hq_rank = hq_series.index.get_level_values("rank")
            for rank in hq_rank:
                merge_series_target = adv_filter_keys(merge_series, units=["harlequin.png", target], ranks=rank)
                if len(merge_series_target.index) == 2:
                    merge_df = self.merge_special_unit(df_split, merge_series_target, special_type="harlequin.png")
                    break
        return merge_df

    def try_merge(self, rank: int = 1, prev_grid=None, merge_target: str = "zealot.png"):
        info = ""
        merge_df = None
        names = self.scan_grid(new=False)
        grid_df = bot_perception.grid_status(names, prev_grid=prev_grid)
        df_split, unit_series, df_groups, _ = grid_meta_info(grid_df)
        merge_series = unit_series.copy()
        merge_series = adv_filter_keys(merge_series, units="empty.png", remove=True)
        self.special_merge(df_split, merge_series, merge_target)
        if merge_target == "demon_hunter.png":
            self.harley_merge(df_split, merge_series, target=merge_target)
            demons = adv_filter_keys(merge_series, units="demon_hunter.png")
            num_demon = sum(demons)
            if num_demon >= 11:
                self.logger.info("Board is full of demons, waiting...")
                time.sleep(10)
            if (
                hasattr(self, "config")
                and self.config.has_section("bot")
                and self.config.has_option("bot", "require_shaman")
                and self.config.getboolean("bot", "require_shaman")
            ):
                merge_series = adv_filter_keys(merge_series, units="demon_hunter.png", remove=True)
        merge_series = preserve_unit(merge_series, target="chemist.png")
        for _ in range(4):
            merge_series = preserve_unit(merge_series, target="cauldron.png", keep_min=True)
        num_knight = sum(adv_filter_keys(merge_series, units="knight_statue.png"))
        if num_knight % 2 == 1:
            self.harley_merge(df_split, merge_series, target="knight_statue.png")
        for _ in range(2):
            merge_series = preserve_unit(merge_series, target="knight_statue.png")
        merge_series = merge_series[merge_series >= 2]
        merge_series = adv_filter_keys(merge_series, ranks=7, remove=True)
        merge_prio = adv_filter_keys(
            merge_series, units=["chemist.png", "bombardier.png", "summoner.png", "knight_statue.png"]
        )
        if not merge_prio.empty:
            info = "Merging High Priority!"
            merge_df = self.merge_unit(df_split, merge_prio)
        if df_groups["empty.png"] <= 2:
            info = "Merging!"
            low_series = adv_filter_keys(merge_series, ranks=rank, remove=False)
            if not low_series.empty:
                merge_df = self.merge_unit(df_split, low_series)
            else:
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

    def mana_level(self, cards, hero_power: bool = False) -> None:
        upgrade_pos_dict = {1: [100, 1500], 2: [200, 1500], 3: [350, 1500], 4: [500, 1500], 5: [650, 1500]}
        for card in cards:
            self.click(*upgrade_pos_dict[card])
        if hero_power:
            self.click(800, 1500)

    def play_dungeon(self, floor: int = 5) -> None:
        self.logger.debug(f"Starting Dungeon floor {floor}")

        floor_icons = {
            1: "floor1.png",
            2: "floor2.png",
            3: "floor3.png",
            4: "floor4.png",
            5: "floor5.png",
            6: "floor6.png",
            7: "floor7.png",
            8: "floor8.png",
            9: "floor9.png",
            10: "floor10.png",
            11: "floor11.png",
            12: "floor12.png",
        }
        target_floor_icon_name = floor_icons.get(floor)
        if not target_floor_icon_name:
            self.logger.error(f"Invalid floor number: {floor}")
            return

        target_chapter = int(np.ceil(floor / 3))
        target_chapter_icon_name = f"chapter_{target_chapter}.png"

        self.logger.debug(f"Looking for target chapter: {target_chapter}, target floor: {target_floor_icon_name}")

        on_dungeon_page = False
        check_attempts = 0
        max_check_attempts = 5
        while not on_dungeon_page and check_attempts < max_check_attempts:
            avail_buttons = self.get_current_icons(available=True, new=True, icon_list=["dungeon_page.png"])
            if (avail_buttons["icon"] == "dungeon_page.png").any():
                self.logger.info("Successfully navigated to dungeon page.")
                on_dungeon_page = True
                break
            self.logger.warning(
                f"Not on dungeon page (attempt {check_attempts + 1}/{max_check_attempts}). Attempting navigation."
            )
            self.battle_screen(pve=True, start=False)
            time.sleep(2)
            check_attempts += 1

        if not on_dungeon_page:
            self.logger.error("Failed to navigate to dungeon page after multiple attempts.")
            return

        self.logger.debug("Scrolling to top of dungeon menu")
        for _ in range(5):
            self.swipe([0, 0], [2, 0])
            time.sleep(0.5)
        self.click(30, 600, 5)
        time.sleep(1)

        found_target_chapter = False
        scroll_attempts_chapter = 0
        max_scroll_attempts_chapter = 10

        while not found_target_chapter and scroll_attempts_chapter < max_scroll_attempts_chapter:
            avail_buttons = self.get_current_icons(
                available=True, new=True, icon_list=[f"chapter_{i}.png" for i in range(1, 13)]
            )
            self.logger.debug(
                f"Chapter scroll attempt {scroll_attempts_chapter + 1}: Available icons: {avail_buttons['icon'].tolist()}"
            )

            if (avail_buttons["icon"] == target_chapter_icon_name).any():
                chapter_pos = get_button_pos(avail_buttons, target_chapter_icon_name)
                self.logger.info(
                    f"Found target chapter {target_chapter} ({target_chapter_icon_name}) at position {chapter_pos}"
                )
                self.logger.info(f"Clicking chapter {target_chapter} to ensure it is expanded.")
                self.click_button(chapter_pos)
                time.sleep(1)
                found_target_chapter = True
                break

            self.logger.debug("Target chapter not visible. Scrolling down to find chapter.")
            self.swipe([2, 0], [0, 0])
            time.sleep(1)
            self.click(30, 600)
            time.sleep(1)
            scroll_attempts_chapter += 1

        if not found_target_chapter:
            self.logger.error(
                f"Could not find target chapter {target_chapter} ({target_chapter_icon_name}) after {max_scroll_attempts_chapter} scroll attempts."
            )
            return

        found_target_floor = False
        scroll_attempts_floor = 0
        max_scroll_attempts_floor = 5
        play_button_offset = np.array([330, 1030]) - np.array([120, 790])
        floor_pos = None

        while not found_target_floor and scroll_attempts_floor < max_scroll_attempts_floor:
            avail_buttons = self.get_current_icons(available=True, new=True, icon_list=[target_floor_icon_name])
            self.logger.debug(
                f"Floor scroll attempt {scroll_attempts_floor + 1}: Available icons: {avail_buttons['icon'].tolist()}"
            )

            if (avail_buttons["icon"] == target_floor_icon_name).any():
                floor_pos = get_button_pos(avail_buttons, target_floor_icon_name)
                self.logger.info(f"Found target floor {floor} ({target_floor_icon_name}) at position {floor_pos}")

                if floor_pos[1] > 1090:
                    self.logger.info(
                        f"Floor icon is low ({floor_pos[1]}). Scrolling down slightly to reveal Play button."
                    )
                    self.swipe([2, 0], [0, 0])
                    time.sleep(1)
                    self.click(30, 600)
                    time.sleep(1)
                    avail_buttons_after_scroll = self.get_current_icons(
                        available=True, new=True, icon_list=[target_floor_icon_name]
                    )
                    if (avail_buttons_after_scroll["icon"] == target_floor_icon_name).any():
                        floor_pos = get_button_pos(avail_buttons_after_scroll, target_floor_icon_name)
                        self.logger.info(f"Found target floor again after scrolling: {floor_pos}")
                    else:
                        self.logger.warning(
                            "Could not find floor icon after scrolling to reveal Play button. Proceeding with last known position."
                        )

                play_button_pos = floor_pos + play_button_offset
                self.logger.info(f"Calculated Play button position: {play_button_pos}")
                self.click_button(play_button_pos)

                found_target_floor = True
                break

            self.logger.debug("Target floor icon not visible. Scrolling down to find floor.")
            self.swipe([2, 0], [0, 0])
            time.sleep(1)
            self.click(30, 600)
            time.sleep(1)
            scroll_attempts_floor += 1

        if not found_target_floor:
            self.logger.error(
                f"Could not find target floor {floor} ({target_floor_icon_name}) after {max_scroll_attempts_floor} scroll attempts within the expanded chapter."
            )
            return

        self.logger.info("Clicked Play button. Waiting for co-op partner selection screen.")
        coop_screen_visible = False
        coop_check_attempts = 0
        max_coop_check_attempts = 15

        while not coop_screen_visible and coop_check_attempts < max_coop_check_attempts:
            avail_buttons = self.get_current_icons(available=True, new=True, icon_list=["random.png"])
            if (avail_buttons["icon"] == "random.png").any():
                self.logger.info("Found random co-op partner button. Clicking it.")
                coop_button_pos = get_button_pos(avail_buttons, "random.png")
                self.click_button(coop_button_pos)
                coop_screen_visible = True
                break
            self.logger.debug(
                f"Random co-op button not found (attempt {coop_check_attempts + 1}/{max_coop_check_attempts}). Waiting..."
            )
            time.sleep(2)
            coop_check_attempts += 1

        if not coop_screen_visible:
            self.logger.error("Could not find random co-op partner button after multiple attempts.")
            return

        self.logger.info("Clicked random co-op button. Waiting for match to start.")
        for i in range(30):
            time.sleep(2)
            avail_buttons = self.get_current_icons(available=True)
            if avail_buttons["icon"].isin(["back_button.png", "fighting.png"]).any():
                self.logger.info(f"Match started detected after {i * 2} seconds.")
                return

        self.logger.error("Match start not detected within timeout.")

    def battle_screen(self, start: bool = False, pve: bool = True, floor: int = 5):
        df = self.get_current_icons(available=True)
        if not df.empty:
            if (df["icon"] == "fighting.png").any() and not (df["icon"] == "0cont_button.png").any():
                return df, "fighting"
            if (df["icon"] == "friend_menu.png").any():
                self.click_button(np.array([100, 600]))
                return df, "friend_menu"
            if (df["icon"] == "home_screen.png").any() and (df["icon"] == "battle_icon.png").any():
                if pve and start:
                    pve_button_df = self.get_current_icons(available=True, new=False, icon_list=["pve_button.png"])
                    if (pve_button_df["icon"] == "pve_button.png").any():
                        pve_button_pos = get_button_pos(pve_button_df, "pve_button.png")
                        self.logger.info(
                            f"Found PvE button at {pve_button_pos}. Clicking to start dungeon navigation."
                        )
                        self.click_button(pve_button_pos)
                        time.sleep(2)
                        self.play_dungeon(floor=floor)
                    else:
                        self.logger.warning(
                            "On home screen but PvE button not found. Falling back to general battle icon."
                        )
                        battle_icon_pos = get_button_pos(df, "battle_icon.png")
                        self.click_button(battle_icon_pos)
                        time.sleep(2)
                        return self.battle_screen(start=start, pve=pve, floor=floor)

                elif start:
                    self.click_button(np.array([140, 1259]))
                time.sleep(1)
                return df, "home"
            df_click = df[df["icon"].isin(["back_button.png", "battle_icon.png", "0cont_button.png", "1quit.png"])]
            if not df_click.empty:
                button_pos = df_click["pos [X,Y]"].tolist()[0]
                self.click_button(button_pos)
                return df, "menu"

        end_screen_icons_filtered = ["cont_button.png"]
        end_screen_buttons = self.get_current_icons(available=True, icon_list=end_screen_icons_filtered)

        if not end_screen_buttons.empty:
            self.logger.info(
                f"Detected non-ad end screen icon(s): {end_screen_buttons['icon'].tolist()}. Attempting to click the first one."
            )
            first_end_button_pos = get_button_pos(end_screen_buttons, end_screen_buttons["icon"].iloc[0])
            self.click_button(first_end_button_pos)
            time.sleep(2)
            return self.battle_screen(start=start, pve=pve, floor=floor)

        self.key_input(const.KEYCODE_BACK)
        return df, "lost"

    def find_store_refresh(self):
        self.click_button((100, 1500))
        [self.swipe([0, 0], [2, 0]) for _ in range(5)]
        self.click(30, 150)
        avail_buttons = self.get_current_icons(available=True)
        if (avail_buttons["icon"] == "refresh_button.png").any():
            pos = get_button_pos(avail_buttons, "refresh_button.png")
            return pos

    def refresh_shop(self):
        self.click_button((100, 1500))
        self.click_button((475, 1300))
        pos = self.find_store_refresh()
        if isinstance(pos, np.ndarray):
            self.click_button(pos - [300, 820])
            self.click(400, 1165)
            self.click(30, 150)
            self.click_button(pos + [400, -400])
            self.click(400, 1165)
            self.click(30, 150)
            self.logger.warning("Bought store units!")
            self.click_button(pos)

    def watch_ads(self) -> None:
        avail_buttons = self.get_current_icons(available=True)
        if (avail_buttons["icon"] == "quest_done.png").any():
            pos = get_button_pos(avail_buttons, "quest_done.png")
            self.click_button(pos)
            self.click(700, 600)
            self.click(700, 400)
            [self.click(150, 250) for _ in range(2)]
            self.click(420, 420)
        elif (avail_buttons["icon"] == "ad_season.png").any():
            pos = get_button_pos(avail_buttons, "ad_season.png")
            self.click_button(pos)
        elif (avail_buttons["icon"] == "ad_pve.png").any():
            pos = get_button_pos(avail_buttons, "ad_pve.png")
            self.click_button(pos)
        elif (avail_buttons["icon"] == "battle_icon.png").any():
            self.refresh_shop()
        else:
            return
        avail_buttons, status = self.battle_screen()
        if status == "menu" or status == "home" or (avail_buttons["icon"] == "refresh_button.png").any():
            self.logger.info("FINISHED AD")
        else:
            time.sleep(30)
            for i in range(10):
                avail_buttons, status = self.battle_screen()
                if status == "menu" or status == "home":
                    self.logger.info("FINISHED AD")
                    return
                time.sleep(2)
                self.click(870, 30)
                self.click(870, 100)
                if i > 5:
                    self.key_input(const.KEYCODE_BACK)
                self.logger.info(f"AD TIME {i} {status}")
            self.restart_RR()


####
#### END OF CLASS
####


def get_grid():
    top_box = (153, 945)
    box_size = (120, 120)
    gap = 0
    height = 3
    width = 5
    x_cord = list(range(top_box[0], top_box[0] + (box_size[0] + gap) * width, box_size[0] + gap))
    y_cord = list(range(top_box[1], top_box[1] + (box_size[1] + gap) * height, box_size[1] + gap))
    boxes = []
    for y_point in y_cord:
        for x_point in x_cord:
            boxes.append((x_point, y_point))
    boxes = np.array(boxes).reshape(height, width, 2)
    return boxes, box_size


def get_unit_count(grid_df):
    df_split = grid_df.groupby("unit")
    df_groups = df_split["unit"].count()
    if "empty.png" not in df_groups:
        df_groups["empty.png"] = 0
    unit_list = list(df_groups.index)
    return df_split, df_groups, unit_list


def preserve_unit(unit_series, target: str = "chemist.png", keep_min: bool = False):
    merge_series = unit_series.copy()
    preserve_series = adv_filter_keys(merge_series, units=target, remove=False)
    if not preserve_series.empty:
        if keep_min:
            preserve_unit = preserve_series.index.min()
        else:
            preserve_unit = preserve_series.index.max()
        merge_series[merge_series.index == preserve_unit] = merge_series[merge_series.index == preserve_unit] - 1
        return merge_series[merge_series > 0]
    return merge_series


def grid_meta_info(grid_df, min_age: int = 0):
    df_groups = get_unit_count(grid_df)[1]
    grid_df = grid_df[grid_df["Age"] >= min_age].reset_index(drop=True)
    df_split = grid_df.groupby(["unit", "rank"])
    unit_series = df_split["unit"].count()
    group_keys = list(unit_series.index)
    return df_split, unit_series, df_groups, group_keys


def filter_units(unit_series, units):
    if not isinstance(units, list):
        if isinstance(units, (int, str)):
            units = [units]
        else:
            raise TypeError(
                f"Units must be a string, integer, or a list of strings/integers, but got {type(units)}"
            )

    series = []
    merge_series = unit_series.copy()
    for token in units:
        if isinstance(token, int):
            exists = merge_series.index.get_level_values("rank").isin([token]).any()
            if exists:
                series.append(merge_series.xs(token, level="rank", drop_level=False))
            else:
                continue
        elif isinstance(token, str):
            if token in merge_series:
                series.append(merge_series.xs(token, level="unit", drop_level=False))
            else:
                continue
        else:
            continue

    if series:
        temp_series = pd.concat(series)
        merge_series = merge_series[merge_series.index.isin(temp_series.index)]
        return merge_series
    return pd.Series(dtype=object)


def adv_filter_keys(unit_series, units=None, ranks=None, remove: bool = False):
    if unit_series.empty:
        return pd.Series(dtype=object)

    filtered_units = unit_series.copy()
    if units is not None:
        filtered_units = filter_units(filtered_units, units)

    filtered_ranks = filtered_units.copy()
    if ranks is not None and not filtered_units.empty:
        filtered_ranks = filter_units(filtered_units, ranks)

    series = unit_series.copy()
    if remove:
        if units is not None and ranks is not None:
            filtered_by_both = unit_series.copy()
            filtered_by_both = filter_units(filtered_by_both, units)
            if ranks is not None and not filtered_by_both.empty:
                filtered_by_both = filter_units(filtered_by_both, ranks)
            series = series[~series.index.isin(filtered_by_both.index)]
        elif units is not None:
            filtered_by_units = filter_units(unit_series, units)
            series = series[~series.index.isin(filtered_by_units.index)]
        elif ranks is not None:
            filtered_by_ranks = filter_units(unit_series, ranks)
            series = series[~series.index.isin(filtered_by_ranks.index)]
    else:
        series = filtered_ranks

    return series


def read_knowledge(bot):
    spam_click = range(1000)
    for _ in spam_click:
        bot.click(450, 1300, 0.1)


def get_button_pos(df: pd.DataFrame, button: str) -> np.ndarray:
    pos = df[df["icon"] == button]["pos [X,Y]"].reset_index(drop=True)[0]
    return np.array(pos)
