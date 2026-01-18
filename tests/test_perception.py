"""Tests for rush_bot.perception module."""

from __future__ import annotations

from pathlib import Path

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
