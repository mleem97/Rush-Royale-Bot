"""
Rush Royale Bot - Dungeon Navigation Module
Python 3.13 Compatible

Handles dungeon floor selection and navigation.
"""
from __future__ import annotations

import time
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


class DungeonNavigator:
    """
    Navigates dungeon floor selection.
    
    Handles scrolling, chapter detection, and floor selection
    for PvE dungeon mode.
    """
    
    def __init__(
        self,
        adb: 'ADBController',
        icon_detector: 'IconDetector',
        logger: logging.Logger | None = None
    ):
        """
        Initialize dungeon navigator.
        
        Args:
            adb: ADB controller for touch actions
            icon_detector: Icon detector for UI detection
            logger: Optional logger instance
        """
        self.adb = adb
        self.icons = icon_detector
        self.logger = logger or logging.getLogger(__name__)
    
    def _swipe_with_grid(
        self, 
        boxes: 'np.ndarray', 
        start: tuple[int, int], 
        end: tuple[int, int],
        offset: int = 60
    ) -> None:
        """
        Swipe using grid coordinates (matches original bot_core.swipe behavior).
        
        This converts grid positions to pixel coordinates for swiping,
        which is needed for dungeon menu scrolling.
        
        Args:
            boxes: Grid coordinate array from get_grid()
            start: Start grid position (row, col)
            end: End grid position (row, col)
            offset: Pixel offset from box edge
        """
        start_pos = boxes[start[0], start[1]] + offset
        end_pos = boxes[end[0], end[1]] + offset
        
        self.adb.swipe(
            (int(start_pos[0]), int(start_pos[1])),
            (int(end_pos[0]), int(end_pos[1]))
        )
    
    def play_dungeon(self, floor: int = 5) -> bool:
        """
        Navigate to and start a dungeon floor.
        
        Args:
            floor: Dungeon floor number (1-42+)
            
        Returns:
            True if floor was started successfully
        """
        self.logger.debug(f'Starting Dungeon floor {floor}')
        
        # Calculate target chapter
        target_chapter = f'chapter_{int(np.ceil(floor / 3))}.png'
        next_chapter = f'chapter_{int(np.ceil((floor + 1) / 3))}.png'
        
        self.logger.debug(f'Target: {target_chapter}, Next: {next_chapter}')
        
        pos = np.array([0, 0])
        avail_buttons = self.icons.get_current_icons(available_only=True)
        
        # Check if on dungeon page
        if not (avail_buttons['icon'] == 'dungeon_page.png').any():
            self.logger.warning('Not on dungeon page')
            return False
        
        # Get grid for swipe coordinates (same as original bot_core.py)
        try:
            from ..utils.grid_utils import get_grid
        except ImportError:
            from Src.utils.grid_utils import get_grid
        
        boxes, _ = get_grid()
        
        # Swipe to top of dungeon list - use grid-based swipe like original
        # [0,0] to [2,0] = swipe from top-left grid to bottom-left grid = scroll UP
        for _ in range(14):
            self._swipe_with_grid(boxes, (0, 0), (2, 0))
        
        self.adb.tap(30, 600, 5)  # Stop scroll and scan screen
        
        # Search for chapter
        expanded = False
        
        for i in range(10):
            avail_buttons = self.icons.get_current_icons(available_only=True)
            available_chapters = [
                icon for icon in avail_buttons['icon']
                if 'chapter_' in icon
            ]
            self.logger.debug(f'Iteration {i}: Chapters: {available_chapters}')
            
            # Found target chapter
            if (avail_buttons['icon'] == target_chapter).any():
                pos = get_button_pos(avail_buttons, target_chapter)
                self.logger.info(f'Found {target_chapter} at {pos}')
                
                if not expanded:
                    expanded = True
                    # Click to expand chapter (same offset as original)
                    self.adb.tap_button((pos[0] + 500, pos[1] + 90))
                
                # Stop when chapter is near top of screen
                if pos[1] < 550 and floor % 3 != 0:
                    break
            
            # Found next chapter (for last floor of chapter)
            elif (avail_buttons['icon'] == next_chapter).any() and floor % 3 == 0:
                pos = get_button_pos(avail_buttons, next_chapter)
                self.logger.info(f'Found {next_chapter} at {pos}')
                break
            
            # Continue scrolling DOWN to find correct chapter
            # [2,0] to [0,0] = swipe from bottom to top = scroll DOWN
            for _ in range(2):
                self._swipe_with_grid(boxes, (2, 0), (0, 0))
            self.adb.tap(30, 600)  # Stop scroll
        
        # Click floor
        if not (pos == np.array([0, 0])).any():
            self.logger.info(f'Clicking floor {floor} at {pos}')
            
            # Calculate floor button offset
            floor_mod = floor % 3
            if floor_mod == 0:
                offset = (30, -460)
            elif floor_mod == 1:
                offset = (30, 485)
            else:  # floor_mod == 2
                offset = (30, 885)
            
            self.adb.tap_button((pos[0] + offset[0], pos[1] + offset[1]))
            self.adb.tap_button((500, 600))  # Confirm
            
            # Wait for match
            for i in range(10):
                time.sleep(2)
                avail_buttons = self.icons.get_current_icons(available_only=True)
                self.logger.info(f'Waiting for match {i}')
                
                if avail_buttons['icon'].isin(['back_button.png', 'fighting.png']).any():
                    return True
        else:
            self.logger.error(f'Could not find chapter for floor {floor}')
        
        return False
