"""PvE Dungeon Loop Automation for Rush Royale Bot.

This module provides complete PvE dungeon automation including:
- Dungeon entry from home screen
- Chapter and floor selection
- Battle automation loop
- Victory/defeat screen handling
- Ad skipping
- Retry/continue logic

Coordinate System (Reference: 1080x1920):
All coordinates are relative to a 1080x1920 reference resolution
and are automatically scaled to the actual screen resolution.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from enum import auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rush_bot.core.device import DeviceManager
    from rush_bot.perception.screen_state import ScreenStateDetector


# =============================================================================
# Constants - Reference Resolution (1080x1920)
# =============================================================================

REFERENCE_WIDTH = 1080
REFERENCE_HEIGHT = 1920

# Button coordinates on home screen
BATTLE_BUTTON_X_REF = 540
BATTLE_BUTTON_Y_REF = 1600

# Dungeon button on battle selection screen
DUNGEON_BUTTON_X_REF = 540
DUNGEON_BUTTON_Y_REF = 800

# Chapter selection coordinates (swipe targets)
CHAPTER_LIST_TOP_Y_REF = 600
CHAPTER_LIST_BOTTOM_Y_REF = 1200

# Chapter button Y position after scroll
CHAPTER_BUTTON_Y_REF = 900

# Floor selection area
FLOOR_GRID_START_X_REF = 100
FLOOR_GRID_START_Y_REF = 600
FLOOR_GRID_CELL_WIDTH_REF = 180
FLOOR_GRID_CELL_HEIGHT_REF = 200
FLOOR_GRID_COLS = 5
FLOOR_GRID_ROWS = 3

# Start button on floor selection
START_BUTTON_X_REF = 540
START_BUTTON_Y_REF = 1700

# Continue button after victory
CONTINUE_BUTTON_X_REF = 540
CONTINUE_BUTTON_Y_REF = 1400

# Quit button after defeat
QUIT_BUTTON_X_REF = 540
QUIT_BUTTON_Y_REF = 1400

# Ad skip button position (usually top-right X)
AD_SKIP_X_REF = 1000
AD_SKIP_Y_REF = 100

# Back button position
BACK_BUTTON_X_REF = 100
BACK_BUTTON_Y_REF = 100

# Battle detection regions
HEALTH_BAR_REGION_Y_REF = 150

# Timing constants (milliseconds)
DEFAULT_ACTION_DELAY_MS = 500
DEFAULT_SCREEN_WAIT_MS = 1000
DEFAULT_BATTLE_CHECK_INTERVAL_MS = 500
DEFAULT_AD_TIMEOUT_MS = 30000
DEFAULT_TRANSITION_TIMEOUT_MS = 10000

# Logger
logger = logging.getLogger(__name__)


class DungeonState(Enum):
    """States in the dungeon automation loop.

    This state machine tracks the current phase of dungeon automation.
    """

    IDLE = auto()
    """Not actively running dungeon automation."""

    NAVIGATING_TO_DUNGEON = auto()
    """Navigating from home to dungeon selection."""

    SELECTING_CHAPTER = auto()
    """Selecting a dungeon chapter."""

    SELECTING_FLOOR = auto()
    """Selecting a floor within the chapter."""

    WAITING_FOR_BATTLE = auto()
    """Waiting for battle to start."""

    IN_BATTLE = auto()
    """Actively in a dungeon battle."""

    BATTLE_ENDED = auto()
    """Battle has ended, handling result screen."""

    HANDLING_VICTORY = auto()
    """Processing victory screen."""

    HANDLING_DEFEAT = auto()
    """Processing defeat screen."""

    HANDLING_AD = auto()
    """Handling advertisement popup."""

    RETURNING_TO_MENU = auto()
    """Returning to main menu or dungeon selection."""

    ERROR = auto()
    """An error occurred."""

    COMPLETED = auto()
    """Dungeon run completed successfully."""


class DungeonResult(Enum):
    """Result of a dungeon run."""

    VICTORY = auto()
    """Successfully cleared the dungeon."""

    DEFEAT = auto()
    """Lost the dungeon battle."""

    ERROR = auto()
    """An error occurred."""

    CANCELLED = auto()
    """Run was cancelled by user."""

    TIMEOUT = auto()
    """Run timed out."""


@dataclass
class DungeonConfig:
    """Configuration for dungeon automation.

    Attributes:
        target_chapter: Target chapter number (1-6).
        target_floor: Target floor number (1-14).
        auto_retry: Automatically retry on defeat.
        max_retries: Maximum retry attempts.
        skip_ads: Skip advertisements when possible.
        action_delay_ms: Delay between actions in milliseconds.
        battle_timeout_seconds: Maximum battle duration before timeout.
        ad_timeout_ms: Maximum time to wait for ad to finish.
        transition_timeout_ms: Maximum time to wait for screen transitions.
        enable_battle_automation: Enable automatic battle actions (summon, merge).
    """

    target_chapter: int = 1
    target_floor: int = 1
    auto_retry: bool = True
    max_retries: int = 3
    skip_ads: bool = True
    action_delay_ms: int = DEFAULT_ACTION_DELAY_MS
    battle_timeout_seconds: int = 600  # 10 minutes max battle
    ad_timeout_ms: int = DEFAULT_AD_TIMEOUT_MS
    transition_timeout_ms: int = DEFAULT_TRANSITION_TIMEOUT_MS
    enable_battle_automation: bool = True

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not 1 <= self.target_chapter <= 6:
            raise ValueError(f"Invalid chapter: {self.target_chapter}. Must be 1-6.")
        if not 1 <= self.target_floor <= 14:
            raise ValueError(f"Invalid floor: {self.target_floor}. Must be 1-14.")
        if self.max_retries < 0:
            raise ValueError(f"Invalid max_retries: {self.max_retries}. Must be >= 0.")


@dataclass
class DungeonStats:
    """Statistics for dungeon automation session.

    Attributes:
        runs_completed: Number of completed dungeon runs.
        victories: Number of victories.
        defeats: Number of defeats.
        errors: Number of errors encountered.
        total_battle_time_seconds: Total time spent in battles.
        ads_skipped: Number of ads skipped.
        retries_used: Total retries used.
    """

    runs_completed: int = 0
    victories: int = 0
    defeats: int = 0
    errors: int = 0
    total_battle_time_seconds: float = 0.0
    ads_skipped: int = 0
    retries_used: int = 0

    def record_victory(self, battle_time: float) -> None:
        """Record a victory.

        Args:
            battle_time: Battle duration in seconds.
        """
        self.runs_completed += 1
        self.victories += 1
        self.total_battle_time_seconds += battle_time

    def record_defeat(self, battle_time: float) -> None:
        """Record a defeat.

        Args:
            battle_time: Battle duration in seconds.
        """
        self.runs_completed += 1
        self.defeats += 1
        self.total_battle_time_seconds += battle_time

    def record_error(self) -> None:
        """Record an error."""
        self.errors += 1

    def record_ad_skip(self) -> None:
        """Record an ad skip."""
        self.ads_skipped += 1

    def record_retry(self) -> None:
        """Record a retry attempt."""
        self.retries_used += 1

    @property
    def win_rate(self) -> float:
        """Calculate win rate as percentage.

        Returns:
            Win rate (0.0-100.0), or 0.0 if no runs completed.
        """
        if self.runs_completed == 0:
            return 0.0
        return (self.victories / self.runs_completed) * 100.0

    @property
    def average_battle_time(self) -> float:
        """Calculate average battle time.

        Returns:
            Average battle time in seconds, or 0.0 if no runs completed.
        """
        if self.runs_completed == 0:
            return 0.0
        return self.total_battle_time_seconds / self.runs_completed


@dataclass
class DungeonRunResult:
    """Result of a single dungeon run.

    Attributes:
        result: The outcome of the run.
        chapter: Chapter that was attempted.
        floor: Floor that was attempted.
        battle_time_seconds: Duration of the battle.
        error_message: Error message if result is ERROR.
        retry_count: Number of retries used.
    """

    result: DungeonResult
    chapter: int
    floor: int
    battle_time_seconds: float = 0.0
    error_message: str = ""
    retry_count: int = 0


class DungeonLoop:
    """Automated PvE dungeon farming loop.

    Handles complete dungeon automation from navigation to battle
    completion, including retry logic and error recovery.

    Usage:
        from rush_bot.core import DeviceManager, DungeonLoop, DungeonConfig
        from rush_bot.perception import ScreenStateDetector

        device = DeviceManager()
        device.connect()

        detector = ScreenStateDetector()
        config = DungeonConfig(target_chapter=1, target_floor=5)

        dungeon = DungeonLoop(device, detector, config)
        result = dungeon.run()

        print(f"Result: {result.result.name}")
        print(f"Stats: {dungeon.stats}")
    """

    def __init__(
        self,
        device: DeviceManager,
        detector: ScreenStateDetector,
        config: DungeonConfig | None = None,
        on_state_change: Callable[[DungeonState], None] | None = None,
        on_battle_action: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize the dungeon automation loop.

        Args:
            device: Connected DeviceManager for screen interaction.
            detector: ScreenStateDetector for screen state recognition.
            config: Optional configuration. Uses defaults if None.
            on_state_change: Callback when state changes.
            on_battle_action: Callback when battle action is taken.
        """
        self.device = device
        self.detector = detector
        self.config = config or DungeonConfig()
        self._on_state_change = on_state_change
        self._on_battle_action = on_battle_action

        self._state = DungeonState.IDLE
        self._is_running = False
        self._should_stop = False
        self._current_retry = 0
        self._battle_start_time: float = 0.0
        self._stats = DungeonStats()

        # Screen resolution for coordinate scaling
        self._screen_width = REFERENCE_WIDTH
        self._screen_height = REFERENCE_HEIGHT

    @property
    def state(self) -> DungeonState:
        """Get current dungeon automation state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if dungeon loop is currently running."""
        return self._is_running

    @property
    def stats(self) -> DungeonStats:
        """Get dungeon automation statistics."""
        return self._stats

    def _set_state(self, state: DungeonState) -> None:
        """Update state and notify callback.

        Args:
            state: New dungeon state.
        """
        if self._state != state:
            old_state = self._state
            self._state = state
            logger.debug(f"Dungeon state: {old_state.name} -> {state.name}")
            if self._on_state_change:
                try:
                    self._on_state_change(state)
                except Exception as e:
                    logger.warning(f"State change callback error: {e}")

    def _notify_battle_action(self, action: str) -> None:
        """Notify about battle action.

        Args:
            action: Description of the action taken.
        """
        logger.debug(f"Battle action: {action}")
        if self._on_battle_action:
            try:
                self._on_battle_action(action)
            except Exception as e:
                logger.warning(f"Battle action callback error: {e}")

    def _scale_x(self, x: int) -> int:
        """Scale X coordinate to current resolution.

        Args:
            x: Reference X coordinate (1080p).

        Returns:
            Scaled X coordinate.
        """
        return int(x * self._screen_width / REFERENCE_WIDTH)

    def _scale_y(self, y: int) -> int:
        """Scale Y coordinate to current resolution.

        Args:
            y: Reference Y coordinate (1920p).

        Returns:
            Scaled Y coordinate.
        """
        return int(y * self._screen_height / REFERENCE_HEIGHT)

    def _update_screen_resolution(self) -> None:
        """Update screen resolution from device info."""
        if self.device.device_info:
            if self.device.device_info.screen_width > 0:
                self._screen_width = self.device.device_info.screen_width
            if self.device.device_info.screen_height > 0:
                self._screen_height = self.device.device_info.screen_height

    def _delay(self, ms: int | None = None) -> None:
        """Delay execution.

        Args:
            ms: Delay in milliseconds. Uses config default if None.
        """
        delay_ms = ms if ms is not None else self.config.action_delay_ms
        time.sleep(delay_ms / 1000.0)

    def _tap(self, x: int, y: int) -> bool:
        """Tap at scaled coordinates.

        Args:
            x: Reference X coordinate.
            y: Reference Y coordinate.

        Returns:
            True if tap successful.
        """
        scaled_x = self._scale_x(x)
        scaled_y = self._scale_y(y)
        result = self.device.tap(scaled_x, scaled_y)
        self._delay()
        return result

    def _swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """Swipe with scaled coordinates.

        Args:
            x1, y1: Start coordinates (reference).
            x2, y2: End coordinates (reference).
            duration_ms: Swipe duration.

        Returns:
            True if swipe successful.
        """
        result = self.device.swipe(
            self._scale_x(x1),
            self._scale_y(y1),
            self._scale_x(x2),
            self._scale_y(y2),
            duration_ms,
        )
        self._delay()
        return result

    def _capture_screen(self) -> NDArray | None:
        """Capture and return screenshot as numpy array.

        Returns:
            Screenshot as BGR numpy array, or None if failed.
        """
        import numpy as np
        from PIL import Image

        pil_image = self.device.screenshot()
        if pil_image is None:
            return None

        # Convert PIL to numpy BGR (OpenCV format)
        if isinstance(pil_image, Image.Image):
            rgb_array = np.array(pil_image)
            # Convert RGB to BGR
            if len(rgb_array.shape) == 3 and rgb_array.shape[2] >= 3:
                return rgb_array[:, :, ::-1].copy()
        return None

    def _wait_for_screen_state(
        self,
        expected_states: list[str],
        timeout_ms: int | None = None,
    ) -> tuple[bool, str]:
        """Wait for one of the expected screen states.

        Args:
            expected_states: List of expected state names.
            timeout_ms: Timeout in milliseconds. Uses config default if None.

        Returns:
            Tuple of (success, detected_state_name).
        """
        from rush_bot.perception import ScreenState

        timeout = timeout_ms if timeout_ms is not None else self.config.transition_timeout_ms
        start_time = time.time()

        # Map string names to ScreenState enum
        state_map = {s.name: s for s in ScreenState}
        target_states = [state_map.get(name, ScreenState.UNKNOWN) for name in expected_states]

        while (time.time() - start_time) * 1000 < timeout:
            if self._should_stop:
                return (False, "CANCELLED")

            screenshot = self._capture_screen()
            if screenshot is None:
                self._delay(200)
                continue

            result = self.detector.detect(screenshot)
            if result.state in target_states:
                return (True, result.state.name)

            self._delay(DEFAULT_BATTLE_CHECK_INTERVAL_MS)

        return (False, "TIMEOUT")

    def _navigate_to_dungeon(self) -> bool:
        """Navigate from home screen to dungeon selection.

        Returns:
            True if successfully reached dungeon selection.
        """
        self._set_state(DungeonState.NAVIGATING_TO_DUNGEON)
        logger.info("Navigating to dungeon selection...")

        # First, check current screen
        screenshot = self._capture_screen()
        if screenshot is None:
            logger.error("Failed to capture screenshot")
            return False

        result = self.detector.detect(screenshot)

        # If already on dungeon selection, we're done
        if result.state.name == "DUNGEON_SELECT":
            logger.info("Already on dungeon selection screen")
            return True

        # If on home screen, tap battle button
        if result.state.name == "HOME":
            logger.debug("On home screen, tapping battle button")
            self._tap(BATTLE_BUTTON_X_REF, BATTLE_BUTTON_Y_REF)
            self._delay(DEFAULT_SCREEN_WAIT_MS)

            # Wait for dungeon button to appear
            screenshot = self._capture_screen()
            if screenshot is not None:
                # Tap dungeon/PvE button
                self._tap(DUNGEON_BUTTON_X_REF, DUNGEON_BUTTON_Y_REF)
                self._delay(DEFAULT_SCREEN_WAIT_MS)

        # Verify we reached dungeon selection
        success, state = self._wait_for_screen_state(
            ["DUNGEON_SELECT"],
            timeout_ms=5000,
        )

        if not success:
            logger.warning(f"Failed to reach dungeon selection, current state: {state}")
            return False

        logger.info("Reached dungeon selection screen")
        return True

    def _select_chapter(self) -> bool:
        """Select the target chapter.

        Returns:
            True if chapter selected successfully.
        """
        self._set_state(DungeonState.SELECTING_CHAPTER)
        logger.info(f"Selecting chapter {self.config.target_chapter}...")

        # Chapters may require scrolling
        # For now, tap on the chapter assuming it's visible
        # Each chapter has a template: chapter_X.png

        screenshot = self._capture_screen()
        if screenshot is None:
            return False

        # Try to find the chapter template
        template_name = f"chapter_{self.config.target_chapter}.png"
        found, region, _confidence = self.detector.find_template(screenshot, template_name)

        if found and region is not None:
            # Tap center of the found region
            x = region[0] + region[2] // 2
            y = region[1] + region[3] // 2
            self.device.tap(x, y)
            self._delay(DEFAULT_SCREEN_WAIT_MS)
            logger.info(f"Tapped chapter {self.config.target_chapter}")
            return True

        # If not found, try scrolling to find it
        logger.debug("Chapter not visible, scrolling...")
        self._swipe(
            REFERENCE_WIDTH // 2,
            CHAPTER_LIST_BOTTOM_Y_REF,
            REFERENCE_WIDTH // 2,
            CHAPTER_LIST_TOP_Y_REF,
            duration_ms=500,
        )
        self._delay(DEFAULT_SCREEN_WAIT_MS)

        # Try again after scroll
        screenshot = self._capture_screen()
        if screenshot is None:
            return False

        found, region, _confidence = self.detector.find_template(screenshot, template_name)

        if found and region is not None:
            x = region[0] + region[2] // 2
            y = region[1] + region[3] // 2
            self.device.tap(x, y)
            self._delay(DEFAULT_SCREEN_WAIT_MS)
            logger.info(f"Tapped chapter {self.config.target_chapter} after scroll")
            return True

        logger.warning(f"Could not find chapter {self.config.target_chapter}")
        return False

    def _select_floor(self) -> bool:
        """Select the target floor.

        Returns:
            True if floor selected successfully.
        """
        self._set_state(DungeonState.SELECTING_FLOOR)
        logger.info(f"Selecting floor {self.config.target_floor}...")

        screenshot = self._capture_screen()
        if screenshot is None:
            return False

        # Try to find the floor template
        template_name = f"floor_{self.config.target_floor}.png"
        found, region, _confidence = self.detector.find_template(screenshot, template_name)

        if found and region is not None:
            x = region[0] + region[2] // 2
            y = region[1] + region[3] // 2
            self.device.tap(x, y)
            self._delay(DEFAULT_SCREEN_WAIT_MS)

            # Tap start button
            self._tap(START_BUTTON_X_REF, START_BUTTON_Y_REF)
            self._delay(DEFAULT_SCREEN_WAIT_MS)
            logger.info(f"Selected floor {self.config.target_floor} and started")
            return True

        # Calculate floor position in grid
        floor_num = self.config.target_floor - 1  # 0-indexed
        col = floor_num % FLOOR_GRID_COLS
        row = floor_num // FLOOR_GRID_COLS

        x = (
            FLOOR_GRID_START_X_REF
            + col * FLOOR_GRID_CELL_WIDTH_REF
            + FLOOR_GRID_CELL_WIDTH_REF // 2
        )
        y = (
            FLOOR_GRID_START_Y_REF
            + row * FLOOR_GRID_CELL_HEIGHT_REF
            + FLOOR_GRID_CELL_HEIGHT_REF // 2
        )

        self._tap(x, y)
        self._delay(DEFAULT_SCREEN_WAIT_MS)

        # Tap start button
        self._tap(START_BUTTON_X_REF, START_BUTTON_Y_REF)
        self._delay(DEFAULT_SCREEN_WAIT_MS)

        logger.info(f"Selected floor {self.config.target_floor} by position")
        return True

    def _wait_for_battle_start(self) -> bool:
        """Wait for battle to start.

        Returns:
            True if battle started.
        """
        self._set_state(DungeonState.WAITING_FOR_BATTLE)
        logger.info("Waiting for battle to start...")

        success, state = self._wait_for_screen_state(
            ["BATTLE"],
            timeout_ms=self.config.transition_timeout_ms,
        )

        if success:
            self._battle_start_time = time.time()
            logger.info("Battle started!")
            return True

        logger.warning(f"Battle did not start, state: {state}")
        return False

    def _run_battle_loop(self) -> DungeonResult:
        """Run the main battle automation loop.

        Returns:
            Battle result (VICTORY, DEFEAT, ERROR, or TIMEOUT).
        """
        self._set_state(DungeonState.IN_BATTLE)
        logger.info("Running battle loop...")

        battle_start = time.time()
        check_interval = DEFAULT_BATTLE_CHECK_INTERVAL_MS / 1000.0

        while not self._should_stop:
            # Check battle timeout
            elapsed = time.time() - battle_start
            if elapsed > self.config.battle_timeout_seconds:
                logger.warning("Battle timeout exceeded")
                return DungeonResult.TIMEOUT

            # Capture screen and check state
            screenshot = self._capture_screen()
            if screenshot is None:
                time.sleep(check_interval)
                continue

            result = self.detector.detect(screenshot)

            # Check for battle end conditions
            if result.state.name == "VICTORY":
                logger.info("Victory detected!")
                return DungeonResult.VICTORY

            if result.state.name == "DEFEAT":
                logger.info("Defeat detected!")
                return DungeonResult.DEFEAT

            # Check for popups/ads during battle
            if result.state.name == "ADVERTISEMENT":
                self._handle_advertisement()
                continue

            if result.state.name == "POPUP":
                self._handle_popup()
                continue

            # Still in battle - perform battle actions if enabled
            if result.state.name == "BATTLE" and self.config.enable_battle_automation:
                self._perform_battle_actions()

            time.sleep(check_interval)

        return DungeonResult.CANCELLED

    def _perform_battle_actions(self) -> None:
        """Perform automated battle actions (summon, merge, etc).

        This is a placeholder for battle automation integration.
        Full implementation would use ManaManager and MergeLogic.
        """
        # This would integrate with ManaManager for summoning
        # and MergeLogic for automatic merging
        self._notify_battle_action("Battle tick")

    def _handle_victory(self) -> None:
        """Handle victory screen.

        Taps continue button and records victory.
        """
        self._set_state(DungeonState.HANDLING_VICTORY)
        battle_time = time.time() - self._battle_start_time
        logger.info(f"Handling victory (battle time: {battle_time:.1f}s)")

        # Tap continue button
        self._tap(CONTINUE_BUTTON_X_REF, CONTINUE_BUTTON_Y_REF)
        self._delay(DEFAULT_SCREEN_WAIT_MS)

        self._stats.record_victory(battle_time)

    def _handle_defeat(self) -> bool:
        """Handle defeat screen.

        Returns:
            True if should retry, False otherwise.
        """
        self._set_state(DungeonState.HANDLING_DEFEAT)
        battle_time = time.time() - self._battle_start_time
        logger.info(f"Handling defeat (battle time: {battle_time:.1f}s)")

        self._stats.record_defeat(battle_time)

        # Check if should retry
        if self.config.auto_retry and self._current_retry < self.config.max_retries:
            self._current_retry += 1
            self._stats.record_retry()
            logger.info(f"Retrying ({self._current_retry}/{self.config.max_retries})...")

            # Tap retry/continue button
            self._tap(QUIT_BUTTON_X_REF, QUIT_BUTTON_Y_REF)
            self._delay(DEFAULT_SCREEN_WAIT_MS)
            return True

        # No retry - tap quit
        self._tap(QUIT_BUTTON_X_REF, QUIT_BUTTON_Y_REF)
        self._delay(DEFAULT_SCREEN_WAIT_MS)
        return False

    def _handle_advertisement(self) -> None:
        """Handle advertisement popup.

        Attempts to skip ad by tapping skip button.
        """
        self._set_state(DungeonState.HANDLING_AD)
        logger.info("Handling advertisement...")

        # Wait a bit for skip button to appear
        self._delay(3000)

        # Try to tap skip button (usually X in top-right)
        self._tap(AD_SKIP_X_REF, AD_SKIP_Y_REF)
        self._delay(DEFAULT_ACTION_DELAY_MS)

        # Alternative skip button location
        self._tap(REFERENCE_WIDTH - 100, REFERENCE_HEIGHT - 100)
        self._delay(DEFAULT_SCREEN_WAIT_MS)

        self._stats.record_ad_skip()
        logger.info("Attempted to skip advertisement")

    def _handle_popup(self) -> None:
        """Handle generic popup by finding and tapping close button."""
        logger.debug("Handling popup...")

        screenshot = self._capture_screen()
        if screenshot is None:
            return

        close_pos = self.detector.get_close_button_location(screenshot)
        if close_pos:
            self.device.tap(close_pos[0], close_pos[1])
            self._delay()
            logger.debug("Closed popup via X button")
            return

        back_pos = self.detector.get_back_button_location(screenshot)
        if back_pos:
            self.device.tap(back_pos[0], back_pos[1])
            self._delay()
            logger.debug("Closed popup via back button")
            return

        # Fallback: tap outside popup area
        self._tap(100, 100)
        logger.debug("Attempted to close popup by tapping outside")

    def _return_to_menu(self) -> None:
        """Return to main menu or dungeon selection."""
        self._set_state(DungeonState.RETURNING_TO_MENU)
        logger.info("Returning to menu...")

        # Press back button a few times to ensure we're back
        for _ in range(3):
            screenshot = self._capture_screen()
            if screenshot is not None:
                result = self.detector.detect(screenshot)
                if result.state.name in ["HOME", "DUNGEON_SELECT"]:
                    break

            self.device.press_back()
            self._delay(DEFAULT_SCREEN_WAIT_MS)

    def run(self) -> DungeonRunResult:
        """Execute a single dungeon run.

        Returns:
            DungeonRunResult with outcome and statistics.
        """
        if self._is_running:
            logger.warning("Dungeon loop already running")
            return DungeonRunResult(
                result=DungeonResult.ERROR,
                chapter=self.config.target_chapter,
                floor=self.config.target_floor,
                error_message="Already running",
            )

        self._is_running = True
        self._should_stop = False
        self._current_retry = 0
        self._update_screen_resolution()

        logger.info(
            f"Starting dungeon run: Chapter {self.config.target_chapter}, "
            f"Floor {self.config.target_floor}"
        )

        try:
            # Navigation phase
            if not self._navigate_to_dungeon():
                return self._create_error_result("Failed to navigate to dungeon")

            if not self._select_chapter():
                return self._create_error_result("Failed to select chapter")

            if not self._select_floor():
                return self._create_error_result("Failed to select floor")

            if not self._wait_for_battle_start():
                return self._create_error_result("Battle did not start")

            # Battle phase
            battle_result = self._run_battle_loop()

            # Handle battle result
            if battle_result == DungeonResult.VICTORY:
                self._handle_victory()
                self._set_state(DungeonState.COMPLETED)
                return DungeonRunResult(
                    result=DungeonResult.VICTORY,
                    chapter=self.config.target_chapter,
                    floor=self.config.target_floor,
                    battle_time_seconds=time.time() - self._battle_start_time,
                    retry_count=self._current_retry,
                )

            if battle_result == DungeonResult.DEFEAT:
                should_retry = self._handle_defeat()
                if should_retry:
                    # Recursive retry
                    return self.run()

                return DungeonRunResult(
                    result=DungeonResult.DEFEAT,
                    chapter=self.config.target_chapter,
                    floor=self.config.target_floor,
                    battle_time_seconds=time.time() - self._battle_start_time,
                    retry_count=self._current_retry,
                )

            if battle_result == DungeonResult.TIMEOUT:
                self._stats.record_error()
                return DungeonRunResult(
                    result=DungeonResult.TIMEOUT,
                    chapter=self.config.target_chapter,
                    floor=self.config.target_floor,
                    error_message="Battle timeout",
                    battle_time_seconds=self.config.battle_timeout_seconds,
                )

            if battle_result == DungeonResult.CANCELLED:
                return DungeonRunResult(
                    result=DungeonResult.CANCELLED,
                    chapter=self.config.target_chapter,
                    floor=self.config.target_floor,
                )

            return self._create_error_result(f"Unexpected result: {battle_result}")

        except Exception as e:
            logger.exception(f"Dungeon run error: {e}")
            self._stats.record_error()
            return self._create_error_result(str(e))

        finally:
            self._is_running = False
            self._set_state(DungeonState.IDLE)

    def _create_error_result(self, message: str) -> DungeonRunResult:
        """Create an error result.

        Args:
            message: Error message.

        Returns:
            DungeonRunResult with ERROR status.
        """
        self._stats.record_error()
        self._set_state(DungeonState.ERROR)
        return DungeonRunResult(
            result=DungeonResult.ERROR,
            chapter=self.config.target_chapter,
            floor=self.config.target_floor,
            error_message=message,
        )

    def run_continuous(self, max_runs: int = 0) -> list[DungeonRunResult]:
        """Run dungeon continuously until stopped.

        Args:
            max_runs: Maximum runs (0 = unlimited).

        Returns:
            List of DungeonRunResult for each run.
        """
        results: list[DungeonRunResult] = []
        run_count = 0

        logger.info(f"Starting continuous dungeon farming (max_runs={max_runs})")

        while not self._should_stop:
            if max_runs > 0 and run_count >= max_runs:
                logger.info(f"Reached max runs ({max_runs})")
                break

            result = self.run()
            results.append(result)
            run_count += 1

            logger.info(
                f"Run {run_count} complete: {result.result.name} "
                f"(Total: {self._stats.victories}W/{self._stats.defeats}L)"
            )

            # Return to dungeon selection for next run
            if not self._should_stop and result.result != DungeonResult.CANCELLED:
                self._return_to_menu()
                self._delay(DEFAULT_SCREEN_WAIT_MS)

        return results

    def stop(self) -> None:
        """Stop the dungeon loop."""
        logger.info("Stopping dungeon loop...")
        self._should_stop = True

    def reset_stats(self) -> None:
        """Reset dungeon statistics."""
        self._stats = DungeonStats()
        logger.info("Dungeon stats reset")


def create_dungeon_loop(
    device: DeviceManager,
    detector: ScreenStateDetector,
    chapter: int = 1,
    floor: int = 1,
    auto_retry: bool = True,
    max_retries: int = 3,
) -> DungeonLoop:
    """Factory function to create a DungeonLoop with common settings.

    Args:
        device: Connected DeviceManager.
        detector: ScreenStateDetector instance.
        chapter: Target chapter (1-6).
        floor: Target floor (1-14).
        auto_retry: Enable auto-retry on defeat.
        max_retries: Maximum retry attempts.

    Returns:
        Configured DungeonLoop instance.
    """
    config = DungeonConfig(
        target_chapter=chapter,
        target_floor=floor,
        auto_retry=auto_retry,
        max_retries=max_retries,
    )
    return DungeonLoop(device, detector, config)
