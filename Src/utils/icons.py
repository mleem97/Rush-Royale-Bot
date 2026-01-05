"""
Rush Royale Bot - Icon Utilities
Python 3.13 Compatible

Provides Lucide icons for the GUI with fallback to Unicode symbols.
Uses CTkImage for high-DPI display support.
"""
from __future__ import annotations

import io
import logging
from functools import lru_cache
from typing import TYPE_CHECKING

# Try to import CTk for images
try:
    import customtkinter as ctk
    from PIL import Image
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False

# Try to import cairosvg for SVG rendering
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False

if TYPE_CHECKING:
    from customtkinter import CTkImage

logger = logging.getLogger(__name__)


# Icon mapping: name -> (lucide_name, unicode_fallback)
ICON_MAP = {
    # Navigation & Actions
    'play': ('Play', '▶'),
    'stop': ('Square', '⏹'),
    'pause': ('Pause', '⏸'),
    'settings': ('Settings', '⚙'),
    'power': ('Power', '⏻'),
    'exit': ('DoorOpen', '🚪'),
    'home': ('Home', '🏠'),
    
    # Bot Controls
    'bot': ('Bot', '🤖'),
    'start': ('Play', '▶'),
    'running': ('Activity', '⚡'),
    'stopped': ('CircleStop', '⏹'),
    
    # Game Related
    'game': ('Gamepad2', '🎮'),
    'dungeon': ('Castle', '🏰'),
    'battle': ('Swords', '⚔'),
    'mana': ('Coins', '💰'),
    'unit': ('Users', '👥'),
    'merge': ('Merge', '🔀'),
    
    # UI Elements
    'grid': ('Grid3x3', '📊'),
    'chart': ('ChartBar', '📈'),
    'log': ('ScrollText', '📜'),
    'info': ('Info', 'ℹ'),
    'warning': ('TriangleAlert', '⚠'),
    'error': ('CircleX', '❌'),
    'success': ('CircleCheck', '✓'),
    
    # Theme
    'sun': ('Sun', '☀'),
    'moon': ('Moon', '🌙'),
    'theme': ('Palette', '🎨'),
    
    # Misc
    'refresh': ('RefreshCw', '🔄'),
    'save': ('Save', '💾'),
    'load': ('FolderOpen', '📂'),
    'config': ('SlidersHorizontal', '⚙'),
}


class IconProvider:
    """
    Provides icons for the GUI using Lucide with Unicode fallback.
    
    Features:
    - Lucide SVG icons when available (Python 3.12+)
    - Unicode symbol fallback for older Python versions
    - CTkImage support for high-DPI displays
    - Caching for performance
    """
    
    def __init__(self, default_size: int = 20, default_color: str = '#ffffff'):
        """
        Initialize icon provider.
        
        Args:
            default_size: Default icon size in pixels
            default_color: Default icon color (hex)
        """
        self.default_size = default_size
        self.default_color = default_color
        self._lucide_available = self._check_lucide()
        
        if self._lucide_available:
            logger.info("Lucide icons available")
        else:
            logger.info("Using Unicode fallback for icons")
    
    def _check_lucide(self) -> bool:
        """Check if Lucide library is available and working."""
        try:
            import lucide
            # Lucide needs a web context, so we can't use it directly
            # We'll use the SVG data from the library
            return CAIROSVG_AVAILABLE
        except ImportError:
            return False
    
    @lru_cache(maxsize=128)
    def get_icon_text(self, name: str) -> str:
        """
        Get Unicode text representation of an icon.
        
        Args:
            name: Icon name from ICON_MAP
            
        Returns:
            Unicode character for the icon
        """
        if name in ICON_MAP:
            return ICON_MAP[name][1]
        return '•'  # Default bullet
    
    def get_icon_image(
        self, 
        name: str, 
        size: int | None = None,
        color: str | None = None
    ) -> 'CTkImage | None':
        """
        Get CTkImage for an icon (if available).
        
        Args:
            name: Icon name from ICON_MAP
            size: Icon size in pixels
            color: Icon color (hex)
            
        Returns:
            CTkImage if available, None otherwise
        """
        if not CTK_AVAILABLE:
            return None
        
        size = size or self.default_size
        color = color or self.default_color
        
        # Try to render Lucide icon
        if self._lucide_available and name in ICON_MAP:
            lucide_name = ICON_MAP[name][0]
            svg_data = self._get_lucide_svg(lucide_name, size, color)
            if svg_data:
                return self._svg_to_ctk_image(svg_data, size)
        
        return None
    
    def _get_lucide_svg(self, icon_name: str, size: int, color: str) -> bytes | None:
        """Get SVG data for a Lucide icon."""
        try:
            # Build SVG manually from Lucide icon data
            # This is a workaround since lucide-py is designed for web frameworks
            import lucide
            
            # Get the icon class
            icon_cls = getattr(lucide, icon_name, None)
            if icon_cls is None:
                return None
            
            # Lucide icons are defined with path data
            # We need to extract the SVG content
            # For now, return None and use fallback
            return None
            
        except Exception as e:
            logger.debug(f"Failed to get Lucide SVG for {icon_name}: {e}")
            return None
    
    def _svg_to_ctk_image(self, svg_data: bytes, size: int) -> 'CTkImage | None':
        """Convert SVG bytes to CTkImage."""
        if not CAIROSVG_AVAILABLE:
            return None
        
        try:
            # Convert SVG to PNG
            png_data = cairosvg.svg2png(
                bytestring=svg_data,
                output_width=size,
                output_height=size
            )
            
            # Create PIL Image
            pil_image = Image.open(io.BytesIO(png_data))
            
            # Create CTkImage for high-DPI support
            return ctk.CTkImage(
                light_image=pil_image,
                dark_image=pil_image,
                size=(size, size)
            )
            
        except Exception as e:
            logger.debug(f"Failed to convert SVG to image: {e}")
            return None


# Global icon provider instance
_icon_provider: IconProvider | None = None


def get_icon_provider() -> IconProvider:
    """Get the global icon provider instance."""
    global _icon_provider
    if _icon_provider is None:
        _icon_provider = IconProvider()
    return _icon_provider


def icon(name: str) -> str:
    """
    Get Unicode icon text.
    
    Convenience function for quick icon access.
    
    Args:
        name: Icon name (e.g., 'play', 'settings', 'game')
        
    Returns:
        Unicode character for the icon
    
    Example:
        >>> label = f"{icon('play')} Start Bot"
        >>> print(label)  # "▶ Start Bot"
    """
    return get_icon_provider().get_icon_text(name)


def icon_image(name: str, size: int = 20, color: str = '#ffffff') -> 'CTkImage | None':
    """
    Get CTkImage for an icon.
    
    Args:
        name: Icon name (e.g., 'play', 'settings', 'game')
        size: Icon size in pixels
        color: Icon color (hex)
        
    Returns:
        CTkImage if available, None otherwise
    """
    return get_icon_provider().get_icon_image(name, size, color)
