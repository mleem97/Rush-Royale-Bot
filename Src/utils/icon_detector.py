"""
Rush Royale Bot - Language-Neutral Icon Detector
Python 3.13 Compatible

Provides language-neutral chapter and floor detection using:
1. Template matching for graphical elements
2. EasyOCR fallback for number detection
3. Configurable thresholds from config.ini

This module addresses Issue #10 (chapter detection across languages).
"""
from __future__ import annotations

import os
import re
import logging
import configparser
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Lazy load EasyOCR to avoid slow startup
_ocr_reader = None


def _get_ocr_reader():
    """Lazy-load EasyOCR reader."""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            # Only load English for number detection (faster)
            _ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            logger.info("EasyOCR reader initialized")
        except ImportError:
            logger.warning("EasyOCR not available, OCR fallback disabled")
            _ocr_reader = False  # Mark as unavailable
    return _ocr_reader if _ocr_reader is not False else None


@dataclass
class DetectionResult:
    """Result of an icon detection operation."""
    found: bool
    icon_name: str
    position: Tuple[int, int]
    confidence: float
    method: str  # 'template', 'ocr', 'hybrid'
    
    def __bool__(self) -> bool:
        return self.found


@dataclass  
class DetectionConfig:
    """Configuration for icon detection thresholds."""
    icon_threshold: float = 0.78
    chapter_threshold: float = 0.70
    dungeon_page_threshold: float = 0.72
    floor_threshold: float = 0.75
    fighting_threshold: float = 0.75
    mse_threshold: int = 2000
    use_ocr_fallback: bool = True
    ocr_confidence_threshold: float = 0.5
    chapter_scales: List[float] = None
    
    def __post_init__(self):
        if self.chapter_scales is None:
            self.chapter_scales = [0.9, 1.0, 1.1]
    
    @classmethod
    def from_config_file(cls, config_path: Path = None) -> 'DetectionConfig':
        """Load detection config from config.ini."""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.ini"
        
        config = configparser.ConfigParser()
        if config_path.exists():
            config.read(config_path)
        
        def get_float(key: str, default: float) -> float:
            try:
                return config.getfloat('detection', key)
            except (configparser.NoSectionError, configparser.NoOptionError):
                return default
        
        def get_bool(key: str, default: bool) -> bool:
            try:
                return config.getboolean('detection', key)
            except (configparser.NoSectionError, configparser.NoOptionError):
                return default
        
        def get_scales(key: str, default: List[float]) -> List[float]:
            try:
                scales_str = config.get('detection', key)
                return [float(s.strip()) for s in scales_str.split(',')]
            except (configparser.NoSectionError, configparser.NoOptionError):
                return default
        
        return cls(
            icon_threshold=get_float('icon_threshold', 0.78),
            chapter_threshold=get_float('chapter_threshold', 0.70),
            dungeon_page_threshold=get_float('dungeon_page_threshold', 0.72),
            floor_threshold=get_float('floor_threshold', 0.75),
            fighting_threshold=get_float('fighting_threshold', 0.75),
            mse_threshold=int(get_float('mse_threshold', 2000)),
            use_ocr_fallback=get_bool('use_ocr_fallback', True),
            ocr_confidence_threshold=get_float('ocr_confidence_threshold', 0.5),
            chapter_scales=get_scales('chapter_scales', [0.9, 1.0, 1.1])
        )


