"""Screen State Detection for Rush Royale Bot.

This module provides detection of various game screens and UI states
using template matching and feature detection.

Supported screen states:
- Home Screen (main menu)
- Battle Screen (in-fight)
- Dungeon Selection
- Popup/Dialog detection
- Advertisement detection
- Victory/Defeat screens
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from enum import auto
from pathlib import Path
from typing import Any
from typing import TypeAlias

import cv2
from numpy.typing import NDArray

# Type alias for image arrays - OpenCV uses various numpy dtypes internally
ImageArray: TypeAlias = NDArray[Any]

# Directory for icon templates
REPO_ROOT = Path(__file__).resolve().parents[3]
ICONS_DIR = REPO_ROOT / "cv-images" / "icons"


class ScreenState(Enum):
    """Enumeration of detectable game screen states.

    Each state represents a distinct screen or UI context in Rush Royale.
    """

    UNKNOWN = auto()
    """Unable to determine screen state."""

    HOME = auto()
    """Main menu / home screen."""

    BATTLE = auto()
    """In an active battle (PvP or PvE)."""

    BATTLE_PREPARATION = auto()
    """Battle preparation screen (deck selection, countdown)."""

    DUNGEON_SELECT = auto()
    """Dungeon chapter selection screen."""

    DUNGEON_FLOOR_SELECT = auto()
    """Dungeon floor selection screen within a chapter."""

    POPUP = auto()
    """Generic popup or dialog overlay."""

    ADVERTISEMENT = auto()
    """Advertisement is being displayed."""

    VICTORY = auto()
    """Victory/win screen after battle."""

    DEFEAT = auto()
    """Defeat/loss screen after battle."""

    LOADING = auto()
    """Loading screen transition."""

    TRANSIT = auto()
    """Screen transition in progress."""

    PVP_LOADING = auto()
    """PVP loading screen with abort button."""

    START_SCREEN = auto()
    """App start/splash screen."""

    QUEST = auto()
    """Quest completion popup."""

    FRIEND_MENU = auto()
    """Friend/social menu."""

    STORE_MENU = auto()
    """Store menu navigation."""

    CARDS_MENU = auto()
    """Cards menu navigation."""

    MAIN_MENU = auto()
    """Main/Battle menu navigation."""

    CLAN_MENU = auto()
    """Clan menu navigation."""

    EVENT_MENU = auto()
    """Event menu navigation."""


@dataclass
class ScreenStateResult:
    """Result of screen state detection.

    Attributes:
        state: The detected screen state.
        confidence: Confidence score (0.0 to 1.0).
        matched_template: Name of the template that matched (if any).
        region: Bounding box of the matched region (x, y, w, h).
        all_matches: Dictionary of all detected templates with confidences.
    """

    state: ScreenState
    confidence: float
    matched_template: str = ""
    region: tuple[int, int, int, int] | None = None
    all_matches: dict[str, float] = field(default_factory=dict)

    def __bool__(self) -> bool:
        """Return True if a valid state was detected with high confidence."""
        return self.state != ScreenState.UNKNOWN and self.confidence >= 0.5


@dataclass
class ScreenStateConfig:
    """Configuration for screen state detection.

    Attributes:
        template_threshold: Minimum confidence for template matching (0.0-1.0).
        use_grayscale: Whether to convert images to grayscale before matching.
        scale_templates: Whether to auto-scale templates to screenshot resolution.
        reference_width: Reference resolution width for template scaling.
        reference_height: Reference resolution height for template scaling.
    """

    template_threshold: float = 0.7
    use_grayscale: bool = False
    scale_templates: bool = True
    reference_width: int = 1080
    reference_height: int = 1920


# Mapping of template names to screen states
TEMPLATE_STATE_MAP: dict[str, ScreenState] = {
    # Home screen indicators
    "home_screen.png": ScreenState.HOME,
    "battle_icon.png": ScreenState.HOME,
    "pvp_button.png": ScreenState.HOME,
    "Home_Menu.png": ScreenState.HOME,
    "PVP_Button.png": ScreenState.HOME,
    "PVE_Button.png": ScreenState.HOME,
    "PVE_Locked.png": ScreenState.HOME,
    "ad_available.png": ScreenState.HOME,
    "green_indicator.png": ScreenState.HOME,
    "red_indicator.png": ScreenState.HOME,
    "quests_menu.png": ScreenState.HOME,
    "mm_main_button.png": ScreenState.HOME,
    "mm_mail_button.png": ScreenState.HOME,
    "mm_friend_button.png": ScreenState.HOME,
    "new_available.png": ScreenState.HOME,
    "quest_new.png": ScreenState.HOME,
    "quest_ad_available.png": ScreenState.HOME,
    "expedition_menu.png": ScreenState.HOME,
    "home_menu.png": ScreenState.HOME,
    # Battle screen indicators
    "fighting.png": ScreenState.BATTLE,
    "infight_players_healthbar.png": ScreenState.BATTLE,
    "shaman_opponent.png": ScreenState.BATTLE,
    "witch_opponent.png": ScreenState.BATTLE,
    # Dungeon chapter selection (choose chapter 1-6)
    "dungeon_modifier_bottom.png": ScreenState.DUNGEON_SELECT,
    "Dungeon_Modifier_Bottom.png": ScreenState.DUNGEON_SELECT,
    "pve_random.png": ScreenState.DUNGEON_SELECT,
    "dungeon_bottombar.png": ScreenState.DUNGEON_SELECT,
    "dungeon_locked.png": ScreenState.DUNGEON_SELECT,
    "chapter_1.png": ScreenState.DUNGEON_SELECT,
    "chapter_2.png": ScreenState.DUNGEON_SELECT,
    "chapter_3.png": ScreenState.DUNGEON_SELECT,
    "chapter_4.png": ScreenState.DUNGEON_SELECT,
    "chapter_5.png": ScreenState.DUNGEON_SELECT,
    "chapter_6.png": ScreenState.DUNGEON_SELECT,
    "Chapter_1.png": ScreenState.DUNGEON_SELECT,
    "Chapter_2.png": ScreenState.DUNGEON_SELECT,
    "Chapter_3.png": ScreenState.DUNGEON_SELECT,
    "Chapter_4.png": ScreenState.DUNGEON_SELECT,
    "Chapter_5.png": ScreenState.DUNGEON_SELECT,
    "Chapter_6.png": ScreenState.DUNGEON_SELECT,
    "Dungeon_Bottom_Bar.png": ScreenState.DUNGEON_SELECT,
    # Dungeon floor selection (choose floor within chapter)
    "floor_1.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_2.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_3.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_4.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_5.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_6.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_7.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_8.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_9.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_10.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_11.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_12.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_13.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "floor_14.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "Floor_12.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "Floor_13.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "Floor_14.png": ScreenState.DUNGEON_FLOOR_SELECT,
    "plus_200_button_on.png": ScreenState.DUNGEON_SELECT,
    "plus_200_button_off.png": ScreenState.DUNGEON_SELECT,
    # Popups and overlays
    "x_mark.png": ScreenState.POPUP,
    "back_button.png": ScreenState.POPUP,
    # Advertisements
    "ad_pve.png": ScreenState.ADVERTISEMENT,
    "ad_season.png": ScreenState.ADVERTISEMENT,
    "AD_Bonus_Button.png": ScreenState.ADVERTISEMENT,
    "ad_bonus.png": ScreenState.ADVERTISEMENT,
    "watch_ads_button.png": ScreenState.ADVERTISEMENT,
    # Loading screens
    "PVP_Loading.png": ScreenState.PVP_LOADING,
    "pvp_loading.png": ScreenState.PVP_LOADING,
    "abort_button.png": ScreenState.PVP_LOADING,
    "Abort_Button.png": ScreenState.PVP_LOADING,
    # Victory/Defeat (Continue/Quit buttons)
    "0cont_button.png": ScreenState.VICTORY,
    "cont_button.png": ScreenState.VICTORY,
    "1quit.png": ScreenState.DEFEAT,
    "quit_button.png": ScreenState.DEFEAT,
    # Quests
    "quest_collect.png": ScreenState.QUEST,
    "quest_done.png": ScreenState.QUEST,
    "Quest_New_Weekly.png": ScreenState.QUEST,
    "collect_button.png": ScreenState.QUEST,
    # Friend menu
    "friend_menu.png": ScreenState.FRIEND_MENU,
    # Menu navigation (bottom menu bar)
    "Store_Menu.png": ScreenState.STORE_MENU,
    "Cards_Menu.png": ScreenState.CARDS_MENU,
    "Main_Menu.png": ScreenState.MAIN_MENU,
    "Clan_Menu.png": ScreenState.CLAN_MENU,
    "Event_Menu.png": ScreenState.EVENT_MENU,
    "store_refresh.png": ScreenState.STORE_MENU,
    "refresh_button.png": ScreenState.STORE_MENU,
}


# Icon location map: name -> list of ScreenStates where it can be found
ICON_LOCATIONS: dict[str, list[ScreenState]] = {
    # Home screen
    "home_screen.png": [ScreenState.HOME],
    "Home_Menu.png": [ScreenState.HOME],
    "battle_icon.png": [ScreenState.HOME],
    "PVP_Button.png": [ScreenState.HOME],
    "PVE_Button.png": [ScreenState.HOME],
    "PVE_Locked.png": [ScreenState.HOME],
    "ad_available.png": [ScreenState.HOME, ScreenState.ADVERTISEMENT],
    "quest_new.png": [ScreenState.HOME, ScreenState.QUEST],
    "quests_menu.png": [ScreenState.HOME],
    "expedition_menu.png": [ScreenState.HOME],
    "green_indicator.png": [ScreenState.HOME],
    "red_indicator.png": [ScreenState.HOME],
    "new_available.png": [ScreenState.HOME],
    # Fight screen (battle)
    "fighting.png": [ScreenState.BATTLE],
    "infight_players_healthbar.png": [ScreenState.BATTLE],
    "shaman_opponent.png": [ScreenState.BATTLE],
    "witch_opponent.png": [ScreenState.BATTLE],
    # Dungeon selection (chapter/floor)
    "dungeon_modifier_bottom.png": [ScreenState.DUNGEON_SELECT],
    "Dungeon_Modifier_Bottom.png": [ScreenState.DUNGEON_SELECT],
    "pve_random.png": [ScreenState.DUNGEON_SELECT, ScreenState.DUNGEON_FLOOR_SELECT],
    "chapter_1.png": [ScreenState.DUNGEON_SELECT],
    "chapter_2.png": [ScreenState.DUNGEON_SELECT],
    "chapter_3.png": [ScreenState.DUNGEON_SELECT],
    "chapter_4.png": [ScreenState.DUNGEON_SELECT],
    "chapter_5.png": [ScreenState.DUNGEON_SELECT],
    "chapter_6.png": [ScreenState.DUNGEON_SELECT],
    "floor_1.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_2.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_3.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_4.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_5.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_6.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_7.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_8.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_9.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_10.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_11.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_12.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_13.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "floor_14.png": [ScreenState.DUNGEON_FLOOR_SELECT],
    "plus_200_button_on.png": [ScreenState.DUNGEON_SELECT],
    "plus_200_button_off.png": [ScreenState.DUNGEON_SELECT],
    # Ads
    "ad_pve.png": [ScreenState.ADVERTISEMENT],
    "ad_season.png": [ScreenState.ADVERTISEMENT],
    "AD_Bonus_Button.png": [ScreenState.ADVERTISEMENT, ScreenState.PVP_LOADING],
    "ad_bonus.png": [ScreenState.ADVERTISEMENT],
    "watch_ads_button.png": [ScreenState.ADVERTISEMENT],
    # Loading
    "PVP_Loading.png": [ScreenState.PVP_LOADING],
    "pvp_loading.png": [ScreenState.PVP_LOADING],
    "abort_button.png": [ScreenState.PVP_LOADING],
    "Abort_Button.png": [ScreenState.PVP_LOADING],
    # Victory/Defeat
    "0cont_button.png": [ScreenState.VICTORY],
    "cont_button.png": [ScreenState.VICTORY],
    "1quit.png": [ScreenState.DEFEAT],
    "quit_button.png": [ScreenState.DEFEAT],
    # Quests
    "quest_collect.png": [ScreenState.QUEST],
    "quest_done.png": [ScreenState.QUEST],
    "Quest_New_Weekly.png": [ScreenState.QUEST],
    "quest_ad_available.png": [ScreenState.QUEST, ScreenState.HOME],
    "collect_button.png": [ScreenState.QUEST],
    # Friend menu
    "friend_menu.png": [ScreenState.FRIEND_MENU],
    # Store/Shop
    "Store_Menu.png": [ScreenState.STORE_MENU],
    "store_refresh.png": [ScreenState.STORE_MENU],
    "refresh_button.png": [ScreenState.STORE_MENU],
    # Popups/Overlays
    "x_mark.png": [ScreenState.POPUP, ScreenState.HOME, ScreenState.QUEST],
    "back_button.png": [ScreenState.POPUP, ScreenState.HOME, ScreenState.DUNGEON_SELECT],
}


class ScreenStateDetector:
    """Detect the current screen state in Rush Royale.

    Uses template matching to identify various game screens like
    home screen, battle, dungeon selection, popups, and ads.

    Usage:
        detector = ScreenStateDetector()
        result = detector.detect(screenshot)

        if result.state == ScreenState.BATTLE:
            # Handle battle screen
            pass
        elif result.state == ScreenState.POPUP:
            # Close popup
            pass
    """

    def __init__(self, config: ScreenStateConfig | None = None) -> None:
        """Initialize the screen state detector.

        Args:
            config: Optional configuration. Uses defaults if None.
        """
        self.config = config or ScreenStateConfig()
        self._templates: dict[str, ImageArray] = {}
        self._template_sizes: dict[str, tuple[int, int]] = {}
        # Allow dynamic mapping so newly added icons in subfolders get a state
        self._template_state_map: dict[str, ScreenState] = dict(TEMPLATE_STATE_MAP)
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all icon templates from the icons directory."""
        if not ICONS_DIR.exists():
            return

        # Load all *.png templates recursively so nested /icons subfolders are picked up
        for template_file in ICONS_DIR.rglob("*.png"):
            if not template_file.is_file():
                continue

            # Skip reference screenshots that are not templates
            if "screenshot" in {p.lower() for p in template_file.parts}:
                continue

            img = cv2.imread(str(template_file))
            if img is None:
                continue

            # Keep name without folder to remain backward compatible with existing mappings
            name = template_file.name
            self._templates[name] = img
            self._template_sizes[name] = (img.shape[1], img.shape[0])

            # Auto-map state when not explicitly listed
            if name not in self._template_state_map:
                inferred = self._infer_state_from_path(template_file)
                if inferred != ScreenState.UNKNOWN:
                    self._template_state_map[name] = inferred

    def _infer_state_from_path(self, template_path: Path) -> ScreenState:
        """Infer screen state from folder/name conventions.

        Folder conventions:
        - home_screen/*        -> HOME
        - loading_screen/*     -> PVP_LOADING
        - pve/*: floor_* -> DUNGEON_FLOOR_SELECT, chapter_* -> DUNGEON_SELECT,
          dungeon_* / plus_* / pve_random -> DUNGEON_SELECT
        - pvp/*                -> BATTLE
        Otherwise UNKNOWN.
        """

        parent = template_path.parent.name.lower()
        name = template_path.name.lower()

        if parent == "home_screen":
            return ScreenState.HOME

        if parent == "loading_screen":
            return ScreenState.PVP_LOADING

        if parent == "pve":
            if name.startswith("floor_"):
                return ScreenState.DUNGEON_FLOOR_SELECT
            if name.startswith("chapter_"):
                return ScreenState.DUNGEON_SELECT
            if name.startswith("dungeon_"):
                return ScreenState.DUNGEON_SELECT
            if name.startswith("plus_"):
                return ScreenState.DUNGEON_SELECT
            if "pve_random" in name:
                return ScreenState.DUNGEON_SELECT
            return ScreenState.DUNGEON_SELECT

        if parent == "pvp":
            return ScreenState.BATTLE

        return ScreenState.UNKNOWN

    def _scale_template(
        self,
        template: ImageArray,
        screen_width: int,
        screen_height: int,
    ) -> ImageArray:
        """Scale a template to match the screenshot resolution.

        Args:
            template: Template image array.
            screen_width: Width of the screenshot.
            screen_height: Height of the screenshot.

        Returns:
            Scaled template image.
        """
        if not self.config.scale_templates:
            return template

        scale_x = screen_width / self.config.reference_width
        scale_y = screen_height / self.config.reference_height
        scale = min(scale_x, scale_y)  # Use uniform scale to preserve aspect

        if abs(scale - 1.0) < 0.01:  # No scaling needed
            return template

        new_width = int(template.shape[1] * scale)
        new_height = int(template.shape[0] * scale)

        if new_width < 10 or new_height < 10:
            return template  # Too small to scale

        return cv2.resize(template, (new_width, new_height))

    def _match_template(
        self,
        screenshot: ImageArray,
        template: ImageArray,
    ) -> tuple[float, tuple[int, int]]:
        """Match a single template against the screenshot.

        Args:
            screenshot: Screenshot image (BGR).
            template: Template image (BGR).

        Returns:
            Tuple of (confidence, (x, y)) of best match location.
        """
        # Convert to grayscale if configured
        if self.config.use_grayscale:
            if len(screenshot.shape) == 3:
                screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            if len(template.shape) == 3:
                template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # Scale template to match screenshot resolution
        screen_h, screen_w = screenshot.shape[:2]
        scaled_template = self._scale_template(template, screen_w, screen_h)

        # Ensure template is smaller than screenshot
        tmpl_h, tmpl_w = scaled_template.shape[:2]
        if tmpl_w > screen_w or tmpl_h > screen_h:
            return (0.0, (0, 0))

        # Perform template matching
        result = cv2.matchTemplate(screenshot, scaled_template, cv2.TM_CCOEFF_NORMED)

        # Find best match
        _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)

        return (float(max_val), (int(max_loc[0]), int(max_loc[1])))

    def detect(
        self,
        screenshot: ImageArray | str | Path,
    ) -> ScreenStateResult:
        """Detect the current screen state from a screenshot.

        Args:
            screenshot: Screenshot as numpy array (BGR), or path to image file.

        Returns:
            ScreenStateResult with detected state and confidence.
        """
        # Load image if path provided
        if isinstance(screenshot, (str, Path)):
            img = cv2.imread(str(screenshot))
            if img is None:
                return ScreenStateResult(
                    state=ScreenState.UNKNOWN,
                    confidence=0.0,
                    matched_template="",
                )
        else:
            img = screenshot

        # Match all templates
        all_matches: dict[str, float] = {}
        best_match = ""
        best_confidence = 0.0
        best_location = (0, 0)
        best_template_size = (0, 0)

        for name, template in self._templates.items():
            confidence, location = self._match_template(img, template)
            all_matches[name] = confidence

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = name
                best_location = location
                best_template_size = self._template_sizes.get(name, (0, 0))

        # Determine state from best match
        if best_confidence >= self.config.template_threshold and best_match:
            state = self._template_state_map.get(best_match, ScreenState.UNKNOWN)
            region = (
                best_location[0],
                best_location[1],
                best_template_size[0],
                best_template_size[1],
            )
        else:
            state = ScreenState.UNKNOWN
            region = None

        return ScreenStateResult(
            state=state,
            confidence=best_confidence,
            matched_template=best_match,
            region=region,
            all_matches=all_matches,
        )

    def detect_all(
        self,
        screenshot: ImageArray | str | Path,
    ) -> list[ScreenStateResult]:
        """Detect all matching screen elements above threshold.

        Useful for detecting multiple overlapping UI elements
        (e.g., popup on battle screen).

        Args:
            screenshot: Screenshot as numpy array (BGR), or path to image file.

        Returns:
            List of ScreenStateResult for all matches above threshold.
        """
        # Load image if path provided
        if isinstance(screenshot, (str, Path)):
            img = cv2.imread(str(screenshot))
            if img is None:
                return []
        else:
            img = screenshot

        results: list[ScreenStateResult] = []

        for name, template in self._templates.items():
            confidence, location = self._match_template(img, template)

            if confidence >= self.config.template_threshold:
                state = self._template_state_map.get(name, ScreenState.UNKNOWN)
                template_size = self._template_sizes.get(name, (0, 0))
                region = (
                    location[0],
                    location[1],
                    template_size[0],
                    template_size[1],
                )

                results.append(
                    ScreenStateResult(
                        state=state,
                        confidence=confidence,
                        matched_template=name,
                        region=region,
                        all_matches={name: confidence},
                    )
                )

        # Sort by confidence (highest first)
        results.sort(key=lambda r: r.confidence, reverse=True)

        return results

    def is_state(
        self,
        screenshot: ImageArray | str | Path,
        expected_state: ScreenState,
        threshold: float | None = None,
    ) -> bool:
        """Check if the screenshot matches an expected state.

        Convenience method for quick state checks.

        Args:
            screenshot: Screenshot to check.
            expected_state: Expected screen state.
            threshold: Optional custom threshold. Uses config default if None.

        Returns:
            True if the detected state matches with sufficient confidence.
        """
        result = self.detect(screenshot)
        min_conf = threshold or self.config.template_threshold

        return result.state == expected_state and result.confidence >= min_conf

    def is_in_battle(self, screenshot: ImageArray | str | Path) -> bool:
        """Check if currently in a battle.

        Args:
            screenshot: Screenshot to check.

        Returns:
            True if in battle screen.
        """
        return self.is_state(screenshot, ScreenState.BATTLE)

    def is_home_screen(self, screenshot: ImageArray | str | Path) -> bool:
        """Check if on home screen.

        Args:
            screenshot: Screenshot to check.

        Returns:
            True if on home screen.
        """
        return self.is_state(screenshot, ScreenState.HOME)

    def has_popup(self, screenshot: ImageArray | str | Path) -> bool:
        """Check if a popup/dialog is visible.

        Args:
            screenshot: Screenshot to check.

        Returns:
            True if popup is detected.
        """
        results = self.detect_all(screenshot)
        return any(r.state == ScreenState.POPUP for r in results)

    def has_advertisement(self, screenshot: ImageArray | str | Path) -> bool:
        """Check if an advertisement is visible.

        Args:
            screenshot: Screenshot to check.

        Returns:
            True if advertisement is detected.
        """
        results = self.detect_all(screenshot)
        return any(r.state == ScreenState.ADVERTISEMENT for r in results)

    def find_template(
        self,
        screenshot: ImageArray | str | Path,
        template_name: str,
    ) -> tuple[bool, tuple[int, int, int, int] | None, float]:
        """Find a specific template in the screenshot.

        Args:
            screenshot: Screenshot to search.
            template_name: Name of the template file (e.g., "x_mark.png").

        Returns:
            Tuple of (found, region, confidence) where:
            - found: True if template was found above threshold
            - region: (x, y, w, h) bounding box or None
            - confidence: Match confidence score
        """
        if template_name not in self._templates:
            return (False, None, 0.0)

        # Load image if path provided
        if isinstance(screenshot, (str, Path)):
            img = cv2.imread(str(screenshot))
            if img is None:
                return (False, None, 0.0)
        else:
            img = screenshot

        template = self._templates[template_name]
        confidence, location = self._match_template(img, template)

        if confidence >= self.config.template_threshold:
            template_size = self._template_sizes.get(template_name, (0, 0))
            region = (
                location[0],
                location[1],
                template_size[0],
                template_size[1],
            )
            return (True, region, confidence)

        return (False, None, confidence)

    def get_close_button_location(
        self,
        screenshot: ImageArray | str | Path,
    ) -> tuple[int, int] | None:
        """Find the location of a close/X button for popup dismissal.

        Args:
            screenshot: Screenshot to search.

        Returns:
            (x, y) center coordinates of close button, or None if not found.
        """
        found, region, _ = self.find_template(screenshot, "x_mark.png")

        if found and region is not None:
            x, y, w, h = region
            return (x + w // 2, y + h // 2)

        return None

    def get_back_button_location(
        self,
        screenshot: ImageArray | str | Path,
    ) -> tuple[int, int] | None:
        """Find the location of a back button.

        Args:
            screenshot: Screenshot to search.

        Returns:
            (x, y) center coordinates of back button, or None if not found.
        """
        found, region, _ = self.find_template(screenshot, "back_button.png")

        if found and region is not None:
            x, y, w, h = region
            return (x + w // 2, y + h // 2)

        return None

    @property
    def available_templates(self) -> list[str]:
        """Get list of available template names.

        Returns:
            List of template file names.
        """
        return list(self._templates.keys())

    @property
    def is_loaded(self) -> bool:
        """Check if templates were successfully loaded.

        Returns:
            True if at least one template is loaded.
        """
        return len(self._templates) > 0

    def detect_menu_context(
        self,
        screenshot: ImageArray | str | Path,
        min_confidence: float = 0.90,
    ) -> ScreenStateResult:
        """Detect current menu context from bottom menu bar.

        CRITICAL: This should be called FIRST before any icon detection
        to determine the current menu context.

        Args:
            screenshot: Screenshot to analyze.
            min_confidence: Minimum confidence threshold (default 0.90).

        Returns:
            ScreenStateResult with menu state (STORE_MENU, CARDS_MENU, etc.)
            or UNKNOWN if no menu detected.
        """
        # Load image if path provided
        if isinstance(screenshot, (str, Path)):
            img = cv2.imread(str(screenshot))
            if img is None:
                return ScreenStateResult(
                    state=ScreenState.UNKNOWN,
                    confidence=0.0,
                )
        else:
            img = screenshot

        screen_h, _screen_w = img.shape[:2]

        # Calculate ROI for bottom menu bar
        # Reference: Y=1414-1600 for 1080x1920 resolution
        roi_y_start_ref = 1414
        roi_y_end_ref = 1600
        ref_height = 1920

        scale_y = screen_h / ref_height
        roi_y_start = int(roi_y_start_ref * scale_y)
        roi_y_end = int(roi_y_end_ref * scale_y)

        # Ensure ROI is within screen bounds
        roi_y_start = max(0, roi_y_start)
        roi_y_end = min(screen_h, roi_y_end)

        # Extract ROI (bottom menu bar)
        roi = img[roi_y_start:roi_y_end, :]

        # Menu templates to check (in priority order)
        menu_templates = [
            "Store_Menu.png",
            "Cards_Menu.png",
            "Main_Menu.png",
            "Clan_Menu.png",
            "Event_Menu.png",
        ]

        best_match = ""
        best_confidence = 0.0
        best_location = (0, 0)
        best_template_size = (0, 0)

        for template_name in menu_templates:
            if template_name not in self._templates:
                continue

            template = self._templates[template_name]
            confidence, location = self._match_template(roi, template)

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = template_name
                # Adjust location to full screenshot coordinates
                best_location = (location[0], location[1] + roi_y_start)
                best_template_size = self._template_sizes.get(template_name, (0, 0))

        # Determine state from best match
        if best_confidence >= min_confidence and best_match:
            state = self._template_state_map.get(best_match, ScreenState.UNKNOWN)
            region = (
                best_location[0],
                best_location[1],
                best_template_size[0],
                best_template_size[1],
            )
        else:
            state = ScreenState.UNKNOWN
            region = None

        return ScreenStateResult(
            state=state,
            confidence=best_confidence,
            matched_template=best_match,
            region=region,
        )

    def detect_with_roi(
        self,
        screenshot: ImageArray | str | Path,
        roi: tuple[int, int, int, int] | None = None,
        min_confidence: float | None = None,
    ) -> ScreenStateResult:
        """Detect screen state within a specific Region of Interest.

        Args:
            screenshot: Screenshot to analyze.
            roi: Region of interest as (x, y, width, height). If None, uses full image.
            min_confidence: Custom confidence threshold. Uses config default if None.

        Returns:
            ScreenStateResult with detected state.
        """
        # Load image if path provided
        if isinstance(screenshot, (str, Path)):
            img = cv2.imread(str(screenshot))
            if img is None:
                return ScreenStateResult(
                    state=ScreenState.UNKNOWN,
                    confidence=0.0,
                )
        else:
            img = screenshot

        # Extract ROI if specified
        roi_offset_x = 0
        roi_offset_y = 0

        if roi is not None:
            x, y, w, h = roi
            screen_h, screen_w = img.shape[:2]

            # Validate ROI bounds
            x = max(0, min(x, screen_w - 1))
            y = max(0, min(y, screen_h - 1))
            w = max(1, min(w, screen_w - x))
            h = max(1, min(h, screen_h - y))

            img = img[y : y + h, x : x + w]
            roi_offset_x = x
            roi_offset_y = y

        # Match templates
        threshold = min_confidence or self.config.template_threshold
        all_matches: dict[str, float] = {}
        best_match = ""
        best_confidence = 0.0
        best_location = (0, 0)
        best_template_size = (0, 0)

        for name, template in self._templates.items():
            confidence, location = self._match_template(img, template)
            all_matches[name] = confidence

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = name
                # Adjust location to full screenshot coordinates
                best_location = (location[0] + roi_offset_x, location[1] + roi_offset_y)
                best_template_size = self._template_sizes.get(name, (0, 0))

        # Determine state from best match
        if best_confidence >= threshold and best_match:
            state = self._template_state_map.get(best_match, ScreenState.UNKNOWN)
            region = (
                best_location[0],
                best_location[1],
                best_template_size[0],
                best_template_size[1],
            )
        else:
            state = ScreenState.UNKNOWN
            region = None

        return ScreenStateResult(
            state=state,
            confidence=best_confidence,
            matched_template=best_match,
            region=region,
            all_matches=all_matches,
        )

    def is_loading_screen(self, screenshot: ImageArray | str | Path) -> bool:
        """Check if any loading screen is visible.

        Args:
            screenshot: Screenshot to check.

        Returns:
            True if loading screen (generic or PVP) is detected.
        """
        results = self.detect_all(screenshot)
        return any(r.state in (ScreenState.LOADING, ScreenState.PVP_LOADING) for r in results)

    def is_pvp_loading(self, screenshot: ImageArray | str | Path) -> bool:
        """Check if PVP loading screen is visible.

        Args:
            screenshot: Screenshot to check.

        Returns:
            True if PVP loading screen is detected.
        """
        return self.is_state(screenshot, ScreenState.PVP_LOADING)

    def get_abort_button_location(
        self,
        screenshot: ImageArray | str | Path,
    ) -> tuple[int, int] | None:
        """Find the location of the abort button on PVP loading screen.

        Args:
            screenshot: Screenshot to search.

        Returns:
            (x, y) center coordinates of abort button, or None if not found.
        """
        found, region, _ = self.find_template(screenshot, "Abort_Button.png")

        if found and region is not None:
            x, y, w, h = region
            return (x + w // 2, y + h // 2)

        return None

    def has_ad_bonus_button(self, screenshot: ImageArray | str | Path) -> bool:
        """Check if the ad bonus button is visible.

        Args:
            screenshot: Screenshot to check.

        Returns:
            True if ad bonus button is detected.
        """
        found, _, confidence = self.find_template(screenshot, "AD_Bonus_Button.png")
        return found and confidence >= self.config.template_threshold


# ============================================================================
# State Machine for Screen State Transitions (T015)
# ============================================================================


@dataclass
class StateHistoryEntry:
    """A single entry in the state history log.

    Attributes:
        state: The screen state.
        timestamp: When the state was detected.
        confidence: Detection confidence.
        iteration: Iteration number within this state.
    """

    state: ScreenState
    timestamp: float
    confidence: float
    iteration: int = 1


@dataclass
class StateTransition:
    """Defines valid state transitions.

    Attributes:
        from_state: Source state.
        to_state: Target state.
        required_time_ms: Minimum time before transition is valid (ms).
        max_iterations: Maximum allowed iterations before forced transition.
    """

    from_state: ScreenState
    to_state: ScreenState
    required_time_ms: int = 0
    max_iterations: int = 10


# Valid state transitions in the game flow
VALID_TRANSITIONS: list[StateTransition] = [
    # Start screen can go to home or loading
    StateTransition(ScreenState.START_SCREEN, ScreenState.HOME),
    StateTransition(ScreenState.START_SCREEN, ScreenState.LOADING),
    # Home screen transitions
    StateTransition(ScreenState.HOME, ScreenState.DUNGEON_SELECT),
    StateTransition(ScreenState.HOME, ScreenState.PVP_LOADING),
    StateTransition(ScreenState.HOME, ScreenState.LOADING),
    StateTransition(ScreenState.HOME, ScreenState.QUEST),
    StateTransition(ScreenState.HOME, ScreenState.POPUP),
    StateTransition(ScreenState.HOME, ScreenState.STORE_MENU),
    StateTransition(ScreenState.HOME, ScreenState.CARDS_MENU),
    StateTransition(ScreenState.HOME, ScreenState.CLAN_MENU),
    StateTransition(ScreenState.HOME, ScreenState.EVENT_MENU),
    StateTransition(ScreenState.HOME, ScreenState.ADVERTISEMENT),
    # Dungeon chapter selection
    StateTransition(ScreenState.DUNGEON_SELECT, ScreenState.DUNGEON_FLOOR_SELECT),
    StateTransition(ScreenState.DUNGEON_SELECT, ScreenState.HOME),
    StateTransition(ScreenState.DUNGEON_SELECT, ScreenState.POPUP),
    # Dungeon floor selection
    StateTransition(ScreenState.DUNGEON_FLOOR_SELECT, ScreenState.BATTLE_PREPARATION),
    StateTransition(ScreenState.DUNGEON_FLOOR_SELECT, ScreenState.LOADING),
    StateTransition(ScreenState.DUNGEON_FLOOR_SELECT, ScreenState.DUNGEON_SELECT),
    StateTransition(ScreenState.DUNGEON_FLOOR_SELECT, ScreenState.POPUP),
    # Battle preparation
    StateTransition(ScreenState.BATTLE_PREPARATION, ScreenState.BATTLE),
    StateTransition(ScreenState.BATTLE_PREPARATION, ScreenState.LOADING),
    StateTransition(ScreenState.BATTLE_PREPARATION, ScreenState.HOME),
    # PVP loading
    StateTransition(ScreenState.PVP_LOADING, ScreenState.BATTLE),
    StateTransition(ScreenState.PVP_LOADING, ScreenState.HOME, max_iterations=30),
    # Battle transitions
    StateTransition(ScreenState.BATTLE, ScreenState.VICTORY),
    StateTransition(ScreenState.BATTLE, ScreenState.DEFEAT),
    StateTransition(ScreenState.BATTLE, ScreenState.LOADING),
    # Victory/Defeat
    StateTransition(ScreenState.VICTORY, ScreenState.HOME),
    StateTransition(ScreenState.VICTORY, ScreenState.DUNGEON_SELECT),
    StateTransition(ScreenState.VICTORY, ScreenState.ADVERTISEMENT),
    StateTransition(ScreenState.VICTORY, ScreenState.QUEST),
    StateTransition(ScreenState.DEFEAT, ScreenState.HOME),
    StateTransition(ScreenState.DEFEAT, ScreenState.DUNGEON_SELECT),
    # Loading transitions (can go anywhere)
    StateTransition(ScreenState.LOADING, ScreenState.HOME),
    StateTransition(ScreenState.LOADING, ScreenState.BATTLE),
    StateTransition(ScreenState.LOADING, ScreenState.DUNGEON_SELECT),
    StateTransition(ScreenState.LOADING, ScreenState.VICTORY),
    StateTransition(ScreenState.LOADING, ScreenState.DEFEAT),
    # Transit screen (temporary)
    StateTransition(ScreenState.TRANSIT, ScreenState.HOME),
    StateTransition(ScreenState.TRANSIT, ScreenState.BATTLE),
    StateTransition(ScreenState.TRANSIT, ScreenState.LOADING),
    # Popups can return to many states
    StateTransition(ScreenState.POPUP, ScreenState.HOME),
    StateTransition(ScreenState.POPUP, ScreenState.BATTLE),
    StateTransition(ScreenState.POPUP, ScreenState.DUNGEON_SELECT),
    StateTransition(ScreenState.POPUP, ScreenState.DUNGEON_FLOOR_SELECT),
    # Quest popup
    StateTransition(ScreenState.QUEST, ScreenState.HOME),
    StateTransition(ScreenState.QUEST, ScreenState.POPUP),
    # Advertisement
    StateTransition(ScreenState.ADVERTISEMENT, ScreenState.HOME),
    StateTransition(ScreenState.ADVERTISEMENT, ScreenState.VICTORY),
    StateTransition(ScreenState.ADVERTISEMENT, ScreenState.POPUP),
    # Menu transitions
    StateTransition(ScreenState.STORE_MENU, ScreenState.HOME),
    StateTransition(ScreenState.CARDS_MENU, ScreenState.HOME),
    StateTransition(ScreenState.CLAN_MENU, ScreenState.HOME),
    StateTransition(ScreenState.EVENT_MENU, ScreenState.HOME),
]


class ScreenStateMachine:
    """State machine for managing screen state transitions.

    Provides state history tracking, transition validation, and
    timeout handling to prevent the bot from getting stuck.

    Usage:
        machine = ScreenStateMachine()
        detector = ScreenStateDetector()

        # In bot loop:
        result = detector.detect(screenshot)
        transition = machine.update(result.state, result.confidence)

        if transition.is_timeout:
            # Handle stuck state
            pass
    """

    DEFAULT_MAX_ITERATIONS = 10
    DEFAULT_HISTORY_SIZE = 100

    def __init__(
        self,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        history_size: int = DEFAULT_HISTORY_SIZE,
    ) -> None:
        """Initialize the state machine.

        Args:
            max_iterations: Default max iterations per state before timeout.
            history_size: Maximum history entries to keep.
        """
        self._max_iterations = max_iterations
        self._history_size = history_size
        self._current_state = ScreenState.UNKNOWN
        self._current_iteration = 0
        self._last_transition_time = 0.0
        self._history: list[StateHistoryEntry] = []
        self._logger = __import__("logging").getLogger("screen_state_machine")

        # Build transition lookup
        self._valid_transitions: dict[ScreenState, dict[ScreenState, StateTransition]] = {}
        for trans in VALID_TRANSITIONS:
            if trans.from_state not in self._valid_transitions:
                self._valid_transitions[trans.from_state] = {}
            self._valid_transitions[trans.from_state][trans.to_state] = trans

    @property
    def current_state(self) -> ScreenState:
        """Get the current state."""
        return self._current_state

    @property
    def current_iteration(self) -> int:
        """Get iteration count in current state."""
        return self._current_iteration

    @property
    def history(self) -> list[StateHistoryEntry]:
        """Get the state history (read-only copy)."""
        return list(self._history)

    def update(
        self,
        detected_state: ScreenState,
        confidence: float = 1.0,
    ) -> tuple[bool, str]:
        """Update the state machine with a new detection.

        Args:
            detected_state: The newly detected screen state.
            confidence: Detection confidence score.

        Returns:
            Tuple of (state_changed, message).
        """
        import time

        now = time.time()

        # Same state - increment iteration
        if detected_state == self._current_state:
            self._current_iteration += 1
            self._add_history(detected_state, now, confidence, self._current_iteration)

            # Check for timeout
            max_iter = self._max_iterations
            if self._current_state in self._valid_transitions:
                # Find the lowest max_iterations for any valid transition
                for trans in self._valid_transitions[self._current_state].values():
                    if trans.max_iterations < max_iter:
                        max_iter = trans.max_iterations

            if self._current_iteration >= max_iter:
                msg = (
                    f"State timeout: {self._current_state.name} "
                    f"after {self._current_iteration} iterations"
                )
                self._logger.warning(msg)
                return False, msg

            return False, f"Same state: {self._current_state.name} (iter {self._current_iteration})"

        # State change - validate transition
        is_valid = self._is_valid_transition(self._current_state, detected_state)
        old_state = self._current_state

        # Accept transition (valid or forced)
        self._current_state = detected_state
        self._current_iteration = 1
        self._last_transition_time = now
        self._add_history(detected_state, now, confidence, 1)

        if is_valid:
            msg = f"Valid transition: {old_state.name} → {detected_state.name}"
            self._logger.info(msg)
        else:
            msg = f"Unexpected transition: {old_state.name} → {detected_state.name}"
            self._logger.warning(msg)

        return True, msg

    def _is_valid_transition(
        self,
        from_state: ScreenState,
        to_state: ScreenState,
    ) -> bool:
        """Check if a state transition is valid.

        Args:
            from_state: Current state.
            to_state: Target state.

        Returns:
            True if transition is valid.
        """
        # Unknown state can transition to anything
        if from_state == ScreenState.UNKNOWN:
            return True

        # Check explicit transitions
        if from_state in self._valid_transitions:
            if to_state in self._valid_transitions[from_state]:
                return True

        return False

    def _add_history(
        self,
        state: ScreenState,
        timestamp: float,
        confidence: float,
        iteration: int,
    ) -> None:
        """Add an entry to the state history.

        Args:
            state: The screen state.
            timestamp: Detection timestamp.
            confidence: Detection confidence.
            iteration: Iteration number.
        """
        entry = StateHistoryEntry(
            state=state,
            timestamp=timestamp,
            confidence=confidence,
            iteration=iteration,
        )
        self._history.append(entry)

        # Trim history if needed
        if len(self._history) > self._history_size:
            self._history = self._history[-self._history_size :]

    def reset(self) -> None:
        """Reset the state machine to initial state."""
        self._current_state = ScreenState.UNKNOWN
        self._current_iteration = 0
        self._last_transition_time = 0.0
        self._history.clear()

    def is_stuck(self, max_same_state: int | None = None) -> bool:
        """Check if the bot appears stuck in a state.

        Args:
            max_same_state: Override for max iterations check.

        Returns:
            True if state has exceeded max iterations.
        """
        threshold = max_same_state or self._max_iterations
        return self._current_iteration >= threshold

    def get_expected_states(self) -> list[ScreenState]:
        """Get list of valid next states from current state.

        Returns:
            List of valid next states.
        """
        if self._current_state in self._valid_transitions:
            return list(self._valid_transitions[self._current_state].keys())
        return []

    def format_history(self, last_n: int = 10) -> str:
        """Format recent history for logging.

        Args:
            last_n: Number of recent entries to include.

        Returns:
            Formatted history string.
        """
        entries = self._history[-last_n:] if self._history else []
        lines = ["State History:"]
        for entry in entries:
            lines.append(
                f"  [{entry.timestamp:.2f}] {entry.state.name} "
                f"(conf={entry.confidence:.2f}, iter={entry.iteration})"
            )
        return "\n".join(lines)
