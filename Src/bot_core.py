"""
Rush Royale Bot Core - Python 3.13 Compatible
Enhanced error handling and modern Python features with auto-scrcpy management
"""
from __future__ import annotations

import os
import time
import logging
import subprocess
import shutil
from subprocess import Popen, DEVNULL, PIPE
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

# Third-party imports
import numpy as np
import pandas as pd
import cv2

# Import our future-proof scrcpy manager
try:
    from .future_proof_scrcpy import ScrcpyManager, FutureProofScrcpy, ModernScreenCapture
    FUTURE_SCRCPY_AVAILABLE = True
except ImportError:
    try:
        from future_proof_scrcpy import ScrcpyManager, FutureProofScrcpy, ModernScreenCapture
        FUTURE_SCRCPY_AVAILABLE = True
    except ImportError:
        FUTURE_SCRCPY_AVAILABLE = False
        # Create fallback classes
        class ScrcpyManager:
            def __init__(self, logger=None):
                self.logger = logger
                self.scrcpy_path = None
            def is_available(self):
                return False
            def get_version(self):
                return None
        
        class FutureProofScrcpy:
            def __init__(self, manager, logger):
                pass
        
        class ModernScreenCapture:
            def __init__(self, device, logger):
                pass
            def via_adb_sync(self, path):
                return False

# Android ADB imports
from ppadb.client import Client as AdbClient
from ppadb.device import Device

# Try to import scrcpy for enhanced screenshot capability
try:
    import scrcpy
    SCRCPY_AVAILABLE = True
except ImportError:
    SCRCPY_AVAILABLE = False

# Create constants for touch actions
class TouchConstants:
    ACTION_DOWN = 0
    ACTION_UP = 1
    KEYCODE_BACK = 4

const = TouchConstants()

# Internal imports
import bot_perception
import port_scan

SLEEP_DELAY = 0.1

# Python 3.13+ compatibility flags
PYTHON_313_FEATURES = hasattr(subprocess, 'CREATE_NO_WINDOW')
ASYNC_AVAILABLE = True  # asyncio is built-in since Python 3.4


