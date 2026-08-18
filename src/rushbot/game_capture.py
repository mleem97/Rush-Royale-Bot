"""Versioned game captures with privacy-preserving sidecar manifests."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from rushbot.capture import write_bytes_atomic
from rushbot.game_version import (
    DEFAULT_GAME_PACKAGE,
    GameBuildInfo,
    PackageShellBackend,
    SupportDecision,
    SupportMatrix,
    inspect_game_build,
)


class ScreenshotProvider(Protocol):
    """Minimum screenshot capability required by a versioned game capture."""

    def capture(self, serial: str, output_path: str | Path | None = None) -> bytes:
        ...


_ALIAS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def anonymize_serial(serial: str) -> str:
    """Return a stable local alias without persisting the raw hardware/network serial."""

    candidate = serial.strip()
    if not candidate:
        raise ValueError("ADB serial must not be empty.")
    digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:12]
    return f"device-{digest}"


def validate_serial_alias(alias: str) -> str:
    candidate = alias.strip()
    if not _ALIAS_RE.fullmatch(candidate):
        raise ValueError(
            "Serial alias must be 1-64 characters using letters, digits, dot, dash, or underscore."
        )
    return candidate


@dataclass(frozen=True, slots=True)
class GameCaptureManifest:
    """Metadata sidecar for one PNG captured from a known Android package build."""

    frame_id: str
    captured_at: str
    serial_alias: str
    output_name: str
    byte_length: int
    sha256: str
    build: GameBuildInfo
    compatibility: SupportDecision

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "frame_id": self.frame_id,
            "captured_at": self.captured_at,
            "serial_alias": self.serial_alias,
            "capture_mode": "capture_only",
            "output_name": self.output_name,
            "byte_length": self.byte_length,
            "sha256": self.sha256,
            "game_build": self.build.as_dict(),
            "compatibility": {
                "status": self.compatibility.status.value,
                "reason": self.compatibility.reason,
                "rule_id": self.compatibility.rule_id,
                "maximum_runtime_mode": self.compatibility.maximum_runtime_mode.value,
                "live_actions_allowed": self.compatibility.live_actions_allowed,
            },
        }


@dataclass(frozen=True, slots=True)
class VersionedCapture:
    """Paths and manifest returned after a successful versioned capture."""

    image_path: Path
    metadata_path: Path
    manifest: GameCaptureManifest


def capture_game_frame(
    *,
    screenshot_provider: ScreenshotProvider,
    package_backend: PackageShellBackend,
    support_matrix: SupportMatrix,
    serial: str,
    output_path: str | Path,
    metadata_path: str | Path | None = None,
    serial_alias: str | None = None,
    package_name: str = DEFAULT_GAME_PACKAGE,
) -> VersionedCapture:
    """Capture a PNG and write a version/status manifest without storing the raw serial."""

    target_serial = serial.strip()
    if not target_serial:
        raise ValueError("ADB serial must not be empty.")
    destination = Path(output_path).expanduser().resolve()
    if destination.suffix.lower() != ".png":
        raise ValueError("Versioned game captures must use a .png output path.")

    sidecar = (
        Path(metadata_path).expanduser().resolve()
        if metadata_path is not None
        else destination.with_name(f"{destination.name}.json")
    )
    if sidecar == destination:
        raise ValueError("Metadata path must not overwrite the PNG capture.")
    if sidecar.suffix.lower() != ".json":
        raise ValueError("Versioned capture metadata must use a .json path.")
    alias = validate_serial_alias(serial_alias) if serial_alias else anonymize_serial(target_serial)

    build = inspect_game_build(package_backend, target_serial, package_name)
    decision = support_matrix.evaluate(build)
    payload = screenshot_provider.capture(target_serial, destination)
    digest = hashlib.sha256(payload).hexdigest()
    captured_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    manifest = GameCaptureManifest(
        frame_id=f"sha256:{digest}",
        captured_at=captured_at,
        serial_alias=alias,
        output_name=destination.name,
        byte_length=len(payload),
        sha256=digest,
        build=build,
        compatibility=decision,
    )
    serialized = json.dumps(
        manifest.as_dict(),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8") + b"\n"
    write_bytes_atomic(sidecar, serialized)
    return VersionedCapture(
        image_path=destination,
        metadata_path=sidecar,
        manifest=manifest,
    )
