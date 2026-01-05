"""
Rush Royale Bot Core - Python 3.13 Compatible
Enhanced error handling and modern Python features
"""
from __future__ import annotations

import os
import time
import configparser
import numpy as np
import pandas as pd
import logging
import subprocess
import shutil
from subprocess import Popen, DEVNULL, PIPE
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

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
        def __init__(self, host='127.0.0.1', port=5037):
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
    ADB_AVAILABLE = False

# Image processing
import cv2

# Handle imports - support both package and direct execution
try:
    from . import bot_perception
    from . import port_scan
    from .utils.icon_detector import IconDetector, DetectionConfig
    ICON_DETECTOR_AVAILABLE = True
except ImportError:
    # Direct execution fallback
    import bot_perception
    import port_scan
    ICON_DETECTOR_AVAILABLE = False
    IconDetector = None
    DetectionConfig = None

# Template coverage analyzer (optional)
try:
    from scripts.template_coverage import TemplateCoverageAnalyzer, CoverageReport
    COVERAGE_ANALYZER_AVAILABLE = True
except ImportError:
    COVERAGE_ANALYZER_AVAILABLE = False
    TemplateCoverageAnalyzer = None
    CoverageReport = None

# Hybrid Navigator (optional) - Kombiniert feste Positionen + Farberkennung + Templates
try:
    from .utils.hybrid_navigator import HybridNavigator, integrate_hybrid_navigator, ScreenType
    HYBRID_NAVIGATOR_AVAILABLE = True
except ImportError:
    try:
        from Src.utils.hybrid_navigator import HybridNavigator, integrate_hybrid_navigator, ScreenType
        HYBRID_NAVIGATOR_AVAILABLE = True
    except ImportError:
        HYBRID_NAVIGATOR_AVAILABLE = False
        HybridNavigator = None
        ScreenType = None

# Template-Free Detector - Komplett ohne Templates
try:
    from .utils.template_free_detector import TemplateFreeDetector, GameScreen, BattleState
    TEMPLATE_FREE_AVAILABLE = True
except ImportError:
    try:
        from Src.utils.template_free_detector import TemplateFreeDetector, GameScreen, BattleState
        TEMPLATE_FREE_AVAILABLE = True
    except ImportError:
        TEMPLATE_FREE_AVAILABLE = False
        TemplateFreeDetector = None
        GameScreen = None
        BattleState = None

# Screen Positions - Feste UI-Koordinaten
try:
    from .utils.screen_positions import HomeScreen, DungeonScreen, BattleScreen, GenericButtons
    SCREEN_POSITIONS_AVAILABLE = True
except ImportError:
    try:
        from Src.utils.screen_positions import HomeScreen, DungeonScreen, BattleScreen, GenericButtons
        SCREEN_POSITIONS_AVAILABLE = True
    except ImportError:
        SCREEN_POSITIONS_AVAILABLE = False

SLEEP_DELAY = 0.1

# Global config cache
_config_cache: Optional[configparser.ConfigParser] = None


def _load_config() -> configparser.ConfigParser:
    """Load configuration from config.ini."""
    global _config_cache
    if _config_cache is None:
        _config_cache = configparser.ConfigParser()
        config_path = Path(__file__).parent.parent / "config.ini"
        if config_path.exists():
            _config_cache.read(config_path)
    return _config_cache


