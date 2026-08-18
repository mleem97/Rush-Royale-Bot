from __future__ import annotations

from pathlib import Path

import pytest

from rushbot.capture import AdbScreenshotProvider, CaptureError, validate_png


class FakeBackend:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.serials: list[str] = []

    def screencap_png(self, serial: str) -> bytes:
        self.serials.append(serial)
        return self.payload


def test_capture_valid_png_atomically(tmp_path: Path) -> None:
    payload = b"\x89PNG\r\n\x1a\n" + b"x" * 64
    backend = FakeBackend(payload)
    destination = tmp_path / "capture.png"

    result = AdbScreenshotProvider(backend).capture("emulator-5554", destination)

    assert result == payload
    assert destination.read_bytes() == payload
    assert backend.serials == ["emulator-5554"]


def test_invalid_screenshot_is_rejected() -> None:
    with pytest.raises(CaptureError):
        validate_png(b"not-a-png")
