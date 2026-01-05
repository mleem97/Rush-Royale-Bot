"""
Tests for ML modules.
"""
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import json


class TestModelRegistry:
    """Tests for ModelRegistry class."""
    
    def test_init_creates_directory(self, tmp_path):
        """Test that init creates models directory."""
        from Src.ml.model_registry import ModelRegistry
        
        models_dir = tmp_path / "models"
        registry = ModelRegistry(models_dir)
        
        assert models_dir.exists()
        assert (models_dir / "registry.json").exists() or registry._registry == {}
    
    def test_save_and_load_model(self, tmp_path):
        """Test saving and loading a model."""
        from Src.ml.model_registry import ModelRegistry
        from sklearn.linear_model import LogisticRegression
        
        registry = ModelRegistry(tmp_path / "models")
        
        # Create and save a simple model
        model = LogisticRegression()
        model.fit([[0], [1]], [0, 1])  # Minimal training
        
        version = registry.save_model(
            model=model,
            name="test_model",
            metrics={"accuracy": 0.95}
        )
        
        assert version == "v1"
        
        # Load the model
        loaded = registry.load_model("test_model")
        assert loaded is not None
        
        # Verify prediction works
        pred = loaded.predict([[0.5]])
        assert len(pred) == 1
    
    def test_version_increment(self, tmp_path):
        """Test that versions increment correctly."""
        from Src.ml.model_registry import ModelRegistry
        from sklearn.linear_model import LogisticRegression
        
        registry = ModelRegistry(tmp_path / "models")
        model = LogisticRegression()
        model.fit([[0], [1]], [0, 1])
        
        v1 = registry.save_model(model, "test", metrics={})
        v2 = registry.save_model(model, "test", metrics={})
        v3 = registry.save_model(model, "test", metrics={})
        
        assert v1 == "v1"
        assert v2 == "v2"
        assert v3 == "v3"
    
    def test_list_models(self, tmp_path):
        """Test listing all models."""
        from Src.ml.model_registry import ModelRegistry
        from sklearn.linear_model import LogisticRegression
        
        registry = ModelRegistry(tmp_path / "models")
        model = LogisticRegression()
        model.fit([[0], [1]], [0, 1])
        
        registry.save_model(model, "model_a", metrics={})
        registry.save_model(model, "model_b", metrics={})
        registry.save_model(model, "model_a", metrics={})
        
        models = registry.list_models()
        
        assert "model_a" in models
        assert "model_b" in models
        assert len(models["model_a"]) == 2
        assert len(models["model_b"]) == 1
    
    def test_get_metadata(self, tmp_path):
        """Test getting model metadata."""
        from Src.ml.model_registry import ModelRegistry
        from sklearn.linear_model import LogisticRegression
        
        registry = ModelRegistry(tmp_path / "models")
        model = LogisticRegression()
        model.fit([[0], [1]], [0, 1])
        
        registry.save_model(
            model, 
            "test",
            metrics={"accuracy": 0.95, "f1_score": 0.92},
            training_samples=1000
        )
        
        metadata = registry.get_metadata("test")
        
        assert metadata is not None
        assert metadata.accuracy == 0.95
        assert metadata.f1_score == 0.92
        assert metadata.training_samples == 1000


