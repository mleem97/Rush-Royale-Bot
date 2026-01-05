"""
Rush Royale Bot - Ad Watching Module
Python 3.13 Compatible

Handles automatic ad watching and rewards collection.
"""
from __future__ import annotations

import time
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..adb_controller import ADBController
    from ..vision.icon_detection import IconDetector
    from .store import StoreNavigator

try:
    from ..utils.grid_utils import get_button_pos
except ImportError:
    from Src.utils.grid_utils import get_button_pos


class AdWatcher:
    """
    Handles automatic ad watching.
    
    Detects and watches various ad types:
    - Quest completion ads
    - Season pass ads
    - PvE reward ads
    - Store refresh ads
    """
    
    def __init__(
        self,
        adb: 'ADBController',
        icon_detector: 'IconDetector',
        store: 'StoreNavigator',
        logger: logging.Logger | None = None
    ):
        """
        Initialize ad watcher.
        
        Args:
            adb: ADB controller for touch actions
            icon_detector: Icon detector for UI detection
            store: Store navigator for shop refresh
            logger: Optional logger instance
        """
        self.adb = adb
        self.icons = icon_detector
        self.store = store
        self.logger = logger or logging.getLogger(__name__)
    
    def watch_ads(self) -> None:
        """
        Watch available ads and collect rewards.
        """
        avail_buttons = self.icons.get_current_icons(available_only=True)
        
        # Quest completion
        if (avail_buttons['icon'] == 'quest_done.png').any():
            pos = get_button_pos(avail_buttons, 'quest_done.png')
            self.adb.tap_button(tuple(pos))
            self.adb.tap(700, 600)  # Collect
            self.adb.tap(700, 400)  # Collect second
            
            for _ in range(2):
                self.adb.tap(150, 250)  # Click dailies
            
            self.adb.tap(420, 420)  # Collect ad chest
        
        # Season pass ad
        elif (avail_buttons['icon'] == 'ad_season.png').any():
            pos = get_button_pos(avail_buttons, 'ad_season.png')
            self.adb.tap_button(tuple(pos))
        
        # PvE ad
        elif (avail_buttons['icon'] == 'ad_pve.png').any():
            pos = get_button_pos(avail_buttons, 'ad_pve.png')
            self.adb.tap_button(tuple(pos))
        
        # Refresh shop
        elif (avail_buttons['icon'] == 'battle_icon.png').any():
            self.store.refresh_shop()
        
        else:
            return  # No ads available
        
        # Wait for ad to complete
        self._wait_for_ad_completion()
    
    def _wait_for_ad_completion(self) -> None:
        """Wait for ad to complete and return to menu."""
        # Check if ad was started
        avail_buttons = self.icons.get_current_icons()
        
        status = self._get_screen_status(avail_buttons)
        
        if status in ['menu', 'home'] or (avail_buttons['icon'] == 'refresh_button.png').any():
            self.logger.info('AD completed quickly')
            return
        
        # Watch ad (30 second timeout)
        time.sleep(30)
        
        # Keep trying to exit
        for i in range(10):
            avail_buttons = self.icons.get_current_icons()
            status = self._get_screen_status(avail_buttons)
            
            if status in ['menu', 'home']:
                self.logger.info('AD completed')
                return
            
            time.sleep(2)
            self.adb.tap(870, 30)   # Skip/close
            self.adb.tap(870, 100)  # Close play store popup
            
            if i > 5:
                self.adb.press_back()
            
            self.logger.info(f'AD TIME {i} {status}')
        
        # Force restart if stuck
        self.logger.warning('Stuck on ad, restarting app')
        self.adb.restart_app()
    
    def _get_screen_status(self, buttons_df) -> str:
        """Determine current screen status."""
        if buttons_df.empty:
            return 'unknown'
        
        icons = buttons_df['icon']
        
        if (icons == 'fighting.png').any():
            return 'fighting'
        if (icons == 'home_screen.png').any():
            return 'home'
        if (icons == 'back_button.png').any():
            return 'menu'
        
        return 'unknown'
