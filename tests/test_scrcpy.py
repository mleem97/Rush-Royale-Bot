from __future__ import annotations

import sys

import pytest

from rushbot.scrcpy import ScrcpyOptions, ScrcpyVersion, build_scrcpy_command


def test_parse_scrcpy_version() -> None:
    output = "scrcpy 4.0 <https://github.com/Genymobile/scrcpy>"
    assert ScrcpyVersion.parse(output) == ScrcpyVersion(4, 0, 0)
    assert ScrcpyVersion.parse("scrcpy 4.1.2") == ScrcpyVersion(4, 1, 2)


def test_build_view_only_command() -> None:
    command = build_scrcpy_command(
        "/usr/bin/scrcpy",
        ScrcpyOptions(
            serial="192.168.1.8:42157",
            control=False,
            audio=False,
            max_size=1920,
            max_fps=60,
        ),
    )

    assert command[0] == "/usr/bin/scrcpy"
    assert "--serial=192.168.1.8:42157" in command
    assert "--no-control" in command
    assert "--no-audio" in command
    assert "--max-size=1920" in command
    assert "--max-fps=60" in command


def test_v4l2_rejected_outside_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    with pytest.raises(ValueError, match="only on Linux"):
        ScrcpyOptions(serial="device", v4l2_sink="/dev/video10").validate()
