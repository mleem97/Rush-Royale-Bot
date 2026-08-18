"""Transport-neutral Android target and coordinate calibration.

The legacy project encoded actions against a portrait 900 × 1600 reference canvas.
This module preserves that coordinate contract while allowing physical devices and
emulators to expose arbitrary resolutions, insets, letterboxing and display rotation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from rushbot.adb import AdbBackend, AndroidDevice
from rushbot.capture import AdbScreenshotProvider


class TargetUnavailableError(RuntimeError):
    """Raised when a configured Android target is missing or not online."""


class FitMode(StrEnum):
    """How the game viewport is derived from the available Android frame."""

    FULL_FRAME = "full-frame"
    CONTAIN = "contain"


class Rotation(IntEnum):
    """Clockwise rotation from the portrait reference canvas."""

    DEG_0 = 0
    DEG_90 = 90
    DEG_180 = 180
    DEG_270 = 270


@dataclass(frozen=True, slots=True)
class Size:
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Size dimensions must be positive.")

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height


REFERENCE_CANVAS = Size(900, 1600)


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class PixelPoint:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class Insets:
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0

    def __post_init__(self) -> None:
        if min(self.left, self.top, self.right, self.bottom) < 0:
            raise ValueError("Insets must not be negative.")


@dataclass(frozen=True, slots=True)
class Rect:
    left: int
    top: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.left < 0 or self.top < 0:
            raise ValueError("Rectangle origin must not be negative.")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Rectangle dimensions must be positive.")

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def inside(self, frame: Size) -> bool:
        return self.right <= frame.width and self.bottom <= frame.height


@dataclass(frozen=True, slots=True)
class ScreenGeometry:
    """Map the historical reference canvas to one concrete Android frame.

    ``content`` is the actual game viewport inside the screenshot. It may exclude
    status/navigation bars or letterboxing. Coordinates are mapped edge-to-edge so
    reference point ``(0, 0)`` and the final reference pixel map exactly to the
    corresponding content edges.
    """

    frame: Size
    content: Rect
    reference: Size = field(default=REFERENCE_CANVAS)
    rotation: Rotation = Rotation.DEG_0

    def __post_init__(self) -> None:
        if not self.content.inside(self.frame):
            raise ValueError("Content rectangle must be fully inside the frame.")

    @classmethod
    def from_frame(
        cls,
        frame: Size,
        *,
        fit: FitMode = FitMode.FULL_FRAME,
        insets: Insets = Insets(),
        reference: Size = REFERENCE_CANVAS,
        rotation: Rotation = Rotation.DEG_0,
    ) -> "ScreenGeometry":
        available = Rect(
            left=insets.left,
            top=insets.top,
            width=frame.width - insets.left - insets.right,
            height=frame.height - insets.top - insets.bottom,
        )
        if not available.inside(frame):
            raise ValueError("Insets leave no valid content rectangle inside the frame.")
        if fit is FitMode.FULL_FRAME:
            content = available
        elif fit is FitMode.CONTAIN:
            content = cls._contained_rect(available, reference, rotation)
        else:  # pragma: no cover - defensive against invalid enum construction
            raise ValueError(f"Unsupported fit mode: {fit}")
        return cls(frame=frame, content=content, reference=reference, rotation=rotation)

    @staticmethod
    def _contained_rect(available: Rect, reference: Size, rotation: Rotation) -> Rect:
        if rotation in (Rotation.DEG_90, Rotation.DEG_270):
            reference_ratio = reference.height / reference.width
        else:
            reference_ratio = reference.aspect_ratio
        available_ratio = available.width / available.height

        if available_ratio > reference_ratio:
            height = available.height
            width = min(available.width, round(height * reference_ratio))
            left = available.left + (available.width - width) // 2
            top = available.top
        else:
            width = available.width
            height = min(available.height, round(width / reference_ratio))
            left = available.left
            top = available.top + (available.height - height) // 2
        return Rect(left=left, top=top, width=width, height=height)

    def map_point(self, point: Point, *, clamp: bool = False) -> PixelPoint:
        x = self._reference_coordinate(point.x, self.reference.width, clamp=clamp)
        y = self._reference_coordinate(point.y, self.reference.height, clamp=clamp)
        u = self._to_unit(x, self.reference.width)
        v = self._to_unit(y, self.reference.height)
        u, v = self._rotate_unit(u, v, self.rotation)
        return PixelPoint(
            x=self.content.left + self._unit_to_pixel(u, self.content.width),
            y=self.content.top + self._unit_to_pixel(v, self.content.height),
        )

    def unmap_point(self, point: PixelPoint, *, clamp: bool = False) -> Point:
        x = self._content_coordinate(
            point.x,
            start=self.content.left,
            extent=self.content.width,
            clamp=clamp,
        )
        y = self._content_coordinate(
            point.y,
            start=self.content.top,
            extent=self.content.height,
            clamp=clamp,
        )
        u = self._to_unit(x - self.content.left, self.content.width)
        v = self._to_unit(y - self.content.top, self.content.height)
        u, v = self._unrotate_unit(u, v, self.rotation)
        return Point(
            x=u * max(self.reference.width - 1, 0),
            y=v * max(self.reference.height - 1, 0),
        )

    @staticmethod
    def _reference_coordinate(value: float, extent: int, *, clamp: bool) -> float:
        maximum = extent - 1
        if clamp:
            return min(max(value, 0.0), float(maximum))
        if not 0 <= value <= maximum:
            raise ValueError(f"Reference coordinate {value} is outside 0..{maximum}.")
        return value

    @staticmethod
    def _content_coordinate(value: int, *, start: int, extent: int, clamp: bool) -> int:
        maximum = start + extent - 1
        if clamp:
            return min(max(value, start), maximum)
        if not start <= value <= maximum:
            raise ValueError(f"Pixel coordinate {value} is outside {start}..{maximum}.")
        return value

    @staticmethod
    def _to_unit(value: float, extent: int) -> float:
        if extent <= 1:
            return 0.0
        return value / (extent - 1)

    @staticmethod
    def _unit_to_pixel(value: float, extent: int) -> int:
        if extent <= 1:
            return 0
        return round(value * (extent - 1))

    @staticmethod
    def _rotate_unit(u: float, v: float, rotation: Rotation) -> tuple[float, float]:
        if rotation is Rotation.DEG_0:
            return u, v
        if rotation is Rotation.DEG_90:
            return 1.0 - v, u
        if rotation is Rotation.DEG_180:
            return 1.0 - u, 1.0 - v
        if rotation is Rotation.DEG_270:
            return v, 1.0 - u
        raise ValueError(f"Unsupported rotation: {rotation}")

    @staticmethod
    def _unrotate_unit(u: float, v: float, rotation: Rotation) -> tuple[float, float]:
        if rotation is Rotation.DEG_0:
            return u, v
        if rotation is Rotation.DEG_90:
            return v, 1.0 - u
        if rotation is Rotation.DEG_180:
            return 1.0 - u, 1.0 - v
        if rotation is Rotation.DEG_270:
            return 1.0 - v, u
        raise ValueError(f"Unsupported rotation: {rotation}")


@runtime_checkable
class AndroidTarget(Protocol):
    """Minimum interface consumed by migrated game logic and action execution."""

    @property
    def serial(self) -> str:
        ...

    @property
    def geometry(self) -> ScreenGeometry:
        ...

    def capture_png(self, output_path: str | os.PathLike[str] | None = None) -> bytes:
        ...

    def tap_reference(self, point: Point) -> PixelPoint:
        ...

    def swipe_reference(
        self,
        start: Point,
        end: Point,
        *,
        duration_ms: int = 300,
    ) -> tuple[PixelPoint, PixelPoint]:
        ...

    def keyevent(self, keycode: int | str) -> None:
        ...

    def start_package(self, package_name: str) -> str:
        ...

    def force_stop_package(self, package_name: str) -> None:
        ...


class AdbAndroidTarget:
    """Android target backed by one exact serial on the official ADB server."""

    def __init__(
        self,
        backend: AdbBackend,
        serial: str,
        geometry: ScreenGeometry,
        *,
        clamp_coordinates: bool = False,
    ) -> None:
        normalized_serial = serial.strip()
        if not normalized_serial:
            raise ValueError("Android target serial must not be empty.")
        self.backend = backend
        self._serial = normalized_serial
        self._geometry = geometry
        self.clamp_coordinates = clamp_coordinates
        self._screenshots = AdbScreenshotProvider(backend)

    @property
    def serial(self) -> str:
        return self._serial

    @property
    def geometry(self) -> ScreenGeometry:
        return self._geometry

    def find_device(self) -> AndroidDevice | None:
        return next(
            (device for device in self.backend.devices() if device.serial == self.serial),
            None,
        )

    def require_online(self) -> AndroidDevice:
        device = self.find_device()
        if device is None:
            raise TargetUnavailableError(f"ADB target is not connected: {self.serial}")
        if not device.online:
            raise TargetUnavailableError(
                f"ADB target {self.serial} is not online; current state: {device.state}"
            )
        return device

    def capture_png(self, output_path: str | os.PathLike[str] | None = None) -> bytes:
        return self._screenshots.capture(self.serial, output_path)

    def tap_reference(self, point: Point) -> PixelPoint:
        mapped = self.geometry.map_point(point, clamp=self.clamp_coordinates)
        self.backend.tap(self.serial, mapped.x, mapped.y)
        return mapped

    def swipe_reference(
        self,
        start: Point,
        end: Point,
        *,
        duration_ms: int = 300,
    ) -> tuple[PixelPoint, PixelPoint]:
        if duration_ms < 0:
            raise ValueError("Swipe duration must not be negative.")
        mapped_start = self.geometry.map_point(start, clamp=self.clamp_coordinates)
        mapped_end = self.geometry.map_point(end, clamp=self.clamp_coordinates)
        self.backend.swipe(
            self.serial,
            mapped_start.x,
            mapped_start.y,
            mapped_end.x,
            mapped_end.y,
            duration_ms=duration_ms,
        )
        return mapped_start, mapped_end

    def keyevent(self, keycode: int | str) -> None:
        self.backend.keyevent(self.serial, keycode)

    def start_package(self, package_name: str) -> str:
        return self.backend.start_package(self.serial, package_name)

    def force_stop_package(self, package_name: str) -> None:
        self.backend.force_stop_package(self.serial, package_name)

    def screenshot_path(self, directory: str | os.PathLike[str], name: str) -> Path:
        """Return a sanitized, serial-independent path for a captured frame."""

        safe_name = Path(name).name
        if safe_name in {"", ".", ".."}:
            raise ValueError("Screenshot name must contain a file name.")
        if Path(safe_name).suffix.lower() != ".png":
            safe_name = f"{safe_name}.png"
        return Path(directory).expanduser().resolve() / safe_name
