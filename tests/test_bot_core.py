#!/usr/bin/env python3
"""
Unit tests for bot_core module
Tests bot initialization, device communication, and core functionality
"""

import unittest
import sys
import os
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock, Mock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Src'))

import bot_core


class TestBotCore(unittest.TestCase):
    """Test cases for bot core functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock scrcpy client to avoid actual device connection
        self.mock_client = MagicMock()
        self.mock_client.control = MagicMock()
        
    @patch('bot_core.port_scan.get_device')
    @patch('bot_core.Client')
    def test_bot_initialization(self, mock_client, mock_get_device):
        """Test bot initialization"""
        mock_get_device.return_value = 'emulator-5554'
        mock_client.return_value = self.mock_client
        
        bot = bot_core.Bot()
        
        self.assertEqual(bot.device, 'emulator-5554')
        self.assertFalse(bot.bot_stop)
        self.assertEqual(bot.combat_step, 0)
    
    @patch('bot_core.port_scan.get_device')
    @patch('bot_core.Client')
    def test_bot_click(self, mock_client, mock_get_device):
        """Test click functionality"""
        mock_get_device.return_value = 'emulator-5554'
        mock_client.return_value = self.mock_client
        
        bot = bot_core.Bot()
        bot.click(100, 200)
        
        # Verify touch events were called
        self.assertEqual(self.mock_client.control.touch.call_count, 2)
    
    @patch('bot_core.port_scan.get_device')
    @patch('bot_core.Client')
    def test_bot_swipe(self, mock_client, mock_get_device):
        """Test swipe functionality"""
        mock_get_device.return_value = 'emulator-5554'
        mock_client.return_value = self.mock_client
        
        bot = bot_core.Bot()
        start_pos = [100, 100]
        end_pos = [200, 200]
        
        bot.swipe(start_pos, end_pos)
        
        # Verify swipe events were called
        self.assertTrue(self.mock_client.control.touch.called)
    
    @patch('subprocess.Popen')
    @patch('bot_core.port_scan.get_device')
    @patch('bot_core.Client')
    def test_shell_command(self, mock_client, mock_get_device, mock_popen):
        """Test ADB shell command execution"""
        mock_get_device.return_value = 'emulator-5554'
        mock_client.return_value = self.mock_client
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        bot = bot_core.Bot()
        bot.shell('echo test')
        
        mock_popen.assert_called_once()
        mock_process.wait.assert_called_once()


class TestBotUtilities(unittest.TestCase):
    """Test utility functions in bot_core"""
    
    def test_get_unit_count(self):
        """Test unit counting functionality"""
        grid_data = {
            'unit': ['demon_hunter.png', 'demon_hunter.png', 'chemist.png', 'empty.png'],
            'rank': [3, 4, 2, 0]
        }
        grid_df = pd.DataFrame(grid_data)
        
        result = bot_core.get_unit_count(grid_df)
        self.assertIsInstance(result, pd.Series)
        self.assertIn('demon_hunter.png', result.index)
        self.assertEqual(result['demon_hunter.png'], 2)
    
    def test_filter_units_by_string(self):
        """Test filtering units by string"""
        # Create test series with MultiIndex
        index = pd.MultiIndex.from_tuples([
            ('demon_hunter.png', 3),
            ('demon_hunter.png', 4), 
            ('chemist.png', 2)
        ], names=['unit', 'rank'])
        
        unit_series = pd.Series([1, 1, 1], index=index)
        
        result = bot_core.filter_units(unit_series, 'demon_hunter.png')
        self.assertEqual(len(result), 2)
        self.assertTrue(all('demon_hunter.png' in str(idx) for idx in result.index))
    
    def test_filter_units_by_rank(self):
        """Test filtering units by rank"""
        index = pd.MultiIndex.from_tuples([
            ('demon_hunter.png', 3),
            ('demon_hunter.png', 4),
            ('chemist.png', 3)
        ], names=['unit', 'rank'])
        
        unit_series = pd.Series([1, 1, 1], index=index)
        
        result = bot_core.filter_units(unit_series, 3)
        self.assertEqual(len(result), 2)
        # All returned items should have rank 3
        for idx in result.index:
            self.assertEqual(idx[1], 3)
    
    def test_adv_filter_keys(self):
        """Test advanced filtering with multiple criteria"""
        index = pd.MultiIndex.from_tuples([
            ('demon_hunter.png', 3),
            ('demon_hunter.png', 4),
            ('chemist.png', 3),
            ('chemist.png', 2)
        ], names=['unit', 'rank'])
        
        unit_series = pd.Series([1, 1, 1, 1], index=index)
        
        # Filter for demon_hunter with rank 3
        result = bot_core.adv_filter_keys(unit_series, units='demon_hunter.png', ranks=3)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.index[0], ('demon_hunter.png', 3))
    
    def test_adv_filter_keys_remove(self):
        """Test advanced filtering with remove=True"""
        index = pd.MultiIndex.from_tuples([
            ('demon_hunter.png', 3),
            ('chemist.png', 2)
        ], names=['unit', 'rank'])
        
        unit_series = pd.Series([1, 1], index=index)
        
        # Remove demon_hunter units
        result = bot_core.adv_filter_keys(unit_series, units='demon_hunter.png', remove=True)
        self.assertEqual(len(result), 1)
        self.assertIn('chemist.png', str(result.index[0]))
    
    def test_preserve_unit(self):
        """Test unit preservation functionality"""
        index = pd.MultiIndex.from_tuples([
            ('chemist.png', 2),
            ('chemist.png', 3),
            ('chemist.png', 4)
        ], names=['unit', 'rank'])
        
        unit_series = pd.Series([2, 1, 1], index=index)
        
        result = bot_core.preserve_unit(unit_series, target='chemist.png')
        # Should remove one instance of the highest rank
        self.assertLess(len(result), len(unit_series))
    
    def test_grid_meta_info(self):
        """Test grid meta information extraction"""
        grid_data = {
            'unit': ['demon_hunter.png', 'chemist.png', 'empty.png'],
            'rank': [3, 2, 0],
            'Age': [5, 3, 0],
            'grid_pos': [[0, 0], [0, 1], [0, 2]]
        }
        grid_df = pd.DataFrame(grid_data)
        
        result = bot_core.grid_meta_info(grid_df, min_age=2)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)  # grid_df, df_groups, grid_analysis


class TestBotScreenAnalysis(unittest.TestCase):
    """Test screen analysis functionality"""
    
    @patch('bot_core.cv2.imread')
    def test_get_grid(self, mock_imread):
        """Test grid coordinate extraction"""
        # Mock image data
        mock_image = np.zeros((900, 1600, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image
        
        result = bot_core.get_grid()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 15)  # 3x5 grid


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
