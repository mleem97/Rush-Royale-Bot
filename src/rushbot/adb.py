"""Safe, cross-platform wrapper around Google's official ``adb`` executable.

This module deliberately does not implement the ADB wire protocol itself. Keeping the
Android SDK Platform Tools executable as the single transport authority makes USB,
emulators, legacy TCP/IP and Android Wireless Debugging behave consistently.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class AdbError(RuntimeError):
    """Raised when an ADB command cannot be executed successfully."""


class DeviceTransport(StrEnum):
    """How ADB currently exposes a device to the host."""

    USB = "usb"
    NETWORK = "network"
    EMULATOR = "emulator"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AndroidDevice:
    """One entry returned by ``adb devices -l``."""

    serial: str
    state: str
    product: str | None = None
    model: str | None = None
    device: str | None = None
    transport_id: str | None = None
    properties: Mapping[str, str] = field(default_factory=dict)

    @property
    def online(self) -> bool:
        return self.state == "device"

    @property
    def transport(self) -> DeviceTransport:
        serial_lower = self.serial.lower()
        model_lower = (self.model or "").lower()
        device_lower = (self.device or "").lower()
        if (
            serial_lower.startswith("emulator-")
            or "emulator" in model_lower
            or model_lower.startswith("sdk_gphone")
            or device_lower.startswith("emu")
        ):
            return DeviceTransport.EMULATOR
        if ":" in self.serial or "_adb-tls-connect._tcp" in serial_lower:
            return DeviceTransport.NETWORK
        if self.serial:
            return DeviceTransport.USB
        return DeviceTransport.UNKNOWN

    def as_dict(self) -> dict[str, Any]:
        return {
            "serial": self.serial,
            "state": self.state,
            "online": self.online,
            "transport": self.transport.value,
            "product": self.product,
            "model": self.model,
            "device": self.device,
            "transport_id": self.transport_id,
            "properties": dict(self.properties),
        }


_ADB_VERSION_RE = re.compile(r"Android Debug Bridge version\s+([0-9.]+)")


def find_adb(explicit: str | os.PathLike[str] | None = None) -> str:
    """Resolve the official ADB executable.

    Search order: explicit argument, ``ADB_PATH``/``ADB``, ``PATH``, Android SDK
    environment variables, then common per-user and system locations.
    """

    requested = explicit or os.getenv("ADB_PATH") or os.getenv("ADB")
    if requested:
        requested_path = Path(requested).expanduser()
        if requested_path.is_file():
            return str(requested_path.resolve())
        located = shutil.which(str(requested))
        if located:
            return str(Path(located).resolve())
        raise FileNotFoundError(f"Configured ADB executable was not found: {requested}")

    executable_name = "adb.exe" if os.name == "nt" else "adb"
    located = shutil.which(executable_name) or shutil.which("adb")
    if located:
        return str(Path(located).resolve())

    candidates: list[Path] = []
    for variable in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        value = os.getenv(variable)
        if value:
            candidates.append(Path(value).expanduser() / "platform-tools" / executable_name)

    candidates.extend(
        [
            Path.home() / "Android" / "Sdk" / "platform-tools" / executable_name,
            Path.home()
            / ".local"
            / "share"
            / "android-sdk"
            / "platform-tools"
            / executable_name,
        ]
    )
    if os.name == "nt":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            candidates.append(
                Path(local_app_data)
                / "Android"
                / "Sdk"
                / "platform-tools"
                / executable_name
            )
    else:
        candidates.extend([Path("/usr/bin/adb"), Path("/usr/local/bin/adb")])

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())

    raise FileNotFoundError(
        "ADB was not found. Install current Android SDK Platform Tools and place "
        "'adb' on PATH, or set ADB_PATH to the executable."
    )


def validate_endpoint(endpoint: str) -> str:
    """Validate and normalize an ``IP-or-hostname:port`` ADB endpoint."""

    candidate = endpoint.strip()
    if not candidate:
        raise ValueError("ADB endpoint must not be empty.")

    if candidate.startswith("["):
        closing = candidate.find("]")
        if closing < 2 or closing + 1 >= len(candidate) or candidate[closing + 1] != ":":
            raise ValueError("IPv6 endpoints must use [address]:port syntax.")
        host = candidate[1:closing]
        port_text = candidate[closing + 2 :]
        normalized_host = f"[{host}]"
    else:
        if candidate.count(":") != 1:
            raise ValueError(
                "ADB endpoint must use host:port syntax; wrap IPv6 addresses in brackets."
            )
        host, port_text = candidate.rsplit(":", maxsplit=1)
        normalized_host = host

    if not host or not port_text.isdecimal():
        raise ValueError("ADB endpoint must contain a host and a numeric port.")
    port = int(port_text)
    if not 1 <= port <= 65535:
        raise ValueError("ADB endpoint port must be between 1 and 65535.")
    return f"{normalized_host}:{port}"


def parse_devices(output: str) -> list[AndroidDevice]:
    """Parse the output of ``adb devices -l``."""

    devices: list[AndroidDevice] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of devices attached") or line.startswith("*"):
            continue

        if " no permissions" in line:
            serial = line.split(maxsplit=1)[0]
            devices.append(AndroidDevice(serial=serial, state="no-permissions"))
            continue

        fields = line.split()
        if len(fields) < 2:
            continue
        serial, state, *property_fields = fields
        properties: dict[str, str] = {}
        for item in property_fields:
            key, separator, value = item.partition(":")
            if separator and key and value:
                properties[key] = value

        devices.append(
            AndroidDevice(
                serial=serial,
                state=state,
                product=properties.get("product"),
                model=properties.get("model"),
                device=properties.get("device"),
                transport_id=properties.get("transport_id"),
                properties=properties,
            )
        )
    return devices


Runner = Callable[..., subprocess.CompletedProcess[Any]]


class AdbBackend:
    """Subprocess-backed ADB client with no shell interpolation."""

    def __init__(
        self,
        adb_executable: str | os.PathLike[str] | None = None,
        *,
        environment: Mapping[str, str] | None = None,
        runner: Runner = subprocess.run,
    ) -> None:
        self.executable = (
            str(Path(adb_executable).expanduser())
            if adb_executable is not None
            else find_adb()
        )
        self.environment = os.environ.copy()
        if environment:
            self.environment.update(environment)
        self._runner = runner

    def run(
        self,
        arguments: Sequence[str | os.PathLike[str] | int | float],
        *,
        serial: str | None = None,
        timeout: float = 30,
        check: bool = True,
        text: bool = True,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
        command = [self.executable]
        if serial:
            command.extend(["-s", serial])
        command.extend(str(argument) for argument in arguments)

        try:
            completed = self._runner(
                command,
                capture_output=True,
                text=text,
                input=input_text,
                timeout=timeout,
                check=False,
                env=self.environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AdbError(f"Could not execute ADB command: {' '.join(command)}") from exc

        if check and completed.returncode != 0:
            stderr = completed.stderr
            stdout = completed.stdout
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            if isinstance(stdout, bytes):
                stdout = stdout.decode(errors="replace")
            detail = str(stderr or stdout or "unknown ADB error").strip()
            raise AdbError(
                f"ADB command failed with exit code {completed.returncode}: {detail}"
            )
        return completed

    def version(self) -> str:
        completed = self.run(["version"], timeout=10)
        output = str(completed.stdout)
        match = _ADB_VERSION_RE.search(output)
        return match.group(1) if match else output.splitlines()[0].strip()

    def start_server(self) -> None:
        self.run(["start-server"], timeout=15)

    def server_status(self) -> str:
        completed = self.run(["server-status"], timeout=10)
        return str(completed.stdout).strip()

    def devices(self, *, online_only: bool = False) -> list[AndroidDevice]:
        completed = self.run(["devices", "-l"], timeout=15)
        devices = parse_devices(str(completed.stdout))
        if online_only:
            return [device for device in devices if device.online]
        return devices

    def pair(self, endpoint: str, pairing_code: str, *, timeout: float = 30) -> str:
        normalized = validate_endpoint(endpoint)
        code = pairing_code.strip()
        if not code:
            raise ValueError("Pairing code must not be empty.")
        completed = self.run(
            ["pair", normalized],
            input_text=f"{code}\n",
            timeout=timeout,
        )
        return str(completed.stdout or completed.stderr).strip()

    def connect(self, endpoint: str, *, timeout: float = 30) -> str:
        normalized = validate_endpoint(endpoint)
        completed = self.run(["connect", normalized], timeout=timeout)
        return str(completed.stdout or completed.stderr).strip()

    def disconnect(self, endpoint: str | None = None) -> str:
        arguments = ["disconnect"]
        if endpoint:
            arguments.append(validate_endpoint(endpoint))
        completed = self.run(arguments, timeout=15)
        return str(completed.stdout or completed.stderr).strip()

    def enable_tcpip(self, serial: str, *, port: int = 5555) -> str:
        if not 1 <= port <= 65535:
            raise ValueError("ADB TCP/IP port must be between 1 and 65535.")
        completed = self.run(["tcpip", port], serial=serial, timeout=20)
        return str(completed.stdout or completed.stderr).strip()

    def shell(self, serial: str, arguments: Sequence[str | int | float]) -> str:
        completed = self.run(["shell", *arguments], serial=serial)
        return str(completed.stdout)

    def tap(self, serial: str, x: int | float, y: int | float) -> None:
        self.run(["shell", "input", "tap", int(x), int(y)], serial=serial)

    def swipe(
        self,
        serial: str,
        x1: int | float,
        y1: int | float,
        x2: int | float,
        y2: int | float,
        *,
        duration_ms: int = 300,
    ) -> None:
        self.run(
            [
                "shell",
                "input",
                "swipe",
                int(x1),
                int(y1),
                int(x2),
                int(y2),
                duration_ms,
            ],
            serial=serial,
        )

    def keyevent(self, serial: str, keycode: int | str) -> None:
        self.run(["shell", "input", "keyevent", keycode], serial=serial)

    def screencap_png(self, serial: str, *, timeout: float = 15) -> bytes:
        completed = self.run(
            ["exec-out", "screencap", "-p"],
            serial=serial,
            timeout=timeout,
            text=False,
        )
        assert isinstance(completed.stdout, bytes)
        return completed.stdout

    def start_package(self, serial: str, package_name: str) -> str:
        package = package_name.strip()
        if not package or any(character.isspace() for character in package):
            raise ValueError("Android package name is invalid.")
        completed = self.run(
            [
                "shell",
                "monkey",
                "-p",
                package,
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ],
            serial=serial,
            timeout=20,
        )
        return str(completed.stdout)

    def force_stop_package(self, serial: str, package_name: str) -> None:
        package = package_name.strip()
        if not package or any(character.isspace() for character in package):
            raise ValueError("Android package name is invalid.")
        self.run(["shell", "am", "force-stop", package], serial=serial, timeout=15)
