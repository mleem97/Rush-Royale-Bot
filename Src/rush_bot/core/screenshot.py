"""
RushBot Core - Screenshot Pipeline
Optimized screenshot capture with scrcpy primary source and ADB fallback.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)


class ScreenshotSource(Enum):
    """Screenshot capture source."""

    SCRCPY = "scrcpy"
    ADB = "adb"
    BUFFER = "buffer"


@dataclass
class ScreenshotConfig:
    """Configuration for ScreenshotPipeline.

    Attributes:
        use_scrcpy: Whether to use scrcpy as primary source.
        scrcpy_max_width: Max width for scrcpy stream (lower = faster).
        scrcpy_bitrate: Bitrate for scrcpy stream.
        scrcpy_max_fps: Maximum FPS for scrcpy stream.
        fallback_to_adb: Whether to fall back to ADB on scrcpy failure.
        buffer_size: Number of frames to keep in buffer.
        target_latency_ms: Target latency in milliseconds.
        max_latency_ms: Maximum acceptable latency before warning.
        auto_select_source: Automatically select fastest source.
        scrcpy_startup_timeout: Timeout for scrcpy startup in seconds.
    """

    use_scrcpy: bool = True
    scrcpy_max_width: int = 800
    scrcpy_bitrate: int = 4_000_000
    scrcpy_max_fps: int = 60
    fallback_to_adb: bool = True
    buffer_size: int = 5
    target_latency_ms: float = 100.0
    max_latency_ms: float = 500.0
    auto_select_source: bool = True
    scrcpy_startup_timeout: float = 5.0


@dataclass
class ScreenshotResult:
    """Result of screenshot capture.

    Attributes:
        image: Captured image as numpy array (BGR format).
        source: Source used for capture.
        latency_ms: Capture latency in milliseconds.
        timestamp: Unix timestamp of capture.
        width: Image width in pixels.
        height: Image height in pixels.
    """

    image: np.ndarray
    source: ScreenshotSource
    latency_ms: float
    timestamp: float
    width: int
    height: int

    @property
    def resolution(self) -> tuple[int, int]:
        """Get resolution as (width, height) tuple."""
        return (self.width, self.height)


@dataclass
class LatencyStats:
    """Latency statistics for monitoring.

    Attributes:
        avg_latency_ms: Average latency in milliseconds.
        min_latency_ms: Minimum latency in milliseconds.
        max_latency_ms: Maximum latency in milliseconds.
        sample_count: Number of samples collected.
        source: Current screenshot source.
        scrcpy_available: Whether scrcpy is available.
        adb_available: Whether ADB is available.
    """

    avg_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    sample_count: int = 0
    source: ScreenshotSource = ScreenshotSource.ADB
    scrcpy_available: bool = False
    adb_available: bool = False


@dataclass
class _FrameBufferEntry:
    """Internal frame buffer entry."""

    frame: np.ndarray
    timestamp: float
    source: ScreenshotSource
    latency_ms: float


class ScreenshotPipeline:
    """Optimized screenshot capture pipeline.

    Features:
    - Scrcpy primary source for low-latency capture (<50ms)
    - ADB fallback for reliability
    - Frame buffer for consistent analysis
    - Latency monitoring and statistics
    - Automatic source selection based on performance

    Example:
        >>> from rush_bot.core import DeviceManager
        >>> device = DeviceManager()
        >>> device.connect()
        >>> pipeline = ScreenshotPipeline(device)
        >>> pipeline.start()
        >>> result = pipeline.capture()
        >>> print(f"Latency: {result.latency_ms:.1f}ms from {result.source.value}")
    """

    def __init__(
        self,
        device_manager: DeviceManager | None = None,
        config: ScreenshotConfig | None = None,
        on_frame: Callable[[ScreenshotResult], None] | None = None,
    ) -> None:
        """Initialize screenshot pipeline.

        Args:
            device_manager: DeviceManager instance for ADB fallback.
            config: Pipeline configuration. Uses defaults if None.
            on_frame: Optional callback for each captured frame.
        """
        self.config = config or ScreenshotConfig()
        self._device_manager = device_manager
        self._on_frame = on_frame

        # State
        self._is_running = False
        self._current_source = ScreenshotSource.ADB
        self._scrcpy_client: ScrcpyClient | None = None
        self._scrcpy_available = False
        self._adb_available = False

        # Frame buffer
        self._buffer: deque[_FrameBufferEntry] = deque(maxlen=self.config.buffer_size)
        self._buffer_lock = threading.Lock()
        self._last_frame: np.ndarray | None = None
        self._last_frame_time: float = 0.0

        # Latency tracking
        self._latency_samples: deque[float] = deque(maxlen=100)
        self._latency_lock = threading.Lock()

        # Scrcpy frame reception
        self._scrcpy_frame: np.ndarray | None = None
        self._scrcpy_frame_lock = threading.Lock()
        self._scrcpy_frame_time: float = 0.0

        logger.debug("ScreenshotPipeline initialized")

    @property
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._is_running

    @property
    def current_source(self) -> ScreenshotSource:
        """Get current screenshot source."""
        return self._current_source

    @property
    def has_scrcpy(self) -> bool:
        """Check if scrcpy is available."""
        return self._scrcpy_available

    @property
    def has_adb(self) -> bool:
        """Check if ADB is available."""
        return self._adb_available

    def set_device_manager(self, device_manager: DeviceManager) -> None:
        """Set or update the device manager.

        Args:
            device_manager: DeviceManager instance.
        """
        self._device_manager = device_manager
        self._check_adb_availability()

    def start(self) -> bool:
        """Start the screenshot pipeline.

        Returns:
            True if at least one source is available.
        """
        if self._is_running:
            logger.warning("Pipeline already running")
            return True

        logger.info("Starting screenshot pipeline...")

        # Check ADB availability
        self._check_adb_availability()

        # Try to start scrcpy if configured
        if self.config.use_scrcpy:
            self._start_scrcpy()

        # Determine best source
        if self._scrcpy_available:
            self._current_source = ScreenshotSource.SCRCPY
            logger.info("Using scrcpy as primary screenshot source")
        elif self._adb_available:
            self._current_source = ScreenshotSource.ADB
            logger.info("Using ADB as screenshot source (scrcpy unavailable)")
        else:
            logger.error("No screenshot source available")
            return False

        self._is_running = True
        logger.info(f"Screenshot pipeline started (source: {self._current_source.value})")
        return True

    def stop(self) -> None:
        """Stop the screenshot pipeline."""
        if not self._is_running:
            return

        logger.info("Stopping screenshot pipeline...")
        self._is_running = False

        # Stop scrcpy
        self._stop_scrcpy()

        # Clear buffer
        with self._buffer_lock:
            self._buffer.clear()
            self._last_frame = None

        logger.info("Screenshot pipeline stopped")

    def capture(self, use_buffer: bool = False) -> ScreenshotResult | None:
        """Capture a screenshot.

        Args:
            use_buffer: If True, return buffered frame if fresh enough.

        Returns:
            ScreenshotResult with image data, or None if capture failed.
        """
        if not self._is_running:
            # Try to capture anyway for one-shot use
            return self._capture_single()

        # Check buffer first if requested
        if use_buffer:
            buffered = self._get_from_buffer()
            if buffered is not None:
                return buffered

        # Capture from current source
        result = self._capture_from_source(self._current_source)

        # Fallback if primary source failed
        if result is None and self.config.fallback_to_adb:
            if self._current_source == ScreenshotSource.SCRCPY:
                logger.debug("Scrcpy capture failed, falling back to ADB")
                result = self._capture_from_source(ScreenshotSource.ADB)

                # If ADB works, consider switching
                if result is not None and self.config.auto_select_source:
                    self._handle_source_fallback()

        # Add to buffer
        if result is not None:
            self._add_to_buffer(result)
            self._record_latency(result.latency_ms)

            # Notify callback
            if self._on_frame:
                try:
                    self._on_frame(result)
                except Exception as e:
                    logger.warning(f"Frame callback error: {e}")

        return result

    def capture_numpy(self, use_buffer: bool = False) -> np.ndarray | None:
        """Capture screenshot as numpy array (BGR format).

        Convenience method that returns just the image.

        Args:
            use_buffer: If True, use buffered frame if available.

        Returns:
            Image as numpy array (BGR format), or None if failed.
        """
        result = self.capture(use_buffer=use_buffer)
        return result.image if result is not None else None

    def capture_pil(self, use_buffer: bool = False) -> Image.Image | None:
        """Capture screenshot as PIL Image (RGB format).

        Convenience method that returns a PIL Image.

        Args:
            use_buffer: If True, use buffered frame if available.

        Returns:
            PIL Image (RGB format), or None if failed.
        """
        result = self.capture(use_buffer=use_buffer)
        if result is None:
            return None

        try:
            import cv2
            from PIL import Image

            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(result.image, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb_image)
        except ImportError:
            logger.error("PIL not available")
            return None

    def get_latest_frame(self) -> np.ndarray | None:
        """Get the most recent frame from buffer without new capture.

        Returns:
            Latest frame as numpy array, or None if buffer empty.
        """
        with self._buffer_lock:
            if self._buffer:
                return self._buffer[-1].frame.copy()
            return self._last_frame.copy() if self._last_frame is not None else None

    def get_latency_stats(self) -> LatencyStats:
        """Get current latency statistics.

        Returns:
            LatencyStats with performance metrics.
        """
        with self._latency_lock:
            samples = list(self._latency_samples)

        if not samples:
            return LatencyStats(
                source=self._current_source,
                scrcpy_available=self._scrcpy_available,
                adb_available=self._adb_available,
            )

        return LatencyStats(
            avg_latency_ms=sum(samples) / len(samples),
            min_latency_ms=min(samples),
            max_latency_ms=max(samples),
            sample_count=len(samples),
            source=self._current_source,
            scrcpy_available=self._scrcpy_available,
            adb_available=self._adb_available,
        )

    def switch_source(self, source: ScreenshotSource) -> bool:
        """Manually switch screenshot source.

        Args:
            source: Target screenshot source.

        Returns:
            True if switch successful.
        """
        if source == ScreenshotSource.SCRCPY and not self._scrcpy_available:
            logger.warning("Cannot switch to scrcpy - not available")
            return False

        if source == ScreenshotSource.ADB and not self._adb_available:
            logger.warning("Cannot switch to ADB - not available")
            return False

        if source == ScreenshotSource.BUFFER:
            logger.warning("Cannot switch to buffer source directly")
            return False

        old_source = self._current_source
        self._current_source = source
        logger.info(f"Switched screenshot source: {old_source.value} -> {source.value}")
        return True

    def benchmark(self, iterations: int = 10) -> dict[ScreenshotSource, float]:
        """Benchmark available screenshot sources.

        Args:
            iterations: Number of captures per source.

        Returns:
            Dictionary mapping source to average latency in ms.
        """
        results: dict[ScreenshotSource, float] = {}

        # Benchmark scrcpy
        if self._scrcpy_available:
            latencies = []
            for _ in range(iterations):
                result = self._capture_from_source(ScreenshotSource.SCRCPY)
                if result:
                    latencies.append(result.latency_ms)
            if latencies:
                results[ScreenshotSource.SCRCPY] = sum(latencies) / len(latencies)

        # Benchmark ADB
        if self._adb_available:
            latencies = []
            for _ in range(iterations):
                result = self._capture_from_source(ScreenshotSource.ADB)
                if result:
                    latencies.append(result.latency_ms)
            if latencies:
                results[ScreenshotSource.ADB] = sum(latencies) / len(latencies)

        return results

    # --- Private Methods ---

    def _check_adb_availability(self) -> None:
        """Check if ADB screenshot is available."""
        if self._device_manager is None:
            self._adb_available = False
            return

        self._adb_available = self._device_manager.is_connected

    def _start_scrcpy(self) -> bool:
        """Start scrcpy client.

        Returns:
            True if scrcpy started successfully.
        """
        try:
            # Get device serial from device manager
            device_serial: str | None = None
            if self._device_manager and self._device_manager.device_info:
                device_serial = self._device_manager.device_info.serial

            self._scrcpy_client = ScrcpyClient(
                device=device_serial,
                max_width=self.config.scrcpy_max_width,
                bitrate=self.config.scrcpy_bitrate,
                max_fps=self.config.scrcpy_max_fps,
                on_frame=self._on_scrcpy_frame,
            )

            if self._scrcpy_client.start(timeout=self.config.scrcpy_startup_timeout):
                self._scrcpy_available = True
                logger.info("Scrcpy client started successfully")
                return True
            else:
                logger.warning("Scrcpy client failed to start")
                self._scrcpy_client = None
                self._scrcpy_available = False
                return False

        except Exception as e:
            logger.warning(f"Failed to start scrcpy: {e}")
            self._scrcpy_client = None
            self._scrcpy_available = False
            return False

    def _stop_scrcpy(self) -> None:
        """Stop scrcpy client."""
        if self._scrcpy_client:
            try:
                self._scrcpy_client.stop()
            except Exception as e:
                logger.debug(f"Error stopping scrcpy: {e}")
            finally:
                self._scrcpy_client = None
                self._scrcpy_available = False

    def _on_scrcpy_frame(self, frame: np.ndarray) -> None:
        """Callback for scrcpy frames.

        Args:
            frame: Frame as numpy array (BGR format).
        """
        with self._scrcpy_frame_lock:
            self._scrcpy_frame = frame
            self._scrcpy_frame_time = time.time()

    def _capture_single(self) -> ScreenshotResult | None:
        """Capture a single screenshot without pipeline running.

        Returns:
            ScreenshotResult or None.
        """
        # Try ADB if device manager available
        if self._device_manager and self._device_manager.is_connected:
            return self._capture_from_source(ScreenshotSource.ADB)
        return None

    def _capture_from_source(self, source: ScreenshotSource) -> ScreenshotResult | None:
        """Capture from specific source.

        Args:
            source: Screenshot source to use.

        Returns:
            ScreenshotResult or None if failed.
        """
        start_time = time.perf_counter()
        timestamp = time.time()

        if source == ScreenshotSource.SCRCPY:
            return self._capture_scrcpy(start_time, timestamp)
        elif source == ScreenshotSource.ADB:
            return self._capture_adb(start_time, timestamp)
        else:
            return None

    def _capture_scrcpy(self, start_time: float, timestamp: float) -> ScreenshotResult | None:
        """Capture from scrcpy.

        Args:
            start_time: Performance counter at capture start.
            timestamp: Unix timestamp.

        Returns:
            ScreenshotResult or None.
        """
        if not self._scrcpy_available or not self._scrcpy_client:
            return None

        with self._scrcpy_frame_lock:
            frame = self._scrcpy_frame

        if frame is None:
            return None

        latency_ms = (time.perf_counter() - start_time) * 1000

        return ScreenshotResult(
            image=frame.copy(),
            source=ScreenshotSource.SCRCPY,
            latency_ms=latency_ms,
            timestamp=timestamp,
            width=frame.shape[1],
            height=frame.shape[0],
        )

    def _capture_adb(self, start_time: float, timestamp: float) -> ScreenshotResult | None:
        """Capture from ADB.

        Args:
            start_time: Performance counter at capture start.
            timestamp: Unix timestamp.

        Returns:
            ScreenshotResult or None.
        """
        if not self._device_manager:
            return None

        try:
            pil_image = self._device_manager.screenshot()
            if pil_image is None:
                return None

            # Convert PIL to numpy BGR
            import cv2

            np_image = np.array(pil_image)

            # PIL returns RGB, convert to BGR for OpenCV compatibility
            if len(np_image.shape) == 3 and np_image.shape[2] == 3:
                np_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)

            latency_ms = (time.perf_counter() - start_time) * 1000

            return ScreenshotResult(
                image=np_image,
                source=ScreenshotSource.ADB,
                latency_ms=latency_ms,
                timestamp=timestamp,
                width=np_image.shape[1],
                height=np_image.shape[0],
            )

        except Exception as e:
            logger.debug(f"ADB capture failed: {e}")
            return None

    def _get_from_buffer(self) -> ScreenshotResult | None:
        """Get fresh frame from buffer.

        Returns:
            ScreenshotResult if fresh frame available, else None.
        """
        max_age_seconds = self.config.target_latency_ms / 1000.0

        with self._buffer_lock:
            if not self._buffer:
                return None

            latest = self._buffer[-1]
            age = time.time() - latest.timestamp

            if age <= max_age_seconds:
                return ScreenshotResult(
                    image=latest.frame.copy(),
                    source=ScreenshotSource.BUFFER,
                    latency_ms=age * 1000,
                    timestamp=latest.timestamp,
                    width=latest.frame.shape[1],
                    height=latest.frame.shape[0],
                )

        return None

    def _add_to_buffer(self, result: ScreenshotResult) -> None:
        """Add frame to buffer.

        Args:
            result: Screenshot result to buffer.
        """
        entry = _FrameBufferEntry(
            frame=result.image.copy(),
            timestamp=result.timestamp,
            source=result.source,
            latency_ms=result.latency_ms,
        )

        with self._buffer_lock:
            self._buffer.append(entry)
            self._last_frame = result.image.copy()
            self._last_frame_time = result.timestamp

    def _record_latency(self, latency_ms: float) -> None:
        """Record latency sample.

        Args:
            latency_ms: Latency in milliseconds.
        """
        with self._latency_lock:
            self._latency_samples.append(latency_ms)

        # Warn if latency is too high
        if latency_ms > self.config.max_latency_ms:
            logger.warning(f"High screenshot latency: {latency_ms:.1f}ms")

    def _handle_source_fallback(self) -> None:
        """Handle source fallback logic."""
        # If scrcpy keeps failing, try to restart it
        logger.info("Scrcpy source failed, attempting recovery...")

        # Stop and restart scrcpy
        self._stop_scrcpy()
        time.sleep(0.5)

        if self._start_scrcpy():
            self._current_source = ScreenshotSource.SCRCPY
            logger.info("Scrcpy recovered successfully")
        else:
            self._current_source = ScreenshotSource.ADB
            logger.warning("Scrcpy recovery failed, staying with ADB")


class ScrcpyClient:
    """Lightweight scrcpy client wrapper for screenshot pipeline.

    This is a simplified wrapper around the vendored scrcpy client,
    optimized for screenshot capture.
    """

    def __init__(
        self,
        device: str | None = None,
        max_width: int = 800,
        bitrate: int = 4_000_000,
        max_fps: int = 60,
        on_frame: Callable[[np.ndarray], None] | None = None,
    ) -> None:
        """Initialize scrcpy client.

        Args:
            device: Device serial (auto-detect if None).
            max_width: Maximum video width.
            bitrate: Video bitrate.
            max_fps: Maximum FPS.
            on_frame: Callback for each frame.
        """
        self.device = device
        self.max_width = max_width
        self.bitrate = bitrate
        self.max_fps = max_fps
        self._on_frame = on_frame

        self._client: Client | None = None
        self._is_connected = False
        self._last_frame: np.ndarray | None = None
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._is_connected

    @property
    def last_frame(self) -> np.ndarray | None:
        """Get last received frame."""
        with self._lock:
            return self._last_frame.copy() if self._last_frame is not None else None

    def start(self, timeout: float = 5.0) -> bool:
        """Start scrcpy client.

        Args:
            timeout: Connection timeout in seconds.

        Returns:
            True if started successfully.
        """
        try:
            # Import vendored scrcpy
            from scrcpy import Client

            self._client = Client(
                device=self.device,
                max_width=self.max_width,
                bitrate=self.bitrate,
                max_fps=self.max_fps,
                block_frame=False,
                stay_awake=True,
            )

            # Register frame callback
            self._client.add_listener("frame", self._handle_frame)  # type: ignore[union-attr]
            self._client.add_listener("init", self._handle_init)  # type: ignore[union-attr]
            self._client.add_listener("disconnect", self._handle_disconnect)  # type: ignore[union-attr]

            # Start in daemon thread
            self._client.start(daemon_threaded=True)  # type: ignore[union-attr]

            # Wait for connection
            start_time = time.time()
            while not self._is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            return self._is_connected

        except ImportError as e:
            logger.warning(f"Scrcpy not available: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to start scrcpy: {e}")
            return False

    def stop(self) -> None:
        """Stop scrcpy client."""
        if self._client:
            try:
                self._client.stop()
            except Exception:
                pass
            finally:
                self._client = None
                self._is_connected = False

    def _handle_frame(self, frame: np.ndarray | None) -> None:
        """Handle incoming frame.

        Args:
            frame: Frame data or None.
        """
        if frame is None:
            return

        with self._lock:
            self._last_frame = frame

        if self._on_frame:
            try:
                self._on_frame(frame)
            except Exception as e:
                logger.debug(f"Frame callback error: {e}")

    def _handle_init(self) -> None:
        """Handle connection init."""
        self._is_connected = True
        logger.debug("Scrcpy connected")

    def _handle_disconnect(self) -> None:
        """Handle disconnection."""
        self._is_connected = False
        logger.debug("Scrcpy disconnected")


# Type alias for DeviceManager import
if TYPE_CHECKING:
    from scrcpy import Client

    from rush_bot.core.device import DeviceManager
