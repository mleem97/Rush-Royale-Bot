"""
RushBot - Automated Bot for Rush Royale.

A Python-based automation bot combining computer vision, machine learning,
and Android device control for Rush Royale gameplay automation.
"""

__version__ = "2026.1"
__author__ = "RushBot Team"

from pathlib import Path

# Package root directory
PACKAGE_ROOT = Path(__file__).parent
PROJECT_ROOT = PACKAGE_ROOT.parent.parent

# Asset directories
CV_IMAGES_DIR = PROJECT_ROOT / "cv-images"
ICONS_DIR = CV_IMAGES_DIR / "icons"
UNITS_DIR = CV_IMAGES_DIR / "all_units"

# Re-export core classes for convenient imports
from rush_bot.core import Bot
from rush_bot.core import BotHandler
from rush_bot.core import BotLogger
from rush_bot.core import DeviceManager
from rush_bot.core import MergeCandidate
from rush_bot.core import MergeConfig
from rush_bot.core import MergeLogic
from rush_bot.core import MergeResult
from rush_bot.core import MergeValidator

# Re-export perception classes
from rush_bot.perception import BotPerception
from rush_bot.perception import GridConfig
from rush_bot.perception import GridExtractor

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Paths
    "PACKAGE_ROOT",
    "PROJECT_ROOT",
    "CV_IMAGES_DIR",
    "ICONS_DIR",
    "UNITS_DIR",
    # Core classes
    "Bot",
    "BotHandler",
    "BotLogger",
    "DeviceManager",
    "MergeCandidate",
    "MergeConfig",
    "MergeLogic",
    "MergeResult",
    "MergeValidator",
    # Perception classes
    "BotPerception",
    "GridConfig",
    "GridExtractor",
]
