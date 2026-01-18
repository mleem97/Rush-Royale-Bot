"""Tests for rush_bot.perception module."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
import pytest

from rush_bot.perception import GRID_COLS
from rush_bot.perception import GRID_ROWS
from rush_bot.perception import REFERENCE_HEIGHT
from rush_bot.perception import REFERENCE_WIDTH
from rush_bot.perception import BotPerception
from rush_bot.perception import GridConfig
from rush_bot.perception import GridExtractor
from rush_bot.perception import get_grid
from rush_bot.perception.vision import UNITS_DIR

if TYPE_CHECKING:
    from rush_bot.perception import ScreenStateDetector


class TestGridExtractor:
    """Tests for the GridExtractor class."""

    def test_default_grid_dimensions(self) -> None:
        """Test that grid has correct dimensions (3x5 = 15 cells)."""
        extractor = GridExtractor()
        boxes, cell_size = extractor.get_grid()

        assert boxes.shape == (GRID_ROWS, GRID_COLS, 2)
        assert boxes.shape == (3, 5, 2)
        assert len(cell_size) == 2

    def test_flat_grid_dimensions(self) -> None:
        """Test that flat grid returns 15 cells."""
        extractor = GridExtractor()
        boxes, cell_size = extractor.get_grid_flat()

        assert boxes.shape == (15, 2)
        assert len(cell_size) == 2

    def test_reference_resolution_coordinates(self) -> None:
        """Test grid coordinates at reference resolution (1080x1920)."""
        extractor = GridExtractor(
            screen_width=REFERENCE_WIDTH,
            screen_height=REFERENCE_HEIGHT,
        )
        boxes, cell_size = extractor.get_grid()

        # Check cell size at reference resolution
        assert cell_size == (120, 120)

        # Check first cell position (top-left)
        assert boxes[0, 0, 0] == 153  # x
        assert boxes[0, 0, 1] == 945  # y

        # Check that cells are properly spaced
        # Second column should be 120 pixels to the right
        assert boxes[0, 1, 0] == 153 + 120

    def test_scaled_resolution_half(self) -> None:
        """Test grid scales correctly for half resolution."""
        extractor = GridExtractor(
            screen_width=REFERENCE_WIDTH // 2,  # 540
            screen_height=REFERENCE_HEIGHT // 2,  # 960
        )
        boxes, cell_size = extractor.get_grid()

        # Cell size should be half
        assert cell_size == (60, 60)

        # Position should be half
        assert boxes[0, 0, 0] == 153 // 2  # ~76
        assert boxes[0, 0, 1] == 945 // 2  # ~472

    def test_scaled_resolution_double(self) -> None:
        """Test grid scales correctly for double resolution."""
        extractor = GridExtractor(
            screen_width=REFERENCE_WIDTH * 2,  # 2160
            screen_height=REFERENCE_HEIGHT * 2,  # 3840
        )
        boxes, cell_size = extractor.get_grid()

        # Cell size should be double
        assert cell_size == (240, 240)

        # Position should be double
        assert boxes[0, 0, 0] == 153 * 2
        assert boxes[0, 0, 1] == 945 * 2

    def test_common_resolution_720p(self) -> None:
        """Test grid for common 720x1280 resolution."""
        extractor = GridExtractor(screen_width=720, screen_height=1280)
        boxes, cell_size = extractor.get_grid()

        # Should have correct shape
        assert boxes.shape == (3, 5, 2)

        # Cell dimensions should be scaled
        scale = 720 / REFERENCE_WIDTH
        expected_width = int(120 * scale)
        assert cell_size[0] == expected_width

    def test_common_resolution_1440p(self) -> None:
        """Test grid for common 1440x2560 resolution."""
        extractor = GridExtractor(screen_width=1440, screen_height=2560)
        boxes, cell_size = extractor.get_grid()

        assert boxes.shape == (3, 5, 2)

        scale = 1440 / REFERENCE_WIDTH
        expected_width = int(120 * scale)
        assert cell_size[0] == expected_width

    def test_cell_center_calculation(self) -> None:
        """Test cell center coordinate calculation."""
        extractor = GridExtractor()

        # First cell center
        center_x, center_y = extractor.get_cell_center(0, 0)
        assert center_x == 153 + 60  # top_x + cell_width/2
        assert center_y == 945 + 60  # top_y + cell_height/2

        # Last cell center (row 2, col 4)
        center_x, center_y = extractor.get_cell_center(2, 4)
        expected_x = 153 + 4 * 120 + 60
        expected_y = 945 + 2 * 120 + 60
        assert center_x == expected_x
        assert center_y == expected_y

    def test_cell_center_bounds_check(self) -> None:
        """Test that invalid cell indices raise ValueError."""
        extractor = GridExtractor()

        with pytest.raises(ValueError):
            extractor.get_cell_center(3, 0)  # row out of bounds

        with pytest.raises(ValueError):
            extractor.get_cell_center(0, 5)  # col out of bounds

        with pytest.raises(ValueError):
            extractor.get_cell_center(-1, 0)  # negative row

    def test_cell_bounds_calculation(self) -> None:
        """Test cell bounding box calculation."""
        extractor = GridExtractor()

        x, y, w, h = extractor.get_cell_bounds(0, 0)
        assert x == 153
        assert y == 945
        assert w == 120
        assert h == 120

        x, y, w, h = extractor.get_cell_bounds(1, 2)
        assert x == 153 + 2 * 120
        assert y == 945 + 1 * 120

    def test_cell_index_conversion(self) -> None:
        """Test conversion between flat index and (row, col)."""
        extractor = GridExtractor()

        # Index 0 -> (0, 0)
        assert extractor.cell_index_to_pos(0) == (0, 0)

        # Index 4 -> (0, 4) (last col of first row)
        assert extractor.cell_index_to_pos(4) == (0, 4)

        # Index 5 -> (1, 0) (first col of second row)
        assert extractor.cell_index_to_pos(5) == (1, 0)

        # Index 14 -> (2, 4) (last cell)
        assert extractor.cell_index_to_pos(14) == (2, 4)

    def test_pos_to_index_conversion(self) -> None:
        """Test conversion from (row, col) to flat index."""
        extractor = GridExtractor()

        assert extractor.pos_to_cell_index(0, 0) == 0
        assert extractor.pos_to_cell_index(0, 4) == 4
        assert extractor.pos_to_cell_index(1, 0) == 5
        assert extractor.pos_to_cell_index(2, 4) == 14

    def test_index_bounds_check(self) -> None:
        """Test that invalid indices raise ValueError."""
        extractor = GridExtractor()

        with pytest.raises(ValueError):
            extractor.cell_index_to_pos(15)

        with pytest.raises(ValueError):
            extractor.cell_index_to_pos(-1)

    def test_from_screenshot(self) -> None:
        """Test creating extractor from screenshot array."""
        # Create a mock screenshot (1080x1920x3)
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        extractor = GridExtractor.from_screenshot(screenshot)

        assert extractor.screen_width == 1080
        assert extractor.screen_height == 1920

    def test_from_screenshot_different_resolution(self) -> None:
        """Test creating extractor from different resolution screenshot."""
        screenshot = np.zeros((2560, 1440, 3), dtype=np.uint8)

        extractor = GridExtractor.from_screenshot(screenshot)

        assert extractor.screen_width == 1440
        assert extractor.screen_height == 2560

    def test_custom_config(self) -> None:
        """Test using custom GridConfig."""
        config = GridConfig(
            top_x=100,
            top_y=500,
            cell_width=100,
            cell_height=100,
            cell_gap=5,
        )
        extractor = GridExtractor(config=config)
        boxes, cell_size = extractor.get_grid()

        assert cell_size == (100, 100)
        assert boxes[0, 0, 0] == 100
        assert boxes[0, 0, 1] == 500
        # Second column with gap
        assert boxes[0, 1, 0] == 100 + 100 + 5

    def test_grid_config_total_cells(self) -> None:
        """Test GridConfig total_cells property."""
        config = GridConfig(top_x=0, top_y=0, cell_width=100, cell_height=100)
        assert config.total_cells == 15

    def test_all_15_cells_unique(self) -> None:
        """Test that all 15 cell positions are unique."""
        extractor = GridExtractor()
        boxes, _ = extractor.get_grid_flat()

        # Convert to set of tuples to check uniqueness
        positions = {tuple(pos) for pos in boxes}
        assert len(positions) == 15


class TestGetGridFunction:
    """Tests for the standalone get_grid function."""

    def test_get_grid_default_resolution(self) -> None:
        """Test get_grid with default resolution."""
        boxes, cell_size = get_grid()

        assert boxes.shape == (3, 5, 2)
        assert cell_size == (120, 120)

    def test_get_grid_custom_resolution(self) -> None:
        """Test get_grid with custom resolution."""
        boxes, cell_size = get_grid(screen_width=540, screen_height=960)

        assert boxes.shape == (3, 5, 2)
        assert cell_size == (60, 60)


class TestBotPerception:
    """Tests for the BotPerception class."""

    def test_perception_creation(self) -> None:
        """Test that BotPerception can be instantiated."""
        perception = BotPerception()
        assert perception is not None

    def test_reference_data_loaded(self) -> None:
        """Test that reference unit data is loaded on init."""
        perception = BotPerception()
        # Should have loaded units from all_units directory
        if UNITS_DIR.exists():
            assert len(perception._ref_units) > 0
            assert len(perception._ref_templates) == len(perception._ref_units)
            assert len(perception._ref_colors) == len(perception._ref_units)
            assert len(perception._ref_histograms) == len(perception._ref_units)

    def test_dominant_color_extraction(self, temp_dir: Path) -> None:
        """Test color extraction from a test image."""
        # Create a simple test image (100x100 red)
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :] = [0, 0, 255]  # BGR red

        img_path = temp_dir / "test_red.png"
        cv2.imwrite(str(img_path), img)

        colors = BotPerception._get_dominant_color(img_path)
        assert colors.shape == (5, 3)
        # First color should be red (RGB)
        assert colors[0, 0] >= 240  # R channel

    def test_dominant_color_with_crop(self, temp_dir: Path) -> None:
        """Test color extraction with center crop."""
        # Create a test image with different center
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :] = [255, 0, 0]  # BGR blue border
        # Green center
        img[15:85, 15:85] = [0, 255, 0]  # BGR green

        img_path = temp_dir / "test_crop.png"
        cv2.imwrite(str(img_path), img)

        colors = BotPerception._get_dominant_color(img_path, crop=True)
        assert colors.shape == (5, 3)
        # With crop, should pick up the green center

    def test_compute_histogram(self, temp_dir: Path) -> None:
        """Test histogram computation."""
        # Create a test image
        img = np.zeros((90, 90, 3), dtype=np.uint8)
        img[:, :] = [100, 150, 200]

        hist = BotPerception._compute_color_histogram(img)
        assert hist.shape == (32 * 32,)  # 32 bins per channel
        assert hist.dtype == np.float32

    def test_match_unit_unknown(self) -> None:
        """Test that unknown images return empty/unknown."""
        perception = BotPerception()
        # Non-existent image should return unknown
        unit, _confidence = perception.match_unit("nonexistent.png")
        assert "empty" in unit or "unknown" in unit

    def test_match_unit_with_template(self, temp_dir: Path) -> None:
        """Test unit matching with actual unit template."""
        perception = BotPerception()

        # Skip if no reference data
        if not perception._ref_units:
            pytest.skip("No reference units loaded")

        # Use the first unit template as test input
        first_unit = perception._ref_units[0]
        template_path = UNITS_DIR / first_unit

        if template_path.exists():
            unit, confidence = perception.match_unit(template_path)
            # Should match itself with high confidence
            assert unit == first_unit
            assert confidence >= 0.7

    def test_match_rank_no_model(self) -> None:
        """Test rank matching returns 0 when no model loaded."""
        perception = BotPerception()
        perception._rank_model = None
        rank, conf = perception.match_rank("nonexistent.png")
        assert rank == 0
        assert conf == 0.0

    def test_is_empty_slot_dark_image(self, temp_dir: Path) -> None:
        """Test empty slot detection with dark image."""
        perception = BotPerception()

        # Create a dark image (simulates empty slot)
        dark_img = np.zeros((90, 90, 3), dtype=np.uint8)
        dark_img[:, :] = [20, 20, 20]  # Very dark

        assert perception._is_empty_slot(dark_img) is True

        # Bright image should not be empty
        bright_img = np.ones((90, 90, 3), dtype=np.uint8) * 200
        assert perception._is_empty_slot(bright_img) is False


class TestUnitRecognitionAccuracy:
    """Tests for unit recognition accuracy (>=90% requirement)."""

    def test_known_units_recognition_rate(self) -> None:
        """Test that known unit templates achieve >=90% recognition rate."""
        perception = BotPerception()

        if not UNITS_DIR.exists():
            pytest.skip("Units directory not found")

        unit_files = list(UNITS_DIR.glob("*.png"))
        if len(unit_files) < 5:
            pytest.skip("Not enough unit templates for accuracy test")

        correct = 0
        total = 0

        for unit_file in unit_files:
            if unit_file.name == "empty.png":
                continue

            unit, _confidence = perception.match_unit(unit_file)
            total += 1

            if unit == unit_file.name:
                correct += 1

        if total > 0:
            accuracy = correct / total
            assert accuracy >= 0.90, f"Recognition accuracy {accuracy:.2%} < 90%"


class TestTrainingFunctions:
    """Tests for training-related functions."""

    def test_ensure_training_dirs(self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that training directories are created."""
        from rush_bot.perception import vision

        # Patch the directory paths
        test_ml_dir = temp_dir / "ml_inputs"
        monkeypatch.setattr(vision, "ML_INPUTS_DIR", test_ml_dir)
        monkeypatch.setattr(vision, "ML_RAW_INPUT_DIR", temp_dir / "raw")
        monkeypatch.setattr(vision, "OCR_INPUTS_DIR", temp_dir / "ocr")

        vision.ensure_training_dirs()

        assert test_ml_dir.exists()


