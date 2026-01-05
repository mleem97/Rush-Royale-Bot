"""
Rush Royale Bot - Pytest Configuration and Fixtures
Python 3.13 Compatible
"""
from __future__ import annotations

import os
import sys
import pytest
import tempfile
import configparser
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Generator

# Add Src directory to path for imports
src_dir = Path(__file__).parent.parent / "Src"
sys.path.insert(0, str(src_dir))


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def src_dir() -> Path:
    """Return the Src directory path."""
    return Path(__file__).parent.parent / "Src"


@pytest.fixture
def sample_config() -> configparser.ConfigParser:
    """Create a sample valid configuration."""
    config = configparser.ConfigParser()
    config["bot"] = {
        "floor": "5",
        "mana_level": "1,2,3,4,5",
        "units": "demo, monk, robot, dryad, franky_stein",
        "dps_unit": "monk",
        "pve": "True",
        "require_shaman": "False",
    }
    return config


@pytest.fixture
def temp_config_file(sample_config: configparser.ConfigParser) -> Generator[Path, None, None]:
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
        sample_config.write(f)
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def mock_adb_client():
    """Mock ADB client for testing without real device."""
    with patch("ppadb.client.Client") as mock_client:
        mock_device = MagicMock()
        mock_device.serial = "127.0.0.1:5555"
        mock_device.shell.return_value = ""
        mock_device.input_tap.return_value = None
        mock_device.input_swipe.return_value = None
        mock_device.screencap.return_value = b"\x89PNG" + b"\x00" * 1000
        
        mock_client.return_value.devices.return_value = [mock_device]
        
        yield mock_client, mock_device


@pytest.fixture
def sample_screenshot(project_root: Path) -> Path | None:
    """Get a sample screenshot if available, or None."""
    possible_paths = [
        project_root / "bot_feed_5555.png",
        project_root / "icons" / "home_screen.png",
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None


@pytest.fixture
def sample_unit_icons(project_root: Path) -> list[Path]:
    """Get list of available unit icons."""
    units_dir = project_root / "all_units"
    if units_dir.exists():
        return list(units_dir.glob("*.png"))
    return []


@pytest.fixture
def mock_cv2():
    """Mock OpenCV for tests that don't need real image processing."""
    import numpy as np
    
    with patch("cv2.imread") as mock_imread, \
         patch("cv2.imwrite") as mock_imwrite, \
         patch("cv2.matchTemplate") as mock_match:
        
        # Return a fake image (100x100 BGR)
        mock_imread.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_imwrite.return_value = True
        mock_match.return_value = np.zeros((10, 10), dtype=np.float32)
        
        yield {
            "imread": mock_imread,
            "imwrite": mock_imwrite,
            "matchTemplate": mock_match,
        }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests requiring real device connection"
    )
    config.addinivalue_line(
        "markers", "ml: marks tests related to machine learning models"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests by default unless --run-integration is passed."""
    if not config.getoption("--run-integration", default=False):
        skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests that require device connection",
    )
