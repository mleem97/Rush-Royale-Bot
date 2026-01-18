"""
RushBot Core - Merge Logic
Handles unit merging validation and execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Callable


class MergeResult(Enum):
    """Result of a merge operation."""

    SUCCESS = "success"
    INVALID_TYPE = "invalid_type"
    INVALID_RANK = "invalid_rank"
    PROTECTED_UNIT = "protected_unit"
    INSUFFICIENT_UNITS = "insufficient_units"
    NO_CANDIDATES = "no_candidates"


@dataclass
class MergeCandidate:
    """Represents a potential merge between two units.

    Attributes:
        unit_type: The unit type (e.g., "demon_hunter.png").
        rank: The rank of the units.
        positions: Grid positions [row, col] of the two units.
        is_protected: Whether one of the units is protected (DPS unit).
    """

    unit_type: str
    rank: int
    positions: list[list[int]]
    is_protected: bool = False

    def __post_init__(self) -> None:
        """Validate merge candidate data."""
        if len(self.positions) != 2:
            raise ValueError("MergeCandidate requires exactly 2 positions")


@dataclass
class MergeConfig:
    """Configuration for merge behavior.

    Attributes:
        protected_units: List of unit types to protect from merging.
        max_protected_rank: Maximum rank at which protection applies.
        min_units_to_keep: Minimum number of protected units to keep.
        special_units: Units with special merge behavior (harlequin, dryad, etc.).
    """

    protected_units: list[str] = field(default_factory=list)
    max_protected_rank: int = 7
    min_units_to_keep: int = 1
    special_units: list[str] = field(
        default_factory=lambda: [
            "harlequin.png",
            "dryad.png",
            "mime.png",
            "scrapper.png",
        ]
    )


class MergeValidator:
    """Validates merge operations between units."""

    def __init__(self, config: MergeConfig | None = None) -> None:
        """Initialize the merge validator.

        Args:
            config: Optional merge configuration. Uses defaults if not provided.
        """
        self.config = config or MergeConfig()

    def can_merge(
        self,
        unit1_type: str,
        unit1_rank: int,
        unit2_type: str,
        unit2_rank: int,
    ) -> tuple[bool, MergeResult]:
        """Check if two units can be merged.

        In Rush Royale, units can only be merged if:
        1. They have the same type (or one is a special unit like harlequin)
        2. They have the same rank

        Args:
            unit1_type: Type of first unit.
            unit1_rank: Rank of first unit.
            unit2_type: Type of second unit.
            unit2_rank: Rank of second unit.

        Returns:
            Tuple of (can_merge, reason).
        """
        # Check for empty cells
        if unit1_type == "empty.png" or unit2_type == "empty.png":
            return False, MergeResult.INVALID_TYPE

        # Check rank match
        if unit1_rank != unit2_rank:
            return False, MergeResult.INVALID_RANK

        # Check type match (special units can merge with anything)
        types_match = unit1_type == unit2_type
        one_is_special = (
            unit1_type in self.config.special_units or unit2_type in self.config.special_units
        )

        if not types_match and not one_is_special:
            return False, MergeResult.INVALID_TYPE

        return True, MergeResult.SUCCESS

    def is_protected(
        self,
        unit_type: str,
        unit_rank: int,
        unit_count: int,
    ) -> bool:
        """Check if a unit should be protected from merging.

        Args:
            unit_type: Type of the unit.
            unit_rank: Rank of the unit.
            unit_count: Total count of this unit type on the board.

        Returns:
            True if unit should be protected.
        """
        if unit_type not in self.config.protected_units:
            return False

        if unit_rank > self.config.max_protected_rank:
            return False

        # Protect if we would go below minimum
        if unit_count <= self.config.min_units_to_keep:
            return True

        return False


class MergeLogic:
    """Handles merge candidate selection and execution."""

    def __init__(
        self,
        config: MergeConfig | None = None,
        swipe_callback: Callable[[list[int], list[int]], None] | None = None,
    ) -> None:
        """Initialize merge logic.

        Args:
            config: Optional merge configuration.
            swipe_callback: Function to execute the actual swipe (start, end).
        """
        self.config = config or MergeConfig()
        self.validator = MergeValidator(self.config)
        self.swipe_callback = swipe_callback

    def find_merge_candidates(
        self,
        grid_df: pd.DataFrame,
    ) -> list[MergeCandidate]:
        """Find all valid merge candidates on the grid.

        Args:
            grid_df: DataFrame with columns 'unit', 'rank', 'grid_pos'.

        Returns:
            List of valid merge candidates.
        """
        candidates: list[MergeCandidate] = []

        if grid_df is None or grid_df.empty:
            return candidates

        # Filter out empty cells
        valid_units = grid_df[grid_df["unit"] != "empty.png"].copy()

        if valid_units.empty:
            return candidates

        # Group by unit type and rank
        grouped = valid_units.groupby(["unit", "rank"])

        for (unit_type, rank), group in grouped:
            if len(group) < 2:
                continue

            # Check if unit is protected
            is_protected = self.validator.is_protected(str(unit_type), int(rank), len(group))

            # Get positions
            positions = group["grid_pos"].tolist()

            # Create candidate with first two positions
            candidate = MergeCandidate(
                unit_type=str(unit_type),
                rank=int(rank),
                positions=positions[:2],
                is_protected=is_protected,
            )
            candidates.append(candidate)

        return candidates

    def find_special_merge_candidates(
        self,
        grid_df: pd.DataFrame,
        target_unit: str,
    ) -> list[MergeCandidate]:
        """Find special merge candidates (harlequin, dryad with target).

        Special merges allow merging different unit types:
        - Harlequin can become any unit
        - Dryad can upgrade a unit

        Args:
            grid_df: DataFrame with columns 'unit', 'rank', 'grid_pos'.
            target_unit: The DPS unit to prioritize for special merges.

        Returns:
            List of special merge candidates.
        """
        candidates: list[MergeCandidate] = []

        if grid_df is None or grid_df.empty:
            return candidates

        valid_units = grid_df[grid_df["unit"] != "empty.png"].copy()

        if valid_units.empty:
            return candidates

        # Group by rank first
        by_rank = valid_units.groupby("rank")

        for rank, rank_group in by_rank:
            # Find special units at this rank
            specials = rank_group[rank_group["unit"].isin(self.config.special_units)]

            if specials.empty:
                continue

            # Find target units at this rank
            targets = rank_group[rank_group["unit"] == target_unit]

            # Also find other non-special units
            others = rank_group[~rank_group["unit"].isin(self.config.special_units)]

            # Prefer pairing special with target, then with others
            for _, special_row in specials.iterrows():
                special_pos = special_row["grid_pos"]
                special_type = special_row["unit"]

                # Try target first
                if not targets.empty:
                    for _, target_row in targets.iterrows():
                        target_pos = target_row["grid_pos"]
                        candidate = MergeCandidate(
                            unit_type=f"{special_type}+{target_unit}",
                            rank=int(str(rank)),
                            positions=[special_pos, target_pos],
                            is_protected=False,
                        )
                        candidates.append(candidate)

                # Then try others
                elif not others.empty:
                    for _, other_row in others.iterrows():
                        other_pos = other_row["grid_pos"]
                        other_type = other_row["unit"]
                        candidate = MergeCandidate(
                            unit_type=f"{special_type}+{other_type}",
                            rank=int(str(rank)),
                            positions=[special_pos, other_pos],
                            is_protected=False,
                        )
                        candidates.append(candidate)
                        break  # Only one per special unit

        return candidates

    def select_best_candidate(
        self,
        candidates: list[MergeCandidate],
        prioritize_low_rank: bool = True,
    ) -> MergeCandidate | None:
        """Select the best merge candidate from a list.

        Args:
            candidates: List of merge candidates.
            prioritize_low_rank: If True, prefer lower rank merges.

        Returns:
            Best candidate, or None if no valid candidates.
        """
        if not candidates:
            return None

        # Filter out protected units
        available = [c for c in candidates if not c.is_protected]

        if not available:
            return None

        # Sort by rank (ascending if prioritize_low_rank)
        available.sort(key=lambda c: c.rank, reverse=not prioritize_low_rank)

        return available[0]

    def execute_merge(
        self,
        candidate: MergeCandidate,
    ) -> MergeResult:
        """Execute a merge operation.

        Args:
            candidate: The merge candidate to execute.

        Returns:
            Result of the merge operation.
        """
        if candidate.is_protected:
            return MergeResult.PROTECTED_UNIT

        if len(candidate.positions) < 2:
            return MergeResult.INSUFFICIENT_UNITS

        if self.swipe_callback:
            start_pos = candidate.positions[0]
            end_pos = candidate.positions[1]
            self.swipe_callback(start_pos, end_pos)

        return MergeResult.SUCCESS


def calculate_merge_direction(
    start: list[int],
    end: list[int],
) -> tuple[int, int]:
    """Calculate the direction vector for a merge swipe.

    Args:
        start: Starting grid position [row, col].
        end: Ending grid position [row, col].

    Returns:
        Direction as (delta_row, delta_col).
    """
    start_arr = np.array(start)
    end_arr = np.array(end)
    direction = end_arr - start_arr
    return int(direction[0]), int(direction[1])


def validate_same_type_merge(
    unit1: str,
    rank1: int,
    unit2: str,
    rank2: int,
) -> bool:
    """Validate that two units can be merged (same type and rank).

    Args:
        unit1: First unit type.
        rank1: First unit rank.
        unit2: Second unit type.
        rank2: Second unit rank.

    Returns:
        True if units can be merged.
    """
    validator = MergeValidator()
    can_merge, _ = validator.can_merge(unit1, rank1, unit2, rank2)
    return can_merge


def get_protected_units_from_config(
    config_parser,  # ConfigParser | None
) -> list[str]:
    """Extract protected unit list from config.

    Args:
        config_parser: ConfigParser with [bot] section.

    Returns:
        List of unit filenames to protect.
    """
    protected: list[str] = []

    if config_parser is None:
        return protected

    if not config_parser.has_section("bot"):
        return protected

    # DPS unit is always protected
    dps_unit = config_parser.get("bot", "dps_unit", fallback="")
    if dps_unit:
        # Normalize to filename format
        if not dps_unit.endswith(".png"):
            dps_unit = f"{dps_unit}.png"
        protected.append(dps_unit)

    return protected
