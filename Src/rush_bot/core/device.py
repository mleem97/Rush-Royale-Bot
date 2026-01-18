"""
RushBot Core - Device Manager
ADB and scrcpy device communication with auto-reconnect capability.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from threading import Lock
from threading import Thread
from typing import TYPE_CHECKING
from typing import Any

from rush_bot import PROJECT_ROOT

if TYPE_CHECKING:
    from PIL import Image


logger = logging.getLogger(__name__)


class DeviceState(Enum):
    """Device connection states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class DeviceConfig:
    """Configuration for DeviceManager."""

    address: str = "127.0.0.1:5555"
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 5
    reconnect_delay_seconds: float = 2.0
    connection_timeout_seconds: float = 10.0
    screenshot_retry_count: int = 3
    screenshot_retry_delay: float = 0.5


@dataclass
class DeviceInfo:
    """Information about connected device."""

    serial: str
    model: str = ""
    android_version: str = ""
    screen_width: int = 0
    screen_height: int = 0
    is_emulator: bool = False

    @classmethod
    def from_device(cls, device: Any) -> DeviceInfo:
        """Create DeviceInfo from adbutils device.

        Args:
            device: adbutils device object.

        Returns:
            DeviceInfo instance.
        """
        serial = device.serial
        is_emulator = serial.startswith("emulator") or serial.startswith("127.0.0.1")

        # Get device properties safely
        try:
            model = device.prop.get("ro.product.model", "Unknown")
        except Exception:
            model = "Unknown"

        try:
            android_version = device.prop.get("ro.build.version.release", "Unknown")
        except Exception:
            android_version = "Unknown"

        # Get screen size from window manager
        screen_width = 0
        screen_height = 0
        try:
            wm_size = device.shell("wm size")
            if "Physical size:" in wm_size:
                size_str = wm_size.split("Physical size:")[1].strip().split()[0]
                width, height = size_str.split("x")
                screen_width = int(width)
                screen_height = int(height)
        except Exception:
            pass

        return cls(
            serial=serial,
            model=model,
            android_version=android_version,
            screen_width=screen_width,
            screen_height=screen_height,
            is_emulator=is_emulator,
        )


class DeviceConnectionError(Exception):
    """Raised when device connection fails."""


class DeviceNotConnectedError(Exception):
    """Raised when operation requires connected device."""


