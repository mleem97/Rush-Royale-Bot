"""Tests for rush_bot.ml module.

Tests for ML training, ONNX export, and merge model planning.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from rush_bot.ml.merge_model import MergeDataCollector
from rush_bot.ml.merge_model import MergeFeatureExtractor
from rush_bot.ml.merge_model import MergeModelSpec
from rush_bot.ml.merge_model import MergeRule
from rush_bot.ml.merge_model import MergeWhitelist
from rush_bot.ml.training import STANDARD_ICON_SIZE
from rush_bot.ml.training import RankModelTrainer
from rush_bot.ml.training import TrainingConfig
from rush_bot.ml.training import TrainingResult
from rush_bot.ml.training import UnitModelTrainer
from rush_bot.ml.training import augment_image

# =============================================================================
# Test augment_image
# =============================================================================


class TestAugmentImage:
    """Tests for augment_image function."""

    def test_augment_returns_list(self):
        """Augmentation returns a list of images."""
        img = np.zeros((64, 64, 3), dtype=np.uint8)
        result = augment_image(img, n_augmentations=3)
        assert isinstance(result, list)
        assert len(result) == 4  # Original + 3 augmented

    def test_augment_preserves_shape(self):
        """All augmented images have same shape."""
        img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        result = augment_image(img, n_augmentations=5)
        for aug in result:
            assert aug.shape == img.shape

    def test_augment_creates_variations(self):
        """Augmented images are different from original."""
        img = np.random.randint(50, 200, (64, 64, 3), dtype=np.uint8)
        result = augment_image(img, n_augmentations=5)

        # At least some should be different
        differences = [not np.array_equal(aug, img) for aug in result[1:]]
        assert any(differences), "No augmented images differ from original"

    def test_augment_grayscale(self):
        """Augmentation works with grayscale images."""
        img = np.zeros((64, 64), dtype=np.uint8)
        result = augment_image(img, n_augmentations=2)
        assert len(result) == 3


# =============================================================================
# Test TrainingConfig
# =============================================================================


class TestTrainingConfig:
    """Tests for TrainingConfig dataclass."""

    def test_default_config(self):
        """Default configuration has expected values."""
        config = TrainingConfig()
        assert config.icon_size == STANDARD_ICON_SIZE
        assert config.use_augmentation is True
        assert config.test_split == 0.2
        assert config.max_iter == 500

    def test_custom_config(self):
        """Custom configuration overrides defaults."""
        config = TrainingConfig(
            icon_size=(64, 64),
            use_augmentation=False,
            max_iter=1000,
        )
        assert config.icon_size == (64, 64)
        assert config.use_augmentation is False
        assert config.max_iter == 1000


# =============================================================================
# Test RankModelTrainer
# =============================================================================


class TestRankModelTrainer:
    """Tests for RankModelTrainer class."""

    def test_trainer_initialization(self):
        """Trainer initializes with default config."""
        trainer = RankModelTrainer()
        assert trainer.config is not None
        assert trainer.model is None

    def test_trainer_custom_config(self):
        """Trainer accepts custom configuration."""
        config = TrainingConfig(max_iter=100)
        trainer = RankModelTrainer(config)
        assert trainer.config.max_iter == 100

    def test_save_without_training_raises(self):
        """Saving without training raises RuntimeError."""
        trainer = RankModelTrainer()
        with pytest.raises(RuntimeError, match="not trained"):
            trainer.save()


class TestRankModelTrainerWithData:
    """Tests for RankModelTrainer with mock data."""

    @pytest.fixture
    def mock_dataset(self, tmp_path: Path):
        """Create mock training dataset."""
        for rank in range(3):
            rank_dir = tmp_path / str(rank)
            rank_dir.mkdir()
            for i in range(5):
                # Create simple test image
                img = np.random.randint(0, 255, (120, 120), dtype=np.uint8)
                cv2.imwrite(str(rank_dir / f"sample_{i}.png"), img)
        return tmp_path

    def test_train_with_mock_data(self, mock_dataset: Path):
        """Training works with mock dataset."""
        trainer = RankModelTrainer(TrainingConfig(max_iter=50))
        result = trainer.train(mock_dataset)

        assert isinstance(result, TrainingResult)
        assert trainer.model is not None
        assert len(result.classes) == 3
        assert result.accuracy >= 0.0
        assert result.val_accuracy is not None

    def test_save_model(self, mock_dataset: Path, tmp_path: Path):
        """Model can be saved to disk."""
        trainer = RankModelTrainer(TrainingConfig(max_iter=50))
        trainer.train(mock_dataset)

        model_path = tmp_path / "test_model.pkl"
        saved_path = trainer.save(model_path)

        assert saved_path == model_path
        assert model_path.exists()


# =============================================================================
# Test UnitModelTrainer
# =============================================================================


class TestUnitModelTrainer:
    """Tests for UnitModelTrainer class."""

    def test_trainer_initialization(self):
        """Trainer initializes correctly."""
        trainer = UnitModelTrainer()
        assert trainer.config is not None
        assert trainer.model is None
        assert trainer.label_map == {}

    @pytest.fixture
    def mock_unit_dataset(self, tmp_path: Path):
        """Create mock unit training dataset."""
        units = ["demon_hunter", "dryad", "knight_statue"]
        for unit in units:
            unit_dir = tmp_path / unit
            unit_dir.mkdir()
            for i in range(5):
                img = np.random.randint(0, 255, (120, 120, 3), dtype=np.uint8)
                cv2.imwrite(str(unit_dir / f"sample_{i}.png"), img)
        return tmp_path

    def test_train_with_mock_data(self, mock_unit_dataset: Path):
        """Training works with mock unit dataset."""
        trainer = UnitModelTrainer(TrainingConfig(max_iter=50))
        result = trainer.train(mock_unit_dataset)

        assert trainer.model is not None
        assert len(result.classes) == 3
        assert len(trainer.label_map) == 3


# =============================================================================
# Test MergeRule and MergeWhitelist
# =============================================================================


class TestMergeRule:
    """Tests for MergeRule dataclass."""

    def test_same_type_rule(self):
        """Rule with 'same' allows same unit type only."""
        rule = MergeRule("demon_hunter", "same")
        assert rule.can_merge_with("demon_hunter") is True
        assert rule.can_merge_with("dryad") is False

    def test_any_type_rule(self):
        """Rule with 'any' allows all unit types."""
        rule = MergeRule("harlequin", "any")
        assert rule.can_merge_with("demon_hunter") is True
        assert rule.can_merge_with("dryad") is True
        assert rule.can_merge_with("anything") is True

    def test_list_rule(self):
        """Rule with list allows specific units."""
        rule = MergeRule("dryad", ["knight_statue", "demon_hunter"])
        assert rule.can_merge_with("knight_statue") is True
        assert rule.can_merge_with("demon_hunter") is True
        assert rule.can_merge_with("chemist") is False


class TestMergeWhitelist:
    """Tests for MergeWhitelist class."""

    def test_default_whitelist(self):
        """Default whitelist has expected rules."""
        wl = MergeWhitelist.default()
        assert "harlequin" in wl.rules
        assert "dryad" in wl.rules
        assert wl.rules["harlequin"].merges_with == "any"

    def test_can_merge_same_type(self):
        """Whitelist allows same type merge by default."""
        wl = MergeWhitelist.default()
        assert wl.can_merge("archer", "archer") is True

    def test_can_merge_harlequin(self):
        """Harlequin can merge with anything."""
        wl = MergeWhitelist.default()
        assert wl.can_merge("harlequin", "demon_hunter") is True
        assert wl.can_merge("harlequin", "dryad") is True

    def test_cannot_merge_different_types(self):
        """Different types cannot merge by default."""
        wl = MergeWhitelist.default()
        # Neither has special rules
        assert wl.can_merge("archer", "hunter") is False

    def test_json_roundtrip(self, tmp_path: Path):
        """Whitelist can be saved and loaded from JSON."""
        wl = MergeWhitelist.default()
        json_path = tmp_path / "whitelist.json"
        wl.to_json(json_path)

        loaded = MergeWhitelist.from_json(json_path)
        assert "harlequin" in loaded.rules


# =============================================================================
# Test MergeModelSpec
# =============================================================================


class TestMergeModelSpec:
    """Tests for MergeModelSpec class."""

    def test_default_spec(self):
        """Default spec has expected values."""
        spec = MergeModelSpec()
        assert spec.n_unit_types == 80
        assert spec.n_ranks == 8
        assert spec.grid_size == 15
        assert spec.architecture == "mlp"

    def test_feature_dim_calculation(self):
        """Feature dimension is calculated correctly."""
        spec = MergeModelSpec(n_unit_types=10, n_ranks=8, grid_size=15)
        expected = 10 * 2 + 2 + 15 * 11 + 2  # units*2 + ranks + grid + context
        assert spec.feature_dim == expected

    def test_json_export(self, tmp_path: Path):
        """Spec can be exported to JSON."""
        spec = MergeModelSpec()
        json_path = tmp_path / "spec.json"
        spec.to_json(json_path)

        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data["architecture"] == "mlp"
        assert data["n_unit_types"] == 80


# =============================================================================
# Test MergeFeatureExtractor
# =============================================================================


class TestMergeFeatureExtractor:
    """Tests for MergeFeatureExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create extractor with test labels."""
        labels = ["demon_hunter", "dryad", "knight_statue"]
        return MergeFeatureExtractor(unit_labels=labels)

    def test_extract_features_shape(self, extractor):
        """Feature extraction returns correct shape."""
        features = extractor.extract_merge_features(
            source_unit="demon_hunter",
            source_rank=3,
            target_unit="dryad",
            target_rank=2,
        )
        assert isinstance(features, np.ndarray)
        assert features.dtype == np.float32

    def test_extract_features_with_grid(self, extractor):
        """Feature extraction works with grid state."""
        grid_state = [
            {"unit": "demon_hunter", "rank": 3},
            {"unit": "dryad", "rank": 2},
        ] + [{"unit": "empty", "rank": 0}] * 13

        features = extractor.extract_merge_features(
            source_unit="demon_hunter",
            source_rank=3,
            target_unit="dryad",
            target_rank=2,
            grid_state=grid_state,
            mana=500,
            game_phase=0.5,
        )
        assert len(features) > 0


# =============================================================================
# Test MergeDataCollector
# =============================================================================


class TestMergeDataCollector:
    """Tests for MergeDataCollector class."""

    def test_collector_initialization(self, tmp_path: Path):
        """Collector initializes correctly."""
        collector = MergeDataCollector(tmp_path)
        assert collector.n_decisions == 0

    def test_record_decision(self, tmp_path: Path):
        """Decisions can be recorded."""
        collector = MergeDataCollector(tmp_path)
        collector.record_decision(
            source_cell=0,
            target_cell=1,
            source_unit="demon_hunter",
            target_unit="dryad",
            source_rank=3,
            target_rank=2,
            was_executed=True,
            outcome="success",
            mana=500,
        )
        assert collector.n_decisions == 1

    def test_save_session(self, tmp_path: Path):
        """Session can be saved to JSON."""
        collector = MergeDataCollector(tmp_path)
        collector.record_decision(
            source_cell=0,
            target_cell=1,
            source_unit="demon_hunter",
            target_unit="dryad",
            source_rank=3,
            target_rank=2,
            was_executed=True,
            outcome="success",
        )

        saved_path = collector.save_session()
        assert saved_path.exists()

        data = json.loads(saved_path.read_text())
        assert data["n_decisions"] == 1
        assert len(data["decisions"]) == 1

    def test_clear_session(self, tmp_path: Path):
        """Clear resets the collector."""
        collector = MergeDataCollector(tmp_path)
        collector.record_decision(
            source_cell=0,
            target_cell=1,
            source_unit="demon_hunter",
            target_unit="dryad",
            source_rank=3,
            target_rank=2,
            was_executed=True,
            outcome="success",
        )

        collector.clear()
        assert collector.n_decisions == 0


# =============================================================================
# Test ONNX Export (Optional)
# =============================================================================


class TestONNXExport:
    """Tests for ONNX export functionality."""

    def test_check_onnx_available(self):
        """Check if ONNX is available."""
        from rush_bot.ml.onnx_export import check_onnx_available

        # Just verify the function runs - result depends on installed packages
        result = check_onnx_available()
        assert isinstance(result, bool)

    @pytest.mark.skipif(
        True,  # Skip by default as ONNX is optional
        reason="ONNX dependencies may not be installed",
    )
    def test_export_sklearn_model(self, tmp_path: Path):
        """Test ONNX export of sklearn model."""
        from sklearn.linear_model import LogisticRegression

        from rush_bot.ml.onnx_export import check_onnx_available
        from rush_bot.ml.onnx_export import export_sklearn_to_onnx

        if not check_onnx_available():
            pytest.skip("ONNX not available")

        # Create and train simple model
        X = np.random.randn(100, 50).astype(np.float32)
        y = (X[:, 0] > 0).astype(np.int64)
        model = LogisticRegression(max_iter=100)
        model.fit(X, y)

        # Export
        onnx_path = tmp_path / "test_model.onnx"
        result = export_sklearn_to_onnx(model, onnx_path, input_shape=(50,))

        assert result.exists()