class IconDetector:
    """
    Language-neutral icon detection using template matching and OCR.
    
    Features:
    - Multi-scale template matching
    - EasyOCR fallback for number detection
    - Configurable thresholds
    - Chapter number extraction (language-neutral)
    
    Example:
        detector = IconDetector()
        
        # Detect chapter by number
        result = detector.detect_chapter_number(screenshot, target_chapter=2)
        if result.found:
            print(f"Chapter 2 at {result.position}")
        
        # Detect any icon
        result = detector.detect_icon(screenshot, 'dungeon_page.png')
    """
    
    def __init__(
        self,
        icons_dir: Path | str = "icons",
        config: DetectionConfig = None
    ):
        """
        Initialize icon detector.
        
        Args:
            icons_dir: Directory containing icon templates
            config: Detection configuration (loads from config.ini if None)
        """
        self.icons_dir = Path(icons_dir)
        self.config = config or DetectionConfig.from_config_file()
        
        # Cache loaded templates
        self._template_cache: Dict[str, np.ndarray] = {}
        
        logger.debug(f"IconDetector initialized with thresholds: "
                    f"chapter={self.config.chapter_threshold}, "
                    f"icon={self.config.icon_threshold}")
    
    def _load_template(self, icon_name: str) -> Optional[np.ndarray]:
        """Load and cache template image."""
        if icon_name in self._template_cache:
            return self._template_cache[icon_name]
        
        icon_path = self.icons_dir / icon_name
        if not icon_path.exists():
            logger.debug(f"Template not found: {icon_path}")
            return None
        
        template = cv2.imread(str(icon_path), cv2.IMREAD_GRAYSCALE)
        if template is not None:
            self._template_cache[icon_name] = template
        
        return template
    
    def _get_threshold_for_icon(self, icon_name: str) -> float:
        """Get appropriate threshold for icon type."""
        if 'chapter_' in icon_name:
            return self.config.chapter_threshold
        elif icon_name == 'dungeon_page.png':
            return self.config.dungeon_page_threshold
        elif 'floor' in icon_name:
            return self.config.floor_threshold
        elif icon_name in ('fighting.png', 'back_button.png'):
            return self.config.fighting_threshold
        return self.config.icon_threshold
    
    def detect_icon(
        self,
        screen: np.ndarray,
        icon_name: str,
        use_multi_scale: bool = False
    ) -> DetectionResult:
        """
        Detect an icon on screen using template matching.
        
        Args:
            screen: Screenshot as numpy array (BGR or grayscale)
            icon_name: Name of icon file to detect
            use_multi_scale: Whether to try multiple scales
            
        Returns:
            DetectionResult with position and confidence
        """
        template = self._load_template(icon_name)
        if template is None:
            return DetectionResult(
                found=False,
                icon_name=icon_name,
                position=(0, 0),
                confidence=0.0,
                method='template'
            )
        
        # Convert to grayscale if needed
        if len(screen.shape) == 3:
            screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        else:
            screen_gray = screen
        
        # Apply Gaussian blur for noise reduction
        screen_blur = cv2.GaussianBlur(screen_gray, (3, 3), 0)
        template_blur = cv2.GaussianBlur(template, (3, 3), 0)
        
        threshold = self._get_threshold_for_icon(icon_name)
        scales = self.config.chapter_scales if use_multi_scale else [1.0]
        
        best_result = DetectionResult(
            found=False,
            icon_name=icon_name,
            position=(0, 0),
            confidence=0.0,
            method='template'
        )
        
        for scale in scales:
            if scale != 1.0:
                new_w = max(1, int(template_blur.shape[1] * scale))
                new_h = max(1, int(template_blur.shape[0] * scale))
                scaled_template = cv2.resize(
                    template_blur, (new_w, new_h), 
                    interpolation=cv2.INTER_AREA
                )
            else:
                scaled_template = template_blur
            
            # Check template fits in screen
            if (screen_blur.shape[0] < scaled_template.shape[0] or
                screen_blur.shape[1] < scaled_template.shape[1]):
                continue
            
            result = cv2.matchTemplate(
                screen_blur, scaled_template, cv2.TM_CCOEFF_NORMED
            )
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            if max_val > best_result.confidence:
                best_result = DetectionResult(
                    found=max_val >= threshold,
                    icon_name=icon_name,
                    position=max_loc,
                    confidence=float(max_val),
                    method='template'
                )
        
        # Relax threshold slightly for chapter icons near threshold
        if ('chapter_' in icon_name and 
            not best_result.found and 
            best_result.confidence >= (threshold - 0.05)):
            best_result = DetectionResult(
                found=True,
                icon_name=icon_name,
                position=best_result.position,
                confidence=best_result.confidence,
                method='template'
            )
        
        return best_result
    
    def detect_chapter_number(
        self,
        screen: np.ndarray,
        target_chapter: int,
        search_region: Tuple[int, int, int, int] = None
    ) -> DetectionResult:
        """
        Detect chapter by number using OCR (language-neutral).
        
        This method extracts the chapter number directly from the screen,
        making it work regardless of game language.
        
        Args:
            screen: Screenshot as numpy array
            target_chapter: Chapter number to find (1-6)
            search_region: Optional (x, y, width, height) to limit search
            
        Returns:
            DetectionResult with chapter position
        """
        # First try template matching
        icon_name = f'chapter_{target_chapter}.png'
        template_result = self.detect_icon(screen, icon_name, use_multi_scale=True)
        
        if template_result.found:
            logger.debug(f"Chapter {target_chapter} found via template: {template_result.confidence:.2f}")
            return template_result
        
        # Fallback to OCR if enabled
        if not self.config.use_ocr_fallback:
            return template_result
        
        ocr_result = self._detect_number_ocr(screen, target_chapter, search_region)
        if ocr_result.found:
            logger.info(f"Chapter {target_chapter} found via OCR: {ocr_result.confidence:.2f}")
            return ocr_result
        
        # Return template result (even if not found) for debugging
        return template_result
    
    def _detect_number_ocr(
        self,
        screen: np.ndarray,
        target_number: int,
        search_region: Tuple[int, int, int, int] = None
    ) -> DetectionResult:
        """
        Detect a number on screen using OCR.
        
        Args:
            screen: Screenshot
            target_number: Number to find
            search_region: Region to search (x, y, w, h)
            
        Returns:
            DetectionResult
        """
        reader = _get_ocr_reader()
        if reader is None:
            return DetectionResult(
                found=False,
                icon_name=f'number_{target_number}',
                position=(0, 0),
                confidence=0.0,
                method='ocr'
            )
        
        # Crop to search region if specified
        if search_region:
            x, y, w, h = search_region
            roi = screen[y:y+h, x:x+w]
            offset = (x, y)
        else:
            roi = screen
            offset = (0, 0)
        
        # Preprocess for OCR
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi
        
        # Enhance contrast
        gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
        
        try:
            # Run OCR - only detect numbers
            results = reader.readtext(
                gray,
                allowlist='0123456789',
                paragraph=False
            )
            
            target_str = str(target_number)
            
            for (bbox, text, confidence) in results:
                # Clean text
                text = text.strip()
                
                if target_str in text and confidence >= self.config.ocr_confidence_threshold:
                    # Calculate center position
                    x_coords = [p[0] for p in bbox]
                    y_coords = [p[1] for p in bbox]
                    center_x = int(sum(x_coords) / len(x_coords)) + offset[0]
                    center_y = int(sum(y_coords) / len(y_coords)) + offset[1]
                    
                    return DetectionResult(
                        found=True,
                        icon_name=f'chapter_{target_number}',
                        position=(center_x, center_y),
                        confidence=float(confidence),
                        method='ocr'
                    )
            
        except Exception as e:
            logger.warning(f"OCR detection failed: {e}")
        
        return DetectionResult(
            found=False,
            icon_name=f'chapter_{target_number}',
            position=(0, 0),
            confidence=0.0,
            method='ocr'
        )
    
    def detect_floor_number(
        self,
        screen: np.ndarray,
        target_floor: int
    ) -> DetectionResult:
        """
        Detect floor number on screen.
        
        Tries template matching first, then OCR fallback.
        
        Args:
            screen: Screenshot
            target_floor: Floor number to find (1-12+)
            
        Returns:
            DetectionResult
        """
        # Try template first
        icon_name = f'floor{target_floor}.png'
        template_result = self.detect_icon(screen, icon_name)
        
        if template_result.found:
            return template_result
        
        # Fallback to OCR
        if self.config.use_ocr_fallback:
            return self._detect_number_ocr(screen, target_floor)
        
        return template_result
    
    def detect_all_chapters(
        self,
        screen: np.ndarray
    ) -> List[DetectionResult]:
        """
        Detect all visible chapter icons on screen.
        
        Args:
            screen: Screenshot
            
        Returns:
            List of detection results for found chapters
        """
        results = []
        
        for chapter_num in range(1, 7):  # Chapters 1-6
            result = self.detect_chapter_number(screen, chapter_num)
            if result.found:
                results.append(result)
        
        return results
    
    def detect_icons(
        self,
        screen: np.ndarray,
        icon_list: List[str] = None,
        available_only: bool = False
    ) -> List[DetectionResult]:
        """
        Detect multiple icons on screen.
        
        Args:
            screen: Screenshot
            icon_list: List of icon names to check (None = all in icons/)
            available_only: Only return found icons
            
        Returns:
            List of detection results
        """
        if icon_list is None:
            icon_list = [f for f in os.listdir(self.icons_dir) 
                        if f.endswith('.png')]
        
        results = []
        for icon_name in icon_list:
            use_multi_scale = 'chapter_' in icon_name
            result = self.detect_icon(screen, icon_name, use_multi_scale)
            
            if not available_only or result.found:
                results.append(result)
        
        return results


# Convenience function for backward compatibility
def get_icon_detector(config: DetectionConfig = None) -> IconDetector:
    """Get a configured icon detector instance."""
    return IconDetector(config=config)
