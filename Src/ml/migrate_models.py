"""
Rush Royale Bot - Model Migration Script
Python 3.13 Compatible

Migrates legacy pickle models to the modern ModelRegistry system.
Addresses Issue #18 (sklearn version mismatch warning).

Usage:
    python -m Src.ml.migrate_models
"""
from __future__ import annotations

import os
import sys
import warnings
import logging
from pathlib import Path
from datetime import datetime

import numpy as np
import cv2

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score, classification_report
import sklearn

try:
    from Src.ml.model_registry import ModelRegistry
except ImportError:
    from model_registry import ModelRegistry


def load_training_data(folder: str = "machine_learning/inputs") -> tuple:
    """
    Load training data from folder.
    
    Args:
        folder: Path to training images
        
    Returns:
        Tuple of (X_train, Y_train)
    """
    folder_path = Path(folder)
    if not folder_path.exists():
        logger.error(f"Training folder not found: {folder}")
        return None, None
    
    X_train = []
    Y_train = []
    
    for file in os.listdir(folder_path):
        if file.endswith(".png"):
            img_path = folder_path / file
            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                X_train.append(img)
                # Extract label from filename (e.g., "0_input_1.png" -> 0)
                label = file.split('_')[0]
                Y_train.append(int(label))
    
    if not X_train:
        logger.error(f"No training images found in {folder}")
        return None, None
    
    X_train = np.array(X_train)
    data_shape = X_train.shape
    X_train = X_train.reshape(data_shape[0], data_shape[1] * data_shape[2])
    Y_train = np.array(Y_train, dtype=int)
    
    logger.info(f"Loaded {len(Y_train)} training samples")
    logger.info(f"Classes: {np.unique(Y_train)}")
    
    return X_train, Y_train


def train_rank_classifier(X_train: np.ndarray, Y_train: np.ndarray) -> tuple:
    """
    Train a new rank classifier with current sklearn version.
    
    Args:
        X_train: Training features
        Y_train: Training labels
        
    Returns:
        Tuple of (model, metrics_dict)
    """
    logger.info(f"Training with sklearn {sklearn.__version__}")
    
    # Train logistic regression
    model = LogisticRegression(
        max_iter=1000,
        solver='lbfgs',
        multi_class='multinomial',
        random_state=42
    )
    
    # Cross-validation
    logger.info("Running 5-fold cross-validation...")
    cv_scores = cross_val_score(model, X_train, Y_train, cv=5, scoring='accuracy')
    logger.info(f"CV Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
    
    # Final training on full dataset
    model.fit(X_train, Y_train)
    
    # Calculate training metrics
    y_pred = model.predict(X_train)
    train_accuracy = accuracy_score(Y_train, y_pred)
    
    logger.info(f"Training Accuracy: {train_accuracy:.4f}")
    logger.info("\nClassification Report:")
    print(classification_report(Y_train, y_pred))
    
    metrics = {
        'accuracy': float(train_accuracy),
        'cv_mean': float(cv_scores.mean()),
        'cv_std': float(cv_scores.std()),
        'sklearn_version': sklearn.__version__,
        'n_classes': len(model.classes_),
        'classes': model.classes_.tolist()
    }
    
    return model, metrics


def migrate_legacy_model():
    """
    Migrate legacy rank_model.pkl to ModelRegistry.
    
    This function:
    1. Loads original training data
    2. Retrains model with current sklearn version
    3. Saves to ModelRegistry with metrics
    4. Optionally backs up the old model
    """
    logger.info("=" * 50)
    logger.info("Rush Royale Bot - Model Migration")
    logger.info("=" * 50)
    logger.info(f"Python: {sys.version}")
    logger.info(f"sklearn: {sklearn.__version__}")
    logger.info("")
    
    # Check for legacy model
    legacy_path = Path("rank_model.pkl")
    if legacy_path.exists():
        logger.info(f"Found legacy model: {legacy_path}")
        # Backup
        backup_path = Path(f"rank_model_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl")
        import shutil
        shutil.copy(legacy_path, backup_path)
        logger.info(f"Backed up to: {backup_path}")
    else:
        logger.warning("No legacy rank_model.pkl found")
    
    # Load training data
    training_folders = [
        "machine_learning/inputs",
        "all_units/unit_rank",
    ]
    
    X_train, Y_train = None, None
    for folder in training_folders:
        X_train, Y_train = load_training_data(folder)
        if X_train is not None:
            break
    
    if X_train is None:
        logger.error("No training data found!")
        logger.info("Please ensure training images are in:")
        for folder in training_folders:
            logger.info(f"  - {folder}/")
        logger.info("\nExpected format: <rank>_input_<id>.png")
        return False
    
    # Train new model
    model, metrics = train_rank_classifier(X_train, Y_train)
    
    # Save to ModelRegistry
    registry = ModelRegistry()
    version = registry.save_model(
        model=model,
        name="rank_classifier",
        model_type="sklearn.LogisticRegression",
        metrics=metrics,
        training_samples=len(Y_train)
    )
    
    logger.info("")
    logger.info("=" * 50)
    logger.info(f"Successfully migrated to ModelRegistry!")
    logger.info(f"Version: {version}")
    logger.info(f"Location: models/rank_classifier/")
    logger.info("=" * 50)
    
    # Verify the new model works
    logger.info("\nVerifying new model...")
    loaded_model = registry.load_model("rank_classifier")
    test_pred = loaded_model.predict(X_train[:5])
    logger.info(f"Test predictions: {test_pred}")
    logger.info("Migration complete!")
    
    return True


def main():
    """Main entry point."""
    try:
        success = migrate_legacy_model()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
