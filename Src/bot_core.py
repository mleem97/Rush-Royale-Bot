"""
Rush Royale Bot Core - Python 3.13 Compatible
Uses adbutils for ADB communication with vendored scrcpy client
"""
from __future__ import annotations

import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from subprocess import Popen, DEVNULL
from typing import Optional

import numpy as np
import pandas as pd
import cv2

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Internal modules
import bot_perception
import port_scan

# Android ADB - Using adbutils (matches requirements.txt)
try:
    from adbutils import adb, AdbDevice
    ADB_AVAILABLE = True
except ImportError:
    ADB_AVAILABLE = False
    adb = None
    AdbDevice = None

# Vendored scrcpy client
try:
    from scrcpy import Client, const
    SCRCPY_AVAILABLE = True
except ImportError:
    SCRCPY_AVAILABLE = False
    Client = None
    const = None

# Fallback constants if scrcpy not available
if const is None:
    class const:
        ACTION_DOWN = 0
        ACTION_UP = 1
        KEYCODE_BACK = 4

SLEEP_DELAY = 0.1


class Bot:

    def __init__(self, device: Optional[str] = None):
        self.bot_stop = False
        self.combat = self.output = self.grid_df = self.unit_series = None
        self.merge_series = self.df_groups = self.info = self.combat_step = None
        self.logger = logging.getLogger('__main__')
        
        # Get device
        if device is None:
            device = port_scan.get_device()
        if not device:
            raise Exception("No device found!")
        self.device = device
        self.bot_id = self.device.split(':')[-1]
        
        # Initialize ADB device using adbutils
        self.adb_device: Optional[AdbDevice] = None
        if ADB_AVAILABLE:
            try:
                # Connect to device
                adb.connect(self.device, timeout=5.0)
                self.adb_device = adb.device(serial=self.device)
                self.logger.info(f'Connected to device via adbutils: {self.device}')
            except Exception as e:
                self.logger.warning(f'adbutils connection failed: {e}, using shell fallback')
        
        # Fallback: use .scrcpy\adb if adbutils failed
        if not self.adb_device:
            self.shell(f'.scrcpy\\adb connect {self.device}')
        
        # Try to launch application through ADB shell
        self.shell('monkey -p com.my.defense 1')
        
        # Check if 'bot_feed.png' exists
        if not os.path.isfile(f'bot_feed_{self.bot_id}.png'):
            self.getScreen()
        self.screenRGB = cv2.imread(f'bot_feed_{self.bot_id}.png')
        
        # Initialize scrcpy client for touch input
        self.client = None
        if SCRCPY_AVAILABLE and Client is not None:
            try:
                self.client = Client(device=self.device)
                self.client.start(threaded=True)
                self.logger.info('Started scrcpy client for touch input')
                time.sleep(0.5)
                # Turn off video stream (spammy)
                self.client.alive = False
            except Exception as e:
                self.logger.warning(f'scrcpy client failed: {e}, using shell input')
                self.client = None
        
        self.logger.info('Bot initialized successfully')

    def __exit__(self, exc_type, exc_value, traceback):
        self.bot_stop = True
        self.logger.info('Exiting bot')
        if self.client:
            try:
                self.client.stop()
            except Exception:
                pass

    def shell(self, cmd: str):
        """Send ADB shell command"""
        if self.adb_device:
            try:
                return self.adb_device.shell(cmd)
            except Exception:
                pass
        # Fallback to .scrcpy\adb
        p = Popen([".scrcpy\\adb", '-s', self.device, 'shell', cmd], stdout=DEVNULL, stderr=DEVNULL)
        p.wait()

    def click(self, x: int, y: int, delay_mult: float = 1):
        """Send ADB to click screen"""
        if self.client and SCRCPY_AVAILABLE:
            self.client.control.touch(x, y, const.ACTION_DOWN)
            time.sleep(SLEEP_DELAY / 2 * delay_mult)
            self.client.control.touch(x, y, const.ACTION_UP)
        else:
            self.shell(f'input tap {x} {y}')
        time.sleep(SLEEP_DELAY * delay_mult)

    def click_button(self, pos):
        """Click button coords offset and extra delay"""
        coords = np.array(pos) + 10
        self.click(*coords)
        time.sleep(SLEEP_DELAY * 10)

    def swipe(self, start, end):
        """Swipe on combat grid to merge units"""
        boxes, box_size = get_grid()
        offset = 60
        start_pos = boxes[start[0], start[1]] + offset
        end_pos = boxes[end[0], end[1]] + offset
        
        if self.client and SCRCPY_AVAILABLE:
            self.client.control.swipe(*start_pos, *end_pos, 20, 1 / 60)
        else:
            self.shell(f'input swipe {start_pos[0]} {start_pos[1]} {end_pos[0]} {end_pos[1]} 300')

    def key_input(self, key: int):
        """Send key command"""
        if self.client and SCRCPY_AVAILABLE:
            self.client.control.keycode(key)
        else:
            self.shell(f'input keyevent {key}')

    def restart_game(self, quick_disconnect: bool = False):
        """Force restart the game through ADB, or spam disconnects to abandon match"""
        if quick_disconnect:
            for _ in range(15):
                self.shell('monkey -p com.my.defense 1')
            return
        # Force kill game through ADB shell
        self.shell('am force-stop com.my.defense')
        time.sleep(2)
        # Launch application through ADB shell
        self.shell('monkey -p com.my.defense 1')
        time.sleep(10)

    def getScreen(self):
        """Take screenshot of device screen and load pixel values"""
        bot_id = self.device.split(':')[-1]
        screenshot_path = f'bot_feed_{bot_id}.png'
        
        success = False
        
        # Method 1: Try adbutils screencap
        if self.adb_device and not success:
            try:
                png_data = self.adb_device.screencap()
                if png_data and len(png_data) > 1000:
                    with open(screenshot_path, 'wb') as f:
                        f.write(png_data)
                    success = True
                    self.logger.debug('Screenshot via adbutils')
            except Exception as e:
                self.logger.debug(f'adbutils screencap failed: {e}')
        
        # Method 2: Fallback to .scrcpy\adb
        if not success:
            try:
                p = Popen(['.scrcpy\\adb', '-s', self.device, 'exec-out', 'screencap', '-p'],
                         stdout=open(screenshot_path, 'wb'), stderr=DEVNULL)
                p.wait(timeout=10)
                if p.returncode == 0:
                    success = True
                    self.logger.debug('Screenshot via .scrcpy\\adb')
            except Exception as e:
                self.logger.debug(f'Shell screencap failed: {e}')
        
        # Method 3: Legacy shell redirect
        if not success:
            p = Popen(['.scrcpy\\adb', 'exec-out', 'screencap', '-p', '>', screenshot_path], shell=True)
            p.wait()
        
        # Load screenshot
        new_img = cv2.imread(screenshot_path)
        if new_img is not None:
            self.screenRGB = new_img
        else:
            self.logger.warning('Failed to get screen')

    def crop_img(self, x: int, y: int, dx: int, dy: int, name: str = 'icon.png'):
        """Crop latest screenshot taken"""
        img_rgb = self.screenRGB
        img_rgb = img_rgb[y:y + dy, x:x + dx]
        cv2.imwrite(name, img_rgb)

    def getMana(self) -> int:
        return int(self.getText(220, 1360, 90, 50, new=False, digits=True))

    def getXYByImage(self, target: str, new: bool = True):
        """Find icon on screen"""
        valid_targets = ['battle_icon', 'pvp_button', 'back_button', 'cont_button', 'fighting']
        if target not in valid_targets:
            return "INVALID TARGET"
        if new:
            self.getScreen()
        imgSrc = f'icons/{target}.png'
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
        store_states_names = ['refresh', 'new_store', 'nothing', 'new_offer', 'spin_only']
        store_states = np.array([[255, 255, 255], [27, 235, 206], [63, 38, 12], [48, 253, 251], [80, 153, 193]])
        store_rgb = self.screenRGB[y:y + 1, x:x + 1]
        store_rgb = store_rgb[0][0]
        store_mse = ((store_states - store_rgb)**2).mean(axis=1)
        closest_state = store_mse.argmin()
        return store_states_names[closest_state]

    def get_current_icons(self, new: bool = True, available: bool = False, icon_list=None) -> pd.DataFrame:
        """Check if any icons are on screen"""
        current_icons = []
        if new:
            self.getScreen()
        img_rgb = self.screenRGB
        if img_rgb is None:
            self.logger.warning('Screenshot is None - cannot detect icons')
            return pd.DataFrame(columns=['icon', 'available', 'pos [X,Y]'])
        
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        img_gray_blur = cv2.GaussianBlur(img_gray, (3, 3), 0)
        
        # Determine which icons to check
        if icon_list is None:
            icons_to_check = [f for f in os.listdir("icons") if f.endswith('.png')]
        else:
            icons_to_check = icon_list
        
        for target in icons_to_check:
            x = 0
            y = 0
            imgSrc = f'icons/{target}'
            
            if not os.path.isfile(imgSrc):
                continue
            
            template = cv2.imread(imgSrc, 0)
            if template is None:
                continue
            
            template_blur = cv2.GaussianBlur(template, (3, 3), 0)
            
            # Per-icon threshold tuning
            is_chapter = 'chapter_' in target
            threshold = 0.8
            if is_chapter:
                threshold = 0.75
            elif target == 'dungeon_page.png':
                threshold = 0.60
            elif 'floor_' in target:
                threshold = 0.95
            elif target == 'pve_random.png':
                threshold = 0.85
            elif target == 'pve_button.png':
                threshold = 0.85
            
            # Multi-scale matching for chapters
            found = False
            best_x, best_y = 0, 0
            max_val = 0
            
            scales = [0.9, 1.0, 1.1] if is_chapter else [1.0]
            for sc in scales:
                if sc != 1.0:
                    new_w = max(1, int(template_blur.shape[1] * sc))
                    new_h = max(1, int(template_blur.shape[0] * sc))
                    tmpl = cv2.resize(template_blur, (new_w, new_h), interpolation=cv2.INTER_AREA)
                else:
                    tmpl = template_blur
                
                if img_gray_blur.shape[0] < tmpl.shape[0] or img_gray_blur.shape[1] < tmpl.shape[1]:
                    continue
                
                res = cv2.matchTemplate(img_gray_blur, tmpl, cv2.TM_CCOEFF_NORMED)
                _, curr_max_val, _, max_loc = cv2.minMaxLoc(res)
                
                if curr_max_val > max_val:
                    max_val = curr_max_val
                    best_x, best_y = max_loc[0], max_loc[1]
                    found = curr_max_val >= threshold
            
            # Relax threshold slightly for chapters
            if is_chapter and not found and max_val >= (threshold - 0.05):
                found = True
            
            if found:
                x = int(best_x)
                y = int(best_y)
            
            current_icons.append([target, found, (x, y)])
        
        icon_df = pd.DataFrame(current_icons, columns=['icon', 'available', 'pos [X,Y]'])
        if available:
            icon_df = icon_df[icon_df['available'] == True].reset_index(drop=True)
        return icon_df

    def scan_grid(self, new: bool = False):
        """Scan battle grid, update OCR images"""
        boxes, box_size = get_grid()
        if new:
            self.getScreen()
        box_list = boxes.reshape(15, 2)
        names = []
        if not os.path.isdir('OCR_inputs'):
            os.mkdir('OCR_inputs')
        for i in range(len(box_list)):
            file_name = f'OCR_inputs/icon_{str(i)}.png'
            self.crop_img(*box_list[i], *box_size, name=file_name)
            names.append(file_name)
        return names

    def merge_unit(self, df_split, merge_series):
        """Take random unit in series, find corresponding dataframe and merge two random ones"""
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
        unit_chosen = merge_df['grid_pos'].tolist()
        self.swipe(*unit_chosen)
        time.sleep(0.2)
        return merge_df

    def merge_special_unit(self, df_split, merge_series, special_type):
        """Merge special units like harlequin, dryad, mime, scrapper"""
        special_unit, normal_unit = [
            adv_filter_keys(merge_series, units=special_type, remove=remove) for remove in [False, True]
        ]
        special_df, normal_df = [df_split.get_group(unit.index[0]).sample() for unit in [special_unit, normal_unit]]
        merge_df = pd.concat([special_df, normal_df])
        self.log_merge(merge_df)
        unit_chosen = merge_df['grid_pos'].tolist()
        self.swipe(*unit_chosen)
        time.sleep(0.2)
        return merge_df

    def log_merge(self, merge_df):
        merge_df['unit'] = merge_df['unit'].apply(lambda x: x.replace('.png', ''))
        unit1, unit2 = merge_df.iloc[0:2]['unit']
        rank = merge_df.iloc[0]['rank']
        log_msg = f"Rank {rank} {unit1}-> {unit2}"
        if rank > 4:
            self.logger.error(log_msg)
        elif rank > 2:
            self.logger.debug(log_msg)
        else:
            self.logger.info(log_msg)

    def special_merge(self, df_split, merge_series, target: str = 'zealot.png'):
        """Find targets for special merge"""
        merge_df = None
        dryads_series = adv_filter_keys(merge_series, units='dryad.png')
        if not dryads_series.empty:
            dryads_rank = dryads_series.index.get_level_values('rank')
            for rank in dryads_rank:
                merge_series_dryad = adv_filter_keys(merge_series, units=['harlequin.png', 'dryad.png'], ranks=rank)
                merge_series_zealot = adv_filter_keys(merge_series, units=['dryad.png', target], ranks=rank)
                if len(merge_series_dryad.index) == 2:
                    merge_df = self.merge_special_unit(df_split, merge_series_dryad, special_type='harlequin.png')
                    break
                if len(merge_series_zealot.index) == 2:
                    merge_df = self.merge_special_unit(df_split, merge_series_zealot, special_type='dryad.png')
                    break
        return merge_df

    def harley_merge(self, df_split, merge_series, target: str = 'knight_statue.png'):
        """Harley merge target"""
        merge_df = None
        hq_series = adv_filter_keys(merge_series, units='harlequin.png')
        if not hq_series.empty:
            hq_rank = hq_series.index.get_level_values('rank')
            for rank in hq_rank:
                merge_series_target = adv_filter_keys(merge_series, units=['harlequin.png', target], ranks=rank)
                if len(merge_series_target.index) == 2:
                    merge_df = self.merge_special_unit(df_split, merge_series_target, special_type='harlequin.png')
                    break
        return merge_df

    def try_merge(self, rank: int = 1, prev_grid=None, merge_target: str = 'zealot.png'):
        """Try to find a merge target and merge it"""
        info = ''
        merge_df = None
        names = self.scan_grid(new=False)
        grid_df = bot_perception.grid_status(names, prev_grid=prev_grid)
        df_split, unit_series, df_groups, group_keys = grid_meta_info(grid_df)
        merge_series = unit_series.copy()
        merge_series = adv_filter_keys(merge_series, units='empty.png', remove=True)
        self.special_merge(df_split, merge_series, merge_target)
        
        if merge_target == 'demon_hunter.png':
            self.harley_merge(df_split, merge_series, target=merge_target)
            demons = adv_filter_keys(merge_series, units='demon_hunter.png')
            num_demon = sum(demons)
            if num_demon >= 11:
                self.logger.info('Board is full of demons, waiting...')
                time.sleep(10)
            if hasattr(self, 'config') and self.config.has_section('bot') and self.config.has_option('bot', 'require_shaman'):
                if self.config.getboolean('bot', 'require_shaman'):
                    merge_series = adv_filter_keys(merge_series, units='demon_hunter.png', remove=True)
        
        merge_series = preserve_unit(merge_series, target='chemist.png')
        for _ in range(4):
            merge_series = preserve_unit(merge_series, target='cauldron.png', keep_min=True)
        num_knight = sum(adv_filter_keys(merge_series, units='knight_statue.png'))
        if num_knight % 2 == 1:
            self.harley_merge(df_split, merge_series, target='knight_statue.png')
        for _ in range(2):
            merge_series = preserve_unit(merge_series, target='knight_statue.png')
        merge_series = merge_series[merge_series >= 2]
        merge_series = adv_filter_keys(merge_series, ranks=7, remove=True)
        merge_prio = adv_filter_keys(merge_series, units=['chemist.png', 'bombardier.png', 'summoner.png', 'knight_statue.png'])
        if not merge_prio.empty:
            info = 'Merging High Priority!'
            merge_df = self.merge_unit(df_split, merge_prio)
        if df_groups['empty.png'] <= 2:
            info = 'Merging!'
            low_series = adv_filter_keys(merge_series, ranks=rank, remove=False)
            if not low_series.empty:
                merge_df = self.merge_unit(df_split, low_series)
            else:
                info = 'Merging high level!'
                merge_series = adv_filter_keys(merge_series, ranks=[3, 4, 5, 6, 7],
                                               units=['zealot.png', 'crystal.png', 'bruser.png', merge_target], remove=True)
                if not merge_series.empty:
                    merge_df = self.merge_unit(df_split, merge_series)
        else:
            info = 'need more units!'
        return grid_df, unit_series, merge_series, merge_df, info

    def mana_level(self, cards, hero_power: bool = False):
        """Mana level cards"""
        upgrade_pos_dict = {1: [100, 1500], 2: [200, 1500], 3: [350, 1500], 4: [500, 1500], 5: [650, 1500]}
        for card in cards:
            self.click(*upgrade_pos_dict[card])
        if hero_power:
            self.click(800, 1500)

    def play_dungeon(self, floor: int = 5):
        """Start a dungeon floor from PvE page"""
        self.logger.debug(f'Starting Dungeon floor {floor}')
        
        # Floor icons use underscore naming: floor_1.png through floor_14.png
        floor_icons = {i: f'floor_{i}.png' for i in range(1, 15)}
        target_floor_icon_name = floor_icons.get(floor)
        if not target_floor_icon_name:
            self.logger.error(f'Invalid floor number: {floor}. Valid range is 1-14.')
            return
        
        target_chapter = int(np.ceil(floor / 3))
        target_chapter_icon_name = f'chapter_{target_chapter}.png'
        
        self.logger.debug(f'Looking for chapter {target_chapter}, floor {target_floor_icon_name}')
        
        # Check if on dungeon page
        on_dungeon_page = False
        for attempt in range(5):
            avail_buttons = self.get_current_icons(available=True, new=True, icon_list=['dungeon_page.png'])
            if (avail_buttons['icon'] == 'dungeon_page.png').any():
                self.logger.info('On dungeon page.')
                on_dungeon_page = True
                break
            self.logger.warning(f'Not on dungeon page (attempt {attempt + 1}/5). Navigating...')
            self.battle_screen(pve=True, start=False)
            time.sleep(2)
        
        if not on_dungeon_page:
            self.logger.error('Failed to navigate to dungeon page.')
            return
        
        # Scroll to top
        self.logger.debug('Scrolling to top of dungeon menu')
        for _ in range(5):
            self.swipe([0, 0], [2, 0])
            time.sleep(0.5)
        self.click(30, 600, 5)
        time.sleep(1)
        
        # Find target chapter
        found_chapter = False
        for scroll_attempt in range(10):
            avail_buttons = self.get_current_icons(available=True, new=True,
                                                   icon_list=[f'chapter_{i}.png' for i in range(1, 7)])
            
            if (avail_buttons['icon'] == target_chapter_icon_name).any():
                chapter_pos = get_button_pos(avail_buttons, target_chapter_icon_name)
                self.logger.info(f'Found chapter {target_chapter} at {chapter_pos}')
                self.click_button(chapter_pos)
                time.sleep(1)
                found_chapter = True
                break
            
            self.logger.debug('Scrolling to find chapter...')
            self.swipe([2, 0], [0, 0])
            time.sleep(1)
            self.click(30, 600)
            time.sleep(1)
        
        if not found_chapter:
            self.logger.error(f'Could not find chapter {target_chapter}')
            return
        
        # Find target floor
        found_floor = False
        play_button_offset = np.array([330, 1030]) - np.array([120, 790])
        
        for scroll_attempt in range(5):
            avail_buttons = self.get_current_icons(available=True, new=True, icon_list=[target_floor_icon_name])
            
            if (avail_buttons['icon'] == target_floor_icon_name).any():
                floor_pos = get_button_pos(avail_buttons, target_floor_icon_name)
                self.logger.info(f'Found floor {floor} at {floor_pos}')
                
                # Scroll if floor is too low
                if floor_pos[1] > 1090:
                    self.swipe([2, 0], [0, 0])
                    time.sleep(1)
                    self.click(30, 600)
                    time.sleep(1)
                    avail_buttons = self.get_current_icons(available=True, new=True, icon_list=[target_floor_icon_name])
                    if (avail_buttons['icon'] == target_floor_icon_name).any():
                        floor_pos = get_button_pos(avail_buttons, target_floor_icon_name)
                
                play_button_pos = floor_pos + play_button_offset
                self.logger.info(f'Clicking play button at {play_button_pos}')
                self.click_button(play_button_pos)
                found_floor = True
                break
            
            self.swipe([2, 0], [0, 0])
            time.sleep(1)
            self.click(30, 600)
            time.sleep(1)
        
        if not found_floor:
            self.logger.error(f'Could not find floor {floor}')
            return
        
        # Wait for co-op screen and click random partner (pve_random.png)
        self.logger.info('Waiting for co-op partner selection...')
        for attempt in range(15):
            avail_buttons = self.get_current_icons(available=True, new=True, icon_list=['pve_random.png'])
            if (avail_buttons['icon'] == 'pve_random.png').any():
                self.logger.info('Found random co-op button. Clicking...')
                coop_pos = get_button_pos(avail_buttons, 'pve_random.png')
                self.click_button(coop_pos)
                break
            time.sleep(2)
        else:
            self.logger.error('Could not find random co-op button.')
            return
        
        # Wait for match to start
        self.logger.info('Waiting for match to start...')
        for i in range(30):
            time.sleep(2)
            avail_buttons = self.get_current_icons(available=True)
            if avail_buttons['icon'].isin(['back_button.png', 'fighting.png']).any():
                self.logger.info(f'Match started after {i * 2} seconds.')
                return
        
        self.logger.error('Match start not detected.')

    def battle_screen(self, start: bool = False, pve: bool = True, floor: int = 5):
        """Locate game home screen and try to start fight if chosen"""
        df = self.get_current_icons(available=True)
        if not df.empty:
            if (df['icon'] == 'fighting.png').any() and not (df['icon'] == '0cont_button.png').any():
                return df, 'fighting'
            if (df['icon'] == 'friend_menu.png').any():
                self.click_button(np.array([100, 600]))
                return df, 'friend_menu'
            if (df['icon'] == 'home_screen.png').any() and (df['icon'] == 'battle_icon.png').any():
                if pve and start:
                    self.click_button(np.array([640, 1259]))
                    self.play_dungeon(floor=floor)
                elif start:
                    self.click_button(np.array([140, 1259]))
                time.sleep(1)
                return df, 'home'
            df_click = df[df['icon'].isin(['back_button.png', 'battle_icon.png', '0cont_button.png', '1quit.png'])]
            if not df_click.empty:
                button_pos = df_click['pos [X,Y]'].tolist()[0]
                self.click_button(button_pos)
                return df, 'menu'
        self.key_input(const.KEYCODE_BACK)
        return df, 'lost'

    def find_store_refresh(self):
        """Navigate and locate store refresh button from battle screen"""
        self.click_button((100, 1500))
        for _ in range(5):
            self.swipe([0, 0], [2, 0])
        self.click(30, 150)
        avail_buttons = self.get_current_icons(available=True)
        if (avail_buttons['icon'] == 'refresh_button.png').any():
            pos = get_button_pos(avail_buttons, 'refresh_button.png')
            return pos

    def refresh_shop(self):
        """Refresh items in shop when available"""
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
            self.logger.warning('Bought store units!')
            self.click_button(pos)

    def watch_ads(self):
        """Watch ads if available"""
        avail_buttons = self.get_current_icons(available=True)
        if (avail_buttons['icon'] == 'quest_done.png').any():
            pos = get_button_pos(avail_buttons, 'quest_done.png')
            self.click_button(pos)
            self.click(700, 600)
            self.click(700, 400)
            for _ in range(2):
                self.click(150, 250)
            self.click(420, 420)
        elif (avail_buttons['icon'] == 'ad_season.png').any():
            pos = get_button_pos(avail_buttons, 'ad_season.png')
            self.click_button(pos)
        elif (avail_buttons['icon'] == 'ad_pve.png').any():
            pos = get_button_pos(avail_buttons, 'ad_pve.png')
            self.click_button(pos)
        elif (avail_buttons['icon'] == 'battle_icon.png').any():
            self.refresh_shop()
        else:
            return
        
        avail_buttons, status = self.battle_screen()
        if status == 'menu' or status == 'home' or (avail_buttons['icon'] == 'refresh_button.png').any():
            self.logger.info('FINISHED AD')
        else:
            time.sleep(30)
            for i in range(10):
                avail_buttons, status = self.battle_screen()
                if status == 'menu' or status == 'home':
                    self.logger.info('FINISHED AD')
                    return
                time.sleep(2)
                self.click(870, 30)
                self.click(870, 100)
                if i > 5:
                    self.key_input(const.KEYCODE_BACK)
                self.logger.info(f'AD TIME {i} {status}')
            self.restart_game()


