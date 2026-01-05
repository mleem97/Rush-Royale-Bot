"""
Rush Royale Bot - Icon Detection Module
Python 3.13 Compatible

Provides template matching and icon detection for:
- Menu buttons and navigation
- Store state detection
- General icon matching
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from ..screen_capture import ScreenCapture


class IconDetector:
    """
    Detects icons and UI elements using template matching.
    
    Uses OpenCV template matching with multi-scale support
    for robust icon detection across different game states.
    """
    
    # Default icon directory
    ICON_DIR = 'icons'
    
    # Valid targets for quick lookup
    QUICK_TARGETS = ['battle_icon', 'pvp_button', 'back_button', 'cont_button', 'fighting']
    
    def __init__(
        self,
        screen_capture: 'ScreenCapture',
        logger: logging.Logger | None = None
    ):
        """
        Initialize icon detector.
        
        Args:
            screen_capture: ScreenCapture instance
            logger: Optional logger instance
        """
        self.screen = screen_capture
        self.logger = logger or logging.getLogger(__name__)
    
    def find_icon(
        self,
        target: str,
        refresh: bool = True,
        threshold: float = 0.8
    ) -> tuple[int, int] | None:
        """
        Find icon position on screen.
        
        Args:
            target: Icon name (without extension for quick targets)
            refresh: Whether to take new screenshot
            threshold: Match confidence threshold
            
        Returns:
            Position (x, y) or None if not found
        """
        if target not in self.QUICK_TARGETS:
            self.logger.warning(f"Invalid quick target: {target}")
            return None
        
        if refresh:
            self.screen.capture()
        
        img_gray = self.screen.grayscale
        if img_gray is None:
            return None
        
        template_path = f'{self.ICON_DIR}/{target}.png'
        template = cv2.imread(template_path, 0)
        
        if template is None:
            self.logger.error(f"Could not load template: {template_path}")
            return None
        
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        
        if len(loc[0]) > 0:
            y = int(loc[0][0])
            x = int(loc[1][0])
            return (x, y)
        
        return None
    
    # Alias for backward compatibility
    getXYByImage = find_icon
    
    def get_store_state(self) -> str:
        """
        Detect current store state by pixel color.
        
        Returns:
            State name: 'refresh', 'new_store', 'nothing', 'new_offer', 'spin_only'
        """
        if self.screen.screen_rgb is None:
            return 'nothing'
        
        x, y = 140, 1412
        
        store_states_names = ['refresh', 'new_store', 'nothing', 'new_offer', 'spin_only']
        store_states = np.array([
            [255, 255, 255],  # refresh
            [27, 235, 206],   # new_store
            [63, 38, 12],     # nothing
            [48, 253, 251],   # new_offer
            [80, 153, 193],   # spin_only
        ])
        
        store_rgb = self.screen.screen_rgb[y:y + 1, x:x + 1][0][0]
        
        # Calculate mean squared error to find closest state
        store_mse = ((store_states - store_rgb) ** 2).mean(axis=1)
        closest_state = store_mse.argmin()
        
        return store_states_names[closest_state]
    
    def _match_template_multi_scale(
        self,
        src_gray: np.ndarray,
        tmpl_gray: np.ndarray,
        base_thresh: float,
        is_chapter: bool = False
    ) -> tuple[bool, tuple[int, int], float]:
        """
        Match template with optional multi-scale support.
        
        Args:
            src_gray: Source grayscale image
            tmpl_gray: Template grayscale image
            base_thresh: Base threshold for matching
            is_chapter: Enable multi-scale for chapter icons
            
        Returns:
            Tuple of (found, (x, y), max_value)
        """
        best = (False, (0, 0), 0.0)
        
        # Scale factors to try
        scales = [1.0]
        if is_chapter:
            scales = [0.9, 1.0, 1.1]
        
        for scale in scales:
            if scale != 1.0:
                new_w = max(1, int(tmpl_gray.shape[1] * scale))
                new_h = max(1, int(tmpl_gray.shape[0] * scale))
                tmpl = cv2.resize(tmpl_gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
            else:
                tmpl = tmpl_gray
            
            # Skip if template larger than source
            if src_gray.shape[0] < tmpl.shape[0] or src_gray.shape[1] < tmpl.shape[1]:
                continue
            
            res = cv2.matchTemplate(src_gray, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            
            # Keep best match
            if max_val > best[2]:
                best = (max_val >= base_thresh, (max_loc[0], max_loc[1]), float(max_val))
        
        # Relaxed threshold for chapter icons
        if is_chapter and not best[0] and best[2] >= (base_thresh - 0.05):
            return (True, best[1], best[2])
        
        return best
    
    def get_current_icons(
        self,
        refresh: bool = True,
        available_only: bool = False
    ) -> pd.DataFrame:
        """
        Detect all icons currently on screen.
        
        Args:
            refresh: Whether to take new screenshot
            available_only: Return only detected icons
            
        Returns:
            DataFrame with columns: icon, available, pos [X,Y]
        """
        if refresh:
            self.screen.capture()
        
        img_rgb = self.screen.screen_rgb
        if img_rgb is None:
            self.logger.warning('Screenshot is None - cannot detect icons')
            return pd.DataFrame(columns=['icon', 'available', 'pos [X,Y]'])
        
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        img_gray_blur = cv2.GaussianBlur(img_gray, (3, 3), 0)
        
        self.logger.debug(f'Screenshot shape: {img_gray.shape}')
        
        current_icons = []
        icon_count = 0
        
        # Check every icon template - only .png files, skip directories
        icon_dir_path = Path(self.ICON_DIR)
        for target in os.listdir(self.ICON_DIR):
            target_path = icon_dir_path / target
            # Skip directories and non-PNG files
            if target_path.is_dir() or not target.lower().endswith('.png'):
                continue
            x, y = 0, 0
            
            template_path = f'{self.ICON_DIR}/{target}'
            template = cv2.imread(template_path, 0)
            
            if template is None:
                self.logger.debug(f'Could not load template: {template_path}')
                continue
            
            template_blur = cv2.GaussianBlur(template, (3, 3), 0)
            
            # Per-icon threshold tuning
            is_chapter = 'chapter_' in target
            threshold = 0.8
            
            if is_chapter:
                threshold = 0.75
            elif target in ['dungeon_page.png']:
                threshold = 0.78
            
            # Match template
            found, (best_x, best_y), max_val = self._match_template_multi_scale(
                img_gray_blur, template_blur, threshold, is_chapter=is_chapter
            )
            
            # Debug logging for key icons
            if target in ['home_screen.png', 'battle_icon.png'] or 'chapter_' in target:
                self.logger.debug(f'Icon {target}: max_val={max_val:.3f}, found={found}')
            
            if found:
                y = int(best_y)
                x = int(best_x)
                icon_count += 1
            
            current_icons.append([target, found, (x, y)])
        
        self.logger.debug(f'Total icons found: {icon_count}/{len(current_icons)}')
        
        icon_df = pd.DataFrame(current_icons, columns=['icon', 'available', 'pos [X,Y]'])
        
        if available_only:
            icon_df = icon_df[icon_df['available'] == True].reset_index(drop=True)
        
        return icon_df
