"""
Rush Royale Bot - Unit Detector
Python 3.13 Compatible

Modern unit type detection using improved feature extraction
combining color histograms and shape features.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class UnitDetector:
    """
    Detects unit types from grid cell images.
    
    Improvements over legacy color-matching:
    - HSV color histograms (more robust to lighting)
    - Optional HOG features for shape
    - KNN or SVM classifier
    - Proper empty cell detection
    
    Example:
        detector = UnitDetector()
        detector.load_references("units/")
        
        unit_type, confidence = detector.predict(cell_image)
    """
    
    def __init__(self):
        """Initialize unit detector."""
        self.reference_colors: dict[str, np.ndarray] = {}
        self.reference_histograms: dict[str, np.ndarray] = {}
        self.unit_names: list[str] = []
        
        # Thresholds
        self.empty_threshold = 2000  # MSE threshold for empty detection
        self.match_threshold = 0.5   # Histogram correlation threshold
    
    def extract_color_features(
        self, 
        image: np.ndarray,
        crop: bool = True
    ) -> np.ndarray:
        """
        Extract dominant colors from image.
        
        Args:
            image: BGR image
            crop: Whether to crop to unit area
            
        Returns:
            Array of top 5 dominant colors (5x3)
        """
        if len(image.shape) != 3:
            # Grayscale - can't extract colors
            return np.zeros((5, 3), dtype=int)
        
        if crop:
            h, w = image.shape[:2]
            # Crop to center unit area
            margin_x = int(w * 0.14)
            margin_y = int(h * 0.125)
            image = image[margin_y:h-margin_y, margin_x:w-margin_x]
        
        # Convert to RGB
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Flatten and quantize colors
        flat = rgb.reshape(-1, 3)
        flat_quantized = (flat // 20) * 20
        
        # Find unique colors and counts
        unique, counts = np.unique(flat_quantized, axis=0, return_counts=True)
        
        if len(unique) < 10:
            return np.zeros((5, 3), dtype=int)
        
        # Get top 5 most common colors
        top_indices = np.argsort(counts)[-5:][::-1]
        colors = unique[top_indices]
        
        return colors
    
    def extract_histogram(
        self,
        image: np.ndarray,
        crop: bool = True
    ) -> np.ndarray:
        """
        Extract HSV color histogram from image.
        
        More robust than raw color matching for:
        - Different lighting conditions
        - Slight position variations
        
        Args:
            image: BGR image
            crop: Whether to crop to unit area
            
        Returns:
            Normalized histogram vector
        """
        if len(image.shape) != 3:
            return np.zeros(32 * 32)
        
        if crop:
            h, w = image.shape[:2]
            margin_x = int(w * 0.14)
            margin_y = int(h * 0.125)
            image = image[margin_y:h-margin_y, margin_x:w-margin_x]
        
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Calculate histogram (H and S channels)
        hist = cv2.calcHist(
            [hsv], 
            [0, 1],  # H and S channels
            None, 
            [32, 32],  # 32 bins each
            [0, 180, 0, 256]  # H: 0-180, S: 0-256
        )
        
        # Normalize
        hist = cv2.normalize(hist, hist).flatten()
        
        return hist
    
    def load_references(self, units_dir: Path | str = "units") -> None:
        """
        Load reference images for all unit types.
        
        Args:
            units_dir: Directory containing unit reference images
        """
        import os
        
        units_dir = Path(units_dir)
        
        if not units_dir.exists():
            logger.warning(f"Units directory not found: {units_dir}")
            return
        
        self.unit_names = []
        self.reference_colors = {}
        self.reference_histograms = {}
        
        for unit_file in os.listdir(units_dir):
            if not unit_file.endswith('.png'):
                continue
            
            unit_path = units_dir / unit_file
            image = cv2.imread(str(unit_path))
            
            if image is None:
                logger.warning(f"Could not load: {unit_path}")
                continue
            
            # Extract features
            colors = self.extract_color_features(image, crop=False)
            hist = self.extract_histogram(image, crop=False)
            
            self.unit_names.append(unit_file)
            self.reference_colors[unit_file] = colors[0]  # Primary color
            self.reference_histograms[unit_file] = hist
        
        logger.info(f"Loaded {len(self.unit_names)} unit references")
    
    def predict(
        self, 
        image: np.ndarray,
        use_histogram: bool = True
    ) -> tuple[str, float]:
        """
        Predict unit type from cell image.
        
        Args:
            image: Grid cell image (BGR)
            use_histogram: Use histogram matching (more robust)
            
        Returns:
            Tuple of (unit_name, confidence)
        """
        if not self.unit_names:
            raise RuntimeError("No references loaded. Call load_references() first.")
        
        if use_histogram:
            return self._predict_histogram(image)
        else:
            return self._predict_color(image)
    
    def _predict_color(self, image: np.ndarray) -> tuple[str, float]:
        """Predict using color matching (legacy method)."""
        colors = self.extract_color_features(image, crop=True)
        
        best_match = 'empty.png'
        best_score = float('inf')
        
        for color in colors:
            for unit_name, ref_color in self.reference_colors.items():
                mse = np.sum((ref_color - color) ** 2)
                if mse < best_score:
                    best_score = mse
                    best_match = unit_name
        
        # Empty detection
        if best_score > self.empty_threshold:
            return 'empty.png', 0.0
        
        # Convert MSE to confidence (lower is better)
        confidence = max(0.0, 1.0 - best_score / self.empty_threshold)
        
        return best_match, confidence
    
    def _predict_histogram(self, image: np.ndarray) -> tuple[str, float]:
        """Predict using histogram correlation."""
        query_hist = self.extract_histogram(image, crop=True)
        
        best_match = 'empty.png'
        best_score = -1.0
        
        for unit_name, ref_hist in self.reference_histograms.items():
            # Compare histograms using correlation
            score = cv2.compareHist(
                query_hist.astype(np.float32),
                ref_hist.astype(np.float32),
                cv2.HISTCMP_CORREL
            )
            
            if score > best_score:
                best_score = score
                best_match = unit_name
        
        # Empty detection based on low correlation
        if best_score < self.match_threshold:
            return 'empty.png', 0.0
        
        return best_match, float(best_score)
    
    def predict_batch(
        self,
        images: list[np.ndarray],
        use_histogram: bool = True
    ) -> list[tuple[str, float]]:
        """
        Predict unit types for multiple images.
        
        Args:
            images: List of grid cell images
            use_histogram: Use histogram matching
            
        Returns:
            List of (unit_name, confidence) tuples
        """
        return [self.predict(img, use_histogram) for img in images]
    
    def is_empty(
        self,
        image: np.ndarray,
        rank: int = 0
    ) -> bool:
        """
        Check if cell is empty.
        
        Args:
            image: Grid cell image
            rank: Detected rank (0 indicates likely empty)
            
        Returns:
            True if cell appears empty
        """
        if rank == 0:
            return True
        
        unit, conf = self.predict(image)
        return unit == 'empty.png' or conf < 0.3
