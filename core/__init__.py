#!/usr/bin/env python3
"""
Rush Royale Bot - Core Module
Modular bot architecture with clean separation of concerns
"""

__version__ = "3.0.0"
__author__ = "Rush Royale Bot Team"

# Core module exports
from .bot import RushRoyaleBot
from .device import DeviceManager, scan_for_devices, get_default_device
from .perception import PerceptionSystem, setup_unit_deck
from .logger import BotLogger, get_logger, setup_logging
from .config import ConfigManager, create_config_template

__all__ = [
    'RushRoyaleBot',
    'DeviceManager',
    'PerceptionSystem', 
    'BotLogger',
    'ConfigManager',
    'scan_for_devices',
    'get_default_device',
    'setup_unit_deck',
    'get_logger',
    'setup_logging',
    'create_config_template'
]
