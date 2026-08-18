from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import rushbot.cli as cli_module
from rushbot.adb import AdbError, AndroidDevice
from rushbot.scrcpy import ScrcpyError, ScrcpyOptions, ScrcpyVersion


class FakeAdb:
    instances: list[FakeAdb] = []
    devices_result: list[AndroidDevice] = [
        AndroidDevice(serial="USB", state="device", model="Pixel")
    ]
    fail_init: BaseException | None = None

    def __init__(self, executable: str | None = None) -> None:
        if self.fail_init:
            raise self.fail_init
        self.executable = executable or "/usr/bin/adb"
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.__class__.instances.append(self)

    def version(self) -> str:
        return "1.0.41"

    def devices(self, *, online_only: bool = False) -> list[AndroidDevice]:
        self.calls.append(("devices", (), {"online_only": online_only}))
        return [device for device in self.devices_result if device.online or not online_only]

    def pair(self, endpoint: str, code: str) -> str:
        self.calls.append(("pair", (endpoint, code), {}))
        return "paired"

    def connect(self, endpoint: str) -> str:
        self.calls.append(("connect", (endpoint,), {}))
        return "connected"

    def disconnect(self, endpoint: str | None) -> str:
        self.calls.append(("disconnect", (endpoint,), {}))
        return "disconnected"

    def enable_tcpip(self, serial: str, *, port: int) -> str:
        self.calls.append(("tcpip", (serial,), {"port": port}))
        return "tcpip enabled"

    def screencap_png(self, serial: str) -> bytes:
        self.calls.append(("screenshot", (serial,), {}))
        return b"\x89PNG\r\n\x1a\n" + b"x" * 64

    def start_package(self, serial: str, package: str) -> str:
        self.calls.append(("start", (serial, package), {}))
        return "started"

    def force_stop_package(self, serial: str, package: str) -> None:
        self.calls.append(("stop", (serial, package), {}))


class FakeSession:
    def __init__(self, *, keyboard_interrupt: bool = False) -> None:
        self.started = False
        self.stopped = False
        self.keyboard_interrupt = keyboard_interrupt

    def start(self) -> None:
        self.started = True

    def wait(self) -> int:
        if self.keyboard_interrupt:
            raise KeyboardInterrupt
        return 7

    def stop(self) -> None:
        self.stopped = True


class FakeScrcpyClient:
    instances: list[FakeScrcpyClient] = []
    fail_init: BaseException | None = None
    keyboard_interrupt = False

    def __init__(self, executable: str | None = None) -> None:
        if self.fail_init:
            raise self.fail_init
        self.executable = executable or "/usr/bin/scrcpy"
        self.options: ScrcpyOptions | None = None
        self.log_path: Path | None = None
        self.session_result = FakeSession(keyboard_interrupt=self.keyboard_interrupt)
        self.__class__.instances.append(self)

    def ensure_supported(self) -> ScrcpyVersion:
        return ScrcpyVersion(4, 0, 0)

    def session(self, options: ScrcpyOptions, *, log_path: Path | None = None) -> FakeSession:
        self.options = options
        self.log_path = log_path
        return self.session_result


@pytest.fixture(autouse=True)
def reset_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAdb.instances = []
    FakeAdb.devices_result = [AndroidDevice(serial="USB", state="device", model="Pixel")]
    FakeAdb.fail_init = None
    FakeScrcpyClient.instances = []
    FakeScrcpyClient.fail_init = None
    FakeScrcpyClient.keyboard_interrupt = False
    monkeypatch.setattr(cli_module, "AdbBackend", FakeAdb)
    monkeypatch.setattr(cli_module, "ScrcpyClient", FakeScrcpyClient)


