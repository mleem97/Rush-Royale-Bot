#!/usr/bin/env python3
"""
Rush Royale Bot - Perception System
Computer vision, unit recognition, and game state analysis
"""

import os
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from sklearn.externals import joblib  # For loading ML models


class PerceptionSystem:
    """Handles computer vision and game state recognition"""
    
    def __init__(self, units_path: str = "data/units", icons_path: str = "data/icons"):
        self.logger = logging.getLogger(__name__)
        self.units_path = Path(units_path)
        self.icons_path = Path(icons_path)
        
        # Recognition parameters
        self.mse_threshold = 2000  # Color matching threshold
        self.confidence_threshold = 0.7
        
        # Cached reference data
        self.unit_colors = {}
        self.icon_templates = {}
        self.rank_model = None
        
        self._load_reference_data()
    
    def _load_reference_data(self):
        """Load reference colors and templates"""
        try:
            # Load unit reference colors
            if self.units_path.exists():
                for unit_file in self.units_path.glob("*.png"):
                    unit_name = unit_file.name
                    colors = self._extract_dominant_colors(str(unit_file))
                    self.unit_colors[unit_name] = colors
                
                self.logger.info(f"Loaded {len(self.unit_colors)} unit references")
            
            # Load icon templates
            if self.icons_path.exists():
                for icon_file in self.icons_path.glob("*.png"):
                    icon_name = icon_file.name
                    template = cv2.imread(str(icon_file))
                    self.icon_templates[icon_name] = template
                
                self.logger.info(f"Loaded {len(self.icon_templates)} icon templates")
            
            # Load ML rank model
            model_path = Path("data/models/rank_model.pkl")
            if model_path.exists():
                self.rank_model = joblib.load(str(model_path))
                self.logger.info("Loaded rank detection model")
            
        except Exception as e:
            self.logger.error(f"Failed to load reference data: {e}")
    
    def _extract_dominant_colors(self, image_path: str, k: int = 3) -> np.ndarray:
        """Extract dominant colors from image using K-means clustering"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return np.array([])
            
            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Reshape image to be a list of pixels
            pixels = image_rgb.reshape(-1, 3)
            
            # Remove black/transparent pixels
            pixels = pixels[np.sum(pixels, axis=1) > 30]
            
            if len(pixels) == 0:
                return np.array([])
            
            # Apply K-means clustering
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=min(k, len(pixels)), random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            # Get dominant colors
            colors = kmeans.cluster_centers_.astype(int)
            return colors
            
        except Exception as e:
            self.logger.warning(f"Failed to extract colors from {image_path}: {e}")
            return np.array([])
    
    def detect_icons(self, screenshot_path: str) -> pd.DataFrame:
        """Detect UI icons in screenshot"""
        try:
            screenshot = cv2.imread(screenshot_path)
            if screenshot is None:
                return pd.DataFrame()
            
            detected_icons = []
            
            for icon_name, template in self.icon_templates.items():
                if template is None:
                    continue
                
                # Template matching
                result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
                locations = np.where(result >= self.confidence_threshold)
                
                for pt in zip(*locations[::-1]):  # Switch x and y
                    detected_icons.append({
                        'icon': icon_name,
                        'pos [X,Y]': [pt[0], pt[1]],
                        'confidence': result[pt[1], pt[0]]
                    })
            
            # Convert to DataFrame and remove duplicates
            df = pd.DataFrame(detected_icons)
            if not df.empty:
                # Remove overlapping detections (keep highest confidence)
                df = self._remove_overlapping_detections(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Icon detection failed: {e}")
            return pd.DataFrame()
    
    def _remove_overlapping_detections(self, df: pd.DataFrame, overlap_threshold: int = 50) -> pd.DataFrame:
        """Remove overlapping icon detections"""
        if df.empty:
            return df
        
        # Sort by confidence descending
        df = df.sort_values('confidence', ascending=False)
        
        keep_indices = []
        positions = np.array([pos for pos in df['pos [X,Y]']])
        
        for i, pos in enumerate(positions):
            if i in keep_indices:
                continue
            
            # Check if this position overlaps with any kept position
            overlaps = False
            for kept_idx in keep_indices:
                kept_pos = positions[kept_idx]
                distance = np.linalg.norm(pos - kept_pos)
                if distance < overlap_threshold:
                    overlaps = True
                    break
            
            if not overlaps:
                keep_indices.append(i)
        
        return df.iloc[keep_indices].reset_index(drop=True)
    
    def recognize_units(self, unit_image_paths: List[str]) -> pd.DataFrame:
        """Recognize units from cropped images"""
        results = []
        
        for i, image_path in enumerate(unit_image_paths):
            try:
                # Extract colors from unit image
                unit_colors = self._extract_dominant_colors(image_path)
                
                if len(unit_colors) == 0:
                    # Empty slot
                    results.append({
                        'slot': i,
                        'unit': 'empty.png',
                        'confidence': 1.0,
                        'rank': 0
                    })
                    continue
                
                # Find best matching unit
                best_match = self._find_best_unit_match(unit_colors)
                
                # Predict rank if model is available
                rank = 0
                if self.rank_model is not None:
                    rank = self._predict_unit_rank(image_path)
                
                results.append({
                    'slot': i,
                    'unit': best_match['unit'],
                    'confidence': best_match['confidence'],
                    'rank': rank
                })
                
            except Exception as e:
                self.logger.warning(f"Failed to recognize unit {i}: {e}")
                results.append({
                    'slot': i,
                    'unit': 'unknown.png',
                    'confidence': 0.0,
                    'rank': 0
                })
        
        return pd.DataFrame(results)
    
    def _find_best_unit_match(self, unit_colors: np.ndarray) -> Dict:
        """Find best matching unit based on color similarity"""
        best_match = {'unit': 'empty.png', 'confidence': 0.0}
        lowest_mse = float('inf')
        
        for unit_name, ref_colors in self.unit_colors.items():
            if len(ref_colors) == 0:
                continue
            
            # Calculate MSE between color sets
            mse = self._calculate_color_mse(unit_colors, ref_colors)
            
            if mse < lowest_mse and mse <= self.mse_threshold:
                lowest_mse = mse
                confidence = max(0.0, 1.0 - (mse / self.mse_threshold))
                best_match = {
                    'unit': unit_name,
                    'confidence': confidence
                }
        
        return best_match
    
    def _calculate_color_mse(self, colors1: np.ndarray, colors2: np.ndarray) -> float:
        """Calculate mean squared error between two color sets"""
        if len(colors1) == 0 or len(colors2) == 0:
            return float('inf')
        
        # Find optimal pairing between color sets
        min_mse = float('inf')
        
        for c1 in colors1:
            for c2 in colors2:
                mse = np.mean((c1 - c2) ** 2)
                min_mse = min(min_mse, mse)
        
        return min_mse
    
    def _predict_unit_rank(self, image_path: str) -> int:
        """Predict unit rank using ML model"""
        try:
            if self.rank_model is None:
                return 1
            
            # Load and preprocess image for rank prediction
            image = cv2.imread(image_path)
            if image is None:
                return 1
            
            # Resize to standard size
            image_resized = cv2.resize(image, (64, 64))
            
            # Convert to feature vector (simplified)
            features = image_resized.flatten()
            
            # Predict rank
            rank = self.rank_model.predict([features])[0]
            return max(1, min(7, int(rank)))  # Clamp to valid rank range
            
        except Exception as e:
            self.logger.warning(f"Rank prediction failed for {image_path}: {e}")
            return 1
    
    def analyze_grid_state(self, unit_files: List[str], previous_grid: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Analyze current grid state from unit image files"""
        # Recognize units
        unit_df = self.recognize_units(unit_files)
        
        # Add grid positions
        unit_df['grid_pos'] = [(i % 5, i // 5) for i in range(len(unit_df))]
        
        # Add age tracking if previous grid provided
        if previous_grid is not None:
            unit_df = self._track_unit_age(unit_df, previous_grid)
        else:
            unit_df['age'] = 0
        
        return unit_df
    
    def _track_unit_age(self, current_grid: pd.DataFrame, previous_grid: pd.DataFrame) -> pd.DataFrame:
        """Track how long units have been in each position"""
        current_grid = current_grid.copy()
        current_grid['age'] = 0
        
        if previous_grid.empty:
            return current_grid
        
        # Match units between grids
        for idx, row in current_grid.iterrows():
            # Find matching unit in previous grid
            prev_match = previous_grid[
                (previous_grid['slot'] == row['slot']) &
                (previous_grid['unit'] == row['unit']) &
                (previous_grid['rank'] == row['rank'])
            ]
            
            if not prev_match.empty:
                # Unit unchanged, increment age
                current_grid.at[idx, 'age'] = prev_match.iloc[0]['age'] + 1
        
        return current_grid
    
    def get_store_state(self, screenshot_path: str) -> str:
        """Analyze store state from screenshot"""
        try:
            screenshot = cv2.imread(screenshot_path)
            if screenshot is None:
                return 'unknown'
            
            # Define store state colors and positions
            x, y = 140, 1412
            if y >= screenshot.shape[0] or x >= screenshot.shape[1]:
                return 'unknown'
            
            store_pixel = screenshot[y, x]  # BGR format
            
            # Define known store states (BGR values)
            store_states = {
                'refresh': [255, 255, 255],
                'new_store': [206, 235, 27],
                'nothing': [12, 38, 63],
                'new_offer': [251, 253, 48],
                'spin_only': [193, 153, 80]
            }
            
            # Find closest match
            best_match = 'unknown'
            min_distance = float('inf')
            
            for state_name, bgr_values in store_states.items():
                distance = np.linalg.norm(store_pixel - np.array(bgr_values))
                if distance < min_distance:
                    min_distance = distance
                    best_match = state_name
            
            return best_match
            
        except Exception as e:
            self.logger.error(f"Store state analysis failed: {e}")
            return 'unknown'
    
    def reload_references(self):
        """Reload reference data (useful after updating unit deck)"""
        self.unit_colors.clear()
        self.icon_templates.clear()
        self._load_reference_data()
        self.logger.info("Reference data reloaded")


# Utility functions
def setup_unit_deck(unit_names: List[str], source_path: str = "all_units", target_path: str = "data/units"):
    """Copy selected units from source to active deck"""
    source_dir = Path(source_path)
    target_dir = Path(target_path)
    
    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Clear existing units
    for existing_file in target_dir.glob("*.png"):
        existing_file.unlink()
    
    # Copy selected units
    copied_count = 0
    for unit_name in unit_names:
        if not unit_name.endswith('.png'):
            unit_name += '.png'
        
        source_file = source_dir / unit_name
        target_file = target_dir / unit_name
        
        if source_file.exists():
            import shutil
            shutil.copy2(source_file, target_file)
            copied_count += 1
    
    return copied_count >= 4  # Minimum viable unit count
