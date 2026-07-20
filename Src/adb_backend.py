"""Cross-platform Android Debug Bridge backend.

The bot talks to Google's official ``adb`` executable instead of depending on a
third-party implementation of the ADB protocol. This keeps Windows and Linux
behaviour aligned and lets users update Platform Tools independently.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]


class AdbError(RuntimeError):
    """Raised when an adb command cannot be executed successfully."""


def _executable_name(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def _resolve_candidate(value: str | os.PathLike[str] | None) -> Path | None:
    if not value:
        return None
    expanded = Path(value).expanduser()
    if expanded.is_file():
        return expanded.resolve()
    located = shutil.which(str(value))
    return Path(located).resolve() if located else None


def find_adb() -> str:
    """Return the absolute path to adb on Windows or Linux.

    Search order: explicit environment variables, PATH, a local scrcpy/platform
    tools directory, Android SDK environment variables, then common OS paths.
    """
    for variable in ("ADB_PATH", "ADB"):
        candidate = _resolve_candidate(os.getenv(variable))
        if candidate:
            return str(candidate)

    for command in ("adb", "adb.exe"):
        candidate = _resolve_candidate(command)
        if candidate:
            return str(candidate)

    adb_name = _executable_name("adb")
    candidates: list[Path] = [
        REPO_ROOT / ".scrcpy" / adb_name,
        REPO_ROOT / "scrcpy" / adb_name,
        REPO_ROOT / "platform-tools" / adb_name,
    ]

    for variable in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        sdk_root = os.getenv(variable)
        if sdk_root:
            candidates.append(Path(sdk_root).expanduser() / "platform-tools" / adb_name)

    if os.name == "nt":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            candidates.append(
                Path(local_app_data) / "Android" / "Sdk" / "platform-tools" / "adb.exe"
            )
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            root = os.getenv(variable)
            if root:
                candidates.extend(
                    [
                        Path(root) / "Android" / "platform-tools" / "adb.exe",
                        Path(root) / "scrcpy" / "adb.exe",
                    ]
                )
    else:
        candidates.extend(
            [
                Path.home() / "Android" / "Sdk" / "platform-tools" / "adb",
                Path.home() / ".local" / "share" / "android-sdk" / "platform-tools" / "adb",
                Path("/usr/bin/adb"),
                Path("/usr/local/bin/adb"),
            ]
        )

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())

    raise FileNotFoundError(
        "ADB was not found. Install Android SDK Platform Tools and make 'adb' "
        "available on PATH, or set ADB_PATH to the executable."
    )


def find_scrcpy() -> str | None:
    """Return an optional scrcpy executable path for diagnostics/mirroring."""
    for variable in ("SCRCPY_PATH", "SCRCPY"):
        candidate = _resolve_candidate(os.getenv(variable))
        if candidate:
            return str(candidate)

    for command in ("scrcpy", "scrcpy.exe"):
        candidate = _resolve_candidate(command)
        if candidate:
            return str(candidate)

    executable = _executable_name("scrcpy")
    for candidate in (
        REPO_ROOT / ".scrcpy" / executable,
        REPO_ROOT / "scrcpy" / executable,
        REPO_ROOT / "bin" / executable,
    ):
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def _normalise_args(args: Iterable[object]) -> list[str]:
    return [str(argument) for argument in args]


def run_adb(
    args: Sequence[object],
    *,
    serial: str | None = None,
    timeout: float = 30,
    check: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    """Run adb without invoking a shell and return the completed process."""
    command = [find_adb()]
    if serial:
        command.extend(["-s", serial])
    command.extend(_normalise_args(args))

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=text,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AdbError(f"Failed to execute adb command: {' '.join(command)}") from exc

    if check and completed.returncode != 0:
        stderr = completed.stderr if text else completed.stderr.decode(errors="replace")
        stdout = completed.stdout if text else completed.stdout.decode(errors="replace")
        detail = (stderr or stdout or "unknown adb error").strip()
        raise AdbError(f"adb command failed ({completed.returncode}): {detail}")
    return completed


def parse_devices(output: str) -> list[tuple[str, str]]:
    """Parse ``adb devices`` output into ``(serial, state)`` tuples."""
    devices: list[tuple[str, str]] = []
    for line in output.splitlines()[1:]:
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append((parts[0], parts[1]))
    return devices


def list_devices(*, online_only: bool = True) -> list[str]:
    completed = run_adb(["devices"], timeout=15)
    devices = parse_devices(completed.stdout)
    if online_only:
        return [serial for serial, state in devices if state == "device"]
    return [serial for serial, _ in devices]


def connect(serial: str, *, timeout: float = 15) -> bool:
    """Connect a TCP/IP device and report whether it is online afterwards."""
    if ":" not in serial:
        return serial in list_devices()
    completed = run_adb(["connect", serial], timeout=timeout, check=False)
    message = f"{completed.stdout}\n{completed.stderr}".lower()
    return completed.returncode == 0 and (
        "connected to" in message or "already connected" in message
    )


class AdbDevice:
    """Small compatibility wrapper used by the existing bot core."""

    def __init__(self, serial: str):
        self.serial = serial

    def shell(self, command: str, timeout: float = 30) -> str:
        return run_adb(["shell", command], serial=self.serial, timeout=timeout).stdout

    def input_tap(self, x: int | float, y: int | float) -> None:
        self.shell(f"input tap {int(x)} {int(y)}")

    def input_swipe(
        self,
        x1: int | float,
        y1: int | float,
        x2: int | float,
        y2: int | float,
        duration: int = 300,
    ) -> None:
        self.shell(
            f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration)}"
        )

    def input_keyevent(self, key: int | str) -> None:
        self.shell(f"input keyevent {key}")

    def screencap(self) -> bytes:
        completed = run_adb(
            ["exec-out", "screencap", "-p"],
            serial=self.serial,
            timeout=15,
            text=False,
        )
        return completed.stdout


class AdbClient:
    """Compatibility API matching the subset of pure-python-adb used by RushBot."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5037):
        self.host = host
        self.port = port

    def devices(self) -> list[AdbDevice]:
        run_adb(["start-server"], timeout=15)
        return [AdbDevice(serial) for serial in list_devices()]
