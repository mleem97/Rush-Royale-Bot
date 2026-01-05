"""
Rush Royale Bot - Utils Package
Python 3.13 Compatible
"""
from __future__ import annotations

from .grid_utils import (
    get_grid,
    get_unit_count,
    preserve_unit,
    grid_meta_info,
    filter_units,
    adv_filter_keys,
    get_button_pos,
    read_knowledge,
    GRID_TOP_BOX,
    GRID_BOX_SIZE,
    GRID_HEIGHT,
    GRID_WIDTH,
)

__all__ = [
    'get_grid',
    'get_unit_count',
    'preserve_unit',
    'grid_meta_info',
    'filter_units',
    'adv_filter_keys',
    'get_button_pos',
    'read_knowledge',
    'GRID_TOP_BOX',
    'GRID_BOX_SIZE',
    'GRID_HEIGHT',
    'GRID_WIDTH',
    # Icons
    'icon',
    'icon_image',
    # Icon Detection
    'IconDetector',
    'DetectionConfig',
    'DetectionResult',
    'get_icon_detector',
]

# Import icon utilities
try:
    from .icons import icon, icon_image
except ImportError:
    # Fallback if icons module not available
    def icon(name: str) -> str:
        return '•'
    def icon_image(*args, **kwargs):
        return None

# Import icon detector
try:
    from .icon_detector import (
        IconDetector,
        DetectionConfig,
        DetectionResult,
        get_icon_detector,
    )
except ImportError:
    # Fallback if icon_detector not available
    IconDetector = None
    DetectionConfig = None
    DetectionResult = None
    get_icon_detector = None
