from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

import rushbot.adb as adb_module
from rushbot.adb import AdbBackend, AdbError, AndroidDevice, DeviceTransport


def completed(
    command: list[str] | None = None,
    *,
    returncode: int = 0,
    stdout: str | bytes = "",
    stderr: str | bytes = "",
) -> subprocess.CompletedProcess[Any]:
    return subprocess.CompletedProcess(command or ["adb"], returncode, stdout=stdout, stderr=stderr)


def test_android_device_dictionary_and_unknown_transport() -> None:
    device = AndroidDevice(serial="", state="offline", properties={"usb": "1-1"})
    assert device.transport is DeviceTransport.UNKNOWN
    assert device.as_dict() == {
        "serial": "",
        "state": "offline",
        "online": False,
        "transport": "unknown",
        "product": None,
        "model": None,
        "device": None,
        "transport_id": None,
        "properties": {"usb": "1-1"},
    }


@pytest.mark.parametrize(
    ("model", "device_name"),
    [("Android Emulator", "phone"), ("sdk_gphone64_x86_64", "phone"), ("Pixel", "emu64")],
)
def test_android_device_emulator_heuristics(model: str, device_name: str) -> None:
    device = AndroidDevice(serial="local", state="device", model=model, device=device_name)
    assert device.transport is DeviceTransport.EMULATOR


def test_android_device_mdns_network_heuristic() -> None:
    device = AndroidDevice(serial="phone._adb-tls-connect._tcp", state="device")
    assert device.transport is DeviceTransport.NETWORK


def test_find_adb_explicit_file_and_path_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "adb"
    executable.write_text("", encoding="utf-8")
    assert adb_module.find_adb(executable) == str(executable.resolve())

    monkeypatch.setattr(
        adb_module.shutil,
        "which",
        lambda name: str(executable) if name == "custom-adb" else None,
    )
    assert adb_module.find_adb("custom-adb") == str(executable.resolve())


def test_find_adb_sdk_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sdk = tmp_path / "sdk"
    executable_name = "adb.exe" if adb_module.os.name == "nt" else "adb"
    executable = sdk / "platform-tools" / executable_name
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    for name in ("ADB_PATH", "ADB", "ANDROID_HOME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANDROID_SDK_ROOT", str(sdk))
    monkeypatch.setattr(adb_module.shutil, "which", lambda _name: None)

    assert adb_module.find_adb() == str(executable.resolve())


def test_find_adb_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ADB_PATH", "ADB", "ANDROID_HOME", "ANDROID_SDK_ROOT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(adb_module.shutil, "which", lambda _name: None)
    monkeypatch.setattr(adb_module.Path, "is_file", lambda _self: False)

    with pytest.raises(FileNotFoundError, match="ADB was not found"):
        adb_module.find_adb()
    with pytest.raises(FileNotFoundError, match="Configured ADB"):
        adb_module.find_adb("definitely-missing-adb")


@pytest.mark.parametrize(
    "endpoint",
    ["", "[fe80::1", "[]:5555", "host:not-a-port", ":5555", "host:0", "host:65536"],
)
def test_validate_endpoint_additional_invalid_values(endpoint: str) -> None:
    with pytest.raises(ValueError):
        adb_module.validate_endpoint(endpoint)


def test_parse_devices_ignores_noise_and_handles_permissions() -> None:
    output = (
        "* daemon started successfully\n"
        "List of devices attached\n"
        "lonely-token\n"
        "ABC no permissions (user in plugdev group)\n"
        "USB123 device usb:1-1 invalid-property product:foo\n"
    )
    devices = adb_module.parse_devices(output)
    assert [device.serial for device in devices] == ["ABC", "USB123"]
    assert devices[0].state == "no-permissions"
    assert devices[1].properties == {"usb": "1-1", "product": "foo"}


