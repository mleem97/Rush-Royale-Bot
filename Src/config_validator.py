"""
Rush Royale Bot - Configuration Validator
Python 3.13 Compatible

Validates the config.ini file structure and values.
"""
from __future__ import annotations

import os
import sys
import configparser
from pathlib import Path
from typing import Any


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


def get_config_path() -> Path:
    """Get the path to config.ini file."""
    # Try multiple locations
    possible_paths = [
        Path("config.ini"),
        Path(__file__).parent.parent / "config.ini",
        Path.cwd() / "config.ini",
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    raise ConfigValidationError("config.ini not found in expected locations")


def validate_floor(value: str) -> int:
    """Validate dungeon floor setting."""
    try:
        floor = int(value)
        if not 1 <= floor <= 15:
            raise ConfigValidationError(f"floor must be between 1 and 15, got {floor}")
        return floor
    except ValueError:
        raise ConfigValidationError(f"floor must be an integer, got '{value}'")


def validate_mana_level(value: str) -> list[int]:
    """Validate mana level targets."""
    try:
        levels = [int(x.strip()) for x in value.split(",") if x.strip()]
        for level in levels:
            if not 1 <= level <= 5:
                raise ConfigValidationError(f"mana_level values must be 1-5, got {level}")
        return levels
    except ValueError as e:
        raise ConfigValidationError(f"mana_level must be comma-separated integers: {e}")


def validate_units(value: str, units_dir: Path | None = None) -> list[str]:
    """Validate unit selection."""
    units = [u.strip() for u in value.split(",") if u.strip()]
    
    if len(units) < 5:
        raise ConfigValidationError(f"At least 5 units required, got {len(units)}")
    
    # Check if units exist in all_units folder
    if units_dir is None:
        units_dir = Path(__file__).parent.parent / "all_units"
    
    if units_dir.exists():
        available_units = {f.stem for f in units_dir.glob("*.png")}
        invalid_units = [u for u in units if u not in available_units]
        if invalid_units:
            raise ConfigValidationError(
                f"Unknown units: {invalid_units}. "
                f"Available: {sorted(available_units)[:10]}..."
            )
    
    return units


def validate_dps_unit(value: str, units: list[str]) -> str:
    """Validate DPS unit is in selected units."""
    dps = value.strip()
    if dps not in units:
        raise ConfigValidationError(
            f"dps_unit '{dps}' must be one of the selected units: {units}"
        )
    return dps


def validate_boolean(value: str, field_name: str) -> bool:
    """Validate boolean configuration value."""
    if value.lower() in ("true", "1", "yes", "on"):
        return True
    elif value.lower() in ("false", "0", "no", "off"):
        return False
    else:
        raise ConfigValidationError(
            f"{field_name} must be a boolean (true/false), got '{value}'"
        )


def validate_bot_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """
    Validate the bot configuration file.
    
    Args:
        config_path: Path to config.ini. If None, searches default locations.
        
    Returns:
        Dictionary of validated configuration values.
        
    Raises:
        ConfigValidationError: If validation fails.
    """
    if config_path is None:
        config_path = get_config_path()
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise ConfigValidationError(f"Configuration file not found: {config_path}")
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # Check required sections
    if "bot" not in config:
        raise ConfigValidationError("Missing [bot] section in config.ini")
    
    bot_config = config["bot"]
    validated = {}
    
    # Validate each field
    required_fields = ["floor", "mana_level", "units", "dps_unit"]
    for field in required_fields:
        if field not in bot_config:
            raise ConfigValidationError(f"Missing required field: {field}")
    
    # Validate floor
    validated["floor"] = validate_floor(bot_config.get("floor", "5"))
    
    # Validate mana_level
    validated["mana_level"] = validate_mana_level(bot_config.get("mana_level", "1,2,3,4,5"))
    
    # Validate units
    validated["units"] = validate_units(bot_config.get("units", ""))
    
    # Validate dps_unit
    validated["dps_unit"] = validate_dps_unit(
        bot_config.get("dps_unit", "monk"),
        validated["units"]
    )
    
    # Validate optional boolean fields
    validated["pve"] = validate_boolean(
        bot_config.get("pve", "True"), "pve"
    )
    validated["require_shaman"] = validate_boolean(
        bot_config.get("require_shaman", "False"), "require_shaman"
    )
    
    print(f"✅ Configuration validated successfully: {config_path}")
    return validated


def main() -> int:
    """Run configuration validation from command line."""
    try:
        config = validate_bot_config()
        print("\nValidated configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        return 0
    except ConfigValidationError as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
