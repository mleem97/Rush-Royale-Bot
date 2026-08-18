"""Deterministic screenshot and optional Linux V4L2 frame sources."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Protocol

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class CaptureError(RuntimeError):
    """Raised when a captured frame is empty or malformed."""


def validate_png(payload: bytes) -> None:
    if len(payload) < 32 or not payload.startswith(PNG_SIGNATURE):
        raise CaptureError("ADB screencap did not return a valid PNG image.")


def write_bytes_atomic(path: str | os.PathLike[str], payload: bytes) -> Path:
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(file_descriptor, "wb") as temporary_file:
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        Path(temporary_name).replace(destination)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise
    return destination


class ScreenshotBackend(Protocol):
    """Minimum capture capability required from an Android target backend."""

    def screencap_png(self, serial: str) -> bytes: ...


class AdbScreenshotProvider:
    """Portable baseline capture using ``adb exec-out screencap -p``."""

    def __init__(self, backend: ScreenshotBackend) -> None:
        self.backend = backend

    def capture(self, serial: str, output_path: str | os.PathLike[str] | None = None) -> bytes:
        payload = self.backend.screencap_png(serial)
        validate_png(payload)
        if output_path is not None:
            write_bytes_atomic(output_path, payload)
        return payload


class V4L2FrameSource:
    """Read scrcpy's Linux V4L2 sink through OpenCV.

    OpenCV is imported only when this optional source is opened, so device-management
    commands remain usable even in a minimal environment.
    """

    def __init__(self, device_path: str = "/dev/video10") -> None:
        if not sys.platform.startswith("linux"):
            raise CaptureError("V4L2 frame capture is available only on Linux.")
        if not device_path.startswith("/dev/video"):
            raise ValueError("V4L2 device must look like /dev/videoN.")
        self.device_path = device_path
        self._capture: Any | None = None

    def open(self) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise CaptureError("opencv-python is required for V4L2 frame capture.") from exc
        self._capture = cv2.VideoCapture(self.device_path, cv2.CAP_V4L2)
        if not self._capture.isOpened():
            self._capture.release()
            self._capture = None
            raise CaptureError(f"Could not open V4L2 source: {self.device_path}")

    def read(self) -> Any:
        if self._capture is None:
            self.open()
        success, frame = self._capture.read()
        if not success or frame is None:
            raise CaptureError(f"Could not read a frame from {self.device_path}")
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> V4L2FrameSource:
        self.open()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
