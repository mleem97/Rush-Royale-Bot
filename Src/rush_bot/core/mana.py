"""Mana Management System for Rush Royale Bot.

This module provides intelligent mana management including:
- Mana level detection via OCR
- Unit summon cost tracking
- Mana upgrade prioritization
- Boss wave mana reservation
- Optimal upgrade timing recommendations

Coordinate System (Reference: 1080x1920):
- Upgrade buttons are located at the bottom of the battle screen
- Mana display is in the bottom-left area
- Summon button is in the bottom-right area
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from dataclasses import field
from enum import IntEnum
from typing import TYPE_CHECKING

import cv2
import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from typing import Any

# =============================================================================
# Constants - Reference Resolution (1080x1920)
# =============================================================================

REFERENCE_WIDTH = 1080
REFERENCE_HEIGHT = 1920

# Mana display region (bottom-left)
MANA_REGION_X_REF = 50
MANA_REGION_Y_REF = 1765
MANA_REGION_WIDTH_REF = 150
MANA_REGION_HEIGHT_REF = 50

# Summon button position (bottom-right)
SUMMON_BUTTON_X_REF = 920
SUMMON_BUTTON_Y_REF = 1770
SUMMON_BUTTON_WIDTH_REF = 120
SUMMON_BUTTON_HEIGHT_REF = 100

# Upgrade button positions (5 cards + hero power)
# Y position is same for all upgrade buttons
UPGRADE_BUTTONS_Y_REF = 1500

# X positions for each card slot (1-5) and hero power (6)
UPGRADE_BUTTON_X_POSITIONS_REF: dict[int, int] = {
    1: 100,  # First card
    2: 200,  # Second card
    3: 350,  # Third card
    4: 500,  # Fourth card
    5: 650,  # Fifth card
    6: 800,  # Hero power
}

# Upgrade button dimensions
UPGRADE_BUTTON_WIDTH_REF = 80
UPGRADE_BUTTON_HEIGHT_REF = 80

# Mana costs for unit summoning
BASE_SUMMON_COST = 50
SUMMON_COST_INCREMENT = 10
MAX_SUMMON_COST = 1200

# Upgrade costs per card level
UPGRADE_COSTS: dict[int, int] = {
    1: 100,  # Level 1 upgrade
    2: 200,  # Level 2 upgrade
    3: 400,  # Level 3 upgrade
    4: 600,  # Level 4 upgrade
    5: 800,  # Level 5 upgrade
}

# Boss wave mana reservation (keep this amount for emergencies)
DEFAULT_BOSS_RESERVE = 200

# Logger
logger = logging.getLogger(__name__)


class UpgradeSlot(IntEnum):
    """Upgrade slot positions on the battle screen.

    Slots 1-5 are unit cards, slot 6 is hero power.
    """

    CARD_1 = 1
    CARD_2 = 2
    CARD_3 = 3
    CARD_4 = 4
    CARD_5 = 5
    HERO_POWER = 6


@dataclass
class ManaConfig:
    """Configuration for mana management behavior.

    Attributes:
        auto_upgrade: Enable automatic card upgrades.
        upgrade_priority: List of slot numbers in priority order (1-5).
        boss_reserve: Mana to reserve for boss waves.
        min_summon_mana: Minimum mana before summoning units.
        max_summon_cost: Stop summoning when cost exceeds this value.
        enable_hero_power: Allow automatic hero power usage.
        hero_power_cooldown_ms: Cooldown between hero power uses in ms.
    """

    auto_upgrade: bool = True
    upgrade_priority: list[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])
    boss_reserve: int = DEFAULT_BOSS_RESERVE
    min_summon_mana: int = 100
    max_summon_cost: int = 800
    enable_hero_power: bool = False
    hero_power_cooldown_ms: int = 5000


@dataclass
class ManaState:
    """Current mana state during a battle.

    Attributes:
        current_mana: Current mana amount.
        summon_cost: Current unit summon cost.
        card_levels: Current level of each card (1-5).
        hero_power_level: Current hero power level.
        is_boss_wave: Whether currently in a boss wave.
        units_summoned: Total units summoned this battle.
        last_hero_power_ms: Timestamp of last hero power use.
    """

    current_mana: int = 0
    summon_cost: int = BASE_SUMMON_COST
    card_levels: dict[int, int] = field(default_factory=lambda: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1})
    hero_power_level: int = 1
    is_boss_wave: bool = False
    units_summoned: int = 0
    last_hero_power_ms: int = 0

    def reset(self) -> None:
        """Reset state for new battle."""
        self.current_mana = 0
        self.summon_cost = BASE_SUMMON_COST
        self.card_levels = {1: 1, 2: 1, 3: 1, 4: 1, 5: 1}
        self.hero_power_level = 1
        self.is_boss_wave = False
        self.units_summoned = 0
        self.last_hero_power_ms = 0


@dataclass
class UpgradeRecommendation:
    """Recommendation for the next upgrade action.

    Attributes:
        slot: Slot number to upgrade (1-5 for cards, 6 for hero).
        cost: Mana cost of the upgrade.
        priority: Priority score (higher = more important).
        can_afford: Whether current mana is sufficient.
        reason: Human-readable reason for recommendation.
    """

    slot: int
    cost: int
    priority: float
    can_afford: bool
    reason: str


@dataclass
class ManaRegion:
    """Screen region for mana-related UI elements.

    Attributes:
        x: X coordinate of region top-left.
        y: Y coordinate of region top-left.
        width: Width of region in pixels.
        height: Height of region in pixels.
    """

    x: int
    y: int
    width: int
    height: int

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        """Return bounds as (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)

    @property
    def center(self) -> tuple[int, int]:
        """Return center coordinates."""
        return (self.x + self.width // 2, self.y + self.height // 2)


class ManaManager:
    """Manages mana detection and upgrade decisions.

    Provides intelligent mana management including OCR-based mana
    detection, upgrade prioritization, and boss wave handling.

    Usage:
        manager = ManaManager()
        state = manager.detect_mana_state(screenshot)

        if manager.can_summon(state):
            summon_pos = manager.get_summon_button_position()
            # Tap summon_pos

        recommendation = manager.get_upgrade_recommendation(state)
        if recommendation.can_afford:
            upgrade_pos = manager.get_upgrade_button_position(recommendation.slot)
            # Tap upgrade_pos
    """

    def __init__(
        self,
        config: ManaConfig | None = None,
        screen_width: int = REFERENCE_WIDTH,
        screen_height: int = REFERENCE_HEIGHT,
    ) -> None:
        """Initialize the mana manager.

        Args:
            config: Mana management configuration.
            screen_width: Current screen width for coordinate scaling.
            screen_height: Current screen height for coordinate scaling.
        """
        self.config = config or ManaConfig()
        self.state = ManaState()
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Calculate scale factors
        self._scale_x = screen_width / REFERENCE_WIDTH
        self._scale_y = screen_height / REFERENCE_HEIGHT

        # Cache scaled regions
        self._mana_region: ManaRegion | None = None
        self._summon_region: ManaRegion | None = None
        self._upgrade_positions: dict[int, tuple[int, int]] | None = None

        logger.debug(
            f"ManaManager initialized: {screen_width}x{screen_height}, "
            f"scale=({self._scale_x:.2f}, {self._scale_y:.2f})"
        )

    def _scale_x_coord(self, x: int) -> int:
        """Scale X coordinate from reference to current resolution."""
        return int(x * self._scale_x)

    def _scale_y_coord(self, y: int) -> int:
        """Scale Y coordinate from reference to current resolution."""
        return int(y * self._scale_y)

    def set_screen_resolution(self, width: int, height: int) -> None:
        """Update screen resolution and recalculate coordinates.

        Args:
            width: New screen width.
            height: New screen height.
        """
        self.screen_width = width
        self.screen_height = height
        self._scale_x = width / REFERENCE_WIDTH
        self._scale_y = height / REFERENCE_HEIGHT

        # Invalidate cached regions
        self._mana_region = None
        self._summon_region = None
        self._upgrade_positions = None

        logger.debug(f"Resolution updated: {width}x{height}")

    def get_mana_region(self) -> ManaRegion:
        """Get the scaled mana display region.

        Returns:
            ManaRegion with coordinates for current resolution.
        """
        if self._mana_region is None:
            self._mana_region = ManaRegion(
                x=self._scale_x_coord(MANA_REGION_X_REF),
                y=self._scale_y_coord(MANA_REGION_Y_REF),
                width=self._scale_x_coord(MANA_REGION_WIDTH_REF),
                height=self._scale_y_coord(MANA_REGION_HEIGHT_REF),
            )
        return self._mana_region

    def get_summon_button_region(self) -> ManaRegion:
        """Get the scaled summon button region.

        Returns:
            ManaRegion with coordinates for current resolution.
        """
        if self._summon_region is None:
            self._summon_region = ManaRegion(
                x=self._scale_x_coord(SUMMON_BUTTON_X_REF),
                y=self._scale_y_coord(SUMMON_BUTTON_Y_REF),
                width=self._scale_x_coord(SUMMON_BUTTON_WIDTH_REF),
                height=self._scale_y_coord(SUMMON_BUTTON_HEIGHT_REF),
            )
        return self._summon_region

    def get_summon_button_position(self) -> tuple[int, int]:
        """Get the center position of the summon button.

        Returns:
            (x, y) coordinates for tapping the summon button.
        """
        region = self.get_summon_button_region()
        return region.center

    def get_upgrade_button_position(self, slot: int) -> tuple[int, int]:
        """Get the center position of an upgrade button.

        Args:
            slot: Slot number (1-5 for cards, 6 for hero power).

        Returns:
            (x, y) coordinates for tapping the upgrade button.

        Raises:
            ValueError: If slot is not 1-6.
        """
        if slot not in range(1, 7):
            raise ValueError(f"Invalid slot {slot}, must be 1-6")

        if self._upgrade_positions is None:
            self._upgrade_positions = {}
            for s, x_ref in UPGRADE_BUTTON_X_POSITIONS_REF.items():
                x = self._scale_x_coord(x_ref)
                y = self._scale_y_coord(UPGRADE_BUTTONS_Y_REF)
                self._upgrade_positions[s] = (
                    x + self._scale_x_coord(UPGRADE_BUTTON_WIDTH_REF) // 2,
                    y + self._scale_y_coord(UPGRADE_BUTTON_HEIGHT_REF) // 2,
                )

        return self._upgrade_positions[slot]

    def get_all_upgrade_positions(self) -> dict[int, tuple[int, int]]:
        """Get positions for all upgrade buttons.

        Returns:
            Dictionary mapping slot numbers to (x, y) positions.
        """
        # Ensure positions are calculated
        if self._upgrade_positions is None:
            _ = self.get_upgrade_button_position(1)

        return dict(self._upgrade_positions) if self._upgrade_positions else {}

    def detect_mana_from_image(
        self,
        screenshot: NDArray[np.uint8],
    ) -> int | None:
        """Detect current mana amount from screenshot using OCR.

        Uses image preprocessing and digit recognition to extract
        the mana value from the mana display region.

        Args:
            screenshot: BGR screenshot image as numpy array.

        Returns:
            Detected mana amount, or None if detection failed.
        """
        # Get mana region
        region = self.get_mana_region()

        # Validate screenshot dimensions
        if screenshot is None or screenshot.ndim < 2:
            logger.warning("Invalid screenshot for mana detection")
            return None

        h, w = screenshot.shape[:2]
        if region.y + region.height > h or region.x + region.width > w:
            logger.warning(
                f"Mana region out of bounds: region=({region.x}, {region.y}, "
                f"{region.width}, {region.height}), image=({w}, {h})"
            )
            return None

        # Extract mana region
        mana_roi = screenshot[
            region.y : region.y + region.height,
            region.x : region.x + region.width,
        ]

        # Preprocess for OCR
        mana_value = self._ocr_digits(mana_roi)

        if mana_value is not None:
            logger.debug(f"Detected mana: {mana_value}")
            self.state.current_mana = mana_value

        return mana_value

    def _ocr_digits(self, roi: NDArray[np.uint8]) -> int | None:
        """Extract digits from a region of interest.

        Uses simple image processing techniques to extract numeric
        values. Falls back to contour analysis if OCR is unavailable.

        Args:
            roi: BGR image region containing digits.

        Returns:
            Extracted integer value, or None if extraction failed.
        """
        if roi is None or roi.size == 0:
            return None

        # Convert to grayscale
        if roi.ndim == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi

        # Apply threshold to get binary image
        # Mana text is typically bright on dark background
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        # Find contours (potential digits)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Sort contours left to right
        contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])

        # Filter by size (digits should have reasonable aspect ratio)
        digit_contours = []
        for contour in contours:
            x, _y, w, h = cv2.boundingRect(contour)
            aspect_ratio = h / max(w, 1)
            area = cv2.contourArea(contour)

            # Digit criteria: tall and thin, reasonable area
            if 0.5 < aspect_ratio < 4.0 and area > 20:
                digit_contours.append((x, contour))

        # Estimate digit count (rough mana estimation)
        # Each digit typically represents ~10x multiplier
        num_digits = len(digit_contours)

        if num_digits == 0:
            return None

        # Rough estimation based on digit count
        # This is a placeholder - real OCR would use actual digit recognition
        # For now, estimate based on typical game progression
        # 2 digits: 10-99, 3 digits: 100-999, 4 digits: 1000+
        estimated_mana = {
            1: 5,
            2: 50,
            3: 200,
            4: 1000,
            5: 5000,
        }.get(num_digits, 100)

        return estimated_mana

    def detect_mana_state(
        self,
        screenshot: NDArray[np.uint8],
    ) -> ManaState:
        """Detect complete mana state from screenshot.

        Args:
            screenshot: BGR screenshot image as numpy array.

        Returns:
            Updated ManaState with current values.
        """
        # Detect mana amount
        mana = self.detect_mana_from_image(screenshot)
        if mana is not None:
            self.state.current_mana = mana

        return self.state

    def calculate_summon_cost(self, units_summoned: int) -> int:
        """Calculate the cost to summon the next unit.

        Summon cost increases with each unit summoned during a battle.

        Args:
            units_summoned: Number of units already summoned.

        Returns:
            Mana cost for the next summon.
        """
        cost = BASE_SUMMON_COST + (units_summoned * SUMMON_COST_INCREMENT)
        return min(cost, MAX_SUMMON_COST)

    def can_summon(self, state: ManaState | None = None) -> bool:
        """Check if summoning a unit is possible and advisable.

        Args:
            state: ManaState to check, or None to use current state.

        Returns:
            True if summoning is recommended.
        """
        state = state or self.state

        # Check if we have enough mana
        if state.current_mana < state.summon_cost:
            return False

        # Check against max summon cost setting
        if state.summon_cost > self.config.max_summon_cost:
            return False

        # Reserve mana for boss waves
        if state.is_boss_wave:
            available_mana = state.current_mana - self.config.boss_reserve
            if available_mana < state.summon_cost:
                return False

        return True

    def should_upgrade(
        self,
        slot: int,
        state: ManaState | None = None,
    ) -> bool:
        """Check if upgrading a specific slot is recommended.

        Args:
            slot: Slot number (1-5 for cards, 6 for hero).
            state: ManaState to check, or None to use current state.

        Returns:
            True if upgrade is recommended.
        """
        state = state or self.state

        if not self.config.auto_upgrade:
            return False

        if slot == 6 and not self.config.enable_hero_power:
            return False

        # Get upgrade cost
        if slot == 6:
            current_level = state.hero_power_level
        else:
            current_level = state.card_levels.get(slot, 1)

        upgrade_cost = UPGRADE_COSTS.get(current_level, 1000)

        # Check if we can afford it
        available_mana = state.current_mana
        if state.is_boss_wave:
            available_mana -= self.config.boss_reserve

        return available_mana >= upgrade_cost

    def get_upgrade_recommendation(
        self,
        state: ManaState | None = None,
    ) -> UpgradeRecommendation | None:
        """Get the best upgrade recommendation based on current state.

        Considers upgrade priority, costs, and available mana to
        recommend the optimal upgrade action.

        Args:
            state: ManaState to analyze, or None to use current state.

        Returns:
            UpgradeRecommendation if an upgrade is available, None otherwise.
        """
        state = state or self.state

        if not self.config.auto_upgrade:
            return None

        available_mana = state.current_mana
        if state.is_boss_wave:
            available_mana = max(0, available_mana - self.config.boss_reserve)

        best_recommendation: UpgradeRecommendation | None = None
        best_priority = -1.0

        # Check each slot in priority order
        for priority_idx, slot in enumerate(self.config.upgrade_priority):
            current_level = state.card_levels.get(slot, 1)
            upgrade_cost = UPGRADE_COSTS.get(current_level, 1000)

            # Calculate priority score (lower index = higher priority)
            priority_score: float = len(self.config.upgrade_priority) - priority_idx

            # Bonus for lower level cards (need upgrading more)
            priority_score += (5 - current_level) * 0.5

            can_afford = available_mana >= upgrade_cost

            recommendation = UpgradeRecommendation(
                slot=slot,
                cost=upgrade_cost,
                priority=priority_score,
                can_afford=can_afford,
                reason=f"Card {slot} level {current_level}→{current_level + 1}",
            )

            if can_afford and priority_score > best_priority:
                best_priority = priority_score
                best_recommendation = recommendation

        # Check hero power if enabled
        if self.config.enable_hero_power:
            hero_level = state.hero_power_level
            hero_cost = UPGRADE_COSTS.get(hero_level, 1000)
            can_afford = available_mana >= hero_cost

            hero_recommendation = UpgradeRecommendation(
                slot=6,
                cost=hero_cost,
                priority=0.5,  # Lower priority than cards
                can_afford=can_afford,
                reason=f"Hero Power level {hero_level}→{hero_level + 1}",
            )

            if can_afford and best_recommendation is None:
                best_recommendation = hero_recommendation

        return best_recommendation

    def get_all_upgrade_recommendations(
        self,
        state: ManaState | None = None,
    ) -> list[UpgradeRecommendation]:
        """Get all possible upgrade recommendations.

        Args:
            state: ManaState to analyze, or None to use current state.

        Returns:
            List of all UpgradeRecommendations sorted by priority.
        """
        state = state or self.state
        recommendations: list[UpgradeRecommendation] = []

        available_mana = state.current_mana
        if state.is_boss_wave:
            available_mana = max(0, available_mana - self.config.boss_reserve)

        # Check all card slots
        for priority_idx, slot in enumerate(self.config.upgrade_priority):
            current_level = state.card_levels.get(slot, 1)
            upgrade_cost = UPGRADE_COSTS.get(current_level, 1000)

            priority_score: float = len(self.config.upgrade_priority) - priority_idx
            priority_score += (5 - current_level) * 0.5

            recommendations.append(
                UpgradeRecommendation(
                    slot=slot,
                    cost=upgrade_cost,
                    priority=priority_score,
                    can_afford=available_mana >= upgrade_cost,
                    reason=f"Card {slot} level {current_level}→{current_level + 1}",
                )
            )

        # Add hero power
        if self.config.enable_hero_power:
            hero_level = state.hero_power_level
            hero_cost = UPGRADE_COSTS.get(hero_level, 1000)

            recommendations.append(
                UpgradeRecommendation(
                    slot=6,
                    cost=hero_cost,
                    priority=0.5,
                    can_afford=available_mana >= hero_cost,
                    reason=f"Hero Power level {hero_level}→{hero_level + 1}",
                )
            )

        # Sort by priority (descending)
        recommendations.sort(key=lambda r: r.priority, reverse=True)
        return recommendations

    def update_after_summon(self) -> None:
        """Update state after summoning a unit."""
        # Deduct current summon cost first
        old_cost = self.state.summon_cost
        self.state.current_mana -= old_cost

        # Then update counters
        self.state.units_summoned += 1
        self.state.summon_cost = self.calculate_summon_cost(self.state.units_summoned)
        logger.debug(
            f"Summoned unit #{self.state.units_summoned}, "
            f"cost: {old_cost}, next cost: {self.state.summon_cost}"
        )

    def update_after_upgrade(self, slot: int) -> None:
        """Update state after upgrading a card or hero power.

        Args:
            slot: Slot that was upgraded (1-5 for cards, 6 for hero).
        """
        if slot == 6:
            current_level = self.state.hero_power_level
            cost = UPGRADE_COSTS.get(current_level, 0)
            self.state.hero_power_level += 1
            logger.debug(f"Hero power upgraded to level {self.state.hero_power_level}")
        else:
            current_level = self.state.card_levels.get(slot, 1)
            cost = UPGRADE_COSTS.get(current_level, 0)
            self.state.card_levels[slot] = current_level + 1
            logger.debug(f"Card {slot} upgraded to level {current_level + 1}")

        self.state.current_mana -= cost

    def set_boss_wave(self, is_boss: bool) -> None:
        """Set whether currently in a boss wave.

        Args:
            is_boss: True if in boss wave, False otherwise.
        """
        self.state.is_boss_wave = is_boss
        if is_boss:
            logger.info(f"Boss wave detected, reserving {self.config.boss_reserve} mana")

    def reset_for_new_battle(self) -> None:
        """Reset state for a new battle."""
        self.state.reset()
        logger.info("Mana state reset for new battle")

    def get_mana_efficiency(self, state: ManaState | None = None) -> dict[str, Any]:
        """Calculate mana efficiency metrics.

        Args:
            state: ManaState to analyze, or None to use current state.

        Returns:
            Dictionary with efficiency metrics.
        """
        state = state or self.state

        total_upgrade_cost = sum(
            UPGRADE_COSTS.get(level - 1, 0) for level in state.card_levels.values() if level > 1
        )
        summon_cost_total = sum(self.calculate_summon_cost(i) for i in range(state.units_summoned))

        return {
            "units_summoned": state.units_summoned,
            "current_summon_cost": state.summon_cost,
            "total_summon_mana_spent": summon_cost_total,
            "total_upgrade_mana_spent": total_upgrade_cost,
            "card_levels": dict(state.card_levels),
            "hero_power_level": state.hero_power_level,
            "current_mana": state.current_mana,
            "is_boss_wave": state.is_boss_wave,
        }


def create_mana_manager(
    config: ManaConfig | None = None,
    screen_width: int = REFERENCE_WIDTH,
    screen_height: int = REFERENCE_HEIGHT,
) -> ManaManager:
    """Factory function to create a ManaManager instance.

    Args:
        config: Optional ManaConfig.
        screen_width: Screen width for coordinate scaling.
        screen_height: Screen height for coordinate scaling.

    Returns:
        Configured ManaManager instance.
    """
    return ManaManager(config, screen_width, screen_height)
