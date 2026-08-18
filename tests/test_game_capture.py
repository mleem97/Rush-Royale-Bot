from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest

from rushbot.game_capture import (
    anonymize_serial,
    capture_game_frame,
    validate_serial_alias,
)
from rushbot.game_version import SupportMatrix

DUMPSYS = dedent(
    """
      Package [com.my.defense] (abc):
        versionCode=3700123 minSdk=24 targetSdk=35
        versionName=37.0.1
        lastUpdateTime=2026-08-14 08:02:03
    """
)
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 64


class Backend:
    def shell(self, serial: str, arguments: list[str | int | float]) -> str:
        assert serial == "192.168.1.20:5555"
        assert arguments == ["dumpsys", "package", "com.my.defense"]
        return DUMPSYS


class Provider:
    def capture(self, serial: str, output_path: str | Path | None = None) -> bytes:
        assert serial == "192.168.1.20:5555"
        assert output_path is not None
        Path(output_path).write_bytes(PNG)
        return PNG


def test_anonymize_serial_is_stable_and_hides_source() -> None:
    first = anonymize_serial("192.168.1.20:5555")
    second = anonymize_serial("192.168.1.20:5555")

    assert first == second
    assert first.startswith("device-")
    assert "192.168" not in first


def test_capture_writes_versioned_sidecar_without_raw_serial(tmp_path: Path) -> None:
    matrix = SupportMatrix.from_toml(
        dedent(
            """
            schema_version = 1
            default_status = "capture_only"
            default_reason = "Unreviewed."

            [[builds]]
            id = "37-capture"
            package = "com.my.defense"
            version_name_prefix = "37."
            status = "capture_only"
            reason = "Capture baseline."
            """
        )
    )
    output = tmp_path / "frame.png"

    result = capture_game_frame(
        screenshot_provider=Provider(),
        package_backend=Backend(),
        support_matrix=matrix,
        serial="192.168.1.20:5555",
        output_path=output,
    )

    metadata_text = result.metadata_path.read_text(encoding="utf-8")
    metadata = json.loads(metadata_text)
    assert result.image_path.read_bytes() == PNG
    assert metadata["game_build"]["version_name"] == "37.0.1"
    assert metadata["game_build"]["version_code"] == 3_700_123
    assert metadata["compatibility"]["status"] == "capture_only"
    assert metadata["compatibility"]["live_actions_allowed"] is False
    assert metadata["capture_mode"] == "capture_only"
    assert metadata["frame_id"].startswith("sha256:")
    assert metadata["serial_alias"].startswith("device-")
    assert "192.168.1.20:5555" not in metadata_text


def test_capture_validates_paths_and_aliases(tmp_path: Path) -> None:
    matrix = SupportMatrix.from_toml(
        'schema_version = 1\ndefault_status = "capture_only"\ndefault_reason = "default"\n'
    )
    with pytest.raises(ValueError, match="serial"):
        anonymize_serial(" ")
    with pytest.raises(ValueError, match="Serial alias"):
        validate_serial_alias("bad alias")
    with pytest.raises(ValueError, match=".png"):
        capture_game_frame(
            screenshot_provider=Provider(),
            package_backend=Backend(),
            support_matrix=matrix,
            serial="192.168.1.20:5555",
            output_path=tmp_path / "frame.jpg",
        )
    output = tmp_path / "frame.png"
    with pytest.raises(ValueError, match="overwrite"):
        capture_game_frame(
            screenshot_provider=Provider(),
            package_backend=Backend(),
            support_matrix=matrix,
            serial="192.168.1.20:5555",
            output_path=output,
            metadata_path=output,
        )
    with pytest.raises(ValueError, match=".json"):
        capture_game_frame(
            screenshot_provider=Provider(),
            package_backend=Backend(),
            support_matrix=matrix,
            serial="192.168.1.20:5555",
            output_path=output,
            metadata_path=tmp_path / "metadata.txt",
        )


def test_capture_accepts_custom_alias_and_sidecar_path(tmp_path: Path) -> None:
    matrix = SupportMatrix.from_toml(
        'schema_version = 1\ndefault_status = "capture_only"\ndefault_reason = "default"\n'
    )
    result = capture_game_frame(
        screenshot_provider=Provider(),
        package_backend=Backend(),
        support_matrix=matrix,
        serial="192.168.1.20:5555",
        output_path=tmp_path / "frame.png",
        metadata_path=tmp_path / "manifest.json",
        serial_alias="lab-device-1",
    )
    assert result.metadata_path.name == "manifest.json"
    assert result.manifest.serial_alias == "lab-device-1"