####
#### END OF CLASS
####


def get_grid():
    """Get fight grid pixel values"""
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
    if 'empty.png' not in df_groups:
        df_groups['empty.png'] = 0
    unit_list = list(df_groups.index)
    return df_split, df_groups, unit_list


def preserve_unit(unit_series, target: str = 'chemist.png', keep_min: bool = False):
    """Remove 1x of the highest rank unit from the merge_series"""
    merge_series = unit_series.copy()
    preserve_series = adv_filter_keys(merge_series, units=target, remove=False)
    if not preserve_series.empty:
        if keep_min:
            preserve_unit_idx = preserve_series.index.min()
        else:
            preserve_unit_idx = preserve_series.index.max()
        merge_series[merge_series.index == preserve_unit_idx] = merge_series[merge_series.index == preserve_unit_idx] - 1
        return merge_series[merge_series > 0]
    return merge_series


def grid_meta_info(grid_df, min_age: int = 0):
    """Split grid df into unique units and ranks"""
    df_groups = get_unit_count(grid_df)[1]
    grid_df = grid_df[grid_df['Age'] >= min_age].reset_index(drop=True)
    df_split = grid_df.groupby(['unit', 'rank'])
    unit_series = df_split['unit'].count()
    group_keys = list(unit_series.index)
    return df_split, unit_series, df_groups, group_keys


