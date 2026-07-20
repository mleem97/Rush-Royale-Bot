from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "Src"))

from adb_backend import find_adb, parse_devices


def test_parse_devices_filters_daemon_output():
    output = """List of devices attached
* daemon started successfully
emulator-5554\tdevice
192.168.1.10:5555\toffline
ABC123\tunauthorized
"""
    assert parse_devices(output) == [
        ("emulator-5554", "device"),
        ("192.168.1.10:5555", "offline"),
        ("ABC123", "unauthorized"),
    ]


def test_find_adb_prefers_explicit_path(tmp_path, monkeypatch):
    adb_name = "adb.exe" if os.name == "nt" else "adb"
    adb = tmp_path / adb_name
    adb.write_text("", encoding="utf-8")
    monkeypatch.setenv("ADB_PATH", str(adb))
    assert Path(find_adb()) == adb.resolve()
