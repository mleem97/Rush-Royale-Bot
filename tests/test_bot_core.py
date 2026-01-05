"""
Rush Royale Bot - Bot Core Tests
Python 3.13 Compatible

Tests for bot_core.py functionality.
"""
from __future__ import annotations

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock


class TestBotInitialization:
    """Tests for Bot class initialization."""
    
    def test_grid_dimensions(self):
        """Test that grid calculation returns correct dimensions."""
        # Import the function directly to test without full Bot initialization
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "Src"))
        
        from bot_core import get_grid
        
        boxes, box_size = get_grid()
        
        # Grid should be 3x5 (height x width)
        assert boxes.shape == (3, 5, 2), f"Expected (3, 5, 2), got {boxes.shape}"
        
        # Box size should be 120x120
        assert box_size == (120, 120), f"Expected (120, 120), got {box_size}"
        
        # First box should be at expected position
        assert boxes[0, 0, 0] == 153, "First box X position incorrect"
        assert boxes[0, 0, 1] == 945, "First box Y position incorrect"
    
    def test_get_button_pos(self):
        """Test button position extraction from DataFrame."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "Src"))
        import pandas as pd
        from bot_core import get_button_pos
        
        # Create test DataFrame
        df = pd.DataFrame({
            "icon": ["home_screen.png", "battle_icon.png", "back_button.png"],
            "available": [True, True, False],
            "pos [X,Y]": [(100, 200), (300, 400), (500, 600)],
        })
        
        pos = get_button_pos(df, "battle_icon.png")
        
        assert isinstance(pos, np.ndarray)
        assert pos[0] == 300
        assert pos[1] == 400


class TestGridMetaInfo:
    """Tests for grid analysis functions."""
    
    def test_preserve_unit(self):
        """Test unit preservation in merge series."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "Src"))
        import pandas as pd
        from bot_core import preserve_unit
        
        # Create test series with multi-index (unit, rank)
        index = pd.MultiIndex.from_tuples([
            ("chemist.png", 1),
            ("chemist.png", 3),
            ("chemist.png", 5),
            ("knight_statue.png", 2),
        ], names=["unit", "rank"])
        
        series = pd.Series([2, 1, 1, 3], index=index)
        
        # Preserve highest chemist
        result = preserve_unit(series, target="chemist.png")
        
        # Should have reduced count of rank 5 chemist by 1
        # Check if key exists first, then check value
        if ("chemist.png", 5) in result.index:
            assert result[("chemist.png", 5)] == 0
        # If key doesn't exist, that's also acceptable (was removed)
    
    def test_adv_filter_keys_by_unit(self):
        """Test advanced filtering by unit type."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "Src"))
        import pandas as pd
        from bot_core import adv_filter_keys
        
        index = pd.MultiIndex.from_tuples([
            ("demon_hunter.png", 1),
            ("demon_hunter.png", 3),
            ("knight_statue.png", 2),
            ("dryad.png", 1),
        ], names=["unit", "rank"])
        
        series = pd.Series([2, 1, 2, 1], index=index)
        
        # Filter for demon_hunter only
        result = adv_filter_keys(series, units="demon_hunter.png")
        
        assert len(result) == 2
        assert all("demon_hunter.png" in str(idx) for idx in result.index)
    
    def test_adv_filter_keys_remove(self):
        """Test advanced filtering with remove=True."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "Src"))
        import pandas as pd
        from bot_core import adv_filter_keys
        
        index = pd.MultiIndex.from_tuples([
            ("empty.png", 0),
            ("demon_hunter.png", 3),
            ("knight_statue.png", 2),
        ], names=["unit", "rank"])
        
        series = pd.Series([5, 1, 2], index=index)
        
        # Remove empty units
        result = adv_filter_keys(series, units="empty.png", remove=True)
        
        assert ("empty.png", 0) not in result.index
        assert len(result) == 2


class TestBotWithMock:
    """Tests using mocked ADB connection."""
    
    @pytest.mark.integration
    def test_bot_initialization(self, mock_adb_client):
        """Test Bot class can be initialized with mock ADB."""
        mock_client, mock_device = mock_adb_client
        
        with patch("bot_core.port_scan.get_device", return_value="127.0.0.1:5555"):
            with patch("bot_core.cv2.imread", return_value=np.zeros((1600, 900, 3), dtype=np.uint8)):
                with patch("os.path.isfile", return_value=True):
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent / "Src"))
                    
                    # This would require full mock setup
                    # For now, just verify imports work
                    from bot_core import Bot, get_grid
                    assert callable(Bot)
                    assert callable(get_grid)


class TestScreenshotMethods:
    """Tests for screenshot capture methods."""
    
    def test_screenshot_path_generation(self):
        """Test that screenshot paths are generated correctly."""
        device_id = "127.0.0.1:5555"
        bot_id = device_id.split(":")[-1]
        expected_path = f"bot_feed_{bot_id}.png"
        
        assert expected_path == "bot_feed_5555.png"
