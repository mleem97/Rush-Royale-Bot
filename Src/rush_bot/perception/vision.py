"""Rush Royale Bot Perception - Computer Vision and ML.

Handles unit recognition, rank detection, and grid analysis
using OpenCV for image processing and scikit-learn for ML.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression

if TYPE_CHECKING:
    pass


# Directory layout
REPO_ROOT = Path(__file__).resolve().parents[3]  # Up to project root
CV_IMAGES_DIR = REPO_ROOT / "cv-images"
UNITS_DIR = CV_IMAGES_DIR / "all_units"  # Unit template images

# Training directories
ML_DIR = REPO_ROOT / "machine_learning"
ML_INPUTS_DIR = ML_DIR / "inputs"
ML_RAW_INPUT_DIR = ML_DIR / "raw_input"
OCR_INPUTS_DIR = REPO_ROOT / "OCR_inputs"

# Model path
RANK_MODEL_PATH = REPO_ROOT / "rank_model.pkl"

# Template matching thresholds
TEMPLATE_MATCH_THRESHOLD = 0.7  # Minimum correlation for a match
COLOR_MSE_THRESHOLD = 3000  # Maximum color MSE for a match


# =============================================================================
# Grid Extraction - Resolution-Independent Coordinate Calculation
# =============================================================================

# Reference resolution for Rush Royale grid coordinates (portrait mode)
REFERENCE_WIDTH = 1080
REFERENCE_HEIGHT = 1920

# Grid layout constants (relative to 1080x1920 reference)
# The game grid is 3 rows x 5 columns = 15 cells
GRID_ROWS = 3
GRID_COLS = 5

# Grid position on screen (relative to reference resolution)
# These values define the top-left corner of the first cell
GRID_TOP_X_REF = 153  # Left margin to first cell
GRID_TOP_Y_REF = 945  # Top margin to first row

# Cell dimensions (in reference resolution)
CELL_WIDTH_REF = 120
CELL_HEIGHT_REF = 120

# Gap between cells (typically 0 in Rush Royale)
CELL_GAP_REF = 0


@dataclass
class GridConfig:
    """Configuration for game grid extraction.

    This dataclass holds the calibrated coordinates for extracting
    the 3x5 game grid from screenshots at various resolutions.

    Attributes:
        top_x: X coordinate of top-left corner of grid (first cell).
        top_y: Y coordinate of top-left corner of grid (first row).
        cell_width: Width of each cell in pixels.
        cell_height: Height of each cell in pixels.
        cell_gap: Gap between cells in pixels.
        rows: Number of rows (default 3).
        cols: Number of columns (default 5).
    """

    top_x: int
    top_y: int
    cell_width: int
    cell_height: int
    cell_gap: int = 0
    rows: int = GRID_ROWS
    cols: int = GRID_COLS

    @property
    def total_cells(self) -> int:
        """Total number of cells in the grid."""
        return self.rows * self.cols


class GridExtractor:
    """Extract game grid cells from screenshots at any resolution.

    The Rush Royale game grid is a 3x5 arrangement of unit cells.
    This class handles coordinate calculation for different screen
    resolutions by scaling from a reference resolution (1080x1920).

    Usage:
        extractor = GridExtractor(screen_width=1080, screen_height=1920)
        boxes, cell_size = extractor.get_grid()

        # boxes is a (3, 5, 2) array with [x, y] coordinates for each cell
        # cell_size is a tuple (width, height)
    """

    def __init__(
        self,
        screen_width: int = REFERENCE_WIDTH,
        screen_height: int = REFERENCE_HEIGHT,
        config: GridConfig | None = None,
    ) -> None:
        """Initialize the grid extractor.

        Args:
            screen_width: Width of the screenshot in pixels.
            screen_height: Height of the screenshot in pixels.
            config: Optional custom GridConfig. If None, uses default
                    calibration scaled to the screen resolution.
        """
        self.screen_width = screen_width
        self.screen_height = screen_height

        if config is not None:
            self.config = config
        else:
            self.config = self._calculate_scaled_config()

    def _calculate_scaled_config(self) -> GridConfig:
        """Calculate grid configuration scaled to current resolution.

        Scales the reference coordinates proportionally based on the
        screen dimensions.

        Returns:
            GridConfig with scaled coordinates.
        """
        # Calculate scale factors
        scale_x = self.screen_width / REFERENCE_WIDTH
        scale_y = self.screen_height / REFERENCE_HEIGHT

        # Scale all coordinates
        top_x = int(GRID_TOP_X_REF * scale_x)
        top_y = int(GRID_TOP_Y_REF * scale_y)
        cell_width = int(CELL_WIDTH_REF * scale_x)
        cell_height = int(CELL_HEIGHT_REF * scale_y)
        cell_gap = int(CELL_GAP_REF * min(scale_x, scale_y))

        return GridConfig(
            top_x=top_x,
            top_y=top_y,
            cell_width=cell_width,
            cell_height=cell_height,
            cell_gap=cell_gap,
            rows=GRID_ROWS,
            cols=GRID_COLS,
        )

    def get_grid(self) -> tuple[NDArray[np.int32], tuple[int, int]]:
        """Get grid cell coordinates.

        Returns:
            Tuple of:
            - boxes: NDArray of shape (rows, cols, 2) containing [x, y]
                     coordinates for the top-left corner of each cell.
            - cell_size: Tuple (width, height) of each cell.
        """
        cfg = self.config

        # Generate x coordinates for each column
        x_coords = [cfg.top_x + col * (cfg.cell_width + cfg.cell_gap) for col in range(cfg.cols)]

        # Generate y coordinates for each row
        y_coords = [cfg.top_y + row * (cfg.cell_height + cfg.cell_gap) for row in range(cfg.rows)]

        # Build the grid array (row-major order)
        boxes = []
        for y in y_coords:
            for x in x_coords:
                boxes.append((x, y))

        # Reshape to (rows, cols, 2)
        boxes_array = np.array(boxes, dtype=np.int32).reshape(cfg.rows, cfg.cols, 2)

        return boxes_array, (cfg.cell_width, cfg.cell_height)

    def get_grid_flat(self) -> tuple[NDArray[np.int32], tuple[int, int]]:
        """Get grid cell coordinates as flat list.

        Returns:
            Tuple of:
            - boxes: NDArray of shape (15, 2) containing [x, y]
                     coordinates for each cell in row-major order.
            - cell_size: Tuple (width, height) of each cell.
        """
        boxes, cell_size = self.get_grid()
        return boxes.reshape(-1, 2), cell_size

    def get_cell_center(self, row: int, col: int) -> tuple[int, int]:
        """Get the center coordinates of a specific cell.

        Args:
            row: Row index (0-2).
            col: Column index (0-4).

        Returns:
            Tuple (center_x, center_y) in pixels.

        Raises:
            ValueError: If row or col is out of bounds.
        """
        if not (0 <= row < self.config.rows):
            raise ValueError(f"Row {row} out of bounds (0-{self.config.rows - 1})")
        if not (0 <= col < self.config.cols):
            raise ValueError(f"Col {col} out of bounds (0-{self.config.cols - 1})")

        cfg = self.config
        x = cfg.top_x + col * (cfg.cell_width + cfg.cell_gap) + cfg.cell_width // 2
        y = cfg.top_y + row * (cfg.cell_height + cfg.cell_gap) + cfg.cell_height // 2

        return (x, y)

    def get_cell_bounds(self, row: int, col: int) -> tuple[int, int, int, int]:
        """Get the bounding box of a specific cell.

        Args:
            row: Row index (0-2).
            col: Column index (0-4).

        Returns:
            Tuple (x, y, width, height).

        Raises:
            ValueError: If row or col is out of bounds.
        """
        if not (0 <= row < self.config.rows):
            raise ValueError(f"Row {row} out of bounds (0-{self.config.rows - 1})")
        if not (0 <= col < self.config.cols):
            raise ValueError(f"Col {col} out of bounds (0-{self.config.cols - 1})")

        cfg = self.config
        x = cfg.top_x + col * (cfg.cell_width + cfg.cell_gap)
        y = cfg.top_y + row * (cfg.cell_height + cfg.cell_gap)

        return (x, y, cfg.cell_width, cfg.cell_height)

    def cell_index_to_pos(self, index: int) -> tuple[int, int]:
        """Convert flat cell index to (row, col) position.

        Args:
            index: Cell index (0-14).

        Returns:
            Tuple (row, col).

        Raises:
            ValueError: If index is out of bounds.
        """
        if not (0 <= index < self.config.total_cells):
            raise ValueError(f"Index {index} out of bounds (0-{self.config.total_cells - 1})")
        row = index // self.config.cols
        col = index % self.config.cols
        return (row, col)

    def pos_to_cell_index(self, row: int, col: int) -> int:
        """Convert (row, col) position to flat cell index.

        Args:
            row: Row index (0-2).
            col: Column index (0-4).

        Returns:
            Cell index (0-14).

        Raises:
            ValueError: If row or col is out of bounds.
        """
        if not (0 <= row < self.config.rows):
            raise ValueError(f"Row {row} out of bounds (0-{self.config.rows - 1})")
        if not (0 <= col < self.config.cols):
            raise ValueError(f"Col {col} out of bounds (0-{self.config.cols - 1})")
        return row * self.config.cols + col

    @classmethod
    def from_screenshot(
        cls,
        screenshot: NDArray[np.uint8],
        config: GridConfig | None = None,
    ) -> GridExtractor:
        """Create a GridExtractor from a screenshot array.

        Args:
            screenshot: Screenshot image as numpy array (H, W, C).
            config: Optional custom GridConfig.

        Returns:
            GridExtractor configured for the screenshot's resolution.
        """
        height, width = screenshot.shape[:2]
        return cls(screen_width=width, screen_height=height, config=config)


def get_grid(
    screen_width: int = REFERENCE_WIDTH,
    screen_height: int = REFERENCE_HEIGHT,
) -> tuple[NDArray[np.int32], tuple[int, int]]:
    """Get fight grid pixel coordinates.

    This is a convenience function that creates a GridExtractor
    and returns the grid coordinates. For repeated use, consider
    creating a GridExtractor instance directly.

    Args:
        screen_width: Width of the screenshot in pixels.
        screen_height: Height of the screenshot in pixels.

    Returns:
        Tuple of:
        - boxes: NDArray of shape (rows, cols, 2) with cell coordinates.
        - cell_size: Tuple (width, height) of each cell.
    """
    extractor = GridExtractor(screen_width, screen_height)
    return extractor.get_grid()


class BotPerception:
    """Computer vision and ML-based perception system for Rush Royale.

    Handles:
    - Unit type recognition via template matching and color analysis
    - Rank detection via LogisticRegression on Canny edges
    - Grid state analysis and tracking

    The recognition uses a hybrid approach:
    1. Template matching (cv2.matchTemplate) for high-confidence matches
    2. Color histogram matching as fallback for rank variations
    """

    def __init__(self) -> None:
        """Initialize the perception system."""
        self._ref_units: list[str] = []
        self._ref_templates: list[np.ndarray] = []
        self._ref_colors: list[np.ndarray] = []
        self._ref_histograms: list[np.ndarray] = []
        self._rank_model: LogisticRegression | None = None
        self._load_reference_data()

    def _load_reference_data(self) -> None:
        """Load reference unit images, templates, and colors for matching."""
        if not UNITS_DIR.exists():
            return

        self._ref_units = []
        self._ref_templates = []
        self._ref_colors = []
        self._ref_histograms = []

        for f in sorted(UNITS_DIR.iterdir()):
            if f.suffix.lower() != ".png":
                continue

            img = cv2.imread(str(f))
            if img is None:
                continue

            self._ref_units.append(f.name)
            self._ref_templates.append(img)
            self._ref_colors.append(self._get_dominant_color(f)[0])
            self._ref_histograms.append(self._compute_color_histogram(img))

    def _load_rank_model(self) -> LogisticRegression | None:
        """Load the rank classification model from disk."""
        if self._rank_model is not None:
            return self._rank_model

        if not RANK_MODEL_PATH.exists():
            return None

        with RANK_MODEL_PATH.open("rb") as f:
            self._rank_model = pickle.load(f)
        return self._rank_model

    @staticmethod
    def _compute_color_histogram(
        img: np.ndarray,
        bins: int = 32,
    ) -> np.ndarray:
        """Compute a normalized color histogram for an image.

        Args:
            img: BGR image array.
            bins: Number of bins per channel.

        Returns:
            Flattened normalized histogram array.
        """
        # Convert to HSV for better color discrimination
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Compute histogram for H and S channels (ignore V for lighting invariance)
        hist = cv2.calcHist([hsv], [0, 1], None, [bins, bins], [0, 180, 0, 256])

        # Normalize histogram
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        return hist.flatten().astype(np.float32)

    @staticmethod
    def _get_dominant_color(
        image_path: Path | str,
        crop: bool = False,
    ) -> NDArray[np.uint8]:
        """Extract the 5 most common pixel colors from an image.

        Args:
            image_path: Path to the image file.
            crop: Whether to crop to the center unit area.

        Returns:
            Array of shape (5, 3) with RGB values of dominant colors.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            return np.zeros((5, 3), dtype=np.uint8)

        if crop:
            # Crop center area (avoid borders that vary by rank)
            h, w = img.shape[:2]
            margin_x = int(w * 0.15)
            margin_y = int(h * 0.15)
            img = img[margin_y : h - margin_y, margin_x : w - margin_x]

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Flatten and quantize colors
        flat = img_rgb.reshape(-1, 3)
        quantized = (flat // 20) * 20

        unique, counts = np.unique(quantized, axis=0, return_counts=True)

        colors = np.zeros((5, 3), dtype=np.uint8)
        if len(unique) < 5:
            # Not enough unique colors, return what we have
            for i in range(min(len(unique), 5)):
                colors[i] = unique[i]
            return colors

        # Get top 5 most common colors
        sorted_indices = np.argsort(counts)[::-1]
        for i in range(min(5, len(sorted_indices))):
            colors[i] = unique[sorted_indices[i]]

        return colors

    def _match_template(
        self,
        img: np.ndarray,
    ) -> tuple[str, float]:
        """Match an image against reference templates using template matching.

        Args:
            img: BGR image to match.

        Returns:
            Tuple of (unit_name, confidence). Higher confidence = better match.
        """
        if not self._ref_templates:
            return ("unknown.png", 0.0)

        best_match = "unknown.png"
        best_score = 0.0

        # Resize input to match template size if needed
        template_h, template_w = self._ref_templates[0].shape[:2]
        if img.shape[:2] != (template_h, template_w):
            img = cv2.resize(img, (template_w, template_h))

        for i, template in enumerate(self._ref_templates):
            # Use normalized cross-correlation
            result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
            score = float(result[0, 0])

            if score > best_score:
                best_score = score
                best_match = self._ref_units[i]

        return (best_match, best_score)

    def _match_histogram(
        self,
        img: np.ndarray,
    ) -> tuple[str, float]:
        """Match an image against references using histogram comparison.

        Args:
            img: BGR image to match.

        Returns:
            Tuple of (unit_name, correlation). Higher = better match.
        """
        if not self._ref_histograms:
            return ("unknown.png", 0.0)

        input_hist = self._compute_color_histogram(img)

        best_match = "unknown.png"
        best_score = 0.0

        for i, ref_hist in enumerate(self._ref_histograms):
            # Use correlation comparison (1.0 = identical)
            score = float(cv2.compareHist(input_hist, ref_hist, cv2.HISTCMP_CORREL))

            if score > best_score:
                best_score = score
                best_match = self._ref_units[i]

        return (best_match, best_score)

    def match_unit(self, image_path: Path | str) -> tuple[str, float]:
        """Match a unit image to known unit types using hybrid approach.

        Uses a combination of template matching and histogram comparison
        for robust recognition across different unit ranks.

        Args:
            image_path: Path to the unit screenshot.

        Returns:
            Tuple of (unit_name, confidence). Higher confidence = better match.
            Confidence is normalized to 0-1 range.
        """
        if not self._ref_units:
            return ("unknown.png", 0.0)

        img = cv2.imread(str(image_path))
        if img is None:
            return ("unknown.png", 0.0)

        # Method 1: Template matching (works best for exact rank match)
        template_match, template_score = self._match_template(img)

        # If high confidence template match, use it directly
        if template_score >= TEMPLATE_MATCH_THRESHOLD:
            return (template_match, template_score)

        # Method 2: Histogram comparison (more robust to rank variations)
        hist_match, hist_score = self._match_histogram(img)

        # Method 3: Color matching as final fallback
        unit_colors = self._get_dominant_color(image_path, crop=True)

        color_match = "empty.png"
        color_score = 0.0

        for color in unit_colors:
            mse = np.sum((np.array(self._ref_colors) - color) ** 2, axis=1)
            min_idx = int(mse.argmin())
            min_mse = float(mse[min_idx])

            if min_mse <= COLOR_MSE_THRESHOLD:
                # Convert MSE to confidence (lower MSE = higher confidence)
                confidence = 1.0 - (min_mse / COLOR_MSE_THRESHOLD)
                if confidence > color_score:
                    color_score = confidence
                    color_match = self._ref_units[min_idx]
                break

        # Combine results: prefer highest confidence method
        results = [
            (template_match, template_score),
            (hist_match, hist_score),
            (color_match, color_score),
        ]

        # Filter out empty/unknown and pick best
        valid_results = [
            (name, score)
            for name, score in results
            if name not in ("unknown.png", "empty.png") and score > 0.3
        ]

        if valid_results:
            return max(valid_results, key=lambda x: x[1])

        # No good match - check if it's an empty slot
        if self._is_empty_slot(img):
            return ("empty.png", 1.0)

        return ("unknown.png", 0.0)

    def _is_empty_slot(self, img: np.ndarray) -> bool:
        """Check if an image represents an empty grid slot.

        Args:
            img: BGR image to check.

        Returns:
            True if the slot appears empty.
        """
        # Empty slots tend to be dark/uniform
        gray: np.ndarray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_val = float(gray.mean())
        std_val = float(gray.std())

        # Empty slots have low brightness and low variance
        return mean_val < 50 and std_val < 30

    def match_rank(self, image_path: Path | str) -> tuple[int, float]:
        """Detect the rank of a unit using edge detection + ML.

        Args:
            image_path: Path to the unit screenshot.

        Returns:
            Tuple of (rank, confidence). Rank 0 = empty slot.
        """
        model = self._load_rank_model()
        if model is None:
            return (0, 0.0)

        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return (0, 0.0)

        edges = cv2.Canny(img, 50, 100)
        prob = model.predict_proba(edges.reshape(1, -1))

        return (int(prob.argmax()), float(prob.max()))

    def match_unit_array(self, img: np.ndarray) -> tuple[str, float]:
        """Match a unit image array to known unit types.

        This is an array-accepting variant of match_unit for in-memory images.

        Args:
            img: BGR image array of the unit.

        Returns:
            Tuple of (unit_name, confidence). Higher confidence = better match.
        """
        if not self._ref_units or img is None or img.size == 0:
            return ("unknown.png", 0.0)

        # Method 1: Template matching
        template_match, template_score = self._match_template(img)

        if template_score >= TEMPLATE_MATCH_THRESHOLD:
            return (template_match, template_score)

        # Method 2: Histogram comparison
        hist_match, hist_score = self._match_histogram(img)

        # Combine results
        results = [
            (template_match, template_score),
            (hist_match, hist_score),
        ]

        valid_results = [
            (name, score)
            for name, score in results
            if name not in ("unknown.png", "empty.png") and score > 0.3
        ]

        if valid_results:
            return max(valid_results, key=lambda x: x[1])

        if self._is_empty_slot(img):
            return ("empty.png", 1.0)

        return ("unknown.png", 0.0)

    def match_rank_array(self, img: np.ndarray) -> tuple[int, float]:
        """Detect the rank of a unit from an image array.

        This is an array-accepting variant of match_rank for in-memory images.

        Args:
            img: BGR or grayscale image array.

        Returns:
            Tuple of (rank, confidence). Rank 0 = empty slot.
        """
        model = self._load_rank_model()
        if model is None or img is None or img.size == 0:
            return (0, 0.0)

        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        edges = cv2.Canny(gray, 50, 100)
        prob = model.predict_proba(edges.reshape(1, -1))

        return (int(prob.argmax()), float(prob.max()))

    def analyze_grid(
        self,
        image_paths: list[Path | str],
        previous_grid: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Analyze the full 3x5 game grid.

        Args:
            image_paths: List of 15 paths to unit screenshots (row-major order).
            previous_grid: Previous grid state for consistency tracking.

        Returns:
            DataFrame with columns: grid_pos, unit, u_prob, rank, r_prob, Age
        """
        grid_stats: list[list] = []

        for _i, path in enumerate(image_paths):
            rank, rank_conf = self.match_rank(path)

            if rank != 0:
                unit, unit_err = self.match_unit(path)
            else:
                unit, unit_err = ("empty.png", 0.0)

            grid_stats.append([unit, unit_err, rank, rank_conf])

        df = pd.DataFrame(
            grid_stats,
            columns=["unit", "u_prob", "rank", "r_prob"],
        )

        # Add grid position as [row, col]
        positions = [[(i // 5) % 3, i % 5] for i in range(15)]
        df.insert(0, "grid_pos", positions)

        # Track consistency with previous grid
        if previous_grid is not None:
            consistency = (
                (df["grid_pos"] == previous_grid["grid_pos"])
                & (df["unit"] == previous_grid["unit"])
                & (df["rank"] == previous_grid["rank"])
            )
            df["Age"] = previous_grid["Age"] * consistency + consistency
        else:
            df["Age"] = 0

        return df

    def find_adjacent_unit(
        self,
        grid_df: pd.DataFrame,
        target_unit: str = "demon_hunter.png",
        adjacent_unit: str = "knight_statue.png",
    ) -> int | None:
        """Find the lowest-rank adjacent unit next to highest-rank target.

        Useful for finding merge targets (e.g., lowest Knight Statue
        adjacent to highest Demon Hunter).

        Args:
            grid_df: Grid DataFrame from analyze_grid().
            target_unit: The main unit to find adjacencies for.
            adjacent_unit: The adjacent unit type to look for.

        Returns:
            Index of the best adjacent unit, or None if not found.
        """
        target_df = grid_df[grid_df["unit"] == target_unit]
        if target_df.empty:
            return None

        # Get highest rank target
        target_df = target_df.sort_values("rank", ascending=False)
        target_pos = target_df.iloc[0]["grid_pos"]

        # Calculate adjacent positions
        row, col = target_pos
        adjacents = [
            (row, col - 1),
            (row, col + 1),
            (row - 1, col),
            (row + 1, col),
        ]

        # Filter valid positions
        valid_adjacent = [(r, c) for r, c in adjacents if 0 <= r < 3 and 0 <= c < 5]

        # Find adjacent units of the target type
        adjacent_indices = []
        for i, pos in enumerate(grid_df["grid_pos"]):
            if tuple(pos) in valid_adjacent and grid_df.iloc[i]["unit"] == adjacent_unit:
                adjacent_indices.append(i)

        if not adjacent_indices:
            return None

        # Return lowest rank adjacent unit
        adj_df = grid_df.iloc[adjacent_indices].sort_values("rank", ascending=True)
        return int(adj_df.index[0])


# === Training Functions ===


def ensure_training_dirs() -> None:
    """Create training data directories if they don't exist."""
    OCR_INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    ML_INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    ML_RAW_INPUT_DIR.mkdir(parents=True, exist_ok=True)


def add_grid_to_dataset() -> int:
    """Append current OCR_inputs images to the ML dataset.

    Uses the current rank model to generate labels.
    For best results, prefer manually labeled datasets.

    Returns:
        Number of images added.
    """
    ensure_training_dirs()
    if not OCR_INPUTS_DIR.exists():
        return 0

    perception = BotPerception()
    example_count = len(list(ML_INPUTS_DIR.glob("*_input_*.png")))
    added = 0

    for slot_path in OCR_INPUTS_DIR.iterdir():
        if slot_path.suffix.lower() != ".png":
            continue

        img = cv2.imread(str(slot_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        edges = cv2.Canny(img, 50, 100)
        rank_guess, _ = perception.match_rank(slot_path)

        # Save edge-detected image for training
        cv2.imwrite(
            str(ML_INPUTS_DIR / f"{rank_guess}_input_{example_count}.png"),
            edges,
        )
        # Save raw image for reference
        cv2.imwrite(
            str(ML_RAW_INPUT_DIR / f"{rank_guess}_raw_{example_count}.png"),
            img,
        )

        example_count += 1
        added += 1

    return added


def load_dataset(folder: Path | str) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    """Load labeled training images from a directory.

    Supports two layouts:
    - Flat: files like "<rank>_input_123.png"
    - Hierarchical: subfolders "0/", "1/", etc. containing PNGs

    Args:
        folder: Path to the dataset directory.

    Returns:
        Tuple of (X, y) arrays for training.

    Raises:
        RuntimeError: If no training images are found.
    """
    folder_path = Path(folder)
    X_train: list[NDArray] = []
    y_train: list[int] = []

    # Layout A: flat files like "<rank>_input_123.png"
    for p in folder_path.glob("*_input_*.png"):
        label = p.name.split("_input", 1)[0]
        if label.isdigit():
            img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                X_train.append(img)
                y_train.append(int(label))

    # Layout B: hierarchical subfolders
    for sub in folder_path.iterdir():
        if not sub.is_dir() or not sub.name.isdigit():
            continue
        label_int = int(sub.name)
        for p in sub.glob("*.png"):
            img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                X_train.append(img)
                y_train.append(label_int)

    if not X_train:
        raise RuntimeError(f"No training images found in: {folder_path}")

    X = np.array(X_train)
    # Flatten images for the classifier
    X = X.reshape(X.shape[0], -1).astype(np.float64)
    y = np.array(y_train, dtype=np.int64)

    return X, y


def train_rank_model(
    dataset_dir: Path | str = ML_INPUTS_DIR,
    max_iter: int = 200,
) -> LogisticRegression:
    """Train a new rank classification model.

    Args:
        dataset_dir: Directory containing labeled training images.
        max_iter: Maximum iterations for logistic regression.

    Returns:
        Trained LogisticRegression model.
    """
    X_train, y_train = load_dataset(dataset_dir)

    model = LogisticRegression(max_iter=max_iter)
    model.fit(X_train, y_train)

    return model


def save_rank_model(
    model: LogisticRegression,
    path: Path | str = RANK_MODEL_PATH,
) -> Path:
    """Save a trained rank model to disk.

    Args:
        model: Trained LogisticRegression model.
        path: Output file path.

    Returns:
        Path where the model was saved.
    """
    out = Path(path)
    with out.open("wb") as f:
        pickle.dump(model, f)
    return out


def quick_train_model() -> LogisticRegression:
    """Train a new model using the default ML inputs directory.

    Convenience function for interactive use.

    Returns:
        Trained model.
    """
    ensure_training_dirs()
    return train_rank_model(ML_INPUTS_DIR)