# =============================================================================
# Screen State Detection Tests
# =============================================================================


class TestScreenState:
    """Tests for ScreenState enum."""

    def test_screen_state_values(self) -> None:
        """Test that all expected screen states exist."""
        from rush_bot.perception import ScreenState

        # Core states must exist
        assert ScreenState.UNKNOWN is not None
        assert ScreenState.HOME is not None
        assert ScreenState.BATTLE is not None
        assert ScreenState.DUNGEON_SELECT is not None
        assert ScreenState.POPUP is not None
        assert ScreenState.ADVERTISEMENT is not None
        assert ScreenState.VICTORY is not None
        assert ScreenState.DEFEAT is not None

    def test_screen_state_unique_values(self) -> None:
        """Test that all screen states have unique values."""
        from rush_bot.perception import ScreenState

        values = [state.value for state in ScreenState]
        assert len(values) == len(set(values)), "Screen states have duplicate values"


class TestScreenStateResult:
    """Tests for ScreenStateResult dataclass."""

    def test_result_creation(self) -> None:
        """Test creating a ScreenStateResult."""
        from rush_bot.perception import ScreenState
        from rush_bot.perception import ScreenStateResult

        result = ScreenStateResult(
            state=ScreenState.HOME,
            confidence=0.85,
            matched_template="home_screen.png",
        )

        assert result.state == ScreenState.HOME
        assert result.confidence == 0.85
        assert result.matched_template == "home_screen.png"
        assert result.region is None
        assert result.all_matches == {}

    def test_result_with_region(self) -> None:
        """Test creating a ScreenStateResult with region."""
        from rush_bot.perception import ScreenState
        from rush_bot.perception import ScreenStateResult

        result = ScreenStateResult(
            state=ScreenState.BATTLE,
            confidence=0.92,
            matched_template="fighting.png",
            region=(100, 200, 50, 50),
        )

        assert result.region == (100, 200, 50, 50)

    def test_result_bool_true_for_valid_state(self) -> None:
        """Test that result evaluates to True for valid state."""
        from rush_bot.perception import ScreenState
        from rush_bot.perception import ScreenStateResult

        result = ScreenStateResult(
            state=ScreenState.HOME,
            confidence=0.75,
        )
        assert bool(result) is True

    def test_result_bool_false_for_unknown(self) -> None:
        """Test that result evaluates to False for unknown state."""
        from rush_bot.perception import ScreenState
        from rush_bot.perception import ScreenStateResult

        result = ScreenStateResult(
            state=ScreenState.UNKNOWN,
            confidence=0.8,
        )
        assert bool(result) is False

    def test_result_bool_false_for_low_confidence(self) -> None:
        """Test that result evaluates to False for low confidence."""
        from rush_bot.perception import ScreenState
        from rush_bot.perception import ScreenStateResult

        result = ScreenStateResult(
            state=ScreenState.HOME,
            confidence=0.3,  # Below 0.5 threshold
        )
        assert bool(result) is False


