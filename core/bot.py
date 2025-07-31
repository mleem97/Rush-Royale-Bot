#!/usr/bin/env python3
"""
Rush Royale Bot - Core Module
Main bot class with consolidated functionality from multiple source files
"""

import os
import time
import logging
import configparser
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

# Suppress harmless warnings
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

# Third-party imports
import numpy as np
import pandas as pd
import cv2
from scrcpy import Client, const

# Local imports - will be updated for new structure
from .device import DeviceManager
from .perception import PerceptionSystem
from .logger import BotLogger
from .config import ConfigManager

SLEEP_DELAY = 0.1


class RushRoyaleBot:
    """
    Main Rush Royale Bot class
    Consolidated from bot_core.py, bot_handler.py, and related modules
    """
    
    def __init__(self, device_id: Optional[str] = None, config_path: str = "config.ini"):
        """Initialize the bot with device and configuration"""
        self.bot_stop = False
        self.running = False
        
        # Initialize subsystems
        self.logger = BotLogger()
        self.config = ConfigManager(config_path)
        self.device_manager = DeviceManager(device_id)
        self.perception = PerceptionSystem()
        
        # Bot state
        self.combat = None
        self.output = None
        self.grid_df = None
        self.unit_series = None
        self.merge_series = None
        self.df_groups = None
        self.info = None
        self.combat_step = None
        
        # Initialize device connection
        self._initialize_device()
        
    def _initialize_device(self):
        """Initialize device connection and scrcpy client"""
        try:
            device = self.device_manager.get_device()
            if not device:
                raise RuntimeError("No device found!")
                
            self.device = device
            self.device_id = device.split(':')[-1]
            
            # Connect and launch game
            self.device_manager.connect(device)
            self.device_manager.launch_game()
            
            # Initialize scrcpy client
            self.client = Client(device=device)
            self.client.start(threaded=True)
            
            # Take initial screenshot
            if not os.path.isfile(f'bot_feed_{self.device_id}.png'):
                self.capture_screen()
                
            self.screen_rgb = cv2.imread(f'bot_feed_{self.device_id}.png')
            
            self.logger.info(f'Connected to device: {device}')
            time.sleep(0.5)
            
            # Turn off video stream to reduce overhead
            self.client.alive = False
            
        except Exception as e:
            self.logger.error(f"Failed to initialize device: {e}")
            raise
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager exit - cleanup resources"""
        self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown the bot"""
        self.bot_stop = True
        self.running = False
        
        try:
            if hasattr(self, 'client'):
                self.client.stop()
            self.logger.info('Bot shutdown complete')
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    # Device Control Methods
    def click(self, x: int, y: int, delay_mult: float = 1.0):
        """Click at screen coordinates"""
        self.client.control.touch(x, y, const.ACTION_DOWN)
        time.sleep(SLEEP_DELAY / 2 * delay_mult)
        self.client.control.touch(x, y, const.ACTION_UP)
        time.sleep(SLEEP_DELAY * delay_mult)
    
    def click_button(self, pos: Tuple[int, int]):
        """Click button with offset and extra delay"""
        coords = np.array(pos) + 10
        self.click(*coords)
        time.sleep(SLEEP_DELAY * 10)
    
    def swipe(self, start: Tuple[int, int], end: Tuple[int, int]):
        """Swipe between two points on the grid"""
        boxes, box_size = self._get_grid_coordinates()
        offset = 60
        start_pos = boxes[start[0], start[1]] + offset
        end_pos = boxes[end[0], end[1]] + offset
        
        self.client.control.swipe(*start_pos, *end_pos, 20, 1/60)
    
    def send_key(self, key):
        """Send key command to device"""
        self.client.control.keycode(key)
    
    def shell_command(self, cmd: str):
        """Execute ADB shell command"""
        self.device_manager.shell_command(cmd)
    
    # Screen Capture Methods
    def capture_screen(self) -> bool:
        """Capture screen and save to file"""
        try:
            # Use scrcpy to capture screen
            # Implementation will use device_manager
            return self.device_manager.capture_screen(f'bot_feed_{self.device_id}.png')
        except Exception as e:
            self.logger.error(f"Screen capture failed: {e}")
            return False
    
    def crop_image(self, x: int, y: int, width: int, height: int, filename: str = 'crop.png'):
        """Crop region from current screen"""
        if self.screen_rgb is None:
            self.capture_screen()
            self.screen_rgb = cv2.imread(f'bot_feed_{self.device_id}.png')
        
        cropped = self.screen_rgb[y:y + height, x:x + width]
        cv2.imwrite(filename, cropped)
        return filename
    
    # Game State Detection
    def get_current_icons(self, new_capture: bool = True) -> pd.DataFrame:
        """Get currently visible UI icons"""
        if new_capture:
            self.capture_screen()
        
        return self.perception.detect_icons(f'bot_feed_{self.device_id}.png')
    
    def get_battle_screen_state(self, start: bool = False, pve: bool = True, floor: int = 5) -> Tuple[pd.DataFrame, str]:
        """Analyze current battle screen state"""
        df = self.get_current_icons(new_capture=True)
        
        if df.empty:
            return df, 'unknown'
        
        # Analyze screen state based on visible icons
        if (df == 'fighting.png').any(axis=None) and not (df == '0cont_button.png').any(axis=None):
            return df, 'fighting'
        
        if (df == 'friend_menu.png').any(axis=None):
            self.click_button(np.array([100, 600]))
            return df, 'friend_menu'
        
        if (df == 'home_screen.png').any(axis=None) and (df == 'battle_icon.png').any(axis=None):
            if pve and start:
                self.click_button(np.array([640, 1259]))  # PvE button
                self._start_dungeon(floor)
            elif start:
                self.click_button(np.array([140, 1259]))  # PvP button
            return df, 'home'
        
        return df, 'menu'
    
    # Grid Analysis
    def scan_battle_grid(self, new_capture: bool = False) -> list:
        """Scan the battle grid and extract unit images"""
        boxes, box_size = self._get_grid_coordinates()
        
        if new_capture:
            self.capture_screen()
        
        box_list = boxes.reshape(15, 2)
        unit_files = []
        
        # Create OCR inputs directory
        os.makedirs('OCR_inputs', exist_ok=True)
        
        for i, (x, y) in enumerate(box_list):
            filename = f'OCR_inputs/icon_{i}.png'
            self.crop_image(x, y, *box_size, filename)
            unit_files.append(filename)
        
        return unit_files
    
    def _get_grid_coordinates(self) -> Tuple[np.ndarray, Tuple[int, int]]:
        """Get battle grid coordinates and box size"""
        # Grid configuration - adjust based on screen resolution
        # This would be moved to a configuration file in the full implementation
        grid_x = np.linspace(160, 740, 5)  # 5 columns
        grid_y = np.linspace(400, 700, 3)  # 3 rows
        
        xx, yy = np.meshgrid(grid_x, grid_y)
        boxes = np.stack([xx.ravel(), yy.ravel()], axis=1).astype(int)
        boxes = boxes.reshape(3, 5, 2)
        
        box_size = (100, 100)  # Standard unit box size
        
        return boxes, box_size
    
    # Game Navigation
    def _start_dungeon(self, floor: int = 5):
        """Navigate to and start a dungeon floor"""
        self.logger.debug(f'Starting Dungeon floor {floor}')
        
        # Calculate target chapter
        target_chapter = f'chapter_{int(np.ceil(floor/3))}.png'
        
        avail_buttons = self.get_current_icons(new_capture=True)
        
        if (avail_buttons == 'dungeon_page.png').any(axis=None):
            # Swipe to top of dungeon list
            for _ in range(14):
                self._swipe_vertical(-1)
            
            self.click(30, 600, 5)  # Stop scroll
            
            # Search for target chapter
            for _ in range(10):
                avail_buttons = self.get_current_icons(new_capture=True)
                
                if (avail_buttons == target_chapter).any(axis=None):
                    pos = self._get_button_position(avail_buttons, target_chapter)
                    if pos is not None:
                        # Click on chapter and then floor
                        self._click_dungeon_floor(pos, floor)
                        break
                
                # Continue scrolling
                self._swipe_vertical(1)
                self.click(30, 600)  # Stop scroll
    
    def _swipe_vertical(self, direction: int):
        """Swipe vertically (direction: -1 up, 1 down)"""
        if direction < 0:
            # Swipe up
            start_y, end_y = 800, 200
        else:
            # Swipe down
            start_y, end_y = 200, 800
        
        self.client.control.swipe(400, start_y, 400, end_y, 20, 1/60)
    
    def _get_button_position(self, buttons_df: pd.DataFrame, button_name: str) -> Optional[np.ndarray]:
        """Get position of a specific button from dataframe"""
        try:
            if 'pos [X,Y]' in buttons_df.columns:
                button_row = buttons_df[buttons_df['icon'] == button_name]
                if not button_row.empty:
                    return np.array(button_row['pos [X,Y]'].iloc[0])
        except Exception as e:
            self.logger.warning(f"Could not get button position for {button_name}: {e}")
        return None
    
    def _click_dungeon_floor(self, chapter_pos: np.ndarray, floor: int):
        """Click on specific dungeon floor based on chapter position"""
        floor_offset = floor % 3
        
        if floor_offset == 0:  # Last floor of chapter
            offset = np.array([30, -460])
        elif floor_offset == 1:  # First floor
            offset = np.array([30, 485])
        else:  # Middle floor
            offset = np.array([30, 885])
        
        self.click_button(chapter_pos + offset)
        self.click_button((500, 600))  # Confirm start
        
        # Wait for match to start
        for i in range(10):
            time.sleep(2)
            avail_buttons = self.get_current_icons(new_capture=True)
            self.logger.info(f'Waiting for match to start {i}')
            
            if avail_buttons['icon'].isin(['back_button.png', 'fighting.png']).any():
                break
    
    def restart_game(self, quick_disconnect: bool = False):
        """Restart the game application"""
        if quick_disconnect:
            # Quick disconnect method
            for _ in range(15):
                self.shell_command('monkey -p com.my.defense 1')
            return
        
        # Full restart
        self.shell_command('am force-stop com.my.defense')
        time.sleep(2)
        self.shell_command('monkey -p com.my.defense 1')
        time.sleep(10)  # Wait for app to load
    
    # Main Bot Loop
    def run(self, max_loops: int = 800):
        """Main bot execution loop"""
        self.running = True
        self.logger.info("Starting bot main loop")
        
        try:
            loop_count = 0
            
            while self.running and not self.bot_stop and loop_count < max_loops:
                # Main game loop logic
                buttons, state = self.get_battle_screen_state(start=False)
                
                if state == 'fighting':
                    self._handle_combat()
                elif state == 'home':
                    self._handle_home_screen()
                elif state == 'menu':
                    self._handle_menu()
                else:
                    self.logger.info(f"Unknown state: {state}")
                    time.sleep(1)
                
                loop_count += 1
                
                if loop_count % 100 == 0:
                    self.logger.info(f"Completed {loop_count} loops")
            
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
            raise
        finally:
            self.running = False
            self.logger.info("Bot main loop ended")
    
    def _handle_combat(self):
        """Handle combat state logic"""
        # This would contain the combat logic from the original bot
        # For now, just a placeholder
        time.sleep(1)
        self.logger.debug("In combat - placeholder logic")
    
    def _handle_home_screen(self):
        """Handle home screen navigation"""
        time.sleep(1)
        self.logger.debug("On home screen - placeholder logic")
    
    def _handle_menu(self):
        """Handle menu interactions"""
        time.sleep(1)
        self.logger.debug("In menu - placeholder logic")


# Utility functions that were previously standalone
def get_grid_coordinates():
    """Get battle grid pixel coordinates"""
    # This would be the implementation from the original get_grid() function
    pass


def filter_units(unit_series, units):
    """Filter units based on criteria"""
    # Implementation from original filter_units function
    pass


# Module initialization
__all__ = ['RushRoyaleBot']
