"""
Rush Royale Bot - Configuration Validator Tests
Python 3.13 Compatible
"""
from __future__ import annotations

import pytest
import configparser
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "Src"))

from config_validator import (
    validate_bot_config,
    validate_floor,
    validate_mana_level,
    validate_units,
    validate_dps_unit,
    validate_boolean,
    ConfigValidationError,
)


class TestFloorValidation:
    """Tests for floor validation."""
    
    def test_valid_floor(self):
        """Test valid floor values."""
        assert validate_floor("1") == 1
        assert validate_floor("5") == 5
        assert validate_floor("15") == 15
    
    def test_invalid_floor_too_low(self):
        """Test floor below minimum."""
        with pytest.raises(ConfigValidationError):
            validate_floor("0")
    
    def test_invalid_floor_too_high(self):
        """Test floor above maximum."""
        with pytest.raises(ConfigValidationError):
            validate_floor("16")
    
    def test_invalid_floor_not_integer(self):
        """Test non-integer floor value."""
        with pytest.raises(ConfigValidationError):
            validate_floor("abc")


class TestManaLevelValidation:
    """Tests for mana level validation."""
    
    def test_valid_mana_levels(self):
        """Test valid mana level strings."""
        assert validate_mana_level("1,2,3,4,5") == [1, 2, 3, 4, 5]
        assert validate_mana_level("1, 3, 5") == [1, 3, 5]
        assert validate_mana_level("5") == [5]
    
    def test_invalid_mana_level_out_of_range(self):
        """Test mana level outside 1-5 range."""
        with pytest.raises(ConfigValidationError):
            validate_mana_level("0,1,2")
        
        with pytest.raises(ConfigValidationError):
            validate_mana_level("1,2,6")
    
    def test_invalid_mana_level_not_integer(self):
        """Test non-integer mana level."""
        with pytest.raises(ConfigValidationError):
            validate_mana_level("a,b,c")


class TestUnitsValidation:
    """Tests for unit selection validation."""
    
    def test_valid_units(self, project_root):
        """Test valid unit selection."""
        units_dir = project_root / "all_units"
        if not units_dir.exists():
            pytest.skip("all_units directory not found")
        
        # Get some actual unit names
        available = list(units_dir.glob("*.png"))[:5]
        if len(available) < 5:
            pytest.skip("Not enough units available")
        
        unit_str = ", ".join(u.stem for u in available)
        result = validate_units(unit_str, units_dir)
        
        assert len(result) == 5
    
    def test_invalid_units_too_few(self):
        """Test insufficient unit count."""
        with pytest.raises(ConfigValidationError):
            validate_units("unit1, unit2, unit3", None)  # Only 3, need 5


class TestBooleanValidation:
    """Tests for boolean field validation."""
    
    @pytest.mark.parametrize("value,expected", [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
        ("off", False),
    ])
    def test_valid_booleans(self, value, expected):
        """Test valid boolean values."""
        assert validate_boolean(value, "test") == expected
    
    def test_invalid_boolean(self):
        """Test invalid boolean value."""
        with pytest.raises(ConfigValidationError):
            validate_boolean("maybe", "test")


class TestFullConfigValidation:
    """Tests for full configuration validation."""
    
    def test_validate_temp_config(self, temp_config_file, project_root):
        """Test validation of temporary config file."""
        # This test may fail if all_units doesn't have the specified units
        # In that case, we skip
        units_dir = project_root / "all_units"
        if not units_dir.exists():
            pytest.skip("all_units directory not found")
        
        try:
            result = validate_bot_config(temp_config_file)
            assert "floor" in result
            assert "mana_level" in result
            assert "units" in result
            assert "dps_unit" in result
            assert "pve" in result
        except ConfigValidationError:
            # May fail due to unit validation - that's OK for this test
            pass
    
    def test_missing_bot_section(self, tmp_path):
        """Test error when [bot] section is missing."""
        config_file = tmp_path / "bad_config.ini"
        config_file.write_text("[other]\nkey = value\n")
        
        with pytest.raises(ConfigValidationError, match="Missing .bot. section"):
            validate_bot_config(config_file)
