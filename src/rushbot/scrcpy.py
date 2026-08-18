"""Integration with the official external scrcpy client.

The scrcpy client/server protocol is intentionally treated as private. RushBot invokes
one matching official scrcpy distribution instead of embedding a Python reimplementation.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO


class ScrcpyError(RuntimeError):
    """Raised when scrcpy is unavailable or exits unexpectedly."""


_VERSION_RE = re.compile(r"\bscrcpy\s+(\d+)\.(\d+)(?:\.(\d+))?\b", re.IGNORECASE)


@dataclass(frozen=True, order=True, slots=True)
class ScrcpyVersion:
    major: int
    minor: int
    patch: int = 0

    @classmethod
    def parse(cls, output: str) -> ScrcpyVersion:
        match = _VERSION_RE.search(output)
        if not match:
            raise ValueError(f"Could not parse scrcpy version from: {output!r}")
        major, minor, patch = match.groups()
        return cls(int(major), int(minor), int(patch or 0))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def find_scrcpy(explicit: str | os.PathLike[str] | None = None) -> str:
    """Resolve the official scrcpy executable on Linux or Windows."""

    requested = explicit or os.getenv("SCRCPY_PATH") or os.getenv("SCRCPY")
    if requested:
        requested_path = Path(requested).expanduser()
        if requested_path.is_file():
            return str(requested_path.resolve())
        located = shutil.which(str(requested))
        if located:
            return str(Path(located).resolve())
        raise FileNotFoundError(f"Configured scrcpy executable was not found: {requested}")

    executable_name = "scrcpy.exe" if os.name == "nt" else "scrcpy"
    located = shutil.which(executable_name) or shutil.which("scrcpy")
    if located:
        return str(Path(located).resolve())

    repo_root = Path(__file__).resolve().parents[2]
    candidates = [
        repo_root / ".tools" / "scrcpy" / executable_name,
        repo_root / ".scrcpy" / executable_name,
        repo_root / "scrcpy" / executable_name,
        repo_root / "bin" / executable_name,
    ]
    if os.name == "nt":
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            value = os.getenv(variable)
            if value:
                candidates.append(Path(value) / "scrcpy" / executable_name)
    else:
        candidates.extend([Path("/usr/bin/scrcpy"), Path("/usr/local/bin/scrcpy")])

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())

    raise FileNotFoundError(
        "scrcpy was not found. Install an official scrcpy 4.x build and place it "
        "on PATH, or set SCRCPY_PATH."
    )


@dataclass(frozen=True, slots=True)
class ScrcpyOptions:
    """Stable subset of scrcpy options used by RushBot."""

    serial: str
    control: bool = True
    audio: bool = False
    window_title: str | None = None
    max_size: int | None = None
    max_fps: int | None = None
    stay_awake: bool = True
    turn_screen_off: bool = False
    v4l2_sink: str | None = None
    video_playback: bool = True
    record_path: Path | None = None

    def validate(self) -> None:
        if not self.serial.strip():
            raise ValueError("A device serial is required for scrcpy.")
        if self.max_size is not None and self.max_size <= 0:
            raise ValueError("max_size must be positive.")
        if self.max_fps is not None and not 1 <= self.max_fps <= 240:
            raise ValueError("max_fps must be between 1 and 240.")
        if self.v4l2_sink and not sys.platform.startswith("linux"):
            raise ValueError("A scrcpy V4L2 sink is supported only on Linux.")
        if self.v4l2_sink and not self.v4l2_sink.startswith("/dev/video"):
            raise ValueError("V4L2 sink must look like /dev/videoN.")


def build_scrcpy_command(executable: str, options: ScrcpyOptions) -> list[str]:
    """Build an argv list without shell interpolation."""

    options.validate()
    command = [executable, f"--serial={options.serial}"]
    command.append(f"--window-title={options.window_title or f'RushBot — {options.serial}'}")
    if not options.control:
        command.append("--no-control")
    if not options.audio:
        command.append("--no-audio")
    if options.max_size is not None:
        command.append(f"--max-size={options.max_size}")
    if options.max_fps is not None:
        command.append(f"--max-fps={options.max_fps}")
    if options.stay_awake:
        command.append("--stay-awake")
    if options.turn_screen_off:
        command.append("--turn-screen-off")
    if options.v4l2_sink:
        command.append(f"--v4l2-sink={options.v4l2_sink}")
    if not options.video_playback:
        command.append("--no-video-playback")
    if options.record_path:
        command.append(f"--record={options.record_path.expanduser().resolve()}")
    return command


class ScrcpyClient:
    """Version-check and launch the official scrcpy executable."""

    def __init__(
        self,
        executable: str | os.PathLike[str] | None = None,
        *,
        minimum_major: int = 4,
    ) -> None:
        self.executable = (
            str(Path(executable).expanduser()) if executable is not None else find_scrcpy()
        )
        self.minimum_major = minimum_major

    def version(self) -> ScrcpyVersion:
        try:
            completed = subprocess.run(
                [self.executable, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ScrcpyError(f"Could not execute scrcpy: {self.executable}") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "unknown error").strip()
            raise ScrcpyError(f"scrcpy --version failed: {detail}")
        return ScrcpyVersion.parse(f"{completed.stdout}\n{completed.stderr}")

    def ensure_supported(self) -> ScrcpyVersion:
        version = self.version()
        if version.major < self.minimum_major:
            raise ScrcpyError(
                f"scrcpy {version} is too old; RushBot requires scrcpy "
                f"{self.minimum_major}.x or newer."
            )
        return version

    def session(
        self,
        options: ScrcpyOptions,
        *,
        log_path: str | os.PathLike[str] | None = None,
    ) -> ScrcpySession:
        self.ensure_supported()
        return ScrcpySession(self.executable, options, log_path=log_path)


class ScrcpySession:
    """Managed lifetime of one external scrcpy process."""

    def __init__(
        self,
        executable: str,
        options: ScrcpyOptions,
        *,
        log_path: str | os.PathLike[str] | None = None,
    ) -> None:
        self.command = build_scrcpy_command(executable, options)
        self.log_path = Path(log_path).expanduser().resolve() if log_path else None
        self.process: subprocess.Popen[bytes] | None = None
        self._log_file: IO[bytes] | None = None

    def start(self) -> subprocess.Popen[bytes]:
        if self.process and self.process.poll() is None:
            return self.process

        stderr_target: int | IO[bytes]
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_file = self.log_path.open("ab")
            stderr_target = self._log_file
        else:
            stderr_target = subprocess.DEVNULL

        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=stderr_target,
                start_new_session=os.name != "nt",
            )
        except OSError as exc:
            self._close_log()
            raise ScrcpyError(f"Could not start scrcpy: {' '.join(self.command)}") from exc

        time.sleep(0.25)
        return_code = self.process.poll()
        if return_code is not None:
            self._close_log()
            raise ScrcpyError(f"scrcpy exited during startup with code {return_code}.")
        return self.process

    def wait(self) -> int:
        if not self.process:
            self.start()
        assert self.process is not None
        try:
            return self.process.wait()
        finally:
            self._close_log()

    def stop(self, *, timeout: float = 5) -> None:
        process = self.process
        if not process:
            self._close_log()
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=timeout)
        self.process = None
        self._close_log()

    def _close_log(self) -> None:
        if self._log_file:
            self._log_file.close()
            self._log_file = None

    def __enter__(self) -> ScrcpySession:
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.stop()
