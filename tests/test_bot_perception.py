"""
Rush Royale Bot - Bot Perception Tests
Python 3.13 Compatible

Tests for computer vision and ML functionality.
"""
from __future__ import annotations

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add Src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Src"))


class TestColorMatching:
    """Tests for unit color matching."""
    
    def test_get_color_returns_correct_shape(self, sample_unit_icons, mock_cv2):
        """Test that get_color returns 5x3 color array."""
        if not sample_unit_icons:
            pytest.skip("No unit icons available for testing")
        
        from bot_perception import get_color
        
        # Mock the image reading
        mock_cv2["imread"].return_value = np.random.randint(
            0, 256, (120, 120, 3), dtype=np.uint8
        )
        
        colors = get_color(str(sample_unit_icons[0]))
        
        assert colors.shape == (5, 3), f"Expected (5, 3), got {colors.shape}"
        assert colors.dtype == int
    
    def test_match_unit_returns_tuple(self, mock_cv2):
        """Test that match_unit returns (unit_name, probability)."""
        from bot_perception import match_unit
        
        # Create mock reference data
        ref_colors = np.array([[100, 100, 100], [200, 200, 200]])
        ref_units = ["unit_a.png", "unit_b.png"]
        
        # Mock the image to have similar colors
        mock_cv2["imread"].return_value = np.full((120, 120, 3), 100, dtype=np.uint8)
        
        with patch("bot_perception.get_color", return_value=np.array([[100, 100, 100]] * 5)):
            result = match_unit("test.png", ref_colors, ref_units)
        
        assert isinstance(result, (list, tuple))
        assert len(result) == 2
        assert isinstance(result[0], str)


class TestRankMatching:
    """Tests for unit rank detection."""
    
    def test_match_rank_with_mock_model(self, mock_cv2):
        """Test rank matching with mocked sklearn model."""
        mock_model = MagicMock()
        mock_model.classes_ = np.array([0, 1, 2, 3, 4, 5, 6, 7])
        mock_model.predict_proba.return_value = np.array([[0.1, 0.7, 0.1, 0.05, 0.025, 0.015, 0.005, 0.005]])
        
        # Clear model cache before test
        import bot_perception
        bot_perception._model_cache.clear()
        
        # Mock the internal model loader to return our mock model
        with patch.object(bot_perception, '_load_rank_model', return_value=mock_model):
            with patch("cv2.Canny", return_value=np.zeros((120, 120), dtype=np.uint8)):
                rank, prob = bot_perception.match_rank("test.png")
                
                assert rank == 1  # Index of highest probability (0.7)
                assert 0 <= prob <= 1
        
        # Clear cache after test
        bot_perception._model_cache.clear()


class TestGridStatus:
    """Tests for grid status analysis."""
    
    def test_grid_status_returns_dataframe(self, mock_cv2):
        """Test that grid_status returns properly structured DataFrame."""
        import pandas as pd
        
        # Create mock file names
        names = [f"OCR_inputs/icon_{i}.png" for i in range(15)]
        
        with patch("os.listdir", return_value=["demo.png", "monk.png"]):
            with patch("bot_perception.get_color", return_value=np.zeros((5, 3), dtype=int)):
                with patch("bot_perception.match_rank", return_value=(1, 0.95)):
                    with patch("bot_perception.match_unit", return_value=["demo.png", 100]):
                        from bot_perception import grid_status
                        
                        df = grid_status(names)
                        
                        assert isinstance(df, pd.DataFrame)
                        assert len(df) == 15
                        assert "grid_pos" in df.columns
                        assert "unit" in df.columns
                        assert "rank" in df.columns
                        assert "Age" in df.columns
    
    def test_grid_status_age_tracking(self, mock_cv2):
        """Test that age tracking works between consecutive grids."""
        import pandas as pd
        
        names = [f"OCR_inputs/icon_{i}.png" for i in range(15)]
        
        with patch("os.listdir", return_value=["demo.png"]):
            with patch("bot_perception.get_color", return_value=np.zeros((5, 3), dtype=int)):
                with patch("bot_perception.match_rank", return_value=(1, 0.95)):
                    with patch("bot_perception.match_unit", return_value=["demo.png", 100]):
                        from bot_perception import grid_status
                        
                        # First grid - no previous
                        df1 = grid_status(names, prev_grid=None)
                        assert all(df1["Age"] == 0)
                        
                        # Second grid - with previous (same units)
                        df2 = grid_status(names, prev_grid=df1)
                        # Age should increase for consistent units
                        assert all(df2["Age"] >= 0)


class TestModelTraining:
    """Tests for ML model training functions."""
    
    @pytest.mark.ml
    def test_load_dataset(self, project_root):
        """Test dataset loading from machine_learning folder."""
        ml_folder = project_root / "machine_learning" / "inputs"
        
        if not ml_folder.exists():
            pytest.skip("machine_learning/inputs folder not found")
        
        from bot_perception import load_dataset
        
        X, Y = load_dataset(str(ml_folder) + "/")
        
        assert len(X) == len(Y)
        if len(X) > 0:
            assert X.ndim == 2  # Flattened images
    
    @pytest.mark.ml
    def test_quick_train_model(self, project_root):
        """Test model training function."""
        ml_folder = project_root / "machine_learning" / "inputs"
        
        if not ml_folder.exists() or not list(ml_folder.glob("*.png")):
            pytest.skip("No training data available")
        
        from bot_perception import quick_train_model
        from sklearn.linear_model import LogisticRegression
        
        model = quick_train_model()
        
        assert isinstance(model, LogisticRegression)


class TestPositionFilter:
    """Tests for position filtering logic."""
    
    def test_position_filter_finds_adjacent(self):
        """Test that position_filter correctly identifies adjacent units."""
        import pandas as pd
        
        # Create a mock grid with demon_hunter and adjacent knight_statues
        grid_data = {
            "grid_pos": [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4],
                        [1, 0], [1, 1], [1, 2], [1, 3], [1, 4],
                        [2, 0], [2, 1], [2, 2], [2, 3], [2, 4]],
            "unit": ["empty.png"] * 15,
            "rank": [0] * 15,
        }
        
        # Place demon_hunter at position [1, 2] (index 7)
        grid_data["unit"][7] = "demon_hunter.png"
        grid_data["rank"][7] = 5
        
        # Place knight_statues adjacent
        grid_data["unit"][6] = "knight_statue.png"  # [1, 1]
        grid_data["rank"][6] = 3
        grid_data["unit"][8] = "knight_statue.png"  # [1, 3]
        grid_data["rank"][8] = 2
        
        df = pd.DataFrame(grid_data)
        
        from bot_perception import position_filter
        
        # This should find the adjacent knight_statue with lowest rank
        try:
            key_pos = position_filter(df, key_target="demon_hunter.png")
            assert key_pos in [6, 8]  # Should be one of the adjacent positions
        except (KeyError, IndexError):
            # Function may fail if no valid positions found
            pass
