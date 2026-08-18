from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

import rushbot.scrcpy as scrcpy_module
from rushbot.scrcpy import (
    ScrcpyClient,
    ScrcpyError,
    ScrcpyOptions,
    ScrcpySession,
    ScrcpyVersion,
    build_scrcpy_command,
)


def test_version_parse_failure_and_string() -> None:
    with pytest.raises(ValueError, match="Could not parse"):
        ScrcpyVersion.parse("not scrcpy")
    assert str(ScrcpyVersion(4, 2, 1)) == "4.2.1"


def test_find_scrcpy_explicit_path_lookup_and_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "scrcpy"
    executable.touch()
    assert scrcpy_module.find_scrcpy(executable) == str(executable.resolve())

    monkeypatch.setattr(
        scrcpy_module.shutil,
        "which",
        lambda name: str(executable) if name == "custom-scrcpy" else None,
    )
    assert scrcpy_module.find_scrcpy("custom-scrcpy") == str(executable.resolve())

    monkeypatch.setattr(scrcpy_module.shutil, "which", lambda _name: None)
    with pytest.raises(FileNotFoundError, match="Configured scrcpy"):
        scrcpy_module.find_scrcpy("missing-scrcpy")


def test_find_scrcpy_path_and_final_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "scrcpy"
    executable.touch()
    for name in ("SCRCPY_PATH", "SCRCPY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        scrcpy_module.shutil,
        "which",
        lambda name: str(executable) if name == "scrcpy" else None,
    )
    assert scrcpy_module.find_scrcpy() == str(executable.resolve())

    monkeypatch.setattr(scrcpy_module.shutil, "which", lambda _name: None)
    monkeypatch.setattr(scrcpy_module.Path, "is_file", lambda _self: False)
    with pytest.raises(FileNotFoundError, match="scrcpy was not found"):
        scrcpy_module.find_scrcpy()


@pytest.mark.parametrize(
    "options",
    [
        ScrcpyOptions(serial=""),
        ScrcpyOptions(serial="device", max_size=0),
        ScrcpyOptions(serial="device", max_fps=0),
        ScrcpyOptions(serial="device", max_fps=241),
        ScrcpyOptions(serial="device", v4l2_sink="camera10"),
    ],
)
def test_option_validation_errors(options: ScrcpyOptions) -> None:
    with pytest.raises(ValueError):
        options.validate()


def test_build_full_scrcpy_command(tmp_path: Path) -> None:
    record = tmp_path / "recording.mkv"
    command = build_scrcpy_command(
        "scrcpy",
        ScrcpyOptions(
            serial="device",
            control=True,
            audio=True,
            window_title="Custom",
            max_size=1600,
            max_fps=30,
            stay_awake=False,
            turn_screen_off=True,
            v4l2_sink="/dev/video10",
            video_playback=False,
            record_path=record,
        ),
    )
    assert command == [
        "scrcpy",
        "--serial=device",
        "--window-title=Custom",
        "--max-size=1600",
        "--max-fps=30",
        "--turn-screen-off",
        "--v4l2-sink=/dev/video10",
        "--no-video-playback",
        f"--record={record.resolve()}",
    ]


def test_scrcpy_client_version_success_and_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "scrcpy"
    executable.touch()
    client = ScrcpyClient(executable)

    monkeypatch.setattr(
        scrcpy_module.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout="scrcpy 4.0\n", stderr=""
        ),
    )
    assert client.version() == ScrcpyVersion(4, 0, 0)
    assert client.ensure_supported() == ScrcpyVersion(4, 0, 0)

    monkeypatch.setattr(
        scrcpy_module.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, stdout="", stderr="failed"
        ),
    )
    with pytest.raises(ScrcpyError, match="failed"):
        client.version()

    def raise_oserror(*_args: object, **_kwargs: object) -> Any:
        raise OSError("missing")

    monkeypatch.setattr(scrcpy_module.subprocess, "run", raise_oserror)
    with pytest.raises(ScrcpyError, match="Could not execute"):
        client.version()


def test_scrcpy_client_rejects_old_and_builds_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "scrcpy"
    executable.touch()
    client = ScrcpyClient(executable)
    monkeypatch.setattr(client, "version", lambda: ScrcpyVersion(3, 3, 4))
    with pytest.raises(ScrcpyError, match="too old"):
        client.ensure_supported()

    monkeypatch.setattr(client, "version", lambda: ScrcpyVersion(4, 0, 0))
    session = client.session(ScrcpyOptions(serial="device"), log_path=tmp_path / "scrcpy.log")
    assert isinstance(session, ScrcpySession)
    assert session.log_path == (tmp_path / "scrcpy.log").resolve()


class FakeProcess:
    def __init__(
        self,
        *,
        poll_values: list[int | None] | None = None,
        wait_results: list[int | BaseException] | None = None,
    ) -> None:
        self.poll_values = list(poll_values or [None])
        self.wait_results = list(wait_results or [0])
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        if len(self.poll_values) > 1:
            return self.poll_values.pop(0)
        return self.poll_values[0]

    def wait(self, timeout: float | None = None) -> int:
        if not self.wait_results:
            return 0
        result = self.wait_results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


def test_session_start_reuses_running_process() -> None:
    session = ScrcpySession("scrcpy", ScrcpyOptions(serial="device"))
    process = FakeProcess()
    session.process = process  # type: ignore[assignment]
    assert session.start() is process


def test_session_start_wait_stop_and_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = FakeProcess(poll_values=[None], wait_results=[0, 0])
    monkeypatch.setattr(scrcpy_module.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(scrcpy_module.time, "sleep", lambda _seconds: None)

    session = ScrcpySession(
        "scrcpy", ScrcpyOptions(serial="device"), log_path=tmp_path / "logs" / "scrcpy.log"
    )
    with session as entered:
        assert entered is session
        assert session.process is process
    assert process.terminated
    assert session.process is None
    assert session._log_file is None


def test_session_wait_starts_process_and_closes_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = FakeProcess(poll_values=[None], wait_results=[7])
    monkeypatch.setattr(scrcpy_module.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(scrcpy_module.time, "sleep", lambda _seconds: None)
    session = ScrcpySession(
        "scrcpy", ScrcpyOptions(serial="device"), log_path=tmp_path / "scrcpy.log"
    )
    assert session.wait() == 7
    assert session._log_file is None


def test_session_start_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scrcpy_module.time, "sleep", lambda _seconds: None)

    def raise_oserror(*_args: object, **_kwargs: object) -> Any:
        raise OSError("cannot spawn")

    monkeypatch.setattr(scrcpy_module.subprocess, "Popen", raise_oserror)
    session = ScrcpySession(
        "scrcpy", ScrcpyOptions(serial="device"), log_path=tmp_path / "scrcpy.log"
    )
    with pytest.raises(ScrcpyError, match="Could not start"):
        session.start()
    assert session._log_file is None

    process = FakeProcess(poll_values=[9])
    monkeypatch.setattr(scrcpy_module.subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(ScrcpyError, match="exited during startup"):
        session.start()


def test_session_stop_kills_after_timeout() -> None:
    timeout = subprocess.TimeoutExpired("scrcpy", 0.1)
    process = FakeProcess(poll_values=[None], wait_results=[timeout, 0])
    session = ScrcpySession("scrcpy", ScrcpyOptions(serial="device"))
    session.process = process  # type: ignore[assignment]

    session.stop(timeout=0.1)

    assert process.terminated
    assert process.killed
    assert session.process is None


def test_session_stop_without_process() -> None:
    session = ScrcpySession("scrcpy", ScrcpyOptions(serial="device"))
    session.stop()
    assert session.process is None
