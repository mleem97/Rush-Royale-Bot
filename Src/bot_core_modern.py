"""
Rush Royale Bot Core - Refactored Version
Python 3.13 Compatible

This is the refactored Bot class that uses the new modular architecture:
- ADBController for device communication
- ScreenCapture for screenshots
- IconDetector for UI detection
- GridAnalyzer for grid analysis
- MergeController for unit merging
- ManaManager for card upgrades
- Navigation modules for game flow
"""
from __future__ import annotations

import os
import time
import logging
from typing import Optional, Any
from configparser import ConfigParser

import numpy as np
import pandas as pd
import cv2

# Import new modular components
try:
    from . import bot_perception
    from . import port_scan
    from .adb_controller import ADBController, const, SLEEP_DELAY
    from .screen_capture import ScreenCapture
    from .vision import IconDetector, GridAnalyzer
    from .combat import MergeController, ManaManager
    from .navigation import DungeonNavigator, StoreNavigator, AdWatcher
    from .utils.grid_utils import (
        get_grid,
        get_unit_count,
        preserve_unit,
        grid_meta_info,
        adv_filter_keys,
        get_button_pos,
    )
except ImportError:
    # Direct execution fallback
    import bot_perception
    import port_scan
    from adb_controller import ADBController, const, SLEEP_DELAY
    from screen_capture import ScreenCapture
    from vision import IconDetector, GridAnalyzer
    from combat import MergeController, ManaManager
    from navigation import DungeonNavigator, StoreNavigator, AdWatcher
    from utils.grid_utils import (
        get_grid,
        get_unit_count,
        preserve_unit,
        grid_meta_info,
        adv_filter_keys,
        get_button_pos,
    )


