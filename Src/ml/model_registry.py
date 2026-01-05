"""
Rush Royale Bot - Model Registry
Python 3.13 Compatible

Centralized model management with versioning, metrics, and persistence.
Replaces raw pickle files with structured model storage.
"""
from __future__ import annotations

import json
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Try joblib first (better for sklearn), fallback to pickle
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    import pickle as joblib
    JOBLIB_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """Metadata for a trained model."""
    
    name: str
    version: str
    model_type: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Training info
    training_samples: int = 0
    training_duration_seconds: float = 0.0
    
    # Performance metrics
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    
    # Additional metrics (flexible)
    extra_metrics: dict = field(default_factory=dict)
    
    # Data fingerprint for reproducibility
    data_hash: str = ""
    
    # File paths
    model_path: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ModelMetadata':
        """Create from dictionary."""
        return cls(**data)


class ModelRegistry:
    """
    Centralized model management with versioning.
    
    Features:
    - Automatic version numbering
    - Metrics tracking
    - Model comparison
    - Easy loading of latest or specific versions
    
    Example:
        registry = ModelRegistry()
        
        # Save a new model
        version = registry.save_model(
            model=trained_model,
            name="rank_classifier",
            metrics={"accuracy": 0.95}
        )
        
        # Load latest model
        model = registry.load_model("rank_classifier")
        
        # Load specific version
        model = registry.load_model("rank_classifier", version="v2")
    """
    
    def __init__(self, models_dir: Path | str = "models"):
        """
        Initialize model registry.
        
        Args:
            models_dir: Directory to store models and registry
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry_file = self.models_dir / "registry.json"
        self._registry: dict[str, list[ModelMetadata]] = {}
        
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load registry from disk."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                
                self._registry = {
                    name: [ModelMetadata.from_dict(m) for m in versions]
                    for name, versions in data.items()
                }
                logger.debug(f"Loaded registry with {len(self._registry)} models")
            except Exception as e:
                logger.warning(f"Failed to load registry: {e}")
                self._registry = {}
        else:
            self._registry = {}
    
    def _save_registry(self) -> None:
        """Save registry to disk."""
        data = {
            name: [m.to_dict() for m in versions]
            for name, versions in self._registry.items()
        }
        
        with open(self.registry_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _get_next_version(self, name: str) -> str:
        """Get next version number for a model."""
        if name not in self._registry or not self._registry[name]:
            return "v1"
        
        versions = self._registry[name]
        latest = max(int(v.version[1:]) for v in versions)
        return f"v{latest + 1}"
    
    def save_model(
        self,
        model: Any,
        name: str,
        model_type: str = "sklearn",
        metrics: dict | None = None,
        training_samples: int = 0,
        training_duration: float = 0.0,
        data_hash: str = ""
    ) -> str:
        """
        Save a model with automatic versioning.
        
        Args:
            model: The trained model object
            name: Model name (e.g., "rank_classifier")
            model_type: Type of model (sklearn, pytorch, onnx)
            metrics: Performance metrics dictionary
            training_samples: Number of training samples used
            training_duration: Training time in seconds
            data_hash: Hash of training data for reproducibility
            
        Returns:
            Version string (e.g., "v1")
        """
        version = self._get_next_version(name)
        
        # Create model directory
        model_subdir = self.models_dir / name
        model_subdir.mkdir(exist_ok=True)
        
        # Determine file extension
        ext = ".joblib" if JOBLIB_AVAILABLE else ".pkl"
        model_path = model_subdir / f"{name}_{version}{ext}"
        
        # Save model
        joblib.dump(model, model_path)
        logger.info(f"Saved model to {model_path}")
        
        # Create metadata
        metrics = metrics or {}
        metadata = ModelMetadata(
            name=name,
            version=version,
            model_type=model_type,
            training_samples=training_samples,
            training_duration_seconds=training_duration,
            accuracy=metrics.get('accuracy', 0.0),
            precision=metrics.get('precision', 0.0),
            recall=metrics.get('recall', 0.0),
            f1_score=metrics.get('f1_score', 0.0),
            extra_metrics={k: v for k, v in metrics.items() 
                          if k not in ['accuracy', 'precision', 'recall', 'f1_score']},
            data_hash=data_hash,
            model_path=str(model_path)
        )
        
        # Update registry
        if name not in self._registry:
            self._registry[name] = []
        self._registry[name].append(metadata)
        
        self._save_registry()
        
        return version
    
    def load_model(
        self,
        name: str,
        version: str | None = None
    ) -> Any:
        """
        Load a model by name and optional version.
        
        Args:
            name: Model name
            version: Specific version (e.g., "v2") or None for latest
            
        Returns:
            The loaded model object
            
        Raises:
            FileNotFoundError: If model not found
        """
        if name not in self._registry or not self._registry[name]:
            raise FileNotFoundError(f"No model found with name: {name}")
        
        versions = self._registry[name]
        
        if version:
            # Find specific version
            metadata = next((m for m in versions if m.version == version), None)
            if not metadata:
                raise FileNotFoundError(f"Version {version} not found for {name}")
        else:
            # Get latest version
            metadata = max(versions, key=lambda m: int(m.version[1:]))
        
        model_path = Path(metadata.model_path)
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        model = joblib.load(model_path)
        logger.info(f"Loaded {name} {metadata.version}")
        
        return model
    
    def get_metadata(
        self,
        name: str,
        version: str | None = None
    ) -> ModelMetadata | None:
        """Get metadata for a model."""
        if name not in self._registry:
            return None
        
        versions = self._registry[name]
        
        if version:
            return next((m for m in versions if m.version == version), None)
        else:
            return max(versions, key=lambda m: int(m.version[1:])) if versions else None
    
    def list_models(self) -> dict[str, list[str]]:
        """List all models and their versions."""
        return {
            name: [m.version for m in versions]
            for name, versions in self._registry.items()
        }
    
    def compare_versions(
        self,
        name: str,
        metrics: list[str] | None = None
    ) -> list[dict]:
        """
        Compare all versions of a model.
        
        Args:
            name: Model name
            metrics: List of metric names to compare
            
        Returns:
            List of version comparison dictionaries
        """
        if name not in self._registry:
            return []
        
        metrics = metrics or ['accuracy', 'f1_score']
        
        comparisons = []
        for m in self._registry[name]:
            comp = {
                'version': m.version,
                'created_at': m.created_at,
                'training_samples': m.training_samples,
            }
            for metric in metrics:
                comp[metric] = getattr(m, metric, m.extra_metrics.get(metric, 0.0))
            comparisons.append(comp)
        
        return sorted(comparisons, key=lambda x: int(x['version'][1:]))
    
    def migrate_legacy_model(
        self,
        legacy_path: Path | str,
        name: str,
        model_type: str = "sklearn"
    ) -> str:
        """
        Migrate a legacy pickle model to the registry.
        
        Args:
            legacy_path: Path to legacy .pkl file
            name: Name for the model in registry
            model_type: Type of model
            
        Returns:
            Version string
        """
        legacy_path = Path(legacy_path)
        
        if not legacy_path.exists():
            raise FileNotFoundError(f"Legacy model not found: {legacy_path}")
        
        # Load with pickle (legacy format)
        import pickle
        with open(legacy_path, 'rb') as f:
            model = pickle.load(f)
        
        # Save to registry
        version = self.save_model(
            model=model,
            name=name,
            model_type=model_type,
            metrics={'note': 'Migrated from legacy pickle'}
        )
        
        logger.info(f"Migrated {legacy_path} to {name} {version}")
        return version


def compute_data_hash(data: Any) -> str:
    """
    Compute hash of training data for reproducibility.
    
    Args:
        data: Training data (numpy array, pandas DataFrame, etc.)
        
    Returns:
        SHA256 hash string
    """
    import numpy as np
    
    if hasattr(data, 'tobytes'):
        # Numpy array
        data_bytes = data.tobytes()
    elif hasattr(data, 'to_numpy'):
        # Pandas DataFrame
        data_bytes = data.to_numpy().tobytes()
    else:
        # Fallback: string representation
        data_bytes = str(data).encode()
    
    return hashlib.sha256(data_bytes).hexdigest()[:16]
