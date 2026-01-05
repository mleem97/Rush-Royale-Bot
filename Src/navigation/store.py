"""
Rush Royale Bot - Store Navigation Module
Python 3.13 Compatible

Handles store navigation and purchases.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..adb_controller import ADBController
    from ..vision.icon_detection import IconDetector

try:
    from ..utils.grid_utils import get_button_pos
except ImportError:
    from Src.utils.grid_utils import get_button_pos


class StoreNavigator:
    """
    Navigates in-game store.
    
    Handles:
    - Store refresh button location
    - Free item collection
    - Shop purchases
    """
    
    # Button positions
    STORE_BUTTON = (100, 1500)
    STORE_TAB = (475, 1300)
    
    def __init__(
        self,
        adb: 'ADBController',
        icon_detector: 'IconDetector',
        logger: logging.Logger | None = None
    ):
        """
        Initialize store navigator.
        
        Args:
            adb: ADB controller for touch actions
            icon_detector: Icon detector for UI detection
            logger: Optional logger instance
        """
        self.adb = adb
        self.icons = icon_detector
        self.logger = logger or logging.getLogger(__name__)
    
    def find_refresh_button(self) -> np.ndarray | None:
        """
        Navigate to and locate store refresh button.
        
        Returns:
            Button position or None
        """
        from ..utils.grid_utils import get_grid
        boxes, _ = get_grid()
        
        self.adb.tap_button(self.STORE_BUTTON)
        
        # Swipe to top
        for _ in range(5):
            self.adb.swipe_grid((0, 0), (2, 0), boxes)
        
        self.adb.tap(30, 150)  # Stop scroll
        
        avail_buttons = self.icons.get_current_icons(available_only=True)
        
        if (avail_buttons['icon'] == 'refresh_button.png').any():
            return get_button_pos(avail_buttons, 'refresh_button.png')
        
        return None
    
    def refresh_shop(self) -> bool:
        """
        Refresh shop and buy items.
        
        Returns:
            True if shop was refreshed
        """
        self.adb.tap_button(self.STORE_BUTTON)
        self.adb.tap_button(self.STORE_TAB)
        
        pos = self.find_refresh_button()
        
        if pos is None:
            return False
        
        # Buy first (free) item
        self.adb.tap_button((pos[0] - 300, pos[1] - 820))
        self.adb.tap(400, 1165)  # Buy
        self.adb.tap(30, 150)    # Close popup
        
        # Buy last item (possible legendary)
        self.adb.tap_button((pos[0] + 400, pos[1] - 400))
        self.adb.tap(400, 1165)  # Buy
        self.adb.tap(30, 150)    # Close popup
        
        self.logger.warning('Bought store units!')
        
        # Refresh shop (watch ad)
        self.adb.tap_button(tuple(pos))
        
        return True
