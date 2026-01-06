"""
Rush Royale Bot - Scrcpy Client Module
Python 3.11+ Compatible

Establishes connection to Android device via scrcpy.
Enables screenshot capture and touch input.
"""
from __future__ import annotations

import sys
import os
import logging
import threading
import time
from pathlib import Path
from typing import Optional, Callable, Any
import numpy as np

# Add scrcpy folder to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import local scrcpy client
try:
    from scrcpy import Client
    from scrcpy import const as scrcpy_const
    SCRCPY_AVAILABLE = True
except ImportError as e:
    SCRCPY_AVAILABLE = False
    Client = None
    scrcpy_const = None
    print(f"Warning: scrcpy not available: {e}")

logger = logging.getLogger(__name__)


class ScrcpyClientWrapper:
    """
    Wrapper class for scrcpy Client.
    
    Provides a simple interface for:
    - Screenshot capture
    - Touch events
    - Key events
    """
    
    # Events
    EVENT_FRAME = "frame"
    EVENT_INIT = "init"
    EVENT_DISCONNECT = "disconnect"
    
    def __init__(
        self,
        device: Optional[str] = None,
        max_width: int = 800,
        bitrate: int = 2_000_000,
        max_fps: int = 30,
        flip: bool = False,
        block_frame: bool = False,
        stay_awake: bool = True,
    ):
        """
        Initialize scrcpy client.
        
        Args:
            device: ADB Device Serial (e.g. 'emulator-5554')
            max_width: Maximum width of video stream
            bitrate: Video bitrate in bps
            max_fps: Maximum framerate
            flip: Flip image horizontally
            block_frame: Block until frame available
            stay_awake: Keep device awake
        """
        if not SCRCPY_AVAILABLE:
            raise RuntimeError("scrcpy Client not available. Please install dependencies.")
        
        self.device = device
        self.max_width = max_width
        self.bitrate = bitrate
        self.max_fps = max_fps
        self.flip = flip
        self.block_frame = block_frame
        self.stay_awake = stay_awake
        
        self._client: Optional[Client] = None
        self._last_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._connected = False
        self._frame_listeners: list[Callable] = []
        
        logger.info(f"ScrcpyClientWrapper initialized for device: {device or 'auto'}")
    
    def _on_frame(self, frame: np.ndarray) -> None:
        """Callback when a new frame is received."""
        with self._frame_lock:
            self._last_frame = frame
        
        # Notify all listeners
        for listener in self._frame_listeners:
            try:
                listener(frame)
            except Exception as e:
                logger.error(f"Frame listener error: {e}")
    
    def _on_init(self) -> None:
        """Callback when connection is established."""
        self._connected = True
        logger.info("scrcpy connection established")
    
    def _on_disconnect(self) -> None:
        """Callback when connection is disconnected."""
        self._connected = False
        logger.warning("scrcpy connection disconnected")
    
    def add_frame_listener(self, callback: Callable[[np.ndarray], None]) -> None:
        """Add a frame listener."""
        self._frame_listeners.append(callback)
    
    def remove_frame_listener(self, callback: Callable) -> None:
        """Remove a frame listener."""
        if callback in self._frame_listeners:
            self._frame_listeners.remove(callback)
    
    def start(self, threaded: bool = True) -> bool:
        """
        Start scrcpy client.
        
        Args:
            threaded: Whether client should run in separate thread
            
        Returns:
            True if successfully started
        """
        try:
            self._client = Client(
                device=self.device,
                max_width=self.max_width,
                bitrate=self.bitrate,
                max_fps=self.max_fps,
                flip=self.flip,
                block_frame=self.block_frame,
                stay_awake=self.stay_awake,
            )
            
            # Register event handlers
            self._client.add_listener(Client.EVENT_FRAME, self._on_frame)
            self._client.add_listener(Client.EVENT_INIT, self._on_init)
            self._client.add_listener(Client.EVENT_DISCONNECT, self._on_disconnect)
            
            logger.info("Starting scrcpy client...")
            self._client.start(threaded=threaded)
            
            # Wait briefly for connection
            timeout = 5.0
            start_time = time.time()
            while not self._connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self._connected:
                logger.info("scrcpy client started successfully")
                return True
            else:
                logger.warning("scrcpy client timeout - no connection")
                return False
                
        except Exception as e:
            logger.error(f"Error starting scrcpy client: {e}")
            return False
    
    def stop(self) -> None:
        """Stop scrcpy client."""
        if self._client:
            try:
                self._client.stop()
                logger.info("scrcpy client stopped")
            except Exception as e:
                logger.error(f"Error stopping: {e}")
            finally:
                self._client = None
                self._connected = False
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Return the last received frame.
        
        Returns:
            numpy array with image (RGB) or None
        """
        with self._frame_lock:
            if self._last_frame is not None:
                return self._last_frame.copy()
        return None
    
    def get_screenshot(self) -> Optional[np.ndarray]:
        """Alias for get_frame() - for compatibility."""
        return self.get_frame()
    
    @property
    def is_connected(self) -> bool:
        """Return whether client is connected."""
        return self._connected
    
    @property
    def resolution(self) -> Optional[tuple[int, int]]:
        """Return current resolution (width, height)."""
        frame = self.get_frame()
        if frame is not None:
            return (frame.shape[1], frame.shape[0])
        return None
    
    # Touch/Input methods
    def touch(self, x: int, y: int, action: int = 0) -> None:
        """
        Send a touch event.
        
        Args:
            x: X-coordinate
            y: Y-coordinate
            action: 0=DOWN, 1=UP, 2=MOVE (see scrcpy.const)
        """
        if self._client and self._connected:
            self._client.control.touch(x, y, action)
    
    def click(self, x: int, y: int, duration: float = 0.05) -> None:
        """
        Perform a click (touch down + up).
        
        Args:
            x: X-coordinate
            y: Y-coordinate
            duration: Delay between down and up in seconds
        """
        if self._client and self._connected:
            # ACTION_DOWN = 0, ACTION_UP = 1
            self._client.control.touch(x, y, 0)
            time.sleep(duration)
            self._client.control.touch(x, y, 1)
    
    def swipe(
        self, 
        start_x: int, 
        start_y: int, 
        end_x: int, 
        end_y: int, 
        duration: float = 0.3,
        steps: int = 10
    ) -> None:
        """
        Perform a swipe gesture.
        
        Args:
            start_x, start_y: Start position
            end_x, end_y: End position
            duration: Duration of gesture
            steps: Number of intermediate steps
        """
        if not self._client or not self._connected:
            return
        
        # Touch down
        self._client.control.touch(start_x, start_y, 0)
        
        # Movement in steps
        step_delay = duration / steps
        for i in range(1, steps + 1):
            progress = i / steps
            x = int(start_x + (end_x - start_x) * progress)
            y = int(start_y + (end_y - start_y) * progress)
            self._client.control.touch(x, y, 2)  # ACTION_MOVE
            time.sleep(step_delay)
        
        # Touch up
        self._client.control.touch(end_x, end_y, 1)
    
    def key(self, keycode: int, action: int = 0) -> None:
        """
        Send a key event.
        
        Args:
            keycode: Android keycode
            action: 0=DOWN, 1=UP
        """
        if self._client and self._connected:
            self._client.control.keycode(keycode, action)
    
    def back(self) -> None:
        """Send back key."""
        self.key(4)  # KEYCODE_BACK
        time.sleep(0.05)
        self.key(4, 1)
    
    def home(self) -> None:
        """Send home key."""
        self.key(3)  # KEYCODE_HOME
        time.sleep(0.05)
        self.key(3, 1)


# Singleton instance for easy access
_client_instance: Optional[ScrcpyClientWrapper] = None


def get_scrcpy_client(
    device: Optional[str] = None,
    auto_start: bool = True,
    **kwargs
) -> ScrcpyClientWrapper:
    """
    Return singleton instance of scrcpy client.
    
    Args:
        device: ADB Device Serial
        auto_start: Automatically start if not connected
        **kwargs: Additional parameters for ScrcpyClientWrapper
        
    Returns:
        ScrcpyClientWrapper instance
    """
    global _client_instance
    
    if _client_instance is None:
        _client_instance = ScrcpyClientWrapper(device=device, **kwargs)
    
    if auto_start and not _client_instance.is_connected:
        _client_instance.start(threaded=True)
    
    return _client_instance


def close_scrcpy_client() -> None:
    """Close singleton instance."""
    global _client_instance
    if _client_instance:
        _client_instance.stop()
        _client_instance = None


# Test/Debug
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    def on_frame(frame):
        print(f"Frame received: {frame.shape}")
    
    client = get_scrcpy_client(device="emulator-5554")
    client.add_frame_listener(on_frame)
    
    print("Client started. Press Ctrl+C to exit...")
    try:
        while True:
            time.sleep(1)
            frame = client.get_frame()
            if frame is not None:
                print(f"Current frame: {frame.shape}")
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        close_scrcpy_client()