def _save_debug_screenshot(screen: np.ndarray, prefix: str = "debug") -> Optional[Path]:
    """Save a debug screenshot if enabled in config."""
    try:
        config = _load_config()
        if config.getboolean('detection', 'debug_save_screenshots', fallback=False):
            debug_dir = Path(__file__).parent.parent / "screenshots"
            debug_dir.mkdir(exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filepath = debug_dir / f"{prefix}_{timestamp}.png"
            cv2.imwrite(str(filepath), cv2.cvtColor(screen, cv2.COLOR_RGB2BGR))
            return filepath
    except Exception:
        pass
    return None


def _get_threshold(key: str, default: float) -> float:
    """Get threshold value from config."""
    config = _load_config()
    try:
        return config.getfloat('detection', key)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return default


class Bot:

    def __init__(self, device=None):
        self.bot_stop = False
        self.combat = self.output = self.grid_df = self.unit_series = self.merge_series = self.df_groups = self.info = self.combat_step = None
        self.logger = logging.getLogger('__main__')
        if device is None:
            device = port_scan.get_device()
        if not device:
            raise Exception("No device found!")
        self.device = device
        self.bot_id = self.device.split(':')[-1]
        
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
            self.shell(f'adb connect {self.device}')
            devices = self.adb_client.devices()
            for dev in devices:
                if dev.serial == self.device:
                    self.adb_device = dev
                    break
        
        if not self.adb_device:
            raise Exception(f"Could not connect to device {self.device}")
            
        # Launch application through ADB shell
        self.adb_device.shell('monkey -p com.my.defense 1')
        
        # Check if 'bot_feed.png' exists
        if not os.path.isfile(f'bot_feed_{self.bot_id}.png'):
            self.getScreen()
        self.screenRGB = cv2.imread(f'bot_feed_{self.bot_id}.png')
        
        self.logger.info('Connected to Android device via ADB')
        time.sleep(0.5)
        
        # Initialize Hybrid Navigator (feste Positionen + Farberkennung + Template-Fallback)
        self.hybrid_nav = None
        if HYBRID_NAVIGATOR_AVAILABLE:
            try:
                self.hybrid_nav = integrate_hybrid_navigator(self)
                self.logger.info('Hybrid Navigator initialisiert (Positions + Farben + Templates)')
            except Exception as e:
                self.logger.warning(f'Hybrid Navigator konnte nicht initialisiert werden: {e}')
        
        # Initialize Template-Free Detector (KEINE Templates nötig!)
        self.template_free_detector = None
        if TEMPLATE_FREE_AVAILABLE:
            try:
                self.template_free_detector = TemplateFreeDetector()
                self.logger.info('Template-Free Detector initialisiert (keine Templates nötig)')
            except Exception as e:
                self.logger.warning(f'Template-Free Detector konnte nicht initialisiert werden: {e}')
        
        # Modus: 'template_free' (neu), 'hybrid' oder 'legacy' (Template-basiert)
        self.detection_mode = 'template_free' if self.template_free_detector else (
            'hybrid' if self.hybrid_nav else 'legacy'
        )
        self.logger.info(f'Detection Mode: {self.detection_mode}')

    def __exit__(self, exc_type, exc_value, traceback):
        self.bot_stop = True
        self.logger.info('Exiting bot')
        # Stop scrcpy process if running
        if self.scrcpy_process:
            self.stop_scrcpy()

    def find_scrcpy_executable(self) -> Optional[str]:
        """Find scrcpy executable in common locations"""
        possible_paths = [
            'scrcpy.exe',  # In PATH
            r'C:\Program Files\scrcpy\scrcpy.exe',
            r'C:\Program Files (x86)\scrcpy\scrcpy.exe',
            r'.\scrcpy\scrcpy.exe',  # Local directory
            r'.\bin\scrcpy.exe',
        ]
        
        for path in possible_paths:
            if shutil.which(path) or os.path.exists(path):
                self.logger.info(f'Found scrcpy at: {path}')
                return path
        
        self.logger.warning('scrcpy executable not found - will use ADB screencap fallback')
        return None

    def start_scrcpy(self) -> bool:
        """Start scrcpy process for screen mirroring"""
        if not self.scrcpy_executable:
            return False
            
        try:
            # Start scrcpy in window mode with no controls (view only)
            cmd = [
                self.scrcpy_executable,
                '--serial', self.device,
                '--no-control',  # View only
                '--window-title', f'RR Bot {self.device}',
                '--window-width', '800',
                '--window-height', '450'
            ]
            
            self.scrcpy_process = Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
            self.logger.info('Started scrcpy process for screen mirroring')
            time.sleep(2)  # Give scrcpy time to start
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to start scrcpy: {e}')
            self.scrcpy_process = None
            return False

    def stop_scrcpy(self):
        """Stop scrcpy process"""
        if self.scrcpy_process:
            try:
                self.scrcpy_process.terminate()
                self.scrcpy_process.wait(timeout=5)
                self.logger.info('Stopped scrcpy process')
            except subprocess.TimeoutExpired:
                self.scrcpy_process.kill()
                self.logger.warning('Force killed scrcpy process')
            except Exception as e:
                self.logger.error(f'Error stopping scrcpy: {e}')
            finally:
                self.scrcpy_process = None

    # Function to send ADB shell command
    def shell(self, cmd):
        if self.adb_device:
            return self.adb_device.shell(cmd)
        else:
            # Fallback to system ADB
            p = Popen(['adb', '-s', self.device, 'shell', cmd], stdout=DEVNULL, stderr=DEVNULL)
            p.wait()

    # Send ADB to click screen
    def click(self, x, y, delay_mult=1):
        if self.adb_device:
            self.adb_device.input_tap(x, y)
        else:
            # Fallback to shell command
            self.shell(f'input tap {x} {y}')
        time.sleep(SLEEP_DELAY * delay_mult)

    # Click button coords offset and extra delay
    def click_button(self, pos):
        coords = np.array(pos) + 10
        self.click(*coords)
        time.sleep(SLEEP_DELAY * 10)

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
            self.shell(f'input swipe {start_pos[0]} {start_pos[1]} {end_pos[0]} {end_pos[1]} 300')

    # Send key command
    def key_input(self, key):
        if self.adb_device:
            self.adb_device.input_keyevent(key)
        else:
            self.shell(f'input keyevent {key}')

    # Force restart the game through ADB, or spam 10 disconnects to abandon match
    def restart_RR(self, quick_disconnect=False):
        if quick_disconnect:
            for i in range(15):
                if self.adb_device:
                    self.adb_device.shell('monkey -p com.my.defense 1')
                else:
                    self.shell('monkey -p com.my.defense 1')  # disconnects really quick for unknown reasons
            return
        # Force kill game through ADB shell
        if self.adb_device:
            self.adb_device.shell('am force-stop com.my.defense')
        else:
            self.shell('am force-stop com.my.defense')
        time.sleep(2)
        # Launch application through ADB shell
        if self.adb_device:
            self.adb_device.shell('monkey -p com.my.defense 1')
        else:
            self.shell('monkey -p com.my.defense 1')
        time.sleep(10)  # wait for app to load

    # Take screenshot of device screen and load pixel values
    def getScreen(self):
        bot_id = self.device.split(':')[-1]
        screenshot_path = f'bot_feed_{bot_id}.png'
        
        # Method 1: Try scrcpy executable screenshot (fastest, highest quality)
        if self.scrcpy_executable and self._try_scrcpy_screenshot(screenshot_path):
            self.logger.debug('Screenshot taken via scrcpy executable')
        # Method 2: Try pure-python-adb (reliable)
        elif self._try_adb_screenshot(screenshot_path):
            self.logger.debug('Screenshot taken via pure-python-adb')
        # Method 3: Fallback to shell ADB (last resort)
        elif self._try_shell_screenshot(screenshot_path):
            self.logger.debug('Screenshot taken via ADB shell')
        else:
            self.logger.error('All screenshot methods failed!')
            return
        
        # Load screenshot and validate
        try:
            new_img = cv2.imread(screenshot_path)
            if new_img is not None and new_img.shape[0] > 0 and new_img.shape[1] > 0:
                self.screenRGB = new_img
                self.logger.debug(f'Screenshot loaded successfully: {new_img.shape}')
            else:
                self.logger.warning(f'Invalid screenshot file: {screenshot_path}')
        except Exception as e:
            self.logger.error(f'Failed to load screenshot: {e}')

    def _try_scrcpy_screenshot(self, output_path: str) -> bool:
        """Try taking screenshot using scrcpy executable"""
        if not self.scrcpy_executable:
            return False
        try:
            cmd = [
                self.scrcpy_executable,
                '--serial', self.device,
                '--no-display',  # No window
                '--record', output_path.replace('.png', '.mp4'),
                '--time-limit', '1'  # Record for 1 second
            ]
            # Alternative: use scrcpy screenshot feature if available
            cmd = ['adb', '-s', self.device, 'exec-out', 'screencap', '-p']
            with open(output_path, 'wb') as f:
                p = subprocess.run(cmd, stdout=f, stderr=DEVNULL, timeout=10)
                return p.returncode == 0
        except Exception:
            return False

    def _try_adb_screenshot(self, output_path: str) -> bool:
        """Try taking screenshot using pure-python-adb"""
        try:
            if self.adb_device:
                screencap = self.adb_device.screencap()
                if screencap and len(screencap) > 1000:  # Reasonable size check
                    with open(output_path, 'wb') as f:
                        f.write(screencap)
                    return True
        except Exception as e:
            self.logger.debug(f'ADB screencap failed: {e}')
        return False

    def _try_shell_screenshot(self, output_path: str) -> bool:
        """Try taking screenshot using shell ADB command"""
        try:
            cmd = ['adb', '-s', self.device, 'exec-out', 'screencap', '-p']
            with open(output_path, 'wb') as f:
                p = subprocess.run(cmd, stdout=f, stderr=DEVNULL, timeout=10)
                return p.returncode == 0
        except Exception:
            return False

    # Crop latest screenshot taken
    def crop_img(self, x, y, dx, dy, name='icon.png'):
        # Load screen
        img_rgb = self.screenRGB
        img_rgb = img_rgb[y:y + dy, x:x + dx]
        cv2.imwrite(name, img_rgb)

    def getMana(self):
        return int(self.getText(220, 1360, 90, 50, new=False, digits=True))

    # find icon on screen
    def getXYByImage(self, target, new=True):
        valid_targets = ['battle_icon', 'pvp_button', 'back_button', 'cont_button', 'fighting']
        if not target in valid_targets:
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
        # Take mean square of rgb value and store states
        store_mse = ((store_states - store_rgb)**2).mean(axis=1)
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
            self.logger.warning('Screenshot is None - cannot detect icons')
            return pd.DataFrame(columns=['icon', 'available', 'pos [X,Y]'])
            
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        # Light blur to reduce noise and improve template match stability
        img_gray_blur = cv2.GaussianBlur(img_gray, (3, 3), 0)
        self.logger.debug(f'Screenshot shape: {img_gray.shape}')
        
        # Load thresholds from config
        icon_threshold = _get_threshold('icon_threshold', 0.78)
        chapter_threshold = _get_threshold('chapter_threshold', 0.70)
        dungeon_threshold = _get_threshold('dungeon_page_threshold', 0.72)
        fighting_threshold = _get_threshold('fighting_threshold', 0.75)
        
        def match_template_multi_scale(src_gray, tmpl_gray, base_thresh, is_chapter=False):
            """Return (found:boolean, (x,y):tuple, max_val:float). Tries multiple scales when needed."""
            best = (False, (0, 0), 0.0)
            # per-icon scaling tries
            scales = [1.0]
            if is_chapter:
                scales = [0.9, 1.0, 1.1]
            for sc in scales:
                if sc != 1.0:
                    new_w = max(1, int(tmpl_gray.shape[1] * sc))
                    new_h = max(1, int(tmpl_gray.shape[0] * sc))
                    tmpl = cv2.resize(tmpl_gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
                else:
                    tmpl = tmpl_gray
                if src_gray.shape[0] < tmpl.shape[0] or src_gray.shape[1] < tmpl.shape[1]:
                    continue
                res = cv2.matchTemplate(src_gray, tmpl, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                # Keep best regardless of threshold, decide later
                if max_val > best[2]:
                    best = (max_val >= base_thresh, (max_loc[0], max_loc[1]), float(max_val))
            # Fallback: slightly relax if near-threshold for chapters
            if is_chapter and not best[0] and best[2] >= (base_thresh - 0.05):
                return (True, best[1], best[2])
            return best

        # Check every target in dir - only .png files, skip directories
        icon_count = 0
        icons_path = Path("icons")
        for target in os.listdir("icons"):
            target_path = icons_path / target
            # Skip directories and non-PNG files
            if target_path.is_dir() or not target.lower().endswith('.png'):
                continue
            x = 0  # reset position
            y = 0
            # Load icon
            imgSrc = f'icons/{target}'
            template = cv2.imread(imgSrc, 0)
            if template is None:
                self.logger.debug(f'Could not load template: {imgSrc}')
                continue
            # Slight blur for template too
            template_blur = cv2.GaussianBlur(template, (3, 3), 0)
            # Per-icon threshold tuning - loaded from config
            is_chapter = ('chapter_' in target)
            threshold = icon_threshold
            if is_chapter:
                threshold = chapter_threshold
            elif target in ['dungeon_page.png']:
                threshold = dungeon_threshold
            elif target in ['fighting.png', 'back_button.png']:
                threshold = fighting_threshold

            # Compare images using robust best-location extraction
            found, (best_x, best_y), max_val = match_template_multi_scale(img_gray_blur, template_blur, threshold, is_chapter=is_chapter)
            icon_found = found
            
            # Enhanced debug for dungeon-related icons
            if target in ['home_screen.png', 'battle_icon.png', 'dungeon_page.png'] or 'chapter_' in target:
                self.logger.debug(f'Icon {target}: max_val={max_val:.3f}, threshold={threshold:.2f}, found={icon_found}')
            
            if icon_found:
                y = int(best_y)
                x = int(best_x)
                icon_count += 1
            current_icons.append([target, icon_found, (x, y)])
            
        self.logger.debug(f'Total icons found: {icon_count}/{len(current_icons)}')
        icon_df = pd.DataFrame(current_icons, columns=['icon', 'available', 'pos [X,Y]'])
        # filter out only available buttons
        if available:
            icon_df = icon_df[icon_df['available'] == True].reset_index(drop=True)
        return icon_df

    # Scan battle grid, update OCR images
    def scan_grid(self, new=False):
        boxes, box_size = get_grid()
        # should be enabled by default
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
        unit_chosen = merge_df['grid_pos'].tolist()
        # Send Merge
        self.swipe(*unit_chosen)
        time.sleep(0.2)
        return merge_df

    # Merge special units ['harlequin.png','dryad.png','mime.png','scrapper.png']
    # Add logging event
    def merge_special_unit(self, df_split, merge_series, special_type):
        # Get special merge unit
        special_unit, normal_unit = [
            adv_filter_keys(merge_series, units=special_type, remove=remove) for remove in [False, True]
        ]  # scrapper support not tested
        # Get corresponding dataframes
        special_df, normal_df = [df_split.get_group(unit.index[0]).sample() for unit in [special_unit, normal_unit]]
        merge_df = pd.concat([special_df, normal_df])
        self.log_merge(merge_df)
        # Merge 'em
        unit_chosen = merge_df['grid_pos'].tolist()
        self.swipe(*unit_chosen)
        time.sleep(0.2)
        return merge_df

    def log_merge(self, merge_df):
        merge_df['unit'] = merge_df['unit'].apply(lambda x: x.replace('.png', ''))
        unit1, unit2 = merge_df.iloc[0:2]['unit']
        rank = merge_df.iloc[0]['rank']
        log_msg = f"Rank {rank} {unit1}-> {unit2}"
        # Determine log level from rank
        if rank > 4:
            self.logger.error(log_msg)
        elif rank > 2:
            self.logger.debug(log_msg)
        else:
            self.logger.info(log_msg)

    # Find targets for special merge
    def special_merge(self, df_split, merge_series, target='zealot.png'):
        merge_df = None
        # Try to rank up dryads
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

    # Harley Merge target
    def harley_merge(self, df_split, merge_series, target='knight_statue.png'):
        merge_df = None
        # Try to copy target
        hq_series = adv_filter_keys(merge_series, units='harlequin.png')
        if not hq_series.empty:
            hq_rank = hq_series.index.get_level_values('rank')
            for rank in hq_rank:
                merge_series_target = adv_filter_keys(merge_series, units=['harlequin.png', target], ranks=rank)
                if len(merge_series_target.index) == 2:
                    merge_df = self.merge_special_unit(df_split, merge_series_target, special_type='harlequin.png')
                    break
        return merge_df

    # Try to find a merge target and merge it
    def try_merge(self, rank=1, prev_grid=None, merge_target='zealot.png'):
        info = ''
        merge_df = None
        names = self.scan_grid(new=False)
        grid_df = bot_perception.grid_status(names, prev_grid=prev_grid)
        df_split, unit_series, df_groups, group_keys = grid_meta_info(grid_df)
        # Select stuff to merge
        merge_series = unit_series.copy()
        # Remove empty groups
        merge_series = adv_filter_keys(merge_series, units='empty.png', remove=True)
        # Do special merge with dryad/Harley
        self.special_merge(df_split, merge_series, merge_target)
        # Use harely on high dps targets
        if merge_target == 'demon_hunter.png':
            self.harley_merge(df_split, merge_series, target=merge_target)
            # Remove all demons (for co-op)
            demons = adv_filter_keys(merge_series, units='demon_hunter.png')
            num_demon = sum(demons)
            if num_demon >= 11:
                # If board is mostly demons, chill out
                self.logger.info(f'Board is full of demons, waiting...')
                time.sleep(10)
            if self.config.getboolean('bot', 'require_shaman'):
                merge_series = adv_filter_keys(merge_series, units='demon_hunter.png', remove=True)
        merge_series = preserve_unit(merge_series, target='chemist.png')
        # Remove 4x cauldrons
        for _ in range(4):
            merge_series = preserve_unit(merge_series, target='cauldron.png', keep_min=True)
        # Try to keep knight_statue numbers even (can conflict if special_merge already merged)
        num_knight = sum(adv_filter_keys(merge_series, units='knight_statue.png'))
        if num_knight % 2 == 1:
            self.harley_merge(df_split, merge_series, target='knight_statue.png')
        # Preserve 2 highest knight statues
        for _ in range(2):
            merge_series = preserve_unit(merge_series, target='knight_statue.png')
        # Select stuff to merge
        merge_series = merge_series[merge_series >= 2]  # At least 2 units
        merge_series = adv_filter_keys(merge_series, ranks=7, remove=True)  # Remove max ranks
        # Try to merge high priority units
        merge_prio = adv_filter_keys(merge_series,
                                     units=['chemist.png', 'bombardier.png', 'summoner.png', 'knight_statue.png'])
        if not merge_prio.empty:
            info = 'Merging High Priority!'
            merge_df = self.merge_unit(df_split, merge_prio)
        # Merge if board is getting full
        if df_groups['empty.png'] <= 2:
            info = 'Merging!'
            # Add criteria
            low_series = adv_filter_keys(merge_series, ranks=rank, remove=False)
            if not low_series.empty:
                merge_df = self.merge_unit(df_split, low_series)
            else:
                # If grid seems full, merge more units
                info = 'Merging high level!'
                merge_series = adv_filter_keys(merge_series,
                                               ranks=[3, 4, 5, 6, 7],
                                               units=['zealot.png', 'crystal.png', 'bruser.png', merge_target],
                                               remove=True)
                if not merge_series.empty:
                    merge_df = self.merge_unit(df_split, merge_series)
        else:
            info = 'need more units!'
        return grid_df, unit_series, merge_series, merge_df, info

    # Mana level cards
    def mana_level(self, cards, hero_power=False):
        upgrade_pos_dict = {1: [100, 1500], 2: [200, 1500], 3: [350, 1500], 4: [500, 1500], 5: [650, 1500]}
        # Level each card
        for card in cards:
            self.click(*upgrade_pos_dict[card])
        if hero_power:
            self.click(800, 1500)

    # Start a dungeon floor from PvE page
    def play_dungeon(self, floor=5):
        self.logger.info(f'Starting Dungeon floor {floor}')
        # Divide by 3 and take ceiling of floor as int
        chapter_num = int(np.ceil((floor)/3))
        target_chapter = f'chapter_{chapter_num}.png'
        next_chapter = f'chapter_{int(np.ceil((floor+1)/3))}.png'
        self.logger.info(f'Looking for target chapter: {target_chapter} (chapter {chapter_num}), next chapter: {next_chapter}')
        pos = np.array([0, 0])
        
        # Try to use IconDetector with OCR if available
        icon_detector = None
        if ICON_DETECTOR_AVAILABLE:
            try:
                icon_detector = IconDetector()
                self.logger.info('Using IconDetector with OCR fallback')
            except Exception as e:
                self.logger.warning(f'IconDetector init failed: {e}')
        
        # Get initial screen state with retry
        for retry in range(3):
            avail_buttons = self.get_current_icons(available=True)
            if not avail_buttons.empty:
                break
            self.logger.warning(f'Empty icon list, retry {retry+1}/3')
            time.sleep(1)
        
        self.logger.info(f'Available buttons: {list(avail_buttons["icon"]) if not avail_buttons.empty else "NONE"}')
        
        # Use helper to check if on dungeon page
        on_dungeon_page = self._is_on_dungeon_page(avail_buttons)
        
        if on_dungeon_page:
            self.logger.info('Detected dungeon page, swiping to top...')
            # Swipe to the top with small delays for stability
            for _ in range(14):
                self.swipe([0, 0], [2, 0])
                time.sleep(0.1)  # Small delay between swipes for stability
            self.click(30, 600, 5)  # stop scroll and scan screen for buttons
            time.sleep(0.5)  # Extra wait for screen to stabilize
            
            # Keep swiping until floor is found
            expanded = 0
            for i in range(10):
                # Scan screen for buttons
                avail_buttons = self.get_current_icons(available=True)
                available_chapters = [icon for icon in avail_buttons['icon'] if 'chapter_' in icon]
                self.logger.debug(f'Iteration {i}: Available chapters: {available_chapters}')
                
                # Try OCR-based detection if template matching fails
                chapter_found = (avail_buttons['icon'] == target_chapter).any()
                
                if not chapter_found and icon_detector is not None:
                    # Try OCR detection for chapter number
                    self.logger.debug(f'Template not found, trying OCR for chapter {chapter_num}')
                    try:
                        ocr_result = icon_detector.detect_chapter_number(
                            self.screenRGB, 
                            target_chapter=chapter_num
                        )
                        if ocr_result.found:
                            self.logger.info(f'Found chapter {chapter_num} via OCR at {ocr_result.position}')
                            pos = np.array(ocr_result.position)
                            chapter_found = True
                    except Exception as e:
                        self.logger.debug(f'OCR detection failed: {e}')
                
                # Look for correct chapter via template
                if chapter_found and not (pos != np.array([0, 0])).any():
                    if (avail_buttons['icon'] == target_chapter).any():
                        pos = get_button_pos(avail_buttons, target_chapter)
                    self.logger.info(f'Found target chapter {target_chapter} at position {pos}')
                    if not expanded:
                        expanded = 1
                        self.click_button(pos + [500, 90])
                    # check button is near top of screen
                    if pos[1] < 550 and floor % 3 != 0:
                        # Stop scrolling when chapter is near top
                        break
                elif (avail_buttons['icon'] == target_chapter).any():
                    pos = get_button_pos(avail_buttons, target_chapter)
                    self.logger.info(f'Found target chapter {target_chapter} at position {pos}')
                    if not expanded:
                        expanded = 1
                        self.click_button(pos + [500, 90])
                    # check button is near top of screen
                    if pos[1] < 550 and floor % 3 != 0:
                        # Stop scrolling when chapter is near top
                        break
                elif (avail_buttons['icon'] == next_chapter).any() and floor % 3 == 0:
                    pos = get_button_pos(avail_buttons, next_chapter)
                    self.logger.info(f'Found next chapter {next_chapter} at position {pos}')
                    # Stop scrolling if the next chapter is found and last floor of chapter is chosen
                    break
                # Contiue to swiping to find correct chapter
                [self.swipe([2, 0], [0, 0]) for i in range(2)]
                self.click(30, 600)  # stop scroll

            # Click play floor if found
            if not (pos == np.array([0, 0])).any():
                self.logger.info(f'Clicking floor {floor} for chapter at position {pos}')
                if floor % 3 == 0:
                    self.click_button(pos + [30, -460])
                elif floor % 3 == 1:
                    self.click_button(pos + [30, 485])
                elif floor % 3 == 2:
                    self.click_button(pos + [30, 885])
                self.click_button((500, 600))
                for i in range(10):
                    time.sleep(2)
                    avail_buttons = self.get_current_icons(available=True)
                    # Look for correct chapter
                    self.logger.info(f'Waiting for match to start {i}')
                    if avail_buttons['icon'].isin(['back_button.png', 'fighting.png']).any():
                        break
            else:
                self.logger.error(f'Could not find chapter for floor {floor}. Target: {target_chapter}, Next: {next_chapter}')
        else:
            self.logger.error(f'Not on dungeon page! Detected icons: {list(avail_buttons["icon"]) if not avail_buttons.empty else "NONE"}')
            self.logger.info('Make sure you are on the PvE/Dungeon selection screen')

    def _is_on_dungeon_page(self, df):
        """Check if currently on dungeon page using multiple detection methods."""
        if df.empty:
            return False
        # Direct detection
        if (df['icon'] == 'dungeon_page.png').any():
            return True
        # Fallback: any chapter icon visible
        if any('chapter_' in icon for icon in df['icon']):
            return True
        return False
    
    def check_template_coverage(self, save_visualization: bool = True) -> Optional[Dict]:
        """
        Check if current screen has unrecognized UI elements.
        
        Returns coverage report dict with:
        - coverage_percent: Percentage of UI elements matched
        - unmatched_count: Number of unrecognized elements
        - suggestions: List of suggested actions
        - needs_update: True if templates likely need updating
        """
        if not COVERAGE_ANALYZER_AVAILABLE:
            self.logger.debug('Coverage analyzer not available')
            return None
        
        if self.screenRGB is None:
            self.getScreen()
        
        if self.screenRGB is None:
            return None
        
        try:
            analyzer = TemplateCoverageAnalyzer()
            screenshot = cv2.cvtColor(self.screenRGB, cv2.COLOR_RGB2BGR)
            report = analyzer.analyze(screenshot)
            
            # Log warnings if coverage is low
            if report.coverage_percent < 50:
                self.logger.warning(f'Low template coverage: {report.coverage_percent:.1f}%')
                self.logger.warning(f'Unrecognized UI elements: {report.unmatched_elements}')
                for suggestion in report.suggestions:
                    self.logger.info(f'Suggestion: {suggestion}')
            
            # Save visualization if requested
            if save_visualization and report.unmatched_elements > 0:
                vis = analyzer.visualize_coverage(screenshot, report)
                saved = _save_debug_screenshot(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB), "coverage")
                if saved:
                    self.logger.info(f'Saved coverage visualization: {saved}')
            
            return {
                'coverage_percent': report.coverage_percent,
                'matched_count': report.matched_elements,
                'unmatched_count': report.unmatched_elements,
                'weak_count': report.weak_matches,
                'suggestions': report.suggestions,
                'needs_update': report.coverage_percent < 60 or report.unmatched_elements > 5,
                'weak_templates': [e.matched_template for e in report.weak if e.matched_template]
            }
        except Exception as e:
            self.logger.debug(f'Coverage check failed: {e}')
            return None
    
    def detect_unknown_screen(self) -> Tuple[bool, List[str]]:
        """
        Detect if we're on an unknown/uncovered screen.
        
        Returns:
            (is_unknown, suggestions): Tuple of detection result and suggested actions
        """
        df = self.get_current_icons(available=True)
        detected = list(df['icon']) if not df.empty else []
        
        # Known screen patterns
        known_patterns = {
            'home': ['home_screen.png', 'battle_icon.png'],
            'dungeon': ['dungeon_page.png', 'chapter_'],
            'battle': ['fighting.png'],
            'menu': ['back_button.png', '0cont_button.png', '1quit.png'],
            'store': ['refresh_button.png', 'store_refresh.png'],
        }
        
        # Check if we match any known pattern
        matched_screen = None
        for screen_name, patterns in known_patterns.items():
            for pattern in patterns:
                if any(pattern in icon for icon in detected):
                    matched_screen = screen_name
                    break
            if matched_screen:
                break
        
        if matched_screen:
            return False, [f'Detected screen: {matched_screen}']
        
        # Unknown screen - generate suggestions
        suggestions = []
        
        if not detected:
            suggestions.append('No icons detected - templates may be outdated')
            suggestions.append('Run: python scripts/template_coverage.py')
        else:
            suggestions.append(f'Unknown screen with icons: {detected}')
            suggestions.append('Consider capturing new templates for this screen')
        
        # Check coverage if analyzer available
        coverage = self.check_template_coverage(save_visualization=True)
        if coverage and coverage['needs_update']:
            suggestions.append(f"Template coverage: {coverage['coverage_percent']:.1f}%")
            suggestions.extend(coverage['suggestions'])
        
        return True, suggestions

    def _navigate_to_dungeon(self, max_attempts=5):
        """Navigate from home screen to dungeon page with retries.
        
        Nutzt primär den Hybrid-Navigator (feste Positionen + Farberkennung),
        fällt auf Template-Matching zurück wenn nicht verfügbar.
        """
        # Versuche zuerst Hybrid-Navigator (zuverlässiger, unabhängig von Templates)
        if self.hybrid_nav is not None:
            self.logger.info('Nutze Hybrid-Navigator für Dungeon-Navigation...')
            try:
                result = self.hybrid_nav.navigate_to_dungeon(max_attempts=max_attempts)
                if result.success:
                    self.logger.info(f'Hybrid-Navigation erfolgreich via {result.method_used}')
                    return True
                else:
                    self.logger.warning(f'Hybrid-Navigation fehlgeschlagen: {result.message}')
                    # Fallback auf alte Methode
            except Exception as e:
                self.logger.warning(f'Hybrid-Navigator Fehler: {e}, nutze Fallback')
        
        # Fallback: Klassische Template-basierte Navigation
        self.logger.info('Nutze klassische Template-Navigation...')
        for attempt in range(max_attempts):
            self.logger.info(f'Navigation attempt {attempt + 1}/{max_attempts}')
            
            # Take fresh screenshot and scan
            df = self.get_current_icons(available=True)
            detected = list(df['icon']) if not df.empty else []
            self.logger.info(f'Detected icons: {detected}')
            
            # Save debug screenshot
            if hasattr(self, 'screenRGB') and self.screenRGB is not None:
                saved = _save_debug_screenshot(self.screenRGB, f"nav_attempt_{attempt+1}")
                if saved:
                    self.logger.debug(f'Saved debug screenshot: {saved}')
            
            # Already on dungeon page?
            if self._is_on_dungeon_page(df):
                self.logger.info('Successfully on dungeon page!')
                return True
            
            # Try pve_button.png if visible
            if not df.empty and (df['icon'] == 'pve_button.png').any():
                pos = get_button_pos(df, 'pve_button.png')
                self.logger.info(f'Clicking PvE button at {pos}')
                self.click_button(pos)
                time.sleep(2)
                continue
            
            # On home screen? Click PvE area (right side of bottom bar)
            if not df.empty and ((df['icon'] == 'home_screen.png').any() or (df['icon'] == 'battle_icon.png').any()):
                # Try clicking PvE button position (right side)
                pve_positions = [
                    np.array([640, 1259]),  # Original position
                    np.array([1100, 1250]), # Far right
                    np.array([800, 1250]),  # Center-right
                ]
                for pos in pve_positions:
                    self.logger.info(f'Clicking PvE area at {pos}')
                    self.click_button(pos)
                    time.sleep(2)
                    
                    # Check if we navigated
                    df_check = self.get_current_icons(available=True)
                    if self._is_on_dungeon_page(df_check):
                        self.logger.info('Found dungeon page after click!')
                        return True
                continue
            
            # Unknown screen - try back button
            if not df.empty and (df['icon'] == 'back_button.png').any():
                pos = get_button_pos(df, 'back_button.png')
                self.click_button(pos)
                time.sleep(1)
                continue
            
            # Check if this is an unknown/uncovered screen
            is_unknown, suggestions = self.detect_unknown_screen()
            if is_unknown:
                self.logger.warning('On unknown screen - templates may need updating')
                for s in suggestions[:3]:  # Limit log spam
                    self.logger.info(f'  → {s}')
            
            # Really lost - send back key
            self.key_input(const.KEYCODE_BACK)
            time.sleep(1)
        
        self.logger.error(f'Failed to navigate to dungeon page after {max_attempts} attempts')
        return False

    # =========================================================================
    # TEMPLATE-FREE SCREEN DETECTION
    # =========================================================================
    
    def detect_screen_template_free(self) -> Tuple[str, float]:
        """
        Erkennt den aktuellen Screen OHNE Templates.
        
        Nutzt Farberkennung an festen Positionen.
        
        Returns:
            Tuple von (screen_name, confidence)
        """
        if not self.template_free_detector:
            return 'unknown', 0.0
        
        self.getScreen()
        if self.screenRGB is None:
            return 'unknown', 0.0
        
        screen, confidence = self.template_free_detector.detect_screen(self.screenRGB)
        return screen.name.lower(), confidence
    
    def battle_screen_template_free(self, start=False, pve=True, floor=5):
        """
        Template-freie Version von battle_screen().
        
        Erkennt Screens via Farbe/Position statt Templates.
        """
        self.getScreen()
        
        if not self.template_free_detector:
            # Fallback auf Template-basiert
            return self.battle_screen_legacy(start, pve, floor)
        
        screen, confidence = self.template_free_detector.detect_screen(self.screenRGB)
        self.logger.debug(f'Template-free detection: {screen.name} ({confidence:.2f})')
        
        # Leeres DataFrame für Kompatibilität
        df = pd.DataFrame(columns=['icon', 'available', 'pos [X,Y]'])
        
        # Screen-spezifische Aktionen
        if screen == GameScreen.BATTLE_ACTIVE:
            battle_state, _ = self.template_free_detector.detect_battle_state(self.screenRGB)
            if battle_state == BattleState.FIGHTING:
                return df, 'fighting'
            elif battle_state == BattleState.VICTORY:
                return df, 'victory'
            elif battle_state == BattleState.DEFEAT:
                return df, 'defeat'
            return df, 'battle'
        
        elif screen == GameScreen.BATTLE_VICTORY:
            # Klicke Continue an fester Position
            if SCREEN_POSITIONS_AVAILABLE:
                self.click_button(BattleScreen.CONTINUE_BUTTON.to_array())
            else:
                self.click_button(np.array([400, 1100]))
            return df, 'victory'
        
        elif screen == GameScreen.BATTLE_DEFEAT:
            # Klicke Quit an fester Position
            if SCREEN_POSITIONS_AVAILABLE:
                self.click_button(BattleScreen.QUIT_BUTTON.to_array())
            else:
                self.click_button(np.array([400, 1200]))
            return df, 'defeat'
        
        elif screen == GameScreen.HOME:
            if pve and start:
                self.logger.info('Auf Home Screen, navigiere zu PvE...')
                # Klicke PvE an fester Position
                if SCREEN_POSITIONS_AVAILABLE:
                    self.click_button(HomeScreen.PVE_BUTTON.to_array())
                else:
                    self.click_button(np.array([640, 1259]))
                time.sleep(2)
                
                # Prüfe ob Dungeon erreicht
                screen2, _ = self.template_free_detector.detect_screen(self.screenRGB)
                if screen2 == GameScreen.DUNGEON_SELECT:
                    self.play_dungeon(floor=floor)
            elif start:
                # PvP
                if SCREEN_POSITIONS_AVAILABLE:
                    self.click_button(HomeScreen.PVP_BUTTON.to_array())
                else:
                    self.click_button(np.array([140, 1259]))
            return df, 'home'
        
        elif screen == GameScreen.DUNGEON_SELECT:
            if pve and start:
                self.logger.info('Auf Dungeon-Seite, starte Dungeon...')
                self.play_dungeon(floor=floor)
            return df, 'dungeon'
        
        elif screen == GameScreen.STORE:
            return df, 'store'
        
        elif screen == GameScreen.FRIEND_MENU:
            # Schließen
            self.click_button(np.array([100, 600]))
            return df, 'friend_menu'
        
        elif screen == GameScreen.POPUP_DIALOG:
            # Dialog schließen
            if SCREEN_POSITIONS_AVAILABLE:
                self.click_button(GenericButtons.CLOSE_BUTTON.to_array())
            else:
                self.click_button(np.array([750, 200]))
            return df, 'popup'
        
        elif screen == GameScreen.LOADING:
            time.sleep(2)  # Warten
            return df, 'loading'
        
        else:
            # Unbekannt - Back-Taste
            self.key_input(const.KEYCODE_BACK)
            return df, 'lost'

    # Locate game home screen and try to start fight is chosen
    def battle_screen(self, start=False, pve=True, floor=5):
        """
        Hauptmethode zur Screen-Erkennung.
        
        Nutzt je nach detection_mode:
        - 'template_free': Farberkennung (KEINE Templates)
        - 'hybrid': Feste Positionen + Farben + Template-Fallback
        - 'legacy': Klassisches Template-Matching
        """
        # Template-freier Modus (bevorzugt)
        if self.detection_mode == 'template_free' and self.template_free_detector:
            return self.battle_screen_template_free(start, pve, floor)
        
        # Legacy/Hybrid Modus
        return self.battle_screen_legacy(start, pve, floor)
    
    def battle_screen_legacy(self, start=False, pve=True, floor=5):
        """Original Template-basierte battle_screen() Funktion."""
        # Scan screen for any key buttons
        df = self.get_current_icons(available=True)
        if not df.empty:
            # list of buttons
            if (df['icon'] == 'fighting.png').any() and not (df['icon'] == '0cont_button.png').any():
                return df, 'fighting'
            if (df['icon'] == 'friend_menu.png').any():
                self.click_button(np.array([100, 600]))
                return df, 'friend_menu'
            # Check if already on dungeon page
            if self._is_on_dungeon_page(df):
                if pve and start:
                    self.logger.info('Already on dungeon page, starting dungeon selection')
                    self.play_dungeon(floor=floor)
                return df, 'dungeon'
            # Start pvp or pve from homescreen
            if (df['icon'] == 'home_screen.png').any() or (df['icon'] == 'battle_icon.png').any():
                if pve and start:
                    self.logger.info('On home screen, navigating to PvE...')
                    if self._navigate_to_dungeon():
                        self.play_dungeon(floor=floor)
                    else:
                        self.logger.error('Could not navigate to dungeon, aborting')
                elif start:
                    # PvP mode
                    self.click_button(np.array([140, 1259]))
                time.sleep(1)
                return df, 'home'
            # Check first button is clickable
            df_click = df[df['icon'].isin(['back_button.png', 'battle_icon.png', '0cont_button.png', '1quit.png'])]
            if not df_click.empty:
                button_pos = df_click['pos [X,Y]'].tolist()[0]
                self.click_button(button_pos)
                return df, 'menu'
        
        # Check if we're on an unknown screen
        is_unknown, suggestions = self.detect_unknown_screen()
        if is_unknown:
            self.logger.warning('Unknown screen detected - templates may need updating')
            for s in suggestions[:2]:
                self.logger.info(f'  → {s}')
        
        self.key_input(const.KEYCODE_BACK)  # Force back
        return df, 'lost'

    # Navigate and locate store refresh button from battle screen
    def find_store_refresh(self):
        self.click_button((100, 1500))  # Click store button
        [self.swipe([0, 0], [2, 0]) for i in range(5)]  # swipe to top
        self.click(30, 150)  # stop scroll
        avail_buttons = self.get_current_icons(available=True)
        if (avail_buttons['icon'] == 'refresh_button.png').any():
            pos = get_button_pos(avail_buttons, 'refresh_button.png')
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
            self.logger.warning('Bought store units!')
            # Try to refresh shop (watch ad)
            self.click_button(pos)

    def watch_ads(self):
        avail_buttons = self.get_current_icons(available=True)
        # Watch ad if available
        if (avail_buttons['icon'] == 'quest_done.png').any():
            pos = get_button_pos(avail_buttons, 'quest_done.png')
            self.click_button(pos)
            self.click(700, 600)  # collect second completed quest
            self.click(700, 400)  # collect second completed quest
            [self.click(150, 250) for i in range(2)]  # click dailies twice
            self.click(420, 420)  # collect ad chest
        elif (avail_buttons['icon'] == 'ad_season.png').any():
            pos = get_button_pos(avail_buttons, 'ad_season.png')
            self.click_button(pos)
        elif (avail_buttons['icon'] == 'ad_pve.png').any():
            pos = get_button_pos(avail_buttons, 'ad_pve.png')
            self.click_button(pos)
        elif (avail_buttons['icon'] == 'battle_icon.png').any():
            self.refresh_shop()
        else:
            #self.logger.info('Watched all ads!')
            return
        # Check if ad was started
        avail_buttons, status = self.battle_screen()
        if status == 'menu' or status == 'home' or (avail_buttons['icon'] == 'refresh_button.png').any():
            self.logger.info('FINISHED AD')
        # Watch ad
        else:
            time.sleep(30)
            # Keep watching until back in menu
            for i in range(10):
                avail_buttons, status = self.battle_screen()
                if status == 'menu' or status == 'home':
                    self.logger.info('FINISHED AD')
                    return  # Exit function
                time.sleep(2)
                self.click(870, 30)  # skip forward/click X
                self.click(870, 100)  # click X playstore popup
                if i > 5:
                    self.key_input(const.KEYCODE_BACK)  # Force back
                self.logger.info(f'AD TIME {i} {status}')
            # Restart game if can't escape ad
            self.restart_RR()


####
#### END OF CLASS
####


# Get fight grid pixel values
def get_grid():
    #Grid dimensions
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
    if not 'empty.png' in df_groups:
        df_groups['empty.png'] = 0
    unit_list = list(df_groups.index)
    return df_split, df_groups, unit_list


# Removes 1x of the highest rank unit from the merge_series
def preserve_unit(unit_series, target='chemist.png', keep_min=False):
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
        merge_series[merge_series.index == preserve_unit] = merge_series[merge_series.index == preserve_unit] - 1
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
    grid_df = grid_df[grid_df['Age'] >= min_age].reset_index(drop=True)
    df_split = grid_df.groupby(['unit', 'rank'])
    # Count number of unit of each rank
    unit_series = df_split['unit'].count()
    #unit_series = unit_series.sort_values(ascending=False)
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
            exists = merge_series.index.get_level_values('rank').isin([token]).any()
            if exists:
                series.append(merge_series.xs(token, level='rank', drop_level=False))
            else:
                continue  # skip if nothing matches criteria
        elif isinstance(token, str):
            if token in merge_series:
                series.append(merge_series.xs(token, level='unit', drop_level=False))
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
    if not units is None:
        filtered_units = filter_units(unit_series, units)
    else:
        filtered_units = unit_series.copy()
    # if all units are filtered already, return empty series
    if not ranks is None and not filtered_units.empty:
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
    #button=button+'.png'
    pos = df[df['icon'] == button]['pos [X,Y]'].reset_index(drop=True)[0]
    return np.array(pos)
