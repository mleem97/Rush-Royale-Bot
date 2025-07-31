#!/usr/bin/env python3
"""
Rush Royale Bot - Configuration Management
Handles bot configuration, validation, and settings persistence
"""

import configparser
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import json


class ConfigManager:
    """Manages bot configuration with validation and type conversion"""
    
    DEFAULT_CONFIG = {
        'bot': {
            'floor': '10',
            'mana_level': '1,3,5',
            'units': 'chemist,harlequin,bombardier,dryad,demon_hunter',
            'dps_unit': 'demon_hunter',
            'pve': 'True',
            'require_shaman': 'False',
            'max_loops': '800',
            'auto_ads': 'True'
        },
        'recognition': {
            'mse_threshold': '2000',
            'confidence_threshold': '0.7',
            'screen_capture_delay': '0.1'
        },
        'debug': {
            'enabled': 'False',
            'log_level': 'INFO',
            'save_screenshots': 'False',
            'performance_monitoring': 'True'
        },
        'gui': {
            'theme': 'dark',
            'auto_scroll_logs': 'True',
            'show_tooltips': 'True'
        }
    }
    
    def __init__(self, config_path: str = "config.ini"):
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser()
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self._load_config()
        self._validate_config()
    
    def _load_config(self):
        """Load configuration from file or create default"""
        try:
            if self.config_path.exists():
                self.config.read(self.config_path, encoding='utf-8')
                self.logger.info(f"Configuration loaded from {self.config_path}")
            else:
                self.logger.info("Creating default configuration")
                self._create_default_config()
                
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration file"""
        try:
            # Set default values
            for section, options in self.DEFAULT_CONFIG.items():
                if not self.config.has_section(section):
                    self.config.add_section(section)
                
                for key, value in options.items():
                    self.config.set(section, key, value)
            
            # Save to file
            self.save()
            self.logger.info("Default configuration created")
            
        except Exception as e:
            self.logger.error(f"Failed to create default configuration: {e}")
    
    def _validate_config(self):
        """Validate configuration values"""
        errors = []
        
        # Validate bot section
        if self.config.has_section('bot'):
            bot_section = self.config['bot']
            
            # Floor validation
            try:
                floor = int(bot_section.get('floor', '10'))
                if floor < 1 or floor > 50:
                    errors.append("Floor must be between 1 and 50")
            except ValueError:
                errors.append("Floor must be a valid integer")
            
            # Mana level validation
            try:
                mana_levels = [int(x.strip()) for x in bot_section.get('mana_level', '1,3,5').split(',')]
                if not all(1 <= level <= 5 for level in mana_levels):
                    errors.append("Mana levels must be between 1 and 5")
            except ValueError:
                errors.append("Mana levels must be comma-separated integers")
            
            # Units validation
            units = [unit.strip() for unit in bot_section.get('units', '').split(',')]
            if len(units) < 4:
                errors.append("At least 4 units must be specified")
        
        # Validate recognition section
        if self.config.has_section('recognition'):
            rec_section = self.config['recognition']
            
            try:
                threshold = float(rec_section.get('confidence_threshold', '0.7'))
                if threshold < 0.0 or threshold > 1.0:
                    errors.append("Confidence threshold must be between 0.0 and 1.0")
            except ValueError:
                errors.append("Confidence threshold must be a valid float")
        
        if errors:
            self.logger.warning("Configuration validation errors:")
            for error in errors:
                self.logger.warning(f"  - {error}")
    
    def get(self, section: str, key: str, fallback: Any = None) -> str:
        """Get configuration value as string"""
        try:
            return self.config.get(section, key, fallback=str(fallback) if fallback is not None else None)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return str(fallback) if fallback is not None else None
    
    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        """Get configuration value as integer"""
        try:
            return self.config.getint(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getfloat(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Get configuration value as float"""
        try:
            return self.config.getfloat(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getboolean(self, section: str, key: str, fallback: bool = False) -> bool:
        """Get configuration value as boolean"""
        try:
            return self.config.getboolean(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getlist(self, section: str, key: str, fallback: Optional[List[str]] = None) -> List[str]:
        """Get configuration value as list (comma-separated)"""
        try:
            value = self.config.get(section, key)
            return [item.strip() for item in value.split(',') if item.strip()]
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback or []
    
    def set(self, section: str, key: str, value: Any):
        """Set configuration value"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        self.config.set(section, key, str(value))
    
    def setlist(self, section: str, key: str, values: List[str]):
        """Set configuration value from list (comma-separated)"""
        self.set(section, key, ','.join(values))
    
    def save(self) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
            
            self.logger.debug(f"Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def reload(self):
        """Reload configuration from file"""
        self._load_config()
        self._validate_config()
        self.logger.info("Configuration reloaded")
    
    def get_bot_config(self) -> Dict[str, Any]:
        """Get bot-specific configuration with type conversion"""
        return {
            'floor': self.getint('bot', 'floor', 10),
            'mana_level': [int(x) for x in self.getlist('bot', 'mana_level', ['1', '3', '5'])],
            'units': self.getlist('bot', 'units', ['chemist', 'harlequin', 'bombardier', 'dryad', 'demon_hunter']),
            'dps_unit': self.get('bot', 'dps_unit', 'demon_hunter'),
            'pve': self.getboolean('bot', 'pve', True),
            'require_shaman': self.getboolean('bot', 'require_shaman', False),
            'max_loops': self.getint('bot', 'max_loops', 800),
            'auto_ads': self.getboolean('bot', 'auto_ads', True)
        }
    
    def get_recognition_config(self) -> Dict[str, Any]:
        """Get recognition-specific configuration"""
        return {
            'mse_threshold': self.getfloat('recognition', 'mse_threshold', 2000.0),
            'confidence_threshold': self.getfloat('recognition', 'confidence_threshold', 0.7),
            'screen_capture_delay': self.getfloat('recognition', 'screen_capture_delay', 0.1)
        }
    
    def get_debug_config(self) -> Dict[str, Any]:
        """Get debug-specific configuration"""
        return {
            'enabled': self.getboolean('debug', 'enabled', False),
            'log_level': self.get('debug', 'log_level', 'INFO'),
            'save_screenshots': self.getboolean('debug', 'save_screenshots', False),
            'performance_monitoring': self.getboolean('debug', 'performance_monitoring', True)
        }
    
    def get_gui_config(self) -> Dict[str, Any]:
        """Get GUI-specific configuration"""
        return {
            'theme': self.get('gui', 'theme', 'dark'),
            'auto_scroll_logs': self.getboolean('gui', 'auto_scroll_logs', True),
            'show_tooltips': self.getboolean('gui', 'show_tooltips', True)
        }
    
    def update_bot_config(self, **kwargs):
        """Update bot configuration with keyword arguments"""
        for key, value in kwargs.items():
            if key in self.DEFAULT_CONFIG['bot']:
                if isinstance(value, list):
                    self.setlist('bot', key, [str(v) for v in value])
                else:
                    self.set('bot', key, value)
        
        self.save()
    
    def export_config(self, output_file: str) -> bool:
        """Export configuration to JSON file"""
        try:
            config_dict = {}
            
            for section_name in self.config.sections():
                config_dict[section_name] = dict(self.config[section_name])
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration exported to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return False
    
    def import_config(self, input_file: str) -> bool:
        """Import configuration from JSON file"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            # Clear existing configuration
            for section in self.config.sections():
                self.config.remove_section(section)
            
            # Load imported configuration
            for section_name, options in config_dict.items():
                self.config.add_section(section_name)
                for key, value in options.items():
                    self.config.set(section_name, key, str(value))
            
            self.save()
            self._validate_config()
            
            self.logger.info(f"Configuration imported from {input_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import configuration: {e}")
            return False
    
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.config.clear()
        self._create_default_config()
        self.logger.info("Configuration reset to defaults")
    
    def get_summary(self) -> str:
        """Get configuration summary as formatted string"""
        summary = []
        summary.append("Rush Royale Bot Configuration")
        summary.append("=" * 35)
        
        bot_config = self.get_bot_config()
        summary.append(f"Floor: {bot_config['floor']}")
        summary.append(f"PvE Mode: {bot_config['pve']}")
        summary.append(f"Units: {', '.join(bot_config['units'])}")
        summary.append(f"DPS Unit: {bot_config['dps_unit']}")
        summary.append(f"Mana Levels: {bot_config['mana_level']}")
        summary.append(f"Max Loops: {bot_config['max_loops']}")
        
        debug_config = self.get_debug_config()
        summary.append(f"Debug Mode: {debug_config['enabled']}")
        summary.append(f"Log Level: {debug_config['log_level']}")
        
        return '\n'.join(summary)


def create_config_template(output_file: str = "data/config/config.template.ini") -> bool:
    """Create configuration template file with comments"""
    template_content = """# Rush Royale Bot Configuration Template
# Copy this file to config.ini and modify as needed

[bot]
# Dungeon floor to farm (1-50)
floor = 10

# Mana upgrade levels (comma-separated, 1-5)
mana_level = 1,3,5

# Units to use (comma-separated)
units = chemist,harlequin,bombardier,dryad,demon_hunter

# Primary damage dealer unit
dps_unit = demon_hunter

# PvE mode (True/False)
pve = True

# Require shaman opponent (True/False)
require_shaman = False

# Maximum loops before restart
max_loops = 800

# Automatically watch ads (True/False)
auto_ads = True

[recognition]
# Color matching threshold (lower = stricter)
mse_threshold = 2000

# Confidence threshold for icon detection (0.0-1.0)
confidence_threshold = 0.7

# Screen capture delay in seconds
screen_capture_delay = 0.1

[debug]
# Enable debug mode (True/False)
enabled = False

# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
log_level = INFO

# Save debug screenshots (True/False)
save_screenshots = False

# Enable performance monitoring (True/False)
performance_monitoring = True

[gui]
# GUI theme (dark/light)
theme = dark

# Auto-scroll log display (True/False)
auto_scroll_logs = True

# Show tooltips (True/False)
show_tooltips = True
"""
    
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        return True
        
    except Exception as e:
        print(f"Failed to create config template: {e}")
        return False
