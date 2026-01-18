"""Pytest configuration and fixtures."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config(temp_dir: Path) -> Path:
    """Create a sample config.ini for testing."""
    config_path = temp_dir / "config.ini"
    config_path.write_text("""\
[Settings]
; Unit positions 1-5 in deck
unit_1 = Demon Hunter
unit_2 = Knight Statue
unit_3 = Bombardier
unit_4 = Chemist
unit_5 = Portal Keeper

; Bot behavior settings
merge_behavior = auto
auto_summon = true
mana_threshold = 50

[Device]
device_ip = 127.0.0.1
scrcpy_port = 5555
""")
    return config_path
