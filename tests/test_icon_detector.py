"""
Tests for Icon Detector and Detection Config
Python 3.13 Compatible

Tests for Issue #10 fix (language-neutral chapter detection).
"""
from __future__ import annotations

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from Src.utils.icon_detector import (
    IconDetector,
    DetectionConfig,
    DetectionResult,
    get_icon_detector,
)


class TestDetectionConfig:
    """Tests for DetectionConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = DetectionConfig()
        
        assert config.icon_threshold == 0.78
        assert config.chapter_threshold == 0.70
        assert config.dungeon_page_threshold == 0.72
        assert config.floor_threshold == 0.75
        assert config.mse_threshold == 2000
        assert config.use_ocr_fallback is True
        assert config.ocr_confidence_threshold == 0.5
        assert config.chapter_scales == [0.9, 1.0, 1.1]
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = DetectionConfig(
            icon_threshold=0.85,
            chapter_threshold=0.80,
            use_ocr_fallback=False,
        )
        
        assert config.icon_threshold == 0.85
        assert config.chapter_threshold == 0.80
        assert config.use_ocr_fallback is False
    
    def test_from_config_file_missing(self):
        """Test loading from non-existent config file."""
        config = DetectionConfig.from_config_file(Path("/nonexistent/config.ini"))
        
        # Should use defaults
        assert config.icon_threshold == 0.78
        assert config.chapter_threshold == 0.70


class TestDetectionResult:
    """Tests for DetectionResult dataclass."""
    
    def test_found_result(self):
        """Test result when icon is found."""
        result = DetectionResult(
            found=True,
            icon_name='chapter_1.png',
            position=(100, 200),
            confidence=0.85,
            method='template'
        )
        
        assert result.found is True
        assert result.icon_name == 'chapter_1.png'
        assert result.position == (100, 200)
        assert result.confidence == 0.85
        assert result.method == 'template'
        assert bool(result) is True
    
    def test_not_found_result(self):
        """Test result when icon is not found."""
        result = DetectionResult(
            found=False,
            icon_name='chapter_5.png',
            position=(0, 0),
            confidence=0.45,
            method='ocr'
        )
        
        assert result.found is False
        assert bool(result) is False


class TestIconDetector:
    """Tests for IconDetector class."""
    
    @pytest.fixture
    def detector(self):
        """Create detector with test config."""
        config = DetectionConfig()
        return IconDetector(icons_dir="icons", config=config)
    
    @pytest.fixture
    def mock_screen(self):
        """Create mock screenshot."""
        # 900x1600 grayscale image
        return np.zeros((1600, 900), dtype=np.uint8)
    
    def test_initialization(self, detector):
        """Test detector initialization."""
        assert detector.icons_dir == Path("icons")
        assert detector.config is not None
        assert detector._template_cache == {}
    
    def test_get_threshold_for_icon(self, detector):
        """Test threshold selection for different icons."""
        assert detector._get_threshold_for_icon('chapter_1.png') == 0.70
        assert detector._get_threshold_for_icon('chapter_5.png') == 0.70
        assert detector._get_threshold_for_icon('dungeon_page.png') == 0.72
        assert detector._get_threshold_for_icon('fighting.png') == 0.75
        assert detector._get_threshold_for_icon('back_button.png') == 0.75
        assert detector._get_threshold_for_icon('home_screen.png') == 0.78
    
    def test_detect_icon_template_not_found(self, detector, mock_screen):
        """Test detection when template doesn't exist."""
        result = detector.detect_icon(mock_screen, 'nonexistent_icon.png')
        
        assert result.found is False
        assert result.confidence == 0.0
        assert result.method == 'template'
    
    def test_detect_chapter_number_no_ocr(self, detector, mock_screen):
        """Test chapter detection without OCR fallback."""
        detector.config.use_ocr_fallback = False
        
        result = detector.detect_chapter_number(mock_screen, 1)
        
        # Should fail template matching on blank screen
        assert result.method == 'template'
    
    def test_get_icon_detector(self):
        """Test convenience function."""
        detector = get_icon_detector()
        
        assert isinstance(detector, IconDetector)
        assert detector.config is not None


class TestIconDetectorWithRealIcons:
    """Tests that use real icon files if available."""
    
    @pytest.fixture
    def detector(self):
        """Create detector with real icons dir."""
        icons_path = Path("icons")
        if not icons_path.exists():
            pytest.skip("Icons directory not found")
        return IconDetector(icons_dir=icons_path)
    
    def test_load_template(self, detector):
        """Test template loading."""
        # Should work with any existing icon
        icon_files = list(detector.icons_dir.glob("*.png"))
        if not icon_files:
            pytest.skip("No icon files found")
        
        template = detector._load_template(icon_files[0].name)
        
        assert template is not None
        assert len(template.shape) == 2  # Grayscale
    
    def test_template_caching(self, detector):
        """Test template caching."""
        icon_files = list(detector.icons_dir.glob("*.png"))
        if not icon_files:
            pytest.skip("No icon files found")
        
        icon_name = icon_files[0].name
        
        # First load
        template1 = detector._load_template(icon_name)
        # Second load (should be cached)
        template2 = detector._load_template(icon_name)
        
        assert template1 is template2  # Same object
        assert icon_name in detector._template_cache


class TestOCRIntegration:
    """Tests for OCR integration."""
    
    @pytest.fixture
    def detector(self):
        """Create detector with OCR enabled."""
        config = DetectionConfig(use_ocr_fallback=True)
        return IconDetector(config=config)
    
    def test_ocr_fallback_disabled(self, detector):
        """Test OCR fallback can be disabled."""
        detector.config.use_ocr_fallback = False
        
        # Create empty image
        screen = np.zeros((100, 100, 3), dtype=np.uint8)
        
        result = detector.detect_chapter_number(screen, 1)
        
        # Should only use template method
        assert result.method == 'template'


class TestBotPerceptionIntegration:
    """Tests for bot_perception.py modernization."""
    
    def test_config_loading(self):
        """Test config loading functions."""
        from Src.bot_perception import _load_config, _get_threshold
        
        config = _load_config()
        assert config is not None
        
        # Should return default if not in config
        threshold = _get_threshold('nonexistent_key', 0.99)
        assert threshold == 0.99
    
    def test_match_rank_function_exists(self):
        """Test match_rank function is available."""
        from Src.bot_perception import match_rank
        
        # Should be callable
        assert callable(match_rank)
    
    def test_model_cache(self):
        """Test model caching."""
        from Src.bot_perception import _model_cache
        
        assert isinstance(_model_cache, dict)