class BotModern:
    """
    Modern Rush Royale Bot using modular architecture.
    
    This class coordinates all bot subsystems:
    - Device control via ADBController
    - Screen capture via ScreenCapture
    - Vision via IconDetector and GridAnalyzer
    - Combat via MergeController and ManaManager
    - Navigation via DungeonNavigator, StoreNavigator, AdWatcher
    """
    
    def __init__(self, device: str | None = None, logger: logging.Logger | None = None):
        """
        Initialize the modern bot.
        
        Args:
            device: Device serial (e.g., "127.0.0.1:5555"). Auto-detected if None.
            logger: Logger instance. Created if None.
        """
        # State variables
        self.bot_stop = False
        self.combat: str | None = None
        self.output: str | None = None
        self.grid_df: pd.DataFrame | None = None
        self.unit_series: pd.Series | None = None
        self.merge_series: pd.Series | None = None
        self.df_groups: pd.Series | None = None
        self.info: str | None = None
        self.combat_step: int | None = None
        self.config: ConfigParser | None = None
        
        # Setup logger
        self.logger = logger or logging.getLogger(__name__)
        
        # Get device
        if device is None:
            device = port_scan.get_device()
        if not device:
            raise ConnectionError("No device found!")
        
        self.device = device
        self.bot_id = device.split(':')[-1]
        
        # Initialize components
        self._init_components()
        
        self.logger.info(f'Bot initialized for device: {device}')
    
    def _init_components(self) -> None:
        """Initialize all bot subsystems."""
        # Core components
        self.adb = ADBController(self.device, self.logger)
        self.screen = ScreenCapture(self.adb, self.bot_id, self.logger)
        
        # Vision components
        self.icons = IconDetector(self.screen, self.logger)
        self.grid_analyzer = GridAnalyzer(self.screen, self.logger)
        
        # Combat components
        self.merger = MergeController(self.adb, self.grid_analyzer, self.logger)
        self.mana = ManaManager(self.adb, self.logger)
        
        # Navigation components
        self.dungeon = DungeonNavigator(self.adb, self.icons, self.logger)
        self.store = StoreNavigator(self.adb, self.icons, self.logger)
        self.ads = AdWatcher(self.adb, self.icons, self.store, self.logger)
        
        # Launch game
        self.adb.launch_app()
        time.sleep(0.5)
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Cleanup on exit."""
        self.bot_stop = True
        self.logger.info('Exiting bot')
        self.screen.cleanup()
    
    # ==================== Compatibility Layer ====================
    # These methods provide backward compatibility with the old Bot class
    
    @property
    def screenRGB(self) -> np.ndarray | None:
        """Get current screen image (backward compatibility)."""
        return self.screen.screen_rgb
    
    @screenRGB.setter
    def screenRGB(self, value: np.ndarray) -> None:
        """Set screen image (backward compatibility)."""
        self.screen.screen_rgb = value
    
    def shell(self, cmd: str) -> str | None:
        """Execute ADB shell command (backward compatibility)."""
        return self.adb.shell(cmd)
    
    def click(self, x: int, y: int, delay_mult: float = 1.0) -> None:
        """Tap screen (backward compatibility)."""
        self.adb.tap(x, y, delay_mult)
    
    def click_button(self, pos: tuple[int, int]) -> None:
        """Tap button (backward compatibility)."""
        self.adb.tap_button(pos)
    
    def swipe(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        """Swipe on grid (backward compatibility)."""
        boxes, _ = get_grid()
        self.adb.swipe_grid(start, end, boxes)
    
    def key_input(self, key: int) -> None:
        """Send key event (backward compatibility)."""
        self.adb.key_input(key)
    
    def restart_RR(self, quick_disconnect: bool = False) -> None:
        """Restart game (backward compatibility)."""
        self.adb.restart_app(quick_disconnect=quick_disconnect)
    
    def getScreen(self) -> np.ndarray | None:
        """Take screenshot (backward compatibility)."""
        return self.screen.capture()
    
    def crop_img(self, x: int, y: int, dx: int, dy: int, name: str = 'icon.png') -> None:
        """Crop image (backward compatibility)."""
        self.screen.crop(x, y, dx, dy, name)
    
    def find_scrcpy_executable(self) -> str | None:
        """Find scrcpy (backward compatibility)."""
        return self.screen.scrcpy_executable
    
    def start_scrcpy(self) -> bool:
        """Start scrcpy mirror (backward compatibility)."""
        return self.screen.start_scrcpy_mirror()
    
    def stop_scrcpy(self) -> None:
        """Stop scrcpy mirror (backward compatibility)."""
        self.screen.stop_scrcpy_mirror()
    
    # ==================== Vision Methods ====================
    
    def getXYByImage(self, target: str, new: bool = True) -> tuple[int, int] | None:
        """Find icon position (backward compatibility)."""
        return self.icons.find_icon(target, refresh=new)
    
    def get_store_state(self) -> str:
        """Get store state (backward compatibility)."""
        return self.icons.get_store_state()
    
    def get_current_icons(self, new: bool = True, available: bool = False) -> pd.DataFrame:
        """Get current icons (backward compatibility)."""
        return self.icons.get_current_icons(refresh=new, available_only=available)
    
    def scan_grid(self, new: bool = False) -> list[str]:
        """Scan grid (backward compatibility)."""
        return self.grid_analyzer.scan_grid(refresh=new)
    
    def getMana(self) -> int:
        """Get mana value (backward compatibility)."""
        return self.grid_analyzer.get_mana()
    
    # ==================== Combat Methods ====================
    
    def merge_unit(self, df_split, merge_series: pd.Series) -> pd.DataFrame | None:
        """Merge unit (backward compatibility)."""
        return self.merger.merge_unit(df_split, merge_series)
    
    def merge_special_unit(self, df_split, merge_series: pd.Series, special_type: str) -> pd.DataFrame | None:
        """Merge special unit (backward compatibility)."""
        return self.merger.merge_special_unit(df_split, merge_series, special_type)
    
    def special_merge(self, df_split, merge_series: pd.Series, target: str = 'zealot.png') -> pd.DataFrame | None:
        """Special merge (backward compatibility)."""
        return self.merger.special_merge(df_split, merge_series, target)
    
    def harley_merge(self, df_split, merge_series: pd.Series, target: str = 'knight_statue.png') -> pd.DataFrame | None:
        """Harley merge (backward compatibility)."""
        return self.merger.harley_merge(df_split, merge_series, target)
    
    def log_merge(self, merge_df: pd.DataFrame) -> None:
        """Log merge (backward compatibility)."""
        self.merger._log_merge(merge_df)
    
    def try_merge(
        self,
        rank: int = 1,
        prev_grid: pd.DataFrame | None = None,
        merge_target: str = 'zealot.png'
    ) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame | None, str]:
        """Try merge (backward compatibility)."""
        return self.merger.try_merge(rank, prev_grid, merge_target, self.config)
    
    def mana_level(self, cards: list[int], hero_power: bool = False) -> None:
        """Upgrade cards (backward compatibility)."""
        self.mana.upgrade_cards(cards, hero_power)
    
    # ==================== Navigation Methods ====================
    
    def play_dungeon(self, floor: int = 5) -> bool:
        """Play dungeon (backward compatibility)."""
        return self.dungeon.play_dungeon(floor)
    
    def find_store_refresh(self) -> np.ndarray | None:
        """Find store refresh button (backward compatibility)."""
        return self.store.find_refresh_button()
    
    def refresh_shop(self) -> bool:
        """Refresh shop (backward compatibility)."""
        return self.store.refresh_shop()
    
    def watch_ads(self) -> None:
        """Watch ads (backward compatibility)."""
        self.ads.watch_ads()
    
    def battle_screen(
        self,
        start: bool = False,
        pve: bool = True,
        floor: int = 5
    ) -> tuple[pd.DataFrame, str]:
        """
        Navigate battle screen (backward compatibility).
        
        Args:
            start: Whether to start a battle
            pve: PvE mode (dungeon) vs PvP
            floor: Dungeon floor number
            
        Returns:
            Tuple of (icon dataframe, status string)
        """
        df = self.get_current_icons(available=True)
        
        if df.empty:
            self.key_input(const.KEYCODE_BACK)
            return df, 'lost'
        
        icons = df['icon']
        
        # Check fighting state
        if (icons == 'fighting.png').any() and not (icons == '0cont_button.png').any():
            return df, 'fighting'
        
        # Check friend menu
        if (icons == 'friend_menu.png').any():
            self.click_button((100, 600))
            return df, 'friend_menu'
        
        # Check home screen
        if (icons == 'home_screen.png').any() and (icons == 'battle_icon.png').any():
            if pve and start:
                self.click_button((640, 1259))
                self.play_dungeon(floor=floor)
            elif start:
                self.click_button((140, 1259))
            time.sleep(1)
            return df, 'home'
        
        # Check clickable buttons
        df_click = df[df['icon'].isin([
            'back_button.png', 'battle_icon.png', '0cont_button.png', '1quit.png'
        ])]
        
        if not df_click.empty:
            button_pos = df_click['pos [X,Y]'].tolist()[0]
            self.click_button(button_pos)
            return df, 'menu'
        
        self.key_input(const.KEYCODE_BACK)
        return df, 'lost'


# ==================== Standalone Functions ====================
# These remain as module-level functions for backward compatibility

# Re-export utility functions
__all__ = [
    'BotModern',
    'Bot',  # Alias for compatibility
    'get_grid',
    'get_unit_count',
    'preserve_unit',
    'grid_meta_info',
    'filter_units',
    'adv_filter_keys',
    'read_knowledge',
    'get_button_pos',
]

# Import remaining functions from utils
try:
    from .utils.grid_utils import filter_units, read_knowledge
except ImportError:
    from utils.grid_utils import filter_units, read_knowledge

# Create Bot alias for backward compatibility
Bot = BotModern