class Bot:

    def __init__(self, device=None, logger=None):
        """
        Initialize bot core with robust ADB device connection and auto-scrcpy management
        Uses hybrid approach: modern ScrcpyManager with fallbacks
        """
        # Initialize bot state
        self.bot_stop = False
        self.combat = self.output = self.grid_df = self.unit_series = self.merge_series = self.df_groups = self.info = self.combat_step = None
        
        # Initialize configuration
        import configparser
        self.config = configparser.ConfigParser()
        try:
            self.config.read('config.ini')
        except:
            # Create default configuration if file doesn't exist
            self.config = self._create_default_config()
        
        # Setup logger
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(f'Bot_{device or "default"}')
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        
        # Device connection with error handling
        try:
            if device is None:
                device = port_scan.get_device()
            if not device:
                # Default device if none found
                device = "emulator-5554"
                self.logger.warning("No device found, using default emulator-5554")
            
            self.device = device
            self.bot_id = self.device.split(':')[-1]
            
            # Initialize ADB components
            self.adb_client = None
            self.adb_device = None
            self.scrcpy_process = None
            
            # Initialize modern ScrcpyManager with auto-download
            self.logger.info("🚀 Initializing ScrcpyManager with auto-download...")
            if FUTURE_SCRCPY_AVAILABLE:
                try:
                    self.scrcpy_manager = ScrcpyManager(logger=self.logger)
                    self.future_scrcpy = FutureProofScrcpy(self.scrcpy_manager, self.logger)
                    self.modern_capture = ModernScreenCapture(self.device, self.logger)
                    
                    # Log scrcpy status
                    if self.scrcpy_manager.is_available():
                        version = self.scrcpy_manager.get_version()
                        self.logger.info(f"✅ Scrcpy ready! Path: {self.scrcpy_manager.scrcpy_path}")
                        self.logger.info(f"📋 Version: {version or 'unknown'}")
                    else:
                        self.logger.warning("⚠️ Scrcpy auto-download failed, using fallback methods")
                        
                except Exception as init_error:
                    self.logger.warning(f"ScrcpyManager initialization failed: {init_error}")
                    self.scrcpy_manager = None
                    self.future_scrcpy = None
                    self.modern_capture = None
            else:
                self.logger.warning("Future-proof scrcpy not available, using legacy methods")
                self.scrcpy_manager = None
                self.future_scrcpy = None
                self.modern_capture = None
            
            # Legacy scrcpy executable for backwards compatibility
            self.scrcpy_executable = self.find_scrcpy_executable()
            
            # Try to establish connection
            self._initialize_connection()
            
            # Initialize screen capture
            self.screenRGB = None
            screenshot_path = f'bot_feed_{self.bot_id}.png'
            
            # Try to get initial screenshot
            if self.getScreen():
                self.screenRGB = cv2.imread(screenshot_path)
                if self.screenRGB is not None:
                    self.logger.info('Initial screenshot captured successfully')
                else:
                    self.logger.warning('Screenshot file exists but could not be loaded')
            else:
                self.logger.warning('Could not capture initial screenshot')
            
            self.logger.info(f'Bot initialized for device: {self.device}')
            
        except Exception as e:
            self.logger.error(f'Bot initialization failed: {e}')
            # Don't raise exception - allow bot to start in limited mode
            self.output = f"Initialization error: {e}"

    def _create_default_config(self):
        """Create default configuration if config.ini is missing"""
        import configparser
        config = configparser.ConfigParser()
        
        config['bot'] = {
            'floor': '7',
            'mana_level': '1,2,3,4,5',
            'units': 'demo, boreas, robot, dryad, franky_stein',
            'dps_unit': 'boreas',
            'pve': 'False',
            'require_shaman': 'False'
        }
        
        return config

    def _initialize_connection(self):
        """Initialize ADB connection with multiple fallback methods"""
        self.logger.info(f"Attempting connection to {self.device}")
        
        try:
            # Try pure-python-adb
            self._try_python_adb_connection()
            
            # Test shell ADB as fallback
            if not self.adb_device:
                self._test_shell_adb_connection()
                
        except Exception as e:
            self.logger.error(f"Connection initialization failed: {e}")
            self.output = f"Connection failed: {e}"

    def _try_python_adb_connection(self):
        """Try to connect using pure-python-adb"""
        try:
            self.adb_client = AdbClient()
            devices = self.adb_client.devices()
            
            # Look for our device
            for dev in devices:
                if dev.serial == self.device:
                    self.adb_device = dev
                    self.logger.info(f"Python ADB connected: {dev.serial}")
                    return True
            
            # Device not found, try to connect
            self.logger.info("Device not found, attempting ADB connect...")
            if '127.0.0.1:5555' in self.device or 'emulator' in self.device:
                connect_address = '127.0.0.1:5555' if 'emulator' in self.device else self.device
                self.shell(f'adb connect {connect_address}')
                time.sleep(2)
                
                # Check again
                devices = self.adb_client.devices()
                for dev in devices:
                    if dev.serial == self.device:
                        self.adb_device = dev
                        self.logger.info(f"Python ADB connected after connect: {dev.serial}")
                        return True
                        
        except Exception as e:
            self.logger.warning(f"Python ADB connection failed: {e}")
            
        return False

    def _test_shell_adb_connection(self):
        """Test shell ADB connection as fallback"""
        try:
            # Test if ADB is available in shell
            result = subprocess.run(['adb', 'devices'], 
                                   capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                self.logger.info("Shell ADB available as fallback")
                # Test basic command
                test_result = self.shell('echo test')
                if test_result == 'test':
                    self.logger.info("Shell ADB connection verified")
                    return True
                else:
                    self.logger.warning(f"Shell ADB test failed: expected 'test', got '{test_result}'")
            else:
                self.logger.warning(f"ADB devices command failed: {result.stderr}")
                
        except FileNotFoundError:
            self.logger.error("ADB not found in PATH")
        except subprocess.TimeoutExpired:
            self.logger.error("ADB command timeout")
        except Exception as e:
            self.logger.error(f"Shell ADB test failed: {e}")
            
        return False

    def is_connected(self):
        """Check if device connection is available"""
        if self.adb_device:
            try:
                # Test with simple command
                self.adb_device.shell('echo test')
                return True
            except:
                pass
        
        # Test shell ADB fallback
        try:
            result = self.shell('echo test')
            return result == 'test'
        except:
            return False

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
    def shell(self, cmd, timeout=10):
        """Execute shell command with improved error handling"""
        try:
            if self.adb_device:
                result = self.adb_device.shell(cmd)
                return result.strip() if result else ""
            else:
                # Fallback to system ADB with proper error handling
                full_cmd = ['adb', '-s', self.device, 'shell', cmd]
                result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
                
                if result.returncode != 0 and result.stderr:
                    self.logger.warning(f"Shell command warning: {result.stderr}")
                
                return result.stdout.strip() if result.stdout else ""
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Shell command timeout: {cmd}")
            return ""
        except Exception as e:
            self.logger.error(f"Shell command error: {e}")
            return ""

    # Send ADB to click screen
    def click(self, x, y, delay_mult=1):
        """Click with error handling and fallback"""
        try:
            if self.adb_device:
                self.adb_device.input_tap(x, y)
                self.logger.debug(f"Click via ADB: ({x}, {y})")
            else:
                # Fallback to shell command
                self.shell(f'input tap {x} {y}')
                self.logger.debug(f"Click via shell: ({x}, {y})")
            
            time.sleep(SLEEP_DELAY * delay_mult)
            
        except Exception as e:
            self.logger.error(f"Click failed at ({x}, {y}): {e}")
            # Try shell fallback if ADB failed
            try:
                self.shell(f'input tap {x} {y}')
                time.sleep(SLEEP_DELAY * delay_mult)
            except Exception as e2:
                self.logger.error(f"Shell click fallback also failed: {e2}")

    def click_button(self, pos, delay_mult=10):
        """Click button coords with offset and extra delay"""
        try:
            if pos is not None and len(pos) >= 2:
                coords = np.array(pos) + 10
                self.click(coords[0], coords[1])
                time.sleep(SLEEP_DELAY * delay_mult)
            else:
                self.logger.warning("Invalid button position provided")
                
        except Exception as e:
            self.logger.error(f"Button click failed: {e}")

    def swipe(self, start, end, duration=300):
        """Swipe on combat grid to merge units"""
        try:
            boxes, box_size = get_grid()
            # Offset from box edge
            offset = 60
            start_pos = boxes[start[0], start[1]] + offset
            end_pos = boxes[end[0], end[1]] + offset
            
            if self.adb_device:
                self.adb_device.input_swipe(start_pos[0], start_pos[1], end_pos[0], end_pos[1], duration)
                self.logger.debug(f"Swipe via ADB: {start} -> {end}")
            else:
                # Fallback to shell command
                self.shell(f'input swipe {start_pos[0]} {start_pos[1]} {end_pos[0]} {end_pos[1]} {duration}')
                self.logger.debug(f"Swipe via shell: {start} -> {end}")
                
            time.sleep(SLEEP_DELAY)
            
        except Exception as e:
            self.logger.error(f"Swipe failed {start} -> {end}: {e}")

    def key_input(self, key):
        """Send key command with error handling"""
        try:
            if self.adb_device:
                self.adb_device.input_keyevent(key)
                self.logger.debug(f"Key input via ADB: {key}")
            else:
                self.shell(f'input keyevent {key}')
                self.logger.debug(f"Key input via shell: {key}")
                
            time.sleep(SLEEP_DELAY)
            
        except Exception as e:
            self.logger.error(f"Key input failed ({key}): {e}")
            # Try shell fallback
            try:
                self.shell(f'input keyevent {key}')
                time.sleep(SLEEP_DELAY)
            except Exception as e2:
                self.logger.error(f"Shell key input fallback also failed: {e2}")

    def restart_RR(self, quick_disconnect=False):
        """Force restart the game through ADB, or spam disconnects to abandon match"""
        try:
            if quick_disconnect:
                self.logger.info("Attempting quick disconnect...")
                for i in range(15):
                    if self.adb_device:
                        self.adb_device.shell('monkey -p com.my.defense 1')
                    else:
                        self.shell('monkey -p com.my.defense 1')
                    time.sleep(0.1)
            else:
                self.logger.info("Restarting Rush Royale...")
                # Force stop
                if self.adb_device:
                    self.adb_device.shell('am force-stop com.my.defense')
                else:
                    self.shell('am force-stop com.my.defense')
                    
                time.sleep(2)
                
                # Start app
                if self.adb_device:
                    self.adb_device.shell('monkey -p com.my.defense -c android.intent.category.LAUNCHER 1')
                else:
                    self.shell('monkey -p com.my.defense -c android.intent.category.LAUNCHER 1')
                    
                time.sleep(5)
                
        except Exception as e:
            self.logger.error(f"Restart failed: {e}")

    def getScreen(self):
        """Robust screenshot capture with modern ScrcpyManager and multiple fallback methods"""
        bot_id = self.device.split(':')[-1]
        screenshot_path = f'bot_feed_{bot_id}.png'
        
        try:
            # Method 1: Try modern ScrcpyManager capture first
            if (hasattr(self, 'modern_capture') and self.modern_capture is not None and 
                self.modern_capture.via_adb_sync(Path(screenshot_path))):
                self.logger.debug('✅ Screenshot taken via ScrcpyManager modern capture')
                return self._validate_and_load_screenshot(screenshot_path)
            
            # Method 2: Try pure-python-adb screencap (most reliable)
            elif self._try_adb_screenshot(screenshot_path):
                self.logger.debug('✅ Screenshot taken via pure-python-adb')
                return self._validate_and_load_screenshot(screenshot_path)
                
            # Method 3: Try shell ADB screencap (fallback)
            elif self._try_shell_screenshot(screenshot_path):
                self.logger.debug('✅ Screenshot taken via ADB shell')
                return self._validate_and_load_screenshot(screenshot_path)
                
            # Method 4: Try legacy scrcpy if available (backwards compatibility)
            elif self.scrcpy_executable and self._try_scrcpy_screenshot(screenshot_path):
                self.logger.debug('✅ Screenshot taken via legacy scrcpy')
                return self._validate_and_load_screenshot(screenshot_path)
            else:
                self.logger.error('❌ All screenshot methods failed!')
                return False
                
        except Exception as e:
            self.logger.error(f'Screenshot capture error: {e}')
            return False

    def _validate_and_load_screenshot(self, screenshot_path: str) -> bool:
        """Validate screenshot file and load into memory"""
        try:
            # Check file exists and has reasonable size
            if not os.path.exists(screenshot_path):
                self.logger.warning(f'Screenshot file not found: {screenshot_path}')
                return False
                
            file_size = os.path.getsize(screenshot_path)
            if file_size < 1000:  # Too small to be valid screenshot
                self.logger.warning(f'Screenshot file too small: {file_size} bytes')
                return False
            
            # Try to load with OpenCV
            new_img = cv2.imread(screenshot_path)
            if new_img is not None and new_img.shape[0] > 0 and new_img.shape[1] > 0:
                self.screenRGB = new_img
                self.logger.debug(f'Screenshot loaded successfully: {new_img.shape}')
                return True
            else:
                self.logger.warning(f'Invalid screenshot image data')
                return False
                
        except Exception as e:
            self.logger.error(f'Screenshot validation error: {e}')
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
                else:
                    self.logger.debug('ADB screencap returned empty/small data')
        except Exception as e:
            self.logger.debug(f'ADB screencap failed: {e}')
        return False

    def _try_shell_screenshot(self, output_path: str) -> bool:
        """Try taking screenshot using shell ADB command"""
        try:
            # Method 1: Direct exec-out (fastest)
            cmd = ['adb', '-s', self.device, 'exec-out', 'screencap', '-p']
            with open(output_path, 'wb') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=10)
                if result.returncode == 0:
                    return True
                    
            # Method 2: Traditional pull method (more compatible)
            self.logger.debug('Trying traditional ADB pull method')
            subprocess.run(['adb', '-s', self.device, 'shell', 'screencap', '-p', '/sdcard/screenshot.png'], 
                          timeout=5, check=False)
            time.sleep(0.5)
            
            result = subprocess.run(['adb', '-s', self.device, 'pull', '/sdcard/screenshot.png', output_path], 
                                   capture_output=True, timeout=10)
            
            if result.returncode == 0 and os.path.exists(output_path):
                return True
                
        except subprocess.TimeoutExpired:
            self.logger.warning('ADB shell screenshot timeout')
        except FileNotFoundError:
            self.logger.warning('ADB not found in PATH')
        except Exception as e:
            self.logger.debug(f'Shell screenshot failed: {e}')
            
        return False

    def _try_scrcpy_screenshot(self, output_path: str) -> bool:
        """Try taking screenshot using scrcpy (legacy support)"""
        if not self.scrcpy_executable:
            return False
        try:
            # Use ADB exec-out instead of scrcpy for screenshot
            cmd = ['adb', '-s', self.device, 'exec-out', 'screencap', '-p']
            with open(output_path, 'wb') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=10)
                return result.returncode == 0
        except Exception:
            return False

    # Crop latest screenshot taken
    def crop_img(self, x, y, dx, dy, name='icon.png'):
        """Crop latest screenshot taken"""
        if self.screenRGB is None:
            self.logger.warning("Cannot crop image: no screenshot available")
            return
            
        # Load screen
        img_rgb = self.screenRGB
        if img_rgb is not None:
            try:
                img_rgb = img_rgb[y:y + dy, x:x + dx]
                cv2.imwrite(name, img_rgb)
            except Exception as e:
                self.logger.error(f"Error cropping image: {e}")

    def getText(self, x, y, dx, dy, new=False, digits=False):
        """Get text from screen region (placeholder method)"""
        # This method seems to be missing from the original implementation
        # Returning a default value to fix the import error
        self.logger.warning("getText method not fully implemented")
        return "0"

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
        self.logger.debug(f'Screenshot shape: {img_gray.shape}')
        
        # Check every target in dir
        icon_count = 0
        for target in os.listdir("icons"):
            x = 0  # reset position
            y = 0
            # Load icon
            imgSrc = f'icons/{target}'
            template = cv2.imread(imgSrc, 0)
            if template is None:
                self.logger.debug(f'Could not load template: {imgSrc}')
                continue
                
            # Compare images
            res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
            threshold = 0.8
            max_val = res.max()
            loc = np.where(res >= threshold)
            icon_found = len(loc[0]) > 0
            
            # Debug for key icons
            if target in ['home_screen.png', 'battle_icon.png']:
                self.logger.debug(f'Icon {target}: max_val={max_val:.3f}, found={icon_found}')
            
            if icon_found:
                y = loc[0][0]
                x = loc[1][0]
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
            # Unpack box coordinates and size
            x, y = box_list[i]
            dx, dy = box_size
            self.crop_img(x, y, dx, dy, name=file_name)
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
        self.logger.debug(f'Starting Dungeon floor {floor}')
        # Divide by 3 and take ceiling of floor as int
        target_chapter = f'chapter_{int(np.ceil((floor)/3))}.png'
        next_chapter = f'chapter_{int(np.ceil((floor+1)/3))}.png'
        pos = np.array([0, 0])
        avail_buttons = self.get_current_icons(available=True)
        # Check if on dungeon page
        if (avail_buttons == 'dungeon_page.png').any(axis=None):
            # Swipe to the top
            [self.swipe([0, 0], [2, 0]) for i in range(14)]
            self.click(30, 600, 5)  # stop scroll and scan screen for buttons
            # Keep swiping until floor is found
            expanded = 0
            for i in range(10):
                # Scan screen for buttons
                avail_buttons = self.get_current_icons(available=True)
                # Look for correct chapter
                if (avail_buttons == target_chapter).any(axis=None):
                    pos = get_button_pos(avail_buttons, target_chapter)
                    if not expanded:
                        expanded = 1
                        self.click_button(pos + [500, 90])
                    # check button is near top of screen
                    if pos[1] < 550 and floor % 3 != 0:
                        # Stop scrolling when chapter is near top
                        break
                elif (avail_buttons == next_chapter).any(axis=None) and floor % 3 == 0:
                    pos = get_button_pos(avail_buttons, next_chapter)
                    # Stop scrolling if the next chapter is found and last floor of chapter is chosen
                    break
                # Contiue to swiping to find correct chapter
                [self.swipe([2, 0], [0, 0]) for i in range(2)]
                self.click(30, 600)  # stop scroll

            # Click play floor if found
            if not (pos == np.array([0, 0])).any():
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

    # Locate game home screen and try to start fight is chosen
    def battle_screen(self, start=False, pve=True, floor=5):
        # Scan screen for any key buttons
        df = self.get_current_icons(available=True)
        if not df.empty:
            # list of buttons
            if (df == 'fighting.png').any(axis=None) and not (df == '0cont_button.png').any(axis=None):
                return df, 'fighting'
            if (df == 'friend_menu.png').any(axis=None):
                self.click_button(np.array([100, 600]))
                return df, 'friend_menu'
            # Start pvp if homescreen
            if (df == 'home_screen.png').any(axis=None) and (df == 'battle_icon.png').any(axis=None):
                if pve and start:
                    # Add a 500 pixel offset for PvE button
                    self.click_button(np.array([640, 1259]))
                    self.play_dungeon(floor=floor)
                elif start:
                    self.click_button(np.array([140, 1259]))
                time.sleep(1)
                return df, 'home'
            # Check first button is clickable
            df_click = df[df['icon'].isin(['back_button.png', 'battle_icon.png', '0cont_button.png', '1quit.png'])]
            if not df_click.empty:
                button_pos = df_click['pos [X,Y]'].tolist()[0]
                self.click_button(button_pos)
                return df, 'menu'
        self.key_input(const.KEYCODE_BACK)  # Force back
        return df, 'lost'

    # Navigate and locate store refresh button from battle screen
    def find_store_refresh(self):
        self.click_button((100, 1500))  # Click store button
        [self.swipe([0, 0], [2, 0]) for i in range(5)]  # swipe to top
        self.click(30, 150)  # stop scroll
        avail_buttons = self.get_current_icons(available=True)
        if (avail_buttons == 'refresh_button.png').any(axis=None):
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
        if (avail_buttons == 'quest_done.png').any(axis=None):
            pos = get_button_pos(avail_buttons, 'quest_done.png')
            self.click_button(pos)
            self.click(700, 600)  # collect second completed quest
            self.click(700, 400)  # collect second completed quest
            [self.click(150, 250) for i in range(2)]  # click dailies twice
            self.click(420, 420)  # collect ad chest
        elif (avail_buttons == 'ad_season.png').any(axis=None):
            pos = get_button_pos(avail_buttons, 'ad_season.png')
            self.click_button(pos)
        elif (avail_buttons == 'ad_pve.png').any(axis=None):
            pos = get_button_pos(avail_buttons, 'ad_pve.png')
            self.click_button(pos)
        elif (avail_buttons == 'battle_icon.png').any(axis=None):
            self.refresh_shop()
        else:
            #self.logger.info('Watched all ads!')
            return
        # Check if ad was started
        avail_buttons, status = self.battle_screen()
        if status == 'menu' or status == 'home' or (avail_buttons == 'refresh_button.png').any(axis=None):
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
