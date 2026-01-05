"""Rush Royale Bot - Source Package

Python 3.13 Compatible
Enables 'Src' as a package for imports.
"""
from __future__ import annotations

__version__ = "2.0.0"
__author__ = "Rush Royale Bot Contributors"
__python_requires__ = ">=3.13"

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__python_requires__",
    # Core modules
    "bot_core",
    "bot_core_modern",
    "bot_handler", 
    "bot_logger",
    "bot_perception",
    "config_validator",
    "gui",
    "gui_modern",
    "port_scan",
    # New modular components
    "adb_controller",
    "screen_capture",
]
