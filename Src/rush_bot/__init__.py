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
