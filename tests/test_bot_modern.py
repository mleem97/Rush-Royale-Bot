"""
Tests for BotModern class.
Python 3.13 Compatible
"""
from __future__ import annotations

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add Src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Src"))


class TestBotModernImport:
    """Test BotModern can be imported."""
    
    def test_bot_modern_import(self):
        """Test BotModern class can be imported."""
        from bot_core_modern import BotModern
        assert BotModern is not None
    
    def test_bot_alias_exists(self):
        """Test Bot alias points to BotModern."""
        from bot_core_modern import Bot, BotModern
        assert Bot is BotModern
    
    def test_utility_exports(self):
        """Test utility functions are exported."""
        from bot_core_modern import (
            get_grid,
            get_unit_count,
            preserve_unit,
            grid_meta_info,
            adv_filter_keys,
            get_button_pos,
        )
        
        assert callable(get_grid)
        assert callable(get_unit_count)
        assert callable(preserve_unit)
        assert callable(grid_meta_info)
        assert callable(adv_filter_keys)
        assert callable(get_button_pos)


class TestBotHandler:
    """Test bot handler integration."""
    
    def test_modern_bot_flag(self):
        """Test MODERN_BOT_AVAILABLE flag exists."""
        import bot_handler
        assert hasattr(bot_handler, 'MODERN_BOT_AVAILABLE')
    
    def test_start_bot_class_signature(self):
        """Test start_bot_class accepts use_modern parameter."""
        import inspect
        import bot_handler
        
        sig = inspect.signature(bot_handler.start_bot_class)
        params = list(sig.parameters.keys())
        
        assert 'logger' in params
        assert 'use_modern' in params


class TestBotModernMethods:
    """Test BotModern method signatures."""
    
    def test_has_compatibility_methods(self):
        """Test BotModern has backward compatibility methods."""
        from bot_core_modern import BotModern
        
        # Check key methods exist
        assert hasattr(BotModern, 'shell')
        assert hasattr(BotModern, 'click')
        assert hasattr(BotModern, 'click_button')
        assert hasattr(BotModern, 'swipe')
        assert hasattr(BotModern, 'key_input')
        assert hasattr(BotModern, 'restart_RR')
        assert hasattr(BotModern, 'getScreen')
        assert hasattr(BotModern, 'crop_img')
    
    def test_has_vision_methods(self):
        """Test BotModern has vision methods."""
        from bot_core_modern import BotModern
        
        assert hasattr(BotModern, 'getXYByImage')
        assert hasattr(BotModern, 'get_store_state')
        assert hasattr(BotModern, 'get_current_icons')
        assert hasattr(BotModern, 'scan_grid')
        assert hasattr(BotModern, 'getMana')
    
    def test_has_combat_methods(self):
        """Test BotModern has combat methods."""
        from bot_core_modern import BotModern
        
        assert hasattr(BotModern, 'merge_unit')
        assert hasattr(BotModern, 'merge_special_unit')
        assert hasattr(BotModern, 'special_merge')
        assert hasattr(BotModern, 'harley_merge')
        assert hasattr(BotModern, 'try_merge')
        assert hasattr(BotModern, 'mana_level')
    
    def test_has_navigation_methods(self):
        """Test BotModern has navigation methods."""
        from bot_core_modern import BotModern
        
        assert hasattr(BotModern, 'play_dungeon')
        assert hasattr(BotModern, 'find_store_refresh')
        assert hasattr(BotModern, 'refresh_shop')
        assert hasattr(BotModern, 'watch_ads')
        assert hasattr(BotModern, 'battle_screen')


class TestBotModernProperties:
    """Test BotModern property accessors."""
    
    def test_screenrgb_property_defined(self):
        """Test screenRGB property is defined."""
        from bot_core_modern import BotModern
        
        # Check it's a property
        assert isinstance(
            getattr(BotModern, 'screenRGB', None),
            property
        )
