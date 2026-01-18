"""CV-Only Debug Mode for Rush Royale Bot.

This module provides a debug/visualization mode that shows what the bot
"sees" without taking any actions. It overlays detection results on
screenshots and logs all CV operations.

Features:
- Screen state detection with confidence overlay
- Unit detection with bounding boxes and labels
- Rank detection visualization
- Merge candidate highlighting
- Menu/page context logging
- Export to JSON for analysis
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from enum import auto
from pathlib import Path
from typing import Any

import cv2
from numpy.typing import NDArray

from .icon_detection import ContextAwareIconDetector
from .screen_state import ScreenState
from .screen_state import ScreenStateConfig
from .screen_state import ScreenStateDetector
from .vision import BotPerception
from .vision import GridExtractor

# Type alias for image arrays
ImageArray = NDArray[Any]

# Directory for debug output
REPO_ROOT = Path(__file__).resolve().parents[3]
DEBUG_OUTPUT_DIR = REPO_ROOT / "cv-debug-output"


class CVDebugLevel(Enum):
    """Verbosity level for CV debug output."""

    MINIMAL = auto()
    """Only log critical detections (page changes, errors)."""

    NORMAL = auto()
    """Log all detections with confidence."""

    VERBOSE = auto()
    """Log everything including failed matches and timing."""


@dataclass
class DetectionResult:
    """Result of a single detection operation.

    Attributes:
        entity_type: Type of detected entity (unit, rank, icon, page).
        name: Name/identifier of the detected entity.
        confidence: Detection confidence score (0.0-1.0).
        method: Detection method used (template, histogram, model).
        position: (x, y) position if applicable.
        bounding_box: (x, y, w, h) if applicable.
        metadata: Additional detection-specific data.
    """

    entity_type: str
    name: str
    confidence: float
    method: str = ""
    position: tuple[int, int] | None = None
    bounding_box: tuple[int, int, int, int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_log_string(self) -> str:
        """Format detection for logging.

        Returns:
            Formatted log string.
        """
        pos_str = f" @ ({self.position[0]}, {self.position[1]})" if self.position else ""
        return f"Found {self.entity_type.upper()} '{self.name}': Detected_Via: [{self.method}, {self.confidence:.2f}]{pos_str}"


@dataclass
class PageContext:
    """Current page/screen context information.

    Attributes:
        state: Detected screen state.
        confidence: Detection confidence.
        detected_via: Template or method that detected the state.
        menu_context: Bottom menu bar context if detected.
    """

    state: ScreenState
    confidence: float
    detected_via: str = ""
    menu_context: str = ""

    def to_log_string(self) -> str:
        """Format page context for logging.

        Returns:
            Formatted log string.
        """
        menu_str = f" (Menu: {self.menu_context})" if self.menu_context else ""
        return f"Viewing {self.state.name}: Detected_via: [{self.detected_via}, {self.confidence:.2f}]{menu_str}"


@dataclass
class MergeCandidate:
    """A potential merge between two units.

    Attributes:
        source_unit: Name of the source unit.
        target_unit: Name of the target unit.
        source_pos: Grid position of source (row, col).
        target_pos: Grid position of target (row, col).
        rank: Rank level of both units.
        is_allowed: Whether this merge is allowed by rules.
        rule_note: Explanation if merge is blocked.
    """

    source_unit: str
    target_unit: str
    source_pos: tuple[int, int]
    target_pos: tuple[int, int]
    rank: int | float
    is_allowed: bool = True
    rule_note: str = ""

    def to_log_string(self) -> str:
        """Format merge candidate for logging.

        Returns:
            Formatted log string.
        """
        status = "✓" if self.is_allowed else "✗"
        note = f" ({self.rule_note})" if self.rule_note else ""
        return (
            f"Merge {status}: {self.source_unit}[{self.source_pos}] → "
            f"{self.target_unit}[{self.target_pos}] (Rank {self.rank}){note}"
        )


@dataclass
class CVDebugFrame:
    """Complete debug information for a single frame.

    Attributes:
        timestamp: Capture timestamp.
        page_context: Current page/screen context.
        detections: All detection results.
        merge_candidates: Detected merge possibilities.
        grid_state: Current grid state if in battle.
        raw_image_path: Path to saved raw screenshot.
        overlay_image_path: Path to saved overlay image.
    """

    timestamp: str
    page_context: PageContext | None = None
    detections: list[DetectionResult] = field(default_factory=list)
    merge_candidates: list[MergeCandidate] = field(default_factory=list)
    grid_state: list[list[str]] = field(default_factory=list)
    raw_image_path: str = ""
    overlay_image_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON export.

        Returns:
            Dictionary representation.
        """
        result: dict[str, Any] = {
            "timestamp": self.timestamp,
            "page_context": None,
            "detections": [],
            "merge_candidates": [],
            "grid_state": self.grid_state,
            "raw_image_path": self.raw_image_path,
            "overlay_image_path": self.overlay_image_path,
        }
        if self.page_context:
            result["page_context"] = {
                "state": self.page_context.state.name,
                "confidence": self.page_context.confidence,
                "detected_via": self.page_context.detected_via,
                "menu_context": self.page_context.menu_context,
            }
        result["detections"] = [asdict(d) for d in self.detections]
        result["merge_candidates"] = [asdict(m) for m in self.merge_candidates]
        return result