class TestModelMetadata:
    """Tests for ModelMetadata dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        from Src.ml.model_registry import ModelMetadata
        
        meta = ModelMetadata(
            name="test",
            version="v1",
            model_type="sklearn",
            accuracy=0.95
        )
        
        d = meta.to_dict()
        
        assert d["name"] == "test"
        assert d["version"] == "v1"
        assert d["accuracy"] == 0.95
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        from Src.ml.model_registry import ModelMetadata
        
        data = {
            "name": "test",
            "version": "v2",
            "model_type": "sklearn",
            "accuracy": 0.9,
            "created_at": "2026-01-02T12:00:00",
            "training_samples": 500,
            "training_duration_seconds": 10.5,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "extra_metrics": {},
            "data_hash": "",
            "model_path": ""
        }
        
        meta = ModelMetadata.from_dict(data)
        
        assert meta.name == "test"
        assert meta.version == "v2"
        assert meta.accuracy == 0.9


class TestRankClassifier:
    """Tests for RankClassifier class."""
    
    def test_extract_features(self):
        """Test feature extraction from image."""
        from Src.ml.rank_classifier import RankClassifier
        
        classifier = RankClassifier()
        
        # Create dummy grayscale image
        image = np.random.randint(0, 255, (120, 120), dtype=np.uint8)
        
        features = classifier.extract_features(image)
        
        assert features.shape == (120 * 120,)
        assert features.min() >= 0
        assert features.max() <= 1
    
    def test_predict_without_model_raises(self):
        """Test that predict raises without loaded model."""
        from Src.ml.rank_classifier import RankClassifier
        
        classifier = RankClassifier()
        image = np.random.randint(0, 255, (120, 120), dtype=np.uint8)
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            classifier.predict(image)
    
    def test_predict_with_mock_model(self):
        """Test prediction with mocked model."""
        from Src.ml.rank_classifier import RankClassifier
        
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = np.array([[0.1, 0.7, 0.1, 0.05, 0.025, 0.015, 0.0025, 0.0025]])
        
        classifier = RankClassifier(model=mock_model)
        image = np.random.randint(0, 255, (120, 120), dtype=np.uint8)
        
        rank, confidence = classifier.predict(image)
        
        assert rank == 1
        assert confidence == pytest.approx(0.7, rel=0.01)


class TestUnitDetector:
    """Tests for UnitDetector class."""
    
    def test_extract_color_features(self):
        """Test color feature extraction."""
        from Src.ml.unit_detector import UnitDetector
        
        detector = UnitDetector()
        
        # Create dummy BGR image
        image = np.random.randint(0, 255, (120, 120, 3), dtype=np.uint8)
        
        colors = detector.extract_color_features(image, crop=False)
        
        assert colors.shape == (5, 3)
    
    def test_extract_histogram(self):
        """Test histogram extraction."""
        from Src.ml.unit_detector import UnitDetector
        
        detector = UnitDetector()
        
        # Create dummy BGR image
        image = np.random.randint(0, 255, (120, 120, 3), dtype=np.uint8)
        
        hist = detector.extract_histogram(image, crop=False)
        
        assert hist.shape == (32 * 32,)
    
    def test_predict_without_references_raises(self):
        """Test that predict raises without loaded references."""
        from Src.ml.unit_detector import UnitDetector
        
        detector = UnitDetector()
        image = np.random.randint(0, 255, (120, 120, 3), dtype=np.uint8)
        
        with pytest.raises(RuntimeError, match="No references loaded"):
            detector.predict(image)
    
    def test_is_empty_with_rank_zero(self):
        """Test empty detection with rank 0."""
        from Src.ml.unit_detector import UnitDetector
        
        detector = UnitDetector()
        image = np.zeros((120, 120, 3), dtype=np.uint8)
        
        # Rank 0 should indicate empty
        assert detector.is_empty(image, rank=0) is True


class TestDataHash:
    """Tests for data hashing utility."""
    
    def test_compute_hash_numpy(self):
        """Test hash computation for numpy arrays."""
        from Src.ml.model_registry import compute_data_hash
        
        data1 = np.array([1, 2, 3, 4, 5])
        data2 = np.array([1, 2, 3, 4, 5])
        data3 = np.array([1, 2, 3, 4, 6])
        
        hash1 = compute_data_hash(data1)
        hash2 = compute_data_hash(data2)
        hash3 = compute_data_hash(data3)
        
        assert hash1 == hash2  # Same data = same hash
        assert hash1 != hash3  # Different data = different hash
        assert len(hash1) == 16  # 16 characters
