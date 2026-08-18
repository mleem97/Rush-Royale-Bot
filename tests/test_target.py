from __future__ import annotations

from pathlib import Path

import pytest

from rushbot.adb import AndroidDevice
from rushbot.target import (
    REFERENCE_CANVAS,
    AdbAndroidTarget,
    FitMode,
    Insets,
    PixelPoint,
    Point,
    Rect,
    Rotation,
    ScreenGeometry,
    Size,
    TargetUnavailableError,
)


def test_reference_canvas_is_portrait_900_by_1600() -> None:
    assert REFERENCE_CANVAS == Size(900, 1600)


def test_identity_mapping_and_round_trip() -> None:
    geometry = ScreenGeometry.from_frame(REFERENCE_CANVAS)

    for source in (Point(0, 0), Point(450, 800), Point(899, 1599)):
        mapped = geometry.map_point(source)
        restored = geometry.unmap_point(mapped)
        assert restored.x == pytest.approx(source.x)
        assert restored.y == pytest.approx(source.y)


def test_scaled_portrait_mapping_hits_exact_edges() -> None:
    geometry = ScreenGeometry.from_frame(Size(1440, 2560))

    assert geometry.map_point(Point(0, 0)) == PixelPoint(0, 0)
    assert geometry.map_point(Point(899, 1599)) == PixelPoint(1439, 2559)
    assert geometry.map_point(Point(450, 800)) == PixelPoint(720, 1280)


def test_contain_mode_centers_reference_inside_tall_phone_frame() -> None:
    geometry = ScreenGeometry.from_frame(Size(1440, 3088), fit=FitMode.CONTAIN)

    assert geometry.content == Rect(left=0, top=264, width=1440, height=2560)
    assert geometry.map_point(Point(0, 0)) == PixelPoint(0, 264)
    assert geometry.map_point(Point(899, 1599)) == PixelPoint(1439, 2823)


def test_insets_are_removed_before_contain_calculation() -> None:
    geometry = ScreenGeometry.from_frame(
        Size(1500, 2800),
        fit=FitMode.CONTAIN,
        insets=Insets(left=30, top=100, right=30, bottom=140),
    )

    assert geometry.content == Rect(left=30, top=100, width=1440, height=2560)


def test_rotation_mapping() -> None:
    geometry_90 = ScreenGeometry.from_frame(
        Size(1600, 900),
        rotation=Rotation.DEG_90,
    )
    geometry_180 = ScreenGeometry.from_frame(
        REFERENCE_CANVAS,
        rotation=Rotation.DEG_180,
    )
    geometry_270 = ScreenGeometry.from_frame(
        Size(1600, 900),
        rotation=Rotation.DEG_270,
    )

    assert geometry_90.map_point(Point(0, 0)) == PixelPoint(1599, 0)
    assert geometry_180.map_point(Point(0, 0)) == PixelPoint(899, 1599)
    assert geometry_270.map_point(Point(0, 0)) == PixelPoint(0, 899)


def test_out_of_range_coordinates_reject_or_clamp() -> None:
    geometry = ScreenGeometry.from_frame(REFERENCE_CANVAS)

    with pytest.raises(ValueError, match="outside"):
        geometry.map_point(Point(-1, 10))
    with pytest.raises(ValueError, match="outside"):
        geometry.unmap_point(PixelPoint(900, 10))
    assert geometry.map_point(Point(-1, 5000), clamp=True) == PixelPoint(0, 1599)
    assert geometry.unmap_point(PixelPoint(-10, 5000), clamp=True) == Point(0, 1599)


@pytest.mark.parametrize(
    "constructor",
    [
        lambda: Size(0, 10),
        lambda: Rect(-1, 0, 10, 10),
        lambda: Rect(0, 0, 0, 10),
        lambda: Insets(left=-1),
    ],
)
def test_invalid_geometry_values(constructor: object) -> None:
    with pytest.raises(ValueError):
        constructor()  # type: ignore[operator]