class CVDebugMode:
    """CV-Only Debug Mode for visualizing bot perception.

    This class runs CV detection without taking any game actions,
    providing detailed visualization and logging of what the bot sees.

    Attributes:
        level: Debug verbosity level.
        save_images: Whether to save debug images to disk.
        output_dir: Directory for debug output.
    """

    # Colors for overlay (BGR format)
    COLOR_UNIT = (0, 255, 0)  # Green for units
    COLOR_RANK = (255, 165, 0)  # Orange for ranks
    COLOR_MERGE_OK = (0, 255, 255)  # Yellow for allowed merges
    COLOR_MERGE_BLOCKED = (0, 0, 255)  # Red for blocked merges
    COLOR_PAGE = (255, 0, 255)  # Magenta for page context
    COLOR_ICON = (255, 255, 0)  # Cyan for icons

    def __init__(
        self,
        level: CVDebugLevel = CVDebugLevel.NORMAL,
        save_images: bool = True,
        output_dir: Path | None = None,
    ) -> None:
        """Initialize CV Debug Mode.

        Args:
            level: Debug verbosity level.
            save_images: Whether to save debug images to disk.
            output_dir: Directory for debug output (default: cv-debug-output/).
        """
        self.level = level
        self.save_images = save_images
        self.output_dir = output_dir or DEBUG_OUTPUT_DIR
        self.logger = logging.getLogger("cv_debug")

        # Initialize perception components
        self._screen_detector = ScreenStateDetector(ScreenStateConfig())
        self._icon_detector = ContextAwareIconDetector()
        self._grid_extractor = GridExtractor()
        self._perception = BotPerception()

        # Session tracking
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._frame_count = 0
        self._frames: list[CVDebugFrame] = []

        # Ensure output directory exists
        if self.save_images:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def _extract_grid_cells(
        self, image: ImageArray
    ) -> list[ImageArray]:
        """Extract cell images from the grid.

        Args:
            image: Screenshot image.

        Returns:
            List of 15 cell images (3 rows x 5 cols, row-major order).
        """
        cells: list[ImageArray] = []
        for row in range(3):
            for col in range(5):
                x, y, w, h = self._grid_extractor.get_cell_bounds(row, col)
                cell_img = image[y : y + h, x : x + w]
                cells.append(cell_img)
        return cells

    def analyze_frame(self, image: ImageArray) -> CVDebugFrame:
        """Analyze a single frame and return debug information.

        Args:
            image: Screenshot image (BGR format).

        Returns:
            CVDebugFrame with all detection results.
        """
        self._frame_count += 1
        timestamp = datetime.now().isoformat()

        frame = CVDebugFrame(timestamp=timestamp)

        # 1. Detect page/screen context
        page_result = self._detect_page_context(image)
        frame.page_context = page_result
        if page_result:
            self.logger.info(page_result.to_log_string())

        # 2. Detect icons based on current context
        icon_detections = self._detect_icons(image, page_result)
        frame.detections.extend(icon_detections)
        for det in icon_detections:
            if self.level != CVDebugLevel.MINIMAL:
                self.logger.info(det.to_log_string())

        # 3. If in battle, detect units and ranks
        if page_result and page_result.state == ScreenState.BATTLE:
            unit_detections = self._detect_units_and_ranks(image)
            frame.detections.extend(unit_detections)
            for det in unit_detections:
                if self.level != CVDebugLevel.MINIMAL:
                    self.logger.info(det.to_log_string())

            # 4. Find merge candidates
            merge_candidates = self._find_merge_candidates(image)
            frame.merge_candidates = merge_candidates
            for mc in merge_candidates:
                self.logger.info(f"Merging: {mc.to_log_string()}")

            # 5. Extract grid state
            frame.grid_state = self._extract_grid_state(image)

        # 6. Save images if enabled
        if self.save_images:
            frame.raw_image_path = self._save_raw_image(image)
            frame.overlay_image_path = self._save_overlay_image(image, frame)

        self._frames.append(frame)
        return frame

    def _detect_page_context(self, image: ImageArray) -> PageContext | None:
        """Detect current page/screen context.

        Args:
            image: Screenshot image.

        Returns:
            PageContext or None if unknown.
        """
        result = self._screen_detector.detect(image)
        if not result or result.state == ScreenState.UNKNOWN:
            return None

        # Try to detect menu context if on a menu screen
        menu_context = ""
        menu_states = [
            ScreenState.STORE_MENU,
            ScreenState.CARDS_MENU,
            ScreenState.MAIN_MENU,
            ScreenState.CLAN_MENU,
            ScreenState.EVENT_MENU,
        ]
        if result.state in menu_states:
            menu_context = result.state.name.replace("_MENU", "")

        return PageContext(
            state=result.state,
            confidence=result.confidence,
            detected_via=result.matched_template,
            menu_context=menu_context,
        )

    def _detect_icons(
        self, image: ImageArray, page_context: PageContext | None
    ) -> list[DetectionResult]:
        """Detect icons based on current context.

        Args:
            image: Screenshot image.
            page_context: Current page context for filtering.

        Returns:
            List of icon detection results.
        """
        detections: list[DetectionResult] = []

        # Use context-aware detection if available
        force_state = page_context.state if page_context else None
        icons = self._icon_detector.detect_icons(image, force_state=force_state)

        for icon_info in icons:
            icon_name = icon_info.get("icon", "unknown")
            confidence = icon_info.get("confidence", 0.0)
            position = icon_info.get("position")

            det = DetectionResult(
                entity_type="icon",
                name=icon_name,
                confidence=confidence,
                method="template",
                position=position,
            )
            detections.append(det)

        return detections

    def _detect_units_and_ranks(self, image: ImageArray) -> list[DetectionResult]:
        """Detect units and their ranks on the battle grid.

        Args:
            image: Screenshot image.

        Returns:
            List of unit and rank detection results.
        """
        detections: list[DetectionResult] = []

        # Get grid cells
        cells = self._extract_grid_cells(image)

        for idx, cell in enumerate(cells):
            row, col = divmod(idx, 5)  # 3 rows, 5 cols

            # Detect unit in cell
            unit_name, unit_conf = self._perception.match_unit_array(cell)
            if unit_name and unit_conf > 0.5:
                center = self._grid_extractor.get_cell_center(row, col)
                det = DetectionResult(
                    entity_type="unit",
                    name=unit_name,
                    confidence=unit_conf,
                    method="histogram",
                    position=center,
                    metadata={"grid_pos": (row, col)},
                )
                detections.append(det)

            # Detect rank in cell
            rank_result = self._perception.match_rank_array(cell)
            rank, _rank_conf = rank_result
            if rank is not None and rank > 0:
                center = self._grid_extractor.get_cell_center(row, col)
                det = DetectionResult(
                    entity_type="rank",
                    name=str(rank),
                    confidence=0.8,  # Rank model doesn't return confidence
                    method="model",
                    position=center,
                    metadata={"grid_pos": (row, col)},
                )
                detections.append(det)

        return detections

    def _find_merge_candidates(self, image: ImageArray) -> list[MergeCandidate]:
        """Find potential merge candidates on the grid.

        Args:
            image: Screenshot image.

        Returns:
            List of merge candidates.
        """
        candidates: list[MergeCandidate] = []

        # Build grid state first
        cells = self._extract_grid_cells(image)
        grid: list[list[tuple[str, int | float]]] = []

        for row in range(3):
            grid_row: list[tuple[str, int | float]] = []
            for col in range(5):
                idx = row * 5 + col
                if idx < len(cells):
                    cell = cells[idx]
                    unit_name, _ = self._perception.match_unit_array(cell)
                    rank_result = self._perception.match_rank_array(cell)
                    rank = rank_result[0] if rank_result else 0
                    grid_row.append((unit_name or "", rank))
                else:
                    grid_row.append(("", 0))
            grid.append(grid_row)

        # Special units that can merge with any type
        special_units = {"harlequin", "dryad", "mime", "scrapper"}

        # Find adjacent pairs
        for row in range(3):
            for col in range(5):
                unit1, rank1 = grid[row][col]
                if not unit1:
                    continue

                # Check right neighbor
                if col < 4:
                    unit2, rank2 = grid[row][col + 1]
                    if unit2 and rank1 == rank2:
                        is_allowed, note = self._check_merge_rules(
                            unit1, unit2, rank1, special_units
                        )
                        candidates.append(
                            MergeCandidate(
                                source_unit=unit1,
                                target_unit=unit2,
                                source_pos=(row, col),
                                target_pos=(row, col + 1),
                                rank=rank1,
                                is_allowed=is_allowed,
                                rule_note=note,
                            )
                        )

                # Check bottom neighbor
                if row < 2:
                    unit2, rank2 = grid[row + 1][col]
                    if unit2 and rank1 == rank2:
                        is_allowed, note = self._check_merge_rules(
                            unit1, unit2, rank1, special_units
                        )
                        candidates.append(
                            MergeCandidate(
                                source_unit=unit1,
                                target_unit=unit2,
                                source_pos=(row, col),
                                target_pos=(row + 1, col),
                                rank=rank1,
                                is_allowed=is_allowed,
                                rule_note=note,
                            )
                        )

        return candidates

    def _check_merge_rules(
        self, unit1: str, unit2: str, rank: int | float, special_units: set[str]
    ) -> tuple[bool, str]:
        """Check if a merge is allowed by game rules.

        Args:
            unit1: First unit name.
            unit2: Second unit name.
            rank: Rank of both units.
            special_units: Set of units that can merge with any type.

        Returns:
            Tuple of (is_allowed, explanation).
        """
        # Normalize names
        u1 = unit1.lower().replace(".png", "")
        u2 = unit2.lower().replace(".png", "")

        # Same type always allowed
        if u1 == u2:
            return True, "same_type"

        # Special units can merge with any
        if u1 in special_units or u2 in special_units:
            return True, f"special_unit:{u1 if u1 in special_units else u2}"

        # Different types not allowed
        return False, "different_types"

    def _extract_grid_state(self, image: ImageArray) -> list[list[str]]:
        """Extract current grid state as string matrix.

        Args:
            image: Screenshot image.

        Returns:
            3x5 grid of unit identifiers.
        """
        cells = self._extract_grid_cells(image)
        grid: list[list[str]] = []

        for row in range(3):
            grid_row: list[str] = []
            for col in range(5):
                idx = row * 5 + col
                if idx < len(cells):
                    cell = cells[idx]
                    unit_name, _ = self._perception.match_unit_array(cell)
                    rank_result = self._perception.match_rank_array(cell)
                    rank = rank_result[0] if rank_result else 0
                    if unit_name:
                        # Format: unit_name:rank
                        name = unit_name.replace(".png", "")
                        grid_row.append(f"{name}:{rank}")
                    else:
                        grid_row.append("empty")
                else:
                    grid_row.append("empty")
            grid.append(grid_row)

        return grid

    def _save_raw_image(self, image: ImageArray) -> str:
        """Save raw screenshot to disk.

        Args:
            image: Screenshot image.

        Returns:
            Path to saved image.
        """
        filename = f"{self._session_id}_frame{self._frame_count:04d}_raw.png"
        path = self.output_dir / filename
        cv2.imwrite(str(path), image)
        return str(path)

    def _save_overlay_image(self, image: ImageArray, frame: CVDebugFrame) -> str:
        """Save screenshot with debug overlay.

        Args:
            image: Screenshot image.
            frame: Debug frame with detection data.

        Returns:
            Path to saved overlay image.
        """
        # Create a copy for drawing
        overlay = image.copy()
        _height, _width = overlay.shape[:2]

        # Draw page context
        if frame.page_context:
            text = frame.page_context.to_log_string()
            cv2.putText(overlay, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_PAGE, 2)

        # Draw detections
        for det in frame.detections:
            color = self.COLOR_UNIT if det.entity_type == "unit" else self.COLOR_ICON
            if det.entity_type == "rank":
                color = self.COLOR_RANK

            if det.position:
                x, y = det.position
                # Draw circle at position
                cv2.circle(overlay, (x, y), 10, color, 2)
                # Draw label
                label = f"{det.name}:{det.confidence:.2f}"
                cv2.putText(
                    overlay,
                    label,
                    (x + 15, y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1,
                )

            if det.bounding_box:
                bx, by, bw, bh = det.bounding_box
                cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), color, 2)

        # Draw merge candidates
        for mc in frame.merge_candidates:
            color = self.COLOR_MERGE_OK if mc.is_allowed else self.COLOR_MERGE_BLOCKED
            # Get pixel positions from grid positions
            src_center = self._grid_extractor.get_cell_center(
                mc.source_pos[0], mc.source_pos[1]
            )
            tgt_center = self._grid_extractor.get_cell_center(
                mc.target_pos[0], mc.target_pos[1]
            )
            # Draw line between merge candidates
            cv2.line(overlay, src_center, tgt_center, color, 3)
            # Draw arrow
            cv2.arrowedLine(overlay, src_center, tgt_center, color, 2, tipLength=0.2)

        # Save overlay image
        filename = f"{self._session_id}_frame{self._frame_count:04d}_overlay.png"
        path = self.output_dir / filename
        cv2.imwrite(str(path), overlay)
        return str(path)

    def export_session(self, output_path: Path | None = None) -> str:
        """Export all frames from current session to JSON.

        Args:
            output_path: Output file path (default: session_id.json in output_dir).

        Returns:
            Path to exported JSON file.
        """
        if output_path is None:
            output_path = self.output_dir / f"{self._session_id}_session.json"

        data = {
            "session_id": self._session_id,
            "frame_count": self._frame_count,
            "level": self.level.name,
            "frames": [f.to_dict() for f in self._frames],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        self.logger.info(f"Exported {self._frame_count} frames to {output_path}")
        return str(output_path)

    def clear_session(self) -> None:
        """Clear current session data."""
        self._frames.clear()
        self._frame_count = 0
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")


def run_cv_debug_on_screenshot(
    image_path: str | Path,
    level: CVDebugLevel = CVDebugLevel.NORMAL,
    save_output: bool = True,
) -> CVDebugFrame:
    """Run CV debug analysis on a single screenshot.

    Convenience function for quick analysis of a screenshot file.

    Args:
        image_path: Path to screenshot image.
        level: Debug verbosity level.
        save_output: Whether to save debug images.

    Returns:
        CVDebugFrame with analysis results.
    """
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    debug = CVDebugMode(level=level, save_images=save_output)
    return debug.analyze_frame(image)
