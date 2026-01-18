"""
RushBot Core - Merge Logic
Handles unit merging validation and execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Callable


# Setup module logger
_logger = logging.getLogger("merge_logic")


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

    def __init__(
        self,
        config: MergeConfig | None = None,
        debugger: MergeDebugger | None = None,
    ) -> None:
        """Initialize the merge validator.

        Args:
            config: Optional merge configuration. Uses defaults if not provided.
            debugger: Optional debugger for logging validation failures.
        """
        self.config = config or MergeConfig()
        self._debugger = debugger

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
            result = (False, MergeResult.INVALID_TYPE)
            if self._debugger:
                self._debugger.log_validation_failure(
                    unit1_type, unit1_rank, unit2_type, unit2_rank, result[1]
                )
            return result

        # Check rank match
        if unit1_rank != unit2_rank:
            result = (False, MergeResult.INVALID_RANK)
            if self._debugger:
                self._debugger.log_validation_failure(
                    unit1_type, unit1_rank, unit2_type, unit2_rank, result[1]
                )
            return result

        # Check type match (special units can merge with anything)
        types_match = unit1_type == unit2_type
        one_is_special = (
            unit1_type in self.config.special_units or unit2_type in self.config.special_units
        )

        if not types_match and not one_is_special:
            result = (False, MergeResult.INVALID_TYPE)
            if self._debugger:
                self._debugger.log_validation_failure(
                    unit1_type, unit1_rank, unit2_type, unit2_rank, result[1]
                )
            return result

        _logger.debug(
            f"Merge validation passed: {unit1_type}(R{unit1_rank}) + "
            f"{unit2_type}(R{unit2_rank})"
        )
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
        debugger: MergeDebugger | None = None,
    ) -> None:
        """Initialize merge logic.

        Args:
            config: Optional merge configuration.
            swipe_callback: Function to execute the actual swipe (start, end).
            debugger: Optional debugger for logging merge attempts.
        """
        self.config = config or MergeConfig()
        self._debugger = debugger
        self.validator = MergeValidator(self.config, debugger)
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
        grid_df: pd.DataFrame | None = None,
    ) -> MergeResult:
        """Execute a merge operation.

        Args:
            candidate: The merge candidate to execute.
            grid_df: Optional grid DataFrame for extracting unit info.

        Returns:
            Result of the merge operation.
        """
        import time

        start_time = time.time()

        # Extract positions for logging
        if len(candidate.positions) >= 2:
            source_pos = tuple(candidate.positions[0])
            target_pos = tuple(candidate.positions[1])
        else:
            source_pos = (0, 0)
            target_pos = (0, 0)

        # Determine source/target unit info
        source_unit = candidate.unit_type
        target_unit = candidate.unit_type
        source_rank = candidate.rank
        target_rank = candidate.rank

        # If grid_df provided, get actual unit info
        if grid_df is not None and len(candidate.positions) >= 2:
            try:
                src_idx = candidate.positions[0][0] * 5 + candidate.positions[0][1]
                tgt_idx = candidate.positions[1][0] * 5 + candidate.positions[1][1]
                if src_idx < len(grid_df):
                    source_unit = grid_df.iloc[src_idx].get("unit", candidate.unit_type)
                    source_rank = int(grid_df.iloc[src_idx].get("rank", candidate.rank))
                if tgt_idx < len(grid_df):
                    target_unit = grid_df.iloc[tgt_idx].get("unit", candidate.unit_type)
                    target_rank = int(grid_df.iloc[tgt_idx].get("rank", candidate.rank))
            except (IndexError, KeyError, TypeError):
                pass  # Use candidate values

        if candidate.is_protected:
            result = MergeResult.PROTECTED_UNIT
            if self._debugger:
                duration = (time.time() - start_time) * 1000
                self._debugger.log_attempt(
                    source_unit=source_unit,
                    source_rank=source_rank,
                    source_pos=source_pos,  # type: ignore[arg-type]
                    target_unit=target_unit,
                    target_rank=target_rank,
                    target_pos=target_pos,  # type: ignore[arg-type]
                    result=result,
                    duration_ms=duration,
                    notes="Protected unit",
                )
            return result

        if len(candidate.positions) < 2:
            result = MergeResult.INSUFFICIENT_UNITS
            if self._debugger:
                duration = (time.time() - start_time) * 1000
                self._debugger.log_attempt(
                    source_unit=source_unit,
                    source_rank=source_rank,
                    source_pos=source_pos,  # type: ignore[arg-type]
                    target_unit=target_unit,
                    target_rank=target_rank,
                    target_pos=target_pos,  # type: ignore[arg-type]
                    result=result,
                    duration_ms=duration,
                    notes="Not enough positions",
                )
            return result

        if self.swipe_callback:
            start_pos = candidate.positions[0]
            end_pos = candidate.positions[1]
            _logger.info(
                f"Executing merge: {source_unit}(R{source_rank})@{source_pos} → "
                f"{target_unit}(R{target_rank})@{target_pos}"
            )
            self.swipe_callback(start_pos, end_pos)

        result = MergeResult.SUCCESS
        if self._debugger:
            duration = (time.time() - start_time) * 1000
            self._debugger.log_attempt(
                source_unit=source_unit,
                source_rank=source_rank,
                source_pos=source_pos,  # type: ignore[arg-type]
                target_unit=target_unit,
                target_rank=target_rank,
                target_pos=target_pos,  # type: ignore[arg-type]
                result=result,
                duration_ms=duration,
            )

        return result


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


# ============================================================================
# Merge Debug Logger (T016)
# ============================================================================


@dataclass
class MergeAttempt:
    """Record of a single merge attempt for debugging.

    Attributes:
        timestamp: When the merge was attempted.
        source_unit: Source unit type.
        source_rank: Source unit rank.
        source_pos: Source grid position (row, col).
        target_unit: Target unit type.
        target_rank: Target unit rank.
        target_pos: Target grid position (row, col).
        result: The merge result.
        duration_ms: Time taken for the operation.
        swipe_vector: Direction of the swipe (delta_row, delta_col).
        notes: Additional debug information.
    """

    timestamp: str
    source_unit: str
    source_rank: int
    source_pos: tuple[int, int]
    target_unit: str
    target_rank: int
    target_pos: tuple[int, int]
    result: MergeResult
    duration_ms: float = 0.0
    swipe_vector: tuple[int, int] = (0, 0)
    notes: str = ""

    def to_log_string(self) -> str:
        """Format for logging.

        Returns:
            Formatted log string.
        """
        status = "✓" if self.result == MergeResult.SUCCESS else "✗"
        return (
            f"[{self.timestamp}] Merge {status}: "
            f"{self.source_unit}(R{self.source_rank})@{self.source_pos} → "
            f"{self.target_unit}(R{self.target_rank})@{self.target_pos} | "
            f"Result: {self.result.value} | Swipe: {self.swipe_vector} | "
            f"Duration: {self.duration_ms:.0f}ms"
        )


class MergeDebugger:
    """Debug logger for merge operations.

    Tracks all merge attempts with detailed information for debugging.
    Can export history to file and generate visual overlays.

    Usage:
        debugger = MergeDebugger()
        debugger.log_attempt(source, target, result)

        # Export history
        debugger.export_history("merge_debug.log")

        # Get recent failures
        failures = debugger.get_failures(last_n=10)
    """

    DEFAULT_HISTORY_SIZE = 500
    DEFAULT_OUTPUT_DIR = Path("debug-output")

    def __init__(
        self,
        history_size: int = DEFAULT_HISTORY_SIZE,
        output_dir: Path | None = None,
        enable_visual: bool = False,
    ) -> None:
        """Initialize the merge debugger.

        Args:
            history_size: Maximum number of attempts to store.
            output_dir: Directory for debug output files.
            enable_visual: Whether to generate visual overlays.
        """
        self._history_size = history_size
        self._output_dir = output_dir or self.DEFAULT_OUTPUT_DIR
        self._enable_visual = enable_visual
        self._history: list[MergeAttempt] = []
        self._logger = logging.getLogger("merge_debugger")

    def log_attempt(
        self,
        source_unit: str,
        source_rank: int,
        source_pos: tuple[int, int],
        target_unit: str,
        target_rank: int,
        target_pos: tuple[int, int],
        result: MergeResult,
        duration_ms: float = 0.0,
        notes: str = "",
    ) -> MergeAttempt:
        """Log a merge attempt.

        Args:
            source_unit: Source unit type.
            source_rank: Source unit rank.
            source_pos: Source grid position (row, col).
            target_unit: Target unit type.
            target_rank: Target unit rank.
            target_pos: Target grid position (row, col).
            result: The merge result.
            duration_ms: Time taken for the operation.
            notes: Additional debug information.

        Returns:
            The logged MergeAttempt.
        """
        swipe = (target_pos[0] - source_pos[0], target_pos[1] - source_pos[1])

        attempt = MergeAttempt(
            timestamp=datetime.now().strftime("%H:%M:%S.%f")[:-3],
            source_unit=source_unit,
            source_rank=source_rank,
            source_pos=source_pos,
            target_unit=target_unit,
            target_rank=target_rank,
            target_pos=target_pos,
            result=result,
            duration_ms=duration_ms,
            swipe_vector=swipe,
            notes=notes,
        )

        self._history.append(attempt)
        if len(self._history) > self._history_size:
            self._history = self._history[-self._history_size :]

        # Log to standard logger
        log_str = attempt.to_log_string()
        if result == MergeResult.SUCCESS:
            self._logger.info(log_str)
        else:
            self._logger.warning(log_str)

        return attempt

    def log_validation_failure(
        self,
        unit1_type: str,
        unit1_rank: int,
        unit2_type: str,
        unit2_rank: int,
        reason: MergeResult,
    ) -> None:
        """Log a merge validation failure.

        Args:
            unit1_type: First unit type.
            unit1_rank: First unit rank.
            unit2_type: Second unit type.
            unit2_rank: Second unit rank.
            reason: Why the merge was rejected.
        """
        self._logger.debug(
            f"Merge validation failed: {unit1_type}(R{unit1_rank}) + "
            f"{unit2_type}(R{unit2_rank}) = {reason.value}"
        )

    @property
    def history(self) -> list[MergeAttempt]:
        """Get the merge history (read-only copy)."""
        return list(self._history)

    def get_failures(self, last_n: int = 10) -> list[MergeAttempt]:
        """Get recent failed merge attempts.

        Args:
            last_n: Number of recent failures to return.

        Returns:
            List of failed merge attempts.
        """
        failures = [a for a in self._history if a.result != MergeResult.SUCCESS]
        return failures[-last_n:]

    def get_success_rate(self) -> float:
        """Calculate the success rate of merge attempts.

        Returns:
            Success rate as percentage (0-100).
        """
        if not self._history:
            return 0.0
        successes = sum(1 for a in self._history if a.result == MergeResult.SUCCESS)
        return (successes / len(self._history)) * 100

    def get_failure_breakdown(self) -> dict[str, int]:
        """Get breakdown of failure reasons.

        Returns:
            Dictionary of {reason: count}.
        """
        breakdown: dict[str, int] = {}
        for attempt in self._history:
            if attempt.result != MergeResult.SUCCESS:
                reason = attempt.result.value
                breakdown[reason] = breakdown.get(reason, 0) + 1
        return breakdown

    def export_history(self, filepath: Path | str | None = None) -> str:
        """Export merge history to a log file.

        Args:
            filepath: Output file path. Auto-generated if None.

        Returns:
            Path to the exported file.
        """
        if filepath is None:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self._output_dir / f"merge_history_{timestamp}.log"

        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("MERGE DEBUG HISTORY\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total Attempts: {len(self._history)}\n")
            f.write(f"Success Rate: {self.get_success_rate():.1f}%\n")
            f.write("=" * 80 + "\n\n")

            # Failure breakdown
            breakdown = self.get_failure_breakdown()
            if breakdown:
                f.write("FAILURE BREAKDOWN:\n")
                for reason, count in breakdown.items():
                    f.write(f"  {reason}: {count}\n")
                f.write("\n")

            # All attempts
            f.write("MERGE ATTEMPTS:\n")
            f.write("-" * 80 + "\n")
            for attempt in self._history:
                f.write(attempt.to_log_string() + "\n")

        self._logger.info(f"Exported merge history to {output_path}")
        return str(output_path)

    def clear_history(self) -> None:
        """Clear the merge history."""
        self._history.clear()

    def format_summary(self) -> str:
        """Format a summary of merge statistics.

        Returns:
            Formatted summary string.
        """
        total = len(self._history)
        if total == 0:
            return "No merge attempts recorded."

        rate = self.get_success_rate()
        breakdown = self.get_failure_breakdown()

        lines = [
            f"Merge Summary: {total} attempts, {rate:.1f}% success",
            "Failure reasons:" if breakdown else "",
        ]
        for reason, count in breakdown.items():
            lines.append(f"  - {reason}: {count}")

        return "\n".join(lines)


# Global debugger instance (optional - can be used for easy access)
_merge_debugger: MergeDebugger | None = None


def get_merge_debugger() -> MergeDebugger:
    """Get or create the global merge debugger instance.

    Returns:
        The global MergeDebugger instance.
    """
    global _merge_debugger
    if _merge_debugger is None:
        _merge_debugger = MergeDebugger()
    return _merge_debugger
