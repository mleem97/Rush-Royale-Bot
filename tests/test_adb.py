from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from rushbot.adb import AdbBackend, DeviceTransport, parse_devices, validate_endpoint

SAMPLE_DEVICES = (
    "List of devices attached\n"
    "emulator-5554 device product:sdk_gphone64_x86_64 "
    "model:sdk_gphone64_x86_64 device:emu64xa transport_id:1\n"
    "R5CT123456A unauthorized usb:1-2 transport_id:2\n"
    "192.168.10.44:42157 device product:dm3qxeea "
    "model:SM_S918B device:dm3q transport_id:3\n"
)


def test_parse_devices_and_transport_classification() -> None:
    devices = parse_devices(SAMPLE_DEVICES)

    assert [device.serial for device in devices] == [
        "emulator-5554",
        "R5CT123456A",
        "192.168.10.44:42157",
    ]
    assert devices[0].transport is DeviceTransport.EMULATOR
    assert devices[1].transport is DeviceTransport.USB
    assert not devices[1].online
    assert devices[2].transport is DeviceTransport.NETWORK
    assert devices[2].model == "SM_S918B"


def test_validate_endpoint() -> None:
    assert validate_endpoint("192.168.1.8:5555") == "192.168.1.8:5555"
    assert validate_endpoint("[fe80::1]:37123") == "[fe80::1]:37123"

    with pytest.raises(ValueError):
        validate_endpoint("192.168.1.8")
    with pytest.raises(ValueError):
        validate_endpoint("fe80::1:5555")
    with pytest.raises(ValueError):
        validate_endpoint("host:70000")


def test_pairing_code_is_sent_on_stdin_not_command_line(tmp_path: Path) -> None:
    executable = tmp_path / "adb"
    executable.touch()
    calls: list[tuple[list[str], dict[str, object]]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="Successfully paired to 192.168.1.8:37123\n",
            stderr="",
        )

    backend = AdbBackend(executable, runner=runner)
    result = backend.pair("192.168.1.8:37123", "123456")

    assert "Successfully paired" in result
    command, kwargs = calls[0]
    assert "123456" not in command
    assert kwargs["input"] == "123456\n"


def test_screencap_uses_selected_serial(tmp_path: Path) -> None:
    executable = tmp_path / "adb"
    executable.touch()
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=png, stderr=b"")

    backend = AdbBackend(executable, runner=runner)
    assert backend.screencap_png("device-123") == png
    assert calls[0] == [
        str(executable),
        "-s",
        "device-123",
        "exec-out",
        "screencap",
        "-p",
    ]
