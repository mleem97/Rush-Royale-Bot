"""
Rush Royale Bot - ADB Controller Module
Python 3.13 Compatible

Handles all Android Debug Bridge (ADB) communication including:
- Device connection and management
- Touch input (tap, swipe)
- Key events
- App lifecycle management
"""
from __future__ import annotations

import time
import logging
from subprocess import Popen, DEVNULL
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ppadb.device import Device

# Try to import ADB client
try:
    from ppadb.client import Client as AdbClient
    ADB_AVAILABLE = True
except ImportError:
    ADB_AVAILABLE = False
    
    class AdbClient:
        """Fallback ADB client stub."""
        def __init__(self, host: str = '127.0.0.1', port: int = 5037):
            self.host = host
            self.port = port
        def devices(self) -> list:
            return []

# Touch action constants
class TouchConstants:
    """Constants for touch and key events."""
    ACTION_DOWN = 0
    ACTION_UP = 1
    KEYCODE_BACK = 4
    KEYCODE_HOME = 3
    KEYCODE_MENU = 82

const = TouchConstants()

# Default delay between actions
SLEEP_DELAY = 0.1


class ADBController:
    """
    Manages ADB device communication.
    
    Provides methods for:
    - Device connection
    - Touch input (tap, swipe)
    - Key events
    - Shell commands
    - App restart
    """
    
    def __init__(self, device_serial: str, logger: logging.Logger | None = None):
        """
        Initialize ADB controller.
        
        Args:
            device_serial: Device serial number (e.g., "127.0.0.1:5555")
            logger: Optional logger instance
        """
        self.device_serial = device_serial
        self.logger = logger or logging.getLogger(__name__)
        self.adb_client = AdbClient()
        self.adb_device: Device | None = None
        
        self._connect_device()
    
    def _connect_device(self) -> None:
        """Connect to the ADB device."""
        devices = self.adb_client.devices()
        
        # Find matching device
        for dev in devices:
            if dev.serial == self.device_serial:
                self.adb_device = dev
                self.logger.info(f"Connected to device: {self.device_serial}")
                return
        
        # Try to connect if not found
        self.shell(f'adb connect {self.device_serial}')
        devices = self.adb_client.devices()
        
        for dev in devices:
            if dev.serial == self.device_serial:
                self.adb_device = dev
                self.logger.info(f"Connected to device: {self.device_serial}")
                return
        
        raise ConnectionError(f"Could not connect to device: {self.device_serial}")
    
    @property
    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self.adb_device is not None
    
    def shell(self, cmd: str) -> str | None:
        """
        Execute ADB shell command.
        
        Args:
            cmd: Shell command to execute
            
        Returns:
            Command output or None
        """
        if self.adb_device:
            return self.adb_device.shell(cmd)
        else:
            # Fallback to system ADB
            p = Popen(
                ['adb', '-s', self.device_serial, 'shell', cmd],
                stdout=DEVNULL, stderr=DEVNULL
            )
            p.wait()
            return None
    
    def tap(self, x: int, y: int, delay_mult: float = 1.0) -> None:
        """
        Tap screen at coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            delay_mult: Delay multiplier after tap
        """
        if self.adb_device:
            self.adb_device.input_tap(x, y)
        else:
            self.shell(f'input tap {x} {y}')
        
        time.sleep(SLEEP_DELAY * delay_mult)
    
    # Alias for backward compatibility
    click = tap
    
    def tap_button(self, pos: tuple[int, int], offset: int = 10) -> None:
        """
        Tap button with offset and extra delay.
        
        Args:
            pos: Button position (x, y)
            offset: Pixel offset from position
        """
        x = pos[0] + offset
        y = pos[1] + offset
        self.tap(x, y)
        time.sleep(SLEEP_DELAY * 10)
    
    # Alias for backward compatibility
    click_button = tap_button
    
    def swipe(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        duration: int = 300
    ) -> None:
        """
        Swipe from start to end position.
        
        Args:
            start: Start position (x, y)
            end: End position (x, y)
            duration: Swipe duration in milliseconds
        """
        if self.adb_device:
            self.adb_device.input_swipe(
                start[0], start[1],
                end[0], end[1],
                duration
            )
        else:
            self.shell(
                f'input swipe {start[0]} {start[1]} {end[0]} {end[1]} {duration}'
            )
    
    def swipe_grid(
        self,
        start_grid: tuple[int, int],
        end_grid: tuple[int, int],
        grid_boxes: 'np.ndarray',
        offset: int = 60
    ) -> None:
        """
        Swipe between grid positions (for unit merging).
        
        Args:
            start_grid: Start grid position (row, col)
            end_grid: End grid position (row, col)
            grid_boxes: Grid coordinate array
            offset: Pixel offset from box edge
        """
        import numpy as np
        
        start_pos = grid_boxes[start_grid[0], start_grid[1]] + offset
        end_pos = grid_boxes[end_grid[0], end_grid[1]] + offset
        
        self.swipe(
            (int(start_pos[0]), int(start_pos[1])),
            (int(end_pos[0]), int(end_pos[1]))
        )
    
    def key_input(self, keycode: int) -> None:
        """
        Send key event.
        
        Args:
            keycode: Android keycode (use TouchConstants)
        """
        if self.adb_device:
            self.adb_device.input_keyevent(keycode)
        else:
            self.shell(f'input keyevent {keycode}')
    
    def press_back(self) -> None:
        """Press back button."""
        self.key_input(const.KEYCODE_BACK)
    
    def press_home(self) -> None:
        """Press home button."""
        self.key_input(const.KEYCODE_HOME)
    
    def launch_app(self, package: str = 'com.my.defense') -> None:
        """
        Launch application.
        
        Args:
            package: App package name
        """
        if self.adb_device:
            self.adb_device.shell(f'monkey -p {package} 1')
        else:
            self.shell(f'monkey -p {package} 1')
    
    def force_stop_app(self, package: str = 'com.my.defense') -> None:
        """
        Force stop application.
        
        Args:
            package: App package name
        """
        if self.adb_device:
            self.adb_device.shell(f'am force-stop {package}')
        else:
            self.shell(f'am force-stop {package}')
    
    def restart_app(
        self,
        package: str = 'com.my.defense',
        quick_disconnect: bool = False,
        load_time: float = 10.0
    ) -> None:
        """
        Restart the Rush Royale app.
        
        Args:
            package: App package name
            quick_disconnect: If True, spam disconnects to abandon match
            load_time: Wait time after app launch
        """
        if quick_disconnect:
            # Spam launch to force disconnect
            for _ in range(15):
                self.launch_app(package)
            return
        
        self.force_stop_app(package)
        time.sleep(2)
        self.launch_app(package)
        time.sleep(load_time)
    
    # Alias for backward compatibility
    restart_RR = restart_app
    
    def screencap(self) -> bytes | None:
        """
        Take screenshot using ADB.
        
        Returns:
            Screenshot bytes or None if failed
        """
        if self.adb_device:
            try:
                return self.adb_device.screencap()
            except Exception as e:
                self.logger.debug(f"ADB screencap failed: {e}")
        return None