def test_content_must_fit_frame_and_insets_must_leave_space() -> None:
    with pytest.raises(ValueError, match="inside the frame"):
        ScreenGeometry(frame=Size(100, 100), content=Rect(0, 0, 101, 100))
    with pytest.raises(ValueError):
        ScreenGeometry.from_frame(Size(100, 100), insets=Insets(left=50, right=50))


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.device_results = [AndroidDevice(serial="SERIAL", state="device")]

    def devices(self) -> list[AndroidDevice]:
        self.calls.append(("devices",))
        return self.device_results

    def screencap_png(self, serial: str) -> bytes:
        self.calls.append(("capture", serial))
        return b"\x89PNG\r\n\x1a\n" + b"x" * 64

    def tap(self, serial: str, x: int, y: int) -> None:
        self.calls.append(("tap", serial, x, y))

    def swipe(
        self,
        serial: str,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        *,
        duration_ms: int,
    ) -> None:
        self.calls.append(("swipe", serial, x1, y1, x2, y2, duration_ms))

    def keyevent(self, serial: str, keycode: int | str) -> None:
        self.calls.append(("keyevent", serial, keycode))

    def start_package(self, serial: str, package_name: str) -> str:
        self.calls.append(("start", serial, package_name))
        return "started"

    def force_stop_package(self, serial: str, package_name: str) -> None:
        self.calls.append(("stop", serial, package_name))


def make_target(backend: FakeBackend, *, clamp: bool = False) -> AdbAndroidTarget:
    return AdbAndroidTarget(
        backend,  # type: ignore[arg-type]
        "SERIAL",
        ScreenGeometry.from_frame(Size(1440, 2560)),
        clamp_coordinates=clamp,
    )


def test_adb_target_routes_capture_and_reference_input(tmp_path: Path) -> None:
    backend = FakeBackend()
    target = make_target(backend)
    screenshot = tmp_path / "frame.png"

    assert target.capture_png(screenshot).startswith(b"\x89PNG")
    assert screenshot.exists()
    assert target.tap_reference(Point(450, 800)) == PixelPoint(720, 1280)
    assert target.swipe_reference(
        Point(0, 0),
        Point(899, 1599),
        duration_ms=450,
    ) == (PixelPoint(0, 0), PixelPoint(1439, 2559))
    target.keyevent("BACK")
    assert target.start_package("com.example.game") == "started"
    target.force_stop_package("com.example.game")

    assert ("capture", "SERIAL") in backend.calls
    assert ("tap", "SERIAL", 720, 1280) in backend.calls
    assert ("swipe", "SERIAL", 0, 0, 1439, 2559, 450) in backend.calls
    assert ("keyevent", "SERIAL", "BACK") in backend.calls
    assert ("start", "SERIAL", "com.example.game") in backend.calls
    assert ("stop", "SERIAL", "com.example.game") in backend.calls


def test_adb_target_connection_validation() -> None:
    backend = FakeBackend()
    target = make_target(backend)

    assert target.find_device() == AndroidDevice(serial="SERIAL", state="device")
    assert target.require_online().online

    backend.device_results = [AndroidDevice(serial="SERIAL", state="unauthorized")]
    with pytest.raises(TargetUnavailableError, match="unauthorized"):
        target.require_online()

    backend.device_results = []
    with pytest.raises(TargetUnavailableError, match="not connected"):
        target.require_online()


def test_adb_target_validates_serial_duration_and_screenshot_name(tmp_path: Path) -> None:
    backend = FakeBackend()
    geometry = ScreenGeometry.from_frame(REFERENCE_CANVAS)

    with pytest.raises(ValueError, match="serial"):
        AdbAndroidTarget(backend, " ", geometry)  # type: ignore[arg-type]

    target = make_target(backend)
    with pytest.raises(ValueError, match="duration"):
        target.swipe_reference(Point(0, 0), Point(1, 1), duration_ms=-1)
    with pytest.raises(ValueError, match="file name"):
        target.screenshot_path(tmp_path, "..")
    assert target.screenshot_path(tmp_path, "capture").name == "capture.png"
    assert target.screenshot_path(tmp_path, "../capture.png").parent == tmp_path.resolve()
