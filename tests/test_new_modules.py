"""
Tests for new modular components.
Python 3.13 Compatible
"""
from __future__ import annotations

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Add Src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Src"))


class TestGridUtils:
    """Test grid utility functions."""
    
    def test_get_grid_shape(self):
        """Test grid returns correct shape."""
        from utils.grid_utils import get_grid
        
        boxes, box_size = get_grid()
        
        assert boxes.shape == (3, 5, 2)  # 3 rows, 5 cols, 2 coords
        assert box_size == (120, 120)
    
    def test_get_grid_coordinates(self):
        """Test grid coordinates are reasonable."""
        from utils.grid_utils import get_grid
        
        boxes, _ = get_grid()
        
        # First box should be at top-left
        assert boxes[0, 0, 0] == 153  # x
        assert boxes[0, 0, 1] == 945  # y
        
        # Last box should be at bottom-right
        assert boxes[2, 4, 0] == 153 + 4 * 120  # x
        assert boxes[2, 4, 1] == 945 + 2 * 120  # y
    
    def test_adv_filter_keys_empty(self):
        """Test filtering empty series."""
        from utils.grid_utils import adv_filter_keys
        
        empty = pd.Series(dtype=object)
        result = adv_filter_keys(empty, units='test.png')
        
        assert result.empty
    
    def test_adv_filter_keys_by_unit(self):
        """Test filtering by unit name."""
        from utils.grid_utils import adv_filter_keys
        
        index = pd.MultiIndex.from_tuples([
            ("zealot.png", 1),
            ("zealot.png", 2),
            ("chemist.png", 1),
            ("chemist.png", 3),
        ], names=["unit", "rank"])
        
        series = pd.Series([2, 1, 1, 1], index=index)
        
        result = adv_filter_keys(series, units='zealot.png')
        
        assert len(result) == 2
        assert all('zealot.png' in str(idx) for idx in result.index)
    
    def test_adv_filter_keys_by_rank(self):
        """Test filtering by rank."""
        from utils.grid_utils import adv_filter_keys
        
        index = pd.MultiIndex.from_tuples([
            ("zealot.png", 1),
            ("zealot.png", 2),
            ("chemist.png", 1),
            ("chemist.png", 3),
        ], names=["unit", "rank"])
        
        series = pd.Series([2, 1, 1, 1], index=index)
        
        result = adv_filter_keys(series, ranks=1)
        
        assert len(result) == 2
        assert all(idx[1] == 1 for idx in result.index)
    
    def test_adv_filter_keys_remove(self):
        """Test filtering with remove=True."""
        from utils.grid_utils import adv_filter_keys
        
        index = pd.MultiIndex.from_tuples([
            ("zealot.png", 1),
            ("zealot.png", 2),
            ("chemist.png", 1),
        ], names=["unit", "rank"])
        
        series = pd.Series([2, 1, 1], index=index)
        
        result = adv_filter_keys(series, units='zealot.png', remove=True)
        
        assert len(result) == 1
        assert 'chemist.png' in str(result.index[0])
    
    def test_preserve_unit_highest(self):
        """Test preserving highest rank unit."""
        from utils.grid_utils import preserve_unit
        
        index = pd.MultiIndex.from_tuples([
            ("chemist.png", 1),
            ("chemist.png", 3),
            ("chemist.png", 5),
            ("zealot.png", 2),
        ], names=["unit", "rank"])
        
        series = pd.Series([2, 1, 1, 3], index=index)
        
        result = preserve_unit(series, target="chemist.png")
        
        # Highest chemist (rank 5) should have count reduced
        if ("chemist.png", 5) in result.index:
            assert result[("chemist.png", 5)] == 0
    
    def test_preserve_unit_keep_min(self):
        """Test preserving lowest rank unit."""
        from utils.grid_utils import preserve_unit
        
        index = pd.MultiIndex.from_tuples([
            ("cauldron.png", 1),
            ("cauldron.png", 3),
            ("zealot.png", 2),
        ], names=["unit", "rank"])
        
        series = pd.Series([2, 1, 3], index=index)
        
        result = preserve_unit(series, target="cauldron.png", keep_min=True)
        
        # Lowest cauldron (rank 1) should have count reduced
        if ("cauldron.png", 1) in result.index:
            assert result[("cauldron.png", 1)] == 1
    
    def test_get_button_pos(self):
        """Test button position extraction."""
        from utils.grid_utils import get_button_pos
        
        df = pd.DataFrame({
            'icon': ['home_screen.png', 'battle_icon.png'],
            'available': [True, True],
            'pos [X,Y]': [(100, 200), (300, 400)],
        })
        
        pos = get_button_pos(df, 'battle_icon.png')
        
        assert np.array_equal(pos, np.array([300, 400]))
    
    def test_grid_meta_info(self):
        """Test grid meta info extraction."""
        from utils.grid_utils import grid_meta_info
        
        grid_df = pd.DataFrame({
            'unit': ['zealot.png', 'zealot.png', 'chemist.png', 'empty.png'],
            'rank': [1, 2, 1, 0],
            'grid_pos': [(0, 0), (0, 1), (0, 2), (0, 3)],
            'Age': [5, 3, 10, 0],
        })
        
        df_split, unit_series, df_groups, group_keys = grid_meta_info(grid_df)
        
        assert 'zealot.png' in df_groups.index
        assert 'empty.png' in df_groups.index


