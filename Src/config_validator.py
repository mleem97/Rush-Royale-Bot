#!/usr/bin/env python3
"""
Configuration validation and management system for Rush Royale Bot
Validates settings, provides defaults, and ensures configuration integrity
"""

import os
import configparser
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class ConfigValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    fixed_values: Dict[str, Any]


class ConfigValidator:
    """Configuration validation and management system"""
    
    def __init__(self, config_file: str = "config.ini"):
        self.config_file = Path(config_file)
        self.logger = logging.getLogger(__name__)
        
        # Define valid configuration schema
        self.schema = {
            'bot': {
                'floor': {
                    'type': int,
                    'min': 1,
                    'max': 50,
                    'default': 10,
                    'description': 'Dungeon floor to farm'
                },
                'mana_level': {
                    'type': 'comma_separated_ints',
                    'valid_values': [1, 2, 3, 4, 5],
                    'default': '1,3,5',
                    'description': 'Mana upgrade levels'
                },
                'units': {
                    'type': 'comma_separated_strings',
                    'validator': self._validate_units,
                    'default': 'chemist,harlequin,bombardier,dryad,demon_hunter',
                    'description': 'Units to use in battle'
                },
                'dps_unit': {
                    'type': str,
                    'validator': self._validate_dps_unit,
                    'default': 'demon_hunter',
                    'description': 'Primary damage dealer unit'
                },
                'pve': {
                    'type': bool,
                    'default': True,
                    'description': 'PvE mode enabled'
                },
                'require_shaman': {
                    'type': bool,
                    'default': False,
                    'description': 'Require shaman opponent'
                },
                'max_loops': {
                    'type': int,
                    'min': 1,
                    'max': 2000,
                    'default': 800,
                    'description': 'Maximum combat loops before restart'
                }
            },
            'performance': {
                'mse_threshold': {
                    'type': float,
                    'min': 500.0,
                    'max': 5000.0,
                    'default': 2000.0,
                    'description': 'MSE threshold for unit recognition'
                },
                'click_delay': {
                    'type': float,
                    'min': 0.01,
                    'max': 1.0,
                    'default': 0.1,
                    'description': 'Delay between clicks (seconds)'
                },
                'screen_capture_timeout': {
                    'type': int,
                    'min': 1,
                    'max': 30,
                    'default': 5,
                    'description': 'Screen capture timeout (seconds)'
                }
            },
            'logging': {
                'level': {
                    'type': str,
                    'valid_values': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    'default': 'INFO',
                    'description': 'Logging level'
                },
                'max_log_size': {
                    'type': int,
                    'min': 1,
                    'max': 100,
                    'default': 10,
                    'description': 'Maximum log file size (MB)'
                }
            }
        }
        
        # Load available units from filesystem
        self.available_units = self._load_available_units()
        
    def _load_available_units(self) -> List[str]:
        """Load available units from all_units directory"""
        units_dir = Path('all_units')
        if not units_dir.exists():
            return []
        
        units = []
        for file in units_dir.glob('*.png'):
            unit_name = file.stem
            if unit_name != 'empty':  # Exclude empty placeholder
                units.append(unit_name)
        
        return sorted(units)
    
    def validate_config(self, config_path: str = None) -> ConfigValidationResult:
        """Validate configuration file"""
        config_file = Path(config_path) if config_path else self.config_file
        
        errors = []
        warnings = []
        fixed_values = {}
        
        # Check if config file exists
        if not config_file.exists():
            self.logger.warning(f"Config file {config_file} not found, creating default")
            self._create_default_config(config_file)
            warnings.append(f"Created default config file: {config_file}")
        
        # Load and validate configuration
        config = configparser.ConfigParser()
        try:
            config.read(config_file)
        except Exception as e:
            errors.append(f"Failed to read config file: {e}")
            return ConfigValidationResult(False, errors, warnings, fixed_values)
        
        # Validate each section and setting
        for section_name, section_schema in self.schema.items():
            if section_name not in config:
                config.add_section(section_name)
                warnings.append(f"Added missing section: [{section_name}]")
            
            section = config[section_name]
            
            for setting_name, setting_schema in section_schema.items():
                result = self._validate_setting(
                    section, section_name, setting_name, setting_schema
                )
                
                if result['error']:
                    errors.append(result['error'])
                if result['warning']:
                    warnings.append(result['warning'])
                if result['fixed_value'] is not None:
                    fixed_values[f"{section_name}.{setting_name}"] = result['fixed_value']
        
        # Write back any fixed values
        if fixed_values:
            self._apply_fixes(config, fixed_values, config_file)
        
        is_valid = len(errors) == 0
        return ConfigValidationResult(is_valid, errors, warnings, fixed_values)
    
    def _validate_setting(self, section: configparser.SectionProxy, 
                         section_name: str, setting_name: str, 
                         setting_schema: Dict) -> Dict:
        """Validate a single configuration setting"""
        result = {
            'error': None,
            'warning': None,
            'fixed_value': None
        }
        
        # Check if setting exists
        if setting_name not in section:
            default_value = setting_schema['default']
            section[setting_name] = str(default_value)
            result['warning'] = f"Added missing setting {section_name}.{setting_name} = {default_value}"
            result['fixed_value'] = default_value
            return result
        
        raw_value = section[setting_name]
        setting_type = setting_schema['type']
        
        try:
            # Type conversion and validation
            if setting_type == bool:
                value = section.getboolean(setting_name)
            elif setting_type == int:
                value = section.getint(setting_name)
                # Check range
                if 'min' in setting_schema and value < setting_schema['min']:
                    result['error'] = f"{section_name}.{setting_name} below minimum ({setting_schema['min']})"
                if 'max' in setting_schema and value > setting_schema['max']:
                    result['error'] = f"{section_name}.{setting_name} above maximum ({setting_schema['max']})"
            elif setting_type == float:
                value = section.getfloat(setting_name)
                # Check range
                if 'min' in setting_schema and value < setting_schema['min']:
                    result['error'] = f"{section_name}.{setting_name} below minimum ({setting_schema['min']})"
                if 'max' in setting_schema and value > setting_schema['max']:
                    result['error'] = f"{section_name}.{setting_name} above maximum ({setting_schema['max']})"
            elif setting_type == str:
                value = raw_value
            elif setting_type == 'comma_separated_ints':
                values = [int(x.strip()) for x in raw_value.split(',')]
                if 'valid_values' in setting_schema:
                    invalid = [v for v in values if v not in setting_schema['valid_values']]
                    if invalid:
                        result['error'] = f"{section_name}.{setting_name} contains invalid values: {invalid}"
                value = values
            elif setting_type == 'comma_separated_strings':
                value = [x.strip() for x in raw_value.split(',')]
            else:
                result['error'] = f"Unknown type {setting_type} for {section_name}.{setting_name}"
                return result
            
            # Check valid values
            if 'valid_values' in setting_schema and setting_type not in ['comma_separated_ints']:
                if value not in setting_schema['valid_values']:
                    result['error'] = f"{section_name}.{setting_name} has invalid value: {value}"
            
            # Custom validator
            if 'validator' in setting_schema:
                validation_result = setting_schema['validator'](value, section_name, setting_name)
                if validation_result is not True:
                    result['error'] = validation_result
                    
        except ValueError as e:
            result['error'] = f"{section_name}.{setting_name} has invalid type: {e}"
        
        return result
    
    def _validate_units(self, units: List[str], section_name: str, setting_name: str) -> Union[bool, str]:
        """Validate unit selection"""
        if not units:
            return "No units specified"
        
        if len(units) < 3:
            return "At least 3 units required"
        
        # Check if units exist
        invalid_units = [unit for unit in units if unit not in self.available_units]
        if invalid_units:
            return f"Invalid units: {invalid_units}. Available: {self.available_units}"
        
        return True
    
    def _validate_dps_unit(self, dps_unit: str, section_name: str, setting_name: str) -> Union[bool, str]:
        """Validate DPS unit selection"""
        if dps_unit not in self.available_units:
            return f"DPS unit '{dps_unit}' not found. Available: {self.available_units}"
        
        return True
    
    def _create_default_config(self, config_file: Path):
        """Create default configuration file"""
        config = configparser.ConfigParser()
        
        # Generate default config from schema
        for section_name, section_schema in self.schema.items():
            config.add_section(section_name)
            for setting_name, setting_schema in section_schema.items():
                default_value = setting_schema['default']
                config.set(section_name, setting_name, str(default_value))
        
        # Write to file
        with open(config_file, 'w') as f:
            config.write(f)
    
    def _apply_fixes(self, config: configparser.ConfigParser, 
                    fixed_values: Dict[str, Any], config_file: Path):
        """Apply fixes to configuration file"""
        for full_key, value in fixed_values.items():
            section_name, setting_name = full_key.split('.')
            config.set(section_name, setting_name, str(value))
        
        # Write back to file
        with open(config_file, 'w') as f:
            config.write(f)
        
        self.logger.info(f"Applied {len(fixed_values)} configuration fixes")
    
    def get_config_documentation(self) -> str:
        """Generate configuration documentation"""
        doc = []
        doc.append("# Rush Royale Bot Configuration Guide")
        doc.append("=" * 50)
        doc.append("")
        
        for section_name, section_schema in self.schema.items():
            doc.append(f"## [{section_name}]")
            doc.append("")
            
            for setting_name, setting_schema in section_schema.items():
                doc.append(f"### {setting_name}")
                doc.append(f"**Description**: {setting_schema['description']}")
                doc.append(f"**Type**: {setting_schema['type']}")
                doc.append(f"**Default**: {setting_schema['default']}")
                
                if 'min' in setting_schema:
                    doc.append(f"**Minimum**: {setting_schema['min']}")
                if 'max' in setting_schema:
                    doc.append(f"**Maximum**: {setting_schema['max']}")
                if 'valid_values' in setting_schema:
                    doc.append(f"**Valid Values**: {setting_schema['valid_values']}")
                
                doc.append("")
        
        if self.available_units:
            doc.append("## Available Units")
            doc.append("")
            for unit in self.available_units:
                doc.append(f"- {unit}")
            doc.append("")
        
        return "\n".join(doc)
    
    def export_template_config(self, output_file: str = "config_template.ini"):
        """Export a template configuration file with comments"""
        config = configparser.ConfigParser(allow_no_value=True)
        
        for section_name, section_schema in self.schema.items():
            config.add_section(section_name)
            
            for setting_name, setting_schema in section_schema.items():
                # Add comment
                comment = f"# {setting_schema['description']}"
                if 'min' in setting_schema and 'max' in setting_schema:
                    comment += f" (Range: {setting_schema['min']}-{setting_schema['max']})"
                elif 'valid_values' in setting_schema:
                    comment += f" (Options: {', '.join(map(str, setting_schema['valid_values']))})"
                
                config.set(section_name, comment, None)
                config.set(section_name, setting_name, str(setting_schema['default']))
                config.set(section_name, "", None)  # Empty line
        
        with open(output_file, 'w') as f:
            config.write(f)
        
        self.logger.info(f"Template configuration exported to {output_file}")


def validate_bot_config(config_file: str = "config.ini") -> ConfigValidationResult:
    """Convenience function to validate bot configuration"""
    validator = ConfigValidator(config_file)
    return validator.validate_config()


if __name__ == '__main__':
    # Test configuration validation
    validator = ConfigValidator()
    
    # Generate documentation
    doc = validator.get_config_documentation()
    with open('CONFIG_DOCUMENTATION.md', 'w') as f:
        f.write(doc)
    print("Configuration documentation generated: CONFIG_DOCUMENTATION.md")
    
    # Export template
    validator.export_template_config()
    print("Template configuration exported: config_template.ini")
    
    # Validate current config
    result = validator.validate_config()
    
    print(f"\nValidation Result: {'✅ VALID' if result.is_valid else '❌ INVALID'}")
    
    if result.errors:
        print("\n❌ Errors:")
        for error in result.errors:
            print(f"  • {error}")
    
    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  • {warning}")
    
    if result.fixed_values:
        print("\n🔧 Fixed Values:")
        for key, value in result.fixed_values.items():
            print(f"  • {key} = {value}")