def test_backend_environment_and_successful_run(tmp_path: Path) -> None:
    executable = tmp_path / "adb"
    executable.touch()
    calls: list[tuple[list[str], dict[str, object]]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return completed(command, stdout="ok")

    backend = AdbBackend(executable, environment={"RUSHBOT_TEST": "1"}, runner=runner)
    result = backend.run(["shell", 123], serial="SERIAL", input_text="input")

    assert result.stdout == "ok"
    command, kwargs = calls[0]
    assert command == [str(executable), "-s", "SERIAL", "shell", "123"]
    assert kwargs["input"] == "input"
    assert kwargs["env"]["RUSHBOT_TEST"] == "1"  # type: ignore[index]


@pytest.mark.parametrize("exception", [OSError("broken"), subprocess.TimeoutExpired("adb", 1)])
def test_backend_wraps_execution_errors(tmp_path: Path, exception: BaseException) -> None:
    executable = tmp_path / "adb"
    executable.touch()

    def runner(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise exception

    backend = AdbBackend(executable, runner=runner)
    with pytest.raises(AdbError, match="Could not execute ADB command"):
        backend.run(["devices"])


def test_backend_decodes_binary_error_and_can_skip_check(tmp_path: Path) -> None:
    executable = tmp_path / "adb"
    executable.touch()

    backend = AdbBackend(
        executable,
        runner=lambda command, **kwargs: completed(
            command, returncode=1, stdout=b"binary output", stderr=b"binary error"
        ),
    )
    with pytest.raises(AdbError, match="binary error"):
        backend.run(["devices"], text=False)

    result = backend.run(["devices"], text=False, check=False)
    assert result.returncode == 1


def test_backend_version_status_and_device_filtering(tmp_path: Path) -> None:
    executable = tmp_path / "adb"
    executable.touch()
    outputs = iter(
        [
            "Android Debug Bridge version 1.0.41\nVersion 37.0.0",
            "adb-custom-version\n",
            "",
            "USB backend: libusb\n",
            "List of devices attached\nA device model:Pixel\nB offline model:Other\n",
        ]
    )

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return completed(command, stdout=next(outputs))

    backend = AdbBackend(executable, runner=runner)
    assert backend.version() == "1.0.41"
    assert backend.version() == "adb-custom-version"
    backend.start_server()
    assert backend.server_status() == "USB backend: libusb"
    devices = backend.devices(online_only=True)
    assert [device.serial for device in devices] == ["A"]


def test_backend_connection_and_input_helpers(tmp_path: Path) -> None:
    executable = tmp_path / "adb"
    executable.touch()
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        message = "stderr response" if command[-1] == "disconnect" else "stdout response"
        if command[-1] == "disconnect":
            return completed(command, stdout="", stderr=message)
        return completed(command, stdout=message)

    backend = AdbBackend(executable, runner=runner)
    assert backend.connect("host:5555") == "stdout response"
    assert backend.disconnect("host:5555") == "stdout response"
    assert backend.disconnect() == "stderr response"
    assert backend.enable_tcpip("USB", port=5556) == "stdout response"
    assert backend.shell("USB", ["getprop", "ro.product.model"]) == "stdout response"
    backend.tap("USB", 1.9, 2.1)
    backend.swipe("USB", 1.1, 2.2, 3.3, 4.4, duration_ms=500)
    backend.keyevent("USB", "BACK")

    assert [str(executable), "connect", "host:5555"] in calls
    assert [str(executable), "disconnect", "host:5555"] in calls
    assert [str(executable), "disconnect"] in calls
    assert [str(executable), "-s", "USB", "tcpip", "5556"] in calls
    assert [str(executable), "-s", "USB", "shell", "input", "tap", "1", "2"] in calls
    assert [
        str(executable),
        "-s",
        "USB",
        "shell",
        "input",
        "swipe",
        "1",
        "2",
        "3",
        "4",
        "500",
    ] in calls

    with pytest.raises(ValueError, match="port"):
        backend.enable_tcpip("USB", port=0)
    with pytest.raises(ValueError, match="Pairing code"):
        backend.pair("host:5555", "  ")


def test_package_helpers_validate_and_build_commands(tmp_path: Path) -> None:
    executable = tmp_path / "adb"
    executable.touch()
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return completed(command, stdout="Events injected: 1\n")

    backend = AdbBackend(executable, runner=runner)
    assert "Events injected" in backend.start_package("SERIAL", "com.example.game")
    backend.force_stop_package("SERIAL", "com.example.game")

    assert "android.intent.category.LAUNCHER" in calls[0]
    assert calls[1][-4:] == ["shell", "am", "force-stop", "com.example.game"]

    for invalid in ("", "bad package"):
        with pytest.raises(ValueError, match="package name"):
            backend.start_package("SERIAL", invalid)
        with pytest.raises(ValueError, match="package name"):
            backend.force_stop_package("SERIAL", invalid)