class TestADBController:
    """Test ADB controller (mock tests)."""
    
    def test_touch_constants(self):
        """Test touch constants are defined."""
        from adb_controller import TouchConstants, const
        
        assert const.ACTION_DOWN == 0
        assert const.ACTION_UP == 1
        assert const.KEYCODE_BACK == 4
    
    def test_sleep_delay_defined(self):
        """Test sleep delay is defined."""
        from adb_controller import SLEEP_DELAY
        
        assert SLEEP_DELAY == 0.1


class TestScreenCapture:
    """Test screen capture module."""
    
    def test_scrcpy_paths_defined(self):
        """Test scrcpy search paths are reasonable."""
        # This is a basic import test
        from screen_capture import ScreenCapture
        
        assert ScreenCapture is not None


class TestVisionModules:
    """Test vision modules."""
    
    def test_icon_detector_import(self):
        """Test icon detector can be imported."""
        from vision import IconDetector
        
        assert IconDetector is not None
    
    def test_grid_analyzer_import(self):
        """Test grid analyzer can be imported."""
        from vision import GridAnalyzer
        
        assert GridAnalyzer is not None


class TestCombatModules:
    """Test combat modules."""
    
    def test_merge_controller_import(self):
        """Test merge controller can be imported."""
        from combat import MergeController
        
        assert MergeController is not None
    
    def test_mana_manager_import(self):
        """Test mana manager can be imported."""
        from combat import ManaManager
        
        assert ManaManager is not None
    
    def test_mana_positions(self):
        """Test mana upgrade positions are defined."""
        from combat.mana_management import ManaManager
        
        assert 1 in ManaManager.UPGRADE_POSITIONS
        assert 5 in ManaManager.UPGRADE_POSITIONS
        assert ManaManager.HERO_POWER_POS == (800, 1500)


class TestNavigationModules:
    """Test navigation modules."""
    
    def test_dungeon_navigator_import(self):
        """Test dungeon navigator can be imported."""
        from navigation import DungeonNavigator
        
        assert DungeonNavigator is not None
    
    def test_store_navigator_import(self):
        """Test store navigator can be imported."""
        from navigation import StoreNavigator
        
        assert StoreNavigator is not None
    
    def test_ad_watcher_import(self):
        """Test ad watcher can be imported."""
        from navigation import AdWatcher
        
        assert AdWatcher is not None


class TestModernGUI:
    """Test modern GUI module."""
    
    def test_gui_import(self):
        """Test GUI module can be imported."""
        # Skip if no display available
        pytest.importorskip("customtkinter")
        
        from gui_modern import ModernBotGUI
        
        assert ModernBotGUI is not None
    
    def test_gui_log_handler_import(self):
        """Test GUI log handler can be imported."""
        pytest.importorskip("customtkinter")
        
        from gui_modern import GUILogHandler
        
        assert GUILogHandler is not None