def filter_units(unit_series, units):
    if not isinstance(units, list):
        units = [units]
    series = []
    merge_series = unit_series.copy()
    for token in units:
        if isinstance(token, int):
            exists = merge_series.index.get_level_values('rank').isin([token]).any()
            if exists:
                series.append(merge_series.xs(token, level='rank', drop_level=False))
        elif isinstance(token, str):
            if token in merge_series:
                series.append(merge_series.xs(token, level='unit', drop_level=False))
    if series:
        temp_series = pd.concat(series)
        merge_series = merge_series[merge_series.index.isin(temp_series.index)]
        return merge_series
    return pd.Series(dtype=object)


def adv_filter_keys(unit_series, units=None, ranks=None, remove: bool = False):
    """Returns all elements which match units and ranks values"""
    if unit_series.empty:
        return pd.Series(dtype=object)
    
    if units is not None:
        filtered_units = filter_units(unit_series, units)
    else:
        filtered_units = unit_series.copy()
    
    if ranks is not None and not filtered_units.empty:
        filtered_ranks = filter_units(filtered_units, ranks)
    else:
        filtered_ranks = filtered_units.copy()
    
    series = unit_series.copy()
    if remove:
        series = series[~series.index.isin(filtered_ranks.index)]
    else:
        series = series[series.index.isin(filtered_ranks.index)]
    return series


def read_knowledge(bot):
    """Spam read all knowledge in knowledge base for free gold"""
    for _ in range(1000):
        bot.click(450, 1300, 0.1)


def get_button_pos(df: pd.DataFrame, button: str) -> np.ndarray:
    pos = df[df['icon'] == button]['pos [X,Y]'].reset_index(drop=True)[0]
    return np.array(pos)
