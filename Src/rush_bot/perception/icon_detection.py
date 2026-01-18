"""Screen State Detection for Rush Royale Bot - Context-Aware Icon Detection Extension.

This module extends screen_state.py with context-aware icon detection
to prevent false positives by enforcing ROI and screen-state filtering.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rush_bot.perception.screen_state import ImageArray
from rush_bot.perception.screen_state import ScreenState
from rush_bot.perception.screen_state import ScreenStateDetector


@dataclass
class IconROI:
    """Region of Interest for icon detection.

    Defines where an icon should be searched based on screen state.
    Coordinates are relative to reference resolution (1080x1920).
    """

    x: int
    y: int
    width: int
    height: int
    min_confidence: float = 0.85

    def scale(self, screen_width: int, screen_height: int) -> tuple[int, int, int, int]:
        """Scale ROI to match actual screen resolution.

        Args:
            screen_width: Actual screen width.
            screen_height: Actual screen height.

        Returns:
            Tuple of (x, y, width, height) in actual resolution.
        """
        ref_width = 1080
        ref_height = 1920

        scale_x = screen_width / ref_width
        scale_y = screen_height / ref_height

        return (
            int(self.x * scale_x),
            int(self.y * scale_y),
            int(self.width * scale_x),
            int(self.height * scale_y),
        )


# Icon ROI definitions for different screen states
# Reference resolution: 1080x1920 (portrait mode)
ICON_ROI_MAP: dict[str, dict[ScreenState, IconROI]] = {
    # PVP/PVE buttons - only visible on HOME screen
    "pvp_button.png": {
        ScreenState.HOME: IconROI(x=125, y=1180, width=200, height=234, min_confidence=0.85),
    },
    "pve_button.png": {
        ScreenState.HOME: IconROI(x=575, y=1180, width=200, height=234, min_confidence=0.85),
    },
    # Battle icon - home screen navigation
    "battle_icon.png": {
        ScreenState.HOME: IconROI(x=360, y=1450, width=120, height=120, min_confidence=0.90),
    },
    # Dungeon page - only on dungeon select screen
    "dungeon_page.png": {
        ScreenState.DUNGEON_SELECT: IconROI(x=0, y=0, width=1080, height=600, min_confidence=0.85),
    },
    # Chapter buttons - dungeon select screen
    "chapter_1.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=200, width=1080, height=1400, min_confidence=0.85
        ),
    },
    "chapter_2.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=200, width=1080, height=1400, min_confidence=0.85
        ),
    },
    "chapter_3.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=200, width=1080, height=1400, min_confidence=0.85
        ),
    },
    "chapter_4.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=200, width=1080, height=1400, min_confidence=0.85
        ),
    },
    "chapter_5.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=200, width=1080, height=1400, min_confidence=0.85
        ),
    },
    "chapter_6.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=200, width=1080, height=1400, min_confidence=0.85
        ),
    },
    # Floor buttons - dungeon select screen
    "floor_1.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_2.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_3.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_4.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_5.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_6.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_7.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_8.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_9.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_10.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_11.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_12.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_13.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    "floor_14.png": {
        ScreenState.DUNGEON_SELECT: IconROI(
            x=0, y=400, width=1080, height=1200, min_confidence=0.90
        ),
    },
    # Continue button - only on victory screen
    "0cont_button.png": {
        ScreenState.VICTORY: IconROI(x=200, y=1400, width=680, height=200, min_confidence=0.90),
    },
    # Quit button - only on defeat screen
    "1quit.png": {
        ScreenState.DEFEAT: IconROI(x=200, y=1400, width=680, height=200, min_confidence=0.90),
    },
}


class ContextAwareIconDetector:
    """Icon detector with screen-state context awareness.

    This detector ensures icons are only detected in appropriate screen states
    and within their defined ROIs, preventing false positives.

    Usage:
        detector = ContextAwareIconDetector()
        icons = detector.detect_icons(screenshot, icon_list=["pvp_button.png"])
    """

    def __init__(self) -> None:
        """Initialize context-aware icon detector."""
        self._state_detector = ScreenStateDetector()
        self._current_state: ScreenState = ScreenState.UNKNOWN
        self._menu_context: ScreenState = ScreenState.UNKNOWN

    def detect_icons(
        self,
        screenshot: ImageArray | str | Path,
        icon_list: list[str] | None = None,
        force_state: ScreenState | None = None,
    ) -> list[dict[str, Any]]:
        """Detect icons with screen-state context awareness.

        Args:
            screenshot: Screenshot to analyze.
            icon_list: List of icon filenames to check. If None, checks all known icons.
            force_state: Force a specific screen state instead of auto-detecting.

        Returns:
            List of detected icons with metadata:
            [{"icon": "name.png", "confidence": 0.95, "position": (x, y), "state": ScreenState}]
        """
        import cv2

        # Load image if path provided
        if isinstance(screenshot, (str, Path)):
            img = cv2.imread(str(screenshot))
            if img is None:
                return []
        else:
            img = screenshot

        screen_h, screen_w = img.shape[:2]

        # Step 1: Detect menu context FIRST (90% confidence required)
        menu_result = self._state_detector.detect_menu_context(img, min_confidence=0.90)
        self._menu_context = menu_result.state

        # Step 2: Detect screen state (or use forced state)
        if force_state is not None:
            self._current_state = force_state
        else:
            state_result = self._state_detector.detect(img)
            self._current_state = state_result.state

        # Step 3: Determine which icons to check
        if icon_list is None:
            # Check all icons that have ROI definitions
            icons_to_check = list(ICON_ROI_MAP.keys())
        else:
            icons_to_check = icon_list

        # Step 4: Detect icons with state/ROI filtering
        detected_icons: list[dict[str, Any]] = []

        for icon_name in icons_to_check:
            # Check if this icon has ROI definitions
            if icon_name not in ICON_ROI_MAP:
                # No ROI defined - skip to prevent false positives
                continue

            roi_states = ICON_ROI_MAP[icon_name]

            # Check if icon is valid for current state
            if self._current_state not in roi_states:
                # Icon not allowed in this state - skip
                continue

            # Get ROI for this icon in current state
            icon_roi = roi_states[self._current_state]
            scaled_roi = icon_roi.scale(screen_w, screen_h)

            # Detect icon within ROI
            result = self._state_detector.detect_with_roi(
                img,
                roi=scaled_roi,
                min_confidence=icon_roi.min_confidence,
            )

            # Check if icon was found
            if (
                result.matched_template == icon_name
                and result.confidence >= icon_roi.min_confidence
            ):
                detected_icons.append(
                    {
                        "icon": icon_name,
                        "confidence": result.confidence,
                        "position": (
                            result.region[0] + result.region[2] // 2,
                            result.region[1] + result.region[3] // 2,
                        )
                        if result.region
                        else (0, 0),
                        "state": self._current_state,
                        "region": result.region,
                    }
                )

        return detected_icons

    @property
    def current_state(self) -> ScreenState:
        """Get the last detected screen state."""
        return self._current_state

    @property
    def menu_context(self) -> ScreenState:
        """Get the last detected menu context."""
        return self._menu_context