def test_doctor_healthy_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli_module.main(["doctor", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["adb"]["version"] == "1.0.41"
    assert report["scrcpy"]["version"] == "4.0.0"
    assert report["devices"][0]["serial"] == "USB"


def test_doctor_plain_and_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli_module.main(["doctor"]) == 0
    output = capsys.readouterr().out
    assert "RushBot:" in output
    assert "devices: 1" in output
    assert "USB  device  usb  Pixel" in output

    FakeAdb.fail_init = FileNotFoundError("adb missing")
    FakeScrcpyClient.fail_init = FileNotFoundError("scrcpy missing")
    assert cli_module.main(["doctor"]) == 1
    output = capsys.readouterr().out
    assert "adb: ERROR" in output
    assert "scrcpy: ERROR" in output


def test_devices_json_plain_and_empty(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli_module.main(["devices", "--online-only", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["transport"] == "usb"
    assert FakeAdb.instances[-1].calls[-1][2] == {"online_only": True}

    assert cli_module.main(["devices"]) == 0
    assert "USB\tdevice\tusb\tPixel" in capsys.readouterr().out

    FakeAdb.devices_result = []
    assert cli_module.main(["devices"]) == 0
    assert "No ADB devices found" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("argv", "expected_call", "expected_output"),
    [
        (["connect", "host:5555"], "connect", "connected"),
        (["disconnect", "host:5555"], "disconnect", "disconnected"),
        (["disconnect"], "disconnect", "disconnected"),
        (["tcpip", "USB", "--port", "5556"], "tcpip", "tcpip enabled"),
        (["start-app", "USB", "com.example.game"], "start", "started"),
        (["stop-app", "USB", "com.example.game"], "stop", ""),
    ],
)
def test_simple_cli_commands(
    argv: list[str],
    expected_call: str,
    expected_output: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli_module.main(argv) == 0
    output = capsys.readouterr().out
    assert expected_output in output
    assert FakeAdb.instances[-1].calls[-1][0] == expected_call


def test_pairing_code_sources(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli_module.main(["pair", "host:37123", "--code", "111111"]) == 0
    assert FakeAdb.instances[-1].calls[-1][1] == ("host:37123", "111111")
    capsys.readouterr()

    monkeypatch.setenv("RUSHBOT_PAIRING_CODE", "222222")
    assert cli_module.main(["pair", "host:37123"]) == 0
    assert FakeAdb.instances[-1].calls[-1][1] == ("host:37123", "222222")
    capsys.readouterr()

    monkeypatch.delenv("RUSHBOT_PAIRING_CODE")
    monkeypatch.setattr(cli_module.getpass, "getpass", lambda _prompt: "333333")
    assert cli_module.main(["pair", "host:37123"]) == 0
    assert FakeAdb.instances[-1].calls[-1][1] == ("host:37123", "333333")


def test_screenshot_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    destination = tmp_path / "capture.png"
    assert cli_module.main(["screenshot", "USB", str(destination)]) == 0
    assert destination.exists()
    assert str(destination.resolve()) in capsys.readouterr().out


def test_mirror_command_and_keyboard_interrupt(tmp_path: Path) -> None:
    record = tmp_path / "record.mkv"
    log = tmp_path / "scrcpy.log"
    result = cli_module.main(
        [
            "mirror",
            "USB",
            "--view-only",
            "--audio",
            "--max-size",
            "1600",
            "--max-fps",
            "30",
            "--turn-screen-off",
            "--v4l2-sink",
            "/dev/video10",
            "--no-window",
            "--record",
            str(record),
            "--log",
            str(log),
        ]
    )
    assert result == 7
    client = FakeScrcpyClient.instances[-1]
    assert client.options == ScrcpyOptions(
        serial="USB",
        control=False,
        audio=True,
        max_size=1600,
        max_fps=30,
        turn_screen_off=True,
        v4l2_sink="/dev/video10",
        video_playback=False,
        record_path=record,
    )
    assert client.session_result.started

    FakeScrcpyClient.keyboard_interrupt = True
    assert cli_module.main(["mirror", "USB"]) == 130
    assert FakeScrcpyClient.instances[-1].session_result.stopped


@pytest.mark.parametrize(
    "exception",
    [AdbError("adb failed"), ScrcpyError("scrcpy failed"), ValueError("invalid")],
)
def test_main_reports_operational_errors(
    exception: BaseException,
    capsys: pytest.CaptureFixture[str],
) -> None:
    FakeAdb.fail_init = exception
    assert cli_module.main(["devices"]) == 2
    assert "error:" in capsys.readouterr().err
