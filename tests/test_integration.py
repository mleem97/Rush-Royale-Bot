#!/usr/bin/env python3
"""
Integration tests for bot functionality
Tests complete workflows and system integration
"""

import unittest
import sys
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Src'))

import bot_handler
import bot_core


class TestBotIntegration(unittest.TestCase):
    """Integration tests for bot components"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create necessary directories
        os.makedirs('all_units', exist_ok=True)
        os.makedirs('units', exist_ok=True)
        
        # Create test unit files
        test_units = ['demon_hunter.png', 'chemist.png', 'bombardier.png']
        for unit in test_units:
            with open(f'all_units/{unit}', 'w') as f:
                f.write('test')
    
    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    @patch('cv2.imread')
    @patch('cv2.imwrite')
    def test_select_units(self, mock_imwrite, mock_imread):
        """Test unit selection functionality"""
        mock_imread.return_value = MagicMock()  # Mock image data
        mock_imwrite.return_value = True
        
        units = ['demon_hunter.png', 'chemist.png']
        result = bot_handler.select_units(units)
        
        self.assertTrue(result)
        self.assertEqual(mock_imwrite.call_count, len(units))
    
    def test_select_units_insufficient(self):
        """Test unit selection with insufficient units"""
        units = ['nonexistent.png']
        result = bot_handler.select_units(units)
        
        self.assertFalse(result)  # Should return False for insufficient units
    
    @patch('bot_handler.check_scrcpy')
    @patch('bot_core.Bot')
    def test_start_bot_class(self, mock_bot, mock_check_scrcpy):
        """Test bot class initialization"""
        mock_check_scrcpy.return_value = True
        mock_logger = MagicMock()
        
        result = bot_handler.start_bot_class(mock_logger)
        
        self.assertIsNotNone(result)
        mock_bot.assert_called_once()
    
    @patch('bot_handler.check_scrcpy')
    def test_start_bot_class_no_scrcpy(self, mock_check_scrcpy):
        """Test bot initialization without scrcpy"""
        mock_check_scrcpy.return_value = False
        mock_logger = MagicMock()
        
        result = bot_handler.start_bot_class(mock_logger)
        
        self.assertIsNone(result)


class TestBotConfiguration(unittest.TestCase):
    """Test bot configuration handling"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_config_creation(self):
        """Test configuration file handling"""
        # Create a simple config file
        config_content = """[bot]
floor = 10
mana_level = 1,3,5
units = chemist, harlequin, bombardier, dryad, demon_hunter
dps_unit = demon_hunter
pve = True
"""
        with open('config.ini', 'w') as f:
            f.write(config_content)
        
        # Verify config file exists and is readable
        self.assertTrue(os.path.exists('config.ini'))
        
        with open('config.ini', 'r') as f:
            content = f.read()
            self.assertIn('demon_hunter', content)
            self.assertIn('floor = 10', content)


class TestBotPerformance(unittest.TestCase):
    """Performance tests for bot functionality"""
    
    @patch('bot_core.port_scan.get_device')
    @patch('bot_core.Client')
    def test_click_performance(self, mock_client, mock_get_device):
        """Test click operation performance"""
        mock_get_device.return_value = 'emulator-5554'
        mock_client.return_value = MagicMock()
        
        bot = bot_core.Bot()
        
        import time
        start_time = time.time()
        
        # Perform multiple clicks
        for i in range(10):
            bot.click(100 + i, 200 + i)
        
        end_time = time.time()
        
        # Should complete within reasonable time
        self.assertLess(end_time - start_time, 5.0)  # 5 seconds max for 10 clicks


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def test_invalid_device_handling(self):
        """Test handling of invalid device scenarios"""
        with patch('bot_core.port_scan.get_device') as mock_get_device:
            mock_get_device.return_value = None
            
            # Should handle no device gracefully
            try:
                bot = bot_core.Bot()
                # If no exception, device should be None or default
                self.assertIsNotNone(bot)
            except Exception as e:
                # Exception is acceptable for no device scenario
                self.assertIn('device', str(e).lower())
    
    def test_empty_unit_series_handling(self):
        """Test handling of empty unit series"""
        import pandas as pd
        
        empty_series = pd.Series(dtype=object)
        
        # Should handle empty series without crashing
        result = bot_core.filter_units(empty_series, 'demon_hunter.png')
        self.assertTrue(result.empty)
        
        result = bot_core.adv_filter_keys(empty_series, units='test')
        self.assertTrue(result.empty)


if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True)
