#!/usr/bin/env python3
"""
Rush Royale Bot - Recognition Module
Advanced unit recognition and game state analysis
"""

import os
import time
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib


class UnitRecognizer:
    """Advanced unit recognition system"""
    
    def __init__(self, units_path: str = "all_units", model_path: str = "rank_model.pkl"):
        self.units_path = Path(units_path)
        self.model_path = Path(model_path)
        self.logger = logging.getLogger(__name__)
        
        # Unit templates
        self.unit_templates = {}
        self.unit_names = []
        
        # ML model for rank recognition
        self.rank_model = None
        self.rank_scaler = None
        
        # Recognition parameters
        self.match_threshold = 0.7
        self.rank_confidence_threshold = 0.6
        
        # Unit colors for enhanced recognition
        self.unit_colors = {}
        
        # Initialize system
        self._load_unit_templates()
        self._load_rank_model()
        
        self.logger.info(f"Unit recognizer initialized with {len(self.unit_templates)} templates")
    
    def _load_unit_templates(self):
        """Load unit templates from all_units directory"""
        try:
            if not self.units_path.exists():
                self.logger.error(f"Units directory not found: {self.units_path}")
                return
            
            # Load all unit images
            for unit_file in self.units_path.glob("*.png"):
                unit_name = unit_file.stem
                
                # Skip certain files
                if unit_name in ['empty', 'old_icon']:
                    continue
                
                try:
                    template = cv2.imread(str(unit_file))
                    if template is not None:
                        self.unit_templates[unit_name] = template
                        self.unit_names.append(unit_name)
                        
                        # Extract dominant color for this unit
                        self.unit_colors[unit_name] = self._extract_dominant_color(template)
                        
                except Exception as e:
                    self.logger.warning(f"Could not load template {unit_file}: {e}")
            
            self.logger.info(f"Loaded {len(self.unit_templates)} unit templates")
            
        except Exception as e:
            self.logger.error(f"Error loading unit templates: {e}")
    
    def _load_rank_model(self):
        """Load machine learning model for rank recognition"""
        try:
            if self.model_path.exists():
                self.rank_model = joblib.load(self.model_path)
                self.logger.info("Rank recognition model loaded")
            else:
                self.logger.warning(f"Rank model not found: {self.model_path}")
                # Create a simple model if none exists
                self._create_basic_rank_model()
                
        except Exception as e:
            self.logger.error(f"Error loading rank model: {e}")
            self._create_basic_rank_model()
    
    def _create_basic_rank_model(self):
        """Create basic rank recognition model"""
        try:
            # Create a simple RandomForest model
            self.rank_model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.rank_scaler = StandardScaler()
            
            # This would need training data in a real implementation
            self.logger.info("Created basic rank model (needs training)")
            
        except Exception as e:
            self.logger.error(f"Error creating rank model: {e}")
    
    def _extract_dominant_color(self, image) -> Tuple[int, int, int]:
        """Extract dominant color from unit image"""
        try:
            # Reshape image to list of pixels
            pixels = image.reshape(-1, 3)
            
            # Remove very dark pixels (background)
            bright_pixels = pixels[np.sum(pixels, axis=1) > 100]
            
            if len(bright_pixels) > 0:
                # Calculate mean color
                mean_color = np.mean(bright_pixels, axis=0)
                return tuple(map(int, mean_color))
            else:
                return (128, 128, 128)  # Default gray
                
        except Exception as e:
            self.logger.debug(f"Error extracting dominant color: {e}")
            return (128, 128, 128)
    
    def recognize_unit(self, unit_image, position: Tuple[int, int] = None) -> Dict[str, Any]:
        """Recognize unit from image crop"""
        try:
            if unit_image is None or unit_image.size == 0:
                return {
                    'unit_name': 'empty',
                    'confidence': 0.0,
                    'rank': 1,
                    'position': position
                }
            
            best_match = self._template_matching(unit_image)
            
            # Enhance with color analysis
            color_match = self._color_matching(unit_image, best_match['unit_name'])
            
            # Combine template and color confidence
            combined_confidence = (best_match['confidence'] * 0.8 + color_match * 0.2)
            
            # Recognize rank if unit is identified
            rank = 1
            if combined_confidence > self.match_threshold:
                rank = self._recognize_rank(unit_image, best_match['unit_name'])
            
            result = {
                'unit_name': best_match['unit_name'],
                'confidence': combined_confidence,
                'rank': rank,
                'position': position,
                'template_confidence': best_match['confidence'],
                'color_confidence': color_match
            }
            
            self.logger.debug(f"Unit recognized: {result['unit_name']} "
                            f"(conf: {result['confidence']:.3f}, rank: {rank})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Unit recognition error: {e}")
            return {
                'unit_name': 'unknown',
                'confidence': 0.0,
                'rank': 1,
                'position': position
            }
    
    def _template_matching(self, unit_image) -> Dict[str, Any]:
        """Perform template matching against all unit templates"""
        best_confidence = 0.0
        best_match = 'empty'
        
        try:
            # Resize unit image to standard size
            standard_size = (64, 64)  # Adjust based on your templates
            unit_resized = cv2.resize(unit_image, standard_size)
            
            for unit_name, template in self.unit_templates.items():
                try:
                    # Resize template to match
                    template_resized = cv2.resize(template, standard_size)
                    
                    # Multiple matching methods
                    confidences = []
                    
                    # Template matching
                    result = cv2.matchTemplate(unit_resized, template_resized, 
                                             cv2.TM_CCOEFF_NORMED)
                    confidence = np.max(result)
                    confidences.append(confidence)
                    
                    # Histogram comparison
                    hist_confidence = self._compare_histograms(unit_resized, template_resized)
                    confidences.append(hist_confidence)
                    
                    # Feature matching (if applicable)
                    feature_confidence = self._feature_matching(unit_resized, template_resized)
                    confidences.append(feature_confidence)
                    
                    # Combined confidence
                    combined_confidence = np.mean(confidences)
                    
                    if combined_confidence > best_confidence:
                        best_confidence = combined_confidence
                        best_match = unit_name
                        
                except Exception as e:
                    self.logger.debug(f"Template matching error for {unit_name}: {e}")
                    continue
            
            return {
                'unit_name': best_match,
                'confidence': best_confidence
            }
            
        except Exception as e:
            self.logger.error(f"Template matching error: {e}")
            return {
                'unit_name': 'empty',
                'confidence': 0.0
            }
    
    def _compare_histograms(self, img1, img2) -> float:
        """Compare color histograms of two images"""
        try:
            # Calculate histograms
            hist1 = cv2.calcHist([img1], [0, 1, 2], None, [50, 50, 50], [0, 256, 0, 256, 0, 256])
            hist2 = cv2.calcHist([img2], [0, 1, 2], None, [50, 50, 50], [0, 256, 0, 256, 0, 256])
            
            # Compare histograms
            correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            
            return max(0.0, correlation)
            
        except Exception as e:
            self.logger.debug(f"Histogram comparison error: {e}")
            return 0.0
    
    def _feature_matching(self, img1, img2) -> float:
        """Feature-based matching using ORB detector"""
        try:
            # Convert to grayscale
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            # Initialize ORB detector
            orb = cv2.ORB_create()
            
            # Find keypoints and descriptors
            kp1, des1 = orb.detectAndCompute(gray1, None)
            kp2, des2 = orb.detectAndCompute(gray2, None)
            
            if des1 is None or des2 is None:
                return 0.0
            
            # Match features
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            
            if len(matches) == 0:
                return 0.0
            
            # Calculate confidence based on good matches
            good_matches = [m for m in matches if m.distance < 50]
            confidence = len(good_matches) / max(len(kp1), len(kp2))
            
            return min(1.0, confidence)
            
        except Exception as e:
            self.logger.debug(f"Feature matching error: {e}")
            return 0.0
    
    def _color_matching(self, unit_image, unit_name: str) -> float:
        """Match unit based on dominant color"""
        try:
            if unit_name not in self.unit_colors:
                return 0.5  # Neutral confidence
            
            # Extract dominant color from unit image
            unit_color = self._extract_dominant_color(unit_image)
            expected_color = self.unit_colors[unit_name]
            
            # Calculate color distance
            color_distance = np.sqrt(sum((a - b) ** 2 for a, b in zip(unit_color, expected_color)))
            
            # Convert to confidence (max distance ~441 for RGB)
            confidence = max(0.0, 1.0 - (color_distance / 441.0))
            
            return confidence
            
        except Exception as e:
            self.logger.debug(f"Color matching error: {e}")
            return 0.5
    
    def _recognize_rank(self, unit_image, unit_name: str) -> int:
        """Recognize unit rank using ML model"""
        try:
            if self.rank_model is None:
                return 1  # Default rank
            
            # Extract features for rank recognition
            features = self._extract_rank_features(unit_image)
            
            if features is None:
                return 1
            
            # Scale features if scaler is available
            if self.rank_scaler is not None:
                features = self.rank_scaler.transform([features])
            else:
                features = [features]
            
            # Predict rank
            try:
                rank_prediction = self.rank_model.predict(features)[0]
                confidence = np.max(self.rank_model.predict_proba(features)[0])
                
                if confidence > self.rank_confidence_threshold:
                    return int(rank_prediction)
                else:
                    return 1  # Default to rank 1 if low confidence
                    
            except Exception as e:
                self.logger.debug(f"Rank prediction error: {e}")
                return 1
                
        except Exception as e:
            self.logger.debug(f"Rank recognition error: {e}")
            return 1
    
    def _extract_rank_features(self, unit_image) -> Optional[List[float]]:
        """Extract features for rank recognition"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(unit_image, cv2.COLOR_BGR2GRAY)
            
            features = []
            
            # Basic image statistics
            features.extend([
                np.mean(gray),
                np.std(gray),
                np.median(gray),
                np.min(gray),
                np.max(gray)
            ])
            
            # Edge density (higher rank units might have more detail)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
            features.append(edge_density)
            
            # Color statistics
            for channel in range(3):
                channel_data = unit_image[:, :, channel]
                features.extend([
                    np.mean(channel_data),
                    np.std(channel_data)
                ])
            
            # Texture features (simplified)
            # In a full implementation, you might use LBP or other texture descriptors
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            features.append(laplacian_var)
            
            return features
            
        except Exception as e:
            self.logger.debug(f"Feature extraction error: {e}")
            return None
    
    def recognize_grid_units(self, grid_crops: List[np.ndarray], 
                            positions: List[Tuple[int, int]]) -> pd.DataFrame:
        """Recognize units in entire grid"""
        try:
            results = []
            
            for i, (crop, position) in enumerate(zip(grid_crops, positions)):
                recognition_result = self.recognize_unit(crop, position)
                
                result_row = {
                    'position_index': i,
                    'grid_x': position[0],
                    'grid_y': position[1],
                    'unit': recognition_result['unit_name'],
                    'confidence': recognition_result['confidence'],
                    'rank': recognition_result['rank']
                }
                
                results.append(result_row)
            
            grid_df = pd.DataFrame(results)
            
            self.logger.debug(f"Recognized {len(grid_df)} grid positions")
            return grid_df
            
        except Exception as e:
            self.logger.error(f"Grid recognition error: {e}")
            return pd.DataFrame()
    
    def get_unit_statistics(self, grid_df: pd.DataFrame) -> Dict[str, Any]:
        """Get statistics about recognized units"""
        try:
            if grid_df.empty:
                return {"total_units": 0, "unique_units": 0, "average_confidence": 0.0}
            
            # Filter out empty positions
            units_df = grid_df[grid_df['unit'] != 'empty']
            
            stats = {
                'total_units': len(units_df),
                'unique_units': len(units_df['unit'].unique()),
                'average_confidence': float(units_df['confidence'].mean()) if len(units_df) > 0 else 0.0,
                'unit_distribution': units_df['unit'].value_counts().to_dict(),
                'rank_distribution': units_df['rank'].value_counts().to_dict(),
                'low_confidence_count': len(units_df[units_df['confidence'] < self.match_threshold])
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Statistics calculation error: {e}")
            return {"error": str(e)}
    
    def validate_recognition(self, grid_df: pd.DataFrame) -> Dict[str, Any]:
        """Validate recognition results and suggest improvements"""
        try:
            validation = {
                'valid': True,
                'warnings': [],
                'suggestions': []
            }
            
            if grid_df.empty:
                validation['valid'] = False
                validation['warnings'].append("No units recognized")
                return validation
            
            # Check for low confidence recognitions
            low_conf_units = grid_df[grid_df['confidence'] < self.match_threshold]
            if len(low_conf_units) > 0:
                validation['warnings'].append(f"{len(low_conf_units)} units with low confidence")
                validation['suggestions'].append("Consider adjusting recognition thresholds")
            
            # Check for suspicious patterns
            unit_counts = grid_df['unit'].value_counts()
            if 'unknown' in unit_counts and unit_counts['unknown'] > 5:
                validation['warnings'].append("Many unknown units detected")
                validation['suggestions'].append("Check unit templates or image quality")
            
            # Check grid utilization
            non_empty = len(grid_df[grid_df['unit'] != 'empty'])
            utilization = non_empty / len(grid_df) if len(grid_df) > 0 else 0
            
            if utilization < 0.3:
                validation['suggestions'].append("Low grid utilization - check if in battle")
            elif utilization > 0.9:
                validation['suggestions'].append("High grid utilization - optimal for merging")
            
            return validation
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return {'valid': False, 'error': str(e)}
    
    def update_unit_template(self, unit_name: str, new_image: np.ndarray):
        """Update unit template with new image"""
        try:
            self.unit_templates[unit_name] = new_image.copy()
            self.unit_colors[unit_name] = self._extract_dominant_color(new_image)
            
            # Add to unit names if new
            if unit_name not in self.unit_names:
                self.unit_names.append(unit_name)
            
            self.logger.info(f"Updated template for {unit_name}")
            
        except Exception as e:
            self.logger.error(f"Template update error: {e}")
    
    def get_available_units(self) -> List[str]:
        """Get list of available unit names"""
        return self.unit_names.copy()
    
    def set_recognition_threshold(self, threshold: float):
        """Set recognition confidence threshold"""
        self.match_threshold = max(0.0, min(1.0, threshold))
        self.logger.info(f"Recognition threshold set to {self.match_threshold}")
    
    def get_recognition_info(self) -> Dict[str, Any]:
        """Get information about recognition system"""
        return {
            'total_templates': len(self.unit_templates),
            'available_units': len(self.unit_names),
            'match_threshold': self.match_threshold,
            'rank_model_available': self.rank_model is not None,
            'rank_confidence_threshold': self.rank_confidence_threshold
        }
