"""Rush Bot ML Training Module.

Provides training utilities for:
- Rank recognition model (T018)
- Unit detection model (T019, T023)

Training pipeline with data augmentation and cross-validation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import train_test_split

# Project paths
REPO_ROOT = Path(__file__).resolve().parents[4]
CV_IMAGES_DIR = REPO_ROOT / "cv-images"
ML_DIR = REPO_ROOT / "machine_learning"
MODELS_DIR = REPO_ROOT / "models"
RANK_MODEL_PATH = REPO_ROOT / "rank_model.pkl"

# Standard icon size for consistent training
STANDARD_ICON_SIZE = (120, 120)  # T019: Unified size for rank and unit detection


@dataclass
class TrainingConfig:
    """Configuration for model training.
    
    Attributes:
        icon_size: Target size for all icons (width, height).
        use_augmentation: Whether to apply data augmentation.
        augmentation_factor: Number of augmented samples per original.
        test_split: Fraction of data for validation.
        random_state: Random seed for reproducibility.
        max_iter: Maximum iterations for LogisticRegression.
    """
    
    icon_size: tuple[int, int] = STANDARD_ICON_SIZE
    use_augmentation: bool = True
    augmentation_factor: int = 5
    test_split: float = 0.2
    random_state: int = 42
    max_iter: int = 500


@dataclass
class TrainingResult:
    """Result of model training.
    
    Attributes:
        model: Trained model object.
        classes: List of class labels.
        accuracy: Training accuracy.
        val_accuracy: Validation accuracy (if applicable).
        cv_scores: Cross-validation scores.
        report: Classification report dict.
        confusion: Confusion matrix.
    """
    
    model: Any
    classes: list[Any]
    accuracy: float
    val_accuracy: float | None = None
    cv_scores: list[float] = field(default_factory=list)
    report: dict[str, Any] = field(default_factory=dict)
    confusion: NDArray[np.int64] | None = None


def augment_image(
    img: NDArray[Any],
    n_augmentations: int = 5,
) -> list[NDArray[Any]]:
    """Apply data augmentation to an image.
    
    Creates variations of the input image to increase training data
    and improve model robustness.
    
    Args:
        img: Input image (BGR or grayscale).
        n_augmentations: Number of augmented versions to create.
        
    Returns:
        List of augmented images including the original.
    """
    augmented: list[NDArray[Any]] = [img.copy()]
    
    for i in range(n_augmentations):
        aug = img.copy()
        
        # Random brightness adjustment
        if i % 5 == 0:
            factor = np.random.uniform(0.7, 1.3)
            aug = np.clip(aug * factor, 0, 255).astype(np.uint8)
        
        # Random rotation (-15 to 15 degrees)
        elif i % 5 == 1:
            angle = np.random.uniform(-15, 15)
            h, w = aug.shape[:2]
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            aug = cv2.warpAffine(aug, M, (w, h), borderValue=0)
        
        # Random horizontal flip
        elif i % 5 == 2:
            if np.random.random() > 0.5:
                aug = cv2.flip(aug, 1)
        
        # Random Gaussian noise
        elif i % 5 == 3:
            noise = np.random.normal(0, 10, aug.shape).astype(np.int16)
            aug = np.clip(aug.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        # Random scale (zoom)
        else:
            scale = np.random.uniform(0.9, 1.1)
            h, w = aug.shape[:2]
            new_h, new_w = int(h * scale), int(w * scale)
            aug = cv2.resize(aug, (new_w, new_h))
            
            # Crop or pad to original size
            if scale > 1:
                # Crop center
                start_h = (new_h - h) // 2
                start_w = (new_w - w) // 2
                aug = aug[start_h:start_h + h, start_w:start_w + w]
            else:
                # Pad with zeros
                pad_h = (h - new_h) // 2
                pad_w = (w - new_w) // 2
                padded = np.zeros_like(img)
                padded[pad_h:pad_h + new_h, pad_w:pad_w + new_w] = aug
                aug = padded
        
        augmented.append(aug)
    
    return augmented


def load_training_dataset(
    folder: Path | str,
    icon_size: tuple[int, int] = STANDARD_ICON_SIZE,
    use_edges: bool = True,
) -> tuple[NDArray[np.float64], NDArray[np.int64], list[str]]:
    """Load labeled training images from a directory.
    
    Supports multiple layouts:
    - Flat: files like "<label>_input_123.png"
    - Hierarchical: subfolders named by label containing PNGs
    
    Args:
        folder: Path to the dataset directory.
        icon_size: Target size for resizing images.
        use_edges: Whether to convert images to Canny edges.
        
    Returns:
        Tuple of (X, y, label_names):
        - X: Feature array of shape (n_samples, n_features)
        - y: Label array of shape (n_samples,)
        - label_names: List mapping indices to label names
        
    Raises:
        RuntimeError: If no training images found.
    """
    folder_path = Path(folder)
    X_train: list[NDArray] = []
    y_train: list[int] = []
    label_map: dict[str, int] = {}
    
    def process_image(img_path: Path, label_str: str) -> None:
        """Process a single image and add to training data."""
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return
        
        # Resize to standard size
        img = cv2.resize(img, icon_size)
        
        # Apply edge detection if requested
        if use_edges:
            img = cv2.Canny(img, 50, 100)
        
        # Assign label index
        if label_str not in label_map:
            label_map[label_str] = len(label_map)
        
        X_train.append(img)
        y_train.append(label_map[label_str])
    
    # Layout A: flat files like "<rank>_input_123.png"
    for p in folder_path.glob("*_input_*.png"):
        label = p.name.split("_input", 1)[0]
        process_image(p, label)
    
    # Layout B: hierarchical subfolders
    for sub in folder_path.iterdir():
        if not sub.is_dir():
            continue
        label = sub.name
        for p in sub.glob("*.png"):
            process_image(p, label)
    
    if not X_train:
        raise RuntimeError(f"No training images found in: {folder_path}")
    
    # Convert to arrays
    X = np.array(X_train)
    X = X.reshape(X.shape[0], -1).astype(np.float64)
    y = np.array(y_train, dtype=np.int64)
    
    # Create label names list
    label_names = [""] * len(label_map)
    for name, idx in label_map.items():
        label_names[idx] = name
    
    return X, y, label_names


class RankModelTrainer:
    """Trainer for rank recognition model (T018).
    
    Trains a LogisticRegression model to classify unit ranks (0-7+)
    from edge-detected cell images.
    
    Attributes:
        config: Training configuration.
        model: Trained LogisticRegression model (after train()).
    """
    
    def __init__(self, config: TrainingConfig | None = None) -> None:
        """Initialize the trainer.
        
        Args:
            config: Training configuration. Uses defaults if None.
        """
        self.config = config or TrainingConfig()
        self.model: LogisticRegression | None = None
        self._result: TrainingResult | None = None
    
    def train(
        self,
        dataset_dir: Path | str | None = None,
    ) -> TrainingResult:
        """Train the rank model from dataset.
        
        Args:
            dataset_dir: Directory containing labeled training images.
                         Defaults to machine_learning/inputs.
                         
        Returns:
            TrainingResult with model and metrics.
        """
        dataset_dir = Path(dataset_dir) if dataset_dir else ML_DIR / "inputs"
        
        # Load dataset
        X, y, label_names = load_training_dataset(
            dataset_dir,
            icon_size=self.config.icon_size,
            use_edges=True,
        )
        
        print(f"Loaded {len(X)} samples with {len(set(y))} classes")
        print(f"Classes: {label_names}")
        
        # Split for validation
        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=self.config.test_split,
            random_state=self.config.random_state,
            stratify=y,
        )
        
        # Train model
        self.model = LogisticRegression(
            max_iter=self.config.max_iter,
            random_state=self.config.random_state,
        )
        self.model.fit(X_train, y_train)
        
        # Calculate metrics
        train_acc = self.model.score(X_train, y_train)
        val_acc = self.model.score(X_val, y_val)
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y, cv=5).tolist()
        
        # Classification report
        y_pred = self.model.predict(X_val)
        report = classification_report(y_val, y_pred, output_dict=True)
        confusion = confusion_matrix(y_val, y_pred)
        
        self._result = TrainingResult(
            model=self.model,
            classes=list(self.model.classes_),
            accuracy=train_acc,
            val_accuracy=val_acc,
            cv_scores=cv_scores,
            report=report,
            confusion=confusion,
        )
        
        print(f"Training accuracy: {train_acc:.4f}")
        print(f"Validation accuracy: {val_acc:.4f}")
        print(f"CV scores: {np.mean(cv_scores):.4f} (+/- {np.std(cv_scores) * 2:.4f})")
        
        return self._result
    
    def save(self, path: Path | str | None = None) -> Path:
        """Save trained model to disk.
        
        Args:
            path: Output path. Defaults to rank_model.pkl.
            
        Returns:
            Path where model was saved.
            
        Raises:
            RuntimeError: If model hasn't been trained.
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")
        
        import pickle
        
        out_path = Path(path) if path else RANK_MODEL_PATH
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        with out_path.open("wb") as f:
            pickle.dump(self.model, f)
        
        print(f"Saved model to: {out_path}")
        return out_path


