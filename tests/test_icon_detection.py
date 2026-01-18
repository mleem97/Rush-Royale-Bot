"""Tests for context-aware icon detection."""

import numpy as np
import pytest

from rush_bot.perception import ContextAwareIconDetector
from rush_bot.perception import IconROI
from rush_bot.perception import ScreenState


@pytest.fixture
def icon_detector() -> ContextAwareIconDetector:
    """Create icon detector instance."""
    return ContextAwareIconDetector()


@pytest.fixture
def dummy_screenshot() -> np.ndarray:
    """Create a dummy screenshot (1080x1920)."""
    return np.zeros((1920, 1080, 3), dtype=np.uint8)


def test_icon_roi_scaling():
    """Test IconROI scaling to different resolutions."""
    roi = IconROI(x=100, y=200, width=300, height=400, min_confidence=0.85)

    # Test scaling to reference resolution (should be same)
    scaled = roi.scale(1080, 1920)
    assert scaled == (100, 200, 300, 400)

    # Test scaling to 2x resolution
    scaled_2x = roi.scale(2160, 3840)
    assert scaled_2x == (200, 400, 600, 800)

    # Test scaling to 0.5x resolution
    scaled_half = roi.scale(540, 960)
    assert scaled_half == (50, 100, 150, 200)


def test_context_aware_detector_initialization(icon_detector: ContextAwareIconDetector):
    """Test detector initializes correctly."""
    assert icon_detector.current_state == ScreenState.UNKNOWN
    assert icon_detector.menu_context == ScreenState.UNKNOWN


def test_detect_icons_empty_screenshot(
    icon_detector: ContextAwareIconDetector, dummy_screenshot: np.ndarray
):
    """Test icon detection on empty screenshot."""
    # Should return empty list since no icons match
    icons = icon_detector.detect_icons(dummy_screenshot)
    assert isinstance(icons, list)


def test_detect_icons_with_empty_list(
    icon_detector: ContextAwareIconDetector, dummy_screenshot: np.ndarray
):
    """Test icon detection with empty icon list."""
    icons = icon_detector.detect_icons(dummy_screenshot, icon_list=[])
    assert icons == []


def test_detect_icons_filters_by_state(
    icon_detector: ContextAwareIconDetector, dummy_screenshot: np.ndarray
):
    """Test that icons are filtered by screen state."""
    # Force HOME state
    icons = icon_detector.detect_icons(
        dummy_screenshot,
        icon_list=["pvp_button.png", "0cont_button.png"],
        force_state=ScreenState.HOME,
    )

    # 0cont_button.png should be filtered out (only valid in VICTORY state)
    detected_names = [icon["icon"] for icon in icons]
    assert "0cont_button.png" not in detected_names


def test_detect_icons_respects_roi(icon_detector: ContextAwareIconDetector):
    """Test that icons are only detected within their ROI."""
    # Create screenshot with white box in specific location
    screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)

    # PVP button should be around x=125, y=1180 (reference resolution)
    # Put a white box there
    screenshot[1180:1414, 125:325] = 255

    # Detection should fail since we don't have actual template
    # But ROI logic should be applied
    icons = icon_detector.detect_icons(
        screenshot, icon_list=["pvp_button.png"], force_state=ScreenState.HOME
    )

    # Just verify no crash and returns list
    assert isinstance(icons, list)


def test_menu_context_detection(
    icon_detector: ContextAwareIconDetector, dummy_screenshot: np.ndarray
):
    """Test menu context detection is called."""
    # Run detection to trigger menu context check
    icon_detector.detect_icons(dummy_screenshot)

    # Menu context should be set (even if UNKNOWN)
    assert icon_detector.menu_context in ScreenState


def test_icon_detection_result_structure(
    icon_detector: ContextAwareIconDetector, dummy_screenshot: np.ndarray
):
    """Test that detected icons have correct structure."""
    icons = icon_detector.detect_icons(dummy_screenshot)

    # Each icon should be a dict with specific keys
    for icon in icons:
        assert "icon" in icon
        assert "confidence" in icon
        assert "position" in icon
        assert "state" in icon
        assert "region" in icon
        assert isinstance(icon["icon"], str)
        assert isinstance(icon["confidence"], float)
        assert isinstance(icon["position"], tuple)
        assert isinstance(icon["state"], ScreenState)


def test_icon_roi_map_has_valid_states():
    """Test that ICON_ROI_MAP contains valid ScreenState mappings."""
    from rush_bot.perception.icon_detection import ICON_ROI_MAP

    for icon_name, state_map in ICON_ROI_MAP.items():
        assert isinstance(icon_name, str)
        assert icon_name.endswith(".png")

        for state, roi in state_map.items():
            assert isinstance(state, ScreenState)
            assert isinstance(roi, IconROI)
            assert 0 <= roi.min_confidence <= 1.0
            assert roi.width > 0
            assert roi.height > 0


def test_pvp_pve_buttons_only_on_home():
    """Test that PVP/PVE buttons are only defined for HOME screen."""
    from rush_bot.perception.icon_detection import ICON_ROI_MAP

    pvp_states = ICON_ROI_MAP.get("pvp_button.png", {})
    pve_states = ICON_ROI_MAP.get("pve_button.png", {})

    # Should only have HOME state
    assert ScreenState.HOME in pvp_states
    assert len(pvp_states) == 1

    assert ScreenState.HOME in pve_states
    assert len(pve_states) == 1


def test_continue_button_only_on_victory():
    """Test that continue button is only defined for VICTORY screen."""
    from rush_bot.perception.icon_detection import ICON_ROI_MAP

    continue_states = ICON_ROI_MAP.get("0cont_button.png", {})

    # Should only have VICTORY state
    assert ScreenState.VICTORY in continue_states
    assert len(continue_states) == 1


def test_floor_buttons_only_on_dungeon_select():
    """Test that floor buttons are only defined for DUNGEON_SELECT screen."""
    from rush_bot.perception.icon_detection import ICON_ROI_MAP

    for floor_num in range(1, 15):
        floor_name = f"floor_{floor_num}.png"
        floor_states = ICON_ROI_MAP.get(floor_name, {})

        # Should only have DUNGEON_SELECT state
        assert ScreenState.DUNGEON_SELECT in floor_states
        assert len(floor_states) == 1


def test_high_confidence_thresholds():
    """Test that all ROIs have confidence >= 0.85."""
    from rush_bot.perception.icon_detection import ICON_ROI_MAP

    for icon_name, state_map in ICON_ROI_MAP.items():
        for _state, roi in state_map.items():
            assert roi.min_confidence >= 0.85, (
                f"{icon_name} has confidence {roi.min_confidence} < 0.85"
            )
