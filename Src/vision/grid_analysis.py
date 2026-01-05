"""
Rush Royale Bot - Grid Analysis Module
Python 3.13 Compatible

Provides grid scanning and analysis:
- Scan battle grid cells
- OCR image preparation
- Grid state tracking
"""
from __future__ import annotations

import os
import logging
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..screen_capture import ScreenCapture

# Try to import bot_perception
try:
    from .. import bot_perception
except ImportError:
    import bot_perception


class GridAnalyzer:
    """
    Analyzes the 3x5 battle grid.
    
    Handles:
    - Grid cell scanning
    - Unit detection via OCR
    - Grid state tracking over time
    """
    
    OCR_DIR = 'OCR_inputs'
    
    def __init__(
        self,
        screen_capture: 'ScreenCapture',
        logger: logging.Logger | None = None
    ):
        """
        Initialize grid analyzer.
        
        Args:
            screen_capture: ScreenCapture instance
            logger: Optional logger instance
        """
        self.screen = screen_capture
        self.logger = logger or logging.getLogger(__name__)
        
        # Ensure OCR directory exists
        if not os.path.isdir(self.OCR_DIR):
            os.mkdir(self.OCR_DIR)
    
    def scan_grid(self, refresh: bool = False) -> list[str]:
        """
        Scan battle grid and save cell images for OCR.
        
        Args:
            refresh: Whether to take new screenshot first
            
        Returns:
            List of saved cell image paths
        """
        from ..utils.grid_utils import get_grid
        
        boxes, box_size = get_grid()
        
        if refresh:
            self.screen.capture()
        
        box_list = boxes.reshape(15, 2)
        names = []
        
        for i in range(len(box_list)):
            file_name = f'{self.OCR_DIR}/icon_{i}.png'
            self.screen.crop(
                int(box_list[i][0]),
                int(box_list[i][1]),
                int(box_size[0]),
                int(box_size[1]),
                save_path=file_name
            )
            names.append(file_name)
        
        return names
    
    def get_grid_status(
        self,
        refresh: bool = False,
        prev_grid: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """
        Get current grid status with unit detection.
        
        Args:
            refresh: Whether to take new screenshot
            prev_grid: Previous grid state for age tracking
            
        Returns:
            DataFrame with unit, rank, grid_pos, Age columns
        """
        names = self.scan_grid(refresh=refresh)
        return bot_perception.grid_status(names, prev_grid=prev_grid)
    
    def get_mana(self) -> int:
        """
        Get current mana value from screen.
        
        Returns:
            Current mana as integer
        """
        # Mana display position
        x, y = 220, 1360
        width, height = 90, 50
        
        # This would need OCR implementation
        # For now, return placeholder
        self.logger.debug("Mana detection requires OCR implementation")
        return 0