class UnitModelTrainer:
    """Trainer for unit detection model (T019, T023).
    
    Trains a model to classify unit types from 120x120 cell images.
    Uses template images from cv-images/all_units as base training data.
    
    Attributes:
        config: Training configuration.
        model: Trained model (after train()).
        label_map: Mapping from unit names to class indices.
    """
    
    def __init__(self, config: TrainingConfig | None = None) -> None:
        """Initialize the trainer.
        
        Args:
            config: Training configuration. Uses defaults if None.
        """
        self.config = config or TrainingConfig()
        self.model: LogisticRegression | None = None
        self.label_map: dict[str, int] = {}
        self._result: TrainingResult | None = None
    
    def prepare_dataset(
        self,
        units_dir: Path | str | None = None,
        output_dir: Path | str | None = None,
    ) -> int:
        """Prepare training dataset from unit template images.
        
        Imports unit icons from cv-images/all_units, resizes to 120x120,
        and optionally applies augmentation.
        
        Args:
            units_dir: Source directory with unit PNGs.
            output_dir: Output directory for processed images.
            
        Returns:
            Number of samples created.
        """
        units_dir = Path(units_dir) if units_dir else CV_IMAGES_DIR / "all_units"
        output_dir = Path(output_dir) if output_dir else ML_DIR / "unit_inputs"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Unit name aliases (combine variants)
        ALIASES = {
            "twins1": "twins",
            "twins2": "twins",
        }
        
        total_count = 0
        
        for unit_file in units_dir.glob("*.png"):
            unit_name = unit_file.stem
            if unit_name in ("empty", "-"):
                continue
            
            # Apply alias
            unit_name = ALIASES.get(unit_name, unit_name)
            
            # Read and resize
            img = cv2.imread(str(unit_file))
            if img is None:
                continue
            
            img = cv2.resize(img, self.config.icon_size)
            
            # Create output directory for this unit
            unit_dir = output_dir / unit_name
            unit_dir.mkdir(exist_ok=True)
            
            # Save base image
            base_path = unit_dir / f"base_{unit_file.stem}.png"
            cv2.imwrite(str(base_path), img)
            total_count += 1
            
            # Apply augmentation
            if self.config.use_augmentation:
                augmented = augment_image(img, self.config.augmentation_factor)
                for i, aug_img in enumerate(augmented[1:], 1):
                    aug_path = unit_dir / f"aug_{unit_file.stem}_{i:02d}.png"
                    cv2.imwrite(str(aug_path), aug_img)
                    total_count += 1
        
        print(f"Created {total_count} training samples in {output_dir}")
        return total_count
    
    def train(
        self,
        dataset_dir: Path | str | None = None,
    ) -> TrainingResult:
        """Train the unit detection model.
        
        Args:
            dataset_dir: Directory with labeled unit images.
                         Expects subdirectories per unit type.
                         
        Returns:
            TrainingResult with model and metrics.
        """
        dataset_dir = Path(dataset_dir) if dataset_dir else ML_DIR / "unit_inputs"
        
        # Load dataset (use color histograms instead of edges)
        X, y, label_names = load_training_dataset(
            dataset_dir,
            icon_size=self.config.icon_size,
            use_edges=False,  # Use raw pixels for unit detection
        )
        
        print(f"Loaded {len(X)} samples with {len(set(y))} unit types")
        print(f"Units: {label_names}")
        
        # Build label map
        self.label_map = {name: i for i, name in enumerate(label_names)}
        
        # Split for validation
        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=self.config.test_split,
            random_state=self.config.random_state,
            stratify=y,
        )
        
        # Train model
        self.model = LogisticRegression(
            max_iter=self.config.max_iter,
            random_state=self.config.random_state,
            solver="lbfgs",
        )
        self.model.fit(X_train, y_train)
        
        # Calculate metrics
        train_acc = self.model.score(X_train, y_train)
        val_acc = self.model.score(X_val, y_val)
        cv_scores = cross_val_score(self.model, X, y, cv=5).tolist()
        
        y_pred = self.model.predict(X_val)
        report = classification_report(y_val, y_pred, output_dict=True)
        confusion = confusion_matrix(y_val, y_pred)
        
        self._result = TrainingResult(
            model=self.model,
            classes=label_names,
            accuracy=train_acc,
            val_accuracy=val_acc,
            cv_scores=cv_scores,
            report=report,
            confusion=confusion,
        )
        
        print(f"Training accuracy: {train_acc:.4f}")
        print(f"Validation accuracy: {val_acc:.4f}")
        
        return self._result
    
    def save(
        self,
        model_path: Path | str | None = None,
        labels_path: Path | str | None = None,
    ) -> tuple[Path, Path]:
        """Save trained model and label mapping.
        
        Args:
            model_path: Path for model file.
            labels_path: Path for labels JSON.
            
        Returns:
            Tuple of (model_path, labels_path).
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")
        
        import pickle
        
        model_path = Path(model_path) if model_path else MODELS_DIR / "unit_classifier.pkl"
        labels_path = Path(labels_path) if labels_path else MODELS_DIR / "unit_labels.json"
        
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save model
        with model_path.open("wb") as f:
            pickle.dump(self.model, f)
        
        # Save labels
        with labels_path.open("w", encoding="utf-8") as f:
            json.dump({
                "labels": list(self.label_map.keys()),
                "label_to_idx": self.label_map,
            }, f, indent=2)
        
        print(f"Saved model to: {model_path}")
        print(f"Saved labels to: {labels_path}")
        
        return model_path, labels_path
