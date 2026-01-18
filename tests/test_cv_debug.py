"""Tests for CV Debug Mode."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import numpy as np
import pytest

from rush_bot.perception.cv_debug import CVDebugFrame
from rush_bot.perception.cv_debug import CVDebugLevel
from rush_bot.perception.cv_debug import CVDebugMode
from rush_bot.perception.cv_debug import DetectionResult
from rush_bot.perception.cv_debug import MergeCandidate
from rush_bot.perception.cv_debug import PageContext
from rush_bot.perception.cv_debug import run_cv_debug_on_screenshot
from rush_bot.perception.screen_state import ScreenState


class TestDetectionResult:
    """Tests for DetectionResult dataclass."""

    def test_detection_result_creation(self) -> None:
        """Test basic detection result creation."""
        det = DetectionResult(
            entity_type="unit",
            name="demon_hunter",
            confidence=0.95,
            method="histogram",
        )
        assert det.entity_type == "unit"
        assert det.name == "demon_hunter"
        assert det.confidence == 0.95
        assert det.method == "histogram"

    def test_detection_result_with_position(self) -> None:
        """Test detection result with position."""
        det = DetectionResult(
            entity_type="icon",
            name="pvp_button",
            confidence=0.88,
            method="template",
            position=(540, 960),
        )
        assert det.position == (540, 960)

    def test_detection_result_to_log_string(self) -> None:
        """Test log string formatting."""
        det = DetectionResult(
            entity_type="unit",
            name="demon_hunter",
            confidence=0.95,
            method="histogram",
            position=(100, 200),
        )
        log_str = det.to_log_string()
        assert "UNIT" in log_str
        assert "demon_hunter" in log_str
        assert "0.95" in log_str
        assert "(100, 200)" in log_str

    def test_detection_result_to_log_string_no_position(self) -> None:
        """Test log string without position."""
        det = DetectionResult(
            entity_type="icon",
            name="battle",
            confidence=0.80,
            method="template",
        )
        log_str = det.to_log_string()
        assert "ICON" in log_str
        assert "battle" in log_str
        assert "@" not in log_str  # No position marker


class TestPageContext:
    """Tests for PageContext dataclass."""

    def test_page_context_creation(self) -> None:
        """Test basic page context creation."""
        ctx = PageContext(
            state=ScreenState.HOME,
            confidence=0.92,
            detected_via="home_screen.png",
        )
        assert ctx.state == ScreenState.HOME
        assert ctx.confidence == 0.92
        assert ctx.detected_via == "home_screen.png"

    def test_page_context_with_menu(self) -> None:
        """Test page context with menu context."""
        ctx = PageContext(
            state=ScreenState.STORE_MENU,
            confidence=0.95,
            detected_via="Store_Menu.png",
            menu_context="STORE",
        )
        assert ctx.menu_context == "STORE"

    def test_page_context_to_log_string(self) -> None:
        """Test log string formatting."""
        ctx = PageContext(
            state=ScreenState.BATTLE,
            confidence=0.99,
            detected_via="fighting.png",
        )
        log_str = ctx.to_log_string()
        assert "BATTLE" in log_str
        assert "0.99" in log_str
        assert "fighting.png" in log_str

    def test_page_context_to_log_string_with_menu(self) -> None:
        """Test log string with menu context."""
        ctx = PageContext(
            state=ScreenState.CARDS_MENU,
            confidence=0.90,
            detected_via="Cards_Menu.png",
            menu_context="CARDS",
        )
        log_str = ctx.to_log_string()
        assert "(Menu: CARDS)" in log_str


class TestMergeCandidate:
    """Tests for MergeCandidate dataclass."""

    def test_merge_candidate_creation(self) -> None:
        """Test basic merge candidate creation."""
        mc = MergeCandidate(
            source_unit="archer",
            target_unit="archer",
            source_pos=(0, 0),
            target_pos=(0, 1),
            rank=2,
        )
        assert mc.source_unit == "archer"
        assert mc.target_unit == "archer"
        assert mc.rank == 2
        assert mc.is_allowed is True

    def test_merge_candidate_blocked(self) -> None:
        """Test blocked merge candidate."""
        mc = MergeCandidate(
            source_unit="archer",
            target_unit="knight",
            source_pos=(0, 0),
            target_pos=(0, 1),
            rank=2,
            is_allowed=False,
            rule_note="different_types",
        )
        assert mc.is_allowed is False
        assert mc.rule_note == "different_types"

    def test_merge_candidate_to_log_string_allowed(self) -> None:
        """Test log string for allowed merge."""
        mc = MergeCandidate(
            source_unit="archer",
            target_unit="archer",
            source_pos=(0, 0),
            target_pos=(0, 1),
            rank=2,
        )
        log_str = mc.to_log_string()
        assert "✓" in log_str
        assert "archer" in log_str
        assert "Rank 2" in log_str

    def test_merge_candidate_to_log_string_blocked(self) -> None:
        """Test log string for blocked merge."""
        mc = MergeCandidate(
            source_unit="archer",
            target_unit="knight",
            source_pos=(0, 0),
            target_pos=(0, 1),
            rank=2,
            is_allowed=False,
            rule_note="different_types",
        )
        log_str = mc.to_log_string()
        assert "✗" in log_str
        assert "(different_types)" in log_str


class TestCVDebugFrame:
    """Tests for CVDebugFrame dataclass."""

    def test_frame_creation(self) -> None:
        """Test basic frame creation."""
        frame = CVDebugFrame(timestamp="2026-01-18T12:00:00")
        assert frame.timestamp == "2026-01-18T12:00:00"
        assert frame.detections == []
        assert frame.merge_candidates == []

    def test_frame_with_detections(self) -> None:
        """Test frame with detections."""
        det = DetectionResult(
            entity_type="unit",
            name="archer",
            confidence=0.9,
            method="histogram",
        )
        frame = CVDebugFrame(
            timestamp="2026-01-18T12:00:00",
            detections=[det],
        )
        assert len(frame.detections) == 1

    def test_frame_to_dict(self) -> None:
        """Test conversion to dictionary."""
        ctx = PageContext(
            state=ScreenState.HOME,
            confidence=0.9,
            detected_via="home.png",
        )
        det = DetectionResult(
            entity_type="icon",
            name="pvp",
            confidence=0.85,
            method="template",
        )
        frame = CVDebugFrame(
            timestamp="2026-01-18T12:00:00",
            page_context=ctx,
            detections=[det],
        )
        d = frame.to_dict()
        assert d["timestamp"] == "2026-01-18T12:00:00"
        assert d["page_context"]["state"] == "HOME"
        assert len(d["detections"]) == 1


class TestCVDebugLevel:
    """Tests for CVDebugLevel enum."""

    def test_all_levels_exist(self) -> None:
        """Test all debug levels exist."""
        assert CVDebugLevel.MINIMAL is not None
        assert CVDebugLevel.NORMAL is not None
        assert CVDebugLevel.VERBOSE is not None


class TestCVDebugMode:
    """Tests for CVDebugMode class."""

    def test_debug_mode_creation(self) -> None:
        """Test basic creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            debug = CVDebugMode(
                level=CVDebugLevel.NORMAL,
                save_images=False,
                output_dir=Path(tmpdir),
            )
            assert debug.level == CVDebugLevel.NORMAL
            assert debug.save_images is False

    def test_debug_mode_with_save_images(self) -> None:
        """Test creation with image saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            debug = CVDebugMode(
                level=CVDebugLevel.VERBOSE,
                save_images=True,
                output_dir=Path(tmpdir),
            )
            assert debug.output_dir.exists()

    @patch.object(CVDebugMode, "_detect_page_context")
    def test_analyze_frame_calls_page_detection(self, mock_detect: MagicMock) -> None:
        """Test that analyze_frame calls page detection."""
        mock_detect.return_value = PageContext(
            state=ScreenState.HOME, confidence=0.9, detected_via="test.png"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            debug = CVDebugMode(
                level=CVDebugLevel.MINIMAL,
                save_images=False,
                output_dir=Path(tmpdir),
            )
            # Create dummy image
            image = np.zeros((1920, 1080, 3), dtype=np.uint8)
            frame = debug.analyze_frame(image)
            mock_detect.assert_called_once()
            assert frame.page_context is not None

    def test_check_merge_rules_same_type(self) -> None:
        """Test merge rules for same type units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            debug = CVDebugMode(save_images=False, output_dir=Path(tmpdir))
            allowed, note = debug._check_merge_rules("archer", "archer", 2, set())
            assert allowed is True
            assert note == "same_type"

    def test_check_merge_rules_different_type(self) -> None:
        """Test merge rules for different type units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            debug = CVDebugMode(save_images=False, output_dir=Path(tmpdir))
            allowed, note = debug._check_merge_rules("archer", "knight", 2, set())
            assert allowed is False
            assert note == "different_types"

    def test_check_merge_rules_special_unit(self) -> None:
        """Test merge rules for special units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            debug = CVDebugMode(save_images=False, output_dir=Path(tmpdir))
            special = {"harlequin", "dryad"}
            allowed, note = debug._check_merge_rules("harlequin", "knight", 2, special)
            assert allowed is True
            assert "special_unit" in note

    def test_export_session(self) -> None:
        """Test session export to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            debug = CVDebugMode(
                level=CVDebugLevel.MINIMAL,
                save_images=False,
                output_dir=Path(tmpdir),
            )
            # Add a dummy frame
            debug._frames.append(CVDebugFrame(timestamp="2026-01-18T12:00:00"))
            debug._frame_count = 1

            # Export
            output_path = debug.export_session()
            assert Path(output_path).exists()

    def test_clear_session(self) -> None:
        """Test session clearing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            debug = CVDebugMode(save_images=False, output_dir=Path(tmpdir))
            debug._frames.append(CVDebugFrame(timestamp="2026-01-18T12:00:00"))
            debug._frame_count = 5

            debug.clear_session()
            assert len(debug._frames) == 0
            assert debug._frame_count == 0


class TestRunCVDebugOnScreenshot:
    """Tests for run_cv_debug_on_screenshot function."""

    def test_invalid_image_path(self) -> None:
        """Test with non-existent image."""
        with pytest.raises(ValueError, match="Could not load image"):
            run_cv_debug_on_screenshot("/nonexistent/path.png")

    @patch("cv2.imread")
    @patch.object(CVDebugMode, "analyze_frame")
    def test_valid_image_path(self, mock_analyze: MagicMock, mock_imread: MagicMock) -> None:
        """Test with valid image."""
        mock_imread.return_value = np.zeros((1920, 1080, 3), dtype=np.uint8)
        mock_analyze.return_value = CVDebugFrame(timestamp="test")

        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            result = run_cv_debug_on_screenshot(tmp.name, save_output=False)
            assert result.timestamp == "test"
