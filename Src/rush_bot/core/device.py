"""
RushBot Core - Device Manager
ADB and scrcpy device communication.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from rush_bot import PROJECT_ROOT


class DeviceManager:
    """Manages ADB device communication."""

    def __init__(self) -> None:
        """Initialize device manager."""
        self.device = None
        self.client = None
        self._setup_adb()

    def _setup_adb(self) -> None:
        """Setup ADB connection."""
        # Determine ADB path based on OS
        if os.name == 'nt':  # Windows
            adb_path = PROJECT_ROOT / ".scrcpy" / "adb.exe"
            if not adb_path.exists():
                adb_path = Path("adb")  # Fall back to PATH
        else:  # Linux/macOS
            adb_path = Path("adb")
        
        self.adb_path = adb_path

    def connect(self, address: str = "127.0.0.1:5555") -> bool:
        """Connect to an ADB device.
        
        Args:
            address: Device address (IP:port or serial).
            
        Returns:
            True if connection successful.
        """
        try:
            from adbutils import adb
            
            # Try to connect
            if ":" in address:
                adb.connect(address)
            
            devices = adb.device_list()
            if devices:
                self.device = devices[0]
                return True
            return False
        except Exception:
            return False

    def tap(self, x: int, y: int) -> None:
        """Tap at screen coordinates.
        
        Args:
            x: X coordinate.
            y: Y coordinate.
        """
        if self.device:
            self.device.click(x, y)

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 300
    ) -> None:
        """Swipe from (x1,y1) to (x2,y2).
        
        Args:
            x1, y1: Start coordinates.
            x2, y2: End coordinates.
            duration_ms: Duration in milliseconds.
        """
        if self.device:
            self.device.swipe(x1, y1, x2, y2, duration_ms / 1000)

    def screenshot(self) -> Any:
        """Capture device screenshot.
        
        Returns:
            Screenshot as PIL Image.
        """
        if self.device:
            return self.device.screenshot()
        return None

    def list_devices(self) -> list[str]:
        """List connected ADB devices.
        
        Returns:
            List of device serials.
        """
        try:
            from adbutils import adb
            return [d.serial for d in adb.device_list()]
        except Exception:
            return []
