from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

import rushbot.capture as capture_module
from rushbot.capture import CaptureError, V4L2FrameSource, write_bytes_atomic


def test_atomic_write_cleans_temporary_file_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "output.bin"
    original_replace = capture_module.Path.replace

    def fail_replace(self: Path, target: Path) -> Path:
        if self.name.endswith(".tmp"):
            raise OSError("replace failed")
        return original_replace(self, target)

    monkeypatch.setattr(capture_module.Path, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        write_bytes_atomic(destination, b"payload")
    assert list(tmp_path.iterdir()) == []


def test_v4l2_constructor_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(capture_module.sys, "platform", "win32")
    with pytest.raises(CaptureError, match="only on Linux"):
        V4L2FrameSource()

    monkeypatch.setattr(capture_module.sys, "platform", "linux")
    with pytest.raises(ValueError, match="/dev/video"):
        V4L2FrameSource("camera0")


class FakeVideoCapture:
    def __init__(
        self,
        opened: bool = True,
        reads: list[tuple[bool, object | None]] | None = None,
    ) -> None:
        self.opened = opened
        self.reads = list(reads or [(True, {"frame": 1})])
        self.released = False

    def isOpened(self) -> bool:  # noqa: N802 - OpenCV API spelling
        return self.opened

    def read(self) -> tuple[bool, object | None]:
        return self.reads.pop(0)

    def release(self) -> None:
        self.released = True


def install_fake_cv2(monkeypatch: pytest.MonkeyPatch, capture: FakeVideoCapture) -> None:
    fake_cv2 = types.SimpleNamespace(
        CAP_V4L2=200,
        VideoCapture=lambda path, backend: capture,
    )
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)


def test_v4l2_open_read_close_and_context(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_capture = FakeVideoCapture(reads=[(True, "frame")])
    install_fake_cv2(monkeypatch, fake_capture)
    source = V4L2FrameSource("/dev/video10")

    with source as entered:
        assert entered.read() == "frame"
    assert fake_capture.released
    assert source._capture is None


def test_v4l2_open_and_read_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    not_opened = FakeVideoCapture(opened=False)
    install_fake_cv2(monkeypatch, not_opened)
    source = V4L2FrameSource("/dev/video10")
    with pytest.raises(CaptureError, match="Could not open"):
        source.open()
    assert not_opened.released

    failed_read = FakeVideoCapture(reads=[(False, None)])
    install_fake_cv2(monkeypatch, failed_read)
    source = V4L2FrameSource("/dev/video10")
    with pytest.raises(CaptureError, match="Could not read"):
        source.read()
    source.close()
