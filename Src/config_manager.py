import os
import configparser
import logging

DEFAULT_CONFIG = {
    'bot': {
        'floor': '5',
        'mana_level': '1, 2, 3, 4, 5',
        'pve': 'True',
        'units': 'chemist, knight_statue, harlequin, dryad, demon_hunter',
        'dps_unit': 'demon_hunter.png',
        'require_shaman': 'False',
        'max_loops': '800'
    },
    'performance': {
        'screenshot_timeout': '3',
        'sleep_delay': '0.1',
        'click_delay': '0.05'
    },
    'advanced': {
        'port_range_start': '48000',
        'port_range_end': '65000',
        'orb_detection_threshold': '10',
        'rank_detection_confidence': '0.8'
    }
}

class ConfigManager:
    def __init__(self, config_path='config.ini'):
        self.config_path = config_path
        self.logger = logging.getLogger('__main__')
        self.config = configparser.ConfigParser()
        
        # Create default config if not exists
        if not os.path.exists(config_path):
            self.create_default_config()
        
        # Load config
        self.config.read(config_path)
        self.validate_config()
    
    def create_default_config(self):
        """Create a new config file with default values"""
        self.config = configparser.ConfigParser()
        
        for section, options in DEFAULT_CONFIG.items():
            self.config[section] = {}
            for option, value in options.items():
                self.config[section][option] = value
        
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
        self.logger.info(f"Created default config at {self.config_path}")
    
    def validate_config(self):
        """Check if all required options are in config, add defaults if missing"""
        modified = False
        
        for section, options in DEFAULT_CONFIG.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
                modified = True
                
            for option, value in options.items():
                if not self.config.has_option(section, option):
                    self.config.set(section, option, value)
                    modified = True
        
        if modified:
            with open(self.config_path, 'w') as configfile:
                self.config.write(configfile)
            self.logger.info("Updated config with missing default values")
    
    def get(self, section, option, fallback=None):
        """Get config value with fallback"""
        return self.config.get(section, option, fallback=fallback)
    
    def getboolean(self, section, option, fallback=None):
        """Get boolean config value with fallback"""
        return self.config.getboolean(section, option, fallback=fallback)
    
    def getint(self, section, option, fallback=None):
        """Get integer config value with fallback"""
        return self.config.getint(section, option, fallback=fallback)
    
    def getfloat(self, section, option, fallback=None):
        """Get float config value with fallback"""
        return self.config.getfloat(section, option, fallback=fallback)
    
    def getlist(self, section, option, fallback=None, dtype=str):
        """Get list from comma-separated values"""
        try:
            value = self.config.get(section, option)
            items = [item.strip() for item in value.split(',')]
            return [dtype(item) for item in items if item]
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def set(self, section, option, value):
        """Set config value"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        self.config.set(section, option, str(value))
    
    def save(self):
        """Save config to file"""
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
        self.logger.info("Config saved")