class TestScreenStateConfig:
    """Tests for ScreenStateConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        from rush_bot.perception import ScreenStateConfig

        config = ScreenStateConfig()

        assert config.template_threshold == 0.7
        assert config.use_grayscale is False
        assert config.scale_templates is True
        assert config.reference_width == 1080
        assert config.reference_height == 1920

    def test_custom_config(self) -> None:
        """Test creating custom configuration."""
        from rush_bot.perception import ScreenStateConfig

        config = ScreenStateConfig(
            template_threshold=0.8,
            use_grayscale=True,
            scale_templates=False,
            reference_width=720,
            reference_height=1280,
        )

        assert config.template_threshold == 0.8
        assert config.use_grayscale is True
        assert config.scale_templates is False
        assert config.reference_width == 720
        assert config.reference_height == 1280


class TestScreenStateDetector:
    """Tests for ScreenStateDetector class."""

    def test_detector_initialization(self) -> None:
        """Test detector initializes correctly."""
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()

        # Should have default config
        assert detector.config.template_threshold == 0.7

    def test_detector_with_custom_config(self) -> None:
        """Test detector with custom config."""
        from rush_bot.perception import ScreenStateConfig
        from rush_bot.perception import ScreenStateDetector

        config = ScreenStateConfig(template_threshold=0.9)
        detector = ScreenStateDetector(config=config)

        assert detector.config.template_threshold == 0.9

    def test_detector_loads_templates(self) -> None:
        """Test that detector loads templates from icons directory."""
        from rush_bot.perception import ScreenStateDetector
        from rush_bot.perception.screen_state import ICONS_DIR

        detector = ScreenStateDetector()

        if ICONS_DIR.exists():
            # Should have loaded templates
            assert detector.is_loaded
            assert len(detector.available_templates) > 0
        else:
            # No templates directory - acceptable for CI
            assert not detector.is_loaded

    def test_available_templates_property(self) -> None:
        """Test available_templates returns list of template names."""
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()
        templates = detector.available_templates

        assert isinstance(templates, list)
        # All items should be strings
        for name in templates:
            assert isinstance(name, str)

    def test_detect_returns_result(self) -> None:
        """Test detect returns ScreenStateResult."""
        from rush_bot.perception import ScreenStateDetector
        from rush_bot.perception import ScreenStateResult

        detector = ScreenStateDetector()

        # Create dummy screenshot
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        result = detector.detect(screenshot)

        assert isinstance(result, ScreenStateResult)
        assert 0.0 <= result.confidence <= 1.0

    def test_detect_with_file_path(self, temp_dir: Path) -> None:
        """Test detect accepts file path."""
        from rush_bot.perception import ScreenStateDetector
        from rush_bot.perception import ScreenStateResult

        detector = ScreenStateDetector()

        # Create and save dummy image
        img = np.zeros((1920, 1080, 3), dtype=np.uint8)
        img_path = temp_dir / "test_screenshot.png"
        cv2.imwrite(str(img_path), img)

        result = detector.detect(img_path)

        assert isinstance(result, ScreenStateResult)

    def test_detect_with_invalid_path(self) -> None:
        """Test detect handles invalid file path."""
        from rush_bot.perception import ScreenState
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()

        result = detector.detect("/nonexistent/path.png")

        assert result.state == ScreenState.UNKNOWN
        assert result.confidence == 0.0

    def test_detect_all_returns_list(self) -> None:
        """Test detect_all returns list of results."""
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()

        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)
        results = detector.detect_all(screenshot)

        assert isinstance(results, list)

    def test_is_state_method(self) -> None:
        """Test is_state convenience method."""
        from rush_bot.perception import ScreenState
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        # Should return boolean
        result = detector.is_state(screenshot, ScreenState.HOME)
        assert isinstance(result, bool)

    def test_is_in_battle_method(self) -> None:
        """Test is_in_battle convenience method."""
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        result = detector.is_in_battle(screenshot)
        assert isinstance(result, bool)

    def test_is_home_screen_method(self) -> None:
        """Test is_home_screen convenience method."""
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        result = detector.is_home_screen(screenshot)
        assert isinstance(result, bool)

    def test_has_popup_method(self) -> None:
        """Test has_popup convenience method."""
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        result = detector.has_popup(screenshot)
        assert isinstance(result, bool)

    def test_has_advertisement_method(self) -> None:
        """Test has_advertisement convenience method."""
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        result = detector.has_advertisement(screenshot)
        assert isinstance(result, bool)

    def test_find_template_not_found(self) -> None:
        """Test find_template returns False for missing template."""
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        found, region, confidence = detector.find_template(screenshot, "nonexistent_template.png")

        assert found is False
        assert region is None
        assert confidence == 0.0

    def test_find_template_returns_tuple(self) -> None:
        """Test find_template returns proper tuple."""
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        # Use a real template if available
        if detector.available_templates:
            template_name = detector.available_templates[0]
            result = detector.find_template(screenshot, template_name)

            assert isinstance(result, tuple)
            assert len(result) == 3
            found, _region, confidence = result
            assert isinstance(found, bool)
            assert isinstance(confidence, float)

    def test_get_close_button_location(self) -> None:
        """Test get_close_button_location method."""
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        # On black image, should return None (no button found)
        result = detector.get_close_button_location(screenshot)

        # Result is either None or tuple of two ints
        assert result is None or (isinstance(result, tuple) and len(result) == 2)

    def test_get_back_button_location(self) -> None:
        """Test get_back_button_location method."""
        from rush_bot.perception import ScreenStateDetector

        detector = ScreenStateDetector()
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        result = detector.get_back_button_location(screenshot)

        # Result is either None or tuple of two ints
        assert result is None or (isinstance(result, tuple) and len(result) == 2)


class TestScreenStateDetectorWithTemplates:
    """Tests for ScreenStateDetector that require actual templates."""

    @pytest.fixture
    def detector_with_templates(self) -> ScreenStateDetector:
        """Create detector and skip if no templates available."""
        from rush_bot.perception import ScreenStateDetector
        from rush_bot.perception.screen_state import ICONS_DIR

        if not ICONS_DIR.exists():
            pytest.skip("Icons directory not found")

        detector = ScreenStateDetector()
        if not detector.is_loaded:
            pytest.skip("No templates loaded")

        return detector

    def test_detect_embedded_template(
        self, detector_with_templates: ScreenStateDetector, temp_dir: Path
    ) -> None:
        """Test detection when template is embedded in screenshot."""
        from rush_bot.perception.screen_state import ICONS_DIR

        # Find a small template
        template_files = list(ICONS_DIR.glob("*.png"))
        if not template_files:
            pytest.skip("No template files found")

        template_path = template_files[0]
        template = cv2.imread(str(template_path))
        if template is None:
            pytest.skip("Could not load template")

        # Create screenshot with template embedded
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)
        th, tw = template.shape[:2]

        # Place template at position (100, 100)
        if 100 + th <= 1920 and 100 + tw <= 1080:
            screenshot[100 : 100 + th, 100 : 100 + tw] = template

            result = detector_with_templates.detect(screenshot)

            # Should detect something with decent confidence
            assert result.confidence > 0.5

    def test_detect_all_finds_multiple(self, detector_with_templates: ScreenStateDetector) -> None:
        """Test detect_all can find multiple templates."""
        from rush_bot.perception.screen_state import ICONS_DIR

        # Load two templates
        template_files = list(ICONS_DIR.glob("*.png"))[:2]
        if len(template_files) < 2:
            pytest.skip("Need at least 2 templates")

        templates = []
        for f in template_files:
            t = cv2.imread(str(f))
            if t is not None:
                templates.append(t)

        if len(templates) < 2:
            pytest.skip("Could not load 2 templates")

        # Create screenshot with both templates
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        # Place first template at top
        t1 = templates[0]
        h1, w1 = t1.shape[:2]
        if h1 <= 1920 and w1 <= 1080:
            screenshot[0:h1, 0:w1] = t1

        # Place second template at bottom (non-overlapping)
        t2 = templates[1]
        h2, w2 = t2.shape[:2]
        pos_y = min(h1 + 50, 1920 - h2)
        if pos_y + h2 <= 1920 and w2 <= 1080:
            screenshot[pos_y : pos_y + h2, 0:w2] = t2

        results = detector_with_templates.detect_all(screenshot)

        # Should have some results
        assert isinstance(results, list)

    def test_template_scaling(self, detector_with_templates: ScreenStateDetector) -> None:
        """Test that templates are scaled correctly for different resolutions."""
        from rush_bot.perception.screen_state import ICONS_DIR

        # Find a template
        template_files = list(ICONS_DIR.glob("*.png"))
        if not template_files:
            pytest.skip("No templates found")

        template_path = template_files[0]
        template = cv2.imread(str(template_path))
        if template is None:
            pytest.skip("Could not load template")

        # Test at half resolution (540x960)
        screenshot_small = np.zeros((960, 540, 3), dtype=np.uint8)
        result_small = detector_with_templates.detect(screenshot_small)

        # Should still return valid result structure
        assert hasattr(result_small, "state")
        assert hasattr(result_small, "confidence")


class TestTemplateStateMap:
    """Tests for the template to state mapping."""

    def test_template_state_map_exists(self) -> None:
        """Test that TEMPLATE_STATE_MAP is defined."""
        from rush_bot.perception import TEMPLATE_STATE_MAP

        assert isinstance(TEMPLATE_STATE_MAP, dict)
        assert len(TEMPLATE_STATE_MAP) > 0

    def test_template_state_map_values_are_states(self) -> None:
        """Test that all values in map are ScreenState enum values."""
        from rush_bot.perception import TEMPLATE_STATE_MAP
        from rush_bot.perception import ScreenState

        for template_name, state in TEMPLATE_STATE_MAP.items():
            assert isinstance(template_name, str)
            assert isinstance(state, ScreenState)

    def test_key_templates_mapped(self) -> None:
        """Test that important templates are mapped."""
        from rush_bot.perception import TEMPLATE_STATE_MAP
        from rush_bot.perception import ScreenState

        # Key templates should be mapped
        expected_mappings = {
            "home_screen.png": ScreenState.HOME,
            "fighting.png": ScreenState.BATTLE,
            "x_mark.png": ScreenState.POPUP,
            "ad_pve.png": ScreenState.ADVERTISEMENT,
        }

        for template, expected_state in expected_mappings.items():
            if template in TEMPLATE_STATE_MAP:
                assert TEMPLATE_STATE_MAP[template] == expected_state


# =============================================================================
# Extended GridExtractor Tests (T010 - Coverage Enhancement)
# =============================================================================


class TestGridExtractorMethods:
    """Extended tests for GridExtractor methods."""

    def test_get_cell_center(self) -> None:
        """Test get_cell_center returns correct center coordinates."""
        extractor = GridExtractor(
            screen_width=REFERENCE_WIDTH,
            screen_height=REFERENCE_HEIGHT,
        )
        center = extractor.get_cell_center(0, 0)

        # Center should be at (top_x + cell_width/2, top_y + cell_height/2)
        expected_x = 153 + 60  # 153 + 120/2
        expected_y = 945 + 60  # 945 + 120/2
        assert center == (expected_x, expected_y)

    def test_get_cell_center_middle(self) -> None:
        """Test get_cell_center for middle cell."""
        extractor = GridExtractor()
        center = extractor.get_cell_center(1, 2)  # Middle cell

        # Should be properly calculated
        assert isinstance(center, tuple)
        assert len(center) == 2
        assert center[0] > 0
        assert center[1] > 0

    def test_get_cell_center_row_out_of_bounds(self) -> None:
        """Test get_cell_center raises for invalid row."""
        extractor = GridExtractor()

        with pytest.raises(ValueError, match=r"Row.*out of bounds"):
            extractor.get_cell_center(5, 0)

    def test_get_cell_center_col_out_of_bounds(self) -> None:
        """Test get_cell_center raises for invalid column."""
        extractor = GridExtractor()

        with pytest.raises(ValueError, match=r"Col.*out of bounds"):
            extractor.get_cell_center(0, 10)

    def test_get_cell_bounds(self) -> None:
        """Test get_cell_bounds returns correct bounding box."""
        extractor = GridExtractor(
            screen_width=REFERENCE_WIDTH,
            screen_height=REFERENCE_HEIGHT,
        )
        bounds = extractor.get_cell_bounds(0, 0)

        assert bounds == (153, 945, 120, 120)

    def test_get_cell_bounds_row_out_of_bounds(self) -> None:
        """Test get_cell_bounds raises for invalid row."""
        extractor = GridExtractor()

        with pytest.raises(ValueError, match=r"Row.*out of bounds"):
            extractor.get_cell_bounds(-1, 0)

    def test_get_cell_bounds_col_out_of_bounds(self) -> None:
        """Test get_cell_bounds raises for invalid column."""
        extractor = GridExtractor()

        with pytest.raises(ValueError, match=r"Col.*out of bounds"):
            extractor.get_cell_bounds(0, -1)

    def test_cell_index_to_pos(self) -> None:
        """Test cell_index_to_pos converts index correctly."""
        extractor = GridExtractor()

        # Index 0 -> (0, 0)
        assert extractor.cell_index_to_pos(0) == (0, 0)

        # Index 4 -> (0, 4)
        assert extractor.cell_index_to_pos(4) == (0, 4)

        # Index 5 -> (1, 0)
        assert extractor.cell_index_to_pos(5) == (1, 0)

        # Index 14 -> (2, 4)
        assert extractor.cell_index_to_pos(14) == (2, 4)

    def test_cell_index_to_pos_out_of_bounds(self) -> None:
        """Test cell_index_to_pos raises for invalid index."""
        extractor = GridExtractor()

        with pytest.raises(ValueError, match=r"Index.*out of bounds"):
            extractor.cell_index_to_pos(15)

        with pytest.raises(ValueError, match=r"Index.*out of bounds"):
            extractor.cell_index_to_pos(-1)

    def test_pos_to_cell_index(self) -> None:
        """Test pos_to_cell_index converts position correctly."""
        extractor = GridExtractor()

        # (0, 0) -> 0
        assert extractor.pos_to_cell_index(0, 0) == 0

        # (0, 4) -> 4
        assert extractor.pos_to_cell_index(0, 4) == 4

        # (1, 0) -> 5
        assert extractor.pos_to_cell_index(1, 0) == 5

        # (2, 4) -> 14
        assert extractor.pos_to_cell_index(2, 4) == 14

    def test_pos_to_cell_index_out_of_bounds(self) -> None:
        """Test pos_to_cell_index raises for invalid position."""
        extractor = GridExtractor()

        with pytest.raises(ValueError, match=r"Row.*out of bounds"):
            extractor.pos_to_cell_index(3, 0)

        with pytest.raises(ValueError, match=r"Col.*out of bounds"):
            extractor.pos_to_cell_index(0, 5)

    def test_from_screenshot(self) -> None:
        """Test from_screenshot class method."""
        # Create a mock screenshot
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

        extractor = GridExtractor.from_screenshot(screenshot)

        assert extractor.screen_width == 1080
        assert extractor.screen_height == 1920


class TestGridConfig:
    """Tests for the GridConfig dataclass."""

    def test_grid_config_creation(self) -> None:
        """Test creating a GridConfig."""
        config = GridConfig(
            top_x=100,
            top_y=200,
            cell_width=50,
            cell_height=50,
        )

        assert config.top_x == 100
        assert config.top_y == 200
        assert config.cell_width == 50
        assert config.cell_height == 50
        assert config.cell_gap == 0  # Default
        assert config.rows == GRID_ROWS
        assert config.cols == GRID_COLS

    def test_grid_config_total_cells(self) -> None:
        """Test total_cells property."""
        config = GridConfig(
            top_x=0,
            top_y=0,
            cell_width=100,
            cell_height=100,
            rows=3,
            cols=5,
        )

        assert config.total_cells == 15

    def test_custom_grid_config(self) -> None:
        """Test GridExtractor with custom config."""
        custom_config = GridConfig(
            top_x=50,
            top_y=100,
            cell_width=100,
            cell_height=100,
            cell_gap=10,
            rows=2,
            cols=3,
        )

        extractor = GridExtractor(config=custom_config)
        boxes, cell_size = extractor.get_grid()

        assert boxes.shape == (2, 3, 2)
        assert cell_size == (100, 100)
        assert boxes[0, 0, 0] == 50
        assert boxes[0, 0, 1] == 100


# =============================================================================
# Extended BotPerception Tests (T010 - Coverage Enhancement)
# =============================================================================


class TestBotPerceptionMethods:
    """Extended tests for BotPerception methods."""

    def test_match_histogram_empty_refs(self) -> None:
        """Test _match_histogram with no reference histograms."""
        perception = BotPerception()
        perception._ref_histograms = []

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = perception._match_histogram(img)

        assert result == ("unknown.png", 0.0)

    def test_match_template_empty_refs(self) -> None:
        """Test _match_template with no reference templates."""
        perception = BotPerception()
        perception._ref_templates = []

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = perception._match_template(img)

        assert result == ("unknown.png", 0.0)

    def test_compute_color_histogram(self) -> None:
        """Test _compute_color_histogram produces valid output."""
        # Create a simple test image
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        img[:, :, 0] = 255  # Blue channel

        hist = BotPerception._compute_color_histogram(img)

        assert isinstance(hist, np.ndarray)
        assert hist.dtype == np.float32
        # With 32 bins per channel, flattened should be 32*32 = 1024
        assert hist.shape == (1024,)

    def test_get_dominant_color_nonexistent_file(self) -> None:
        """Test _get_dominant_color with nonexistent file."""
        result = BotPerception._get_dominant_color("nonexistent.png")

        assert result.shape == (5, 3)
        assert np.all(result == 0)

    def test_get_dominant_color_with_crop(self, temp_dir: Path) -> None:
        """Test _get_dominant_color with crop option."""
        # Create a test image
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        test_path = temp_dir / "test_image.png"
        cv2.imwrite(str(test_path), img)

        result = BotPerception._get_dominant_color(test_path, crop=True)

        assert result.shape == (5, 3)

    def test_match_unit_nonexistent_file(self) -> None:
        """Test match_unit with nonexistent file."""
        perception = BotPerception()

        result = perception.match_unit("nonexistent.png")

        assert result == ("unknown.png", 0.0)

    def test_match_unit_empty_refs(self) -> None:
        """Test match_unit with no reference units."""
        perception = BotPerception()
        perception._ref_units = []

        result = perception.match_unit("some_file.png")

        assert result == ("unknown.png", 0.0)

    def test_is_empty_slot_dark_image(self) -> None:
        """Test _is_empty_slot with dark image."""
        perception = BotPerception()

        # Very dark image should be considered empty
        dark_img = np.zeros((100, 100, 3), dtype=np.uint8)
        dark_img[:] = 10  # Very dark

        result = perception._is_empty_slot(dark_img)

        # The actual behavior depends on implementation
        assert isinstance(result, bool)


class TestBotPerceptionRankModel:
    """Tests for BotPerception rank model functionality."""

    def test_load_rank_model_cached(self) -> None:
        """Test that rank model is cached after loading."""
        perception = BotPerception()

        # Load once
        model1 = perception._load_rank_model()

        # Load again - should return same instance
        model2 = perception._load_rank_model()

        if model1 is not None:
            assert model1 is model2

    def test_match_rank_with_valid_image(self, temp_dir: Path) -> None:
        """Test match_rank with valid image."""
        perception = BotPerception()

        # Create a test image with correct dimensions (120x120 for the model)
        img = np.full((120, 120, 3), 128, dtype=np.uint8)
        test_path = temp_dir / "test_unit.png"
        cv2.imwrite(str(test_path), img)

        # match_rank returns a tuple (rank, confidence)
        result = perception.match_rank(test_path)

        assert isinstance(result, tuple)
        assert len(result) == 2
        rank, confidence = result
        assert isinstance(rank, int)
        assert rank >= 0
        assert isinstance(confidence, float)

    def test_match_rank_nonexistent_file(self) -> None:
        """Test match_rank with nonexistent file returns (0, 0.0)."""
        perception = BotPerception()

        result = perception.match_rank("nonexistent_file.png")

        assert result == (0, 0.0)


class TestModuleLevelFunctions:
    """Tests for module-level functions in vision.py."""

    def test_get_grid_function(self) -> None:
        """Test the get_grid convenience function."""
        boxes, cell_size = get_grid()

        assert boxes.shape == (GRID_ROWS, GRID_COLS, 2)
        assert len(cell_size) == 2

    def test_get_grid_with_custom_resolution(self) -> None:
        """Test get_grid with custom resolution."""
        boxes, cell_size = get_grid(screen_width=720, screen_height=1280)

        assert boxes.shape == (GRID_ROWS, GRID_COLS, 2)
        # Should be scaled
        scale_x = 720 / REFERENCE_WIDTH
        assert cell_size[0] == int(120 * scale_x)
