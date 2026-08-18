from __future__ import annotations

import json
from textwrap import dedent

import rushbot.game_cli as game_cli
from rushbot.game_cli import build_parser
from rushbot.game_version import SupportMatrix


def test_status_parser_defaults_to_live_gate() -> None:
    arguments = build_parser().parse_args(["status", "emulator-5554"])

    assert arguments.command == "status"
    assert arguments.serial == "emulator-5554"
    assert arguments.request_mode == "live"
    assert arguments.strict is False


def test_capture_parser_accepts_privacy_alias() -> None:
    arguments = build_parser().parse_args(
        ["capture", "emulator-5554", "frame.png", "--alias", "lab-emulator"]
    )

    assert arguments.command == "capture"
    assert arguments.alias == "lab-emulator"
    assert arguments.output.name == "frame.png"


DUMPSYS = dedent(
    """
    Package [com.my.defense] (abc):
      versionCode=3700123 minSdk=24 targetSdk=35
      versionName=37.0.1
    """
)
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 64


class FakeAdb:
    def __init__(self, path=None) -> None:
        self.path = path

    def shell(self, serial, arguments):
        return DUMPSYS

    def screencap_png(self, serial):
        return PNG


def capture_matrix() -> SupportMatrix:
    return SupportMatrix.from_toml(
        'schema_version = 1\ndefault_status = "capture_only"\ndefault_reason = "unreviewed"\n'
    )


def live_matrix() -> SupportMatrix:
    return SupportMatrix.from_toml(
        dedent(
            """
            schema_version = 1
            default_status = "capture_only"
            default_reason = "unreviewed"

            [[builds]]
            id = "live"
            package = "com.my.defense"
            version_code = 3700123
            status = "live_validated"
            reason = "validated"
            """
        )
    )


def test_status_json_and_strict_downgrade(monkeypatch, capsys) -> None:
    monkeypatch.setattr(game_cli, "AdbBackend", FakeAdb)
    monkeypatch.setattr(game_cli.SupportMatrix, "load", lambda path=None: capture_matrix())

    result = game_cli.main(["status", "emulator-5554", "--json", "--strict"])

    assert result == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "capture_only"
    assert payload["authorization"]["effective_mode"] == "capture_only"


def test_status_text_allows_exact_live_build(monkeypatch, capsys) -> None:
    monkeypatch.setattr(game_cli, "AdbBackend", FakeAdb)
    monkeypatch.setattr(game_cli.SupportMatrix, "load", lambda path=None: live_matrix())

    result = game_cli.main(["status", "emulator-5554", "--strict"])

    assert result == 0
    output = capsys.readouterr().out
    assert "Live actions: ALLOWED" in output
    assert "live -> live" in output


def test_capture_command_writes_image_and_manifest(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(game_cli, "AdbBackend", FakeAdb)
    monkeypatch.setattr(game_cli.SupportMatrix, "load", lambda path=None: capture_matrix())
    output = tmp_path / "capture.png"

    result = game_cli.main(
        ["capture", "emulator-5554", str(output), "--alias", "test-device", "--json"]
    )

    assert result == 0
    response = json.loads(capsys.readouterr().out)
    assert output.read_bytes() == PNG
    assert response["manifest"]["serial_alias"] == "test-device"
    assert response["manifest"]["compatibility"]["live_actions_allowed"] is False


def test_capture_command_text_output(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(game_cli, "AdbBackend", FakeAdb)
    monkeypatch.setattr(game_cli.SupportMatrix, "load", lambda path=None: capture_matrix())

    result = game_cli.main(["capture", "emulator-5554", str(tmp_path / "capture.png")])

    assert result == 0
    assert "Live actions: BLOCKED" in capsys.readouterr().out


def test_cli_errors_return_two(monkeypatch, capsys) -> None:
    def fail(path=None):
        raise FileNotFoundError("matrix missing")

    monkeypatch.setattr(game_cli.SupportMatrix, "load", fail)

    assert game_cli.main(["status", "emulator-5554"]) == 2
    assert "matrix missing" in capsys.readouterr().err
