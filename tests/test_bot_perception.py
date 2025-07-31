#!/usr/bin/env python3
"""
Unit tests for bot_perception module
Tests unit recognition, color matching, and ML rank detection
"""

import unittest
import sys
import os
import numpy as np
import pandas as pd
import cv2
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Src'))

import bot_perception


class TestBotPerception(unittest.TestCase):
    """Test cases for bot perception functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_image_path = "test_unit.png"
        self.sample_color = [120, 150, 200]  # BGR format
        
        # Create a simple test image
        test_img = np.zeros((50, 50, 3), dtype=np.uint8)
        test_img[:, :] = self.sample_color
        cv2.imwrite(self.test_image_path, test_img)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)
    
    def test_get_color(self):
        """Test color extraction from image"""
        colors = bot_perception.get_color(self.test_image_path)
        self.assertIsInstance(colors, list)
        self.assertTrue(len(colors) > 0)
        
        # Test with crop
        colors_cropped = bot_perception.get_color(self.test_image_path, crop=True)
        self.assertIsInstance(colors_cropped, list)
    
    def test_match_unit(self):
        """Test unit matching functionality"""
        ref_colors = np.array([[120, 150, 200], [100, 100, 100]])
        ref_units = ['demon_hunter.png', 'chemist.png']
        
        result = bot_perception.match_unit(self.test_image_path, ref_colors, ref_units)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)  # unit, mse_score
        self.assertIn('.png', result[0])
    
    @patch('os.listdir')
    def test_grid_status(self, mock_listdir):
        """Test grid status analysis"""
        mock_listdir.return_value = ['demon_hunter.png', 'chemist.png']
        
        # Mock file names
        test_names = [self.test_image_path] * 15  # 15 grid positions
        
        with patch('bot_perception.get_color') as mock_get_color, \
             patch('bot_perception.match_unit') as mock_match_unit, \
             patch('bot_perception.match_rank') as mock_match_rank:
            
            mock_get_color.return_value = [self.sample_color]
            mock_match_unit.return_value = ['demon_hunter.png', 1500]
            mock_match_rank.return_value = (3, 0.8)
            
            result = bot_perception.grid_status(test_names)
            
            self.assertIsInstance(result, pd.DataFrame)
            self.assertEqual(len(result), 15)
            self.assertIn('grid_pos', result.columns)
            self.assertIn('unit', result.columns)
            self.assertIn('rank', result.columns)
    
    def test_match_rank_file_not_found(self):
        """Test rank matching with non-existent file"""
        result = bot_perception.match_rank("nonexistent.png")
        self.assertEqual(result, (0, 1.0))  # Default values
    
    def test_mse_threshold(self):
        """Test MSE threshold for unit recognition"""
        ref_colors = np.array([[120, 150, 200]])  # Exact match
        ref_units = ['test_unit.png']
        
        result = bot_perception.match_unit(self.test_image_path, ref_colors, ref_units)
        mse_score = result[1]
        
        # MSE should be very low for exact match
        self.assertLess(mse_score, 100)
        self.assertLessEqual(mse_score, 2000)  # Within threshold


class TestGridAnalysis(unittest.TestCase):
    """Test grid analysis and consistency checking"""
    
    def test_position_filter(self):
        """Test position filtering for adjacent units"""
        # Create sample grid data
        grid_data = {
            'grid_pos': [[0, 0], [0, 1], [1, 0], [1, 1]],
            'unit': ['demon_hunter.png', 'knight_statue.png', 'empty.png', 'knight_statue.png'],
            'rank': [5, 3, 0, 4]
        }
        grid_df = pd.DataFrame(grid_data)
        
        result = bot_perception.position_filter(grid_df, 'demon_hunter.png')
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)  # target_pos, best_pos
    
    def test_grid_consistency(self):
        """Test grid consistency checking with previous state"""
        # Create current and previous grid
        current_data = {
            'grid_pos': [[0, 0], [0, 1]],
            'unit': ['demon_hunter.png', 'chemist.png'],
            'rank': [3, 2]
        }
        
        prev_data = {
            'grid_pos': [[0, 0], [0, 1]], 
            'unit': ['demon_hunter.png', 'chemist.png'],
            'rank': [3, 2],
            'Age': [5, 3]
        }
        
        current_df = pd.DataFrame(current_data)
        prev_df = pd.DataFrame(prev_data)
        
        with patch('os.listdir') as mock_listdir, \
             patch('bot_perception.get_color') as mock_get_color, \
             patch('bot_perception.match_unit') as mock_match_unit, \
             patch('bot_perception.match_rank') as mock_match_rank:
            
            mock_listdir.return_value = ['demon_hunter.png', 'chemist.png']
            mock_get_color.return_value = [[120, 150, 200]]
            mock_match_unit.return_value = ['demon_hunter.png', 1500]  
            mock_match_rank.return_value = (3, 0.8)
            
            result = bot_perception.grid_status(['test1.png', 'test2.png'], prev_grid=prev_df)
            
            self.assertIn('Age', result.columns)
            # Age should be incremented for consistent units
            self.assertTrue(all(result['Age'] >= prev_df['Age']))


if __name__ == '__main__':
    # Configure test output
    unittest.main(verbosity=2, buffer=True)