class DeviceManager:
    """Manages ADB device communication with auto-reconnect.

    Features:
    - Automatic reconnection on connection loss
    - Connection state tracking
    - Screenshot retry on failure
    - Thread-safe operations
    - Device info retrieval

    Example:
        >>> manager = DeviceManager(DeviceConfig(auto_reconnect=True))
        >>> manager.connect("127.0.0.1:5555")
        True
        >>> manager.tap(500, 500)
        >>> screenshot = manager.screenshot()
    """

    def __init__(
        self,
        config: DeviceConfig | None = None,
        on_state_change: Callable[[DeviceState], None] | None = None,
    ) -> None:
        """Initialize device manager.

        Args:
            config: Device configuration. Uses defaults if None.
            on_state_change: Callback for state changes.
        """
        self.config = config or DeviceConfig()
        self._on_state_change = on_state_change

        self._device: Any = None
        self._client: Any = None
        self._state = DeviceState.DISCONNECTED
        self._device_info: DeviceInfo | None = None
        self._lock = Lock()
        self._reconnect_thread: Thread | None = None
        self._should_stop_reconnect = False
        self._reconnect_attempt = 0
        self._last_address: str = ""

        self._setup_adb()

    def _setup_adb(self) -> None:
        """Setup ADB connection."""
        # Determine ADB path based on OS
        if os.name == "nt":  # Windows
            adb_path = PROJECT_ROOT / ".scrcpy" / "adb.exe"
            if not adb_path.exists():
                adb_path = Path("adb")  # Fall back to PATH
        else:  # Linux/macOS
            adb_path = Path("adb")

        self.adb_path = adb_path

    @property
    def state(self) -> DeviceState:
        """Get current device state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._state == DeviceState.CONNECTED

    @property
    def device_info(self) -> DeviceInfo | None:
        """Get connected device info."""
        return self._device_info

    @property
    def device(self) -> Any:
        """Get raw adbutils device object."""
        return self._device

    def _set_state(self, state: DeviceState) -> None:
        """Set device state and notify callback.

        Args:
            state: New device state.
        """
        if self._state != state:
            old_state = self._state
            self._state = state
            logger.debug(f"Device state changed: {old_state.value} -> {state.value}")
            if self._on_state_change:
                try:
                    self._on_state_change(state)
                except Exception as e:
                    logger.warning(f"State change callback error: {e}")

    def connect(self, address: str | None = None) -> bool:
        """Connect to an ADB device.

        Args:
            address: Device address (IP:port or serial). Uses config default if None.

        Returns:
            True if connection successful.

        Raises:
            DeviceConnectionError: If connection fails and auto_reconnect is disabled.
        """
        with self._lock:
            address = address or self.config.address
            self._last_address = address
            self._set_state(DeviceState.CONNECTING)
            self._should_stop_reconnect = False

            try:
                from adbutils import adb

                # Try to connect if it's a network address
                if ":" in address:
                    logger.info(f"Connecting to {address}...")
                    adb.connect(address, timeout=self.config.connection_timeout_seconds)

                # Find device
                devices = adb.device_list()
                target_device = None

                for device in devices:
                    if device.serial == address or address in device.serial:
                        target_device = device
                        break

                # Fall back to first device
                if target_device is None and devices:
                    target_device = devices[0]
                    logger.info(f"Using first available device: {target_device.serial}")

                if target_device:
                    self._device = target_device
                    self._device_info = DeviceInfo.from_device(target_device)
                    self._set_state(DeviceState.CONNECTED)
                    self._reconnect_attempt = 0
                    logger.info(
                        f"Connected to {self._device_info.model} ({self._device_info.serial})"
                    )
                    return True

                logger.warning("No devices found")
                self._set_state(DeviceState.DISCONNECTED)
                return False

            except Exception as e:
                logger.error(f"Connection failed: {e}")
                self._set_state(DeviceState.ERROR)

                if self.config.auto_reconnect:
                    self._start_reconnect()
                    return False
                raise DeviceConnectionError(f"Failed to connect: {e}") from e

    def disconnect(self) -> None:
        """Disconnect from device."""
        with self._lock:
            self._should_stop_reconnect = True
            self._device = None
            self._device_info = None
            self._set_state(DeviceState.DISCONNECTED)
            logger.info("Disconnected from device")

    def _start_reconnect(self) -> None:
        """Start reconnection thread."""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return  # Already reconnecting

        self._reconnect_thread = Thread(target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()

    def _reconnect_loop(self) -> None:
        """Background reconnection loop."""
        self._set_state(DeviceState.RECONNECTING)

        while (
            not self._should_stop_reconnect
            and self._reconnect_attempt < self.config.max_reconnect_attempts
        ):
            self._reconnect_attempt += 1
            logger.info(
                f"Reconnect attempt {self._reconnect_attempt}/{self.config.max_reconnect_attempts}"
            )

            time.sleep(self.config.reconnect_delay_seconds)

            try:
                from adbutils import adb

                if ":" in self._last_address:
                    adb.connect(self._last_address, timeout=self.config.connection_timeout_seconds)

                devices = adb.device_list()
                for device in devices:
                    if device.serial == self._last_address or self._last_address in device.serial:
                        with self._lock:
                            self._device = device
                            self._device_info = DeviceInfo.from_device(device)
                            self._set_state(DeviceState.CONNECTED)
                            self._reconnect_attempt = 0
                        logger.info("Reconnected successfully")
                        return

            except Exception as e:
                logger.debug(f"Reconnect attempt failed: {e}")

        if not self._should_stop_reconnect:
            logger.error("Max reconnect attempts reached")
            self._set_state(DeviceState.ERROR)

    def _ensure_connected(self) -> None:
        """Ensure device is connected.

        Raises:
            DeviceNotConnectedError: If not connected.
        """
        if not self.is_connected or not self._device:
            raise DeviceNotConnectedError("Device not connected")

    def _handle_operation_error(self, operation: str, error: Exception) -> None:
        """Handle operation error, potentially triggering reconnect.

        Args:
            operation: Name of failed operation.
            error: Exception that occurred.
        """
        logger.error(f"{operation} failed: {error}")

        # Check if device is still reachable
        try:
            if self._device:
                self._device.shell("echo ping")
                return  # Device still works, was transient error
        except Exception:
            pass

        # Device unreachable, trigger reconnect
        self._set_state(DeviceState.RECONNECTING)
        if self.config.auto_reconnect:
            self._start_reconnect()

    def tap(self, x: int, y: int) -> bool:
        """Tap at screen coordinates.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            True if tap successful.
        """
        try:
            self._ensure_connected()
            self._device.click(x, y)
            logger.debug(f"Tap at ({x}, {y})")
            return True
        except DeviceNotConnectedError:
            return False
        except Exception as e:
            self._handle_operation_error("Tap", e)
            return False

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """Swipe from (x1,y1) to (x2,y2).

        Args:
            x1, y1: Start coordinates.
            x2, y2: End coordinates.
            duration_ms: Duration in milliseconds.

        Returns:
            True if swipe successful.
        """
        try:
            self._ensure_connected()
            self._device.swipe(x1, y1, x2, y2, duration_ms / 1000)
            logger.debug(f"Swipe from ({x1},{y1}) to ({x2},{y2})")
            return True
        except DeviceNotConnectedError:
            return False
        except Exception as e:
            self._handle_operation_error("Swipe", e)
            return False

    def screenshot(self) -> Image.Image | None:
        """Capture device screenshot with retry.

        Returns:
            Screenshot as PIL Image, or None if failed.
        """
        for attempt in range(self.config.screenshot_retry_count):
            try:
                self._ensure_connected()
                img = self._device.screenshot()
                logger.debug("Screenshot captured")
                return img
            except DeviceNotConnectedError:
                return None
            except Exception as e:
                if attempt < self.config.screenshot_retry_count - 1:
                    logger.debug(f"Screenshot retry {attempt + 1}: {e}")
                    time.sleep(self.config.screenshot_retry_delay)
                else:
                    self._handle_operation_error("Screenshot", e)

        return None

    def shell(self, command: str) -> str | None:
        """Execute shell command on device.

        Args:
            command: Shell command to execute.

        Returns:
            Command output, or None if failed.
        """
        try:
            self._ensure_connected()
            result = self._device.shell(command)
            logger.debug(f"Shell command: {command}")
            return result
        except DeviceNotConnectedError:
            return None
        except Exception as e:
            self._handle_operation_error("Shell", e)
            return None

    def input_text(self, text: str) -> bool:
        """Input text on device.

        Args:
            text: Text to input.

        Returns:
            True if successful.
        """
        try:
            self._ensure_connected()
            # Escape special characters for shell
            escaped = text.replace(" ", "%s").replace("'", "\\'")
            self._device.shell(f"input text '{escaped}'")
            logger.debug(f"Input text: {text}")
            return True
        except DeviceNotConnectedError:
            return False
        except Exception as e:
            self._handle_operation_error("Input text", e)
            return False

    def press_key(self, keycode: int) -> bool:
        """Press a key on device.

        Args:
            keycode: Android keycode (e.g., 4 for BACK, 3 for HOME).

        Returns:
            True if successful.
        """
        try:
            self._ensure_connected()
            self._device.shell(f"input keyevent {keycode}")
            logger.debug(f"Key press: {keycode}")
            return True
        except DeviceNotConnectedError:
            return False
        except Exception as e:
            self._handle_operation_error("Key press", e)
            return False

    def press_back(self) -> bool:
        """Press back button."""
        return self.press_key(4)

    def press_home(self) -> bool:
        """Press home button."""
        return self.press_key(3)

    def list_devices(self) -> list[str]:
        """List connected ADB devices.

        Returns:
            List of device serials.
        """
        try:
            from adbutils import adb

            return [d.serial for d in adb.device_list()]
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []

    def get_all_device_info(self) -> list[DeviceInfo]:
        """Get info for all connected devices.

        Returns:
            List of DeviceInfo for each connected device.
        """
        try:
            from adbutils import adb

            return [DeviceInfo.from_device(d) for d in adb.device_list()]
        except Exception as e:
            logger.error(f"Failed to get device info: {e}")
            return []
