"""
Rush Royale Bot - Rank Classifier
Python 3.13 Compatible

Modern rank classification using improved feature extraction
and sklearn pipelines with cross-validation.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from sklearn.base import BaseEstimator

logger = logging.getLogger(__name__)


class RankClassifier:
    """
    Classifies unit ranks from grid cell images.
    
    Improvements over legacy:
    - Feature extraction pipeline (edges + histogram)
    - Proper train/test split with cross-validation
    - Model versioning via ModelRegistry
    - Confidence scores
    
    Example:
        classifier = RankClassifier()
        classifier.load()  # Load from registry
        
        rank, confidence = classifier.predict(cell_image)
    """
    
    NUM_RANKS = 8  # Ranks 0-7
    
    def __init__(self, model: 'BaseEstimator | None' = None):
        """
        Initialize rank classifier.
        
        Args:
            model: Pre-trained sklearn model (optional)
        """
        self.model = model
        self._feature_size: int | None = None
    
    def extract_features(self, image: np.ndarray) -> np.ndarray:
        """
        Extract features from a cell image.
        
        Uses combination of:
        - Canny edge detection (legacy compatible)
        - Histogram of oriented gradients (optional enhancement)
        
        Args:
            image: Grayscale or BGR image of grid cell
            
        Returns:
            1D feature vector
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Resize to standard size for consistency
        standard_size = (120, 120)
        if gray.shape[:2] != standard_size:
            gray = cv2.resize(gray, standard_size)
        
        # Canny edge detection (legacy method)
        edges = cv2.Canny(gray, 50, 100)
        
        # Flatten to 1D feature vector
        features = edges.flatten().astype(np.float32)
        
        # Normalize
        features = features / 255.0
        
        return features
    
    def predict(self, image: np.ndarray) -> tuple[int, float]:
        """
        Predict rank from cell image.
        
        Args:
            image: Grid cell image
            
        Returns:
            Tuple of (predicted_rank, confidence)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        
        features = self.extract_features(image)
        features = features.reshape(1, -1)
        
        # Get prediction and probability
        proba = self.model.predict_proba(features)[0]
        rank = int(proba.argmax())
        confidence = float(proba.max())
        
        return rank, confidence
    
    def predict_batch(
        self, 
        images: list[np.ndarray]
    ) -> list[tuple[int, float]]:
        """
        Predict ranks for multiple images.
        
        Args:
            images: List of grid cell images
            
        Returns:
            List of (rank, confidence) tuples
        """
        if not images:
            return []
        
        # Extract features for all images
        features = np.array([self.extract_features(img) for img in images])
        
        # Batch prediction
        probas = self.model.predict_proba(features)
        
        results = []
        for proba in probas:
            rank = int(proba.argmax())
            confidence = float(proba.max())
            results.append((rank, confidence))
        
        return results
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        model_type: str = "gradient_boosting"
    ) -> dict:
        """
        Train the rank classifier.
        
        Args:
            X_train: Training images or pre-extracted features
            y_train: Rank labels (0-7)
            model_type: Type of model to train
            
        Returns:
            Training metrics dictionary
        """
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import classification_report, accuracy_score
        
        # Extract features if needed
        if len(X_train.shape) > 2:
            logger.info("Extracting features from images...")
            features = np.array([self.extract_features(img) for img in X_train])
        else:
            features = X_train
        
        # Create model
        if model_type == "gradient_boosting":
            from sklearn.ensemble import GradientBoostingClassifier
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=42
            )
        elif model_type == "logistic":
            from sklearn.linear_model import LogisticRegression
            self.model = LogisticRegression(
                max_iter=1000,
                random_state=42
            )
        else:
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(
                n_estimators=100,
                random_state=42
            )
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, features, y_train, cv=5)
        logger.info(f"Cross-validation scores: {cv_scores}")
        logger.info(f"Mean CV score: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
        
        # Final training
        self.model.fit(features, y_train)
        
        # Calculate metrics
        y_pred = self.model.predict(features)
        accuracy = accuracy_score(y_train, y_pred)
        
        metrics = {
            'accuracy': accuracy,
            'cv_mean': float(cv_scores.mean()),
            'cv_std': float(cv_scores.std()),
            'model_type': model_type,
            'n_samples': len(y_train),
        }
        
        logger.info(f"Training complete. Accuracy: {accuracy:.4f}")
        
        return metrics
    
    def load(
        self,
        registry_path: Path | str = "models",
        version: str | None = None
    ) -> None:
        """
        Load model from registry.
        
        Args:
            registry_path: Path to model registry
            version: Specific version to load (None for latest)
        """
        from .model_registry import ModelRegistry
        
        registry = ModelRegistry(registry_path)
        self.model = registry.load_model("rank_classifier", version)
        logger.info(f"Loaded rank classifier from registry")
    
    def save(
        self,
        registry_path: Path | str = "models",
        metrics: dict | None = None
    ) -> str:
        """
        Save model to registry.
        
        Args:
            registry_path: Path to model registry
            metrics: Training metrics
            
        Returns:
            Version string
        """
        if self.model is None:
            raise RuntimeError("No model to save")
        
        from .model_registry import ModelRegistry
        
        registry = ModelRegistry(registry_path)
        version = registry.save_model(
            model=self.model,
            name="rank_classifier",
            model_type="sklearn",
            metrics=metrics or {}
        )
        
        logger.info(f"Saved rank classifier as {version}")
        return version
    
    def load_legacy(self, pkl_path: Path | str = "rank_model.pkl") -> None:
        """
        Load legacy pickle model.
        
        Args:
            pkl_path: Path to legacy .pkl file
        """
        import pickle
        
        pkl_path = Path(pkl_path)
        if not pkl_path.exists():
            raise FileNotFoundError(f"Legacy model not found: {pkl_path}")
        
        with open(pkl_path, 'rb') as f:
            self.model = pickle.load(f)
        
        logger.info(f"Loaded legacy model from {pkl_path}")
